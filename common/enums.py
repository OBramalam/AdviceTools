from enum import Enum

class CashFlowType(str, Enum):
    RECURRING = "recurring"
    ONEOFF = "oneoff"

class CashFlowPeriodicity(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"
    ONE_OFF = "one_off"
