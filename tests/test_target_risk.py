import numpy as np
import pandas as pd

from simulation_engine.commands import RunSimulationCommand
from simulation_engine.common.types import CashFlow, SimulationPortfolioWeights
from simulation_engine.dto import SimulationDataDTO, SimulationResultDTO
from services.simulation_service import SimulationService


class _FakeSimulationStrategy:
    def __init__(self, simulation_data: np.ndarray):
        self.simulation_data = simulation_data
        self.number_of_simulations = simulation_data.shape[0]
        self.expected_returns = pd.DataFrame(
            {"Expected Return": [0.08, 0.04, 0.02]},
            index=["stocks", "bonds", "cash"],
        )

    def get_mean(self):
        return np.mean(self.simulation_data, axis=0)

    def get_median(self):
        return np.median(self.simulation_data, axis=0)

    def get_percentiles(self, percentiles):
        return np.percentile(self.simulation_data, percentiles, axis=0)


def _make_result(simulation_data: np.ndarray) -> SimulationResultDTO:
    mean = np.mean(simulation_data, axis=0)
    percentiles = np.percentile(simulation_data, [5, 25, 50, 75, 95], axis=0)

    nominal = SimulationDataDTO(
        simulation_data=simulation_data,
        percentiles={p: percentiles[i, :].tolist() for i, p in enumerate([5, 25, 50, 75, 95])},
        mean=mean.tolist(),
        final_mean=float(mean[-1]),
        final_median=float(np.median(simulation_data[:, -1])),
        final_std=float(np.std(simulation_data[:, -1])),
        final_min=float(np.min(simulation_data[:, -1])),
        final_max=float(np.max(simulation_data[:, -1])),
    )
    real = nominal

    return SimulationResultDTO(
        real=real,
        nominal=nominal,
        destitution=[0.0] * simulation_data.shape[1],
        below_target=[0.0] * simulation_data.shape[1],
        timesteps=[0.0, 1.0, 2.0],
        simulation_time=1.0,
        simulation_time_per_timestep=0.33,
        simulation_time_per_path=0.5,
        total_parameters=10,
        destitution_area=0.0,
        below_target_area=0.0,
    )


def test_run_simulation_command_computes_below_target():
    command = RunSimulationCommand(
        number_of_simulations=2,
        end_step=2,
        weights=[SimulationPortfolioWeights(step=0, stocks=0.6, bonds=0.4)],
        savings_rates=[CashFlow(step=0, value=0.0)],
        oneoff_transactions=[],
        inflation=0.0,
        target_value=100.0,
    )
    command._simulation_strategy = _FakeSimulationStrategy(
        np.array(
            [
                [150.0, 90.0, 80.0],
                [120.0, 110.0, 95.0],
            ]
        )
    )

    result = command.handle()

    assert result.below_target == [0.0, 0.5, 1.0]
    assert result.below_target_area == 0.75


def test_aggregate_portfolio_results_computes_below_target():
    service = SimulationService.__new__(SimulationService)
    service.financial_plan = type("Plan", (), {"portfolio_target_value": 100.0})()
    service.adviser_config = type("Config", (), {"number_of_simulations": 2})()

    portfolio_results = {
        "p1": _make_result(
            np.array(
                [
                    [70.0, 40.0, 30.0],
                    [90.0, 50.0, 40.0],
                ]
            )
        ),
        "p2": _make_result(
            np.array(
                [
                    [50.0, 40.0, 30.0],
                    [30.0, 40.0, 30.0],
                ]
            )
        ),
    }

    aggregated = service._aggregate_portfolio_results(portfolio_results, end_step=2)

    assert aggregated.below_target == [0.0, 1.0, 1.0]
    assert aggregated.below_target_area == 1.0
