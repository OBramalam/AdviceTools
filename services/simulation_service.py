from datetime import date
import datetime
import time
import logging
from dateutil.relativedelta import relativedelta
from typing import List, Optional, Dict
import numpy as np
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
from schemas import FinancialPlan, CashFlow, AdviserConfig, PortfolioConfig
from common.utils import to_annual, convert_json_to_snake, sqlalchemy_to_pydantic_cashflow, get_adviser_config_by_user_id
from common.enums import CashFlowPeriodicity
from simulation_engine.commands import RunSimulationCommand
from simulation_engine.common.types import CashFlow as SimulationCashFlow
from simulation_engine.common.types import SimulationPortfolioWeights, ExpectedReturns, AssetCosts
from simulation_engine.common.enums import SimulationType, SimulationStepType, InterpolationMethod
from simulation_engine.dto import SimulationResultDTO, SimulationDataDTO, MultiPortfolioSimulationResultDTO
from .risk_indicator_service import calculate_risk_indicator
from .cashflow_service import CashflowService

class SimulationService:
    # TODO: Move this to adviser_config later
    USE_MONTHLY_STEPS = True  # Set to False for annual steps

    def __init__(
        self, 
        financial_plan: FinancialPlan, 
        cash_flows: Optional[List[CashFlow]] = None,
        adviser_config: Optional[AdviserConfig] = None,
        weights: Optional[List[SimulationPortfolioWeights]] = None,
        portfolios: Optional[List[PortfolioConfig]] = None,
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
            t0 = time.time()
            self.cash_flows = self._get_cashflows_from_db(financial_plan.id, db)
            logger.info(f"[TIMING] DB: Fetch cashflows: {time.time() - t0:.3f}s")
        else:
            self.cash_flows = cash_flows

        # Use default adviser_config if not provided, otherwise fetch from database
        if adviser_config is None:
            if db and financial_plan.user_id:
                # Fetch from database using user_id
                t0 = time.time()
                self.adviser_config = get_adviser_config_by_user_id(financial_plan.user_id, db)
                logger.info(f"[TIMING] DB: Fetch adviser_config: {time.time() - t0:.3f}s")
            else:
                # Fallback to defaults if no db session or user_id
                self.adviser_config = AdviserConfig()  # Uses defaults from schema
        else:
            self.adviser_config = adviser_config
        
        self.weights = weights if weights else None
        # Cashflow service encapsulates all plan/portfolio cashflow construction.
        self.cashflow_service = CashflowService(use_monthly_steps=self.USE_MONTHLY_STEPS)

        # Handle portfolios: if provided, use them; otherwise fetch from database or use default
        if portfolios is not None:
            self.portfolios = portfolios
            self._validate_portfolio_allocations()
        else:
            # Try to fetch portfolios from database
            if db is not None and financial_plan.id is not None:
                t0 = time.time()
                self.portfolios = self._get_portfolios_from_db(financial_plan.id, db)
                logger.info(f"[TIMING] DB: Fetch portfolios: {time.time() - t0:.3f}s")
                if self.portfolios:
                    self._validate_portfolio_allocations()
                else:
                    # No portfolios in database, use default single portfolio behavior
                    self.portfolios = None
            else:
                # No database access, use default single portfolio behavior
                self.portfolios = None

    def simulate(self) -> MultiPortfolioSimulationResultDTO:
        """
        Run simulation.
        
        Always returns MultiPortfolioSimulationResultDTO for consistent structure:
        - For single portfolio: individual_portfolios contains one entry, aggregated is the same result
        - For multi-portfolio: individual_portfolios contains all portfolios, aggregated is the combined result
        
        Returns:
            MultiPortfolioSimulationResultDTO: Contains aggregated and individual portfolio results
        """
        # If portfolios are specified, run multi-portfolio simulation
        if self.portfolios is not None:
            return self._simulate_multiple_portfolios()
        else:
            # Single portfolio simulation: wrap in MultiPortfolioSimulationResultDTO
            return self._simulate_single_portfolio()
            

    def _simulate_multiple_portfolios(self) -> MultiPortfolioSimulationResultDTO:
        """Run simulation for multiple portfolios and return both aggregated and individual results."""
        # Build plan-level cashflow context and per-portfolio streams using CashflowService.
        plan_ctx = self.cashflow_service.build_plan_cashflow_context(
            self.financial_plan, self.cash_flows
        )
        portfolio_streams = self.cashflow_service.build_portfolio_streams(
            plan_ctx, self.portfolios, self.cash_flows
        )

        step_size = SimulationStepType.MONTHLY if self.USE_MONTHLY_STEPS else SimulationStepType.ANNUAL
        end_step = plan_ctx.end_step
        inflation = self._convert_inflation_to_period(self.adviser_config.inflation)

        # Run simulation for each portfolio
        portfolio_results: Dict[str, SimulationResultDTO] = {}
        total_simulation_time = 0.0
        
        for portfolio in self.portfolios:
            # Use portfolio-specific initial wealth directly (nominal dollar value)
            portfolio_initial_wealth = portfolio.initial_portfolio_value

            # Retrieve pre-built cashflow streams for this portfolio.
            portfolio_key = str(portfolio.id) if portfolio.id else f"temp_{len(portfolio_results)}"
            streams = portfolio_streams[portfolio_key]
            
            # Convert portfolio expected returns and asset costs if using monthly steps
            if self.USE_MONTHLY_STEPS:
                # Convert annual returns to monthly: monthly = (1 + annual)^(1/12) - 1
                portfolio_expected_returns = ExpectedReturns(
                    stocks=(1 + portfolio.expected_returns.stocks) ** (1/12) - 1 if portfolio.expected_returns.stocks is not None else None,
                    bonds=(1 + portfolio.expected_returns.bonds) ** (1/12) - 1 if portfolio.expected_returns.bonds is not None else None,
                    cash=(1 + portfolio.expected_returns.cash) ** (1/12) - 1 if portfolio.expected_returns.cash is not None else None
                )
                # Convert annual costs to monthly (linear division, costs are not compounded)
                portfolio_asset_costs = AssetCosts(
                    stocks=portfolio.asset_costs.stocks / 12,
                    bonds=portfolio.asset_costs.bonds / 12,
                    cash=portfolio.asset_costs.cash / 12
                )
            else:
                portfolio_expected_returns = portfolio.expected_returns
                portfolio_asset_costs = portfolio.asset_costs


            # Validate and prepare tax config for this portfolio
            from common.utils import validate_tax_config
            tax_model_config = validate_tax_config(
                portfolio.tax_jurisdiction,
                portfolio.tax_config
            )
            
            # Build simulation data for this portfolio
            data = {
                "number_of_simulations": self.adviser_config.number_of_simulations,
                "end_step": end_step,
                "weights": portfolio.weights,
                "savings_rates": streams.savings_rates,
                "oneoff_transactions": streams.transactions,
                "inflation": inflation,
                "initial_wealth": portfolio_initial_wealth,
                "percentiles": [5, 25, 50, 75, 95],
                "simulation_type": SimulationType.CHOLESKY,
                "step_size": step_size,
                "weights_interpolation": InterpolationMethod.FFILL,
                "savings_rate_interpolation": InterpolationMethod.FFILL,
                "asset_costs": portfolio_asset_costs,
                "asset_returns": portfolio_expected_returns,
                "tax_model_config": tax_model_config
            }
            
            command = RunSimulationCommand.model_validate(convert_json_to_snake(data))
            result = command.handle()
            # Use id as key, or generate a temporary key if id is None
            portfolio_key = str(portfolio.id) if portfolio.id else f"temp_{len(portfolio_results)}"
            portfolio_results[portfolio_key] = result
        
        # Aggregate results across all portfolios
        aggregated_result = self._aggregate_portfolio_results(portfolio_results, end_step)
        
        # Return both aggregated and individual results
        timestep_unit = "monthly" if self.USE_MONTHLY_STEPS else "annual"
        return MultiPortfolioSimulationResultDTO(
            timestep_unit=timestep_unit,
            aggregated=aggregated_result,
            individual_portfolios=portfolio_results
        )

    def _simulate_single_portfolio(self) -> MultiPortfolioSimulationResultDTO:
        """
        Run simulation for a single portfolio (default behavior).
        Returns MultiPortfolioSimulationResultDTO with one portfolio in individual_portfolios
        and the same result as aggregated.
        """
        data = self._build_simulation_data()
        command = RunSimulationCommand.model_validate(convert_json_to_snake(data))
        result = command.handle()
        
        # Wrap single portfolio result in MultiPortfolioSimulationResultDTO
        # Use "default" as the key for single portfolio simulations
        timestep_unit = "monthly" if self.USE_MONTHLY_STEPS else "annual"
        return MultiPortfolioSimulationResultDTO(
            timestep_unit=timestep_unit,
            aggregated=result,
            individual_portfolios={"default": result}
        )

    def _build_simulation_data(self):
        plan_start_date = self.financial_plan.plan_start_date
        plan_end_date = plan_start_date + relativedelta(years=int(self.financial_plan.plan_end_age)-int(self.financial_plan.start_age))
        plan_start_year = plan_start_date.year
        plan_end_year = plan_end_date.year

        cash_flows = self._build_cash_flows(plan_start_year, plan_end_year)
        transactions = self._build_transactions_from_irregular_cashflows(plan_start_year, plan_end_year)
        expected_returns = self._build_expected_returns()
        asset_costs = self._build_asset_costs()
        weights = self.weights if self.weights else self._build_weights(plan_start_year, plan_end_year)

        steps_per_year = 12 if self.USE_MONTHLY_STEPS else 1
        step_size = SimulationStepType.MONTHLY if self.USE_MONTHLY_STEPS else SimulationStepType.ANNUAL
        inflation = self._convert_inflation_to_period(self.adviser_config.inflation)

        end_step = (plan_end_year - plan_start_year) * steps_per_year

        data = {
            "number_of_simulations": self.adviser_config.number_of_simulations,
            "end_step": end_step,
            "weights": weights,
            "savings_rates": cash_flows,
            "oneoff_transactions": transactions,
            "inflation": inflation,
            "initial_wealth": 0.0,  # TODO: This method should not be used - always create default portfolio instead
            "percentiles": [5, 25, 50, 75, 95],
            "simulation_type": SimulationType.CHOLESKY,
            "step_size": step_size,
            "weights_interpolation": InterpolationMethod.FFILL,
            "savings_rate_interpolation": InterpolationMethod.FFILL,
            "asset_costs": asset_costs,
            "asset_returns": expected_returns
        }

        # 1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 99

        return data

    def _normalize_periodicity(self, periodicity) -> CashFlowPeriodicity:
        """Normalize periodicity to enum, handling string values from database."""
        if isinstance(periodicity, str):
            try:
                return CashFlowPeriodicity(periodicity)
            except ValueError:
                return CashFlowPeriodicity.MONTHLY
        elif isinstance(periodicity, CashFlowPeriodicity):
            return periodicity
        else:
            return CashFlowPeriodicity.MONTHLY

    def _build_cash_flows(
        self,
        plan_start_year: int,
        plan_end_year: int,
        step_size: str = "annual"
        ) -> List[SimulationCashFlow]:
        """
        Build regular monthly cashflows (periodicity=MONTHLY, frequency=1) using step-function approach.
        These are sparse cashflows that get interpolated to create a continuous rate.
        """ 
        steps_per_year = 12 if self.USE_MONTHLY_STEPS else 1
        cf_events = {}

        def add_cashflow_event(step: int, change_amount: float):
            if step < 0:
                return
            cf_events[step] = cf_events.get(step, 0.0) + change_amount

        # Only process regular monthly cashflows (periodicity=MONTHLY, frequency=1)
        for cf in self.cash_flows or []:
            # Plan-level main cashflows only: ignore portfolio-specific rows here
            # and any cashflows that are explicitly excluded from main savings.
            if getattr(cf, "portfolio_id", None) is not None:
                continue
            if not getattr(cf, "include_in_main_savings", True):
                continue
            # For now, only treat 'fixed' basis as part of main cashflows. Percentage-based
            # cashflows (pct_total_income, pct_specific_income, pct_savings) will be
            # handled separately as portfolio-specific contributions.
            if getattr(cf, "basis", "fixed") != "fixed":
                continue
            periodicity = self._normalize_periodicity(getattr(cf, 'periodicity', CashFlowPeriodicity.MONTHLY))
            frequency = getattr(cf, 'frequency', 1)
            
            # Skip irregular cashflows (will be handled as transactions)
            if periodicity != CashFlowPeriodicity.MONTHLY or frequency != 1:
                continue
            
            # Regular monthly cashflows require both start and end dates
            if not cf.start_date or not cf.end_date:
                continue
            
            # Use step-function approach: add at start, subtract at end+1
            # Cashflow array stores monthly amounts for monthly steps, annual for annual steps
            if self.USE_MONTHLY_STEPS:
                amount = cf.amount  # Keep as monthly amount
                start_year_diff = cf.start_date.year - plan_start_year
                start_month = cf.start_date.month - 1
                s = start_year_diff * 12 + start_month
                
                end_year_diff = cf.end_date.year - plan_start_year
                end_month = cf.end_date.month - 1
                e = end_year_diff * 12 + end_month
            else:
                amount = to_annual(cf.amount)  # Convert monthly to annual
            s = cf.start_date.year - plan_start_year
            e = cf.end_date.year - plan_start_year

            add_cashflow_event(max(0, s), +amount)  # Start: add the cash flow
            add_cashflow_event(e + 1, -amount)      # End: remove the cash flow

        end_step = (plan_end_year - plan_start_year) * steps_per_year
        cf_events = {k: v for k, v in cf_events.items() if 0 <= k <= end_step}

        cashflows: List[SimulationCashFlow] = []
        running = 0.0

        # Build as step function (running total) - will be interpolated
        for step in sorted(cf_events.keys()):
            running += cf_events[step]
            cashflows.append(SimulationCashFlow(step=float(step), value=running))

        if not cashflows:
            cashflows = [SimulationCashFlow(step=0.0, value=0.0)]

        return cashflows

    def _build_transactions_from_irregular_cashflows(
        self,
        plan_start_year: int,
        plan_end_year: int
        ) -> List[SimulationCashFlow]:
        """
        Build one-off transactions from irregular cashflows (everything except monthly, frequency=1).
        These are discrete events at specific steps.
        """
        steps_per_year = 12 if self.USE_MONTHLY_STEPS else 1
        transactions = {}

        def normalize_feb_29(date_obj: datetime.datetime) -> datetime.datetime:
            """Convert Feb 29 to Feb 28 for annual cashflow handling."""
            if date_obj.month == 2 and date_obj.day == 29:
                return date_obj.replace(day=28)
            return date_obj

        def calculate_step_from_date(date_obj: datetime.datetime, plan_start_year: int) -> int:
            """Calculate simulation step from a date."""
            if self.USE_MONTHLY_STEPS:
                year_diff = date_obj.year - plan_start_year
                month = date_obj.month - 1
                return year_diff * 12 + month
            else:
                return date_obj.year - plan_start_year

        def add_transaction(step: int, amount: float):
            """Add a transaction at a specific step (sum if multiple at same step)."""
            if step < 0:
                return
            transactions[step] = transactions.get(step, 0.0) + amount

        # Process all irregular cashflows
        for cf in self.cash_flows or []:
            # Plan-level main cashflows only: ignore portfolio-specific rows here
            # and any cashflows that are explicitly excluded from main savings.
            if getattr(cf, "portfolio_id", None) is not None:
                continue
            if not getattr(cf, "include_in_main_savings", True):
                continue
            if getattr(cf, "basis", "fixed") != "fixed":
                continue
            periodicity = self._normalize_periodicity(getattr(cf, 'periodicity', CashFlowPeriodicity.MONTHLY))
            frequency = getattr(cf, 'frequency', 1)
            
            # Skip regular monthly cashflows (handled in _build_cash_flows)
            if periodicity == CashFlowPeriodicity.MONTHLY and frequency == 1:
                continue
            
            # Handle one-off cashflows
            if periodicity == CashFlowPeriodicity.ONE_OFF:
                if not cf.start_date:
                    continue
                occurrence_date = normalize_feb_29(cf.start_date)
                step = calculate_step_from_date(occurrence_date, plan_start_year)
                add_transaction(step, cf.amount)
                continue
            
            # Handle irregular recurring cashflows (require both start and end dates)
            if not cf.start_date or not cf.end_date:
                continue
            
            # Normalize start_date (handle Feb 29)
            current_date = normalize_feb_29(cf.start_date)
            end_date = normalize_feb_29(cf.end_date)
            
            # Determine interval in months based on periodicity
            if periodicity == CashFlowPeriodicity.MONTHLY:
                interval_months = frequency
            elif periodicity == CashFlowPeriodicity.QUARTERLY:
                interval_months = frequency * 3
            elif periodicity == CashFlowPeriodicity.ANNUALLY:
                interval_months = frequency * 12
            else:
                interval_months = frequency
            
            # Amount is the full amount per occurrence (no conversion needed)
            amount_per_occurrence = cf.amount
            
            # Generate all occurrences between start_date and end_date
            while current_date <= end_date:
                step = calculate_step_from_date(current_date, plan_start_year)
                add_transaction(step, amount_per_occurrence)
                
                # Move to next occurrence
                current_date = current_date + relativedelta(months=interval_months)
                
                # Normalize Feb 29 to Feb 28 after date arithmetic
                if periodicity == CashFlowPeriodicity.ANNUALLY:
                    current_date = normalize_feb_29(current_date)

        end_step = (plan_end_year - plan_start_year) * steps_per_year
        transactions = {k: v for k, v in transactions.items() if 0 <= k <= end_step}

        # Convert to list of SimulationCashFlow objects
        transaction_list: List[SimulationCashFlow] = []
        for step in sorted(transactions.keys()):
            transaction_list.append(SimulationCashFlow(step=float(step), value=transactions[step]))

        if not transaction_list:
            transaction_list = [SimulationCashFlow(step=0.0, value=0.0)]

        return transaction_list


    def _build_weights(self, plan_start_year: int, plan_end_year: int):
        """Build portfolios with only allocation changes."""
        steps_per_year = 12 if self.USE_MONTHLY_STEPS else 1
        portfolios = []
        step = 0
        last_equity_allocation = None
        
        for year in range(plan_start_year, plan_end_year):
            # Calculate years to retirement based on year index, not step index
            year_index = year - plan_start_year
            years_to_retirement = (self.financial_plan.retirement_age - self.financial_plan.start_age) - year_index
            risk_score = calculate_risk_indicator(years_to_retirement)
            equity_allocation = self.adviser_config.risk_allocation_map[risk_score]
            
            if equity_allocation != last_equity_allocation:
                # Convert step to monthly if needed
                step_in_simulation_units = step * steps_per_year
                portfolios.append(SimulationPortfolioWeights(
                    step=float(step_in_simulation_units), 
                    stocks=equity_allocation, 
                    bonds=1-equity_allocation
                ))
                last_equity_allocation = equity_allocation
            
            step += 1
        
        return portfolios

    def _build_expected_returns(self):
        """Build expected returns, converting from annual to monthly if using monthly steps."""
        if self.USE_MONTHLY_STEPS:
            # Convert annual returns to monthly: monthly = (1 + annual)^(1/12) - 1
            stocks_annual = self.adviser_config.expected_returns['stocks']
            bonds_annual = self.adviser_config.expected_returns['bonds']
            cash_annual = self.adviser_config.expected_returns['cash']
            
            stocks_monthly = (1 + stocks_annual) ** (1/12) - 1
            bonds_monthly = (1 + bonds_annual) ** (1/12) - 1
            cash_monthly = (1 + cash_annual) ** (1/12) - 1
            
            expected_returns = ExpectedReturns(
                stocks=stocks_monthly,
                bonds=bonds_monthly,
                cash=cash_monthly
            )
        else:
            expected_returns = ExpectedReturns(
                stocks=self.adviser_config.expected_returns['stocks'],
                bonds=self.adviser_config.expected_returns['bonds'],
                cash=self.adviser_config.expected_returns['cash']
            )
        return expected_returns

    def _build_asset_costs(self):
        """Build asset costs, converting from annual to monthly if using monthly steps."""
        if self.USE_MONTHLY_STEPS:
            asset_costs = AssetCosts(
                stocks=self.adviser_config.asset_costs['stocks'] / 12,
                bonds=self.adviser_config.asset_costs['bonds'] / 12,
                cash=self.adviser_config.asset_costs['cash'] / 12
            )
        else:
            asset_costs = AssetCosts(
                stocks=self.adviser_config.asset_costs['stocks'],
                bonds=self.adviser_config.asset_costs['bonds'],
                cash=self.adviser_config.asset_costs['cash']
            )
        return asset_costs
    
    def _convert_inflation_to_period(self, annual_inflation: float) -> float:
        """Convert annual inflation to the appropriate period (monthly or annual)."""
        if self.USE_MONTHLY_STEPS:
            # Convert annual inflation to monthly: monthly = (1 + annual)^(1/12) - 1
            monthly_inflation = (1 + annual_inflation) ** (1/12) - 1
            return monthly_inflation
        else:
            return annual_inflation

    def _get_cashflows_from_db(self, plan_id: int, db: Session) -> List[CashFlow]:
        """Fetch cashflows for a financial plan from the database."""
        from infra.database.models.cashflow import CashFlow as DBCashFlow
        
        db_cashflows = db.query(DBCashFlow).filter(DBCashFlow.plan_id == plan_id).all()
        return [sqlalchemy_to_pydantic_cashflow(cf, CashFlow) for cf in db_cashflows]
    
    def _get_portfolios_from_db(self, plan_id: int, db: Session) -> Optional[List[PortfolioConfig]]:
        """Fetch portfolios for a financial plan from the database."""
        from infra.database.models.portfolio import Portfolio as DBPortfolio
        from common.utils import sqlalchemy_to_pydantic_portfolio
        
        db_portfolios = db.query(DBPortfolio).filter(DBPortfolio.plan_id == plan_id).all()
        
        if not db_portfolios:
            return None
        
        return [sqlalchemy_to_pydantic_portfolio(p, PortfolioConfig) for p in db_portfolios]
    
    def _get_adviser_config_from_db(self, user_id: int, db: Session) -> AdviserConfig:
        """
        Fetch adviser config for a user from the database.
        
        Args:
            user_id: The user ID to fetch the config for
            db: SQLAlchemy database session
        
        Returns:
            AdviserConfig: The user's adviser config, or default config if not found
        """
        return get_adviser_config_by_user_id(user_id, db)
    
    def _validate_portfolio_allocations(self):
        """Validate that portfolio values and cashflow allocations are valid."""
        # Check that initial portfolio values are non-negative
        for portfolio in self.portfolios:
            if portfolio.initial_portfolio_value < 0:
                portfolio_identifier = portfolio.id if portfolio.id else "new"
                raise ValueError(
                    f"Portfolio (id={portfolio_identifier}) has negative initial_portfolio_value: {portfolio.initial_portfolio_value}"
                )
        
        # Validation: portfolio values must be non-negative
        # (removed check against current_portfolio_value since that field no longer exists)
        
        # Validate cashflow allocations sum to 1.0
        total_cashflow_allocation = sum(p.cashflow_allocation for p in self.portfolios)
        if not abs(total_cashflow_allocation - 1.0) < 1e-6:
            raise ValueError(
                f"Cashflow allocations must sum to 1.0, got {total_cashflow_allocation}"
        )
    
    def _aggregate_portfolio_results(
        self, 
        portfolio_results: Dict[str, SimulationResultDTO],
        end_step: int
    ) -> SimulationResultDTO:
        """Aggregate simulation results from multiple portfolios."""
        # Get timesteps from first portfolio (all should have same timesteps)
        first_result = next(iter(portfolio_results.values()))
        timesteps = first_result.timesteps
        
        # Aggregate nominal wealth data (sum across portfolios)
        aggregated_nominal_data = None
        aggregated_real_data = None
        
        for portfolio_id, result in portfolio_results.items():
            if aggregated_nominal_data is None:
                aggregated_nominal_data = result.nominal.simulation_data.copy()
                aggregated_real_data = result.real.simulation_data.copy()
            else:
                aggregated_nominal_data += result.nominal.simulation_data
                aggregated_real_data += result.real.simulation_data
        
        # Calculate aggregated statistics
        aggregated_nominal_mean = np.mean(aggregated_nominal_data, axis=0)
        aggregated_nominal_median = np.median(aggregated_nominal_data, axis=0)
        aggregated_nominal_percentiles = np.percentile(aggregated_nominal_data, [5, 25, 50, 75, 95], axis=0)
        
        aggregated_real_mean = np.mean(aggregated_real_data, axis=0)
        aggregated_real_median = np.median(aggregated_real_data, axis=0)
        aggregated_real_percentiles = np.percentile(aggregated_real_data, [5, 25, 50, 75, 95], axis=0)
        
        # Calculate final statistics
        final_nominal_mean = aggregated_nominal_mean[-1]
        final_nominal_median = aggregated_nominal_median[-1]
        final_nominal_std = np.std(aggregated_nominal_data[:, -1])
        final_nominal_min = np.min(aggregated_nominal_data[:, -1])
        final_nominal_max = np.max(aggregated_nominal_data[:, -1])
        
        final_real_mean = aggregated_real_mean[-1]
        final_real_median = aggregated_real_median[-1]
        final_real_std = np.std(aggregated_real_data[:, -1])
        final_real_min = np.min(aggregated_real_data[:, -1])
        final_real_max = np.max(aggregated_real_data[:, -1])
        
        # Calculate destitution risk (any portfolio at zero = destitute)
        # For aggregated wealth, destitution is when total wealth is zero
        destitution_risk = (aggregated_nominal_data == 0).sum(axis=0) / aggregated_nominal_data.shape[0]
        
        # Calculate time deltas (same as in simulation engine)
        time_deltas = np.diff(np.concatenate([[0], timesteps]))
        destitution_area = np.sum(destitution_risk * time_deltas) / np.sum(time_deltas) if np.sum(time_deltas) > 0 else 0.0
        
        # Build aggregated DTOs
        aggregated_nominal = SimulationDataDTO(
            simulation_data=aggregated_nominal_data,
            percentiles={percentile: aggregated_nominal_percentiles[i, :].tolist() for i, percentile in enumerate([5, 25, 50, 75, 95])},
            mean=aggregated_nominal_mean.tolist(),
            final_mean=final_nominal_mean,
            final_median=final_nominal_median,
            final_std=final_nominal_std,
            final_min=final_nominal_min,
            final_max=final_nominal_max,
        )
        
        aggregated_real = SimulationDataDTO(
            simulation_data=aggregated_real_data,
            percentiles={percentile: aggregated_real_percentiles[i, :].tolist() for i, percentile in enumerate([5, 25, 50, 75, 95])},
            mean=aggregated_real_mean.tolist(),
            final_mean=final_real_mean,
            final_median=final_real_median,
            final_std=final_real_std,
            final_min=final_real_min,
            final_max=final_real_max,
        )
        
        # Calculate total parameters and simulation time (sum across all portfolios)
        total_parameters = sum(
            result.total_parameters for result in portfolio_results.values()
        )
        total_simulation_time = sum(
            result.simulation_time for result in portfolio_results.values()
        )
        
        return SimulationResultDTO(
            real=aggregated_real,
            nominal=aggregated_nominal,
            destitution=destitution_risk.tolist(),
            timesteps=timesteps,
            simulation_time=total_simulation_time,
            simulation_time_per_timestep=total_simulation_time / len(timesteps) if len(timesteps) > 0 else 0.0,
            simulation_time_per_path=total_simulation_time / self.adviser_config.number_of_simulations,
            total_parameters=total_parameters,
            destitution_area=destitution_area,
        )
