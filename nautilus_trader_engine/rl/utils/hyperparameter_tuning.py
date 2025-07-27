# nautilus_trader_engine/rl/utils/hyperparameter_tuning.py

"""
Hyperparameter tuning for RL agents using Optuna.

This module provides functions to define search spaces and sample hyperparameters
for different RL agents, facilitating automated optimization.
"""

from typing import Dict, Any
import optuna

def sample_ppo_hyperparams(trial: optuna.Trial) -> Dict[str, Any]:
    """
    Samples hyperparameters for the PPO agent.
    """
    return {
        "n_steps": trial.suggest_int("n_steps", 256, 4096, step=256),
        "gamma": trial.suggest_float("gamma", 0.9, 0.9999, log=True),
        "learning_rate": trial.suggest_float("learning_rate", 1e-5, 1e-3, log=True),
        "clip_range": trial.suggest_float("clip_range", 0.1, 0.4, step=0.1),
        "ent_coef": trial.suggest_float("ent_coef", 0.0, 0.1, step=0.01),
    }

def sample_sac_hyperparams(trial: optuna.Trial) -> Dict[str, Any]:
    """
    Samples hyperparameters for the SAC agent.
    """
    return {
        "gamma": trial.suggest_float("gamma", 0.9, 0.9999, log=True),
        "learning_rate": trial.suggest_float("learning_rate", 1e-5, 1e-3, log=True),
        "batch_size": trial.suggest_categorical("batch_size", [128, 256, 512, 1024]),
        "buffer_size": trial.suggest_int("buffer_size", 100_000, 1_000_000),
        "tau": trial.suggest_float("tau", 0.001, 0.02, step=0.001),
    }

def sample_a2c_hyperparams(trial: optuna.Trial) -> Dict[str, Any]:
    """
    Samples hyperparameters for the A2C agent.
    """
    return {
        "n_steps": trial.suggest_int("n_steps", 5, 50, step=5),
        "gamma": trial.suggest_float("gamma", 0.9, 0.99),
        "learning_rate": trial.suggest_float("learning_rate", 1e-5, 1e-3, log=True),
        "vf_coef": trial.suggest_float("vf_coef", 0.1, 1.0),
        "ent_coef": trial.suggest_float("ent_coef", 0.0, 0.1),
    }

def sample_ddpg_hyperparams(trial: optuna.Trial) -> Dict[str, Any]:
    """
    Samples hyperparameters for the DDPG agent.
    """
    return {
        "gamma": trial.suggest_float("gamma", 0.9, 0.9999, log=True),
        "learning_rate": trial.suggest_float("learning_rate", 1e-5, 1e-3, log=True),
        "batch_size": trial.suggest_categorical("batch_size", [128, 256, 512]),
        "buffer_size": trial.suggest_int("buffer_size", 100_000, 1_000_000),
        "tau": trial.suggest_float("tau", 0.001, 0.02),
    }

def sample_hyperparams(trial: optuna.Trial, agent_name: str) -> Dict[str, Any]:
    """
    Samples hyperparameters for a given agent.

    Args:
        trial (optuna.Trial): The Optuna trial object.
        agent_name (str): The name of the agent.

    Returns:
        A dictionary of sampled hyperparameters.
    """
    agent_name = agent_name.upper()
    if agent_name == "PPO":
        return sample_ppo_hyperparams(trial)
    elif agent_name == "SAC":
        return sample_sac_hyperparams(trial)
    elif agent_name == "A2C":
        return sample_a2c_hyperparams(trial)
    elif agent_name == "DDPG":
        return sample_ddpg_hyperparams(trial)
    else:
        raise ValueError(f"Unknown agent: {agent_name}")