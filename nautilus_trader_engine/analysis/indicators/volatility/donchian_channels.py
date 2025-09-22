"""
Donchian Channels Indicator.
"""
from collections import deque
from dataclasses import dataclass

import numpy as np
from nautilus_trader.model.data import Bar

from nautilus_trader_engine.indicators.base import Indicator, IndicatorConfig


@dataclass
class DCConfig(IndicatorConfig):
    """
    Configuration for the DonchianChannels indicator.

    Args:
        period (int): The period for the channels. Default is 20.
    """
    period: int = 20


class DonchianChannels(Indicator):
    """
    Donchian Channels indicator.

    Calculates upper and lower bands based on the highest high and lowest low
    over a specified period, with a middle band in between.
    """

    def __init__(self, config: DCConfig):
        super().__init__(config)
        self._highs = deque(maxlen=self.config.period)
        self._lows = deque(maxlen=self.config.period)
        self._upper_band = deque(maxlen=self.config.buffer_size)
        self._middle_band = deque(maxlen=self.config.buffer_size)
        self._lower_band = deque(maxlen=self.config.buffer_size)

    @property
    def is_ready(self) -> bool:
        """Returns whether the indicator is ready to provide values."""
        return len(self._middle_band) > 0

    @property
    def upper_band(self) -> float:
        """Returns the last calculated upper band value."""
        return self._upper_band[-1] if self.is_ready else 0.0

    @property
    def middle_band(self) -> float:
        """Returns the last calculated middle band value."""
        return self._middle_band[-1] if self.is_ready else 0.0

    @property
    def lower_band(self) -> float:
        """Returns the last calculated lower band value."""
        return self._lower_band[-1] if self.is_ready else 0.0

    def handle_bar(self, bar: Bar):
        """
        Calculate Donchian Channels for the given bar.
        """
        self._highs.append(bar.high)
        self._lows.append(bar.low)

        if len(self._highs) == self.config.period:
            upper_band = np.max(self._highs)
            lower_band = np.min(self._lows)
            middle_band = (upper_band + lower_band) / 2

            self._upper_band.append(upper_band)
            self._middle_band.append(middle_band)
            self._lower_band.append(lower_band)

    def reset(self):
        """
        Reset the state of the indicator.
        """
        super().reset()
        self._highs.clear()
        self._lows.clear()
        self._upper_band.clear()
        self._middle_band.clear()
        self._lower_band.clear()