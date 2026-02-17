import numpy as np
import pandas as pd
# from numba import jit


def cholesky_bootstrap_returns(n: int, s: int, cov: pd.DataFrame, exp_ret: pd.DataFrame) -> np.ndarray:
    """
    Simulate returns using the Cholesky decomposition of the covariance matrix.
    Parameters
    ----------
    n : int
        Number of simulations.
    s : int
        Length of the simulation.
    cov : pandas.DataFrame
        Covariance matrix.
    exp_ret : pandas.DataFrame
        Expected returns.

    Returns
    -------
    np.array
        n x s x num_assets tensor

    """
    rng = np.random.default_rng()
    y = rng.multivariate_normal(exp_ret.values.flatten(), cov.values, size=(n, s))
    return y

# @jit(nopython=True)
# def _compute_wealth_loop(wealth, simulated_returns, weights, cashflows, transactions,
#                          time_delta, inflation, s):
#     """
#     JIT-compiled version of the wealth calculation loop.
#     Keeps the exact same vectorized numpy operations.
#     """
#     inflation_factor = 1.0
    
#     for i in range(s):
#         inflation_factor *= (1.0 + inflation) ** time_delta[i]
#         portfolio_returns = (weights[i] * (1.0 + simulated_returns[:, i, :]) ** time_delta[i]).sum(axis=1)
        
#         wealth[:, i + 1] = (
#             wealth[:, i] * portfolio_returns + 
#             (cashflows[i] * time_delta[i] + transactions[i]) * inflation_factor
#         )
#         negative_mask = wealth[:, i + 1] < 0.0
#         wealth[negative_mask, i + 1] = 0.0
    
#     return wealth  


def simulate_wealth(
    simulated_returns: np.ndarray,
    weights: np.ndarray,
    initial_wealth: float,
    cashflows: np.ndarray,
    transactions: np.ndarray,
    inflation: float = 0.03,
    time_steps: np.ndarray = None,
    tax_model = None,
    is_monthly: bool = True,
) -> np.ndarray:
    """
    Simulate wealth using the simulated returns and weights.
    Parameters
    ----------
    simulated_returns : np.array
        n x s x n_assets tensor of simulated returns.
    weights : np.array
        s x num_assets matrix of weights.
    initial_wealth : float
        Initial wealth.
    cashflows : np.array
        s x 1 vector of cashflows.
    transactions : np.array
        s x 1 vector of transactions.
    inflation : float, optional
        Inflation rate. Default is 0.03.
    time_steps : np.array, optional
        s+1 x 1 vector of time steps. If None, will be set to np.arange(0, s + 1).
    tax_model : optional
        Tax model for calculating tax on returns. If None, no tax is applied.
    is_monthly : bool, optional
        If True, uses monthly steps (tax calculated annually at year boundaries).
        If False, uses annual steps (tax calculated every step).
        Default is True.
    Returns
    -------
    np.array
        n x s+1 matrix of wealth.
    """

    n = simulated_returns.shape[0]  # number of simulations
    s = simulated_returns.shape[1]  # number of time steps
    k = simulated_returns.shape[2]  # number of assets
    
    wealth = np.zeros((n, s + 1))  # wealth array
    wealth[:, 0] = initial_wealth  # set initial wealth
    if time_steps is None:
        time_steps = np.arange(0, s + 1)  # time steps
    time_delta = np.diff(time_steps)  # time delta

    assert len(cashflows) == s, "Cashflows must be the same length as the number of time steps"
    assert len(transactions) == s, "Transactions must be the same length as the number of time steps"
    assert len(time_steps) == s + 1, "Time steps must be the same length as the number of time steps + 1"
    assert weights.shape[0] == s, "Weights first dimension must be the same length as the number of time steps"
    assert weights.shape[1] == k, "Weights second dimension must be the same length as the number of assets"
    assert len(time_delta) == s, "Time delta must be the same length as the number of time steps - 1"
    assert np.all(time_delta > 0), "Time steps must be in ascending order"
    assert np.all(np.isfinite(simulated_returns)), "Simulated returns must be finite"
    assert np.all(np.isfinite(weights)), "Weights must be finite"
    assert np.all(np.isfinite(cashflows)), "Cashflows must be finite"
    assert np.all(np.isfinite(transactions)), "Transactions must be finite"
    assert np.all(np.isfinite(initial_wealth)), "Initial wealth must be finite"
    assert np.all(np.isfinite(time_steps)), "Time steps must be finite"

    # For annual tax calculation: accumulate returns throughout the year, tax at year boundaries
    yearly_return_accumulator = np.zeros(n)  # Track accumulated returns for the current year
    
    inflation_factor = 1
    for i in range(s):
        inflation_factor *= (1 + inflation) ** time_delta[i]
        
        # Compute portfolio return factor
        portfolio_return_factor = (weights[i] * (1 + simulated_returns[:, i, :]) ** time_delta[i]).sum(axis=1)
        
        # Calculate return amount in dollar terms: wealth * (factor - 1)
        pre_tax_wealth = wealth[:, i] * portfolio_return_factor
        return_amount = pre_tax_wealth - wealth[:, i]  # Dollar return
        
        # Compute tax on this step's return (if tax model provided)
        tax_amount = np.zeros(n)  # Initialize tax array for all paths
        if tax_model is not None:
            if is_monthly:
                # Monthly steps: accumulate returns, tax at year boundaries
                yearly_return_accumulator += return_amount
                
                # Check if this is a year boundary (month 11 = December, or final step)
                is_year_end = (i % 12 == 11) or (i == s - 1)
                
                if is_year_end:
                    # Calculate tax on accumulated annual return
                    tax_amount = tax_model.calculate_tax(yearly_return_accumulator)
                    # Reset accumulator for next year
                    yearly_return_accumulator = np.zeros(n)
                # Otherwise, tax_amount remains 0 (no tax during the year)
            else:
                # Annual steps: tax every step (already at year boundaries)
                tax_amount = tax_model.calculate_tax(return_amount)
        
        # Apply wealth update with tax deduction
        wealth[:, i + 1] = (
            wealth[:, i] * portfolio_return_factor + 
            (cashflows[i] * time_delta[i] + transactions[i]) * inflation_factor -
            tax_amount * inflation_factor  # Subtract tax
        )
        wealth[wealth[:, i + 1] < 0, i + 1] = 0  # set negative wealth to 0

    return wealth

    # wealth = _compute_wealth_loop(
    #     wealth, 
    #     simulated_returns, 
    #     weights, 
    #     cashflows, 
    #     transactions,
    #     time_delta, 
    #     inflation, 
    #     s
    # )
    
    # return wealth


def convert_to_real_wealth(
    wealth: np.ndarray, time_steps: np.ndarray, inflation: float = 0.03, 
) -> np.array:
    """
    Convert wealth to real wealth using the inflation rate.
    Parameters
    ----------
    wealth : np.array
        n x s+1 matrix of wealth.
    inflation : float, optional
        Inflation rate. Default is 0.03.
    time_steps : np.array, optional
        s+1 x 1 vector of time steps. If None, will be set to np.arange(0, s + 1).
    Returns
    -------
    np.array
        n x s+1 matrix of real wealth.
    """
    assert np.all(np.isfinite(wealth)), "Wealth must be finite"
    assert np.all(np.isfinite(time_steps)), "Time steps must be finite"

    inflation_factor = (1 + inflation) ** time_steps
    return wealth / inflation_factor.reshape(1, -1)