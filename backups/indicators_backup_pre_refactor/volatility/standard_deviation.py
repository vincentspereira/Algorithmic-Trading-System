"""Standard Deviation Indicator.

This module provides an implementation of the Standard Deviation indicator.
"""

from collections import deque
from dataclasses import dataclass
import numpy as np

from nautilus_trader.model.data import Bar
from nautilus_trader_engine.indicators.base import Indicator, IndicatorConfig


@dataclass
class StandardDeviationConfig(IndicatorConfig):
    """
    Configuration for the Standard Deviation indicator.

    Args:
        period (int): The period for the standard deviation calculation.
    """
    period: int


class StandardDeviation(Indicator):
    """
    Standard Deviation is a statistical measure of market volatility.
    """

    def __init__(self, config: StandardDeviationConfig):
        super().__init__(config)
        self._prices = deque(maxlen=self.config.period)
        self._std_dev_values = deque(maxlen=self.config.period)

    @property
    def is_ready(self) -> bool:
        return len(self._prices) == self.config.period

    @property
    def value(self) -> float:
        """Returns the last calculated standard deviation value."""
        return self._std_dev_values[-1] if self.is_ready else 0.0

    def handle_bar(self, bar: Bar):
        self._prices.append(bar.close)

        if self.is_ready:
            std_dev = np.std(self._prices, ddof=1)
            self._std_dev_values.append(std_dev)

    def reset(self):
        super().reset()
        self._prices.clear()
        self._std_dev_values.clear()