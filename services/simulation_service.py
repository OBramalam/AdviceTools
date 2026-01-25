from datetime import date
import datetime
from dateutil.relativedelta import relativedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from schemas import FinancialPlan, CashFlow, AdviserConfig
from common.utils import to_annual, convert_json_to_snake, sqlalchemy_to_pydantic_cashflow
from simulation_engine.commands import RunSimulationCommand
from simulation_engine.common.types import CashFlow as SimulationCashFlow
from simulation_engine.common.types import SimulationPortfolioWeights, ExpectedReturns, AssetCosts
from simulation_engine.common.enums import SimulationType, SimulationStepType, InterpolationMethod
from .risk_indicator_service import calculate_risk_indicator

class SimulationService:
    def __init__(
        self, 
        financial_plan: FinancialPlan, 
        cash_flows: Optional[List[CashFlow]] = None,
        adviser_config: Optional[AdviserConfig] = None,
        weights: Optional[List[SimulationPortfolioWeights]] = None,
        db: Optional[Session] = None,
    ):
        self.financial_plan = financial_plan
        self.db = db
        
        # Fetch cashflows from database if not provided
        if cash_flows is None:
            if db is None:
                raise ValueError("Database session required when cash_flows is not provided")
            if financial_plan.id is None:
                raise ValueError("Financial plan must have an id to fetch cashflows from database")
            self.cash_flows = self._get_cashflows_from_db(financial_plan.id, db)
        else:
            self.cash_flows = cash_flows
        
        # Use default adviser_config if not provided
        # TODO: In the future, fetch from database when adviser_config table is implemented
        if adviser_config is None:
            self.adviser_config = AdviserConfig()  # Uses defaults from schema
        else:
            self.adviser_config = adviser_config
        
        self.weights = weights if weights else None

    def simulate(self):
        data = self._build_simulation_data()
        command = RunSimulationCommand.model_validate(convert_json_to_snake(data))
        result = command.handle()
        return result

    def _build_simulation_data(self):
        plan_start_date = self.financial_plan.plan_start_date
        plan_end_date = plan_start_date + relativedelta(years=int(self.financial_plan.plan_end_age)-int(self.financial_plan.start_age))
        plan_start_year = plan_start_date.year
        plan_end_year = plan_end_date.year

        cash_flows = self._build_cash_flows(plan_start_year, plan_end_year)
        expected_returns = self._build_expected_returns()
        asset_costs = self._build_asset_costs()
        weights = self.weights if self.weights else self._build_weights(plan_start_year, plan_end_year)

        data = {
            "number_of_simulations": self.adviser_config.number_of_simulations,
            "end_step": plan_end_year - plan_start_year,
            "weights": weights,
            "savings_rates": cash_flows,
            "oneoff_transactions": [],
            "inflation": self.adviser_config.inflation,
            "initial_wealth": self.financial_plan.current_portfolio_value,
            "percentiles": [5, 25, 50, 75, 95],
            "simulation_type": SimulationType.CHOLESKY,
            "step_size": SimulationStepType.ANNUAL,
            "weights_interpolation": InterpolationMethod.FFILL,
            "savings_rate_interpolation": InterpolationMethod.FFILL,
            "asset_costs": asset_costs,
            "asset_returns": expected_returns
        }

        return data

    def _build_cash_flows(
        self,
        plan_start_year: int,
        plan_end_year: int,
        step_size: str = "annual"
        ) -> List[SimulationCashFlow]:

        cf_events = {}

        def add_cashflow_event(step: int, change_amount: float):
            if step < 0:
                return
            cf_events[step] = cf_events.get(step, 0.0) + change_amount

        for cf in self.cash_flows or []:
            annual = to_annual(cf.amount)
            s = cf.start_date.year - plan_start_year
            e = cf.end_date.year - plan_start_year
            add_cashflow_event(max(0, s), +annual)  # Start: add the cash flow
            add_cashflow_event(e + 1, -annual)      # End: remove the cash flow

        end_step = plan_end_year - plan_start_year
        cf_events = {k: v for k, v in cf_events.items() if 0 <= k <= end_step}

        cashflows: List[SimulationCashFlow] = []
        running = 0.0

        for step in sorted(cf_events.keys()):
            running += cf_events[step]
            cashflows.append(SimulationCashFlow(step=float(step), value=running))

        if not cashflows:
            cashflows = [SimulationCashFlow(step=0.0, value=0.0)]

        return cashflows


    def _build_weights(self, plan_start_year: int, plan_end_year: int):
        """Build portfolios with only allocation changes."""
        portfolios = []
        step = 0
        last_equity_allocation = None
        
        for year in range(plan_start_year, plan_end_year):
            years_to_retirement = (self.financial_plan.retirement_age - self.financial_plan.start_age) - step
            risk_score = calculate_risk_indicator(years_to_retirement)
            equity_allocation = self.adviser_config.risk_allocation_map[risk_score]
            
            if equity_allocation != last_equity_allocation:
                portfolios.append(SimulationPortfolioWeights(
                    step=float(step), 
                    stocks=equity_allocation, 
                    bonds=1-equity_allocation
                ))
                last_equity_allocation = equity_allocation
            
            step += 1
        
        return portfolios

    def _build_expected_returns(self):
        expected_returns = ExpectedReturns(
            stocks=self.adviser_config.expected_returns['stocks'],
            bonds=self.adviser_config.expected_returns['bonds'],
            cash=self.adviser_config.expected_returns['cash']
        )
        return expected_returns

    def _build_asset_costs(self):
        asset_costs = AssetCosts(
            stocks=self.adviser_config.asset_costs['stocks'],
            bonds=self.adviser_config.asset_costs['bonds'],
            cash=self.adviser_config.asset_costs['cash']
        )
        return asset_costs

    def _get_cashflows_from_db(self, plan_id: int, db: Session) -> List[CashFlow]:
        """Fetch cashflows for a financial plan from the database."""
        from infra.database.models.cashflow import CashFlow as DBCashFlow
        
        db_cashflows = db.query(DBCashFlow).filter(DBCashFlow.plan_id == plan_id).all()
        return [sqlalchemy_to_pydantic_cashflow(cf, CashFlow) for cf in db_cashflows]
    
    def _get_adviser_config_from_db(self, plan_id: int, db: Session) -> AdviserConfig:
        """
        Fetch adviser config for a financial plan from the database.
        
        TODO: Implement when adviser_config table is added to the database.
        For now, returns default AdviserConfig.
        """
        # Future implementation:
        # from infra.database.models.adviser_config import AdviserConfig as DBAdviserConfig
        # db_config = db.query(DBAdviserConfig).filter(DBAdviserConfig.plan_id == plan_id).first()
        # if db_config:
        #     return sqlalchemy_to_pydantic_adviser_config(db_config, AdviserConfig)
        # else:
        #     return AdviserConfig()  # Use defaults
        
        return AdviserConfig()  # Use defaults for now
