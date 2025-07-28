# nautilus_trader_engine/services/trading_gateway.py

"""
Handles the integration between the FastAPI application and the Interactive Brokers (IB) gateway.

This service is responsible for:
- Establishing and maintaining a connection to the IB gateway.
- Translating API requests into IB-compatible order objects.
- Executing, monitoring, and managing the lifecycle of trades.
- Integrating with the risk management service to ensure all trades comply with predefined limits.
"""

import asyncio
import logging
from nautilus_trader_engine.adapters.interactive_brokers import InteractiveBrokersAdapter
from nautilus_trader_engine.config.ib_config import IBCommonConfig
from nautilus_trader.core.logging import Logger
from nautilus_trader.model.enums import OrderSide, OrderType, OrderStatus as NautilusOrderStatus
from nautilus_trader.model.identifiers import InstrumentId, OrderId
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.model.orders.limit import LimitOrder
from nautilus_trader.model.orders.order import Order as NautilusOrder
from nautilus_trader_engine.services.risk_management_service import RiskManagementService

class TradingGateway:
    """
    Manages the connection to the Interactive Brokers gateway and handles order execution.
    """
    def __init__(self, loop: asyncio.AbstractEventLoop, risk_management_service: RiskManagementService, config: IBCommonConfig):
        self.loop = loop
        self.config = config
        self.risk_management_service = risk_management_service
        self.logger = Logger(self.__class__.__name__)
        self.adapter = InteractiveBrokersAdapter(
            loop=self.loop,
            config=self.config,
        )
        self.order_statuses = {}
        self.trade_updates = []
        self.order_books = {}
        self.positions = {}
        self.active_orders = {} # To store active orders by client_order_id or order_id

    async def connect(self):
        """
        Connects to the Interactive Brokers gateway.
        """
        try:
            await self.adapter.start()
            self.logger.info("Successfully connected to Interactive Brokers gateway.")
        except Exception as e:
            self.logger.error(f"Failed to connect to Interactive Brokers gateway: {e}")
            raise

    async def disconnect(self):
        """
        Disconnects from the Interactive Brokers gateway.
        """
        await self.adapter.stop()
        self.logger.info("Disconnected from Interactive Brokers gateway.")

    async def place_order(self, order: NautilusOrder):
        """
        Places a new order after validating it with the risk management service.

        Args:
            order (NautilusOrder): The order object to place.

        Returns:
            The IB Trade object if successful, None otherwise.
        """
        # Validate the order with the risk management service
        if not self.risk_management_service.validate_order(order):
            self.logger.warning(f"Order {order.client_order_id} failed risk validation.")
            return None

        # Execute the order through the IB adapter
        try:
            trade = await self.adapter.submit_order(order)
            if trade:
                self.logger.info(f"Successfully placed order: {order.client_order_id}")
                self.order_statuses[str(order.client_order_id)] = NautilusOrderStatus.PENDING_NEW
                self.active_orders[str(order.client_order_id)] = trade.order.orderId # Store IB order ID
                self.trade_updates.append(f"Order {order.client_order_id} submitted and pending. IB Order ID: {trade.order.orderId}")
                return trade
            else:
                self.logger.error(f"Failed to place order {order.client_order_id}: No trade object returned.")
                return None
        except Exception as e:
            self.logger.error(f"Error placing order {order.client_order_id}: {e}")
            return None

    async def cancel_order(self, client_order_id: str) -> bool:
        """
        Cancels an existing order.

        Args:
            client_order_id (str): The client order ID of the order to cancel.
        """
        ib_order_id = self.active_orders.get(client_order_id)
        if not ib_order_id:
            self.logger.warning(f"No active order found for client order ID: {client_order_id}")
            return False

        try:
            success = await self.adapter.cancel_order(ib_order_id)
            if success:
                self.logger.info(f"Successfully cancelled order: {client_order_id}")
                self.order_statuses[client_order_id] = NautilusOrderStatus.CANCELED
                self.trade_updates.append(f"Order {client_order_id} was successfully cancelled.")
                if client_order_id in self.active_orders:
                    del self.active_orders[client_order_id]
            else:
                self.logger.warning(f"Failed to cancel order {client_order_id}.")
            return success
        except Exception as e:
            self.logger.error(f"Error cancelling order {client_order_id}: {e}")
            return False

    async def get_order_status(self, client_order_id: str) -> dict:
        """
        Retrieves the status of a specific order.

        Args:
            client_order_id (str): The client order ID of the order to check.

        Returns:
            A dictionary containing the order status.
        """
        ib_order_id = self.active_orders.get(client_order_id)
        if not ib_order_id:
            return {"client_order_id": client_order_id, "status": "UNKNOWN", "ib_order_id": None}

        status = await self.adapter.get_order_status(ib_order_id)
        return {"client_order_id": client_order_id, "status": status.value if status else "UNKNOWN", "ib_order_id": ib_order_id}

    async def get_portfolio(self) -> dict:
        """
        Retrieves the current portfolio from the Interactive Brokers gateway.
        """
        portfolio = await self.adapter.get_portfolio()
        return portfolio

    async def get_trade_updates(self):
        """
        Retrieves all trade updates.

        Returns:
            A list of trade update messages.
        """
        return self.trade_updates

    async def get_order_book(self, instrument_id: str):
        """
        Retrieves the order book for a given instrument.

        Args:
            instrument_id (str): The ID of the instrument.

        Returns:
            The order book for the instrument.
        """
        return self.order_books.get(instrument_id, {})

    async def update_positions(self, instrument_id: str, quantity: float, avg_cost: float):
        """
        Updates the position for a given instrument.

        Args:
            instrument_id (str): The ID of the instrument.
            quantity (float): The quantity of the instrument.
            avg_cost (float): The average cost of the position.
        """
        self.positions[instrument_id] = {"quantity": quantity, "average_cost": avg_cost}

    async def get_positions(self):
        """
        Retrieves the current positions.

        Returns:
            A dictionary of current positions.
        """
        return self.positions

# Example usage
if __name__ == "__main__":
    import asyncio
    from nautilus_trader_engine.config.ib_config import get_ib_config
    from nautilus_trader.model.identifiers import InstrumentId, ClientOrderId
    from nautilus_trader.model.enums import OrderSide, OrderType, TimeInForce
    from nautilus_trader.model.objects import Price, Quantity
    from nautilus_trader.model.orders.market import MarketOrder

    async def main():
        loop = asyncio.get_event_loop()
        ib_config = get_ib_config()
        risk_service = RiskManagementService() # You'll need a concrete implementation
        gateway = TradingGateway(loop=loop, risk_management_service=risk_service, config=ib_config)

        # Connect to the gateway
        await gateway.connect()

        # Example: Place a market order
        instrument_id = InstrumentId.from_str("SPY.STK.SMART")
        order = MarketOrder(
            instrument_id=instrument_id,
            order_side=OrderSide.BUY,
            quantity=Quantity(10),
            client_order_id=ClientOrderId("test_market_order_1"),
            time_in_force=TimeInForce.DAY
        )
        trade = await gateway.place_order(order)
        if trade:
            print(f"Placed order with IB Order ID: {trade.order.orderId}")
            # Wait a bit for status update
            await asyncio.sleep(5)
            status = await gateway.get_order_status("test_market_order_1")
            print(f"Order status: {status}")

            # Example: Cancel the order (if still active)
            # await gateway.cancel_order("test_market_order_1")
            # status = await gateway.get_order_status("test_market_order_1")
            # print(f"Order status after cancellation attempt: {status}")

        # Get portfolio
        portfolio = await gateway.get_portfolio()
        print(f"Portfolio: {portfolio}")

        # Disconnect from the gateway
        await gateway.disconnect()

    asyncio.run(main())