from llama_cloud_services import LlamaExtract
from dotenv import load_dotenv
from sqlalchemy.orm.session import Session
from schemas import ExtractionSchema, FinancialPlan, CashFlow, PortfolioConfig, ExpectedReturns, AssetCosts
from simulation_engine.common.types import SimulationPortfolioWeights
from common.utils import age_to_date, pydantic_to_sqlalchemy_financial_plan, pydantic_to_sqlalchemy_cashflow, sqlalchemy_to_pydantic_financial_plan, sqlalchemy_to_pydantic_cashflow, pydantic_to_sqlalchemy_portfolio, sqlalchemy_to_pydantic_portfolio
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
        agent = self.extractor.get_agent(name='advice_parser')
        data = agent.extract(self.filepath).data
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

    def _build_data_objects(self, data):

        financial_plan = FinancialPlan(
            user_id=self.user_id,
            name=data['name'],
            description=data['name'],
            start_age=data['age'],
            retirement_age=data['retirement_age'],
            plan_end_age=data['plan_end_age'],
            plan_start_date=data.get('plan_start_date', datetime.now()),
            portfolio_target_value=data.get('portfolio_target_value', 0),
        )
        financial_plan = self._commit_plan_to_db(financial_plan)

        portfolios = []
        for i in range(len(data['current_portfolio_value'])):
            portfolios.append(
                PortfolioConfig(
                    plan_id=financial_plan.id,
                    name="Default portfolio",
                    weights=[SimulationPortfolioWeights(step=0.0, stocks=0.6)],
                    expected_returns=ExpectedReturns(stocks=0.10, bonds=0.03, cash=0.02),
                    asset_costs=AssetCosts(stocks=0.0015, bonds=0.001, cash=0.001),
                    initial_portfolio_value=data['current_portfolio_value'][i],
                    cashflow_allocation=1/len(data['current_portfolio_value']),
            ))
        
        incomes = [
            CashFlow(
                plan_id=financial_plan.id,
                name=data['income_source'][i],
                description=data['income_source'][i],
                amount=data['income_amount'][i],
                start_date=age_to_date(data['age'], data['income_start_age'][i]),
                end_date=age_to_date(data['age'], data['income_end_age'][i]),
            )
            for i in range(len(data['income_source']))
        ]

        expenses = [
            CashFlow(
                plan_id=financial_plan.id,
                name=data['expense_name'][i],
                description=data['expense_name'][i],
                amount=-data['expense_amount'][i],
                start_date=age_to_date(data['age'], data['expense_start_age'][i]),
                end_date=age_to_date(data['age'], data['expense_end_age'][i]),
            )
            for i in range(len(data['expense_name']))
        ]

        cash_flows = incomes + expenses

        
        cash_flows = self._commit_cashflows_to_db(cash_flows)
        portfolios = self._commit_portfolios_to_db(portfolios)

        return financial_plan, cash_flows, portfolios

        # profile = Profile(
        #     id=self.user_id,
        #     name=data['name'],
        #     age=data['age'],
        #     retirement_age=data['retirement_age'],
        #     plan_end_age=data['plan_end_age'],
        #     current_portfolio_value=data['current_portfolio_value'],
        # )

        # incomes = [
        #     RecurringCashFlow(
        #         profile=self.user_id,
        #         name=data['income_source'][i],
        #         amount=data['income_amount'][i],
        #         start_date=age_to_date(data['age'], data['income_start_age'][i]),
        #         end_date=age_to_date(data['age'], data['income_end_age'][i]),
        #     )
        #     for i in range(len(data['income_source']))
        # ]

        # expenses = [
        #     RecurringCashFlow(
        #         profile=self.user_id,
        #         name=data['expense_name'][i],
        #         amount=-data['expense_amount'][i],
        #         start_date=age_to_date(data['age'], data['expense_start_age'][i]),
        #         end_date=age_to_date(data['age'], data['expense_end_age'][i]),
        #     )
        #     for i in range(len(data['expense_name']))
        # ]

        # recurring_cashflows = incomes + expenses

        
