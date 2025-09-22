import math

from nautilus_trader.model.data import Bar
from nautilus_trader.model.enums import PriceType
from nautilus_trader.model.events import OrderSide
from nautilus_trader.model.indicators import Indicator
from nautilus_trader.model.instruments import Instrument

from .wma import WMA


class HMA(Indicator):
    def __init__(self, period: int, price_type: PriceType = PriceType.CLOSE, instrument: Instrument = None):
        super().__init__(instrument)
        self.period = period
        self.price_type = price_type
        self.wma_half = WMA(period=period // 2, price_type=price_type, instrument=instrument)
        self.wma_full = WMA(period=period, price_type=price_type, instrument=instrument)
        self.wma_sqrt = WMA(period=int(math.sqrt(period)), price_type=price_type, instrument=instrument)

    def _calculate(self, bar: Bar):
        self.wma_half.add_bar(bar)
        self.wma_full.add_bar(bar)

        if self.wma_half.is_ready and self.wma_full.is_ready:
            wma_diff = 2 * self.wma_half.value - self.wma_full.value
            # This is a bit of a hack, but we need to create a fake bar to pass to the wma_sqrt indicator
            fake_bar = Bar(
                instrument_id=bar.instrument_id,
                bar_type=bar.bar_type,
                ts_event=bar.ts_event,
                ts_init=bar.ts_init,
                open=wma_diff,
                high=wma_diff,
                low=wma_diff,
                close=wma_diff,
                volume=bar.volume,
            )
            self.wma_sqrt.add_bar(fake_bar)
            if self.wma_sqrt.is_ready:
                self.add_value(self.wma_sqrt.value, bar.ts_event)