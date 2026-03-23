import os
import time
import pydantic
from pydantic import ConfigDict
import pandas as pd
import numpy as np
import tensorflow as tf
import tensorflow_probability as tfp

from functools import cached_property
from pydantic.alias_generators import to_camel, to_snake

from .common.types import SimulationPortfolioWeights, CashFlow, AssetCosts, ExpectedReturns
from .common.enums import SimulationType, SimulationStepType, InterpolationMethod
from .simulation_strategies import SimulationStrategyFactoryTF
from .dto import SimulationDataDTO, SimulationResultDTO
from simulation_engine.calcs import convert_to_real_wealth  # reuse existing real-wealth conversion


class RunSimulationCommandTF(pydantic.BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    number_of_simulations: int
    end_step: int
    weights: list[SimulationPortfolioWeights]
    savings_rates: list[CashFlow] = [CashFlow(step=0, value=0.0)]
    oneoff_transactions: list[CashFlow] = []
    inflation: float = 0.03
    initial_wealth: float = 0.0
    target_value: float | None = None
    percentiles: list[float] = [5, 25, 50, 75, 95]
    simulation_type: SimulationType = pydantic.Field(default=SimulationType.CHOLESKY)
    step_size: SimulationStepType = pydantic.Field(default=SimulationStepType.ANNUAL)
    weights_interpolation: InterpolationMethod = pydantic.Field(default=InterpolationMethod.LINEAR)
    savings_rate_interpolation: InterpolationMethod = pydantic.Field(default=InterpolationMethod.LINEAR)
    asset_costs: AssetCosts = pydantic.Field(default=AssetCosts())
    asset_returns: ExpectedReturns = pydantic.Field(default=ExpectedReturns())

    weights_tensor: tf.Tensor | None = None
    cashflows_tensor: tf.Tensor | None = None
    transactions_tensor: tf.Tensor | None = None
    time_steps_tensor: tf.Tensor | None = None

    def __init__(self, **data):
        super().__init__(**data)
        self.number_of_simulations = min(int(os.environ.get("MAX_SIMULATIONS", 1000000)), self.number_of_simulations)
        self._simulation_strategy = SimulationStrategyFactoryTF(
            self.base_simulation_data,
            self.number_of_simulations,
            self.inflation,
            self.initial_wealth,
            self.step_size,
            weights_tensor=self.weights_tensor,
            cashflows_tensor=self.cashflows_tensor,
            transactions_tensor=self.transactions_tensor,
            time_steps_tensor=self.time_steps_tensor,
        ).build_strategy(self.simulation_type)

    @property
    def simulation_strategy(self) -> SimulationStrategyFactoryTF:
        return self._simulation_strategy

    @cached_property
    def base_simulation_data(self) -> pd.DataFrame:
        base_timesteps = np.arange(0, self.end_step + 1, 1)
        base_timesteps = pd.Series(base_timesteps, name="timesteps")
        base_sim_data = pd.DataFrame(index=base_timesteps)

        self.weights.sort(key=lambda x: x.step)
        self.savings_rates.sort(key=lambda x: x.step)

        weights_df = pd.DataFrame([weight.model_dump() for weight in self.weights]).set_index("step")
        cashflows_df = pd.DataFrame([cf.model_dump() for cf in self.savings_rates]).rename(columns={"value": "cashflow"}).set_index("step")

        if self.oneoff_transactions:
            oneoff_df = pd.DataFrame([tx.model_dump() for tx in self.oneoff_transactions]).rename(columns={"value": "transactions"}).set_index("step")
        else:
            oneoff_df = pd.DataFrame(columns=["transactions"])        

        base_sim_data = base_sim_data.merge(weights_df, how="outer", left_index=True, right_index=True)
        base_sim_data = base_sim_data.merge(cashflows_df, how="outer", left_index=True, right_index=True)
        base_sim_data = base_sim_data.merge(oneoff_df, how="outer", left_index=True, right_index=True)

        base_sim_data["stocks"] = self.interpolate_series(base_sim_data["stocks"], self.weights_interpolation).fillna(0)
        base_sim_data["bonds"] = self.interpolate_series(base_sim_data["bonds"], self.weights_interpolation).fillna(0)
        base_sim_data["cash"] = 1 - base_sim_data["stocks"] - base_sim_data["bonds"]

        base_sim_data["cashflow"] = self.interpolate_series(base_sim_data["cashflow"], self.savings_rate_interpolation).fillna(0)
        base_sim_data["transactions"] = base_sim_data["transactions"].fillna(0)
        base_sim_data["time_delta"] = base_sim_data.index.to_series().diff().astype(float)
        base_sim_data["time_delta"] = base_sim_data["time_delta"].astype(float)
        return base_sim_data

    @staticmethod
    def interpolate_series(series: pd.Series, method: InterpolationMethod) -> pd.Series:
        if method == InterpolationMethod.LINEAR:
            return series.interpolate(method="index", limit_direction="both")
        elif method == InterpolationMethod.FFILL:
            return series.ffill()
        else:
            raise ValueError(f"Unknown interpolation method: {method}")

    def handle(self) -> SimulationResultDTO:
        import pandas as pd
        simulation = self.simulation_strategy

        exp_return = simulation.expected_returns.join(pd.Series(self.asset_returns.model_dump(), name='overrides'))
        exp_return = exp_return.join(pd.Series(self.asset_costs.model_dump(), name='costs'))
        exp_return['Expected Return'] = exp_return['overrides'].combine_first(exp_return['Expected Return'])
        exp_return['Expected Return'] = exp_return['Expected Return'] - exp_return['costs']
        exp_return = exp_return.drop(columns=['overrides', 'costs'])
        simulation.expected_returns = exp_return

        start = time.time()
        sim_data_tf = simulation.simulation_data

        mean_tf = tf.reduce_mean(sim_data_tf, axis=0)
        median_tf = tfp.stats.percentile(sim_data_tf, q=50.0, axis=0, interpolation="linear")
        percentiles_tf = tfp.stats.percentile(sim_data_tf, q=self.percentiles, axis=0, interpolation="linear")

        destitution_tf = tf.reduce_mean(tf.cast(tf.equal(sim_data_tf, 0), tf.float64), axis=0)
        if self.target_value is None:
            below_target_tf = tf.zeros_like(destitution_tf, dtype=tf.float64)
        else:
            below_target_tf = tf.reduce_mean(tf.cast(tf.less(sim_data_tf, self.target_value), tf.float64), axis=0)

        end = time.time()

        simulation_data = sim_data_tf.numpy()
        timesteps = self.base_simulation_data.index.to_list()
        mean = mean_tf.numpy()
        median = median_tf.numpy()
        percentiles = percentiles_tf.numpy()
        destitution = destitution_tf.numpy()
        below_target = below_target_tf.numpy()

        final_std = float(np.std(simulation_data[:, -1]))
        final_min = float(np.min(simulation_data[:, -1]))
        final_max = float(np.max(simulation_data[:, -1]))

        simulation_data_real = convert_to_real_wealth(simulation_data, np.array(timesteps, dtype=float), self.inflation)
        mean_real = convert_to_real_wealth(mean, np.array(timesteps, dtype=float), self.inflation)[0]
        percentiles_real = convert_to_real_wealth(percentiles, np.array(timesteps, dtype=float), self.inflation)
        final_std_real = float(np.std(simulation_data_real[:, -1]))
        final_min_real = float(np.min(simulation_data_real[:, -1]))
        final_max_real = float(np.max(simulation_data_real[:, -1]))

        time_deltas = pd.Series(self.base_simulation_data.time_delta).fillna(0).values
        total_time_delta = np.sum(time_deltas)
        if total_time_delta > 0:
            destitution_area = float(np.sum(destitution * time_deltas) / total_time_delta)
            below_target_area = float(np.sum(below_target * time_deltas) / total_time_delta)
        else:
            destitution_area = 0.0
            below_target_area = 0.0

        nominal = SimulationDataDTO(
            simulation_data=simulation_data,
            percentiles={p: percentiles[i, :].tolist() for i, p in enumerate(self.percentiles)},
            mean=mean.tolist(),
            final_mean=float(mean[-1]),
            final_median=float(median[-1]),
            final_max=final_max,
            final_min=final_min,
            final_std=final_std,
        )
        real = SimulationDataDTO(
            simulation_data=simulation_data_real,
            percentiles={p: percentiles_real[i, :].tolist() for i, p in enumerate(self.percentiles)},
            mean=mean_real.tolist(),
            final_mean=float(mean_real[-1]),
            final_median=float(median[-1]),
            final_max=final_max_real,
            final_min=final_min_real,
            final_std=final_std_real,
        )

        return SimulationResultDTO(
            real=real,
            nominal=nominal,
            destitution=destitution.tolist(),
            below_target=below_target.tolist(),
            timesteps=timesteps,
            simulation_time=end - start,
            simulation_time_per_timestep=(end - start) / len(timesteps),
            total_parameters=len(timesteps) * 3 * simulation.number_of_simulations,
            simulation_time_per_path=(end - start) / simulation.number_of_simulations,
            destitution_area=destitution_area,
            below_target_area=below_target_area,
        )

    def handle_tf(self) -> tf.Tensor:
        """
        Run the TF simulation and return the raw nominal simulation_data as a tf.Tensor
        without converting to numpy or wrapping in DTOs. This preserves the TF graph
        for autodiff/optimization use cases.
        """
        import pandas as pd

        simulation = self.simulation_strategy

        exp_return = simulation.expected_returns.join(pd.Series(self.asset_returns.model_dump(), name='overrides'))
        exp_return = exp_return.join(pd.Series(self.asset_costs.model_dump(), name='costs'))
        exp_return['Expected Return'] = exp_return['overrides'].combine_first(exp_return['Expected Return'])
        exp_return['Expected Return'] = exp_return['Expected Return'] - exp_return['costs']
        exp_return = exp_return.drop(columns=['overrides', 'costs'])
        simulation.expected_returns = exp_return

        return simulation.simulation_data

