from llama_cloud_services import LlamaExtract
from dotenv import load_dotenv
from schemas import ExtractionSchema, Profile, RecurringCashFlow, FinancialPlan, CashFlow
from common.utils import age_to_date
from datetime import datetime

class ParserService:
    load_dotenv()

    def __init__(self, user_id, filepath):
        self.user_id = user_id
        self.filepath = filepath
        self.extractor = LlamaExtract()

    def extract_data(self):
        agent = self.extractor.get_agent(name='parser')
        data = agent.extract(self.filepath).data
        profile, cashflows = self._build_data_objects(data)
        return profile, cashflows

    def save(self):
        pass

    def _build_data_objects(self, data):

        financial_plan = FinancialPlan(
            user_id=self.user_id,
            name=data['name'],
            description=data['description'],
            start_age=data['age'],
            retirement_age=data['retirement_age'],
            plan_end_age=data['plan_end_age'],
            plan_start_date=datetime.now(),
            current_portfolio_value=data['current_portfolio_value'],
            portfolio_target_value=data['portfolio_target_value'],
        )

        incomes = [
            CashFlow(
                plan_id=financial_plan.id,
                name=data['income_source'][i],
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
                amount=-data['expense_amount'][i],
                start_date=age_to_date(data['age'], data['expense_start_age'][i]),
                end_date=age_to_date(data['age'], data['expense_end_age'][i]),
            )
            for i in range(len(data['expense_name']))
        ]

        cash_flows = incomes + expenses

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

        
