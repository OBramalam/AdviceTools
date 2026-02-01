from .base import AccountType
from abc import abstractmethod
from ..tax_calcs.new_zealand import calculate_PIE_tax, calculate_FIF_tax


class NewZealandBaseAccount(AccountType):
    def __init__(
        self, 
        return_on_investment: float,
        pir_rate: float, 
        marginal_tax_rate: float,
        percent_pie_fund: float,
        percent_fif_fund: float,
    ):
        self.return_on_investment = return_on_investment
        self.pir_rate = pir_rate
        self.marginal_tax_rate = marginal_tax_rate
        self.percent_pie_fund = percent_pie_fund
        self.percent_fif_fund = percent_fif_fund


    def calculate_tax(self) -> float:
        
        pie_return = self.percent_pie_fund * self.return_on_investment
        fif_return = self.percent_fif_fund * self.return_on_investment

        pie_tax = calculate_PIE_tax(self.pir_rate, self.marginal_tax_rate, pie_return)
        fif_tax = calculate_FIF_tax(self.marginal_tax_rate, fif_return)

        return pie_tax + fif_tax


class NewZealandKiwiSaver(NewZealandBaseAccount):
    def __init__(
        self, 
        return_on_investment: float,
        pir_rate: float, 
        marginal_tax_rate: float, 
        percent_pie_fund: float,
        percent_fif_fund: float,
        employee_contribution: float, 
        employer_contribution: float,
    ):
        self.employee_contribution = employee_contribution
        self.employer_contribution = employer_contribution
        super().__init__(return_on_investment, pir_rate, marginal_tax_rate, percent_pie_fund, percent_fif_fund)
    
