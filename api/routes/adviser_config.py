import os
import sys
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from infra.database.models.adviser_config import AdviserConfig as DBAdviserConfig
from infra.database.models.user import User
from schemas.base_schemas import AdviserConfig
from api.dependencies import get_db, get_current_active_user
from common.utils import pydantic_to_sqlalchemy_adviser_config, sqlalchemy_to_pydantic_adviser_config

router = APIRouter()


@router.get("", response_model=AdviserConfig)
async def get_adviser_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get adviser config for the current user."""
    adviser_config = db.query(DBAdviserConfig).filter(DBAdviserConfig.user_id == current_user.id).first()
    
    if not adviser_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Adviser config not found"
        )
    
    return sqlalchemy_to_pydantic_adviser_config(adviser_config, AdviserConfig)


@router.post("", status_code=status.HTTP_405_METHOD_NOT_ALLOWED)
async def create_adviser_config(
    adviser_config: AdviserConfig,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create adviser config is not allowed. Adviser config is automatically created during user registration."""
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="Adviser config is automatically created during user registration. Use PUT to update your config."
    )


@router.put("", response_model=AdviserConfig)
async def update_adviser_config(
    adviser_config: AdviserConfig,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update adviser config for the current user."""
    db_config = db.query(DBAdviserConfig).filter(DBAdviserConfig.user_id == current_user.id).first()
    
    if not db_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Adviser config not found"
        )
    
    config_data = adviser_config.model_dump(exclude={'id'})
    
    # Update fields
    db_config.risk_allocation_map = config_data.get('risk_allocation_map')
    db_config.inflation = config_data.get('inflation')
    db_config.asset_costs = config_data.get('asset_costs')
    db_config.expected_returns = config_data.get('expected_returns')
    db_config.number_of_simulations = config_data.get('number_of_simulations')
    db_config.allocation_step = config_data.get('allocation_step', 0.10)
    db_config.tax_jurisdiction = config_data.get('tax_jurisdiction')
    
    db.commit()
    db.refresh(db_config)
    
    return sqlalchemy_to_pydantic_adviser_config(db_config, AdviserConfig)


@router.delete("", status_code=status.HTTP_405_METHOD_NOT_ALLOWED)
async def delete_adviser_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete adviser config is not allowed. Adviser config cannot be deleted."""
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="Adviser config cannot be deleted. Use PUT to update your config."
    )

