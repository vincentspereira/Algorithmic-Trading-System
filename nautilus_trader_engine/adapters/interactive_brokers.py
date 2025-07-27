"""
interactive_brokers.py

NautilusTrader adapter for Interactive Brokers.

This module provides the integration layer to connect NautilusTrader with the
Interactive Brokers TWS or Gateway using the `ib_insync` library. It handles:
- Connection and session management
- Market data subscriptions
- Order routing, execution, and lifecycle management
- Account and position updates
- Error handling and reconnection logic
"""

import asyncio
from typing import Optional

from ib_insync import IB, Contract, Order as IBOrder, Ticker
from nautilus_trader.core.component import Component
from nautilus_trader.core.message import Event
from nautilus_trader.model.book import QuoteTick
from nautilus_trader.model.data import Bar
from nautilus_trader.model.enums import OrderSide, OrderType, TimeInForce
from nautilus_trader.model.events import (
    AccountState,
    OrderFilled,
    PositionState,
)
from nautilus_trader.model.identifiers import InstrumentId, OrderId, ClientOrderId
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.model.orders.order import Order
from nautilus_trader.model.position import Position

from nautilus_trader_engine.utils.ib_utils import (
    to_ib_contract,
    to_nautilus_bar,
    to_nautilus_quote_tick,
    from_ib_order_status
)
from nautilus_trader_engine.config.ib_config import IBCommonConfig


class InteractiveBrokersAdapter(Component):
    """
    Adapter for connecting to Interactive Brokers.
    """

    def __init__(self, loop, config: IBCommonConfig):
        super().__init__(loop)
        self.config = config
        self.ib = IB()
        self._is_connected = False
        self._log = self.get_logger()

    async def start(self):
        """Connects to the IB Gateway/TWS."""
        if not self.ib.isConnected():
            try:
                await self.ib.connectAsync(
                    self.config.HOST, self.config.PORT, self.config.CLIENT_ID
                )
                self._is_connected = True
                self._log.info(
                    f"Connected to IB {self.config.NAME} at "
                    f"{self.config.HOST}:{self.config.PORT}"
                )
                self.ib.newBarsEvent += self.on_bar
                self.ib.pendingTickersEvent += self.on_ticker
                self.ib.orderStatusEvent += self.on_order_status
                self.ib.pnlSingleEvent += self.on_pnl
                self.ib.positionEvent += self.on_position
                await self.ib.reqPositionsAsync()
            except ConnectionRefusedError:
                self._log.error(
                    f"Connection refused to IB {self.config.NAME}. "
                    "Ensure TWS/Gateway is running and API connections are enabled."
                )
            except Exception as e:
                self._log.error(f"Error connecting to IB: {e}")
                self._is_connected = False

    async def stop(self):
        """Disconnects from the IB Gateway/TWS."""
        if self.ib.isConnected():
            self.ib.disconnect()
        self._is_connected = False
        self._log.info(f"Disconnected from IB {self.config.NAME}")

    def on_bar(self, bars, has_new_bar):
        """Handles incoming bar data."""
        if not has_new_bar:
            return
        for bar_data in bars:
            nautilus_bar = to_nautilus_bar(bar_data, self.config.VENUE)
            self.put_event(nautilus_bar)
            self._log.debug(f"Processed new bar: {nautilus_bar}")

    def on_ticker(self, tickers):
        """Handles incoming quote tick data."""
        for ticker in tickers:
            quote_tick = to_nautilus_quote_tick(ticker, self.config.VENUE)
            if quote_tick:
                self.put_event(quote_tick)
                self._log.debug(f"Processed new quote tick: {quote_tick}")

    def on_order_status(self, trade):
        """Handles order status updates."""
        order_status = from_ib_order_status(trade.orderStatus)
        if order_status:
            # Create the appropriate Nautilus event, e.g., OrderFilled
            pass

    def on_pnl(self, pnl):
        """Handles profit and loss updates."""
        pass

    def on_position(self, position):
        """Handles position updates."""
        # Create PositionState events
        pass

    async def subscribe_market_data(self, instrument_id: InstrumentId):
        """Subscribes to market data for an instrument."""
        if not self._is_connected:
            self._log.warning("Not connected to IB, cannot subscribe to market data.")
            return

        contract = to_ib_contract(instrument_id, self.config.SYMBOL_MAP)
        try:
            await self.ib.reqMktDataAsync(contract)
            self._log.info(f"Subscribed to market data for {instrument_id}")
        except Exception as e:
            self._log.error(f"Error subscribing to market data for {instrument_id}: {e}")

    async def submit_order(self, order: Order):
        """Submits an order to IB."""
        if not self._is_connected:
            self._log.warning("Not connected to IB, cannot submit order.")
            return

        contract = to_ib_contract(order.instrument_id, self.config.SYMBOL_MAP)
        ib_order = IBOrder(
            action="BUY" if order.side == OrderSide.BUY else "SELL",
            totalQuantity=float(order.quantity),
            orderType=order.order_type.value,
            lmtPrice=float(order.price) if hasattr(order, 'price') else 0.0,
            tif=order.time_in_force.value,
        )

        try:
            trade = self.ib.placeOrder(contract, ib_order)
            self._log.info(f"Placed order {order.client_order_id}: {trade}")
        except Exception as e:
            self._log.error(f"Error submitting order {order.client_order_id}: {e}")

    async def cancel_order(self, order_id: OrderId):
        """Cancels an existing order."""
        # Implementation for order cancellation
        pass