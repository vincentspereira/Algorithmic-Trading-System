"""
On-Balance Volume (OBV) Indicator.
"""
from collections import deque
from dataclasses import dataclass

from nautilus_trader.model.data import Bar

from nautilus_trader_engine.indicators.base import (
    Indicator,
    IndicatorConfig,
)


@dataclass
class OBVConfig(IndicatorConfig):
    """Configuration for the OBV indicator."""

    pass


class OBV(Indicator):
    """
    On-Balance Volume (OBV) indicator.
    """

    def __init__(self, config: OBVConfig):
        super().__init__(config)
        self.config = config
        self._obv_values = deque(maxlen=self.config.buffer_size)
        self._closes = deque(maxlen=2)
        self._obv_value = 0.0

    @property
    def obv_line(self) -> float:
        """Returns the most recent OBV value."""
        return self._obv_values[-1] if self._obv_values else 0.0

    @property
    def is_ready(self) -> bool:
        """Returns True if the indicator is ready."""
        return len(self._obv_values) > 0

    def handle_bar(self, bar: Bar):
        """
        Handles a new bar.

        Args:
            bar (Bar): The new bar.
        """
        self._closes.append(bar.close)

        if len(self._closes) < 2:
            self._obv_values.append(self._obv_value)
            return

        if bar.close > self._closes[-2]:
            self._obv_value += bar.volume
        elif bar.close < self._closes[-2]:
            self._obv_value -= bar.volume

        self._obv_values.append(self._obv_value)

    def reset(self):
        """
        Resets the indicator to its initial state.
        """
        super().reset()
        self._obv_values.clear()
        self._closes.clear()
        self._obv_value = 0.0