from enum import Enum


class SimulationType(Enum):
    CHOLESKY = "CHOLESKY"


class SimulationStepType(Enum):
    MONTHLY = "MONTHLY"
    ANNUAL = "ANNUAL"


class InterpolationMethod(Enum):
    LINEAR = "LINEAR"
    FFILL = "FFILL"

