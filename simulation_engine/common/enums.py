from enum import Enum


class SimulationType(str, Enum):
    CHOLESKY = "cholesky"
    BLOCK_BOOTSTRAP = "block_bootstrap"

class SimulationStepType(str, Enum):
    ANNUAL = "annual"
    MONTHLY = "monthly"

class InterpolationMethod(str, Enum):
    LINEAR = "linear"
    FFILL = "ffill"
    