"""
The Relative Strength Index (RSI) indicator.
"""
from collections import deque
from dataclasses import dataclass

from nautilus_trader.model.data import Bar
from nautilus_trader.model.enums import PriceType
from nautilus_trader.model.indicator import Indicator, IndicatorConfig


@dataclass
class RSIConfig(IndicatorConfig):
    """
    Configuration for the RSI indicator.

    Attributes:
        period (int): The period for the RSI calculation.
        price_type (PriceType): The price type to use for the calculation. Defaults to CLOSE.
    """
    period: int
    price_type: PriceType = PriceType.CLOSE


class RSI(Indicator):
    """
    Relative Strength Index (RSI) indicator.

    Calculates the RSI, a momentum oscillator that measures the speed and change of
    price movements.
    """

    def __init__(self, config: RSIConfig):
        super().__init__(config)
        self._prices = deque(maxlen=self.config.period + 1)
        self._rsi_values = deque(maxlen=self.config.buffer_size)
        self._avg_gain = 0.0
        self._avg_loss = 0.0
        self._last_price = None

    @property
    def rsi(self) -> float:
        """The RSI value."""
        return self._rsi_values[-1] if self.is_ready else 0.0

    @property
    def is_ready(self) -> bool:
        return len(self._rsi_values) > 0

    def handle_bar(self, bar: Bar):
        """
        Handles a new bar.

        Args:
            bar (Bar): The new bar.
        """
        price = bar.price(self.config.price_type)
        
        if self._last_price is None:
            self._last_price = price
            return

        change = price - self._last_price
        gain = change if change > 0 else 0
        loss = -change if change < 0 else 0

        if len(self._prices) < self.config.period:
            self._avg_gain = (self._avg_gain * (len(self._prices)) + gain) / (len(self._prices) + 1)
            self._avg_loss = (self._avg_loss * (len(self._prices)) + loss) / (len(self._prices) + 1)
        else:
            self._avg_gain = (self._avg_gain * (self.config.period - 1) + gain) / self.config.period
            self._avg_loss = (self._avg_loss * (self.config.period - 1) + loss) / self.config.period

        self._prices.append(price)
        self._last_price = price

        if len(self._prices) > self.config.period:
            if self._avg_loss > 0:
                rs = self._avg_gain / self._avg_loss
                rsi = 100 - (100 / (1 + rs))
            else:
                rsi = 100
            self._rsi_values.append(rsi)

    def reset(self):
        """Resets the indicator."""
        super().reset()
        self._prices.clear()
        self._rsi_values.clear()
        self._avg_gain = 0.0
        self._avg_loss = 0.0
        self._last_price = None