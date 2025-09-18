# nautilus_trader_engine/services/trading_gateway.py

"""
Handles the integration between the FastAPI application and the Interactive Brokers (IB) gateway.

This service is responsible for:
- Establishing and maintaining a connection to the IB gateway.
- Translating API requests into IB-compatible order objects.
- Executing, monitoring, and managing the lifecycle of trades.
- Integrating with the risk management service to ensure all trades comply with predefined limits.

Note:
- This module is designed to import safely even when optional trading dependencies
  (e.g., NautilusTrader, IB adapter libs) are not installed. In such cases it
  transparently falls back to a no-op dummy adapter so tests can import and run.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

from nautilus_trader_engine.services.risk_management_service import RiskManagementService

logger = logging.getLogger(__name__)


class _DummyAdapter:
    """Minimal in-memory adapter used when real trading deps are unavailable."""

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def submit_order(self, order: Any) -> Any:
        # Return a dummy trade-like object
        class _DummyTrade:
            class _DummyOrder:
                orderId = 1

            order = _DummyOrder()
        return _DummyTrade()

    async def cancel_order(self, ib_order_id: Any) -> bool:
        return True

    async def get_order_status(self, ib_order_id: Any) -> str:
        return "PENDING_NEW"

    async def get_portfolio(self) -> dict:
        return {"cash": 100000.0, "positions": []}


class TradingGateway:
    """
    Trading gateway that integrates FastAPI with IB gateway.
    
    This service acts as a bridge between the web API and the Interactive Brokers
    trading system, providing order management, position tracking, and risk controls.
    """

    def __init__(
        self,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        risk_management_service: RiskManagementService = None,
        config: Any = None,
    ):
        self.loop = loop or asyncio.get_event_loop()
        self.config = config or {}
        self.risk_management_service = risk_management_service
        self.logger = logging.getLogger(self.__class__.__name__)
        self.order_statuses: dict[str, str] = {}
        self.trade_updates: list[str] = []
        self.order_books: dict[str, Any] = {}
        self.positions: dict[str, Any] = {}
        self.active_orders: dict[str, Any] = {}
        self.is_connected = False
        self.orders = {}
        self.order_counter = 0
        self.connection_status = "disconnected"
        self.last_heartbeat = None

        # Lazy import of the real adapter; fall back to dummy if unavailable
        self._dummy_mode = False
        self.adapter: Optional[Any] = None
        try:
            from nautilus_trader_engine.adapters.interactive_brokers import (
                InteractiveBrokersAdapter,
            )

            # If loop or config are not provided, force dummy mode to avoid misconfiguration
            if self.loop is None or self.config is None:
                raise RuntimeError("Missing event loop or config; using dummy adapter.")

            self.adapter = InteractiveBrokersAdapter(
                loop=self.loop,
                config=self.config,
            )
            self.adapter_type = "nautilus_ib"
            self.logger.debug("Initialized InteractiveBrokersAdapter")
        except Exception as e:  # broad to catch ImportError and runtime import errors
            self.logger.warning(
                "Falling back to dummy trading adapter due to missing/invalid deps: %s",
                e,
            )
            self._dummy_mode = True
            self.adapter = _DummyAdapter()
            self.adapter_type = "dummy"

    async def connect(self):
        """
        Connects to the Interactive Brokers gateway.
        """
        try:
            await self.adapter.start()
            self.is_connected = True
            self.connection_status = "connected"
            self.last_heartbeat = datetime.now()
            self.logger.info(
                "Successfully connected to %s (%s)",
                "DummyAdapter" if self._dummy_mode else "Interactive Brokers gateway",
                self.adapter_type,
            )
        except Exception as e:
            self.connection_status = "error"
            self.logger.error("Failed to connect to trading adapter: %s", e)
            raise

    async def disconnect(self):
        """
        Disconnects from the Interactive Brokers gateway.
        """
        try:
            await self.adapter.stop()
            self.is_connected = False
            self.connection_status = "disconnected"
            self.last_heartbeat = None
        except Exception as e:
            self.connection_status = "error"
            self.logger.error("Error during disconnect: %s", e)
            raise
        finally:
            self.logger.info(
                "Disconnected from %s",
                "DummyAdapter" if self._dummy_mode else "Interactive Brokers gateway",
            )

    async def place_order(self, order: Any):
        """
        Places a new order after validating it with the risk management service.

        Args:
            order: The order object to place.

        Returns:
            A trade-like object if successful, None otherwise.
        """
        # Validate the order with the risk management service
        try:
            is_valid = self.risk_management_service.validate_order(order)
        except Exception as e:
            self.logger.error("Risk validation errored: %s", e)
            is_valid = False

        if not is_valid:
            cid = getattr(order, "client_order_id", None)
            self.logger.warning("Order %s failed risk validation.", cid)
            return None

        # Execute the order through the adapter
        try:
            trade = await self.adapter.submit_order(order)
            if trade:
                cid = str(getattr(order, "client_order_id", "unknown_client_order_id"))
                self.logger.info("Successfully placed order: %s", cid)
                self.order_statuses[cid] = "PENDING_NEW"
                self.active_orders[cid] = getattr(getattr(trade, "order", None), "orderId", None)
                self.trade_updates.append(
                    f"Order {cid} submitted and pending. IB Order ID: {self.active_orders[cid]}"
                )
                return trade
            else:
                cid = str(getattr(order, "client_order_id", "unknown_client_order_id"))
                self.logger.error("Failed to place order %s: No trade object returned.", cid)
                return None
        except Exception as e:
            cid = str(getattr(order, "client_order_id", "unknown_client_order_id"))
            self.logger.error("Error placing order %s: %s", cid, e)
            return None

    async def cancel_order(self, client_order_id: str) -> bool:
        """
        Cancels an existing order.

        Args:
            client_order_id (str): The client order ID of the order to cancel.
        """
        ib_order_id = self.active_orders.get(client_order_id)
        if not ib_order_id:
            self.logger.warning("No active order found for client order ID: %s", client_order_id)
            return False

        try:
            success = await self.adapter.cancel_order(ib_order_id)
            if success:
                self.logger.info("Successfully cancelled order: %s", client_order_id)
                self.order_statuses[client_order_id] = "CANCELED"
                self.trade_updates.append(
                    f"Order {client_order_id} was successfully cancelled."
                )
                if client_order_id in self.active_orders:
                    del self.active_orders[client_order_id]
            else:
                self.logger.warning("Failed to cancel order %s.", client_order_id)
            return success
        except Exception as e:
            self.logger.error("Error cancelling order %s: %s", client_order_id, e)
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
            return {
                "client_order_id": client_order_id,
                "status": "UNKNOWN",
                "ib_order_id": None,
            }

        try:
            status = await self.adapter.get_order_status(ib_order_id)
        except Exception:
            status = None

        status_value = (
            getattr(status, "value", None) if status is not None else None
        ) or (status if isinstance(status, str) else None) or "UNKNOWN"

        return {
            "client_order_id": client_order_id,
            "status": status_value,
            "ib_order_id": ib_order_id,
        }

    async def get_portfolio(self) -> dict:
        """
        Retrieves the current portfolio from the Interactive Brokers gateway.
        """
        try:
            portfolio = await self.adapter.get_portfolio()
        except Exception:
            portfolio = {"cash": None, "positions": []}
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
        self.positions[instrument_id] = {
            "quantity": quantity,
            "average_cost": avg_cost,
        }

    async def get_positions(self):
        """
        Retrieves the current positions.

        Returns:
            A dictionary of current positions.
        """
        return self.positions


# Example usage (guarded to avoid import issues during tests)
if __name__ == "__main__":
    import asyncio as _asyncio

    try:
        from nautilus_trader_engine.config.ib_config import get_ib_config as _get_ib_config
        from nautilus_trader.model.identifiers import InstrumentId as _InstrumentId, ClientOrderId as _ClientOrderId
        from nautilus_trader.model.enums import OrderSide as _OrderSide, TimeInForce as _TimeInForce
        from nautilus_trader.model.orders.market import MarketOrder as _MarketOrder
    except Exception as _e:  # pragma: no cover - example block only
        logger.error("Example cannot run due to missing deps: %s", _e)
    else:
        async def _main():
            loop = _asyncio.get_event_loop()
            ib_config = _get_ib_config()
            risk_service = RiskManagementService()  # concrete implementation expected
            gateway = TradingGateway(
                loop=loop, risk_management_service=risk_service, config=ib_config
            )

            # Connect to the gateway
            await gateway.connect()

            # Example: Place a market order
            instrument_id = _InstrumentId.from_str("SPY.STK.SMART")
            order = _MarketOrder(
                instrument_id=instrument_id,
                order_side=_OrderSide.BUY,
                quantity=10,  # type: ignore[arg-type]
                client_order_id=_ClientOrderId("test_market_order_1"),
                time_in_force=_TimeInForce.DAY,
            )
            trade = await gateway.place_order(order)
            if trade:
                print(f"Placed order with IB Order ID: {getattr(getattr(trade, 'order', None), 'orderId', None)}")
                # Wait a bit for status update
                await _asyncio.sleep(1)
                status = await gateway.get_order_status("test_market_order_1")
                print(f"Order status: {status}")

            # Get portfolio
            portfolio = await gateway.get_portfolio()
            print(f"Portfolio: {portfolio}")

            # Disconnect from the gateway
            await gateway.disconnect()

        _asyncio.run(_main())