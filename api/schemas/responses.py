from schemas.base_schemas import FinancialPlan, CashFlow, AdviserConfig
from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class SimulationResponse(BaseModel):
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    traceback: Optional[str] = None


class UploadResponse(BaseModel):
    success: bool
    financial_plan: Optional[FinancialPlan] = None
    cash_flows: Optional[List[CashFlow]] = None
    adviser_config: Optional[AdviserConfig] = None
    error: Optional[str] = None

