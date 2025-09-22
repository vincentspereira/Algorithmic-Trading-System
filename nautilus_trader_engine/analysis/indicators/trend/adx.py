"""Average Directional Index (ADX) Indicator.

This module provides the ADX indicator, which measures trend strength.
"""

from collections import deque
from dataclasses import dataclass

from nautilus_trader.model.data import Bar
from nautilus_trader_engine.indicators.base import Indicator, IndicatorConfig


@dataclass
class ADXConfig(IndicatorConfig):
    """Configuration for the ADX indicator."""

    period: int = 14
    """The period over which to calculate the ADX."""


class ADX(Indicator):
    """
    Average Directional Index (ADX) indicator.
    """

    def __init__(self, config: ADXConfig):
        super().__init__(config)

        self._plus_di_values = deque(maxlen=self.config.period)
        self._minus_di_values = deque(maxlen=self.config.period)
        self._adx_values = deque(maxlen=self.config.period)

        self._true_ranges = deque(maxlen=self.config.period)
        self._plus_dms = deque(maxlen=self.config.period)
        self._minus_dms = deque(maxlen=self.config.period)
        self._dxs = deque(maxlen=self.config.period)

        self._smoothed_plus_dm = 0.0
        self._smoothed_minus_dm = 0.0
        self._atr = 0.0
        self._smoothed_dx = 0.0

        self._previous_bar = None

    @property
    def plus_di(self) -> float:
        """The last calculated +DI value."""
        return self._plus_di_values[-1] if self._plus_di_values else 0.0

    @property
    def minus_di(self) -> float:
        """The last calculated -DI value."""
        return self._minus_di_values[-1] if self._minus_di_values else 0.0

    @property
    def adx(self) -> float:
        """The last calculated ADX value."""
        return self._adx_values[-1] if self._adx_values else 0.0

    @property
    def is_ready(self) -> bool:
        return len(self._adx_values) > 0

    def handle_bar(self, bar: Bar):
        if self._previous_bar is None:
            self._previous_bar = bar
            return

        self._calculate_directional_movement(bar)

        if len(self._true_ranges) == self.config.period:
            self._smooth_values()
            self._calculate_directional_indices()

        if len(self._dxs) == self.config.period:
            self._calculate_adx()

        self._previous_bar = bar

    def _calculate_directional_movement(self, bar: Bar):
        true_range = max(
            bar.high - bar.low,
            abs(bar.high - self._previous_bar.close),
            abs(bar.low - self._previous_bar.close),
        )

        up_move = bar.high - self._previous_bar.high
        down_move = self._previous_bar.low - bar.low

        plus_dm = up_move if up_move > down_move and up_move > 0 else 0.0
        minus_dm = down_move if down_move > up_move and down_move > 0 else 0.0

        self._true_ranges.append(true_range)
        self._plus_dms.append(plus_dm)
        self._minus_dms.append(minus_dm)

    def _smooth_values(self):
        if self._atr == 0.0:  # First calculation
            self._atr = sum(self._true_ranges) / self.config.period
            self._smoothed_plus_dm = sum(self._plus_dms) / self.config.period
            self._smoothed_minus_dm = sum(self._minus_dms) / self.config.period
        else:  # Wilder's smoothing
            self._atr = (self._atr * (self.config.period - 1) + self._true_ranges[-1]) / self.config.period
            self._smoothed_plus_dm = (
                self._smoothed_plus_dm * (self.config.period - 1) + self._plus_dms[-1]
            ) / self.config.period
            self._smoothed_minus_dm = (
                self._smoothed_minus_dm * (self.config.period - 1) + self._minus_dms[-1]
            ) / self.config.period

    def _calculate_directional_indices(self):
        plus_di_val = 100 * (self._smoothed_plus_dm / self._atr) if self._atr > 0 else 0.0
        minus_di_val = 100 * (self._smoothed_minus_dm / self._atr) if self._atr > 0 else 0.0

        self._plus_di_values.append(plus_di_val)
        self._minus_di_values.append(minus_di_val)

        di_sum = plus_di_val + minus_di_val
        dx = 100 * (abs(plus_di_val - minus_di_val) / di_sum) if di_sum > 0 else 0.0
        self._dxs.append(dx)

    def _calculate_adx(self):
        if not self._adx_values:  # First calculation
            self._smoothed_dx = sum(self._dxs) / self.config.period
        else:
            self._smoothed_dx = (self._smoothed_dx * (self.config.period - 1) + self._dxs[-1]) / self.config.period

        self._adx_values.append(self._smoothed_dx)

    def reset(self):
        super().reset()
        self._plus_di_values.clear()
        self._minus_di_values.clear()
        self._adx_values.clear()
        self._true_ranges.clear()
        self._plus_dms.clear()
        self._minus_dms.clear()
        self._dxs.clear()
        self._smoothed_plus_dm = 0.0
        self._smoothed_minus_dm = 0.0
        self._atr = 0.0
        self._smoothed_dx = 0.0
        self._previous_bar = None