from nautilus_trader.model.data import Bar
from nautilus_trader.model.enums import PriceType
from nautilus_trader.model.events import OrderSide
from nautilus_trader.model.indicators import Indicator
from nautilus_trader.model.instruments import Instrument

from .ema import EMA


class TEMA(Indicator):
    """Triple Exponential Moving Average (TEMA)."""
    def __init__(self, period: int, price_type: PriceType = PriceType.CLOSE, instrument: Instrument = None):
        super().__init__(instrument)
        self.period = period
        self.price_type = price_type
        self.ema1 = EMA(period=period, price_type=price_type, instrument=instrument)
        self.ema2 = EMA(period=period, price_type=price_type, instrument=instrument)
        self.ema3 = EMA(period=period, price_type=price_type, instrument=instrument)

    def _calculate(self, bar: Bar):
        self.ema1.add_bar(bar)
        if self.ema1.is_ready:
            # This is a bit of a hack, but we need to create a fake bar to pass to the ema2 indicator
            fake_bar1 = Bar(
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
            self.ema2.add_bar(fake_bar1)
            if self.ema2.is_ready:
                # This is a bit of a hack, but we need to create a fake bar to pass to the ema3 indicator
                fake_bar2 = Bar(
                    instrument_id=bar.instrument_id,
                    bar_type=bar.bar_type,
                    ts_event=bar.ts_event,
                    ts_init=bar.ts_init,
                    open=self.ema2.value,
                    high=self.ema2.value,
                    low=self.ema2.value,
                    close=self.ema2.value,
                    volume=bar.volume,
                )
                self.ema3.add_bar(fake_bar2)
                if self.ema3.is_ready:
                    tema = 3 * self.ema1.value - 3 * self.ema2.value + self.ema3.value
                    self.add_value(tema, bar.ts_event)