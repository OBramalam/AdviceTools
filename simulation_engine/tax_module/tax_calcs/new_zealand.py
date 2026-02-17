import numpy as np
from typing import Union


def calculate_PIE_tax(
    pir_rate: float, 
    marginal_tax_rate: float, 
    pie_return: Union[float, np.ndarray]
) -> Union[float, np.ndarray]:
    """
    Calculate the PIE tax on income.
    
    Args:
        pir_rate: Prescribed Investor Rate (PIR)
        marginal_tax_rate: Marginal tax rate
        pie_return: PIE return amount(s) - can be scalar or numpy array
        
    Returns:
        PIE tax amount(s) - same shape as pie_return
    """
    # Check if input is scalar before converting to array
    is_scalar = isinstance(pie_return, (int, float))
    pie_return = np.asarray(pie_return)
    
    # Assume 40% returns come from interest/dividends
    taxable_income = pie_return * 0.4
    
    # Set tax to 0 for negative returns
    tax = np.where(
        pie_return < 0,
        0.0,
        np.where(
            marginal_tax_rate <= pir_rate,
            marginal_tax_rate * taxable_income,
            pir_rate * taxable_income
        )
    )
    
    # Return scalar if input was scalar, otherwise return array
    if is_scalar:
        return float(tax.item() if isinstance(tax, np.ndarray) else tax)
    return tax


def calculate_FIF_tax(
    marginal_tax_rate: float, 
    fif_return: Union[float, np.ndarray]
) -> Union[float, np.ndarray]:
    """
    Calculate the FIF tax on income.
    
    Args:
        marginal_tax_rate: Marginal tax rate
        fif_return: FIF return amount(s) - can be scalar or numpy array
        
    Returns:
        FIF tax amount(s) - same shape as fif_return
    """
    # Check if input is scalar before converting to array
    is_scalar = isinstance(fif_return, (int, float))
    fif_return = np.asarray(fif_return)
    
    fair_dividend_rate_tax = marginal_tax_rate * 0.05
    comparative_value_tax = marginal_tax_rate * fif_return
    
    # Take the minimum of fair dividend rate tax and comparative value tax
    # Set tax to 0 for negative returns (no tax refunds on losses)
    tax = np.where(
        fif_return < 0,
        0.0,
        np.minimum(fair_dividend_rate_tax, comparative_value_tax)
    )
    
    # Return scalar if input was scalar, otherwise return array
    if is_scalar:
        return float(tax.item() if isinstance(tax, np.ndarray) else tax)
    return tax

