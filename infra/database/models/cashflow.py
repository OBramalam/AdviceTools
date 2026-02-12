from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, Boolean, func
from sqlalchemy.orm import relationship
from ..base import Base
from sqlalchemy.sql.schema import ForeignKey
from common.enums import CashFlowType, CashFlowPeriodicity

class CashFlow(Base):
    __tablename__ = "cashflows"

    id = Column(Integer, primary_key=True)
    plan_id = Column(Integer, ForeignKey("financial_plans.id"), nullable=False)
    # Optional link to a specific portfolio for portfolio-level cashflows.
    # When NULL, the cashflow is plan-level (shared across portfolios).
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=True)
    financial_plan = relationship("FinancialPlan", back_populates="cashflows")
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    periodicity = Column(String(20), nullable=False, default=CashFlowPeriodicity.MONTHLY.value)
    frequency = Column(Integer, nullable=False, default=1)
    start_date = Column(DateTime, nullable = True)
    end_date = Column(DateTime, nullable = True)
    # How to interpret the amount. When "fixed", amount is a nominal cash amount.
    # When percentage-based (e.g. "pct_total_income"), amount is a percentage (e.g. 10 = 10%).
    basis = Column(String(30), nullable=False, default="fixed")
    # Optional reference to another cashflow (e.g. for percentage-of-specific-income rules).
    reference_cashflow_id = Column(Integer, ForeignKey("cashflows.id"), nullable=True)
    # Whether this cashflow should be included when computing main plan-level net savings
    # (income - expenses). Portfolio-specific employer/government contributions would
    # typically set this to False so they don't change the shared savings pool.
    include_in_main_savings = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)