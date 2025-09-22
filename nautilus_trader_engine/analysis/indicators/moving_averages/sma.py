from nautilus_trader.model.data import Bar
from nautilus_trader.model.enums import PriceType
from nautilus_trader.model.events import OrderSide
from nautilus_trader.model.indicators import Indicator
from nautilus_trader.model.instruments import Instrument


class SMA(Indicator):
    def __init__(self, period: int, price_type: PriceType = PriceType.CLOSE, instrument: Instrument = None):
        super().__init__(instrument)
        self.period = period
        self.price_type = price_type
        self.prices = []

    def _calculate(self, bar: Bar):
        price = bar.price(self.price_type)
        self.prices.append(price)
        if len(self.prices) > self.period:
            self.prices.pop(0)
        if len(self.prices) == self.period:
            sma = sum(self.prices) / self.period
            self.add_value(sma, bar.ts_event)