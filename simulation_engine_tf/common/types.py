import pydantic
from functools import cached_property


class ExpectedReturns(pydantic.BaseModel):
    cash: float | None = pydantic.Field(default=None, ge=0.0, le=1.0)
    stocks: float | None = pydantic.Field(default=None, ge=0.0, le=1.0)
    bonds: float | None = pydantic.Field(default=None, ge=0.0, le=1.0)

    @pydantic.model_validator(mode="after")
    def check_returns(self):
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
    def check_fees(self):
        all_fees = [self.cash, self.stocks, self.bonds]
        if not all(fee >= 0 for fee in all_fees):
            raise ValueError("Fees must be non-negative.")
        if not all(fee <= 1 for fee in all_fees):
            raise ValueError("Fees must be less than or equal to 1.")
        return self


class SimulationPortfolioWeights(pydantic.BaseModel):
    step: float
    stocks: float = 0.0
    bonds: float = 0.0

    @pydantic.model_validator(mode="after")
    def check_weights(self):
        all_weights = [self.stocks, self.bonds, self.cash]
        total_weight = sum(all_weights)
        if not abs(total_weight - 1) < 1e-6:
            raise ValueError(f"Asset weights must sum to 1. Current sum: {total_weight}")
        if not all(weight >= 0 for weight in all_weights):
            raise ValueError("Asset weights must be non-negative.")
        return self

    @cached_property
    def cash(self) -> float:
        return 1 - self.stocks - self.bonds

    def model_dump(self, *args, **kwargs):
        data = super().model_dump(*args, **kwargs)
        data["cash"] = self.cash
        return data


class CashFlow(pydantic.BaseModel):
    step: float
    value: float

    @pydantic.model_validator(mode="after")
    def check_step(self):
        if self.step < 0:
            raise ValueError("Cash flow step must be positive.")
        return self

