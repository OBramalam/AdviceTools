import os
import pandas as pd
import numpy as np
from functools import cache
from .common.enums import SimulationStepType

DATA_DIR = "../data"

this_dir = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(this_dir, DATA_DIR)

@cache
def load_historical_returns_header() -> pd.Series:
    """
    Load the header of the historical returns file.
    Returns
    -------
    pd.Series
        Series containing the header of the historical returns file.
    """
    file_path = os.path.join(DATA_DIR, "returns.csv")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    df = pd.read_csv(file_path, header=0)
    header = df.columns[1:]
    return pd.Series(header, name="Assets")
    

@cache
def load_historical_returns(step_type: SimulationStepType = SimulationStepType.MONTHLY) -> pd.DataFrame:
    """
    Load historical returns from the data directory.
    Returns
    -------
    pd.DataFrame
        DataFrame containing historical returns.
    """
    file_path = os.path.join(DATA_DIR, "returns.csv")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    returns = pd.read_csv(file_path, index_col=0, parse_dates=True, header=0)
    returns.index.name = "Date"
    match step_type:
        case SimulationStepType.MONTHLY:
            pass # Monthly returns are already in the correct format
        case SimulationStepType.ANNUAL:
            returns = returns.resample("YE").apply(lambda x: (1 + x).prod() - 1)
            returns = returns.dropna()
    return returns


def get_cov_from_returns(returns: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate the covariance matrix from historical returns.
    Parameters
    ----------
    returns : pd.DataFrame
        DataFrame containing historical returns.

    Returns
    -------
    pd.DataFrame
        Covariance matrix of the returns.
    """
    if returns.empty:
        raise ValueError("The input DataFrame is empty.")
    
    cov_matrix = returns.dropna().cov()
    return cov_matrix


@cache
def get_historical_cov(step_type: SimulationStepType = SimulationStepType.MONTHLY) -> pd.DataFrame:
    """
    Get the covariance matrix of historical returns.
    Returns
    -------
    pd.DataFrame
        Covariance matrix of historical returns.
    """
    returns = load_historical_returns(step_type=step_type)
    return get_cov_from_returns(returns)


@cache
def get_historical_exp_ret(step_type: SimulationStepType = SimulationStepType.MONTHLY) -> pd.DataFrame:
    """
    Get the expected returns from historical returns.
    Returns
    -------
    pd.DataFrame
        Expected returns of historical returns.
    """
    returns = load_historical_returns(step_type=step_type)
    exp_ret = returns.mean()
    return exp_ret.to_frame(name="Expected Return")


@cache
def get_historical_vol(step_type: SimulationStepType = SimulationStepType.MONTHLY) -> pd.DataFrame:
    """
    Get the historical volatility from historical returns.
    Returns
    -------
    pd.DataFrame
        Historical volatility of returns.
    """
    returns = load_historical_returns()
    vol = returns.std()
    match step_type:
        case SimulationStepType.MONTHLY:
            pass 
        case SimulationStepType.ANNUAL:
            vol = vol * np.sqrt(12)
    return vol.to_frame(name="Historical Volatility")