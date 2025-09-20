"""Average True Range (ATR) Indicator."""
from collections import deque
from dataclasses import dataclass

from nautilus_trader.model.data import Bar
from nautilus_trader_engine.indicators.base import Indicator, IndicatorConfig


@dataclass
class ATRConfig(IndicatorConfig):
    """
    Configuration for the ATR indicator.

    Args:
        period (int): The period over which to calculate the ATR. Default is 14.
        smoothing_type (str): The type of smoothing to use ('sma' or 'smma').
            Default is 'smma'.
    """

    period: int = 14
    smoothing_type: str = "smma"  # Smoothed Moving Average


class ATR(Indicator):
    """
    Calculates the Average True Range (ATR), a volatility measure.

    The ATR is calculated as the smoothed moving average of the true range.
    The true range is the greatest of the following:
    - High minus low
    - Absolute value of high minus previous close
    - Absolute value of low minus previous close
    """

    def __init__(self, config: ATRConfig):
        super().__init__(config)
        self._true_ranges = deque(maxlen=self.config.period)
        self._previous_bar: Bar | None = None
        self._atr_values = deque(maxlen=self.config.buffer_size)

    @property
    def atr(self) -> float:
        """Returns the last calculated ATR value."""
        return self._atr_values[-1] if self.is_ready else 0.0

    @property
    def is_ready(self) -> bool:
        """Returns True if the indicator has enough data to be calculated."""
        return len(self._atr_values) > 0

    def handle_bar(self, bar: Bar):
        """
        Updates the ATR with a new bar.

        Args:
            bar (Bar): The new bar to process.
        """
        true_range = self._calculate_true_range(bar)
        self._true_ranges.append(true_range)

        if len(self._true_ranges) == self.config.period:
            if not self.is_ready:
                # First ATR value is the simple average of the first `period` true ranges
                atr = sum(self._true_ranges) / len(self._true_ranges)
            else:
                if self.config.smoothing_type == "smma":
                    # Subsequent ATR values are smoothed
                    atr = (
                        self._atr_values[-1] * (self.config.period - 1) + true_range
                    ) / self.config.period
                else:  # sma
                    atr = sum(self._true_ranges) / len(self._true_ranges)

            self._atr_values.append(atr)

        self._previous_bar = bar

    def _calculate_true_range(self, bar: Bar) -> float:
        """
        Calculates the true range for a given bar.

        Args:
            bar (Bar): The bar to calculate the true range for.

        Returns:
            The true range value.
        """
        if self._previous_bar:
            high_low = bar.high - bar.low
            high_prev_close = abs(bar.high - self._previous_bar.close)
            low_prev_close = abs(bar.low - self._previous_bar.close)
            return max(high_low, high_prev_close, low_prev_close)
        else:
            # First bar, true range is simply high - low
            return bar.high - bar.low

    def reset(self):
        """
        Resets the indicator to its initial state.
        """
        super().reset()
        self._true_ranges.clear()
        self._previous_bar = None
        self._atr_values.clear()