"""Twelve Data provider implementation"""

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
class TwelveDataConfig:
    """Twelve Data API configuration"""
    api_key: str
    base_url: str = "https://api.twelvedata.com"
    timeout: float = 5.0
    rate_limit: int = 8  # requests per minute for free tier

class TwelveDataProvider(BaseDataProvider):
    """Twelve Data provider for stocks, ETFs, forex, and crypto"""
    
    def __init__(self, api_key: str, config: Optional[TwelveDataConfig] = None):
        super().__init__("twelve_data")
        self.api_key = api_key
        self.config = config or TwelveDataConfig(api_key=api_key)
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
        """Create rate limiter for Twelve Data API"""
        # Implement basic rate limiting
        return None  # Placeholder
        
    async def get_quote(self, symbol: str) -> Optional[Quote]:
        """Get real-time quote for a symbol"""
        try:
            url = f"{self.config.base_url}/price"
            params = {
                'symbol': symbol.upper(),
                'apikey': self.api_key
            }
            
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                )
                
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if 'price' in data:
                        price = float(data['price'])
                        return Quote(
                            symbol=symbol,
                            bid=price,  # Use price as bid
                            ask=price,  # Use price as ask
                            last=price,  # Last price
                            volume=0,  # Twelve Data doesn't provide volume in price endpoint
                            timestamp=datetime.now(),
                            provider="twelve_data"
                        )
                else:
                    logger.error(f"Twelve Data API error: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error fetching quote from Twelve Data: {e}")
            
        return None
        
    async def get_historical_data(
        self, 
        symbol: str, 
        start_date: datetime, 
        end_date: datetime,
        interval: str = "1day"
    ) -> List[Bar]:
        """Get historical data for a symbol"""
        try:
            # Map interval to Twelve Data format
            interval_map = {
                "1m": "1min",
                "5m": "5min",
                "15m": "15min",
                "30m": "30min",
                "1h": "1h",
                "D": "1day",
                "W": "1week",
                "M": "1month"
            }
            
            td_interval = interval_map.get(interval, "1day")
            
            url = f"{self.config.base_url}/time_series"
            params = {
                'symbol': symbol.upper(),
                'interval': td_interval,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'apikey': self.api_key,
                'format': 'JSON'
            }
            
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                )
                
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if 'values' in data and data['values']:
                        bars = []
                        for value in reversed(data['values']):  # Reverse to get chronological order
                            try:
                                bar = Bar(
                                    symbol=symbol,
                                    timestamp=datetime.strptime(value['datetime'], '%Y-%m-%d %H:%M:%S'),
                                    open=float(value['open']),
                                    high=float(value['high']),
                                    low=float(value['low']),
                                    close=float(value['close']),
                                    volume=int(value.get('volume', 0)),
                                    provider="twelve_data"
                                )
                                bars.append(bar)
                            except (ValueError, KeyError) as e:
                                logger.warning(f"Skipping invalid bar data: {e}")
                                continue
                                
                        return bars
                else:
                    logger.error(f"Twelve Data historical data API error: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error fetching historical data from Twelve Data: {e}")
            
        return []
        
    async def get_real_time_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get real-time price with additional data"""
        try:
            url = f"{self.config.base_url}/quote"
            params = {
                'symbol': symbol.upper(),
                'apikey': self.api_key
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
                    logger.error(f"Twelve Data quote API error: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error fetching real-time price from Twelve Data: {e}")
            
        return None
        
    async def get_technical_indicators(
        self, 
        symbol: str, 
        indicator: str, 
        interval: str = "1day",
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Get technical indicators"""
        try:
            url = f"{self.config.base_url}/{indicator.lower()}"
            params = {
                'symbol': symbol.upper(),
                'interval': interval,
                'apikey': self.api_key,
                **kwargs
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
                    logger.error(f"Twelve Data technical indicators API error: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error fetching technical indicators from Twelve Data: {e}")
            
        return None
        
    async def get_forex_pairs(self) -> List[str]:
        """Get available forex pairs"""
        try:
            url = f"{self.config.base_url}/forex_pairs"
            params = {'apikey': self.api_key}
            
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                )
                
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return [pair['symbol'] for pair in data.get('data', [])]
                else:
                    logger.error(f"Twelve Data forex pairs API error: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error fetching forex pairs from Twelve Data: {e}")
            
        return []
        
    async def get_crypto_currencies(self) -> List[str]:
        """Get available cryptocurrencies"""
        try:
            url = f"{self.config.base_url}/cryptocurrencies"
            params = {'apikey': self.api_key}
            
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                )
                
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return [crypto['symbol'] for crypto in data.get('data', [])]
                else:
                    logger.error(f"Twelve Data crypto currencies API error: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error fetching crypto currencies from Twelve Data: {e}")
            
        return []
        
    def is_supported_symbol(self, symbol: str) -> bool:
        """Check if symbol is supported by Twelve Data"""
        # Twelve Data supports stocks, ETFs, forex, and crypto
        return True  # Basic implementation
        
    def get_supported_intervals(self) -> List[str]:
        """Get supported time intervals"""
        return ["1m", "5m", "15m", "30m", "1h", "D", "W", "M"]
        
    def get_supported_indicators(self) -> List[str]:
        """Get supported technical indicators"""
        return [
            "sma", "ema", "wma", "dema", "tema", "trima", "kama", "mama",
            "rsi", "macd", "stoch", "adx", "cci", "aroon", "bbands",
            "ad", "obv", "ht_trendline", "sar", "adosc"
        ]
        
    async def health_check(self) -> bool:
        """Check if the provider is healthy"""
        try:
            # Test with a simple API call
            url = f"{self.config.base_url}/price"
            params = {
                'symbol': 'AAPL',
                'apikey': self.api_key
            }
            
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                )
                
            async with self.session.get(url, params=params) as response:
                return response.status == 200
                
        except Exception as e:
            logger.error(f"Twelve Data health check failed: {e}")
            return False