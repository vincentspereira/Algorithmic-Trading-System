"""
The Stochastic Oscillator indicator.
"""
from collections import deque
from dataclasses import dataclass

from nautilus_trader.model.data import Bar
from nautilus_trader.model.enums import PriceType
from nautilus_trader.model.indicator import Indicator, IndicatorConfig


@dataclass
class StochasticConfig(IndicatorConfig):
    """
    Configuration for the Stochastic Oscillator.

    Attributes:
        period (int): The period for the %K calculation.
        smoothing_period (int): The period for the %D calculation.
        price_type (PriceType): The price type to use for the calculation. Defaults to CLOSE.
    """
    period: int = 14
    smoothing_period: int = 3
    price_type: PriceType = PriceType.CLOSE


class Stochastic(Indicator):
    """
    Stochastic Oscillator indicator.

    Calculates the %K and %D lines.
    """

    def __init__(self, config: StochasticConfig):
        super().__init__(config)
        self._bars = deque(maxlen=self.config.period)
        self._k_values = deque(maxlen=self.config.smoothing_period)
        self._percent_k_values = deque(maxlen=self.config.buffer_size)
        self._percent_d_values = deque(maxlen=self.config.buffer_size)

    @property
    def percent_k(self) -> float:
        """The %K value."""
        return self._percent_k_values[-1] if self.is_ready else 0.0

    @property
    def percent_d(self) -> float:
        """The %D value."""
        return self._percent_d_values[-1] if self.is_ready else 0.0

    @property
    def is_ready(self) -> bool:
        return len(self._percent_d_values) > 0

    def handle_bar(self, bar: Bar):
        """
        Handles a new bar.

        Args:
            bar (Bar): The new bar.
        """
        self._bars.append(bar)

        if len(self._bars) < self.config.period:
            return

        period_high = max(b.high for b in self._bars)
        period_low = min(b.low for b in self._bars)
        current_price = bar.price(self.config.price_type)

        if period_high - period_low > 0:
            percent_k = ((current_price - period_low) / (period_high - period_low)) * 100
        else:
            percent_k = 50.0  # Neutral value

        self._k_values.append(percent_k)
        self._percent_k_values.append(percent_k)

        if len(self._k_values) == self.config.smoothing_period:
            percent_d = sum(self._k_values) / len(self._k_values)
            self._percent_d_values.append(percent_d)

    def reset(self):
        """Resets the indicator."""
        super().reset()
        self._bars.clear()
        self._k_values.clear()
        self._percent_k_values.clear()
        self._percent_d_values.clear()