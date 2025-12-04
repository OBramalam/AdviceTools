from llama_cloud_services import LlamaExtract
from dotenv import load_dotenv
from sqlalchemy.orm.session import Session
from schemas import ExtractionSchema, FinancialPlan, CashFlow
from common.utils import age_to_date, pydantic_to_sqlalchemy_financial_plan, pydantic_to_sqlalchemy_cashflow, sqlalchemy_to_pydantic_financial_plan, sqlalchemy_to_pydantic_cashflow
from datetime import datetime
from infra.database.models.financial_plan import FinancialPlan as DBFinancialPlan
from infra.database.models.cashflow import CashFlow as DBCashFlow


class ParserService:
    load_dotenv()

    def __init__(self, user_id, filepath, db: Session):
        self.user_id = user_id
        self.filepath = filepath
        self.extractor = LlamaExtract()
        self.db = db

    def extract_data(self):
        # TODO: Create agent if it doesn't already exist
        agent = self.extractor.get_agent(name='conversation_parser')
        data = agent.extract(self.filepath).data
        financial_plan, cashflows = self._build_data_objects(data)

        return financial_plan, cashflows

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

    def _build_data_objects(self, data):

        financial_plan = FinancialPlan(
            user_id=self.user_id,
            name=data['name'],
            description=data['name'],
            start_age=data['age'],
            retirement_age=data['retirement_age'],
            plan_end_age=data['plan_end_age'],
            plan_start_date=data.get('plan_start_date', datetime.now()),
            current_portfolio_value=data['current_portfolio_value'],
            portfolio_target_value=data.get('portfolio_target_value', 0),
        )

        financial_plan = self._commit_plan_to_db(financial_plan)

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

        return financial_plan, cash_flows

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

        
