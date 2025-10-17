import pydantic
from pydantic import Field
from typing import List, Optional
from functools import cached_property
import numpy as np


class ExpectedReturns(pydantic.BaseModel):
    cash: float = pydantic.Field(default=None, ge=0.0, le=1.0)
    stocks: float = pydantic.Field(default=None, ge=0.0, le=1.0)
    bonds: float = pydantic.Field(default=None, ge=0.0, le=1.0)

    @pydantic.model_validator(mode="after")
    def check_returns(self) -> dict[str, float]:
        """Check that returns are non-negative."""
        all_returns = [self.cash, self.stocks, self.bonds]
        all_returns = [ret for ret in all_returns if ret is not None]
        if not all(ret >= 0 for ret in all_returns):
            raise ValueError("Returns must be non-negative.")
        if not all(ret <= 1 for ret in all_returns):
            raise ValueError("Returns must be less than or equal to 1.")
        return self
    

class AssetCosts(pydantic.BaseModel):
    cash: float = 0.0
    stocks: float = 0.0
    bonds: float = 0.0

    @pydantic.model_validator(mode="after")
    def check_fees(self) -> dict[str, float]:
        """Check that fees are non-negative."""
        all_fees = [self.cash, self.stocks, self.bonds]
        if not all(fee >= 0 for fee in all_fees):
            raise ValueError("Fees must be non-negative.")
        if not all(fee <= 1 for fee in all_fees):
            raise ValueError("Fees must be less than or equal to 1.")
        return self


class SimulationPortfolioWeights(pydantic.BaseModel):
    """Model for asset weights."""
    step: float
    stocks: float = 0.0
    bonds: float = 0.0

    @pydantic.model_validator(mode="after")
    def check_weights(self) -> dict[str, float]:
        """Check that weights sum to 1."""
        all_weights = [self.stocks, self.bonds, self.cash]
        total_weight = sum(all_weights)
        if not abs(total_weight - 1) < 1e-6:
            raise ValueError(f"Asset weights must sum to 1. Current sum: {total_weight}")
        if not all(weight >= 0 for weight in all_weights):
            raise ValueError("Asset weights must be non-negative.")
        return self
    
    @cached_property
    def cash(self) -> float:
        """Calculate cash weight."""
        return 1 - self.stocks - self.bonds
    
    def model_dump(self, *args, **kwargs) -> dict[str, float]:
        """Override model_dump to include cash."""
        data = super().model_dump(*args, **kwargs)
        data["cash"] = self.cash
        return data


class CashFlow(pydantic.BaseModel):
    step: float
    value: float

    @pydantic.model_validator(mode="after")
    def check_step(self) -> dict[str, float]:
        """Check that step is non-negative."""
        if self.step < 0:
            raise ValueError("Cash flow step must be positive.")
        return self
    
    @staticmethod
    def interpolate_to_regular_rate(
        defined_points: list["CashFlow"],
        step: int = 1) -> list["CashFlow"]:
        """
        Interpolate to regular points.
        """
        regular_steps = np.arange(0, defined_points[-1].step + step, step)
        interpolated_points = []
        prev_x = 0
        prev_y = 0
        next_x = defined_points[0].step
        next_y = defined_points[0].value
        for x in regular_steps:
            if x >= defined_points[-1].step:
                interpolated_points.append((defined_points[-1].step, defined_points[-1].value))
                break
            if next_x <= x:
                interpolated_points.append((next_x, next_y))
                prev_x = next_x
                prev_y = next_y
                for i in range(len(defined_points)):
                    if defined_points[i].step > x:
                        next_x = defined_points[i].step
                        next_y = defined_points[i].value
                        break
                else:
                    next_x = defined_points[-1].step
                    next_y = defined_points[-1].value
            if x == next_x:
                interpolated_points.append((x, next_y))
            else:
                y = prev_y + (next_y - prev_y) * (x - prev_x) / (next_x - prev_x)
                interpolated_points.append((x, y))
        return [CashFlow(step=step, value=value) for step, value in interpolated_points]
