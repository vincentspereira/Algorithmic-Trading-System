# nautilus_trader_engine/rl/utils/performance_metrics.py

"""
Performance metrics for evaluating RL trading strategies.

This module provides functions to calculate various risk and return metrics
tailored for reinforcement learning-based trading systems.
"""

import numpy as np
import pandas as pd

def calculate_sharpe_ratio(
    returns: pd.Series, risk_free_rate: float = 0.0, annualization_factor: int = 252
) -> float:
    """Calculates the annualized Sharpe ratio."""
    mean_return = returns.mean()
    std_return = returns.std()
    if std_return == 0:
        return np.nan
    return (mean_return - risk_free_rate / annualization_factor) / std_return * np.sqrt(
        annualization_factor
    )

def calculate_sortino_ratio(
    returns: pd.Series, risk_free_rate: float = 0.0, annualization_factor: int = 252
) -> float:
    """Calculates the annualized Sortino ratio."""
    mean_return = returns.mean()
    downside_returns = returns[returns < 0]
    downside_std = downside_returns.std()
    if downside_std == 0:
        return np.nan
    return (mean_return - risk_free_rate / annualization_factor) / downside_std * np.sqrt(
        annualization_factor
    )

def calculate_max_drawdown(returns: pd.Series) -> float:
    """Calculates the maximum drawdown."""
    cumulative_returns = (1 + returns).cumprod()
    peak = cumulative_returns.expanding(min_periods=1).max()
    drawdown = (cumulative_returns - peak) / peak
    return drawdown.min()

def calculate_calmar_ratio(returns: pd.Series, annualization_factor: int = 252) -> float:
    """Calculates the Calmar ratio."""
    annual_return = returns.mean() * annualization_factor
    max_dd = calculate_max_drawdown(returns)
    if max_dd == 0:
        return np.nan
    return annual_return / abs(max_dd)

def get_performance_summary(portfolio_df: pd.DataFrame) -> dict:
    """
    Generates a summary of key performance metrics.

    Args:
        portfolio_df (pd.DataFrame): DataFrame with portfolio value and returns.

    Returns:
        A dictionary of performance metrics.
    """
    returns = portfolio_df["returns"].dropna()
    
    summary = {
        "sharpe_ratio": calculate_sharpe_ratio(returns),
        "sortino_ratio": calculate_sortino_ratio(returns),
        "max_drawdown": calculate_max_drawdown(returns),
        "calmar_ratio": calculate_calmar_ratio(returns),
        "total_return": (portfolio_df["portfolio_value"].iloc[-1] / portfolio_df["portfolio_value"].iloc[0]) - 1,
        "annualized_return": returns.mean() * 252,
        "annualized_volatility": returns.std() * np.sqrt(252),
    }
    
    return summary