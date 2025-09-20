"""Volume-Weighted Moving Average Convergence Divergence (VW-MACD) Indicator."""

from collections import deque
from typing import Tuple

import numpy as np
from nautilus_trader.model.data import Bar

from nautilus_trader_engine.indicators.base import (
    MultiTimeframeIndicator,
    MultiTimeframeIndicatorConfig,
)


class VWMACDConfig(MultiTimeframeIndicatorConfig):
    """
    Configuration for the VW-MACD indicator.

    Attributes:
        fast_period (int): The period for the fast VW-EMA.
        slow_period (int): The period for the slow VW-EMA.
        signal_period (int): The period for the signal line EMA.
    """

    fast_period: int = 12
    slow_period: int = 26
    signal_period: int = 9


class VWMACD(MultiTimeframeIndicator):
    """
    Volume-Weighted Moving Average Convergence Divergence (VW-MACD) indicator.
    """

    def __init__(self, config: VWMACDConfig):
        super().__init__(config)
        self.fast_period = config.fast_period
        self.slow_period = config.slow_period
        self.signal_period = config.signal_period

        self.values = deque(maxlen=config.buffer_size)
        self.vw_macd_line = deque(maxlen=config.buffer_size)
        self.vw_signal_line = deque(maxlen=config.buffer_size)
        self.vw_histogram = deque(maxlen=config.buffer_size)

        self.fast_alpha = 1.0 / max(1, self.fast_period)
        self.slow_alpha = 1.0 / max(1, self.slow_period)
        self.signal_alpha = 1.0 / max(1, self.signal_period)

        self.cumulative_price_volume_fast = 0.0
        self.cumulative_volume_fast = 0.0
        self.cumulative_price_volume_slow = 0.0
        self.cumulative_volume_slow = 0.0
        self.cumulative_macd_signal = 0.0

    @property
    def is_ready(self) -> bool:
        return len(self.vw_macd_line) > 0 and len(self.vw_signal_line) > 0

    def on_aggregated_bar(self, bar: Bar):
        # Calculate fast VW-EMA
        price_volume_fast = bar.close * bar.volume
        self.cumulative_price_volume_fast = (
            self.fast_alpha * price_volume_fast
            + (1 - self.fast_alpha) * self.cumulative_price_volume_fast
        )
        self.cumulative_volume_fast = (
            self.fast_alpha * bar.volume
            + (1 - self.fast_alpha) * self.cumulative_volume_fast
        )

        vw_ema_fast = 0.0
        if self.cumulative_volume_fast > 0:
            vw_ema_fast = self.cumulative_price_volume_fast / self.cumulative_volume_fast

        # Calculate slow VW-EMA
        price_volume_slow = bar.close * bar.volume
        self.cumulative_price_volume_slow = (
            self.slow_alpha * price_volume_slow
            + (1 - self.slow_alpha) * self.cumulative_price_volume_slow
        )
        self.cumulative_volume_slow = (
            self.slow_alpha * bar.volume
            + (1 - self.slow_alpha) * self.cumulative_volume_slow
        )

        vw_ema_slow = 0.0
        if self.cumulative_volume_slow > 0:
            vw_ema_slow = self.cumulative_price_volume_slow / self.cumulative_volume_slow

        # Calculate VW-MACD Line
        vw_macd_line_value = vw_ema_fast - vw_ema_slow
        self.vw_macd_line.append(vw_macd_line_value)

        # Calculate Signal Line
        self.cumulative_macd_signal = (
            self.signal_alpha * vw_macd_line_value
            + (1 - self.signal_alpha) * self.cumulative_macd_signal
        )
        self.vw_signal_line.append(self.cumulative_macd_signal)

        # Calculate Histogram
        vw_histogram_value = vw_macd_line_value - self.cumulative_macd_signal
        self.vw_histogram.append(vw_histogram_value)

        self.values.append(vw_macd_line_value) # Store MACD line as the primary value

    def reset(self):
        super().reset()
        self.values.clear()
        self.vw_macd_line.clear()
        self.vw_signal_line.clear()
        self.vw_histogram.clear()
        self.cumulative_price_volume_fast = 0.0
        self.cumulative_volume_fast = 0.0
        self.cumulative_price_volume_slow = 0.0
        self.cumulative_volume_slow = 0.0
        self.cumulative_macd_signal = 0.0