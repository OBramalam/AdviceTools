from abc import ABC, abstractmethod
from functools import cached_property
import pandas as pd
import tensorflow as tf
import tensorflow_probability as tfp

from .calcs import cholesky_bootstrap_returns_tf, simulate_wealth_tf
from .common.enums import SimulationStepType, SimulationType


class AbstractSimulationStrategyTF(ABC):
    def __init__(
        self,
        base_sim_data: pd.DataFrame,
        number_of_simulations: int,
        inflation: float,
        initial_wealth: float,
        step_type: SimulationStepType = SimulationStepType.MONTHLY,
        weights_tensor: tf.Tensor | None = None,
        cashflows_tensor: tf.Tensor | None = None,
        transactions_tensor: tf.Tensor | None = None,
        time_steps_tensor: tf.Tensor | None = None,
    ):
        self.base_sim_data = base_sim_data
        self.number_of_simulations = number_of_simulations
        self.inflation = inflation
        self.initial_wealth = initial_wealth
        self._simulation_data = None
        self.step_type = step_type
        self._weights_override = weights_tensor
        self._cashflows_override = cashflows_tensor
        self._transactions_override = transactions_tensor
        self._time_steps_override = time_steps_tensor

    @property
    @abstractmethod
    def simulated_returns(self) -> tf.Tensor:
        raise NotImplementedError

    @cached_property
    @abstractmethod
    def assets(self) -> list[str]:
        raise NotImplementedError

    @property
    def weights(self) -> tf.Tensor:
        if self._weights_override is not None:
            return self._weights_override
        _sim_data = self.base_sim_data.dropna(how="any")
        weights = _sim_data[self.assets].values
        return tf.convert_to_tensor(weights, dtype=tf.float64)

    @property
    def cashflows(self) -> tf.Tensor:
        if self._cashflows_override is not None:
            return self._cashflows_override
        _sim_data = self.base_sim_data.dropna(how="any")
        cashflows = _sim_data["cashflow"].values
        return tf.convert_to_tensor(cashflows, dtype=tf.float64)

    @property
    def transactions(self) -> tf.Tensor:
        if self._transactions_override is not None:
            return self._transactions_override
        _sim_data = self.base_sim_data.dropna(how="any")
        transactions = _sim_data["transactions"].values
        return tf.convert_to_tensor(transactions, dtype=tf.float64)

    @property
    def time_steps(self) -> tf.Tensor:
        if self._time_steps_override is not None:
            return self._time_steps_override
        time_steps = self.base_sim_data.index.to_series().values
        return tf.convert_to_tensor(time_steps, dtype=tf.float64)

    def simulate(self) -> tf.Tensor:
        return simulate_wealth_tf(
            self.simulated_returns,
            self.weights,
            self.initial_wealth,
            self.cashflows,
            self.transactions,
            self.inflation,
            self.time_steps,
        )

    @property
    def simulation_data(self) -> tf.Tensor:
        if self._simulation_data is None:
            self._simulation_data = self.simulate()
        return self._simulation_data

    def get_percentiles(self, percentiles: list[float] = [5, 25, 50, 75, 95]) -> tf.Tensor:
        q = tfp.stats.percentile(self.simulation_data, q=percentiles, axis=0, interpolation="linear")
        return q

    def get_mean(self) -> tf.Tensor:
        return tf.reduce_mean(self.simulation_data, axis=0)

    def get_median(self) -> tf.Tensor:
        return tfp.stats.percentile(self.simulation_data, q=50.0, axis=0, interpolation="linear")


class CholeskySimulationStrategyTF(AbstractSimulationStrategyTF):
    def __init__(
        self,
        base_sim_data: pd.DataFrame,
        number_of_simulations: int,
        inflation: float,
        initial_wealth: float,
        expected_returns: pd.DataFrame | None = None,
        step_type: SimulationStepType = SimulationStepType.MONTHLY,
        **overrides,
    ):
        super().__init__(
            base_sim_data,
            number_of_simulations,
            inflation,
            initial_wealth,
            step_type,
            **overrides,
        )
        self._expected_returns = expected_returns

    @cached_property
    def covariance_matrix(self) -> pd.DataFrame:
        from simulation_engine.data_utils import get_historical_cov
        from simulation_engine.common.enums import SimulationStepType as OrigStep
        step = OrigStep[self.step_type.name]
        return get_historical_cov(step_type=step)

    @cached_property
    def assets(self) -> list[str]:
        from simulation_engine.data_utils import load_historical_returns_header
        return load_historical_returns_header().str.lower().to_list()

    @property
    def expected_returns(self) -> pd.DataFrame:
        if self._expected_returns is not None:
            return self._expected_returns
        from simulation_engine.data_utils import get_historical_exp_ret
        from simulation_engine.common.enums import SimulationStepType as OrigStep
        step = OrigStep[self.step_type.name]
        return get_historical_exp_ret(step_type=step)

    @expected_returns.setter
    def expected_returns(self, value: pd.DataFrame):
        self._expected_returns = value.T[self.assets].T

    @property
    def simulated_returns(self) -> tf.Tensor:
        from simulation_engine.calcs import cholesky_bootstrap_returns
        import numpy as np

        cov_np = self.covariance_matrix
        exp_np = self.expected_returns.loc[self.assets, "Expected Return"].to_frame()
        n = int(self.number_of_simulations)
        s = int(self.base_sim_data.shape[0] - 1)
        samples_np = cholesky_bootstrap_returns(n, s, cov_np, exp_np)  # shape [n,s,k]
        return tf.convert_to_tensor(samples_np, dtype=tf.float64)


class SimulationStrategyFactoryTF:
    def __init__(
        self,
        base_sim_data: pd.DataFrame,
        number_of_simulations: int,
        inflation: float,
        initial_wealth: float,
        step_type: SimulationStepType = SimulationStepType.MONTHLY,
        weights_tensor: tf.Tensor | None = None,
        cashflows_tensor: tf.Tensor | None = None,
        transactions_tensor: tf.Tensor | None = None,
        time_steps_tensor: tf.Tensor | None = None,
    ):
        self.base_sim_data = base_sim_data
        self.number_of_simulations = number_of_simulations
        self.inflation = inflation
        self.initial_wealth = initial_wealth
        self.step_type = step_type
        self.weights_tensor = weights_tensor
        self.cashflows_tensor = cashflows_tensor
        self.transactions_tensor = transactions_tensor
        self.time_steps_tensor = time_steps_tensor

    def build_strategy(self, simulation_type: SimulationType) -> AbstractSimulationStrategyTF:
        if simulation_type == SimulationType.CHOLESKY:
            return CholeskySimulationStrategyTF(
                self.base_sim_data,
                self.number_of_simulations,
                self.inflation,
                self.initial_wealth,
                step_type=self.step_type,
                weights_tensor=self.weights_tensor,
                cashflows_tensor=self.cashflows_tensor,
                transactions_tensor=self.transactions_tensor,
                time_steps_tensor=self.time_steps_tensor,
            )
        raise ValueError(f"Unsupported simulation type: {simulation_type}")

