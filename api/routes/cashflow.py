import os
import sys
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from infra.database.models.cashflow import CashFlow as DBCashFlow
from infra.database.models.financial_plan import FinancialPlan as DBFinancialPlan
from infra.database.models.user import User
from schemas.base_schemas import CashFlow
from api.dependencies import get_db, get_current_active_user
from common.utils import pydantic_to_sqlalchemy_cashflow, sqlalchemy_to_pydantic_cashflow

router = APIRouter()


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


@router.get("/plan/{plan_id}", response_model=List[CashFlow])
async def list_cashflows(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all cash flows for a specific financial plan."""
    verify_plan_ownership(plan_id, current_user.id, db)
    
    cashflows = db.query(DBCashFlow).filter(DBCashFlow.plan_id == plan_id).all()
    return [sqlalchemy_to_pydantic_cashflow(cf, CashFlow) for cf in cashflows]


@router.get("/{cashflow_id}", response_model=CashFlow)
async def get_cashflow(
    cashflow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific cash flow by ID."""
    cashflow = db.query(DBCashFlow).filter(DBCashFlow.id == cashflow_id).first()
    
    if not cashflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cash flow not found"
        )
    
    verify_plan_ownership(cashflow.plan_id, current_user.id, db)
    
    return sqlalchemy_to_pydantic_cashflow(cashflow, CashFlow)


@router.post("/plan/{plan_id}", response_model=CashFlow, status_code=status.HTTP_201_CREATED)
async def create_cashflow(
    plan_id: int,
    cashflow: CashFlow,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new cash flow for a financial plan."""
    verify_plan_ownership(plan_id, current_user.id, db)
    
    cashflow_data = cashflow.model_dump()
    cashflow_data['plan_id'] = plan_id
    
    cashflow_obj = CashFlow(**cashflow_data)
    db_cashflow = pydantic_to_sqlalchemy_cashflow(cashflow_obj, DBCashFlow)
    
    db.add(db_cashflow)
    db.commit()
    db.refresh(db_cashflow)
    
    return sqlalchemy_to_pydantic_cashflow(db_cashflow, CashFlow)


@router.put("/{cashflow_id}", response_model=CashFlow)
async def update_cashflow(
    cashflow_id: int,
    cashflow: CashFlow,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update an existing cash flow."""
    db_cashflow = db.query(DBCashFlow).filter(DBCashFlow.id == cashflow_id).first()
    
    if not db_cashflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cash flow not found"
        )
    
    verify_plan_ownership(db_cashflow.plan_id, current_user.id, db)
    
    cashflow_data = cashflow.model_dump(exclude={'id', 'plan_id'})
    
    for key, value in cashflow_data.items():
        setattr(db_cashflow, key, value)
    
    db.commit()
    db.refresh(db_cashflow)
    
    return sqlalchemy_to_pydantic_cashflow(db_cashflow, CashFlow)


@router.delete("/{cashflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cashflow(
    cashflow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a cash flow."""
    db_cashflow = db.query(DBCashFlow).filter(DBCashFlow.id == cashflow_id).first()
    
    if not db_cashflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cash flow not found"
        )
    
    verify_plan_ownership(db_cashflow.plan_id, current_user.id, db)
    
    db.delete(db_cashflow)
    db.commit()
    
    return None

