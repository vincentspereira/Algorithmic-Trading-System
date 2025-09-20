"""Volume-Weighted Simple Moving Average (VW-SMA) Indicator."""

from collections import deque

from nautilus_trader.model.data import Bar

from nautilus_trader_engine.indicators.base import (
    MultiTimeframeIndicator,
    MultiTimeframeIndicatorConfig,
)


class VWSMAConfig(MultiTimeframeIndicatorConfig):
    """
    Configuration for the VW-SMA indicator.

    Attributes:
        period (int): The period for the moving average.
    """

    period: int = 20


class VWSMA(MultiTimeframeIndicator):
    """
    Volume-Weighted Simple Moving Average (VW-SMA) indicator.
    """

    def __init__(self, config: VWSMAConfig):
        super().__init__(config)
        self.period = config.period
        self.values = deque(maxlen=config.buffer_size)
        self.price_volume_sum = deque(maxlen=self.period)
        self.volume_sum = deque(maxlen=self.period)

    @property
    def is_ready(self) -> bool:
        return len(self.values) > 0

    def on_aggregated_bar(self, bar: Bar):
        self.price_volume_sum.append(bar.close * bar.volume)
        self.volume_sum.append(bar.volume)

        if len(self.price_volume_sum) < self.period:
            self.values.append(0.0)  # Not enough data
            return

        total_price_volume = sum(self.price_volume_sum)
        total_volume = sum(self.volume_sum)

        if total_volume > 0:
            vw_sma = total_price_volume / total_volume
            self.values.append(vw_sma)
        else:
            self.values.append(self.values[-1] if self.values else 0.0)

    def reset(self):
        super().reset()
        self.values.clear()
        self.price_volume_sum.clear()
        self.volume_sum.clear()