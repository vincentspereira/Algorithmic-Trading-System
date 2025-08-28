"""
Market Data Service

This service is responsible for ingesting, processing, and distributing
real-time and historical market data across the algorithmic trading system.
It provides normalized data feeds from multiple sources with fallback mechanisms.

Key Features:
- Multi-source data ingestion (Yahoo Finance, Alpha Vantage, Finnhub, etc.)
- Real-time tick data processing
- Historical data management
- Data validation and normalization
- Fallback mechanisms for data source failures
- Caching and storage optimization
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Import shared utilities
try:
    from shared.utils import (
        format_price, validate_symbol, parse_timestamp,
        retry, handle_error, TradingSystemError, NetworkError
    )
    from shared.utils.rate_limiting import RateLimiter, RateLimitRule, RateLimitAlgorithm
except ImportError:
    # Fallback for development
    logging.warning("Shared utilities not found, using local implementations")
    from decimal import Decimal
    
    def format_price(price, symbol=None, decimals=None):
        return f"{float(price):.2f}"
    
    def validate_symbol(symbol):
        return bool(symbol and isinstance(symbol, str))


logger = logging.getLogger(__name__)


@dataclass
class MarketDataTick:
    """Market data tick structure"""
    symbol: str
    timestamp: datetime
    bid: Optional[float] = None
    ask: Optional[float] = None
    last: Optional[float] = None
    volume: Optional[int] = None
    high: Optional[float] = None
    low: Optional[float] = None
    open: Optional[float] = None
    source: str = "unknown"


@dataclass
class DataSourceConfig:
    """Configuration for data sources"""
    name: str
    url: str
    api_key: Optional[str] = None
    rate_limit: int = 100
    timeout: int = 30
    priority: int = 1  # Lower number = higher priority
    is_enabled: bool = True


class MarketDataService:
    """
    Main market data service for the algorithmic trading system.
    
    Provides unified interface for market data from multiple sources
    with automatic failover and data validation.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize market data service.
        
        Args:
            config: Service configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Data sources configuration
        self.data_sources: List[DataSourceConfig] = []
        self._initialize_data_sources()
        
        # Rate limiters for each source
        self.rate_limiters: Dict[str, RateLimiter] = {}
        self._initialize_rate_limiters()
        
        # Data cache
        self.data_cache: Dict[str, MarketDataTick] = {}
        self.cache_ttl = config.get('cache_ttl', 300)  # 5 minutes default
        
        # Subscription management
        self.subscriptions: Dict[str, List[callable]] = {}
        
        # Service state
        self.is_running = False
        self._tasks: List[asyncio.Task] = []
    
    def _initialize_data_sources(self) -> None:
        """Initialize data source configurations"""
        default_sources = [
            DataSourceConfig(
                name="yahoo_finance",
                url="https://query1.finance.yahoo.com/v8/finance/chart/",
                rate_limit=2000,  # 2000 requests per hour
                priority=1
            ),
            DataSourceConfig(
                name="alpha_vantage",
                url="https://www.alphavantage.co/query",
                api_key=self.config.get('alpha_vantage_api_key'),
                rate_limit=5,  # 5 requests per minute for free tier
                priority=2
            ),
            DataSourceConfig(
                name="finnhub",
                url="https://finnhub.io/api/v1/",
                api_key=self.config.get('finnhub_api_key'),
                rate_limit=60,  # 60 requests per minute
                priority=3
            )
        ]
        
        # Load from config or use defaults
        sources_config = self.config.get('data_sources', [])
        if sources_config:
            self.data_sources = [DataSourceConfig(**src) for src in sources_config]
        else:
            self.data_sources = default_sources
        
        # Sort by priority
        self.data_sources.sort(key=lambda x: x.priority)
        
        self.logger.info(f"Initialized {len(self.data_sources)} data sources")
    
    def _initialize_rate_limiters(self) -> None:
        """Initialize rate limiters for each data source"""
        for source in self.data_sources:
            if source.is_enabled:
                rule = RateLimitRule(
                    limit=source.rate_limit,
                    window_seconds=3600,  # 1 hour window
                    algorithm=RateLimitAlgorithm.SLIDING_WINDOW
                )
                self.rate_limiters[source.name] = RateLimiter(rule)
        
        self.logger.info(f"Initialized rate limiters for {len(self.rate_limiters)} sources")
    
    async def start(self) -> None:
        """Start the market data service"""
        if self.is_running:
            self.logger.warning("Service is already running")
            return
        
        self.logger.info("Starting market data service")
        self.is_running = True
        
        # Start background tasks
        self._tasks.append(asyncio.create_task(self._data_cleanup_task()))
        
        self.logger.info("Market data service started successfully")
    
    async def stop(self) -> None:
        """Stop the market data service"""
        if not self.is_running:
            return
        
        self.logger.info("Stopping market data service")
        self.is_running = False
        
        # Cancel all background tasks
        for task in self._tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        self._tasks.clear()
        self.logger.info("Market data service stopped")
    
    async def get_quote(self, symbol: str, source: Optional[str] = None) -> Optional[MarketDataTick]:
        """
        Get current quote for a symbol.
        
        Args:
            symbol: Trading symbol to get quote for
            source: Specific data source to use (optional)
            
        Returns:
            MarketDataTick object or None if not available
        """
        if not validate_symbol(symbol):
            raise TradingSystemError(f"Invalid symbol: {symbol}")
        
        symbol = symbol.upper()
        
        # Check cache first
        cached_tick = self._get_from_cache(symbol)
        if cached_tick and self._is_cache_valid(cached_tick):
            return cached_tick
        
        # Determine sources to try
        sources_to_try = [s for s in self.data_sources if s.is_enabled]
        if source:
            sources_to_try = [s for s in sources_to_try if s.name == source]
        
        # Try each source in priority order
        for data_source in sources_to_try:
            try:
                # Check rate limits
                rate_limiter = self.rate_limiters.get(data_source.name)
                if rate_limiter:
                    result, info = await rate_limiter.check_limit(symbol)
                    if result.name == "DENIED":
                        self.logger.warning(f"Rate limit exceeded for {data_source.name}")
                        continue
                
                # Fetch data from source
                tick = await self._fetch_from_source(symbol, data_source)
                if tick:
                    # Cache the result
                    self._cache_tick(tick)
                    return tick
                    
            except Exception as e:
                self.logger.error(f"Error fetching from {data_source.name}: {e}")
                continue
        
        self.logger.warning(f"Failed to get quote for {symbol} from all sources")
        return None
    
    async def subscribe_to_symbol(self, symbol: str, callback: callable) -> bool:
        """
        Subscribe to real-time updates for a symbol.
        
        Args:
            symbol: Trading symbol to subscribe to
            callback: Function to call when data is updated
            
        Returns:
            True if subscription successful, False otherwise
        """
        if not validate_symbol(symbol):
            raise TradingSystemError(f"Invalid symbol: {symbol}")
        
        symbol = symbol.upper()
        
        if symbol not in self.subscriptions:
            self.subscriptions[symbol] = []
        
        if callback not in self.subscriptions[symbol]:
            self.subscriptions[symbol].append(callback)
            self.logger.info(f"Added subscription for {symbol}")
            return True
        
        return False
    
    async def unsubscribe_from_symbol(self, symbol: str, callback: callable) -> bool:
        """
        Unsubscribe from real-time updates for a symbol.
        
        Args:
            symbol: Trading symbol to unsubscribe from
            callback: Callback function to remove
            
        Returns:
            True if unsubscription successful, False otherwise
        """
        symbol = symbol.upper()
        
        if symbol in self.subscriptions and callback in self.subscriptions[symbol]:
            self.subscriptions[symbol].remove(callback)
            if not self.subscriptions[symbol]:
                del self.subscriptions[symbol]
            self.logger.info(f"Removed subscription for {symbol}")
            return True
        
        return False
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        Get current service status.
        
        Returns:
            Dictionary containing service status information
        """
        return {
            "is_running": self.is_running,
            "data_sources": [
                {
                    "name": source.name,
                    "enabled": source.is_enabled,
                    "priority": source.priority
                }
                for source in self.data_sources
            ],
            "active_subscriptions": len(self.subscriptions),
            "cache_size": len(self.data_cache),
            "background_tasks": len(self._tasks)
        }
    
    async def _fetch_from_source(self, symbol: str, source: DataSourceConfig) -> Optional[MarketDataTick]:
        """
        Fetch market data from a specific source.
        
        Args:
            symbol: Trading symbol
            source: Data source configuration
            
        Returns:
            MarketDataTick or None
        """
        try:
            if source.name == "yahoo_finance":
                return await self._fetch_yahoo_finance(symbol, source)
            elif source.name == "alpha_vantage":
                return await self._fetch_alpha_vantage(symbol, source)
            elif source.name == "finnhub":
                return await self._fetch_finnhub(symbol, source)
            else:
                self.logger.warning(f"Unknown data source: {source.name}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error fetching from {source.name}: {e}")
            return None
    
    async def _fetch_yahoo_finance(self, symbol: str, source: DataSourceConfig) -> Optional[MarketDataTick]:
        """Fetch data from Yahoo Finance"""
        # Implementation would go here
        # For now, return mock data
        return MarketDataTick(
            symbol=symbol,
            timestamp=datetime.now(),
            last=100.0,
            bid=99.95,
            ask=100.05,
            volume=1000000,
            source=source.name
        )
    
    async def _fetch_alpha_vantage(self, symbol: str, source: DataSourceConfig) -> Optional[MarketDataTick]:
        """Fetch data from Alpha Vantage"""
        # Implementation would go here
        return None
    
    async def _fetch_finnhub(self, symbol: str, source: DataSourceConfig) -> Optional[MarketDataTick]:
        """Fetch data from Finnhub"""
        # Implementation would go here
        return None
    
    def _get_from_cache(self, symbol: str) -> Optional[MarketDataTick]:
        """Get tick data from cache"""
        return self.data_cache.get(symbol)
    
    def _is_cache_valid(self, tick: MarketDataTick) -> bool:
        """Check if cached tick is still valid"""
        age = (datetime.now() - tick.timestamp).total_seconds()
        return age < self.cache_ttl
    
    def _cache_tick(self, tick: MarketDataTick) -> None:
        """Cache tick data"""
        self.data_cache[tick.symbol] = tick
    
    async def _data_cleanup_task(self) -> None:
        """Background task to clean up old cached data"""
        while self.is_running:
            try:
                current_time = datetime.now()
                expired_symbols = []
                
                for symbol, tick in self.data_cache.items():
                    age = (current_time - tick.timestamp).total_seconds()
                    if age > self.cache_ttl:
                        expired_symbols.append(symbol)
                
                for symbol in expired_symbols:
                    del self.data_cache[symbol]
                
                if expired_symbols:
                    self.logger.debug(f"Cleaned up {len(expired_symbols)} expired cache entries")
                
                # Sleep for 60 seconds before next cleanup
                await asyncio.sleep(60)
                
            except Exception as e:
                self.logger.error(f"Error in data cleanup task: {e}")
                await asyncio.sleep(60)


# Factory function for creating service instance
def create_market_data_service(config: Dict[str, Any]) -> MarketDataService:
    """
    Create and configure market data service instance.
    
    Args:
        config: Service configuration
        
    Returns:
        Configured MarketDataService instance
    """
    return MarketDataService(config)