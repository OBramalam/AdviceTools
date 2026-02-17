from sqlalchemy import Column, Integer, String, Float, DateTime, func, JSON
from sqlalchemy.orm import relationship
from ..base import Base
from sqlalchemy.sql.schema import ForeignKey

class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True)
    plan_id = Column(Integer, ForeignKey("financial_plans.id"), nullable=False)
    financial_plan = relationship("FinancialPlan", back_populates="portfolios")
    name = Column(String, nullable=True)
    weights = Column(JSON, nullable=False)  # List of SimulationPortfolioWeights as JSON
    expected_returns = Column(JSON, nullable=False)  # ExpectedReturns as JSON
    asset_costs = Column(JSON, nullable=False)  # AssetCosts as JSON
    initial_portfolio_value = Column(Float, nullable=False)  # Nominal dollar value of initial wealth
    cashflow_allocation = Column(Float, nullable=False)  # Fraction of cashflows (0.0 to 1.0)
    tax_jurisdiction = Column(String(50), nullable=True)  # Tax jurisdiction (e.g., "nz", "au") or None for no tax
    tax_config = Column(JSON, nullable=True)  # Jurisdiction-specific tax parameters as JSON
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

