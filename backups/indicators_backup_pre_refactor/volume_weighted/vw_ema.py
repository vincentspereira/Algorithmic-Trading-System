"""Volume-Weighted Exponential Moving Average (VW-EMA) Indicator."""

from collections import deque

import numpy as np
from nautilus_trader.model.data import Bar

from nautilus_trader_engine.indicators.base import (
    MultiTimeframeIndicator,
    MultiTimeframeIndicatorConfig,
)


class VWEMAConfig(MultiTimeframeIndicatorConfig):
    """
    Configuration for the VW-EMA indicator.

    Attributes:
        period (int): The moving average period.
    """

    period: int = 20


class VWEMA(MultiTimeframeIndicator):
    """
    Volume-Weighted Exponential Moving Average (VW-EMA) indicator.
    """

    def __init__(self, config: VWEMAConfig):
        super().__init__(config)
        self.period = config.period
        self.values = deque(maxlen=config.buffer_size)
        self.cumulative_price_volume_ema = 0.0
        self.cumulative_volume_ema = 0.0
        self.alpha = 1.0 / max(1, self.period)

    @property
    def is_ready(self) -> bool:
        return len(self.values) > 0

    def on_aggregated_bar(self, bar: Bar):
        price_volume = bar.close * bar.volume
        self.cumulative_price_volume_ema = (
            self.alpha * price_volume
            + (1 - self.alpha) * self.cumulative_price_volume_ema
        )
        self.cumulative_volume_ema = (
            self.alpha * bar.volume + (1 - self.alpha) * self.cumulative_volume_ema
        )

        if self.cumulative_volume_ema > 0:
            vwema = self.cumulative_price_volume_ema / self.cumulative_volume_ema
            self.values.append(vwema)

    def reset(self):
        super().reset()
        self.values.clear()
        self.cumulative_price_volume_ema = 0.0
        self.cumulative_volume_ema = 0.0