"""Market Data Service with Multi-Source Feeds and Fallback Mechanisms

Provides robust market data collection and distribution with:
- Multi-source data feeds with automatic failover
- Asset-class specific provider chains
- Real-time and historical data support
- Kafka streaming for normalized data distribution
- Circuit breaker pattern for provider reliability
- Performance monitoring and health checks

Supported Providers:
- Yahoo Finance (Primary - Free)
- Interactive Brokers
- Alpha Vantage
- Finnhub
- Polygon.io
- Twelve Data
- CME Group
- Oanda
- And more...

Supported Asset Classes:
- Stocks & ETFs
- Futures & Options
- Forex
- Commodities
- Cryptocurrencies

Architecture:
- Event-driven data streaming via Kafka
- Microservice-ready with Docker support
- Horizontal scaling capabilities
- Real-time health monitoring
"""

__version__ = "1.0.0"
__author__ = "Algorithmic Trading System"

# Core components
from .data_feed_manager import (
    DataFeedManager,
    data_feed_manager,
    get_data_feed_manager,
    MarketDataPoint,
    ProviderConfig,
    DataProviderInterface
)

# Enums
from .data_feed_manager import (
    AssetClass,
    DataProvider,
    DataType
)

# Models
from .models import (
    MarketData,
    Quote,
    Trade,
    Bar
)

# Configuration
from .config import MarketDataConfig
from .provider_configs import get_provider_configs

# API
from .api import MarketDataAPI

# Data fetcher
from .data_fetcher import DataFetcher

# Provider implementations
from .data_feed_manager import (
    YahooFinanceProvider,
    AlphaVantageProvider
)

# Lazy imports for optional providers
def get_finnhub_provider():
    """Get Finnhub provider if available"""
    try:
        from .providers.finnhub_provider import FinnhubProvider
        return FinnhubProvider
    except ImportError:
        return None

def get_polygon_provider():
    """Get Polygon provider if available"""
    try:
        from .providers.polygon_provider import PolygonProvider
        return PolygonProvider
    except ImportError:
        return None

def get_twelve_data_provider():
    """Get Twelve Data provider if available"""
    try:
        from .providers.twelve_data_provider import TwelveDataProvider
        return TwelveDataProvider
    except ImportError:
        return None

# Export all components
__all__ = [
    # Core classes
    "DataFeedManager",
    "MarketDataPoint",
    "ProviderConfig",
    "DataProviderInterface",
    
    # Enums
    "AssetClass",
    "DataProvider", 
    "DataType",
    
    # Models
    "MarketData",
    "Quote",
    "Trade",
    "Bar",
    
    # Configuration
    "MarketDataConfig",
    "get_provider_configs",
    
    # API
    "MarketDataAPI",
    
    # Data fetcher
    "DataFetcher",
    
    # Provider implementations
    "YahooFinanceProvider",
    "AlphaVantageProvider",
    
    # Factory functions
    "get_finnhub_provider",
    "get_polygon_provider", 
    "get_twelve_data_provider",
    
    # Global instances
    "data_feed_manager",
    "get_data_feed_manager"
]

# Default configuration
DEFAULT_CONFIG = {
    "primary_provider": "yahoo_finance",
    "fallback_enabled": True,
    "circuit_breaker_threshold": 5,
    "circuit_breaker_timeout_minutes": 5,
    "kafka_streaming_enabled": True,
    "health_check_interval_seconds": 30,
    "rate_limit_buffer_percent": 10
}

# Factory functions
def create_data_feed_manager(config: dict = None) -> DataFeedManager:
    """Create a configured data feed manager instance
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        Configured DataFeedManager instance
    """
    if config:
        # Apply custom configuration
        pass
    return DataFeedManager()

def create_market_data_api(data_feed_manager: DataFeedManager = None) -> 'MarketDataAPI':
    """Create a market data API instance
    
    Args:
        data_feed_manager: Optional DataFeedManager instance
        
    Returns:
        MarketDataAPI instance
    """
    if data_feed_manager is None:
        data_feed_manager = create_data_feed_manager()
    return MarketDataAPI(data_feed_manager)

async def start_market_data_service(config: dict = None) -> DataFeedManager:
    """Start the market data service with all components
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        Started DataFeedManager instance
    """
    manager = create_data_feed_manager(config)
    await manager.start()
    return manager

# Logging setup
import logging
logging.getLogger(__name__).addHandler(logging.NullHandler())

# Version info
print(f"Market Data Service v{__version__} initialized")
print(f"Supported providers: {len([p for p in DataProvider])} configured")
print(f"Supported asset classes: {len([ac for ac in AssetClass])} types")