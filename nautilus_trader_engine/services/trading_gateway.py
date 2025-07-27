# nautilus_trader_engine/services/trading_gateway.py

"""
Handles the integration between the FastAPI application and the Interactive Brokers (IB) gateway.

This service is responsible for:
- Establishing and maintaining a connection to the IB gateway.
- Translating API requests into IB-compatible order objects.
- Executing, monitoring, and managing the lifecycle of trades.
- Integrating with the risk management service to ensure all trades comply with predefined limits.
"""

import logging
from nautilus_trader.adapters.interactive_brokers.client import InteractiveBrokersClient
from nautilus_trader.config.ib_config import get_ib_config
from nautilus_trader.core.logging import Logger
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.enums import OrderType
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.objects import Price
from nautilus_trader.model.orders.limit import LimitOrder
from nautilus_trader.model.enums import OrderStatus
from nautilus_trader_engine.services.risk_management_service import RiskManagementService

class TradingGateway:
    """
    Manages the connection to the Interactive Brokers gateway and handles order execution.
    """
    def __init__(self, risk_management_service: RiskManagementService):
        self.config = get_ib_config()
        self.risk_management_service = risk_management_service
        self.logger = Logger(self.__class__.__name__)
        self.client = InteractiveBrokersClient(
            host=self.config.host,
            port=self.config.port,
            client_id=self.config.client_id,
        )
        self.order_statuses = {}
        self.trade_updates = []
        self.order_books = {}
        self.positions = {}

    async def connect(self):
        """
        Connects to the Interactive Brokers gateway.
        """
        try:
            await self.client.connect()
            self.logger.info("Successfully connected to Interactive Brokers gateway.")
        except Exception as e:
            self.logger.error(f"Failed to connect to Interactive Brokers gateway: {e}")
            raise

    async def disconnect(self):
        """
        Disconnects from the Interactive Brokers gateway.
        """
        await self.client.disconnect()
        self.logger.info("Disconnected from Interactive Brokers gateway.")

    async def place_order(self, instrument_id: InstrumentId, side: OrderSide, quantity: float, price: Price, order_type: OrderType):
        """
        Places a new order after validating it with the risk management service.

        Args:
            instrument_id (InstrumentId): The identifier of the instrument to trade.
            side (OrderSide): The side of the order (buy or sell).
            quantity (float): The quantity of the instrument to trade.
            price (Price): The price at which to place the order.
            order_type (OrderType): The type of order to place.

        Returns:
            A dictionary with the order ID and status, or None if failed.
        """
        # Create a mock order for risk validation
        order = self._create_order(instrument_id, side, quantity, price, order_type)

        # Validate the order with the risk management service
        if not self.risk_management_service.validate_order(order):
            self.logger.warning(f"Order {order.order_id} failed risk validation.")
            return None

        # Execute the order through the IB client
        try:
            await self.client.submit_order(order)
            self.logger.info(f"Successfully placed order: {order}")
            self.order_statuses[order.order_id] = OrderStatus.ACCEPTED
            self.trade_updates.append(f"Order {order.order_id} submitted and pending.")
            return {"order_id": order.order_id, "status": "PENDING"}
        except Exception as e:
            self.logger.error(f"Failed to place order {order.order_id}: {e}")
            return None

    def _create_order(self, instrument_id: InstrumentId, side: OrderSide, quantity: float, price: Price, order_type: OrderType):
        """
        Creates a new order object.

        Args:
            instrument_id (InstrumentId): The identifier of the instrument.
            side (OrderSide): The side of the order.
            quantity (float): The quantity of the instrument.
            price (Price): The price for the order.
            order_type (OrderType): The type of order.

        Returns:
            A new LimitOrder object.
        """
        if order_type == OrderType.LIMIT:
            return LimitOrder(
                instrument_id=instrument_id,
                order_side=side,
                quantity=quantity,
                limit_price=price,
            )
        # Add other order types as needed
        raise NotImplementedError(f"Order type {order_type} not supported.")

    async def get_order_status(self, order_id: str) -> dict:
        """
        Retrieves the status of a specific order.

        Args:
            order_id (str): The ID of the order to check.

        Returns:
            A dictionary containing the order status.
        """
        return {"order_id": order_id, "status": self.order_statuses.get(order_id, "UNKNOWN")}

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

    async def cancel_order(self, order_id):
        """
        Cancels an existing order.

        Args:
            order_id: The ID of the order to cancel.
        """
        try:
            # Find the order by its ID and cancel it
            order_to_cancel = await self.client.get_order(order_id)
            if order_to_cancel:
                await self.client.cancel_order(order_to_cancel)
                self.logger.info(f"Successfully cancelled order: {order_id}")
                self.order_statuses[order_id] = OrderStatus.CANCELLED
                self.trade_updates.append(f"Order {order_id} was successfully cancelled.")
            else:
                self.logger.warning(f"Order {order_id} not found for cancellation.")
        except Exception as e:
            self.logger.error(f"Failed to cancel order {order_id}: {e}")

# Example usage
if __name__ == "__main__":
    import asyncio

    async def main():
        # Initialize services
        risk_service = RiskManagementService()
        gateway = TradingGateway(risk_management_service=risk_service)

        # Connect to the gateway
        await gateway.connect()

        # Example: Place a buy order
        instrument = InstrumentId.from_str("EUR/USD.FX.IDEALPRO")
        buy_order = await gateway.place_order(
            instrument_id=instrument,
            side=OrderSide.BUY,
            quantity=1000,
            price=Price(1.1),
            order_type=OrderType.LIMIT
        )

        # Example: Cancel the order
        if buy_order:
            await gateway.cancel_order(buy_order.order_id)

        # Disconnect from the gateway
        await gateway.disconnect()

    asyncio.run(main())