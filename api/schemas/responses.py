from schemas.base_schemas import Profile, RecurringCashFlow, AdviserConfig
from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class SimulationResponse(BaseModel):
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    traceback: Optional[str] = None


class UploadResponse(BaseModel):
    success: bool
    profile: Optional[Profile] = None
    cash_flows: Optional[List[RecurringCashFlow]] = None
    adviser_config: Optional[AdviserConfig] = None
    error: Optional[str] = None

