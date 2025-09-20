"""The Commodity Channel Index (CCI) indicator.
"""
from collections import deque
from dataclasses import dataclass

import numpy as np

from nautilus_trader.model.data import Bar
from nautilus_trader.model.enums import PriceType
from nautilus_trader.model.indicator import Indicator, IndicatorConfig


@dataclass
class CCIConfig(IndicatorConfig):
    """
    Configuration for the CCI indicator.

    Attributes:
        period (int): The period for the CCI calculation.
        price_type (PriceType): The price type to use for the calculation. Defaults to TYPICAL.
    """
    period: int
    price_type: PriceType = PriceType.TYPICAL


class CCI(Indicator):
    """
    Commodity Channel Index (CCI) indicator.

    Measures the variation of a security's price from its statistical mean.
    """

    def __init__(self, config: CCIConfig):
        super().__init__(config)
        self._prices = deque(maxlen=self.config.period)
        self._cci_values = deque(maxlen=self.config.buffer_size)

    @property
    def cci(self) -> float:
        """The CCI value."""
        return self._cci_values[-1] if self._cci_values else 0.0

    @property
    def is_ready(self) -> bool:
        return len(self._cci_values) > 0

    def handle_bar(self, bar: Bar):
        """
        Handles a new bar.

        Args:
            bar (Bar): The new bar.
        """
        price = bar.price(self.config.price_type)
        self._prices.append(price)

        if len(self._prices) == self.config.period:
            sma_tp = np.mean(self._prices)
            mean_deviation = np.mean([abs(p - sma_tp) for p in self._prices])

            if mean_deviation > 0:
                cci = (price - sma_tp) / (0.015 * mean_deviation)
            else:
                cci = 0.0
            self._cci_values.append(cci)

    def reset(self):
        """Resets the indicator."""
        super().reset()
        self._prices.clear()
        self._cci_values.clear()