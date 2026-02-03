from sqlalchemy import Column, Integer, Float, DateTime, func, JSON
from sqlalchemy.orm import relationship
from ..base import Base
from sqlalchemy.sql.schema import ForeignKey

class AdviserConfig(Base):
    __tablename__ = "adviser_configs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    user = relationship("User", back_populates="adviser_config")
    risk_allocation_map = Column(JSON, nullable=False)  # dict[int, float]
    inflation = Column(Float, nullable=False)
    asset_costs = Column(JSON, nullable=False)  # dict[str, float]
    expected_returns = Column(JSON, nullable=False)  # dict[str, float]
    number_of_simulations = Column(Integer, nullable=False)
    allocation_step = Column(Float, nullable=False, default=0.10)  # Step size for allocations (0.0 to 1.0)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

