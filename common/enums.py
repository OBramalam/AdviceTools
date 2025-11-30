from enum import Enum

class CashFlowType(str, Enum):
    RECURRING = "recurring"
    ONEOFF = "oneoff"
