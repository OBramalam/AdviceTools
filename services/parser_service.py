from llama_cloud_services import LlamaExtract
from dotenv import load_dotenv
from sqlalchemy.orm.session import Session
from schemas import ExtractionSchema, FinancialPlan, CashFlow, PortfolioConfig, ExpectedReturns, AssetCosts
from schemas.extraction_schema import Income, Expense, Portfolio, NZExtractionSchema
from simulation_engine.common.types import SimulationPortfolioWeights
from common.utils import age_to_date, pydantic_to_sqlalchemy_financial_plan, pydantic_to_sqlalchemy_cashflow, sqlalchemy_to_pydantic_financial_plan, sqlalchemy_to_pydantic_cashflow, pydantic_to_sqlalchemy_portfolio, sqlalchemy_to_pydantic_portfolio, get_adviser_config_by_user_id
from common.enums import CashFlowPeriodicity
from datetime import datetime
from infra.database.models.financial_plan import FinancialPlan as DBFinancialPlan
from infra.database.models.cashflow import CashFlow as DBCashFlow
from infra.database.models.portfolio import Portfolio as DBPortfolio


def _normalize_name(s: str) -> str:
    return (s or "").strip().casefold()


def _portfolio_id_for_kiwisaver_name(portfolios: list[PortfolioConfig], portfolio_name: str) -> int:
    key = _normalize_name(portfolio_name)
    portfolio_by_name: dict[str, PortfolioConfig] = {}
    for p in portfolios:
        nk = _normalize_name(p.name or "")
        if nk in portfolio_by_name:
            raise ValueError(
                f"Duplicate portfolio names after normalization: {portfolio_by_name[nk].name!r} and {p.name!r}"
            )
        portfolio_by_name[nk] = p
    if key not in portfolio_by_name:
        raise ValueError(f"No portfolio matched KiwiSaver portfolio name {portfolio_name!r}")
    pid = portfolio_by_name[key].id
    if pid is None:
        raise ValueError(f"Portfolio {portfolio_name!r} has no id")
    return pid


def _resolve_reference_income_cashflow(
    cash_flows: list[CashFlow], reference_income_name: str
) -> CashFlow:
    key = _normalize_name(reference_income_name)
    matches = [cf for cf in cash_flows if _normalize_name(cf.name) == key]
    if not matches:
        raise ValueError(
            f"No cashflow found matching reference income name {reference_income_name!r}"
        )
    if len(matches) > 1:
        raise ValueError(
            f"Multiple cashflows match reference income name {reference_income_name!r}"
        )
    if not matches[0].id:
        raise ValueError("Reference cashflow has no id")
    return matches[0]


class ParserService:
    load_dotenv()

    def __init__(self, user_id, filepath, db: Session):
        self.user_id = user_id
        self.filepath = filepath
        self.extractor = LlamaExtract()
        self.db = db

    def extract_data(self):
        # TODO: Create agent if it doesn't already exist
        if self.db is not None:
            adviser_config = get_adviser_config_by_user_id(self.user_id, self.db)
            domicile = (adviser_config.tax_jurisdiction or "").lower()
        else:
            domicile = ""

        if domicile == "nz":
            agent = self.extractor.get_agent(name="nz_parser")
            data = NZExtractionSchema(**agent.extract(self.filepath).data)
        else:
            agent = self.extractor.get_agent(name="base_parser")
            data = ExtractionSchema(**agent.extract(self.filepath).data)

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

    def _build_data_objects(self, data: ExtractionSchema | NZExtractionSchema):
        # Fetch adviser config for the user
        adviser_config = get_adviser_config_by_user_id(self.user_id, self.db)

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

        if isinstance(data, NZExtractionSchema) and data.kiwisaver_specific_data:
            nz_specific_cashflows = self.build_nz_specific_cashflows(
                data, financial_plan, cash_flows, portfolios
            )
            nz_specific_cashflows = self._commit_cashflows_to_db(nz_specific_cashflows)
            cash_flows = cash_flows + nz_specific_cashflows

        return financial_plan, cash_flows, portfolios

    def build_nz_specific_cashflows(
        self,
        data: NZExtractionSchema,
        financial_plan: FinancialPlan,
        cash_flows: list[CashFlow],
        portfolios: list[PortfolioConfig],
    ) -> list[CashFlow]:
        government_contribution = 260
        nz_specific_cashflows: list[CashFlow] = []
        ks_end = age_to_date(data.age, financial_plan.retirement_age)

        for ks in data.kiwisaver_specific_data:
            ref = _resolve_reference_income_cashflow(cash_flows, ks.reference_income)
            portfolio_id = _portfolio_id_for_kiwisaver_name(portfolios, ks.kiwisaver_portfolio_name)
            ks_start = ref.start_date
            ks_end_date = ref.end_date if ref.end_date is not None else ks_end

            nz_specific_cashflows.append(
                CashFlow(
                    plan_id=financial_plan.id,
                    portfolio_id=portfolio_id,
                    name="Employee contribution",
                    description="Employee contribution",
                    amount=ks.kiwisaver_employee_contribution,
                    periodicity=CashFlowPeriodicity.MONTHLY,
                    frequency=1,
                    start_date=ks_start,
                    end_date=ks_end_date,
                    basis="pct_specific_income",
                    include_in_main_savings=True,
                    reference_cashflow_id=ref.id,
                )
            )

            nz_specific_cashflows.append(
                CashFlow(
                    plan_id=financial_plan.id,
                    portfolio_id=portfolio_id,
                    name="Employer contribution",
                    description="Employer contribution",
                    amount=ks.kiwisaver_employer_contribution,
                    periodicity=CashFlowPeriodicity.MONTHLY,
                    frequency=1,
                    start_date=ks_start,
                    end_date=ks_end_date,
                    basis="pct_specific_income",
                    include_in_main_savings=False,
                    reference_cashflow_id=ref.id,
                )
            )

            nz_specific_cashflows.append(
                CashFlow(
                    plan_id=financial_plan.id,
                    portfolio_id=portfolio_id,
                    name="Government contribution",
                    description="Government contribution",
                    amount=government_contribution,
                    periodicity=CashFlowPeriodicity.MONTHLY,
                    frequency=1,
                    start_date=ks_start,
                    end_date=ks_end_date,
                    basis="fixed",
                    include_in_main_savings=False,
                )
            )

        return nz_specific_cashflows
