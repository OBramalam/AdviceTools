"""Simulation routes."""
import os
import sys
import traceback
from typing import Annotated

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services import SimulationService
from api.schemas.requests import SimulationRequest
from api.schemas.responses import SimulationResponse
from api.dependencies import get_db

router = APIRouter()


@router.post("/simulate", response_model=SimulationResponse)
async def run_simulation(
    request: SimulationRequest,
    db: Session = Depends(get_db)
):
    """
    Run a financial simulation.
    
    Takes profile, cash flows, and adviser config, returns simulation results.
    """
    try:
        simulator = SimulationService(
            profile=request.profile,
            cash_flows=request.cash_flows,
            adviser_config=request.adviser_config
        )
        
        result = simulator.simulate()
        
        # Convert result to JSON-serializable format
        if hasattr(result, 'model_dump'):
            result_data = result.model_dump()
        else:
            result_data = result
        
        return SimulationResponse(
            success=True,
            result=result_data
        )
        
    except Exception as e:
        return SimulationResponse(
            success=False,
            error=str(e),
            traceback=traceback.format_exc()
        )

