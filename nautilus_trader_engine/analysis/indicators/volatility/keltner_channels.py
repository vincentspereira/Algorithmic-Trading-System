"""Keltner Channels Indicator.

This module provides an implementation of the Keltner Channels indicator, which 
can be used to identify volatility and potential trend direction.
"""

from collections import deque
from dataclasses import dataclass

from nautilus_trader.model.data import Bar
from nautilus_trader_engine.indicators.base import Indicator, IndicatorConfig
from nautilus_trader_engine.indicators.volatility.atr import ATR, ATRConfig
from nautilus_trader_engine.indicators.trend.ema import EMA, EMAConfig


@dataclass
class KCConfig(IndicatorConfig):
    """
    Configuration for the Keltner Channels indicator.

    Args:
        ema_period (int): The period for the exponential moving average. Default is 20.
        atr_period (int): The period for the Average True Range. Default is 10.
        atr_multiplier (float): The multiplier for the ATR. Default is 2.0.
    """
    ema_period: int = 20
    atr_period: int = 10
    atr_multiplier: float = 2.0


class KeltnerChannels(Indicator):
    """
    Keltner Channels are volatility-based bands that are placed on either side of an asset's price 
    and can aid in determining the direction of a trend.
    """
    def __init__(self, config: KCConfig):
        super().__init__(config)
        self._ema = EMA(config=EMAConfig(period=config.ema_period))
        self._atr = ATR(config=ATRConfig(period=config.atr_period))

        self._upper_band = deque(maxlen=self.config.buffer_size)
        self._middle_band = deque(maxlen=self.config.buffer_size)
        self._lower_band = deque(maxlen=self.config.buffer_size)

    @property
    def is_ready(self) -> bool:
        return self._ema.is_ready and self._atr.is_ready

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
        self._ema.handle_bar(bar)
        self._atr.handle_bar(bar)

        if self.is_ready:
            middle = self._ema.ema
            atr_value = self._atr.atr

            upper = middle + (atr_value * self.config.atr_multiplier)
            lower = middle - (atr_value * self.config.atr_multiplier)

            self._middle_band.append(middle)
            self._upper_band.append(upper)
            self._lower_band.append(lower)

    def reset(self):
        super().reset()
        self._ema.reset()
        self._atr.reset()
        self._upper_band.clear()
        self._middle_band.clear()
        self._lower_band.clear()