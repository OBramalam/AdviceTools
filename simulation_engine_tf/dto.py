import pydantic
import numpy as np
import tensorflow as tf


class AbstractDTO(pydantic.BaseModel):
    class Config:
        arbitrary_types_allowed = True
        use_enum_values = True
        allow_population_by_field_name = True
        validate_assignment = True
        validate_all = True


def _to_numpy(x):
    if isinstance(x, tf.Tensor):
        return x.numpy()
    return x


class SimulationDataDTO(AbstractDTO):
    simulation_data: np.ndarray
    percentiles: dict[float, list[float]]
    mean: list[float]
    final_mean: float
    final_median: float
    final_std: float
    final_min: float
    final_max: float

    @pydantic.model_validator(mode="before")
    @classmethod
    def convert_tensors(cls, values):
        d = dict(values)
        d["simulation_data"] = _to_numpy(d["simulation_data"])

        m = d.get("mean")
        if isinstance(m, tf.Tensor):
            d["mean"] = m.numpy().tolist()
        elif isinstance(m, np.ndarray):
            d["mean"] = m.tolist()
        elif isinstance(m, list):
            d["mean"] = m
        else:
            d["mean"] = list(np.atleast_1d(m))
        return d


class SimulationResultDTO(AbstractDTO):
    real: SimulationDataDTO
    nominal: SimulationDataDTO
    destitution: list[float]
    timesteps: list[float]
    simulation_time: float
    simulation_time_per_timestep: float
    simulation_time_per_path: float
    total_parameters: int
    destitution_area: float

