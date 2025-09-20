"""Bollinger Bands Indicator.

This module provides the implementation of the Bollinger Bands indicator.
"""

from collections import deque
from dataclasses import dataclass
from math import sqrt

from nautilus_trader.model.data import Bar
from nautilus_trader_engine.indicators.base import Indicator, IndicatorConfig


@dataclass
class BBConfig(IndicatorConfig):
    """
    Configuration for the BollingerBands indicator.

    Args:
        period (int): The period for the moving average. Default is 20.
        std_dev (float): The number of standard deviations for the bands. Default is 2.0.
    """

    period: int = 20
    std_dev: float = 2.0


class BollingerBands(Indicator):
    """
    Bollinger Bands indicator.

    Calculates a middle band (simple moving average) and upper and lower bands
    that are a number of standard deviations above and below the middle band.
    """

    def __init__(self, config: BBConfig):
        super().__init__(config)
        self._prices = deque(maxlen=self.config.period)
        self._upper_band_values = deque(maxlen=self.config.buffer_size)
        self._middle_band_values = deque(maxlen=self.config.buffer_size)
        self._lower_band_values = deque(maxlen=self.config.buffer_size)

    @property
    def is_ready(self) -> bool:
        """Returns whether the indicator is ready to provide values."""
        return len(self._middle_band_values) > 0

    @property
    def upper_band(self) -> float:
        """Returns the last calculated upper band value."""
        return self._upper_band_values[-1] if self.is_ready else 0.0

    @property
    def middle_band(self) -> float:
        """Returns the last calculated middle band value."""
        return self._middle_band_values[-1] if self.is_ready else 0.0

    @property
    def lower_band(self) -> float:
        """Returns the last calculated lower band value."""
        return self._lower_band_values[-1] if self.is_ready else 0.0

    def handle_bar(self, bar: Bar):
        """
        Calculates the Bollinger Bands values for the given bar.

        Args:
            bar (Bar): The new aggregated bar.
        """
        self._prices.append(bar.close)

        if len(self._prices) == self.config.period:
            middle_band = sum(self._prices) / self.config.period
            variance = sum([(p - middle_band) ** 2 for p in self._prices]) / self.config.period
            std = sqrt(variance)
            upper_band = middle_band + (self.config.std_dev * std)
            lower_band = middle_band - (self.config.std_dev * std)

            self._upper_band_values.append(upper_band)
            self._middle_band_values.append(middle_band)
            self._lower_band_values.append(lower_band)

    def reset(self):
        """
        Resets the indicator to its initial state.
        """
        super().reset()
        self._prices.clear()
        self._upper_band_values.clear()
        self._middle_band_values.clear()
        self._lower_band_values.clear()