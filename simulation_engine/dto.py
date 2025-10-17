import pydantic


class AbstractDTO(pydantic.BaseModel):
    """
    Abstract base class for Data Transfer Objects (DTOs).
    This class provides a common interface for all DTOs in the application.
    """
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True
        json_encoders = {
            pydantic.BaseModel: lambda v: v.model_dump(),
            pydantic.BaseModel.__name__: lambda v: v.model_dump(),
        }
        use_enum_values = True
        allow_population_by_field_name = True
        validate_assignment = True
        validate_all = True
        
class SimulationDataDTO(AbstractDTO):
    """Data Transfer Object for simulation data."""
    percentiles: dict[float, list[float]]
    mean: list[float]
    final_mean: float
    final_median: float
    final_std: float
    final_min: float
    final_max: float
    

class SimulationResultDTO(AbstractDTO):
    real: SimulationDataDTO
    nominal: SimulationDataDTO
    destitution: list[float]
    timesteps: list[float]
    # final_mean: float
    # final_median: float
    # final_std: float
    # final_min: float
    # final_max: float
    simulation_time: float
    simulation_time_per_timestep: float
    simulation_time_per_path: float
    total_parameters: int
    destitution_area: float
    