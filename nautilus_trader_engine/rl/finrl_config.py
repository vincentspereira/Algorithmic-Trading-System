# nautilus_trader_engine/rl/finrl_config.py

"""
Configuration settings for FinRL integration, including environment parameters,
agent hyperparameters, and other RL-related settings.
"""

import gymnasium as gym

# Default hyperparameters for RL agents
# These can be overridden by specific training configurations
HYPERPARAMS = {
    "PPO": {
        "learning_rate": 0.0003,
        "n_steps": 2048,
        "batch_size": 64,
        "n_epochs": 10,
        "gamma": 0.99,
        "gae_lambda": 0.95,
        "clip_range": 0.2,
        "ent_coef": 0.0,
        "verbose": 0,
    },
    "A2C": {
        "learning_rate": 0.0007,
        "n_steps": 5,
        "gamma": 0.99,
        "gae_lambda": 1.0,
        "ent_coef": 0.0,
        "vf_coef": 0.5,
        "max_grad_norm": 0.5,
        "verbose": 0,
    },
    "DDPG": {
        "learning_rate": 0.001,
        "buffer_size": 1_000_000,
        "learning_starts": 100,
        "batch_size": 256,
        "tau": 0.005,
        "gamma": 0.99,
        "verbose": 0,
    },
    "SAC": {
        "learning_rate": 0.0003,
        "buffer_size": 1_000_000,
        "learning_starts": 100,
        "batch_size": 256,
        "tau": 0.005,
        "gamma": 0.99,
        "verbose": 0,
    },
}

# Environment configuration
# Defines the action and observation spaces, and other environment-specific settings
ENV_CONFIG = {
    "initial_balance": 100_000,
    "commission_pct": 0.001,
    "max_episode_duration": "1Y",  # e.g., '1Y', '6M', '30D'
    "window_size": 30,  # Number of past time steps to include in the observation
}

# Action space configuration
# DISCRETE: Buy, Sell, Hold
# CONTINUOUS: Amount to buy/sell (-1.0 to 1.0)
ACTION_SPACE_CONFIG = {
    "type": "discrete",  # "discrete" or "continuous"
    "discrete": {
        "n": 3,  # 0: Hold, 1: Buy, 2: Sell
    },
    "continuous": {
        "low": -1.0,
        "high": 1.0,
        "shape": (1,),
    },
}

# Observation space configuration
# Defines the features that the RL agent will use to make decisions
# Example features: 'close', 'volume', 'sma_30', 'rsi_14'
OBSERVATION_SPACE_FEATURES = [
    "close",
    "volume",
    "sma_30",
    "ema_14",
    "rsi_14",
    "macd",
    "bbands_upper",
    "bbands_lower",
]

# Reward function configuration
REWARD_FUNCTION_CONFIG = {
    "default": "sharpe_ratio",
    "options": {
        "profit": {"risk_aversion": 0.5},
        "sharpe_ratio": {"risk_free_rate": 0.02, "annualization_factor": 252},
        "sortino_ratio": {"risk_free_rate": 0.02, "annualization_factor": 252},
    },
}

# Training configuration
TRAINING_CONFIG = {
    "total_timesteps": 100_000,
    "log_interval": 1,
    "eval_freq": 20000,
    "n_eval_episodes": 5,
    "deterministic_eval": True,
}

# Backtesting configuration
BACKTESTING_CONFIG = {
    "start_date": "2022-01-01",
    "end_date": "2023-01-01",
    "capital_base": 100_000,
}