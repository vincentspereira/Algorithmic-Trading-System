"""Module for providing a comprehensive suite of technical indicators for pairs trading."""
from __future__ import annotations

from typing import Tuple

import numpy as np
import talib
from sklearn.linear_model import LinearRegression


class PairsIndicatorSuite:
    """Comprehensive technical indicators for pairs trading."""

    def __init__(self):
        self.epsilon = 1e-8

    def spread_sma(self, spread: np.ndarray, period: int = 20) -> np.ndarray:
        """Simple Moving Average of spread."""
        return talib.SMA(spread, timeperiod=period)

    def spread_ema(self, spread: np.ndarray, period: int = 20) -> np.ndarray:
        """Exponential Moving Average of spread."""
        return talib.EMA(spread, timeperiod=period)

    def spread_rsi(self, spread: np.ndarray, period: int = 14) -> np.ndarray:
        """RSI applied to spread data."""
        return talib.RSI(spread, timeperiod=period)

    def spread_macd(
        self, spread: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """MACD applied to spread data."""
        macd, signal_line, histogram = talib.MACD(
            spread, fastperiod=fast, slowperiod=slow, signalperiod=signal
        )
        return macd, signal_line, histogram

    def spread_bollinger_bands(
        self, spread: np.ndarray, period: int = 20, std_dev: float = 2.0
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Bollinger Bands for spread."""
        upper, middle, lower = talib.BBANDS(
            spread, timeperiod=period, nbdevup=std_dev, nbdevdn=std_dev
        )
        return upper, middle, lower

    def spread_atr(
        self, spread_high: np.ndarray, spread_low: np.ndarray, spread_close: np.ndarray, period: int = 14
    ) -> np.ndarray:
        """Average True Range for spread volatility."""
        return talib.ATR(spread_high, spread_low, spread_close, timeperiod=period)

    def ratio_momentum(self, ratio: np.ndarray, period: int = 10) -> np.ndarray:
        """Momentum indicator for ratio."""
        return talib.MOM(ratio, timeperiod=period)

    def ratio_stochastic(
        self, ratio_high: np.ndarray, ratio_low: np.ndarray, ratio_close: np.ndarray, k_period: int = 14, d_period: int = 3
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Stochastic oscillator for ratio."""
        k_percent, d_percent = talib.STOCH(
            ratio_high, ratio_low, ratio_close, fastk_period=k_period, slowk_period=d_period, slowd_period=d_period
        )
        return k_percent, d_percent

    def volume_weighted_spread_indicator(
        self, spread: np.ndarray, volume: np.ndarray, period: int = 20
    ) -> np.ndarray:
        """Volume-weighted moving average of spread."""
        vw_sum = np.convolve(spread * volume, np.ones(period), mode="same")
        volume_sum = np.convolve(volume, np.ones(period), mode="same")
        return np.divide(vw_sum, volume_sum + self.epsilon)

    def spread_z_score(self, spread: np.ndarray, period: int = 252) -> np.ndarray:
        """Z-score normalization of spread."""
        rolling_mean = talib.SMA(spread, timeperiod=period)
        rolling_std = talib.STDDEV(spread, timeperiod=period)
        return np.divide(spread - rolling_mean, rolling_std + self.epsilon)

    def cointegration_residual_indicator(
        self, price_a: np.ndarray, price_b: np.ndarray, period: int = 252
    ) -> np.ndarray:
        """Rolling cointegration residual as indicator."""
        residuals = np.full(len(price_a), np.nan)

        for i in range(period, len(price_a)):
            y = price_a[i - period : i]
            x = price_b[i - period : i].reshape(-1, 1)

            if len(x) > 0 and len(y) > 0:
                model = LinearRegression().fit(x, y)
                predicted = model.predict(x)
                residuals[i] = y[-1] - predicted[-1]

        return residuals

    def half_life_indicator(self, spread: np.ndarray, period: int = 252) -> np.ndarray:
        """Rolling half-life of mean reversion."""
        half_lives = np.full(len(spread), np.nan)

        for i in range(period, len(spread)):
            series = spread[i - period : i]
            lagged = series[:-1]
            changes = np.diff(series)

            if len(lagged) > 0 and len(changes) > 0:
                try:
                    model = LinearRegression().fit(lagged.reshape(-1, 1), changes)
                    lambda_coef = model.coef_[0]
                    if lambda_coef < 0:
                        half_lives[i] = -np.log(2) / lambda_coef
                except:
                    half_lives[i] = np.nan

        return half_lives