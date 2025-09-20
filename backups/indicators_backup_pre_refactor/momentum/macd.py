"""
Moving Average Convergence Divergence (MACD) indicator.
"""
from collections import deque
from dataclasses import dataclass

from nautilus_trader.model.data import Bar
from nautilus_trader.model.enums import PriceType
from nautilus_trader.model.indicator import Indicator, IndicatorConfig
from nautilus_trader_engine.indicators.moving_average.ema import EMA, EMAConfig


@dataclass
class MACDConfig(IndicatorConfig):
    """
    Configuration for the MACD indicator.

    Attributes:
        fast_period (int): The period for the fast EMA.
        slow_period (int): The period for the slow EMA.
        signal_period (int): The period for the signal line EMA.
        price_type (PriceType): The price type to use for the calculation. Defaults to CLOSE.
    """
    fast_period: int
    slow_period: int
    signal_period: int
    price_type: PriceType = PriceType.CLOSE


class MACD(Indicator):
    """
    Moving Average Convergence Divergence (MACD) indicator.

    Calculates the MACD line, signal line, and histogram.
    """

    def __init__(self, config: MACDConfig):
        super().__init__(config)
        self._fast_ema = EMA(EMAConfig(period=self.config.fast_period))
        self._slow_ema = EMA(EMAConfig(period=self.config.slow_period))
        self._signal_ema = EMA(EMAConfig(period=self.config.signal_period))

        self._macd_values = deque(maxlen=self.config.buffer_size)
        self._signal_values = deque(maxlen=self.config.buffer_size)
        self._histogram_values = deque(maxlen=self.config.buffer_size)

    @property
    def macd(self) -> float:
        """The MACD line value."""
        return self._macd_values[-1] if self._macd_values else 0.0

    @property
    def signal(self) -> float:
        """The signal line value."""
        return self._signal_values[-1] if self._signal_values else 0.0

    @property
    def histogram(self) -> float:
        """The histogram value."""
        return self._histogram_values[-1] if self._histogram_values else 0.0

    @property
    def is_ready(self) -> bool:
        return self._slow_ema.is_ready and self._signal_ema.is_ready

    def handle_bar(self, bar: Bar):
        """
        Handles a new bar.

        Args:
            bar (Bar): The new bar.
        """
        price = bar.price(self.config.price_type)
        self._fast_ema.handle_bar(bar)
        self._slow_ema.handle_bar(bar)

        if self._slow_ema.is_ready:
            macd = self._fast_ema.value - self._slow_ema.value
            self._macd_values.append(macd)

            # Create a dummy bar for the signal EMA to consume the MACD value
            # This is a simplification; in a real scenario, you might need a more robust way to pass values between indicators
            dummy_bar = Bar(
                instrument_id=bar.instrument_id,
                bar_type=bar.bar_type,
                open=macd,
                high=macd,
                low=macd,
                close=macd,
                volume=bar.volume,
                time=bar.time,
                date_time=bar.date_time,
                bid_open=macd,
                bid_high=macd,
                bid_low=macd,
                bid_close=macd,
                ask_open=macd,
                ask_high=macd,
                ask_low=macd,
                ask_close=macd,
            )
            self._signal_ema.handle_bar(dummy_bar)

            if self._signal_ema.is_ready:
                signal = self._signal_ema.value
                self._signal_values.append(signal)
                self._histogram_values.append(macd - signal)

    def reset(self):
        """Resets the indicator."""
        super().reset()
        self._fast_ema.reset()
        self._slow_ema.reset()
        self._signal_ema.reset()
        self._macd_values.clear()
        self._signal_values.clear()
        self._histogram_values.clear()