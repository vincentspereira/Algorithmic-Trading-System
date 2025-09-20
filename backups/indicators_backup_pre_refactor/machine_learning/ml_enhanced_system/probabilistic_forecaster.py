import logging
from typing import Dict, List, Tuple

import numpy as np

from .data_models import MarketRegime, ProbabilisticForecast

logger = logging.getLogger(__name__)


class ProbabilisticForecaster:
    """Generates probabilistic forecasts based on market regime"""

    def __init__(self, forecast_horizon: int = 10, num_simulations: int = 1000):
        self.forecast_horizon = forecast_horizon
        self.num_simulations = num_simulations

    def generate_forecast(
        self, current_price: float, regime: MarketRegime, volatility: float
    ) -> ProbabilisticForecast:
        """Generate a probabilistic price forecast"""
        mu, sigma = self._estimate_regime_parameters(regime, volatility)

        simulations = self._monte_carlo_simulation(current_price, mu, sigma)

        mean_forecast = np.mean(simulations[:, -1])
        median_forecast = np.median(simulations[:, -1])

        confidence_interval = (
            np.percentile(simulations[:, -1], 5),
            np.percentile(simulations[:, -1], 95),
        )

        prob_above, prob_below = self._calculate_probabilities(
            current_price, simulations[:, -1]
        )

        return ProbabilisticForecast(
            mean_forecast=mean_forecast,
            median_forecast=median_forecast,
            confidence_interval_5th=confidence_interval[0],
            confidence_interval_95th=confidence_interval[1],
            probability_price_increase=prob_above,
            probability_price_decrease=prob_below,
            forecast_horizon=self.forecast_horizon,
            simulations=simulations,  # Optional: for more detailed analysis
        )

    def _estimate_regime_parameters(
        self, regime: MarketRegime, volatility: float
    ) -> Tuple[float, float]:
        """Estimate drift (mu) and volatility (sigma) based on regime"""
        base_drift = 0.0001  # Small default drift

        if regime == MarketRegime.TRENDING_UP:
            mu = base_drift + volatility * 0.5
        elif regime == MarketRegime.TRENDING_DOWN:
            mu = -base_drift - volatility * 0.5
        elif regime == MarketRegime.HIGH_VOLATILITY:
            mu = 0
        else:  # Ranging, low volatility, etc.
            mu = 0

        sigma = volatility * 1.2  # Scale volatility for simulation
        return mu, sigma

    def _monte_carlo_simulation(
        self, start_price: float, mu: float, sigma: float
    ) -> np.ndarray:
        """Run Monte Carlo simulation for price paths"""
        dt = 1  # Time step (1 bar)
        price_paths = np.zeros((self.num_simulations, self.forecast_horizon + 1))
        price_paths[:, 0] = start_price

        for t in range(1, self.forecast_horizon + 1):
            z = np.random.standard_normal(self.num_simulations)
            price_paths[:, t] = price_paths[:, t - 1] * np.exp(
                (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * z
            )

        return price_paths

    def _calculate_probabilities(
        self, current_price: float, final_prices: np.ndarray
    ) -> Tuple[float, float]:
        """Calculate probabilities of price movements"""
        prob_above = np.sum(final_prices > current_price) / self.num_simulations
        prob_below = np.sum(final_prices < current_price) / self.num_simulations
        return prob_above, prob_below

    def get_scenario_probabilities(
        self, scenarios: Dict[str, float], forecast: ProbabilisticForecast
    ) -> Dict[str, float]:
        """Calculate probabilities for custom price scenarios"""
        final_prices = forecast.simulations[:, -1]
        scenario_probs = {}

        for name, target_price in scenarios.items():
            if "above" in name.lower():
                prob = np.sum(final_prices > target_price) / self.num_simulations
            elif "below" in name.lower():
                prob = np.sum(final_prices < target_price) / self.num_simulations
            else:
                # Default to probability of exceeding the target
                prob = np.sum(final_prices > target_price) / self.num_simulations
            scenario_probs[name] = prob

        return scenario_probs