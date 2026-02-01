from sqlalchemy import Column, Integer, String, Float, DateTime, func
from sqlalchemy.orm import relationship
from ..base import Base
from sqlalchemy.sql.schema import ForeignKey

class FinancialPlan(Base):
    __tablename__ = "financial_plans"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="financial_plans")
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    start_age = Column(Integer, nullable=False)
    retirement_age = Column(Integer, nullable=False)
    plan_end_age = Column(Integer, nullable=False)
    plan_start_date = Column(DateTime, nullable=False)
    portfolio_target_value = Column(Float, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    cashflows = relationship("CashFlow", back_populates="financial_plan")
    portfolios = relationship("Portfolio", back_populates="financial_plan")