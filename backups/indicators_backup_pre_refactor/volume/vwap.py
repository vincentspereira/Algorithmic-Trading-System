"""
Volume-Weighted Average Price (VWAP) Indicator.
"""
from datetime import datetime
from collections import deque
from typing import Optional

from nautilus_trader.model.data import Bar

from nautilus_trader_engine.indicators.base import (
    Indicator,
    IndicatorConfig,
)


class VWAPConfig(IndicatorConfig):
    """
    Configuration for the VWAP indicator.

    Attributes:
        reset_period (str): The period at which the VWAP should reset (e.g., "daily", "weekly", "monthly").
    """

    reset_period: str = "daily"


class VWAP(Indicator):
    """
    Volume-Weighted Average Price (VWAP) indicator.
    """

    def __init__(self, config: VWAPConfig):
        super().__init__(config)
        self._vwap_values = deque(maxlen=config.buffer_size)
        self.reset_period = config.reset_period.lower()
        self._cumulative_price_volume = 0.0
        self._cumulative_volume = 0.0
        self._last_reset_timestamp: Optional[datetime] = None

    @property
    def vwap(self) -> float:
        """Returns the most recent VWAP value."""
        return self._vwap_values[-1] if self._vwap_values else 0.0

    @property
    def is_ready(self) -> bool:
        """Returns True if the indicator is ready."""
        return len(self._vwap_values) > 0

    def handle_bar(self, bar: Bar):
        """
        Handles a new bar.

        Args:
            bar (Bar): The new bar.
        """
        if self._should_reset(bar.ts_event):
            self.reset()
        self._last_reset_timestamp = bar.ts_event

        typical_price = (bar.high + bar.low + bar.close) / 3
        self._cumulative_price_volume += typical_price * bar.volume
        self._cumulative_volume += bar.volume

        if self._cumulative_volume > 0:
            vwap = self._cumulative_price_volume / self._cumulative_volume
            self._vwap_values.append(vwap)

    def _should_reset(self, timestamp: datetime) -> bool:
        if self._last_reset_timestamp is None:
            return True
        if self.reset_period == "daily":
            return timestamp.date() > self._last_reset_timestamp.date()
        if self.reset_period == "weekly":
            return timestamp.isocalendar()[1] > self._last_reset_timestamp.isocalendar()[
                1
            ]
        if self.reset_period == "monthly":
            return timestamp.month > self._last_reset_timestamp.month
        return False

    def reset(self):
        """
        Resets the indicator to its initial state.
        """
        super().reset()
        self._vwap_values.clear()
        self._cumulative_price_volume = 0.0
        self._cumulative_volume = 0.0
        self._last_reset_timestamp = None