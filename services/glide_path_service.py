from services import ParserService, SimulationService
from schemas import AdviserConfig, Profile, RecurringCashFlow, ExtractionSchema
from simulation_engine.common.types import SimulationPortfolioWeights
from scipy.optimize import minimize
import datetime
import numpy as np
from typing import List

class GlidePathOptimizer:

    def __init__(self, profile: Profile, cash_flows: List[RecurringCashFlow], adviser_config: AdviserConfig):
        self.profile = profile
        self.cash_flows = cash_flows
        self.adviser_config = adviser_config


    def run(self):

        result = self.optimize()
        equity_weights = result.x
        simulation_weights = self._build_simulation_weights(equity_weights)

        return simulation_weights


    def optimize(self):

        start_weights = self._build_start_weights()
        bounds = [(0, 1) for _ in range(len(start_weights))]

        res = minimize(
            fun=self._objective, 
            x0=start_weights,
            method='SLSQP',
            bounds=bounds
        )

        return res


    def _objective(self, allocations):
        result = self._run_simulation_with_allocations(allocations)
        destitution = result.destitution_area

        penalty = self._direction_penalty(allocations)

        return destitution + penalty


    def _run_simulation_with_allocations(self, weights):

        simulation_weights = self._build_simulation_weights(weights)

        simulation_service = SimulationService(
            profile=self.profile, 
            cash_flows=self.cash_flows, 
            adviser_config=self.adviser_config, 
            weights=simulation_weights
        )

        result = simulation_service.simulate()
        return result


    def _build_simulation_weights(self, weights):

        changes = np.concatenate([[True], weights[1:] != weights[:-1]])
        change_indices = np.where(changes)[0]
        
        simulation_weights = []

        for idx in change_indices:
            simulation_weights.append(SimulationPortfolioWeights(
                step=float(idx),
                stocks=float(weights[idx]),
                bonds=float(1.0 - weights[idx])
            )
        )

        return simulation_weights


    def _build_start_weights(self):
        n_years = int(self.profile.plan_end_age) - int(self.profile.age)
        start_weights = np.linspace(1, 0.3, n_years)
        return start_weights


    def _direction_penalty(self, allocations: np.ndarray) -> float:
        changes = np.diff(allocations)
        increases = np.clip(changes, 0.0, None)
        penalty = 200.0 * float(np.sum(increases ** 2))
        return penalty

