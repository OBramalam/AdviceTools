from datetime import date
import datetime
from pydantic import BaseModel, Field
from .base_schemas import Profile


class ExtractionSchema(BaseModel):
    name: str = Field(description="Name of the client")
    age: float = Field(description="Age of the client")
    retirement_age: float = Field(description="Age the client would like to retire")
    current_portfolio_value: float = Field(description="The current value of the clients retirement/private wealth investments")
    income_source: list[str] = Field(description="Source of income")
    income_amount: list[float] = Field(description="Amount of income per month")
    income_start_age: list[int] = Field(description="The age the user will start recieving this source of income. If it is a current source of use current age.")
    income_end_age: list[int] = Field(description="The date the user will stop recieving this source of income, format. If none provided default to retirement age.")
    expense_name: list[str] = Field(description="Expense name")
    expense_amount: list[float] = Field(description="Amount of expense per month")
    expense_start_age: list[int] = Field(description="The age the user will start paying this expense. If it is a current expense use current age.")
    expense_end_age: list[int] = Field(description="The age the user will stop paying this expense. If none provided default to 100.")
