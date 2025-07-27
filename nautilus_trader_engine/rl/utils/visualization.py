# nautilus_trader_engine/rl/utils/visualization.py

"""
Visualization tools for RL trading analysis.

This module provides functions to plot training progress, backtesting results,
and other relevant charts for evaluating RL strategies.
"""

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

def plot_portfolio_performance(
    portfolio_df: pd.DataFrame, title: str = "Portfolio Performance"
):
    """
    Plots the cumulative returns and drawdown of the portfolio.

    Args:
        portfolio_df (pd.DataFrame): DataFrame with portfolio performance data.
        title (str): The title of the plot.
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(12, 8))
    
    # Plot cumulative returns
    portfolio_df["cumulative_returns"].plot(ax=ax1, color="b")
    ax1.set_title(title)
    ax1.set_ylabel("Cumulative Returns")
    ax1.grid(True)
    
    # Plot drawdown
    drawdown = (portfolio_df["cumulative_returns"] + 1).div(
        (portfolio_df["cumulative_returns"] + 1).cummax()
    ) - 1
    drawdown.plot(ax=ax2, color="r")
    ax2.set_ylabel("Drawdown")
    ax2.grid(True)
    
    plt.xlabel("Date")
    plt.tight_layout()
    plt.show()

def plot_training_logs(log_df: pd.DataFrame, title: str = "Training Progress"):
    """
    Plots the training progress from Stable Baselines3 logs.

    Args:
        log_df (pd.DataFrame): DataFrame containing the training logs.
        title (str): The title of the plot.
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    
    log_df["rollout/ep_rew_mean"].plot(ax=ax, label="Mean Reward")
    ax.set_title(title)
    ax.set_xlabel("Timesteps")
    ax.set_ylabel("Mean Reward")
    ax.legend()
    ax.grid(True)
    
    plt.tight_layout()
    plt.show()

def plot_optuna_study(study):
    """
    Visualizes the results of an Optuna hyperparameter optimization study.
    """
    if study:
        fig1 = optuna.visualization.plot_optimization_history(study)
        fig1.show()
        
        fig2 = optuna.visualization.plot_param_importances(study)
        fig2.show()