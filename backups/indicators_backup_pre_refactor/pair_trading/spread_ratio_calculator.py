"""Module for calculating spread and ratio metrics for pairs trading."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .data_models.data_models import PairData, SpreadRatioData


class SpreadRatioCalculator:
    """Calculate spread and ratio metrics for pairs trading."""

    def __init__(self):
        self.epsilon = 1e-8  # Small value to avoid division by zero

    def calculate_spread_ratio(self, pair_data: PairData) -> SpreadRatioData:
        """Calculate all spread and ratio metrics."""
        # Basic spread calculations
        spread_open = pair_data.open_a - pair_data.open_b
        spread_high = pair_data.high_a - pair_data.high_b
        spread_low = pair_data.low_a - pair_data.low_b
        spread_close = pair_data.close_a - pair_data.close_b
        spread_volume = pair_data.volume_a + pair_data.volume_b

        # Basic ratio calculations (avoid division by zero)
        ratio_open = np.divide(pair_data.open_a, pair_data.open_b + self.epsilon)
        ratio_high = np.divide(pair_data.high_a, pair_data.high_b + self.epsilon)
        ratio_low = np.divide(pair_data.low_a, pair_data.low_b + self.epsilon)
        ratio_close = np.divide(pair_data.close_a, pair_data.close_b + self.epsilon)
        ratio_volume = np.divide(pair_data.volume_a, pair_data.volume_b + self.epsilon)

        # Volume-weighted calculations
        total_volume = pair_data.volume_a + pair_data.volume_b + self.epsilon
        vw_price_a = (pair_data.close_a * pair_data.volume_a) / total_volume
        vw_price_b = (pair_data.close_b * pair_data.volume_b) / total_volume

        vw_spread_close = vw_price_a - vw_price_b
        vw_ratio_close = np.divide(vw_price_a, vw_price_b + self.epsilon)

        # Log ratio for better statistical properties
        log_ratio_close = np.log(ratio_close + self.epsilon)

        return SpreadRatioData(
            spread_open=spread_open,
            spread_high=spread_high,
            spread_low=spread_low,
            spread_close=spread_close,
            spread_volume=spread_volume,
            ratio_open=ratio_open,
            ratio_high=ratio_high,
            ratio_low=ratio_low,
            ratio_close=ratio_close,
            ratio_volume=ratio_volume,
            vw_spread_close=vw_spread_close,
            vw_ratio_close=vw_ratio_close,
            log_ratio_close=log_ratio_close,
        )

    def calculate_beta_adjusted_spread(
        self, pair_data: PairData, lookback: int = 252
    ) -> np.ndarray:
        """Calculate beta-adjusted spread for better neutrality."""
        beta = self._calculate_rolling_beta(
            pair_data.close_a, pair_data.close_b, lookback
        )
        return pair_data.close_a - (beta * pair_data.close_b)

    def _calculate_rolling_beta(
        self, price_a: np.ndarray, price_b: np.ndarray, window: int
    ) -> np.ndarray:
        """Calculate rolling beta between two price series."""
        returns_a = np.diff(np.log(price_a + self.epsilon))
        returns_b = np.diff(np.log(price_b + self.epsilon))

        beta = np.full(len(price_a), np.nan)

        for i in range(window, len(returns_a)):
            y = returns_a[i - window : i]
            x = returns_b[i - window : i]

            if len(x) > 0 and len(y) > 0:
                covariance = np.cov(x, y)[0, 1]
                variance = np.var(x)
                beta[i + 1] = covariance / (variance + self.epsilon)

        # Forward fill NaN values
        beta = pd.Series(beta).fillna(method="ffill").values
        return beta