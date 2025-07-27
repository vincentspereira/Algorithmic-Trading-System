"""
Trading Service
This service connects to the Interactive Brokers gateway and manages trading operations.
"""

import logging
from typing import Dict, Any, Optional

from nautilus_trader_engine.adapters.interactive_brokers import InteractiveBrokersAdapter
from nautilus_trader_engine.config.ib_config import get_ib_config
from nautilus_trader_engine.domain.entities import Order, OrderStatus, Trade

logger = logging.getLogger(__name__)

class TradingService:
    """
    Manages the connection to the Interactive Brokers gateway and executes trades.
    """

    def __init__(self):
        self.config = get_ib_config()
        self.adapter = InteractiveBrokersAdapter(self.config)
        self.is_connected = False

    async def connect(self):
        """
        Connects to the Interactive Brokers gateway.
        """
        try:
            await self.adapter.connect()
            self.is_connected = True
            logger.info("Successfully connected to Interactive Brokers gateway.")
        except Exception as e:
            logger.error(f"Error connecting to Interactive Brokers gateway: {e}")
            raise

    async def disconnect(self):
        """
        Disconnects from the Interactive Brokers gateway.
        """
        await self.adapter.disconnect()
        self.is_connected = False
        logger.info("Disconnected from Interactive Brokers gateway.")

    async def place_order(self, order: Order) -> Trade:
        """
        Places a new order through the Interactive Brokers gateway.
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to Interactive Brokers gateway.")
        
        try:
            trade = await self.adapter.place_order(order)
            logger.info(f"Successfully placed order {order.order_id} for {order.symbol}.")
            return trade
        except Exception as e:
            logger.error(f"Error placing order {order.order_id}: {e}")
            raise

    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancels an existing order.
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to Interactive Brokers gateway.")
            
        try:
            success = await self.adapter.cancel_order(order_id)
            if success:
                logger.info(f"Successfully cancelled order {order_id}.")
            else:
                logger.warning(f"Failed to cancel order {order_id}.")
            return success
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            raise

    async def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """
        Retrieves the status of an order.
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to Interactive Brokers gateway.")
            
        return await self.adapter.get_order_status(order_id)

    async def get_portfolio(self) -> Dict[str, Any]:
        """
        Retrieves the current portfolio from the Interactive Brokers gateway.
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to Interactive Brokers gateway.")

        return await self.adapter.get_portfolio()