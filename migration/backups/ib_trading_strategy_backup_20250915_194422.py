"""
ib_trading_strategy.py

Base trading strategy for Interactive Brokers.

This module defines a base strategy class that is specifically designed to work
with the Interactive Brokers adapter. It provides functionality for:
- Handling IB-specific order types and parameters
- Implementing position sizing and risk management for IB accounts
- Interacting with the IB adapter for order execution
"""

from nautilus_trader.model.data import Bar
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.events import OrderFilled
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.orders.limit import LimitOrder
from nautilus_trader.model.orders.market import MarketOrder
from nautilus_trader.model.position import Position
from nautilus_trader.strategy import Strategy

from nautilus_trader_engine.adapters.interactive_brokers import InteractiveBrokersAdapter


class IBTradingStrategy(Strategy):
    """
    A base strategy for trading with Interactive Brokers.

    This strategy assumes it is running in an environment with a configured
    InteractiveBrokersAdapter.
    """

    def __init__(self, instrument_id: InstrumentId):
        super().__init__()
        self.instrument_id = instrument_id
        # Note: The adapter is not directly accessed here, but through the context
        # provided by the trading engine.

    def on_start(self):
        """Called when the strategy is started."""
        self.log.info(f"{self.instrument_id}: Strategy started.")
        # Subscribe to data if not already handled by the engine
        self.subscribe_bars(self.instrument_id)

    def on_stop(self):
        """Called when the strategy is stopped."""
        self.log.info(f"{self.instrument_id}: Strategy stopped.")

    def on_bar(self, bar: Bar):
        """
        Called on a new bar of data.
        This is where the trading logic should be implemented.
        """
        self.log.info(f"Received bar: {bar}")
        # Example logic: Buy if the close is higher than the open
        if bar.close > bar.open:
            self.buy(bar.instrument_id, 100)

    def on_order_filled(self, event: OrderFilled):
        """Called when an order is filled."""
        self.log.info(f"Order filled: {event}")

    def on_position_opened(self, position: Position):
        """Called when a position is opened."""
        self.log.info(f"Position opened: {position}")

    def on_position_closed(self, position: Position):
        """Called when a position is closed."""
        self.log.info(f"Position closed: {position}")

    def buy(self, instrument_id: InstrumentId, quantity: float):
        """Submits a market buy order."""
        order = MarketOrder(
            instrument_id=instrument_id,
            order_side=OrderSide.BUY,
            quantity=quantity,
        )
        self.submit_order(order)
        self.log.info(f"Submitted market buy order for {quantity} of {instrument_id}")

    def sell(self, instrument_id: InstrumentId, quantity: float):
        """Submits a market sell order."""
        order = MarketOrder(
            instrument_id=instrument_id,
            order_side=OrderSide.SELL,
            quantity=quantity,
        )
        self.submit_order(order)
        self.log.info(f"Submitted market sell order for {quantity} of {instrument_id}")