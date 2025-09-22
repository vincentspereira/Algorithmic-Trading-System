"""
The Williams %R indicator.
"""
from collections import deque
from dataclasses import dataclass

from nautilus_trader.model.data import Bar
from nautilus_trader.model.enums import PriceType
from nautilus_trader.model.indicator import Indicator, IndicatorConfig


@dataclass
class WilliamsRConfig(IndicatorConfig):
    """
    Configuration for the Williams %R indicator.

    Attributes:
        period (int): The period for the Williams %R calculation.
        price_type (PriceType): The price type to use for the calculation. Defaults to CLOSE.
    """
    period: int = 14
    price_type: PriceType = PriceType.CLOSE


class WilliamsR(Indicator):
    """
    Williams %R indicator.

    A momentum indicator that is the inverse of the Fast Stochastic Oscillator.
    """

    def __init__(self, config: WilliamsRConfig):
        super().__init__(config)
        self._bars = deque(maxlen=self.config.period)
        self._williams_r_values = deque(maxlen=self.config.buffer_size)

    @property
    def williams_r(self) -> float:
        """The Williams %R value."""
        return self._williams_r_values[-1] if self.is_ready else 0.0

    @property
    def is_ready(self) -> bool:
        return len(self._williams_r_values) > 0

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
            value = ((period_high - current_price) / (period_high - period_low)) * -100
        else:
            value = -50.0  # Neutral value

        self._williams_r_values.append(value)

    def reset(self):
        """
        Resets the indicator.
        """
        super().reset()
        self._bars.clear()
        self._williams_r_values.clear()