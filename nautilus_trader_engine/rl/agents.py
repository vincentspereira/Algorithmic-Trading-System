# nautilus_trader_engine/rl/agents.py

"""
RL agents for trading, leveraging the Stable Baselines3 library.

This module provides a factory function to create and configure various reinforcement
learning agents (PPO, A2C, DDPG, SAC) for use in the trading environment.
"""

from typing import Type
from stable_baselines3 import PPO, A2C, DDPG, SAC
from stable_baselines3.common.base_class import BaseAlgorithm

from nautilus_trader_engine.rl.finrl_config import HYPERPARAMS
from nautilus_trader_engine.rl.environment import NautilusTradingEnv


def get_agent(agent_name: str, env: NautilusTradingEnv, **kwargs) -> BaseAlgorithm:
    """
    Factory function to get a Stable Baselines3 agent by name.

    Args:
        agent_name (str): The name of the agent (e.g., "PPO", "A2C").
        env (NautilusTradingEnv): The trading environment.
        **kwargs: Additional hyperparameters to override the defaults.

    Returns:
        An instance of the specified RL agent.

    Raises:
        ValueError: If the agent_name is not supported.
    """
    agent_map = {
        "PPO": PPO,
        "A2C": A2C,
        "DDPG": DDPG,
        "SAC": SAC,
    }

    if agent_name.upper() not in agent_map:
        raise ValueError(f"Agent '{agent_name}' not supported. Choose from {list(agent_map.keys())}")

    agent_class: Type[BaseAlgorithm] = agent_map[agent_name.upper()]
    agent_params = HYPERPARAMS.get(agent_name.upper(), {}).copy()
    agent_params.update(kwargs)

    # Determine the policy based on the environment's observation space
    # This example assumes a MultiInputPolicy for dictionary observations,
    # but adjust as needed based on your environment's observation space structure.
    policy = "MlpPolicy"
    
    return agent_class(policy, env, **agent_params)


def train_agent(
    agent: BaseAlgorithm,
    total_timesteps: int,
    log_interval: int = 1,
    **kwargs,
):
    """
    Trains the given RL agent.

    Args:
        agent (BaseAlgorithm): The RL agent to train.
        total_timesteps (int): The total number of steps to train for.
        log_interval (int): a log every `log_interval` episodes.
        **kwargs: Additional arguments for the learn method.
    """
    agent.learn(
        total_timesteps=total_timesteps,
        log_interval=log_interval,
        **kwargs,
    )
    return agent


def save_agent(agent: BaseAlgorithm, path: str):
    """
    Saves the trained agent to a file.

    Args:
        agent (BaseAlgorithm): The agent to save.
        path (str): The file path to save the agent to.
    """
    agent.save(path)


def load_agent(agent_name: str, path: str, env: NautilusTradingEnv) -> BaseAlgorithm:
    """
    Loads a trained agent from a file.

    Args:
        agent_name (str): The name of the agent.
        path (str): The file path to load the agent from.
        env (NautilusTradingEnv): The trading environment.

    Returns:
        The loaded RL agent.
    """
    agent_map = {
        "PPO": PPO,
        "A2C": A2C,
        "DDPG": DDPG,
        "SAC": SAC,
    }
    agent_class = agent_map[agent_name.upper()]
    return agent_class.load(path, env=env)