from nautilus_trader.model.data import Bar
from nautilus_trader.model.enums import PriceType
from nautilus_trader.model.events import OrderSide
from nautilus_trader.model.indicators import Indicator
from nautilus_trader.model.instruments import Instrument

from .ema import EMA


class DEMA(Indicator):
    """Double Exponential Moving Average (DEMA)."""
    def __init__(self, period: int, price_type: PriceType = PriceType.CLOSE, instrument: Instrument = None):
        super().__init__(instrument)
        self.period = period
        self.price_type = price_type
        self.ema1 = EMA(period=period, price_type=price_type, instrument=instrument)
        self.ema2 = EMA(period=period, price_type=price_type, instrument=instrument)

    def _calculate(self, bar: Bar):
        self.ema1.add_bar(bar)
        if self.ema1.is_ready:
            # This is a bit of a hack, but we need to create a fake bar to pass to the ema2 indicator
            fake_bar = Bar(
                instrument_id=bar.instrument_id,
                bar_type=bar.bar_type,
                ts_event=bar.ts_event,
                ts_init=bar.ts_init,
                open=self.ema1.value,
                high=self.ema1.value,
                low=self.ema1.value,
                close=self.ema1.value,
                volume=bar.volume,
            )
            self.ema2.add_bar(fake_bar)
            if self.ema2.is_ready:
                dema = 2 * self.ema1.value - self.ema2.value
                self.add_value(dema, bar.ts_event)