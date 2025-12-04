import os
import sys
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from infra.database.models.financial_plan import FinancialPlan as DBFinancialPlan
from infra.database.models.user import User
from schemas.base_schemas import FinancialPlan
from api.dependencies import get_db, get_current_active_user
from common.utils import pydantic_to_sqlalchemy_financial_plan, sqlalchemy_to_pydantic_financial_plan

router = APIRouter()


@router.get("", response_model=List[FinancialPlan])
async def list_financial_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all financial plans for the current user."""
    plans = db.query(DBFinancialPlan).filter(DBFinancialPlan.user_id == current_user.id).all()
    return [sqlalchemy_to_pydantic_financial_plan(plan, FinancialPlan) for plan in plans]


@router.get("/{plan_id}", response_model=FinancialPlan)
async def get_financial_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific financial plan by ID."""
    plan = db.query(DBFinancialPlan).filter(
        DBFinancialPlan.id == plan_id,
        DBFinancialPlan.user_id == current_user.id
    ).first()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial plan not found"
        )
    
    return sqlalchemy_to_pydantic_financial_plan(plan, FinancialPlan)


@router.post("", response_model=FinancialPlan, status_code=status.HTTP_201_CREATED)
async def create_financial_plan(
    plan: FinancialPlan,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new financial plan."""
    plan_data = plan.model_dump()
    plan_data['user_id'] = current_user.id
    
    plan_obj = FinancialPlan(**plan_data)
    db_plan = pydantic_to_sqlalchemy_financial_plan(plan_obj, DBFinancialPlan)
    
    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)
    
    return sqlalchemy_to_pydantic_financial_plan(db_plan, FinancialPlan)


@router.put("/{plan_id}", response_model=FinancialPlan)
async def update_financial_plan(
    plan_id: int,
    plan: FinancialPlan,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update an existing financial plan."""
    db_plan = db.query(DBFinancialPlan).filter(
        DBFinancialPlan.id == plan_id,
        DBFinancialPlan.user_id == current_user.id
    ).first()
    
    if not db_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial plan not found"
        )
    
    plan_data = plan.model_dump(exclude={'id'})
    plan_data['user_id'] = current_user.id
    
    for key, value in plan_data.items():
        setattr(db_plan, key, value)
    
    db.commit()
    db.refresh(db_plan)
    
    return sqlalchemy_to_pydantic_financial_plan(db_plan, FinancialPlan)


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_financial_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a financial plan."""
    db_plan = db.query(DBFinancialPlan).filter(
        DBFinancialPlan.id == plan_id,
        DBFinancialPlan.user_id == current_user.id
    ).first()
    
    if not db_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial plan not found"
        )
    
    db.delete(db_plan)
    db.commit()
    
    return None

