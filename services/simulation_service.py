from datetime import date
import datetime
from dateutil.relativedelta import relativedelta
from typing import List
from schemas import Profile, RecurringCashFlow, AdviserConfig
from common.utils import to_annual, convert_json_to_snake
from simulation_engine.commands import RunSimulationCommand
from simulation_engine.common.types import CashFlow, SimulationPortfolioWeights, ExpectedReturns, AssetCosts
from simulation_engine.common.enums import SimulationType, SimulationStepType, InterpolationMethod
from .risk_indicator_service import calculate_risk_indicator

class SimulationService:
    def __init__(
        self, 
        profile: Profile, 
        cash_flows: List[RecurringCashFlow], 
        adviser_config: AdviserConfig
    ):
        self.profile = profile
        self.cash_flows = cash_flows
        self.adviser_config = adviser_config

    def simulate(self):

        data = self._build_simulation_data()

        command = RunSimulationCommand.model_validate(convert_json_to_snake(data))
        result = command.handle()
        return result


    def _build_simulation_data(self):
        plan_start_date = datetime.date.today()
        plan_end_date = plan_start_date + relativedelta(years=int(self.profile.plan_end_age)-int(self.profile.age))
        plan_start_year = plan_start_date.year
        plan_end_year = plan_end_date.year

        cash_flows = self._build_cash_flows(plan_start_year, plan_end_year)
        weights = self._build_weights(plan_start_year, plan_end_year)
        expected_returns = self._build_expected_returns()
        asset_costs = self._build_asset_costs()

        data = {
            "number_of_simulations": self.adviser_config.number_of_simulations,
            "end_step": plan_end_year - plan_start_year,
            "weights": weights,
            "savings_rates": cash_flows,
            "oneoff_transactions": [],
            "inflation": self.adviser_config.inflation,
            "initial_wealth": self.profile.current_portfolio_value,
            "percentiles": [25, 50, 75],
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
        ) -> List[CashFlow]:

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

        cashflows: List[CashFlow] = []
        running = 0.0

        for step in sorted(cf_events.keys()):
            running += cf_events[step]
            cashflows.append(CashFlow(step=float(step), value=running))

        if not cashflows:
            cashflows = [CashFlow(step=0.0, value=0.0)]

        return cashflows


    def _build_weights(self, plan_start_year: int, plan_end_year: int):
        """Build portfolios with only allocation changes."""
        portfolios = []
        step = 0
        last_equity_allocation = None
        
        for year in range(plan_start_year, plan_end_year):
            years_to_retirement = (self.profile.retirement_age - self.profile.age) - step
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
 