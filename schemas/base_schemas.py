from datetime import date
import datetime
from pydantic import BaseModel, Field


class Profile(BaseModel):
    id: int = Field(description="Unique id")
    name: str = Field(description="Name of the client")
    age: float = Field(description="Age of the client")
    retirement_age: float = Field(description="Age the client would like to retire")
    plan_end_age: int = Field(description="Age the client would like to plan to")
    current_portfolio_value: float = Field(description="The current value of the clients retirement/private wealth investments")


class BaseCashFlow(BaseModel):
    profile: int = Field()
    name: str = Field()
    amount: float = Field()

class SingleCashFlow(BaseCashFlow):
    flow_date: date = Field()

class RecurringCashFlow(BaseCashFlow):
    start_date: date = Field()
    end_date: date = Field()

class AdviserConfig(BaseModel):
    risk_allocation_map: dict[int, float] = Field(default={1: 0.3, 2: 0.5, 3: 0.6, 4: 0.8, 5: 0.9})
    inflation: float = Field(default=0.02)
    asset_costs: dict[str, float] = Field(default={"stocks": 0.001, "bonds": 0.001, "cash": 0.001})
    expected_returns: dict[str, float] = Field(default={"stocks": 0.08, "bonds": 0.04, "cash": 0.02})
    number_of_simulations: int = Field(default=5000)