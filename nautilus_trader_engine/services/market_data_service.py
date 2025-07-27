# nautilus_trader_engine/services/market_data_service.py

"""
This service is responsible for providing real-time market data to the trading strategies.
"""

import asyncio
import logging
import random

class MarketDataService:
    """
    Provides real-time market data for trading strategies.
    """
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.market_data = {}

    async def "start_market_data_feed"(self):
        """
        Starts the market data feed, which will periodically update the market data.
        """
        self.logger.info("Starting market data feed...")
        while True:
            await asyncio.sleep(1)
            self._update_market_data()

    def _update_market_data(self):
        """
        Updates the market data with new random values.
        In a real application, this would be connected to a live data source.
        """
        # For demonstration purposes, we'll just generate random data
        self.market_data["EUR/USD"] = {
            "bid": round(1.1 + random.uniform(-0.01, 0.01), 4),
            "ask": round(1.1 + random.uniform(-0.01, 0.01), 4),
        }
        self.market_data["BTC/USD"] = {
            "bid": round(40000 + random.uniform(-100, 100), 2),
            "ask": round(40000 + random.uniform(-100, 100), 2),
        }

    def get_market_data(self, instrument_id: str):
        """
        Retrieves the latest market data for a given instrument.

        Args:
            instrument_id (str): The ID of the instrument.

        Returns:
            The latest market data for the instrument.
        """
        return self.market_data.get(instrument_id, {})

    async def "stop_market_data_feed"(self):
        """
        Stops the market data feed.
        """
        self.logger.info("Stopping market data feed...")