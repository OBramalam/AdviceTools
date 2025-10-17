from datetime import date
import datetime
from pydantic import BaseModel, Field


class Profile(BaseModel):
    id: int = Field(description="Unique id")
    name: str = Field(description="Name of the client")
    age: float = Field(description="Age of the client")
    retirement_age: float = Field(description="Age the client would like to retire")

class BaseCashFlow(BaseModel):
    profile: int = Field()
    name: str = Field()
    amount: float = Field()

class SingleCashFlow(BaseCashFlow):
    flow_date: date = Field()

class RecurringCashFlow(BaseCashFlow):
    start_date: date = Field()
    end_date: date = Field()
