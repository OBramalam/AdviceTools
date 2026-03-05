from llama_cloud_services import LlamaExtract
from dotenv import load_dotenv
from sqlalchemy.orm.session import Session
from schemas import ExtractionSchema, FinancialPlan, CashFlow, PortfolioConfig, ExpectedReturns, AssetCosts
from schemas.extraction_schema import Income, Expense, Portfolio
from simulation_engine.common.types import SimulationPortfolioWeights
from common.utils import age_to_date, pydantic_to_sqlalchemy_financial_plan, pydantic_to_sqlalchemy_cashflow, sqlalchemy_to_pydantic_financial_plan, sqlalchemy_to_pydantic_cashflow, pydantic_to_sqlalchemy_portfolio, sqlalchemy_to_pydantic_portfolio, get_adviser_config_by_user_id
from common.enums import CashFlowPeriodicity
from datetime import datetime
from infra.database.models.financial_plan import FinancialPlan as DBFinancialPlan
from infra.database.models.cashflow import CashFlow as DBCashFlow
from infra.database.models.portfolio import Portfolio as DBPortfolio


class ParserService:
    load_dotenv()

    def __init__(self, user_id, filepath, db: Session):
        self.user_id = user_id
        self.filepath = filepath
        self.extractor = LlamaExtract()
        self.db = db

    def extract_data(self):
        # TODO: Create agent if it doesn't already exist
        agent = self.extractor.get_agent(name='new_parser3')
        data_dict = agent.extract(self.filepath).data
        # Convert dict to ExtractionSchema Pydantic model
        data = ExtractionSchema(**data_dict)
        financial_plan, cashflows, portfolios = self._build_data_objects(data)

        return financial_plan, cashflows, portfolios

    def _commit_plan_to_db(self, financial_plan):
        financial_plan = pydantic_to_sqlalchemy_financial_plan(financial_plan, DBFinancialPlan)
        self.db.add(financial_plan)
        self.db.commit()
        self.db.refresh(financial_plan)
        return sqlalchemy_to_pydantic_financial_plan(financial_plan, FinancialPlan)

    def _commit_cashflows_to_db(self, cashflows):
        cashflows = [pydantic_to_sqlalchemy_cashflow(cashflow, DBCashFlow) for cashflow in cashflows]
        self.db.add_all(cashflows)
        self.db.commit()
        for cashflow in cashflows:
            self.db.refresh(cashflow)
        return [sqlalchemy_to_pydantic_cashflow(cashflow, CashFlow) for cashflow in cashflows]

    def _commit_portfolios_to_db(self, portfolios):
        portfolios = [pydantic_to_sqlalchemy_portfolio(portfolio, DBPortfolio) for portfolio in portfolios]
        self.db.add_all(portfolios)
        self.db.commit()
        for portfolio in portfolios:
            self.db.refresh(portfolio)
        return [sqlalchemy_to_pydantic_portfolio(portfolio, PortfolioConfig) for portfolio in portfolios]

    def _build_data_objects(self, data: ExtractionSchema):
        # Fetch adviser config for the user
        adviser_config = get_adviser_config_by_user_id(self.user_id, self.db)
        print(data.model_dump_json())

        # Create financial plan
        financial_plan = FinancialPlan(
            user_id=self.user_id,
            name=data.name,
            description=data.name,
            start_age=int(data.age),
            retirement_age=int(data.retirement_age),
            plan_end_age=int(data.plan_end_age),
            plan_start_date=datetime.now(),
            portfolio_target_value=0,  # Will be calculated from portfolios
        )
        financial_plan = self._commit_plan_to_db(financial_plan)

        # Convert extraction schema portfolios to PortfolioConfig objects
        portfolios = []
        if data.portfolios:
            # If portfolios are extracted, use them
            num_portfolios = len(data.portfolios)
            for portfolio in data.portfolios:
                portfolios.append(
                    PortfolioConfig(
                        plan_id=financial_plan.id,
                        name=portfolio.name or "Default portfolio",
                        weights=[SimulationPortfolioWeights(step=0.0, stocks=0.6, bonds=0.38)],
                        expected_returns=ExpectedReturns(
                            stocks=adviser_config.expected_returns.get('stocks', 0.08),
                            bonds=adviser_config.expected_returns.get('bonds', 0.04),
                            cash=adviser_config.expected_returns.get('cash', 0.02)
                        ),
                        asset_costs=AssetCosts(
                            stocks=adviser_config.asset_costs.get('stocks', 0.001),
                            bonds=adviser_config.asset_costs.get('bonds', 0.001),
                            cash=adviser_config.asset_costs.get('cash', 0.001)
                        ),
                        initial_portfolio_value=portfolio.initial_portfolio_value,
                        cashflow_allocation=1.0 / num_portfolios if num_portfolios > 0 else 1.0,
                    )
                )
        else:
            # Fallback: create default portfolio if none extracted
            portfolios.append(
                PortfolioConfig(
                    plan_id=financial_plan.id,
                    name="Default portfolio",
                    weights=[SimulationPortfolioWeights(step=0.0, stocks=0.6)],
                    expected_returns=ExpectedReturns(
                        stocks=adviser_config.expected_returns.get('stocks', 0.08),
                        bonds=adviser_config.expected_returns.get('bonds', 0.04),
                        cash=adviser_config.expected_returns.get('cash', 0.02)
                    ),
                    asset_costs=AssetCosts(
                        stocks=adviser_config.asset_costs.get('stocks', 0.001),
                        bonds=adviser_config.asset_costs.get('bonds', 0.001),
                        cash=adviser_config.asset_costs.get('cash', 0.001)
                    ),
                    initial_portfolio_value=0.0,
                    cashflow_allocation=1.0,
                )
            )

        # Convert extraction schema incomes to CashFlow objects
        incomes = []
        for income in data.incomes:
            # Derive dates from extracted start_age and end_age
            start_date = age_to_date(data.age, income.start_age)
            end_date = age_to_date(data.age, income.end_age)
            
            # Convert periodicity string to enum
            periodicity_map = {
                'monthly': CashFlowPeriodicity.MONTHLY,
                'quarterly': CashFlowPeriodicity.QUARTERLY,
                'annually': CashFlowPeriodicity.ANNUALLY,
                'one_off': CashFlowPeriodicity.ONE_OFF,
            }
            periodicity = periodicity_map.get(income.periodicity.lower(), CashFlowPeriodicity.MONTHLY)
            
            incomes.append(
                CashFlow(
                    plan_id=financial_plan.id,
                    name=income.name,
                    description=income.description or income.name,
                    amount=income.amount,
                    periodicity=periodicity,
                    frequency=income.frequency,
                    start_date=start_date,
                    end_date=end_date,
                    basis="fixed",
                    include_in_main_savings=True,
                )
            )

        # Convert extraction schema expenses to CashFlow objects
        expenses = []
        for expense in data.expenses:
            # Derive dates from extracted start_age and end_age
            start_date = age_to_date(data.age, expense.start_age)
            end_date = age_to_date(data.age, expense.end_age)
            
            # Convert periodicity string to enum
            periodicity_map = {
                'monthly': CashFlowPeriodicity.MONTHLY,
                'quarterly': CashFlowPeriodicity.QUARTERLY,
                'annually': CashFlowPeriodicity.ANNUALLY,
                'one_off': CashFlowPeriodicity.ONE_OFF,
            }
            periodicity = periodicity_map.get(expense.periodicity.lower(), CashFlowPeriodicity.MONTHLY)
            
            expenses.append(
                CashFlow(
                    plan_id=financial_plan.id,
                    name=expense.name,
                    description=expense.description or expense.name,
                    amount=-abs(expense.amount),  # Ensure expenses are negative
                    periodicity=periodicity,
                    frequency=expense.frequency,
                    start_date=start_date,
                    end_date=end_date,
                    basis="fixed",
                    include_in_main_savings=True,
                )
            )

        cash_flows = incomes + expenses

        # Commit to database
        cash_flows = self._commit_cashflows_to_db(cash_flows)
        portfolios = self._commit_portfolios_to_db(portfolios)

        return financial_plan, cash_flows, portfolios
        
