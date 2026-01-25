from schemas.base_schemas import FinancialPlan, CashFlow, AdviserConfig
from pydantic import BaseModel
from typing import List, Optional

class SimulationRequest(BaseModel):
    financial_plan_id: int
    # Optional: can override cashflows and adviser_config if needed
    cash_flows: Optional[List[CashFlow]] = None
    adviser_config: Optional[AdviserConfig] = None
