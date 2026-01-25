"""Simulation routes."""
import os
import sys
import traceback
from typing import Annotated, Any

import numpy as np
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services import SimulationService
from api.schemas.requests import SimulationRequest
from api.schemas.responses import SimulationResponse
from api.dependencies import get_db, get_current_active_user
from infra.database.models.financial_plan import FinancialPlan as DBFinancialPlan
from infra.database.models.user import User
from schemas.base_schemas import FinancialPlan
from common.utils import sqlalchemy_to_pydantic_financial_plan

router = APIRouter()


def convert_numpy_to_list(obj: Any) -> Any:
    """
    Recursively convert numpy arrays to lists for JSON serialization.
    
    This function handles nested structures including:
    - numpy arrays -> lists
    - dictionaries with numpy arrays
    - lists with numpy arrays
    - Pydantic models with numpy arrays
    """
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_to_list(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_to_list(item) for item in obj]
    elif hasattr(obj, 'model_dump'):
        # Handle Pydantic models
        return convert_numpy_to_list(obj.model_dump())
    return obj


def verify_plan_ownership(plan_id: int, user_id: int, db: Session) -> DBFinancialPlan:
    """Verify that the plan exists and belongs to the user."""
    plan = db.query(DBFinancialPlan).filter(
        DBFinancialPlan.id == plan_id,
        DBFinancialPlan.user_id == user_id
    ).first()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial plan not found"
        )
    
    return plan


@router.post("/simulate", response_model=SimulationResponse)
async def run_simulation(
    request: SimulationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Run a financial simulation.
    
    Takes financial_plan_id, fetches cashflows from database, and uses default or provided adviser_config.
    Returns simulation results.
    """
    try:
        # Verify plan ownership and get the financial plan
        db_plan = verify_plan_ownership(request.financial_plan_id, current_user.id, db)
        financial_plan = sqlalchemy_to_pydantic_financial_plan(db_plan, FinancialPlan)
        
        # Create simulation service with financial plan
        # cash_flows and adviser_config will be fetched from DB if not provided
        simulator = SimulationService(
            financial_plan=financial_plan,
            cash_flows=request.cash_flows,  # Optional override
            adviser_config=request.adviser_config,  # Optional override
            db=db
        )
        
        result = simulator.simulate()
        
        # Convert result to JSON-serializable format
        # Handle numpy arrays by converting them to lists
        if hasattr(result, 'model_dump'):
            result_data = result.model_dump()
        else:
            result_data = result
        
        # Convert any numpy arrays to lists for JSON serialization
        result_data = convert_numpy_to_list(result_data)
        
        return SimulationResponse(
            success=True,
            result=result_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return SimulationResponse(
            success=False,
            error=str(e),
            traceback=traceback.format_exc()
        )

