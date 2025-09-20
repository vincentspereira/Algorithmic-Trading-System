"""
Accumulation/Distribution (A/D) Line Indicator.
"""

from collections import deque
from dataclasses import dataclass

from nautilus_trader.model.data import Bar

from nautilus_trader_engine.indicators.base import Indicator, IndicatorConfig


@dataclass
class ADConfig(IndicatorConfig):
    """Configuration for the AD indicator."""

    pass


class AD(Indicator):
    """
    Accumulation/Distribution Line.
    """

    def __init__(self, config: ADConfig):
        super().__init__(config)
        self._ad_values = deque(maxlen=self.config.buffer_size)
        self._ad_value = 0.0

    @property
    def is_ready(self) -> bool:
        return len(self._ad_values) > 0

    @property
    def ad_line(self) -> float:
        """Returns the last calculated A/D line value."""
        return self._ad_values[-1] if self.is_ready else 0.0

    def handle_bar(self, bar: Bar):
        high = float(bar.high)
        low = float(bar.low)
        close = float(bar.close)
        volume = float(bar.volume)

        # Calculate Money Flow Multiplier
        if high == low:
            mf_multiplier = 0.0
        else:
            mf_multiplier = ((close - low) - (high - close)) / (high - low)

        # Calculate Money Flow Volume and update A/D Line
        mf_volume = mf_multiplier * volume
        self._ad_value += mf_volume

        self._ad_values.append(self._ad_value)

    def reset(self):
        super().reset()
        self._ad_values.clear()
        self._ad_value = 0.0