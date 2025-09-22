from nautilus_trader.model.data import Bar
from nautilus_trader.model.enums import PriceType
from nautilus_trader.model.events import OrderSide
from nautilus_trader.model.indicators import Indicator
from nautilus_trader.model.instruments import Instrument


class VWMA(Indicator):
    def __init__(self, period: int, price_type: PriceType = PriceType.CLOSE, instrument: Instrument = None):
        super().__init__(instrument)
        self.period = period
        self.price_type = price_type
        self.prices = []
        self.volumes = []

    def _calculate(self, bar: Bar):
        price = bar.price(self.price_type)
        self.prices.append(price)
        self.volumes.append(bar.volume)
        if len(self.prices) > self.period:
            self.prices.pop(0)
            self.volumes.pop(0)
        if len(self.prices) == self.period:
            price_volume = sum(p * v for p, v in zip(self.prices, self.volumes))
            total_volume = sum(self.volumes)
            vwma = price_volume / total_volume if total_volume > 0 else 0
            self.add_value(vwma, bar.ts_event)