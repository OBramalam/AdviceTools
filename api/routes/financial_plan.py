import os
import sys
from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from infra.database.models.financial_plan import FinancialPlan as DBFinancialPlan
from infra.database.models.cashflow import CashFlow as DBCashFlow
from infra.database.models.portfolio import Portfolio as DBPortfolio
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
    
    plan_data = plan.model_dump(exclude={'id', 'user_id'})
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


@router.post("/{plan_id}/duplicate", response_model=FinancialPlan, status_code=status.HTTP_201_CREATED)
async def duplicate_financial_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Duplicate an existing financial plan, including its portfolios and cashflows.

    - The source plan must belong to the current user.
    - The new plan will have a generated name based on the source plan's name:
      "<name> (Copy)", "<name> (Copy 2)", etc.
    - All portfolios and cashflows are cloned:
        * `plan_id` is set to the new plan's id
        * `portfolio_id` on cashflows is remapped to the new portfolios
        * `reference_cashflow_id` is remapped to the new cashflows
    """
    # Fetch and authorize source plan
    source_plan = (
        db.query(DBFinancialPlan)
        .filter(
            DBFinancialPlan.id == plan_id,
            DBFinancialPlan.user_id == current_user.id,
        )
        .first()
    )

    if not source_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial plan not found"
        )

    # Generate a unique name for the duplicated plan
    base_name = f"{source_plan.name} (Copy)"
    # Collect existing plan names for this user
    existing_name_rows = (
        db.query(DBFinancialPlan.name)
        .filter(DBFinancialPlan.user_id == current_user.id)
        .all()
    )
    existing_names = {row[0] for row in existing_name_rows}

    new_name = base_name
    counter = 2
    while new_name in existing_names:
        new_name = f"{source_plan.name} (Copy {counter})"
        counter += 1

    try:
        # Create the new financial plan
        new_plan = DBFinancialPlan(
            user_id=current_user.id,
            name=new_name,
            description=source_plan.description,
            start_age=source_plan.start_age,
            retirement_age=source_plan.retirement_age,
            plan_end_age=source_plan.plan_end_age,
            plan_start_date=source_plan.plan_start_date,
            portfolio_target_value=source_plan.portfolio_target_value,
        )
        db.add(new_plan)
        db.flush()  # Assign new_plan.id without committing yet

        # Clone portfolios first so we can remap portfolio_id on cashflows
        source_portfolios = (
            db.query(DBPortfolio)
            .filter(DBPortfolio.plan_id == source_plan.id)
            .all()
        )

        portfolio_id_map: Dict[int, int] = {}
        for p in source_portfolios:
            new_p = DBPortfolio(
                plan_id=new_plan.id,
                name=p.name,
                weights=p.weights,
                expected_returns=p.expected_returns,
                asset_costs=p.asset_costs,
                initial_portfolio_value=p.initial_portfolio_value,
                cashflow_allocation=p.cashflow_allocation,
                tax_jurisdiction=p.tax_jurisdiction,
                tax_config=p.tax_config,
            )
            db.add(new_p)
            db.flush()  # get new_p.id
            portfolio_id_map[p.id] = new_p.id

        # Clone cashflows in two passes to correctly handle reference_cashflow_id
        source_cashflows = (
            db.query(DBCashFlow)
            .filter(DBCashFlow.plan_id == source_plan.id)
            .all()
        )

        # First pass: create new cashflows without reference_cashflow_id
        cashflow_map: Dict[int, DBCashFlow] = {}
        for cf in source_cashflows:
            new_cf = DBCashFlow(
                plan_id=new_plan.id,
                portfolio_id=(
                    portfolio_id_map.get(cf.portfolio_id)
                    if cf.portfolio_id is not None
                    else None
                ),
                name=cf.name,
                description=cf.description,
                amount=cf.amount,
                periodicity=cf.periodicity,
                frequency=cf.frequency,
                start_date=cf.start_date,
                end_date=cf.end_date,
                basis=cf.basis,
                reference_cashflow_id=None,  # set in second pass
                include_in_main_savings=cf.include_in_main_savings,
            )
            db.add(new_cf)
            db.flush()
            cashflow_map[cf.id] = new_cf

        # Second pass: remap reference_cashflow_id for intra-plan references
        for cf in source_cashflows:
            if cf.reference_cashflow_id is not None:
                old_ref_id = cf.reference_cashflow_id
                if old_ref_id in cashflow_map:
                    new_cf = cashflow_map[cf.id]
                    new_ref_cf = cashflow_map[old_ref_id]
                    new_cf.reference_cashflow_id = new_ref_cf.id

        db.commit()
        db.refresh(new_plan)

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to duplicate financial plan",
        )

    return sqlalchemy_to_pydantic_financial_plan(new_plan, FinancialPlan)

