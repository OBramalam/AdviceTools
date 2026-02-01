from abc import ABC, abstractmethod

class AccountType(ABC):
    @abstractmethod
    def calculate_tax(self, income: float) -> float:
        pass