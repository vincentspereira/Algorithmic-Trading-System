"""Multi-Source Data Feed Manager with Fallback Mechanism

Provides robust data feed management with automatic failover across multiple providers:
- Primary: Yahoo Finance
- Fallbacks: Alpha Vantage, Finnhub, Investing.com, CME Group, Twelve Data, Polygon, etc.
- Asset-specific provider chains with automatic switching on failure
- Kafka streaming for normalized data distribution
- Performance monitoring and logging
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from enum import Enum
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import json
import time
from contextlib import asynccontextmanager

import pandas as pd
import numpy as np
from pydantic import BaseModel, Field

from shared.config import settings
from kafka_service.producer import KafkaEventProducer
from database.data_access_layer import DataAccessLayer
from shared.utils.logging_utils import get_logger

# Configure logging
logger = get_logger(__name__)

class AssetClass(str, Enum):
    STOCK = "stock"
    ETF = "etf"
    FUTURE = "future"
    OPTION = "option"
    FOREX = "forex"
    COMMODITY = "commodity"
    CRYPTO = "crypto"

class DataProvider(str, Enum):
    YAHOO_FINANCE = "yahoo_finance"
    IBKR = "ibkr"
    ALPHA_VANTAGE = "alpha_vantage"
    FINNHUB = "finnhub"
    INVESTING_COM = "investing_com"
    CME_GROUP = "cme_group"
    TWELVE_DATA = "twelve_data"
    POLYGON = "polygon"
    BARCHART = "barchart"
    SPIDERROCK = "spiderrock"
    TRADING_CHARTS = "trading_charts"
    OANDA = "oanda"
    CBOE = "cboe"

class DataType(str, Enum):
    REAL_TIME = "real_time"
    HISTORICAL = "historical"
    OPTIONS_CHAIN = "options_chain"
    IMPLIED_VOLATILITY = "implied_volatility"
    DIVIDEND_FORECAST = "dividend_forecast"

@dataclass
class MarketDataPoint:
    """Normalized market data structure"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    asset_class: AssetClass
    provider: DataProvider
    data_type: DataType
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ProviderConfig:
    """Configuration for a data provider"""
    name: DataProvider
    base_url: str
    api_key: Optional[str] = None
    rate_limit_per_minute: int = 60
    timeout_seconds: float = 3.0
    retry_attempts: int = 3
    supported_asset_classes: List[AssetClass] = field(default_factory=list)
    supported_data_types: List[DataType] = field(default_factory=list)
    priority: int = 1  # Lower number = higher priority

class DataProviderInterface(ABC):
    """Abstract interface for data providers"""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.last_request_time = 0.0
        self.request_count = 0
        self.rate_limit_reset_time = time.time() + 60
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _rate_limit_check(self):
        """Check and enforce rate limits"""
        current_time = time.time()
        
        # Reset counter if minute has passed
        if current_time > self.rate_limit_reset_time:
            self.request_count = 0
            self.rate_limit_reset_time = current_time + 60
        
        # Check if we've exceeded rate limit
        if self.request_count >= self.config.rate_limit_per_minute:
            sleep_time = self.rate_limit_reset_time - current_time
            if sleep_time > 0:
                logger.warning(f"Rate limit reached for {self.config.name}, sleeping {sleep_time:.2f}s")
                await asyncio.sleep(sleep_time)
                self.request_count = 0
                self.rate_limit_reset_time = time.time() + 60
        
        self.request_count += 1
        self.last_request_time = current_time
    
    @abstractmethod
    async def get_real_time_data(self, symbol: str, asset_class: AssetClass) -> Optional[MarketDataPoint]:
        """Get real-time market data"""
        pass
    
    @abstractmethod
    async def get_historical_data(
        self, 
        symbol: str, 
        asset_class: AssetClass,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d"
    ) -> List[MarketDataPoint]:
        """Get historical market data"""
        pass
    
    @abstractmethod
    async def get_options_chain(self, symbol: str, expiration_date: datetime) -> List[MarketDataPoint]:
        """Get options chain data"""
        pass

class YahooFinanceProvider(DataProviderInterface):
    """Yahoo Finance data provider implementation"""
    
    def __init__(self):
        config = ProviderConfig(
            name=DataProvider.YAHOO_FINANCE,
            base_url="https://query1.finance.yahoo.com",
            rate_limit_per_minute=2000,  # Yahoo is quite generous
            timeout_seconds=5.0,
            supported_asset_classes=[AssetClass.STOCK, AssetClass.ETF, AssetClass.FOREX, AssetClass.CRYPTO],
            supported_data_types=[DataType.REAL_TIME, DataType.HISTORICAL],
            priority=1
        )
        super().__init__(config)
    
    async def get_real_time_data(self, symbol: str, asset_class: AssetClass) -> Optional[MarketDataPoint]:
        """Get real-time data from Yahoo Finance"""
        await self._rate_limit_check()
        
        try:
            url = f"{self.config.base_url}/v8/finance/chart/{symbol}"
            params = {
                "interval": "1m",
                "range": "1d",
                "includePrePost": "true"
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    result = data.get("chart", {}).get("result", [])
                    
                    if result and len(result) > 0:
                        chart_data = result[0]
                        timestamps = chart_data.get("timestamp", [])
                        indicators = chart_data.get("indicators", {}).get("quote", [])
                        
                        if timestamps and indicators and len(indicators) > 0:
                            quote = indicators[0]
                            latest_idx = -1
                            
                            return MarketDataPoint(
                                symbol=symbol,
                                timestamp=datetime.fromtimestamp(timestamps[latest_idx]),
                                open=quote["open"][latest_idx] or 0.0,
                                high=quote["high"][latest_idx] or 0.0,
                                low=quote["low"][latest_idx] or 0.0,
                                close=quote["close"][latest_idx] or 0.0,
                                volume=quote["volume"][latest_idx] or 0,
                                asset_class=asset_class,
                                provider=DataProvider.YAHOO_FINANCE,
                                data_type=DataType.REAL_TIME
                            )
                
        except Exception as e:
            logger.error(f"Yahoo Finance real-time data fetch failed for {symbol}: {e}")
        
        return None
    
    async def get_historical_data(
        self, 
        symbol: str, 
        asset_class: AssetClass,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d"
    ) -> List[MarketDataPoint]:
        """Get historical data from Yahoo Finance"""
        await self._rate_limit_check()
        
        try:
            start_timestamp = int(start_date.timestamp())
            end_timestamp = int(end_date.timestamp())
            
            url = f"{self.config.base_url}/v8/finance/chart/{symbol}"
            params = {
                "period1": start_timestamp,
                "period2": end_timestamp,
                "interval": interval,
                "includePrePost": "true"
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    result = data.get("chart", {}).get("result", [])
                    
                    if result and len(result) > 0:
                        chart_data = result[0]
                        timestamps = chart_data.get("timestamp", [])
                        indicators = chart_data.get("indicators", {}).get("quote", [])
                        
                        if timestamps and indicators and len(indicators) > 0:
                            quote = indicators[0]
                            data_points = []
                            
                            for i in range(len(timestamps)):
                                if all(quote[field][i] is not None for field in ["open", "high", "low", "close"]):
                                    data_points.append(MarketDataPoint(
                                        symbol=symbol,
                                        timestamp=datetime.fromtimestamp(timestamps[i]),
                                        open=quote["open"][i],
                                        high=quote["high"][i],
                                        low=quote["low"][i],
                                        close=quote["close"][i],
                                        volume=quote["volume"][i] or 0,
                                        asset_class=asset_class,
                                        provider=DataProvider.YAHOO_FINANCE,
                                        data_type=DataType.HISTORICAL
                                    ))
                            
                            return data_points
                
        except Exception as e:
            logger.error(f"Yahoo Finance historical data fetch failed for {symbol}: {e}")
        
        return []
    
    async def get_options_chain(self, symbol: str, expiration_date: datetime) -> List[MarketDataPoint]:
        """Yahoo Finance doesn't provide comprehensive options data"""
        return []

class AlphaVantageProvider(DataProviderInterface):
    """Alpha Vantage data provider implementation"""
    
    def __init__(self, api_key: str):
        config = ProviderConfig(
            name=DataProvider.ALPHA_VANTAGE,
            base_url="https://www.alphavantage.co/query",
            api_key=api_key,
            rate_limit_per_minute=5,  # Free tier limit
            timeout_seconds=10.0,
            supported_asset_classes=[AssetClass.STOCK, AssetClass.ETF, AssetClass.FOREX, AssetClass.CRYPTO],
            supported_data_types=[DataType.REAL_TIME, DataType.HISTORICAL],
            priority=3
        )
        super().__init__(config)
    
    async def get_real_time_data(self, symbol: str, asset_class: AssetClass) -> Optional[MarketDataPoint]:
        """Get real-time data from Alpha Vantage"""
        await self._rate_limit_check()
        
        try:
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": self.config.api_key
            }
            
            async with self.session.get(self.config.base_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    quote = data.get("Global Quote", {})
                    
                    if quote:
                        return MarketDataPoint(
                            symbol=symbol,
                            timestamp=datetime.now(),
                            open=float(quote.get("02. open", 0)),
                            high=float(quote.get("03. high", 0)),
                            low=float(quote.get("04. low", 0)),
                            close=float(quote.get("05. price", 0)),
                            volume=int(quote.get("06. volume", 0)),
                            asset_class=asset_class,
                            provider=DataProvider.ALPHA_VANTAGE,
                            data_type=DataType.REAL_TIME
                        )
                
        except Exception as e:
            logger.error(f"Alpha Vantage real-time data fetch failed for {symbol}: {e}")
        
        return None
    
    async def get_historical_data(
        self, 
        symbol: str, 
        asset_class: AssetClass,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d"
    ) -> List[MarketDataPoint]:
        """Get historical data from Alpha Vantage"""
        await self._rate_limit_check()
        
        try:
            function_map = {
                "1d": "TIME_SERIES_DAILY",
                "1h": "TIME_SERIES_INTRADAY",
                "5m": "TIME_SERIES_INTRADAY"
            }
            
            params = {
                "function": function_map.get(interval, "TIME_SERIES_DAILY"),
                "symbol": symbol,
                "apikey": self.config.api_key,
                "outputsize": "full"
            }
            
            if interval in ["1h", "5m"]:
                params["interval"] = interval
            
            async with self.session.get(self.config.base_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Find the time series key
                    time_series_key = None
                    for key in data.keys():
                        if "Time Series" in key:
                            time_series_key = key
                            break
                    
                    if time_series_key:
                        time_series = data[time_series_key]
                        data_points = []
                        
                        for date_str, values in time_series.items():
                            timestamp = datetime.strptime(date_str, "%Y-%m-%d")
                            
                            if start_date <= timestamp <= end_date:
                                data_points.append(MarketDataPoint(
                                    symbol=symbol,
                                    timestamp=timestamp,
                                    open=float(values.get("1. open", 0)),
                                    high=float(values.get("2. high", 0)),
                                    low=float(values.get("3. low", 0)),
                                    close=float(values.get("4. close", 0)),
                                    volume=int(values.get("5. volume", 0)),
                                    asset_class=asset_class,
                                    provider=DataProvider.ALPHA_VANTAGE,
                                    data_type=DataType.HISTORICAL
                                ))
                        
                        return sorted(data_points, key=lambda x: x.timestamp)
                
        except Exception as e:
            logger.error(f"Alpha Vantage historical data fetch failed for {symbol}: {e}")
        
        return []
    
    async def get_options_chain(self, symbol: str, expiration_date: datetime) -> List[MarketDataPoint]:
        """Alpha Vantage has limited options data"""
        return []

class DataFeedManager:
    """Main data feed manager with fallback mechanism"""
    
    def __init__(self):
        self.providers: Dict[DataProvider, DataProviderInterface] = {}
        self.asset_provider_chains: Dict[AssetClass, List[DataProvider]] = {}
        self.kafka_producer: Optional[KafkaEventProducer] = None
        self.failure_counts: Dict[DataProvider, int] = {}
        self.last_failure_time: Dict[DataProvider, datetime] = {}
        self.circuit_breaker_threshold = 5
        self.circuit_breaker_timeout = timedelta(minutes=5)
        
        self._setup_provider_chains()
        self._initialize_providers()
    
    def _setup_provider_chains(self):
        """Setup asset-specific provider fallback chains"""
        self.asset_provider_chains = {
            AssetClass.STOCK: [
                DataProvider.YAHOO_FINANCE,
                DataProvider.IBKR,
                DataProvider.ALPHA_VANTAGE,
                DataProvider.FINNHUB,
                DataProvider.TWELVE_DATA,
                DataProvider.POLYGON
            ],
            AssetClass.ETF: [
                DataProvider.YAHOO_FINANCE,
                DataProvider.IBKR,
                DataProvider.ALPHA_VANTAGE,
                DataProvider.TWELVE_DATA
            ],
            AssetClass.FUTURE: [
                DataProvider.IBKR,
                DataProvider.CME_GROUP,
                DataProvider.BARCHART
            ],
            AssetClass.OPTION: [
                DataProvider.YAHOO_FINANCE,
                DataProvider.IBKR,
                DataProvider.CBOE,
                DataProvider.SPIDERROCK
            ],
            AssetClass.FOREX: [
                DataProvider.YAHOO_FINANCE,
                DataProvider.OANDA,
                DataProvider.ALPHA_VANTAGE,
                DataProvider.TWELVE_DATA
            ],
            AssetClass.CRYPTO: [
                DataProvider.YAHOO_FINANCE,
                DataProvider.ALPHA_VANTAGE,
                DataProvider.TWELVE_DATA
            ]
        }
    
    def _initialize_providers(self):
        """Initialize available data providers"""
        # Initialize Yahoo Finance (free, no API key required)
        self.providers[DataProvider.YAHOO_FINANCE] = YahooFinanceProvider()
        
        # Initialize Alpha Vantage if API key is available
        alpha_vantage_key = getattr(settings, 'ALPHA_VANTAGE_API_KEY', None)
        if alpha_vantage_key:
            self.providers[DataProvider.ALPHA_VANTAGE] = AlphaVantageProvider(alpha_vantage_key)
        
        # TODO: Initialize other providers as needed
        # self.providers[DataProvider.FINNHUB] = FinnhubProvider(api_key)
        # self.providers[DataProvider.POLYGON] = PolygonProvider(api_key)
        # etc.
        
        logger.info(f"Initialized {len(self.providers)} data providers")
    
    async def start(self):
        """Start the data feed manager"""
        try:
            # Initialize Kafka producer for data streaming
            self.kafka_producer = KafkaEventProducer()
            await self.kafka_producer.start()
            
            logger.info("Data Feed Manager started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Data Feed Manager: {e}")
            raise
    
    async def stop(self):
        """Stop the data feed manager"""
        try:
            # Close all provider sessions
            for provider in self.providers.values():
                if hasattr(provider, 'session') and provider.session:
                    await provider.session.close()
            
            # Close Kafka producer
            if self.kafka_producer:
                await self.kafka_producer.close()
            
            logger.info("Data Feed Manager stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping Data Feed Manager: {e}")
    
    def _is_provider_available(self, provider: DataProvider) -> bool:
        """Check if provider is available (not in circuit breaker state)"""
        if provider not in self.failure_counts:
            return True
        
        failure_count = self.failure_counts[provider]
        last_failure = self.last_failure_time.get(provider)
        
        # Check if circuit breaker should be reset
        if (last_failure and 
            datetime.now() - last_failure > self.circuit_breaker_timeout):
            self.failure_counts[provider] = 0
            return True
        
        return failure_count < self.circuit_breaker_threshold
    
    def _record_provider_failure(self, provider: DataProvider):
        """Record a provider failure for circuit breaker logic"""
        self.failure_counts[provider] = self.failure_counts.get(provider, 0) + 1
        self.last_failure_time[provider] = datetime.now()
        
        if self.failure_counts[provider] >= self.circuit_breaker_threshold:
            logger.warning(f"Circuit breaker activated for {provider} after {self.failure_counts[provider]} failures")
    
    def _record_provider_success(self, provider: DataProvider):
        """Record a provider success (reset failure count)"""
        if provider in self.failure_counts:
            self.failure_counts[provider] = 0
    
    async def get_real_time_data(
        self, 
        symbol: str, 
        asset_class: AssetClass
    ) -> Optional[MarketDataPoint]:
        """Get real-time data with automatic fallback"""
        provider_chain = self.asset_provider_chains.get(asset_class, [])
        
        for provider_name in provider_chain:
            if (provider_name in self.providers and 
                self._is_provider_available(provider_name)):
                
                provider = self.providers[provider_name]
                
                try:
                    start_time = time.time()
                    
                    async with provider:
                        data = await provider.get_real_time_data(symbol, asset_class)
                    
                    fetch_time = (time.time() - start_time) * 1000  # Convert to ms
                    
                    if data:
                        self._record_provider_success(provider_name)
                        
                        # Stream to Kafka
                        if self.kafka_producer:
                            await self._stream_to_kafka(data, "real_time_data")
                        
                        # Log successful fetch
                        logger.debug(f"Real-time data fetched for {symbol} from {provider_name} in {fetch_time:.2f}ms")
                        
                        return data
                    
                except Exception as e:
                    self._record_provider_failure(provider_name)
                    logger.warning(f"Provider {provider_name} failed for {symbol}: {e}")
                    
                    # If fetch took too long, consider it a timeout failure
                    if time.time() - start_time > 3.0:
                        logger.warning(f"Provider {provider_name} timeout for {symbol}")
                    
                    continue
        
        logger.error(f"All providers failed for real-time data: {symbol} ({asset_class})")
        return None
    
    async def get_historical_data(
        self,
        symbol: str,
        asset_class: AssetClass,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d"
    ) -> List[MarketDataPoint]:
        """Get historical data with automatic fallback"""
        provider_chain = self.asset_provider_chains.get(asset_class, [])
        
        for provider_name in provider_chain:
            if (provider_name in self.providers and 
                self._is_provider_available(provider_name)):
                
                provider = self.providers[provider_name]
                
                try:
                    start_time = time.time()
                    
                    async with provider:
                        data = await provider.get_historical_data(
                            symbol, asset_class, start_date, end_date, interval
                        )
                    
                    fetch_time = (time.time() - start_time) * 1000
                    
                    if data:
                        self._record_provider_success(provider_name)
                        
                        # Stream to Kafka
                        if self.kafka_producer:
                            for data_point in data:
                                await self._stream_to_kafka(data_point, "historical_data")
                        
                        logger.info(f"Historical data fetched for {symbol}: {len(data)} points from {provider_name} in {fetch_time:.2f}ms")
                        
                        return data
                    
                except Exception as e:
                    self._record_provider_failure(provider_name)
                    logger.warning(f"Provider {provider_name} failed for historical {symbol}: {e}")
                    continue
        
        logger.error(f"All providers failed for historical data: {symbol} ({asset_class})")
        return []
    
    async def _stream_to_kafka(self, data: MarketDataPoint, topic_suffix: str):
        """Stream normalized data to Kafka"""
        try:
            topic = f"market_data.{data.asset_class.value}.{topic_suffix}"
            
            message = {
                "symbol": data.symbol,
                "timestamp": data.timestamp.isoformat(),
                "open": data.open,
                "high": data.high,
                "low": data.low,
                "close": data.close,
                "volume": data.volume,
                "asset_class": data.asset_class.value,
                "provider": data.provider.value,
                "data_type": data.data_type.value,
                "metadata": data.metadata
            }
            
            await self.kafka_producer.send_message(topic, message)
            
        except Exception as e:
            logger.error(f"Failed to stream data to Kafka: {e}")
    
    async def get_provider_health_status(self) -> Dict[str, Any]:
        """Get health status of all providers"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "providers": {},
            "circuit_breakers": {}
        }
        
        for provider_name, provider in self.providers.items():
            failure_count = self.failure_counts.get(provider_name, 0)
            last_failure = self.last_failure_time.get(provider_name)
            is_available = self._is_provider_available(provider_name)
            
            status["providers"][provider_name.value] = {
                "available": is_available,
                "failure_count": failure_count,
                "last_failure": last_failure.isoformat() if last_failure else None,
                "supported_assets": [ac.value for ac in provider.config.supported_asset_classes],
                "rate_limit_per_minute": provider.config.rate_limit_per_minute
            }
            
            if failure_count >= self.circuit_breaker_threshold:
                status["circuit_breakers"][provider_name.value] = {
                    "active": True,
                    "failure_count": failure_count,
                    "reset_time": (last_failure + self.circuit_breaker_timeout).isoformat() if last_failure else None
                }
        
        return status

# Global instance
data_feed_manager = DataFeedManager()

# Async context manager for easy usage
@asynccontextmanager
async def get_data_feed_manager():
    """Async context manager for data feed manager"""
    await data_feed_manager.start()
    try:
        yield data_feed_manager
    finally:
        await data_feed_manager.stop()