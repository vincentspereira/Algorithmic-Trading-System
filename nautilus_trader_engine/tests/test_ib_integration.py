"""
test_ib_integration.py

Integration tests for the Interactive Brokers adapter.

These tests are designed to run against a live or paper TWS/Gateway instance
to verify the functionality of the IB adapter. They cover:
- Connection to the paper trading environment
- Order submission, modification, and cancellation
- Market data subscriptions and reception
- Position and account updates
"""

import asyncio
import unittest
from unittest.mock import AsyncMock

from nautilus_trader.model.enums import OrderSide, OrderType
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.orders.market import MarketOrder

from nautilus_trader_engine.adapters.interactive_brokers import InteractiveBrokersAdapter
from nautilus_trader_engine.config.ib_config import IBPaperConfig


class TestIBIntegration(unittest.TestCase):
    """
    Integration tests for the IB adapter.
    
    NOTE: These tests require a running TWS or IB Gateway instance with paper
          trading enabled on the configured port.
    """

    def setUp(self):
        """Set up the test environment."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        self.config = IBPaperConfig()
        self.adapter = InteractiveBrokersAdapter(self.loop, self.config)
        
        # Mock the event-putting methods to avoid dependency on a full engine
        self.adapter.put_event = AsyncMock()

    def tearDown(self):
        """Tear down the test environment."""
        self.loop.run_until_complete(self.adapter.stop())
        self.loop.close()

    def test_connect_and_disconnect(self):
        """Test connection and disconnection to the IB paper trading."""
        async def run_test():
            await self.adapter.start()
            self.assertTrue(self.adapter._is_connected)
            await self.adapter.stop()
            self.assertFalse(self.adapter._is_connected)
        
        self.loop.run_until_complete(run_test())

    def test_subscribe_market_data(self):
        """Test subscribing to market data."""
        async def run_test():
            await self.adapter.start()
            instrument_id = InstrumentId("AAPL-STK-SMART", self.config.VENUE)
            await self.adapter.subscribe_market_data(instrument_id)
            # Add assertions here to check if data is being received
            # This might involve checking the mock `put_event` or a test queue
            await asyncio.sleep(5)  # Wait for some data

        self.loop.run_until_complete(run_test())

    def test_submit_market_order(self):
        """Test submitting a market order."""
        async def run_test():
            await self.adapter.start()
            instrument_id = InstrumentId("MSFT-STK-SMART", self.config.VENUE)
            order = MarketOrder(
                instrument_id=instrument_id,
                order_side=OrderSide.BUY,
                quantity=100,
            )
            await self.adapter.submit_order(order)
            # Add assertions here to check for order status updates
            await asyncio.sleep(2)

        self.loop.run_until_complete(run_test())

    def test_position_updates(self):
        """Test receiving position updates."""
        async def run_test():
            await self.adapter.start()
            # The adapter requests positions on start.
            # We can check if `on_position` was called.
            # This requires more advanced mocking or a test harness.
            await asyncio.sleep(5) # Wait for initial position data
            # Add assertions here

        self.loop.run_until_complete(run_test())

if __name__ == "__main__":
    unittest.main()