from nautilus_trader.model.data import Bar
from nautilus_trader.model.enums import PriceType
from nautilus_trader.model.events import OrderSide
from nautilus_trader.model.indicators import Indicator
from nautilus_trader.model.instruments import Instrument


class KAMA(Indicator):
    """Kaufman's Adaptive Moving Average (KAMA)."""
    def __init__(self, period: int = 10, fast_ema: int = 2, slow_ema: int = 30, price_type: PriceType = PriceType.CLOSE, instrument: Instrument = None):
        super().__init__(instrument)
        self.period = period
        self.fast_ema = fast_ema
        self.slow_ema = slow_ema
        self.price_type = price_type
        self.prices = []
        self.kama = None

        self.fast_alpha = 2.0 / (self.fast_ema + 1)
        self.slow_alpha = 2.0 / (self.slow_ema + 1)

    def _calculate(self, bar: Bar):
        price = bar.price(self.price_type)
        self.prices.append(price)
        if len(self.prices) > self.period + 1:
            self.prices.pop(0)

        if len(self.prices) < self.period + 1:
            return

        change = abs(self.prices[-1] - self.prices[0])
        volatility = sum(abs(self.prices[i] - self.prices[i-1]) for i in range(1, len(self.prices)))

        if volatility == 0:
            er = 1.0
        else:
            er = change / volatility

        sc = (er * (self.fast_alpha - self.slow_alpha) + self.slow_alpha) ** 2

        if self.kama is None:
            self.kama = price
        else:
            self.kama = self.kama + sc * (price - self.kama)

        self.add_value(self.kama, bar.ts_event)