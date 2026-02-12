from typing import Literal, Union
from pydantic import BaseModel, Field, model_validator


class TaxConfigBase(BaseModel):
    """Base class for all tax configs - identifies jurisdiction"""
    jurisdiction: str


class NewZealandTaxConfig(TaxConfigBase):
    """Tax configuration for New Zealand accounts (PIE + FIF)."""
    jurisdiction: Literal["nz"] = "nz"
    pir_rate: float = Field(ge=0.0, le=1.0, description="Prescribed Investor Rate (PIR)")
    marginal_tax_rate: float = Field(ge=0.0, le=1.0, description="Marginal tax rate")
    percent_pie_fund: float = Field(ge=0.0, le=1.0, description="Percentage of portfolio in PIE funds (0.0 to 1.0)")
    percent_fif_fund: float = Field(ge=0.0, le=1.0, description="Percentage of portfolio in FIF funds (0.0 to 1.0)")
    
    @model_validator(mode='after')
    def validate_pie_fif_sum(self):
        """Ensure PIE + FIF percentages sum to 1.0 (within tolerance)."""
        total = self.percent_pie_fund + self.percent_fif_fund
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"PIE + FIF percentages must sum to 1.0, got {total}")
        return self


# Union type for all possible tax configs
# Add more jurisdictions here as they are implemented
TaxConfig = Union[NewZealandTaxConfig]

