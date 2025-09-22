"""Choppiness Index Indicator.
"""
from collections import deque
from dataclasses import dataclass
import math

import numpy as np
from nautilus_trader.model.data import Bar

from nautilus_trader_engine.indicators.base import Indicator, IndicatorConfig
from nautilus_trader_engine.indicators.volatility.atr import ATR, ATRConfig


@dataclass
class ChoppinessIndexConfig(IndicatorConfig):
    """
    Configuration for the ChoppinessIndex indicator.

    Args:
        period (int): The period for the index calculation. Default is 14.
    """
    period: int = 14


class ChoppinessIndex(Indicator):
    """
    Choppiness Index indicator.

    Measures the "choppiness" or trendiness of the market. A higher value
    indicates a choppy, sideways market, while a lower value suggests a
    trending market.
    """

    def __init__(self, config: ChoppinessIndexConfig):
        super().__init__(config)
        self._highs = deque(maxlen=self.config.period)
        self._lows = deque(maxlen=self.config.period)
        atr_config = ATRConfig(period=1)  # ATR period of 1 for summing true ranges
        self._atr = ATR(config=atr_config)
        self._true_ranges = deque(maxlen=self.config.period)
        self._ci_values = deque(maxlen=self.config.buffer_size)

    @property
    def choppiness_index(self) -> float:
        """Returns the last calculated choppiness index value."""
        return self._ci_values[-1] if self.is_ready else 0.0

    @property
    def is_ready(self) -> bool:
        """Returns whether the indicator is ready to provide values."""
        return len(self._ci_values) > 0

    def handle_bar(self, bar: Bar):
        """
        Calculate Choppiness Index for the given bar.
        """
        self._highs.append(bar.high)
        self._lows.append(bar.low)
        self._atr.handle_bar(bar)

        if self._atr.is_ready:
            self._true_ranges.append(self._atr.atr)

        if len(self._highs) == self.config.period and len(self._true_ranges) == self.config.period:
            highest_high = np.max(self._highs)
            lowest_low = np.min(self._lows)
            atr_sum = np.sum(self._true_ranges)

            if atr_sum > 0 and highest_high > lowest_low:
                log10_period = math.log10(self.config.period)
                choppiness = 100 * math.log10(atr_sum / (highest_high - lowest_low)) / log10_period
                self._ci_values.append(choppiness)
            else:
                self._ci_values.append(self._ci_values[-1] if self.is_ready else 50.0)

    def reset(self):
        """
        Reset the state of the indicator.
        """
        super().reset()
        self._highs.clear()
        self._lows.clear()
        self._atr.reset()
        self._true_ranges.clear()
        self._ci_values.clear()