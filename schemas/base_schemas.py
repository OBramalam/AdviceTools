from datetime import date, datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from common.enums import CashFlowType, CashFlowPeriodicity
from simulation_engine.common.types import SimulationPortfolioWeights, ExpectedReturns, AssetCosts


class Profile(BaseModel):
    id: int = Field(description="Unique id")
    name: str = Field(description="Name of the client")
    age: float = Field(description="Age of the client")
    retirement_age: float = Field(description="Age the client would like to retire")
    plan_end_age: int = Field(description="Age the client would like to plan to")
    current_portfolio_value: float = Field(description="The current value of the clients retirement/private wealth investments")


class BaseCashFlow(BaseModel):
    profile: int = Field()
    name: str = Field()
    amount: float = Field()


class SingleCashFlow(BaseCashFlow):
    flow_date: date = Field()


class RecurringCashFlow(BaseCashFlow):
    start_date: date = Field()
    end_date: date = Field()


class AdviserConfig(BaseModel):
    risk_allocation_map: dict[int, float] = Field(default={1: 0.3, 2: 0.5, 3: 0.6, 4: 0.8, 5: 0.9})
    inflation: float = Field(default=0.02)
    asset_costs: dict[str, float] = Field(default={"stocks": 0.001, "bonds": 0.001, "cash": 0.001})
    expected_returns: dict[str, float] = Field(default={"stocks": 0.08, "bonds": 0.04, "cash": 0.02})
    number_of_simulations: int = Field(default=5000)
    allocation_step: float = Field(default=0.10, ge=0.01, le=1.0, description="Step size for allocation inputs (e.g., 0.10 = 10% increments)")
    tax_jurisdiction: Optional[str] = Field(None, description="Default tax jurisdiction (e.g., 'nz', 'au') for new portfolios. Note: portfolios still require tax_config to actually apply tax.")


class FinancialPlan(BaseModel):
    id: Optional[int] = Field(None, description="Unique id (auto-generated)")
    user_id: Optional[int] = Field(None, description="User who owns this financial plan (required on create, optional on update)")
    name: str = Field(description="Name of the financial plan")
    description: str = Field(description="Description of the financial plan")
    start_age: int = Field(description="Age of the client")
    retirement_age: int = Field(description="Age the client would like to retire")
    plan_end_age: int = Field(description="Age the client would like to plan to")
    plan_start_date: datetime = Field(description="The date the client started planning")
    portfolio_target_value: float = Field(description="The target value of the clients retirement/private wealth investments")


class PortfolioConfig(BaseModel):
    id: Optional[int] = Field(None, description="Unique database id (auto-generated)")
    plan_id: Optional[int] = Field(None, description="Financial plan this portfolio belongs to (required on create, optional on update)")
    name: Optional[str] = Field(None, description="Name of the portfolio")
    weights: List[SimulationPortfolioWeights] = Field(description="Weights of the portfolio")
    expected_returns: ExpectedReturns = Field(description="Expected returns of the portfolio")
    asset_costs: AssetCosts = Field(description="Asset costs of the portfolio")
    initial_portfolio_value: float = Field(ge=0.0, description="Nominal dollar value of initial wealth allocated to this portfolio")
    cashflow_allocation: float = Field(ge=0.0, le=1.0, description="Fraction of total cashflows allocated to this portfolio (must sum to 1.0 across all portfolios)")
    tax_jurisdiction: Optional[str] = Field(None, description="Tax jurisdiction (e.g., 'nz', 'au') or None for no tax")
    tax_config: Optional[Dict[str, Any]] = Field(None, description="Jurisdiction-specific tax parameters as JSON")


class CashFlow(BaseModel):
    id: Optional[int] = Field(None, description="Unique id (auto-generated)")
    plan_id: Optional[int] = Field(None, description="Financial plan this cash flow belongs to (required on create, optional on update)")
    portfolio_id: Optional[int] = Field(
        None,
        description="Portfolio this cash flow belongs to (NULL = plan-level/main cashflow)",
    )
    name: str = Field(description="Name of the cash flow")
    description: str = Field(description="Description of the cash flow")
    amount: float = Field(
        description=(
            "Cash flow amount. Interpreted as a nominal amount when basis='fixed', "
            "or as a percentage (e.g. 10 = 10%) when basis is percentage-based."
        )
    )
    periodicity: CashFlowPeriodicity = Field(default=CashFlowPeriodicity.MONTHLY, description="Time unit: 'monthly', 'quarterly', 'annually', or 'one_off'")
    frequency: int = Field(default=1, ge=1, description="Number of periods to skip between occurrences (ignored for one_off)")
    start_date: Optional[datetime] = Field(None, description="Start date (required for recurring, optional for one_off)")
    end_date: Optional[datetime] = Field(None, description="End date (required for recurring, optional for one_off)")
    basis: str = Field(
        default="fixed",
        description=(
            "How to interpret amount: 'fixed' = nominal amount; "
            "'pct_total_income' = percentage of total income; "
            "'pct_specific_income' = percentage of a specific income source; "
            "'pct_savings' = percentage of net savings."
        ),
    )
    reference_cashflow_id: Optional[int] = Field(
        None,
        description=(
            "Optional id of another cashflow this one is based on "
            "(e.g. for pct_specific_income rules)."
        ),
    )
    include_in_main_savings: bool = Field(
        default=True,
        description=(
            "Whether this cashflow should be included when computing main plan-level "
            "net savings (income - expenses). Portfolio-specific contributions like "
            "employer/government super contributions would typically set this to False."
        ),
    )
