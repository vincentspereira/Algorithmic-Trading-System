"""
Mock Data Feed Manager for API Testing
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import yfinance as yf

class DataFeedManager:
    """Mock data feed manager for testing the API"""
    
    def __init__(self):
        self.initialized = False
        
    async def initialize(self):
        """Initialize the data feed manager"""
        self.initialized = True
        
    async def cleanup(self):
        """Cleanup resources"""
        self.initialized = False
        
    async def health_check(self) -> bool:
        """Check if data feeds are healthy"""
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
        """Get real-time quote (mock implementation)"""
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