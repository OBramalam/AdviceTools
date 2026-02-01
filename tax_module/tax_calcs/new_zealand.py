

def calculate_PIE_tax(pir_rate: float, marginal_tax_rate: float, pie_return: float) -> float:
    """
    Calculate the PIE tax on income.
    """
    if pie_return < 0:
        return 0
    
    taxable_income = pie_return / 0.4 # Assume 50% returns come from interest/dividends

    if marginal_tax_rate <= pir_rate:
        return marginal_tax_rate * pie_return
    else:
        return pir_rate * pie_return

def calculate_FIF_tax(marginal_tax_rate: float, fif_return: float) -> float:
    """
    Calculate the FIF tax on income.
    """
    fair_dividend_rate_tax = marginal_tax_rate * 0.05

    comparative_value_tax = marginal_tax_rate * fif_return

    if comparative_value_tax > fair_dividend_rate_tax:
        return fair_dividend_rate_tax
    else:
        return comparative_value_tax

