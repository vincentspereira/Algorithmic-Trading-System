# nautilus_trader_engine/rl/utils/market_simulator.py

"""
Market simulator for RL training.

This module provides tools to simulate different market conditions,
such as varying volatility or market trends, to train more robust RL agents.
"""

import numpy as np
import pandas as pd

class MarketSimulator:
    """
    A simple market simulator that can generate synthetic market data or modify
    existing data to simulate different market scenarios.
    """

    def __init__(self, base_data: pd.DataFrame = None):
        self.base_data = base_data

    def generate_gbm_data(
        self,
        initial_price: float,
        mu: float,
        sigma: float,
        time_steps: int,
        dt: float = 1.0,
    ) -> pd.DataFrame:
        """
        Generates synthetic market data using a Geometric Brownian Motion (GBM) model.

        Args:
            initial_price (float): The starting price.
            mu (float): The drift (average rate of return).
            sigma (float): The volatility.
            time_steps (int): The number of time steps to simulate.
            dt (float): The time increment.

        Returns:
            A DataFrame with the simulated price series.
        """
        prices = [initial_price]
        for _ in range(1, time_steps):
            drift = mu * dt
            shock = sigma * np.random.normal(0, np.sqrt(dt))
            price_change = drift + shock
            prices.append(prices[-1] * (1 + price_change))

        return pd.DataFrame({"close": prices})

    def introduce_volatility_shock(
        self,
        volatility_factor: float,
        start_step: int,
        end_step: int,
    ) -> pd.DataFrame:
        """
        Introduces a volatility shock to the base data.

        Args:
            volatility_factor (float): The factor by which to increase volatility.
            start_step (int): The start of the shock period.
            end_step (int): The end of the shock period.

        Returns:
            A DataFrame with the modified price series.
        """
        if self.base_data is None:
            raise ValueError("Base data must be provided for this operation.")

        modified_data = self.base_data.copy()
        returns = modified_data["close"].pct_change()
        
        shock_period = returns.iloc[start_step:end_step]
        shocked_returns = shock_period * volatility_factor
        
        returns.iloc[start_step:end_step] = shocked_returns
        
        # Reconstruct prices from returns
        initial_price = modified_data["close"].iloc[0]
        modified_prices = [initial_price]
        for ret in returns.dropna():
            modified_prices.append(modified_prices[-1] * (1 + ret))
            
        modified_data["close"] = modified_prices
        return modified_data