
from decimal import Decimal
from typing import Optional

from nautilus_trader.core.data import Data
from nautilus_trader.indicators.average.moving_average import MovingAverageSimple
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.identifiers import Symbol
from nautilus_trader.model.objects import Quantity
from nautilus_trader.trading.strategy import Strategy, StrategyConfig

class MACrossoverConfig(StrategyConfig):
    """
    Configuration for MA Crossover strategy.
    """
    def __init__(
        self,
        symbol: str,
        fast_ma_period: int = 20,
        slow_ma_period: int = 50,
        trade_size: Decimal = Decimal("100"),
        position_size: Optional[Decimal] = None
    ):
        super().__init__()
        self.symbol = symbol
        self.fast_ma_period = fast_ma_period
        self.slow_ma_period = slow_ma_period
        self.trade_size = trade_size
        self.position_size = position_size or trade_size

class MACrossoverStrategy(Strategy):
    """
    Moving Average Crossover strategy implementation.
    """
    def __init__(
        self,
        config: MACrossoverConfig
    ):
        super().__init__(config)

        # Create strategy components
        self.symbol = Symbol.from_str(config.symbol)
        self.fast_ma = MovingAverageSimple(config.fast_ma_period)
        self.slow_ma = MovingAverageSimple(config.slow_ma_period)
        self.position_size = config.position_size
        self.trade_size = config.trade_size

        # Initialize state
        self.initialized = False
        self.last_signal = None

    def on_start(self):
        """Handle strategy start."""
        self.subscribe_bars(self.symbol)
        self.initialized = True

    def on_bar(self, bar):
        """
        Handle bar updates.
        """
        # Update indicators
        self.fast_ma.update_raw(bar.close.as_double())
        self.slow_ma.update_raw(bar.close.as_double())

        if not self.initialized:
            return

        # Generate trading signals
        if self.fast_ma.value >= self.slow_ma.value:
            signal = 1  # Buy signal
        else:
            signal = -1  # Sell signal

        # Check for signal change
        if signal != self.last_signal:
            self.last_signal = signal

            if signal == 1:
                # Buy signal
                self.buy()
            else:
                # Sell signal
                self.sell()

    def buy(self):
        """Execute buy order."""
        if self.portfolio.is_flat(self.symbol):
            order = self.order_factory.market(
                symbol=self.symbol,
                order_side=OrderSide.BUY,
                quantity=Quantity.from_int(self.trade_size),
                time_in_force=TimeInForce.IOC
            )
            self.submit_order(order)

    def sell(self):
        """Execute sell order."""
        if self.portfolio.is_long(self.symbol):
            position = self.portfolio.get_position(self.symbol)
            order = self.order_factory.market(
                symbol=self.symbol,
                order_side=OrderSide.SELL,
                quantity=position.quantity,
                time_in_force=TimeInForce.IOC
            )
            self.submit_order(order)
