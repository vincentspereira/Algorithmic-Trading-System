"""Finnhub data provider implementation"""

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
class FinnhubConfig:
    """Finnhub API configuration"""
    api_key: str
    base_url: str = "https://finnhub.io/api/v1"
    timeout: float = 5.0
    rate_limit: int = 60  # requests per minute

class FinnhubProvider(BaseDataProvider):
    """Finnhub data provider for stocks, forex, and crypto"""
    
    def __init__(self, api_key: str, config: Optional[FinnhubConfig] = None):
        super().__init__("finnhub")
        self.api_key = api_key
        self.config = config or FinnhubConfig(api_key=api_key)
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
        """Create rate limiter for Finnhub API"""
        # Implement basic rate limiting
        return None  # Placeholder
        
    async def get_quote(self, symbol: str) -> Optional[Quote]:
        """Get real-time quote for a symbol"""
        try:
            url = f"{self.config.base_url}/quote"
            params = {
                'symbol': symbol.upper(),
                'token': self.api_key
            }
            
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                )
                
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if 'c' in data and data['c'] is not None:
                        return Quote(
                            symbol=symbol,
                            bid=data.get('c', 0.0),  # Current price as bid
                            ask=data.get('c', 0.0),  # Current price as ask
                            last=data.get('c', 0.0),  # Current price
                            volume=0,  # Finnhub doesn't provide volume in quote
                            timestamp=datetime.now(),
                            provider="finnhub"
                        )
                else:
                    logger.error(f"Finnhub API error: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error fetching quote from Finnhub: {e}")
            
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
            # Convert dates to Unix timestamps
            start_ts = int(start_date.timestamp())
            end_ts = int(end_date.timestamp())
            
            # Map interval to Finnhub resolution
            resolution_map = {
                "1m": "1",
                "5m": "5", 
                "15m": "15",
                "30m": "30",
                "1h": "60",
                "D": "D",
                "W": "W",
                "M": "M"
            }
            
            resolution = resolution_map.get(interval, "D")
            
            url = f"{self.config.base_url}/stock/candle"
            params = {
                'symbol': symbol.upper(),
                'resolution': resolution,
                'from': start_ts,
                'to': end_ts,
                'token': self.api_key
            }
            
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                )
                
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get('s') == 'ok' and 'c' in data:
                        bars = []
                        timestamps = data['t']
                        opens = data['o']
                        highs = data['h']
                        lows = data['l']
                        closes = data['c']
                        volumes = data['v']
                        
                        for i in range(len(timestamps)):
                            bar = Bar(
                                symbol=symbol,
                                timestamp=datetime.fromtimestamp(timestamps[i]),
                                open=opens[i],
                                high=highs[i],
                                low=lows[i],
                                close=closes[i],
                                volume=volumes[i],
                                provider="finnhub"
                            )
                            bars.append(bar)
                            
                        return bars
                else:
                    logger.error(f"Finnhub historical data API error: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error fetching historical data from Finnhub: {e}")
            
        return []
        
    async def get_company_profile(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get company profile information"""
        try:
            url = f"{self.config.base_url}/stock/profile2"
            params = {
                'symbol': symbol.upper(),
                'token': self.api_key
            }
            
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                )
                
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    logger.error(f"Finnhub company profile API error: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error fetching company profile from Finnhub: {e}")
            
        return None
        
    async def get_news(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get company news"""
        try:
            url = f"{self.config.base_url}/company-news"
            
            # Get news from last 30 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            params = {
                'symbol': symbol.upper(),
                'from': start_date.strftime('%Y-%m-%d'),
                'to': end_date.strftime('%Y-%m-%d'),
                'token': self.api_key
            }
            
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                )
                
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data[:limit] if data else []
                else:
                    logger.error(f"Finnhub news API error: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error fetching news from Finnhub: {e}")
            
        return []
        
    def is_supported_symbol(self, symbol: str) -> bool:
        """Check if symbol is supported by Finnhub"""
        # Finnhub supports most US stocks, some international stocks, forex, and crypto
        return True  # Basic implementation
        
    def get_supported_intervals(self) -> List[str]:
        """Get supported time intervals"""
        return ["1m", "5m", "15m", "30m", "1h", "D", "W", "M"]
        
    async def health_check(self) -> bool:
        """Check if the provider is healthy"""
        try:
            # Test with a simple API call
            url = f"{self.config.base_url}/quote"
            params = {
                'symbol': 'AAPL',
                'token': self.api_key
            }
            
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                )
                
            async with self.session.get(url, params=params) as response:
                return response.status == 200
                
        except Exception as e:
            logger.error(f"Finnhub health check failed: {e}")
            return False