"""
Mock Data Feed Manager for API Testing
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import yfinance as yf

from nautilus_trader_engine.brokers.ibapi import IBClient
from nautilus_trader_engine.config.ib_config import IBPaperConfig, IBLiveConfig

class DataFeedManager:
    """Mock data feed manager for testing the API"""
    
    def __init__(self, use_ibkr: bool = False, ib_config: Optional[Any] = None):
        self.initialized = False
        self.use_ibkr = use_ibkr
        self.ib_client = None
        self.ib_config = ib_config
        
    async def initialize(self):
        """Initialize the data feed manager"""
        if self.use_ibkr:
            if self.ib_config is None:
                raise ValueError("IBKR configuration must be provided when use_ibkr is True")
            self.ib_client = IBClient(
                host=self.ib_config.HOST,
                port=self.ib_config.PORT,
                client_id=self.ib_config.CLIENT_ID,
                account_id=self.ib_config.ACCOUNT_ID
            )
            await self.ib_client.connect()
        self.initialized = True
        
    async def cleanup(self):
        """Cleanup resources"""
        if self.ib_client and self.ib_client.connected:
            await self.ib_client.disconnect()
        self.initialized = False
        
    async def health_check(self) -> bool:
        """Check if data feeds are healthy"""
        if self.use_ibkr:
            return self.initialized and self.ib_client and self.ib_client.connected
        return self.initialized
        
    async def get_historical_data(
        self, 
        symbol: str, 
        period: str = "1y", 
        interval: str = "1d",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Get historical market data"""
        if self.use_ibkr and self.ib_client and self.ib_client.connected:
            # Map period and interval to IBKR compatible formats if necessary
            # For simplicity, directly use the mock IBClient's method
            return await self.ib_client.get_historical_data(symbol, period, interval)
        
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)
            return data
        except Exception:
            # Return synthetic data if yfinance fails
            dates = pd.date_range(start=datetime.now() - timedelta(days=365), periods=250, freq='D')
            np.random.seed(42)
            prices = 100 + np.cumsum(np.random.randn(250) * 0.02)
            
            return pd.DataFrame({
                'Open': prices + np.random.randn(250) * 0.5,
                'High': prices + abs(np.random.randn(250)) * 0.8,
                'Low': prices - abs(np.random.randn(250)) * 0.8,
                'Close': prices,
                'Volume': np.random.randint(1000000, 5000000, 250)
            }, index=dates)
    
    async def get_real_time_quote(self, symbol: str) -> Dict[str, Any]:
        """Get real-time quote (mock implementation or IBKR)"""
        if self.use_ibkr and self.ib_client and self.ib_client.connected:
            return await self.ib_client.get_real_time_quote(symbol)

        # Generate mock real-time data
        base_price = 150 + np.random.randn() * 10
        return {
            "symbol": symbol,
            "price": round(base_price, 2),
            "bid": round(base_price - 0.01, 2),
            "ask": round(base_price + 0.01, 2),
            "volume": np.random.randint(100000, 1000000),
            "timestamp": datetime.now().isoformat()
        }