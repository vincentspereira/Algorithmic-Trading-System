"""Polygon.io data provider implementation"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import aiohttp
from dataclasses import dataclass

from ..config import ProviderAPIConfig
from ..models import MarketData, Quote, Trade, Bar
from .base_provider import BaseDataProvider

logger = logging.getLogger(__name__)

@dataclass
class PolygonConfig:
    """Polygon.io API configuration"""
    api_key: str
    base_url: str = "https://api.polygon.io"
    timeout: float = 5.0
    rate_limit: int = 5  # requests per minute for free tier

class PolygonProvider(BaseDataProvider):
    """Polygon.io data provider for stocks, options, forex, and crypto"""
    
    def __init__(self, api_key: str, config: Optional[PolygonConfig] = None):
        super().__init__("polygon")
        self.api_key = api_key
        self.config = config or PolygonConfig(api_key=api_key)
        self.session: Optional[aiohttp.ClientSession] = None
        self._rate_limiter = self._create_rate_limiter()
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            
    def _create_rate_limiter(self):
        """Create rate limiter for Polygon API"""
        # Implement basic rate limiting
        return None  # Placeholder
        
    async def get_quote(self, symbol: str) -> Optional[Quote]:
        """Get real-time quote for a symbol"""
        try:
            url = f"{self.config.base_url}/v2/last/trade/{symbol.upper()}"
            params = {'apikey': self.api_key}
            
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                )
                
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if 'results' in data and data['results']:
                        result = data['results']
                        return Quote(
                            symbol=symbol,
                            bid=result.get('p', 0.0),  # Last trade price as bid
                            ask=result.get('p', 0.0),  # Last trade price as ask
                            last=result.get('p', 0.0),  # Last trade price
                            volume=result.get('s', 0),  # Last trade size
                            timestamp=datetime.fromtimestamp(result.get('t', 0) / 1000),
                            provider="polygon"
                        )
                else:
                    logger.error(f"Polygon API error: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error fetching quote from Polygon: {e}")
            
        return None
        
    async def get_historical_data(
        self, 
        symbol: str, 
        start_date: datetime, 
        end_date: datetime,
        interval: str = "D"
    ) -> List[Bar]:
        """Get historical data for a symbol"""
        try:
            # Map interval to Polygon timespan
            timespan_map = {
                "1m": "minute",
                "5m": "minute",
                "15m": "minute",
                "30m": "minute",
                "1h": "hour",
                "D": "day",
                "W": "week",
                "M": "month"
            }
            
            multiplier_map = {
                "1m": 1,
                "5m": 5,
                "15m": 15,
                "30m": 30,
                "1h": 1,
                "D": 1,
                "W": 1,
                "M": 1
            }
            
            timespan = timespan_map.get(interval, "day")
            multiplier = multiplier_map.get(interval, 1)
            
            # Format dates for Polygon API
            from_date = start_date.strftime('%Y-%m-%d')
            to_date = end_date.strftime('%Y-%m-%d')
            
            url = f"{self.config.base_url}/v2/aggs/ticker/{symbol.upper()}/range/{multiplier}/{timespan}/{from_date}/{to_date}"
            params = {
                'adjusted': 'true',
                'sort': 'asc',
                'apikey': self.api_key
            }
            
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                )
                
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get('status') == 'OK' and 'results' in data:
                        bars = []
                        for result in data['results']:
                            bar = Bar(
                                symbol=symbol,
                                timestamp=datetime.fromtimestamp(result['t'] / 1000),
                                open=result['o'],
                                high=result['h'],
                                low=result['l'],
                                close=result['c'],
                                volume=result['v'],
                                provider="polygon"
                            )
                            bars.append(bar)
                            
                        return bars
                else:
                    logger.error(f"Polygon historical data API error: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error fetching historical data from Polygon: {e}")
            
        return []
        
    async def get_ticker_details(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get ticker details"""
        try:
            url = f"{self.config.base_url}/v3/reference/tickers/{symbol.upper()}"
            params = {'apikey': self.api_key}
            
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                )
                
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('results', {})
                else:
                    logger.error(f"Polygon ticker details API error: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error fetching ticker details from Polygon: {e}")
            
        return None
        
    async def get_market_status(self) -> Optional[Dict[str, Any]]:
        """Get market status"""
        try:
            url = f"{self.config.base_url}/v1/marketstatus/now"
            params = {'apikey': self.api_key}
            
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                )
                
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    logger.error(f"Polygon market status API error: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error fetching market status from Polygon: {e}")
            
        return None
        
    async def get_trades(self, symbol: str, limit: int = 100) -> List[Trade]:
        """Get recent trades for a symbol"""
        try:
            url = f"{self.config.base_url}/v3/trades/{symbol.upper()}"
            params = {
                'limit': limit,
                'apikey': self.api_key
            }
            
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                )
                
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    trades = []
                    if 'results' in data:
                        for result in data['results']:
                            trade = Trade(
                                symbol=symbol,
                                price=result.get('price', 0.0),
                                size=result.get('size', 0),
                                timestamp=datetime.fromtimestamp(result.get('participant_timestamp', 0) / 1000000000),
                                provider="polygon"
                            )
                            trades.append(trade)
                            
                    return trades
                else:
                    logger.error(f"Polygon trades API error: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error fetching trades from Polygon: {e}")
            
        return []
        
    def is_supported_symbol(self, symbol: str) -> bool:
        """Check if symbol is supported by Polygon"""
        # Polygon supports US stocks, options, forex, and crypto
        return True  # Basic implementation
        
    def get_supported_intervals(self) -> List[str]:
        """Get supported time intervals"""
        return ["1m", "5m", "15m", "30m", "1h", "D", "W", "M"]
        
    async def health_check(self) -> bool:
        """Check if the provider is healthy"""
        try:
            # Test with market status endpoint
            url = f"{self.config.base_url}/v1/marketstatus/now"
            params = {'apikey': self.api_key}
            
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                )
                
            async with self.session.get(url, params=params) as response:
                return response.status == 200
                
        except Exception as e:
            logger.error(f"Polygon health check failed: {e}")
            return False