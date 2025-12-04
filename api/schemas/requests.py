from schemas.base_schemas import Profile, RecurringCashFlow, AdviserConfig
from pydantic import BaseModel
from typing import List

class SimulationRequest(BaseModel):
    profile: Profile
    cash_flows: List[RecurringCashFlow]
    adviser_config: AdviserConfig
