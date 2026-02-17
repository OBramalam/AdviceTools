import datetime
import calendar
from dateutil.relativedelta import relativedelta
import re
from typing import Union, TYPE_CHECKING, Optional, Dict, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def age_to_date(current_age, target_age):
    today = datetime.date.today()
    today = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    
    year_increment = target_age - current_age
    
    return today + relativedelta(years=year_increment)


def to_annual(amount: float) -> float:
    return amount * 12  # Convert monthly to annual - update when we add more simulation step types.


def year_to_simulation_step(date, start_year) -> int:
    return date.year - start_year


def camel_to_snake(name: str) -> str:
    return "".join(["_" + char.lower() if char.isupper() else char for char in name]).lstrip("_")


def snake_to_camel(name: str) -> str:
    return "".join([char.capitalize() for char in name.split("_")])


def convert_key_to_snake(s: str) -> str:
    if " " in s:
        words = s.split(" ")
        for word in words:
            word.title()
    else:
        words = re.findall(r'[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+', s)
    words = [word.title() for word in words]
    s = "".join(words)
    return camel_to_snake(s)


def convert_json_to_snake(obj: Union[object, dict, list]) -> Union[object, dict, list]:
    if isinstance(obj, dict):
        return {convert_key_to_snake(k): convert_json_to_snake(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_json_to_snake(v) for v in obj]
    else:
        return obj


def convert_key_to_camel(s: str) -> str:
    return snake_to_camel(s)


def convert_json_to_camel(obj: Union[object, dict, list]) -> Union[object, dict, list]:
    if isinstance(obj, dict):
        return {convert_key_to_camel(k): convert_json_to_camel(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_json_to_camel(v) for v in obj]
    else:
        return obj


def pydantic_to_sqlalchemy_financial_plan(pydantic_plan, sqlalchemy_plan_class, exclude_fields: set = None):
    if exclude_fields is None:
        exclude_fields = {'id', 'created_at', 'updated_at'}
    
    data = pydantic_plan.model_dump(exclude=exclude_fields)
    
    sqlalchemy_fields = {'user_id', 'name', 'description', 'start_age', 'retirement_age', 
                         'plan_end_age', 'plan_start_date', 'portfolio_target_value'}
    data = {k: v for k, v in data.items() if k in sqlalchemy_fields}
    
    return sqlalchemy_plan_class(**data)


def pydantic_to_sqlalchemy_cashflow(pydantic_cashflow, sqlalchemy_cashflow_class, exclude_fields: set = None):
    if exclude_fields is None:
        exclude_fields = {'id', 'created_at', 'updated_at'}
    
    data = pydantic_cashflow.model_dump(exclude=exclude_fields)
    
    sqlalchemy_fields = {
        'plan_id', 'name', 'description', 'amount', 'periodicity', 'frequency', 
        'start_date', 'end_date', 'portfolio_id', 'basis', 'reference_cashflow_id', 
        'include_in_main_savings'
    }
    data = {k: v for k, v in data.items() if k in sqlalchemy_fields}
    
    return sqlalchemy_cashflow_class(**data)


def sqlalchemy_to_pydantic_financial_plan(sqlalchemy_plan, pydantic_plan_class):
    return pydantic_plan_class.model_validate(sqlalchemy_plan, from_attributes=True)


def sqlalchemy_to_pydantic_cashflow(sqlalchemy_cashflow, pydantic_cashflow_class):
    return pydantic_cashflow_class.model_validate(sqlalchemy_cashflow, from_attributes=True)


def pydantic_to_sqlalchemy_portfolio(pydantic_portfolio, sqlalchemy_portfolio_class, exclude_fields: set = None):
    if exclude_fields is None:
        exclude_fields = {'id', 'created_at', 'updated_at'}
    
    data = pydantic_portfolio.model_dump(exclude=exclude_fields)
    
    # Convert nested Pydantic models to JSON
    if 'weights' in data and data['weights']:
        data['weights'] = [w.model_dump() if hasattr(w, 'model_dump') else w for w in data['weights']]
    if 'expected_returns' in data and data['expected_returns']:
        if hasattr(data['expected_returns'], 'model_dump'):
            data['expected_returns'] = data['expected_returns'].model_dump()
    if 'asset_costs' in data and data['asset_costs']:
        if hasattr(data['asset_costs'], 'model_dump'):
            data['asset_costs'] = data['asset_costs'].model_dump()
    
    sqlalchemy_fields = {'plan_id', 'name', 'weights', 'expected_returns', 
                         'asset_costs', 'initial_portfolio_value', 'cashflow_allocation',
                         'tax_jurisdiction', 'tax_config'}
    data = {k: v for k, v in data.items() if k in sqlalchemy_fields}
    
    return sqlalchemy_portfolio_class(**data)


def sqlalchemy_to_pydantic_portfolio(sqlalchemy_portfolio, pydantic_portfolio_class):
    """Convert SQLAlchemy Portfolio to Pydantic PortfolioConfig."""
    from schemas.base_schemas import PortfolioConfig
    from simulation_engine.common.types import SimulationPortfolioWeights, ExpectedReturns, AssetCosts
    
    # Convert JSON fields back to Pydantic models
    weights = [SimulationPortfolioWeights.model_validate(w) for w in sqlalchemy_portfolio.weights]
    expected_returns = ExpectedReturns.model_validate(sqlalchemy_portfolio.expected_returns)
    asset_costs = AssetCosts.model_validate(sqlalchemy_portfolio.asset_costs)
    
    return PortfolioConfig(
        id=sqlalchemy_portfolio.id,
        plan_id=sqlalchemy_portfolio.plan_id,
        name=sqlalchemy_portfolio.name,
        weights=weights,
        expected_returns=expected_returns,
        asset_costs=asset_costs,
        initial_portfolio_value=sqlalchemy_portfolio.initial_portfolio_value,
        cashflow_allocation=sqlalchemy_portfolio.cashflow_allocation,
        tax_jurisdiction=getattr(sqlalchemy_portfolio, 'tax_jurisdiction', None),
        tax_config=getattr(sqlalchemy_portfolio, 'tax_config', None)
    )


def pydantic_to_sqlalchemy_adviser_config(pydantic_config, sqlalchemy_config_class, exclude_fields: set = None):
    if exclude_fields is None:
        exclude_fields = {'id', 'created_at', 'updated_at'}
    
    data = pydantic_config.model_dump(exclude=exclude_fields)
    
    sqlalchemy_fields = {'user_id', 'risk_allocation_map', 'inflation', 'asset_costs', 
                         'expected_returns', 'number_of_simulations', 'allocation_step', 'tax_jurisdiction'}
    data = {k: v for k, v in data.items() if k in sqlalchemy_fields}
    
    return sqlalchemy_config_class(**data)


def sqlalchemy_to_pydantic_adviser_config(sqlalchemy_config, pydantic_config_class):
    return pydantic_config_class.model_validate(sqlalchemy_config, from_attributes=True)


def validate_tax_config(
    tax_jurisdiction: Optional[str], 
    tax_config: Optional[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Validate tax_config JSON against jurisdiction-specific Pydantic schema.
    Returns validated config dict ready for engine, or None if no tax.
    Raises ValidationError if tax_config doesn't match jurisdiction schema.
    
    Args:
        tax_jurisdiction: Tax jurisdiction string (e.g., "nz", "au") or None
        tax_config: Dictionary of tax parameters or None
        
    Returns:
        Validated tax config dict with jurisdiction key, or None if no tax
        
    Raises:
        ValueError: If jurisdiction is unknown or invalid
        ValidationError: If tax_config doesn't match jurisdiction schema
    """
    from schemas.tax_schemas import NewZealandTaxConfig
    
    # No tax if jurisdiction or config is None
    if not tax_jurisdiction or not tax_config:
        return None
    
    # Validate against jurisdiction-specific schema
    if tax_jurisdiction == "nz":
        # Validate and parse NZ tax config
        nz_config = NewZealandTaxConfig(**tax_config)
        # Return clean dict for engine (includes jurisdiction for factory)
        return {
            "jurisdiction": "nz",
            "pir_rate": nz_config.pir_rate,
            "marginal_tax_rate": nz_config.marginal_tax_rate,
            "percent_pie_fund": nz_config.percent_pie_fund,
            "percent_fif_fund": nz_config.percent_fif_fund,
        }
    else:
        raise ValueError(f"Unknown tax jurisdiction: {tax_jurisdiction}")


def get_adviser_config_by_user_id(user_id: int, db: "Session", use_defaults_if_not_found: bool = True):
    """
    Get adviser config for a user from the database.
    
    Args:
        user_id: The user ID to fetch the config for
        db: SQLAlchemy database session
        use_defaults_if_not_found: If True, return default AdviserConfig if not found. If False, return None.
    
    Returns:
        AdviserConfig: The user's adviser config, or default config if not found and use_defaults_if_not_found=True,
                      or None if not found and use_defaults_if_not_found=False
    """
    from infra.database.models.adviser_config import AdviserConfig as DBAdviserConfig
    from schemas.base_schemas import AdviserConfig
    
    db_config = db.query(DBAdviserConfig).filter(DBAdviserConfig.user_id == user_id).first()
    
    if db_config:
        return sqlalchemy_to_pydantic_adviser_config(db_config, AdviserConfig)
    elif use_defaults_if_not_found:
        return AdviserConfig()  # Return default config
    else:
        return None

