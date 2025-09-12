"""Yahoo Finance data provider implementation"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import yfinance as yf
from dataclasses import dataclass

from ..models import MarketData, Quote, Trade, Bar
from .base_provider import BaseDataProvider

logger = logging.getLogger(__name__)

class YahooFinanceProvider(BaseDataProvider):
    """Yahoo Finance data provider for stocks, forex, and crypto"""
    
    def __init__(self):
        super().__init__("yahoo_finance")
        
    async def get_quote(self, symbol: str) -> Optional[Quote]:
        """Get real-time quote for a symbol"""
        try:
            ticker = await asyncio.to_thread(yf.Ticker, symbol)
            info = ticker.info
            return Quote(
                symbol=symbol,
                bid=info.get('bid', 0.0),
                ask=info.get('ask', 0.0),
                last=info.get('regularMarketPrice', 0.0),
                volume=info.get('regularMarketVolume', 0),
                timestamp=datetime.now(),
                provider="yahoo_finance"
            )
        except Exception as e:
            logger.error(f"Error fetching quote from Yahoo Finance: {e}")
            return None
        
    async def get_historical_data(
        self, 
        symbol: str, 
        start_date: datetime, 
        end_date: datetime,
        interval: str = "1d"
    ) -> List[Bar]:
        """Get historical data for a symbol"""
        try:
            data = await asyncio.to_thread(
                yf.download,
                symbol,
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d'),
                interval=interval
            )
            
            bars = []
            for idx, row in data.iterrows():
                bar = Bar(
                    symbol=symbol,
                    timestamp=idx,
                    open=row['Open'],
                    high=row['High'],
                    low=row['Low'],
                    close=row['Close'],
                    volume=row['Volume'],
                    provider="yahoo_finance"
                )
                bars.append(bar)
                
            return bars
            
        except Exception as e:
            logger.error(f"Error fetching historical data from Yahoo Finance: {e}")
            return []
        
    async def get_company_profile(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get company profile information"""
        try:
            ticker = await asyncio.to_thread(yf.Ticker, symbol)
            return ticker.info
        except Exception as e:
            logger.error(f"Error fetching company profile from Yahoo Finance: {e}")
            return None
        
    async def get_news(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get company news"""
        try:
            ticker = await asyncio.to_thread(yf.Ticker, symbol)
            news = ticker.news
            return news[:limit] if news else []
        except Exception as e:
            logger.error(f"Error fetching news from Yahoo Finance: {e}")
            return []
        
    def is_supported_symbol(self, symbol: str) -> bool:
        """Check if symbol is supported by Yahoo Finance"""
        return True
        
    def get_supported_intervals(self) -> List[str]:
        """Get supported time intervals"""
        return ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"]
        
    async def health_check(self) -> bool:
        """Check if the provider is healthy"""
        try:
            test = await self.get_quote('AAPL')
            return test is not None
        except Exception:
            return False