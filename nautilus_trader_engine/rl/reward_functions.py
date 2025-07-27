# nautilus_trader_engine/rl/reward_functions.py

"""
Reward functions for the RL trading environment.

These functions calculate a scalar reward signal based on the performance of the
trading agent, which is used to guide the learning process.
"""

import numpy as np
import pandas as pd

from nautilus_trader_engine.rl.environment import NautilusTradingEnv
from nautilus_trader_engine.rl.finrl_config import REWARD_FUNCTION_CONFIG


def get_reward_function(name: str, **kwargs):
    """
    Factory function to get a reward function by name.

    Args:
        name (str): The name of the reward function.
        **kwargs: Additional parameters for the reward function.

    Returns:
        A callable reward function.
    """
    reward_functions = {
        "profit": profit_reward,
        "sharpe_ratio": sharpe_ratio_reward,
        "sortino_ratio": sortino_ratio_reward,
    }

    if name not in reward_functions:
        raise ValueError(
            f"Reward function '{name}' not supported. "
            f"Choose from {list(reward_functions.keys())}"
        )

    config = REWARD_FUNCTION_CONFIG["options"].get(name, {})
    config.update(kwargs)

    return lambda env: reward_functions[name](env, **config)


def profit_reward(env: NautilusTradingEnv, risk_aversion: float = 0.5) -> float:
    """
    Calculates reward based on realized and unrealized profit, with a penalty
    for risk.

    Args:
        env (NautilusTradingEnv): The trading environment.
        risk_aversion (float): a penalty for holding open positions.

    Returns:
        The calculated profit-based reward.
    """
    portfolio_value = env._get_info()["portfolio_value"]
    previous_portfolio_value = getattr(env, "previous_portfolio_value", portfolio_value)

    profit = portfolio_value - previous_portfolio_value
    
    # Simple risk aversion: penalize for holding large positions
    position_value = sum(p.value for p in env._get_info()["positions"])
    risk_penalty = risk_aversion * (position_value / portfolio_value)

    reward = profit - risk_penalty

    # Store current portfolio value for the next step
    env.previous_portfolio_value = portfolio_value

    return reward


def sharpe_ratio_reward(
    env: NautilusTradingEnv,
    risk_free_rate: float = 0.02,
    annualization_factor: int = 252,
) -> float:
    """
    Calculates reward based on the Sharpe ratio of portfolio returns.

    Args:
        env (NautilusTradingEnv): The trading environment.
        risk_free_rate (float): The risk-free rate of return.
        annualization_factor (int): The number of periods in a year.

    Returns:
        The calculated Sharpe ratio-based reward.
    """
    # This is a simplified example. A proper implementation would track returns
    # over a period to calculate the Sharpe ratio.
    returns = _calculate_returns(env)
    if len(returns) < 2:
        return 0.0

    mean_return = np.mean(returns)
    std_return = np.std(returns)

    if std_return == 0:
        return 0.0

    sharpe_ratio = (mean_return - risk_free_rate / annualization_factor) / std_return
    return sharpe_ratio * np.sqrt(annualization_factor)


def sortino_ratio_reward(
    env: NautilusTradingEnv,
    risk_free_rate: float = 0.02,
    annualization_factor: int = 252,
) -> float:
    """
    Calculates reward based on the Sortino ratio of portfolio returns.

    Args:
        env (NautilusTradingEnv): The trading environment.
        risk_free_rate (float): The risk-free rate of return.
        annualization_factor (int): The number of periods in a year.

    Returns:
        The calculated Sortino ratio-based reward.
    """
    returns = _calculate_returns(env)
    if len(returns) < 2:
        return 0.0

    mean_return = np.mean(returns)
    negative_returns = returns[returns < 0]
    downside_std = np.std(negative_returns)

    if downside_std == 0:
        return 0.0

    sortino_ratio = (mean_return - risk_free_rate / annualization_factor) / downside_std
    return sortino_ratio * np.sqrt(annualization_factor)


def _calculate_returns(env: NautilusTradingEnv) -> np.ndarray:
    """Helper function to calculate portfolio returns."""
    portfolio_value = env._get_info()["portfolio_value"]
    
    if not hasattr(env, "portfolio_history"):
        env.portfolio_history = [portfolio_value]
        return np.array([])
        
    env.portfolio_history.append(portfolio_value)
    
    returns = pd.Series(env.portfolio_history).pct_change().dropna().values
    return returns