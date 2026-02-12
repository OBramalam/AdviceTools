from abc import ABC, abstractmethod
from typing import Union
import numpy as np


class AccountType(ABC):
    @abstractmethod
    def calculate_tax(
        self, 
        return_on_investment: Union[float, np.ndarray]
    ) -> Union[float, np.ndarray]:
        """
        Calculate tax on investment returns.
        
        Args:
            return_on_investment: Investment return amount(s) - can be scalar or numpy array
                representing returns for one or multiple simulation paths
            
        Returns:
            Tax amount(s) - same shape as return_on_investment
        """
        pass