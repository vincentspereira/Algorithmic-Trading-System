# nautilus_trader_engine/rl/training/model_trainer.py

"""
RL model training and hyperparameter optimization.

This module provides a training pipeline for RL agents, including a training
loop, hyperparameter tuning with Optuna, and model evaluation.
"""

import optuna
from stable_baselines3.common.callbacks import EvalCallback
from stable_baselines3.common.monitor import Monitor

from nautilus_trader_engine.rl.agents import get_agent, train_agent, save_agent
from nautilus_trader_engine.rl.environment import NautilusTradingEnv
from nautilus_trader_engine.rl.finrl_config import (
    TRAINING_CONFIG,
    HYPERPARAMS,
)
from nautilus_trader_engine.rl.utils.hyperparameter_tuning import (
    sample_hyperparams,
)


class ModelTrainer:
    """
    Coordinates the training, evaluation, and hyperparameter tuning of RL models.
    """

    def __init__(
        self,
        env: NautilusTradingEnv,
        eval_env: NautilusTradingEnv,
        agent_name: str,
        model_dir: str = "trained_models",
    ):
        self.env = Monitor(env)
        self.eval_env = Monitor(eval_env)
        self.agent_name = agent_name
        self.model_dir = model_dir

    def run_training_pipeline(self, total_timesteps: int = TRAINING_CONFIG["total_timesteps"]):
        """
        Executes the full training pipeline with default hyperparameters.
        """
        agent = get_agent(self.agent_name, self.env)

        eval_callback = EvalCallback(
            self.eval_env,
            best_model_save_path=f"{self.model_dir}/{self.agent_name}_best",
            log_path=f"{self.model_dir}/{self.agent_name}_logs",
            eval_freq=TRAINING_CONFIG["eval_freq"],
            n_eval_episodes=TRAINING_CONFIG["n_eval_episodes"],
            deterministic=TRAINING_CONFIG["deterministic_eval"],
            render=False,
        )

        trained_agent = train_agent(
            agent,
            total_timesteps,
            callback=eval_callback,
        )

        save_path = f"{self.model_dir}/{self.agent_name}_final.zip"
        save_agent(trained_agent, save_path)
        print(f"Final model saved to {save_path}")

        return trained_agent

    def optimize_hyperparameters(
        self,
        n_trials: int = 50,
        n_timesteps: int = 20_000,
    ) -> optuna.study.Study:
        """
        Performs hyperparameter optimization using Optuna.
        """
        study = optuna.create_study(direction="maximize")
        study.optimize(
            lambda trial: self._objective(trial, n_timesteps),
            n_trials=n_trials,
        )
        print("Best hyperparameters: ", study.best_params)
        return study

    def _objective(self, trial: optuna.Trial, n_timesteps: int) -> float:
        """
        The objective function for Optuna optimization.
        """
        hyperparams = sample_hyperparams(trial, self.agent_name)
        agent = get_agent(self.agent_name, self.env, **hyperparams)

        eval_callback = EvalCallback(
            self.eval_env,
            eval_freq=5000,
            n_eval_episodes=5,
            deterministic=True,
            render=False,
        )

        agent.learn(total_timesteps=n_timesteps, callback=eval_callback)

        # The objective value is the mean reward of the last evaluation
        mean_reward = eval_callback.best_mean_reward

        return mean_reward