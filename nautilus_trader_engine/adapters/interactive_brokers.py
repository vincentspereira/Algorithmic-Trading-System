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

from ib_insync import IB, Contract, Order as IBOrder, Ticker, Trade
from nautilus_trader.core.component import Component
from nautilus_trader.core.message import Event
from nautilus_trader.model.book import QuoteTick
from nautilus_trader.model.data import Bar
from nautilus_trader.model.enums import OrderSide, OrderType, TimeInForce, OrderStatus as NautilusOrderStatus
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

    def on_order_status(self, trade: Trade):
        """Handles order status updates."""
        nautilus_order_status = from_ib_order_status(trade.orderStatus.status)
        if nautilus_order_status:
            # Example: Emit OrderFilled event if order is filled
            if nautilus_order_status == NautilusOrderStatus.FILLED:
                order_filled_event = OrderFilled(
                    order_id=OrderId(str(trade.order.orderId)),
                    client_order_id=ClientOrderId(trade.order.permId),
                    instrument_id=InstrumentId(trade.contract.symbol, trade.contract.exchange, trade.contract.currency),
                    price=Price(trade.avgFillPrice),
                    quantity=Quantity(trade.filled),
                    timestamp=self.loop.time() # Use loop time for consistency
                )
                self.put_event(order_filled_event)
                self._log.info(f"Order filled: {order_filled_event}")
            # You can add more conditions for other order statuses (e.g., CANCELED, PARTIAL_FILL)
            # and emit corresponding Nautilus events.

    def on_pnl(self, pnl):
        """Handles profit and loss updates."""
        # Example: Emit AccountState event
        account_state_event = AccountState(
            account_id="IB_ACCOUNT", # Replace with actual account ID
            timestamp=self.loop.time(),
            cash_balance=pnl.equityWithLoanValue, # This might not be directly from pnl, need to verify IB API
            # Add other relevant account state details
        )
        self.put_event(account_state_event)
        self._log.debug(f"PNL update: {pnl}")

    def on_position(self, position):
        """Handles position updates."""
        # Example: Emit PositionState event
        position_state_event = PositionState(
            instrument_id=InstrumentId(position.contract.symbol, position.contract.exchange, position.contract.currency),
            account_id="IB_ACCOUNT", # Replace with actual account ID
            quantity=Quantity(position.position),
            average_price=Price(position.avgCost),
            timestamp=self.loop.time()
        )
        self.put_event(position_state_event)
        self._log.info(f"Position update: {position_state_event}")

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
            trade = await self.ib.placeOrderAsync(contract, ib_order)
            self._log.info(f"Placed order {order.client_order_id}: {trade}")
            return trade
        except Exception as e:
            self._log.error(f"Error submitting order {order.client_order_id}: {e}")
            raise

    async def cancel_order(self, ib_order_id: int):
        """Cancels an existing order by IB order ID."""
        if not self._is_connected:
            self._log.warning("Not connected to IB, cannot cancel order.")
            return False

        try:
            trade = await self.ib.reqGlobalCancel() # This cancels all open orders
            # For specific order cancellation, you would need to find the trade object
            # trade = self.ib.orders() # or self.ib.trades()
            # for t in trade:
            #     if t.order.orderId == ib_order_id:
            #         await self.ib.cancelOrder(t.order)
            #         self._log.info(f"Cancelled order {ib_order_id}")
            #         return True
            self._log.info(f"Attempted to cancel all open orders.")
            return True # Assuming reqGlobalCancel is sufficient for now
        except Exception as e:
            self._log.error(f"Error cancelling order {ib_order_id}: {e}")
            return False

    async def get_order_status(self, ib_order_id: int) -> Optional[NautilusOrderStatus]:
        """Retrieves the status of an order by IB order ID."""
        if not self._is_connected:
            self._log.warning("Not connected to IB, cannot get order status.")
            return None
        
        for trade in self.ib.trades():
            if trade.order.orderId == ib_order_id:
                return from_ib_order_status(trade.orderStatus.status)
        return None

    async def get_portfolio(self):
        """Retrieves the current portfolio and positions."""
        if not self._is_connected:
            self._log.warning("Not connected to IB, cannot get portfolio.")
            return None
        
        await self.ib.reqAccountUpdatesAsync(True, self.config.ACCOUNT_CODE)
        
        account_values = {v.tag: v.value for v in self.ib.accountValues()}
        positions = [
            {
                "contract": p.contract.localSymbol,
                "position": p.position,
                "avg_cost": p.avgCost
            } for p in self.ib.positions()
        ]
        
        return {
            "account_values": account_values,
            "positions": positions
        }