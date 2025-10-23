import pydantic
from enum import Enum
from functools import cached_property
import pandas as pd
import numpy as np
from .common.types import SimulationPortfolioWeights, CashFlow, AssetCosts, ExpectedReturns
from .common.enums import SimulationType, SimulationStepType, InterpolationMethod
from .simulation_strategies import SimulationStrategyFactory
from .dto import SimulationDataDTO, SimulationResultDTO
from pydantic.alias_generators import to_camel, to_snake
from .calcs import convert_to_real_wealth
import os


class RunSimulationCommand(pydantic.BaseModel):
    """Command to create a simulation."""

    number_of_simulations: int
    end_step: int
    weights: list[SimulationPortfolioWeights]
    savings_rates: list[CashFlow] = [CashFlow(step=0, value=0.0)]
    oneoff_transactions: list[CashFlow] = []
    inflation: float = 0.03
    initial_wealth: float = 0.0
    percentiles: list[float] = [5, 25, 50, 75, 95]
    simulation_type: SimulationType = pydantic.Field(default=SimulationType.CHOLESKY)
    step_size: SimulationStepType = pydantic.Field(default=SimulationStepType.ANNUAL)
    weights_interpolation: InterpolationMethod = pydantic.Field(default=InterpolationMethod.LINEAR)
    savings_rate_interpolation: InterpolationMethod = pydantic.Field(default=InterpolationMethod.LINEAR)
    asset_costs: AssetCosts = pydantic.Field(default=AssetCosts())
    asset_returns: ExpectedReturns = pydantic.Field(default=ExpectedReturns())


    def __init__(self, **data):
        super().__init__(**data)
        self.number_of_simulations = min(int(os.environ.get("MAX_SIMULATIONS", 1000000)), self.number_of_simulations)
        self._simulation_strategy = SimulationStrategyFactory(
            self.base_simulation_data, self.number_of_simulations, self.inflation, self.initial_wealth, self.step_size
        ).build_strategy(self.simulation_type)
        
        asset_returns_df = pd.DataFrame([self.asset_returns.model_dump()])

    @property
    def simulation_strategy(self) -> SimulationStrategyFactory:
        return self._simulation_strategy

    @cached_property
    def base_simulation_data(self) -> pd.DataFrame:
        base_timesteps = np.arange(0, self.end_step + 1, 1)
        base_timesteps = pd.Series(base_timesteps, name="timesteps")

        base_sim_data = pd.DataFrame(index=base_timesteps)

        self.weights.sort(key=lambda x: x.step)
        self.savings_rates.sort(key=lambda x: x.step)

        weights_df = pd.DataFrame([weight.model_dump() for weight in self.weights])
        weights_df = weights_df.set_index("step")

        cashflows_df = pd.DataFrame([cashflow.model_dump() for cashflow in self.savings_rates])
        cashflows_df = cashflows_df.rename(columns={"value": "cashflow"})
        cashflows_df = cashflows_df.set_index("step")

        
        if self.oneoff_transactions:
            oneoff_df = pd.DataFrame([oneoff.model_dump() for oneoff in self.oneoff_transactions])
            oneoff_df = oneoff_df.rename(columns={"value": "transactions"})
            oneoff_df = oneoff_df.set_index("step")
        else:
            oneoff_df = pd.DataFrame(columns=["transactions"])

        base_sim_data = base_sim_data.merge(weights_df, how="outer", left_index=True, right_index=True)
        base_sim_data = base_sim_data.merge(cashflows_df, how="outer", left_index=True, right_index=True)
        base_sim_data = base_sim_data.merge(oneoff_df, how="outer", left_index=True, right_index=True)

        base_sim_data["stocks"] = self.interpolate_series(
            base_sim_data["stocks"], self.weights_interpolation
        ).fillna(0)
        base_sim_data["bonds"] = self.interpolate_series(
            base_sim_data["bonds"], self.weights_interpolation
        ).fillna(0)
        base_sim_data["cash"] = 1 - base_sim_data["stocks"] - base_sim_data["bonds"]

        base_sim_data["cashflow"] = self.interpolate_series(
            base_sim_data["cashflow"], self.savings_rate_interpolation
        ).fillna(0)

        base_sim_data["transactions"] = base_sim_data["transactions"].fillna(0)
        base_sim_data["time_delta"] = base_sim_data.index.to_series().diff().astype(float)
        base_sim_data["time_delta"] = base_sim_data["time_delta"].astype(float)
        return base_sim_data
    
    @staticmethod
    def interpolate_series(series: pd.Series, method: InterpolationMethod) -> pd.Series:
        """
        Interpolate a pandas Series using the specified method.
        Parameters
        ----------
        series : pd.Series
            The series to interpolate.
        method : InterpolationMethod
            The interpolation method to use.
        Returns
        -------
        pd.Series
            The interpolated series.
        """
        if method == InterpolationMethod.LINEAR:
            return series.interpolate(method="index", limit_direction="both")
        elif method == InterpolationMethod.FFILL:
            return series.ffill()
        else:
            raise ValueError(f"Unknown interpolation method: {method}")
    
    def handle(self) -> SimulationResultDTO:
        """
        Handle the command to run the simulation.
        Returns
        -------
        SimulationDTO
            Data Transfer Object containing the simulation results.
        """
        import time

        simulation = self.simulation_strategy

        # setup simulation

        exp_return = self.simulation_strategy.expected_returns.join(pd.Series(self.asset_returns.model_dump(), name='overrides'))
        exp_return = exp_return.join(pd.Series(self.asset_costs.model_dump(), name='costs'))
        exp_return['Expected Return'] = exp_return['overrides'].combine_first(exp_return['Expected Return'])
        exp_return['Expected Return'] = exp_return['Expected Return'] - exp_return['costs']
        exp_return = exp_return.drop(columns=['overrides', 'costs'])


        simulation.expected_returns = exp_return
        
        start = time.time()
        simulation.simulation_data
        

        mean = simulation.get_mean()
        mean_real = convert_to_real_wealth(
            mean, self.base_simulation_data.index.values, self.inflation
        )[0]
        
        median = simulation.get_median()
        median_real = convert_to_real_wealth(
            median, self.base_simulation_data.index.values, self.inflation
        )[0]
        

        percentiles = simulation.get_percentiles(self.percentiles)
        percentiles_real = convert_to_real_wealth(
            percentiles, self.base_simulation_data.index.values, self.inflation
        )

        destitution_risk = (simulation.simulation_data == 0).sum(axis=0) / simulation.simulation_data.shape[0]
        destitution_risk = destitution_risk

        final_std=np.std(simulation.simulation_data[-1])
        final_min=np.min(simulation.simulation_data[-1])
        final_max=np.max(simulation.simulation_data[-1])
        
        real_data = convert_to_real_wealth(
            simulation.simulation_data[-1], self.base_simulation_data.index.values, self.inflation
        )
        final_std_real = np.std(real_data[-1])
        final_min_real = np.min(real_data[-1])
        final_max_real = np.max(real_data[-1])
        
        destitution_area = np.sum(destitution_risk * self.base_simulation_data.time_delta.fillna(0).values)/ np.sum(self.base_simulation_data.time_delta.fillna(0).values)
        
        end = time.time()
        

        nominal = SimulationDataDTO(
            percentiles={percentile: percentiles[i, :].tolist() for i, percentile in enumerate(self.percentiles)},
            mean=mean.tolist(),
            final_mean=mean[-1],
            final_median=median[-1],
            final_max=final_max,
            final_min=final_min,
            final_std=final_std,
        )
        real = SimulationDataDTO(
            percentiles={percentile: percentiles_real[i, :].tolist() for i, percentile in enumerate(self.percentiles)},
            mean=mean_real.tolist(),
            final_mean=mean_real[-1],
            final_median=median_real[-1],
            final_max=final_max_real,
            final_min=final_min_real,
            final_std=final_std_real,
        )

        return SimulationResultDTO(
            real=real,
            nominal=nominal,
            destitution=destitution_risk.tolist(),
            timesteps=self.base_simulation_data.index.to_list(),
            simulation_time=end - start,
            simulation_time_per_timestep=(end - start) / len(self.base_simulation_data.index),
            total_parameters=len(self.base_simulation_data.index) * 3 * simulation.number_of_simulations,
            simulation_time_per_path=(end - start) / simulation.number_of_simulations,
            destitution_area=destitution_area,
        )
