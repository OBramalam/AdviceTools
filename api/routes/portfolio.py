import os
import sys
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from infra.database.models.portfolio import Portfolio as DBPortfolio
from infra.database.models.financial_plan import FinancialPlan as DBFinancialPlan
from infra.database.models.user import User
from schemas.base_schemas import PortfolioConfig
from api.dependencies import get_db, get_current_active_user
from common.utils import pydantic_to_sqlalchemy_portfolio, sqlalchemy_to_pydantic_portfolio, validate_tax_config

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


@router.get("/plan/{plan_id}", response_model=List[PortfolioConfig])
async def list_portfolios(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all portfolios for a financial plan."""
    verify_plan_ownership(plan_id, current_user.id, db)
    
    portfolios = db.query(DBPortfolio).filter(DBPortfolio.plan_id == plan_id).all()
    return [sqlalchemy_to_pydantic_portfolio(p, PortfolioConfig) for p in portfolios]


@router.get("/{portfolio_id}", response_model=PortfolioConfig)
async def get_portfolio(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific portfolio by ID."""
    portfolio = db.query(DBPortfolio).filter(DBPortfolio.id == portfolio_id).first()
    
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    verify_plan_ownership(portfolio.plan_id, current_user.id, db)
    
    return sqlalchemy_to_pydantic_portfolio(portfolio, PortfolioConfig)


@router.post("/plan/{plan_id}", response_model=PortfolioConfig, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    plan_id: int,
    portfolio: PortfolioConfig,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new portfolio for a financial plan."""
    verify_plan_ownership(plan_id, current_user.id, db)
    
    # Validate tax config if provided
    if portfolio.tax_jurisdiction or portfolio.tax_config:
        try:
            validate_tax_config(portfolio.tax_jurisdiction, portfolio.tax_config)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tax configuration: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tax configuration validation error: {str(e)}"
            )
    
    portfolio_data = portfolio.model_dump(exclude={'id'})
    portfolio_data['plan_id'] = plan_id
    
    # Create a new PortfolioConfig with plan_id
    portfolio_with_plan = PortfolioConfig(**portfolio_data)
    db_portfolio = pydantic_to_sqlalchemy_portfolio(portfolio_with_plan, DBPortfolio)
    
    db.add(db_portfolio)
    db.commit()
    db.refresh(db_portfolio)
    
    return sqlalchemy_to_pydantic_portfolio(db_portfolio, PortfolioConfig)


@router.put("/{portfolio_id}", response_model=PortfolioConfig)
async def update_portfolio(
    portfolio_id: int,
    portfolio: PortfolioConfig,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update an existing portfolio."""
    db_portfolio = db.query(DBPortfolio).filter(DBPortfolio.id == portfolio_id).first()
    
    if not db_portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    verify_plan_ownership(db_portfolio.plan_id, current_user.id, db)
    
    portfolio_data = portfolio.model_dump(exclude={'id', 'plan_id'})
    
    # Update fields
    db_portfolio.name = portfolio_data.get('name')
    
    # Convert nested Pydantic models to JSON
    if 'weights' in portfolio_data and portfolio_data['weights']:
        db_portfolio.weights = [w.model_dump() if hasattr(w, 'model_dump') else w for w in portfolio_data['weights']]
    if 'expected_returns' in portfolio_data and portfolio_data['expected_returns']:
        if hasattr(portfolio_data['expected_returns'], 'model_dump'):
            db_portfolio.expected_returns = portfolio_data['expected_returns'].model_dump()
        else:
            db_portfolio.expected_returns = portfolio_data['expected_returns']
    if 'asset_costs' in portfolio_data and portfolio_data['asset_costs']:
        if hasattr(portfolio_data['asset_costs'], 'model_dump'):
            db_portfolio.asset_costs = portfolio_data['asset_costs'].model_dump()
        else:
            db_portfolio.asset_costs = portfolio_data['asset_costs']
    
    db_portfolio.initial_portfolio_value = portfolio_data['initial_portfolio_value']
    db_portfolio.cashflow_allocation = portfolio_data['cashflow_allocation']
    
    # Update tax fields with validation
    if 'tax_jurisdiction' in portfolio_data or 'tax_config' in portfolio_data:
        tax_jurisdiction = portfolio_data.get('tax_jurisdiction')
        tax_config = portfolio_data.get('tax_config')
        
        # Validate tax config if provided (will raise ValidationError if invalid)
        try:
            validate_tax_config(tax_jurisdiction, tax_config)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tax configuration: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tax configuration validation error: {str(e)}"
            )
        
        # Update fields (validation passed)
        if 'tax_jurisdiction' in portfolio_data:
            db_portfolio.tax_jurisdiction = tax_jurisdiction
        if 'tax_config' in portfolio_data:
            db_portfolio.tax_config = tax_config
    
    db.commit()
    db.refresh(db_portfolio)
    
    return sqlalchemy_to_pydantic_portfolio(db_portfolio, PortfolioConfig)


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a portfolio."""
    db_portfolio = db.query(DBPortfolio).filter(DBPortfolio.id == portfolio_id).first()
    
    if not db_portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    verify_plan_ownership(db_portfolio.plan_id, current_user.id, db)
    
    db.delete(db_portfolio)
    db.commit()
    
    return None

