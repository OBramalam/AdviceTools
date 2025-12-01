from sqlalchemy import Column, Integer, String, Float, DateTime, Enum
from sqlalchemy.orm import relationship
from ..base import Base
from sqlalchemy.sql.schema import ForeignKey
from common.enums import CashFlowType

class CashFlow(Base):
    __tablename__ = "cashflows"

    id = Column(Integer, primary_key=True)
    plan_id = Column(Integer, ForeignKey("financial_plans.id"), nullable=False)
    financial_plan = relationship("FinancialPlan", back_populates="cashflows")
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    start_date = Column(DateTime, nullable = True)
    end_date = Column(DateTime, nullable = True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)