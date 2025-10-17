from abc import ABC, abstractmethod
import numpy as np
import pandas as pd
from functools import cached_property
from .data_utils import get_historical_cov, get_historical_exp_ret, load_historical_returns_header
from .calcs import cholesky_bootstrap_returns, simulate_wealth
from .common.enums import SimulationStepType, SimulationType


class AbstractSimulationStrategy(ABC):
    """
    Abstract base class for simulation strategies.
    """

    def __init__(
        self,
        base_sim_data: pd.DataFrame,
        number_of_simulations: int,
        inflation: float,
        initial_wealth: float,
        step_type: SimulationStepType = SimulationStepType.MONTHLY,
    ):
        self.base_sim_data = base_sim_data
        self.number_of_simulations = number_of_simulations
        self.inflation = inflation
        self.initial_wealth = initial_wealth
        self._simulation_data = None
        self.step_type = step_type

    @property
    @abstractmethod
    def simulated_returns(self) -> np.ndarray:
        """
        Returns the simulated returns.
        """
        raise NotImplementedError("Subclasses must implement this property.")

    @property
    @abstractmethod
    def assets(self) -> list[str]:
        """
        Returns the list of assets.
        """
        raise NotImplementedError("Subclasses must implement this property.")

    @property
    def weights(self) -> np.ndarray:
        """
        Returns the weights of the assets.
        """
        _sim_data = self.base_sim_data.dropna(how="any")
        weights = _sim_data[self.assets]
        weights = weights.values
        return weights

    @property
    def cashflows(self) -> np.ndarray:
        """
        Returns the cashflows.
        """
        _sim_data = self.base_sim_data.dropna(how="any")
        cashflows = _sim_data["cashflow"].values
        return cashflows

    @property
    def transactions(self) -> np.ndarray:
        """
        Returns the transactions.
        """
        _sim_data = self.base_sim_data.dropna(how="any")
        transactions = _sim_data["transactions"].values
        return transactions

    @property
    def time_steps(self) -> np.ndarray:
        """
        Returns the time steps.
        """
        time_steps = self.base_sim_data.index.to_series().values
        return time_steps

    def simulate(self):
        return simulate_wealth(
            self.simulated_returns,
            self.weights,
            self.initial_wealth,
            self.cashflows,
            self.transactions,
            self.inflation,
            self.time_steps,
        )

    @property
    def simulation_data(self) -> np.ndarray:
        """
        Returns the simulation data.
        If the simulation has not been run yet, it will be executed.

        Returns
        -------
        np.ndarray
            The simulation data. numer_of_simulations x num_timesteps array of wealth values.
        """
        if self._simulation_data is None:
            print("Simulating...")
            self._simulation_data = self.simulate()
        return self._simulation_data

    def get_percentiles(self, percentiles: list[float] = [5, 25, 50, 75, 95]) -> np.ndarray:
        """
        Returns the percentiles of the simulation data.

        Parameters
        ----------
        percentiles : list[float], optional
            List of percentiles to calculate, by default [5, 25, 50, 75, 95]

        Returns
        -------
        pd.DataFrame
            DataFrame containing the percentiles.
        """
        return np.percentile(self.simulation_data, percentiles, axis=0)

    def get_mean(self) -> np.ndarray:
        """
        Returns the mean of the simulation data.

        Returns
        -------
        pd.DataFrame
            DataFrame containing the mean.
        """
        return np.mean(self.simulation_data, axis=0)
    
    def get_median(self) -> np.ndarray:
        """
        Returns the median of the simulation data.

        Returns
        -------
        pd.DataFrame
            DataFrame containing the median.
        """
        return np.median(self.simulation_data, axis=0)


class CholeskySimulationStrategy(AbstractSimulationStrategy):

    def __init__(
        self,
        base_sim_data: pd.DataFrame,
        number_of_simulations: int,
        inflation: float,
        initial_wealth: float,
        expected_returns: pd.DataFrame = None,
        step_type: SimulationStepType = SimulationStepType.MONTHLY,
    ):
        super().__init__(base_sim_data, number_of_simulations, inflation, initial_wealth, step_type)
        self._expected_returns = expected_returns

    @cached_property
    def covariance_matrix(self) -> pd.DataFrame:
        """
        Calculate the covariance matrix from the base simulation data.
        """
        cov = get_historical_cov(step_type=self.step_type)
        return cov

    @cached_property
    def assets(self) -> list[str]:
        return load_historical_returns_header().str.lower().to_list()

    @property
    def expected_returns(self) -> pd.DataFrame:
        """
        Calculate the expected returns from the base simulation data. Use historical data if not provided.
        """
        if self._expected_returns is not None:
            return self._expected_returns
        exp_ret = get_historical_exp_ret(step_type=self.step_type)
        return exp_ret

    @expected_returns.setter
    def expected_returns(self, value: pd.DataFrame):
        """
        Set the expected returns for the simulation.
        """
        self._expected_returns = value.T[self.assets].T

    @property
    def simulated_returns(self) -> np.ndarray:
        """
        Simulate returns using the Cholesky decomposition of the covariance matrix.
        """
        cov = self.covariance_matrix
        exp_ret = self.expected_returns
        n = self.number_of_simulations
        s = self.base_sim_data.shape[0] - 1  # number of time steps
        return cholesky_bootstrap_returns(n, s, cov, exp_ret)


class SimulationStrategyFactory:

    def __init__(
        self,
        base_sim_data: pd.DataFrame,
        number_of_simulations: int,
        inflation: float,
        initial_wealth: float,
        step_type: SimulationStepType = SimulationStepType.MONTHLY,
    ):
        self.base_sim_data = base_sim_data
        self.number_of_simulations = number_of_simulations
        self.inflation = inflation
        self.initial_wealth = initial_wealth
        self.step_type = step_type

    def build_strategy(self, simulation_type: SimulationType) -> AbstractSimulationStrategy:
        if simulation_type == SimulationType.CHOLESKY:
            return CholeskySimulationStrategy(
                self.base_sim_data,
                self.number_of_simulations,
                self.inflation,
                self.initial_wealth,
                step_type=self.step_type,
            )
        raise ValueError(f"Unsupported simulation type: {simulation_type}")
