from typing import Union
import numpy as np
from .base import AccountType
from ..tax_calcs.new_zealand import calculate_PIE_tax, calculate_FIF_tax


class NewZealandBaseAccount(AccountType):
    def __init__(
        self, 
        pir_rate: float, 
        marginal_tax_rate: float,
        percent_pie_fund: float,
        percent_fif_fund: float,
    ):
        """
        Initialize a New Zealand tax account model.
        
        Args:
            pir_rate: Prescribed Investor Rate (PIR)
            marginal_tax_rate: Marginal tax rate
            percent_pie_fund: Percentage of portfolio in PIE funds (0.0 to 1.0)
            percent_fif_fund: Percentage of portfolio in FIF funds (0.0 to 1.0)
        """
        self.pir_rate = pir_rate
        self.marginal_tax_rate = marginal_tax_rate
        self.percent_pie_fund = percent_pie_fund
        self.percent_fif_fund = percent_fif_fund

    def calculate_tax(
        self, 
        return_on_investment: Union[float, np.ndarray]
    ) -> Union[float, np.ndarray]:
        """
        Calculate tax on investment returns for NZ account.
        
        Args:
            return_on_investment: Investment return amount(s) - can be scalar or numpy array
                representing returns for one or multiple simulation paths
        
        Returns:
            Total tax amount(s) - same shape as return_on_investment
        """
        # Check if input is scalar before converting to array
        is_scalar = isinstance(return_on_investment, (int, float))
        return_on_investment = np.asarray(return_on_investment)
        
        # Split returns into PIE and FIF portions
        pie_return = self.percent_pie_fund * return_on_investment
        fif_return = self.percent_fif_fund * return_on_investment

        # Calculate tax for each portion
        pie_tax = calculate_PIE_tax(self.pir_rate, self.marginal_tax_rate, pie_return)
        fif_tax = calculate_FIF_tax(self.marginal_tax_rate, fif_return)

        # Total tax is sum of PIE and FIF tax
        total_tax = pie_tax + fif_tax
        
        # Return scalar if input was scalar, otherwise return array
        if is_scalar:
            return float(total_tax.item() if isinstance(total_tax, np.ndarray) else total_tax)
        return total_tax


