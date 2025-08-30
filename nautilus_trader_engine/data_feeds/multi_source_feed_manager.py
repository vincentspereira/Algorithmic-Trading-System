"""
Multi-Source Data Feeds with Fallback Mechanism

Implements redundant data sources with automatic failover for reliable market data:
- Primary: Interactive Brokers (IBKR)
- Secondary: Yahoo Finance
- Tertiary: Alpha Vantage
- Quaternary: Polygon.io
- Emergency: Static/Cached data

Author: Vincent S. Pereira
Version: 1.0.0
Phase: Phase 1 - Core System Validation & Hardening
"""

import asyncio
import logging
import time
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass, asdict
import sys
import os

# Add project paths
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Add IB API path
ibapi_path = r"C:\TWS API\source\pythonclient"
if os.path.exists(ibapi_path):
    sys.path.insert(0, ibapi_path)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import dependencies
try:
    from ib_insync import IB, Stock, Contract
    IBKR_AVAILABLE = True
except ImportError:
    IBKR_AVAILABLE = False
    logger.warning("IB API not available")

try:
    import yfinance as yf
    YAHOO_AVAILABLE = True
except ImportError:
    YAHOO_AVAILABLE = False
    logger.warning("Yahoo Finance not available")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("Requests not available")


class DataSource(Enum):
    """Data source enumeration"""
    IBKR = "interactive_brokers"
    YAHOO = "yahoo_finance"
    ALPHA_VANTAGE = "alpha_vantage"
    POLYGON = "polygon_io"
    CACHE = "cached_data"


class DataStatus(Enum):
    """Data status enumeration"""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    NO_DATA = "no_data"
    STALE = "stale"


@dataclass
class MarketDataPoint:
    """Standard market data structure"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    source: DataSource
    status: DataStatus
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = None
    error_message: str = ""

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def price(self) -> float:
        """Alias for close price for backward compatibility"""
        return self.close


@dataclass
class DataSourceConfig:
    """Data source configuration"""
    name: DataSource
    priority: int
    enabled: bool
    timeout_seconds: int
    rate_limit_per_minute: int
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class DataFeedManager:
    """Multi-source data feed manager with failover"""
    
    def __init__(self):
        self.sources = {}
        self.fallback_order = []
        self.cache = {}
        self.source_stats = {}
        self.active_connections = {}
        
        # Initialize source configurations
        self._initialize_sources()
        
    def _initialize_sources(self):
        """Initialize data source configurations"""
        self.sources = {
            DataSource.IBKR: DataSourceConfig(
                name=DataSource.IBKR,
                priority=1,
                enabled=IBKR_AVAILABLE,
                timeout_seconds=10,
                rate_limit_per_minute=1000,
                metadata={"real_time": True, "paper_trading": True}
            ),
            DataSource.YAHOO: DataSourceConfig(
                name=DataSource.YAHOO,
                priority=2,
                enabled=YAHOO_AVAILABLE,
                timeout_seconds=15,
                rate_limit_per_minute=200,
                metadata={"real_time": False, "delayed": True}
            ),
            DataSource.ALPHA_VANTAGE: DataSourceConfig(
                name=DataSource.ALPHA_VANTAGE,
                priority=3,
                enabled=REQUESTS_AVAILABLE,
                timeout_seconds=20,
                rate_limit_per_minute=500,
                api_key=os.getenv("ALPHA_VANTAGE_API_KEY"),
                base_url="https://www.alphavantage.co/query",
                metadata={"real_time": True, "premium": True}
            ),
            DataSource.POLYGON: DataSourceConfig(
                name=DataSource.POLYGON,
                priority=4,
                enabled=REQUESTS_AVAILABLE,
                timeout_seconds=20,
                rate_limit_per_minute=1000,
                api_key=os.getenv("POLYGON_API_KEY"),
                base_url="https://api.polygon.io",
                metadata={"real_time": True, "premium": True}
            ),
            DataSource.CACHE: DataSourceConfig(
                name=DataSource.CACHE,
                priority=5,
                enabled=True,
                timeout_seconds=1,
                rate_limit_per_minute=10000,
                metadata={"fallback": True, "offline": True}
            )
        }
        
        # Set fallback order based on priority
        self.fallback_order = sorted(
            [source for source in self.sources.values() if source.enabled],
            key=lambda x: x.priority
        )
        
        # Initialize statistics
        for source in self.sources.values():
            self.source_stats[source.name] = {
                "requests": 0,
                "successes": 0,
                "failures": 0,
                "avg_latency": 0.0,
                "last_success": None,
                "last_failure": None,
                "uptime_percentage": 100.0
            }
    
    async def get_market_data(
        self, 
        symbol: str, 
        timeframe: str = "1d", 
        period: str = "5d",
        force_source: Optional[DataSource] = None
    ) -> Optional[MarketDataPoint]:
        """Get market data with automatic fallback"""
        
        if force_source:
            sources_to_try = [self.sources[force_source]]
        else:
            sources_to_try = self.fallback_order
        
        for source_config in sources_to_try:
            try:
                logger.info(f"Attempting to fetch {symbol} from {source_config.name.value}")
                
                start_time = time.time()
                
                # Try to get data from this source
                data_point = await self._fetch_from_source(
                    source_config, symbol, timeframe, period
                )
                
                if data_point and data_point.status == DataStatus.SUCCESS:
                    latency = (time.time() - start_time) * 1000
                    data_point.latency_ms = latency
                    
                    # Update statistics
                    self._update_source_stats(source_config.name, True, latency)
                    
                    # Cache the data
                    self._cache_data(symbol, data_point)
                    
                    logger.info(f"✓ Successfully fetched {symbol} from {source_config.name.value} "
                              f"({latency:.2f}ms)")
                    
                    return data_point
                else:
                    # This source failed, try next
                    self._update_source_stats(source_config.name, False, 0)
                    logger.warning(f"✗ Failed to fetch {symbol} from {source_config.name.value}")
                    continue
                    
            except Exception as e:
                self._update_source_stats(source_config.name, False, 0)
                logger.error(f"✗ Error fetching {symbol} from {source_config.name.value}: {e}")
                continue
        
        # If all sources failed, try cache
        cached_data = self._get_cached_data(symbol)
        if cached_data:
            logger.warning(f"⚠ Using cached data for {symbol}")
            cached_data.status = DataStatus.STALE
            return cached_data
        
        logger.error(f"✗ All data sources failed for {symbol}")
        return None
    
    async def _fetch_from_source(
        self, 
        source_config: DataSourceConfig, 
        symbol: str, 
        timeframe: str, 
        period: str
    ) -> Optional[MarketDataPoint]:
        """Fetch data from specific source"""
        
        if source_config.name == DataSource.IBKR:
            return await self._fetch_from_ibkr(symbol, timeframe, period)
        elif source_config.name == DataSource.YAHOO:
            return await self._fetch_from_yahoo(symbol, timeframe, period)
        elif source_config.name == DataSource.ALPHA_VANTAGE:
            return await self._fetch_from_alpha_vantage(source_config, symbol)
        elif source_config.name == DataSource.POLYGON:
            return await self._fetch_from_polygon(source_config, symbol)
        elif source_config.name == DataSource.CACHE:
            return self._get_cached_data(symbol)
        
        return None
    
    async def _fetch_from_ibkr(self, symbol: str, timeframe: str, period: str) -> Optional[MarketDataPoint]:
        """Fetch data from Interactive Brokers"""
        if not IBKR_AVAILABLE:
            return None
        
        try:
            # Use existing connection or create new one
            if DataSource.IBKR not in self.active_connections:
                ib = IB()
                await ib.connectAsync('127.0.0.1', 7497, clientId=0)
                self.active_connections[DataSource.IBKR] = ib
            else:
                ib = self.active_connections[DataSource.IBKR]
            
            # Create contract based on symbol type
            if len(symbol) == 6 and symbol.upper() in ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCAD', 'AUDUSD', 'NZDUSD', 'USDCHF']:
                # Forex pair - create Forex contract
                from ib_insync import Forex
                base_currency = symbol[:3].upper()
                quote_currency = symbol[3:].upper()
                contract = Forex(base_currency + quote_currency)
            else:
                # Stock contract
                contract = Stock(symbol, 'SMART', 'USD')
            
            # Get real-time ticker data
            ticker = ib.reqMktData(contract, '', False, False)
            await asyncio.sleep(2)  # Wait for data
            
            if ticker.last and ticker.last > 0:
                # Create data point from real-time data
                current_time = datetime.now()
                
                data_point = MarketDataPoint(
                    symbol=symbol,
                    timestamp=current_time,
                    open=float(ticker.last),  # Use last as approximation
                    high=float(ticker.last * 1.01),  # Simulated high
                    low=float(ticker.last * 0.99),   # Simulated low
                    close=float(ticker.last),
                    volume=int(ticker.volume) if ticker.volume else 0,
                    source=DataSource.IBKR,
                    status=DataStatus.SUCCESS,
                    metadata={"bid": ticker.bid, "ask": ticker.ask}
                )
                
                # Cancel market data
                ib.cancelMktData(contract)
                
                return data_point
            else:
                # No data available, return error data point
                return MarketDataPoint(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    open=0.0, high=0.0, low=0.0, close=0.0, volume=0,
                    source=DataSource.IBKR,
                    status=DataStatus.NO_DATA,
                    error_message="No market data available"
                )
            
        except Exception as e:
            logger.error(f"IBKR fetch error: {e}")
            # Clean up connection on error
            if DataSource.IBKR in self.active_connections:
                try:
                    self.active_connections[DataSource.IBKR].disconnect()
                except:
                    pass
                del self.active_connections[DataSource.IBKR]
            
            # Return error data point
            return MarketDataPoint(
                symbol=symbol,
                timestamp=datetime.now(),
                open=0.0, high=0.0, low=0.0, close=0.0, volume=0,
                source=DataSource.IBKR,
                status=DataStatus.FAILED,
                error_message=str(e)
            )
    
    async def _fetch_from_yahoo(self, symbol: str, timeframe: str, period: str) -> Optional[MarketDataPoint]:
        """Fetch data from Yahoo Finance"""
        if not YAHOO_AVAILABLE:
            return None
        
        try:
            # Convert forex symbol format for Yahoo Finance
            yahoo_symbol = symbol
            if len(symbol) == 6 and symbol.upper() in ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCAD', 'AUDUSD', 'NZDUSD', 'USDCHF']:
                # Convert EURUSD to EUR=X format for Yahoo
                yahoo_symbol = symbol[:3].upper() + symbol[3:].upper() + "=X"
            
            ticker = yf.Ticker(yahoo_symbol)
            hist = ticker.history(period="1d", interval="1m")
            
            if not hist.empty:
                latest = hist.iloc[-1]
                
                data_point = MarketDataPoint(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    open=float(latest['Open']),
                    high=float(latest['High']),
                    low=float(latest['Low']),
                    close=float(latest['Close']),
                    volume=int(latest['Volume']),
                    source=DataSource.YAHOO,
                    status=DataStatus.SUCCESS,
                    metadata={"delayed": True}
                )
                
                return data_point
            else:
                # No data available
                return MarketDataPoint(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    open=0.0, high=0.0, low=0.0, close=0.0, volume=0,
                    source=DataSource.YAHOO,
                    status=DataStatus.NO_DATA,
                    error_message="No historical data available"
                )
                
        except Exception as e:
            logger.error(f"Yahoo Finance fetch error: {e}")
            return MarketDataPoint(
                symbol=symbol,
                timestamp=datetime.now(),
                open=0.0, high=0.0, low=0.0, close=0.0, volume=0,
                source=DataSource.YAHOO,
                status=DataStatus.FAILED,
                error_message=str(e)
            )
    
    async def _fetch_from_alpha_vantage(self, source_config: DataSourceConfig, symbol: str) -> Optional[MarketDataPoint]:
        """Fetch data from Alpha Vantage"""
        if not REQUESTS_AVAILABLE or not source_config.api_key:
            return None
        
        try:
            url = f"{source_config.base_url}?function=GLOBAL_QUOTE&symbol={symbol}&apikey={source_config.api_key}"
            
            response = requests.get(url, timeout=source_config.timeout_seconds)
            data = response.json()
            
            if "Global Quote" in data:
                quote = data["Global Quote"]
                
                data_point = MarketDataPoint(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    open=float(quote["02. open"]),
                    high=float(quote["03. high"]),
                    low=float(quote["04. low"]),
                    close=float(quote["05. price"]),
                    volume=int(quote["06. volume"]),
                    source=DataSource.ALPHA_VANTAGE,
                    status=DataStatus.SUCCESS,
                    metadata={"change": quote["09. change"], "change_percent": quote["10. change percent"]}
                )
                
                return data_point
                
        except Exception as e:
            logger.error(f"Alpha Vantage fetch error: {e}")
        
        return None
    
    async def _fetch_from_polygon(self, source_config: DataSourceConfig, symbol: str) -> Optional[MarketDataPoint]:
        """Fetch data from Polygon.io"""
        if not REQUESTS_AVAILABLE or not source_config.api_key:
            return None
        
        try:
            # Get previous day's data
            prev_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            url = f"{source_config.base_url}/v1/open-close/{symbol}/{prev_date}?adjusted=true&apikey={source_config.api_key}"
            
            response = requests.get(url, timeout=source_config.timeout_seconds)
            data = response.json()
            
            if data.get("status") == "OK":
                data_point = MarketDataPoint(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    open=float(data["open"]),
                    high=float(data["high"]),
                    low=float(data["low"]),
                    close=float(data["close"]),
                    volume=int(data["volume"]),
                    source=DataSource.POLYGON,
                    status=DataStatus.SUCCESS,
                    metadata={"after_hours": data.get("afterHours")}
                )
                
                return data_point
                
        except Exception as e:
            logger.error(f"Polygon fetch error: {e}")
        
        return None
    
    def _cache_data(self, symbol: str, data_point: MarketDataPoint):
        """Cache data for fallback"""
        self.cache[symbol] = {
            "data": data_point,
            "timestamp": datetime.now()
        }
        
        # Limit cache size
        if len(self.cache) > 1000:
            # Remove oldest entries
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]["timestamp"])
            del self.cache[oldest_key]
    
    def _get_cached_data(self, symbol: str) -> Optional[MarketDataPoint]:
        """Get cached data"""
        if symbol in self.cache:
            cached_entry = self.cache[symbol]
            
            # Check if cache is not too old (1 hour max)
            if datetime.now() - cached_entry["timestamp"] < timedelta(hours=1):
                cached_data = cached_entry["data"]
                cached_data.source = DataSource.CACHE
                return cached_data
        
        return None
    
    def _update_source_stats(self, source: DataSource, success: bool, latency: float):
        """Update source statistics"""
        stats = self.source_stats[source]
        stats["requests"] += 1
        
        if success:
            stats["successes"] += 1
            stats["last_success"] = datetime.now()
            
            # Update rolling average latency
            if stats["avg_latency"] == 0:
                stats["avg_latency"] = latency
            else:
                stats["avg_latency"] = (stats["avg_latency"] * 0.9) + (latency * 0.1)
        else:
            stats["failures"] += 1
            stats["last_failure"] = datetime.now()
        
        # Calculate uptime percentage
        if stats["requests"] > 0:
            stats["uptime_percentage"] = (stats["successes"] / stats["requests"]) * 100
    
    def get_source_health(self) -> Dict[str, Any]:
        """Get health status of all data sources"""
        health_report = {}
        
        for source, stats in self.source_stats.items():
            health_report[source.value] = {
                "enabled": self.sources[source].enabled,
                "priority": self.sources[source].priority,
                "uptime_percentage": round(stats["uptime_percentage"], 2),
                "avg_latency_ms": round(stats["avg_latency"], 2),
                "total_requests": stats["requests"],
                "successes": stats["successes"],
                "failures": stats["failures"],
                "last_success": stats["last_success"].isoformat() if stats["last_success"] else None,
                "last_failure": stats["last_failure"].isoformat() if stats["last_failure"] else None,
                "status": "healthy" if stats["uptime_percentage"] >= 90 else "degraded" if stats["uptime_percentage"] >= 50 else "unhealthy"
            }
        
        return health_report
    
    @property
    def health_monitor(self) -> Dict[str, Any]:
        """Backward compatibility property for health monitoring"""
        health_data = {}
        for source, stats in self.source_stats.items():
            health_data[source.value] = {
                "status": "healthy" if stats["uptime_percentage"] >= 90 else "degraded" if stats["uptime_percentage"] >= 50 else "unhealthy",
                "success_rate": stats["uptime_percentage"] / 100.0,
                "total_requests": stats["requests"]
            }
        return health_data
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get source statistics"""
        return {
            source.value: {
                "requests": stats["requests"],
                "successes": stats["successes"],
                "failures": stats["failures"],
                "avg_latency": stats["avg_latency"]
            }
            for source, stats in self.source_stats.items()
        }
    
    async def test_all_sources(self, test_symbol: str = "AAPL") -> Dict[str, Any]:
        """Test all data sources"""
        logger.info(f"🧪 Testing all data sources with symbol: {test_symbol}")
        
        test_results = {}
        
        for source_config in self.fallback_order:
            logger.info(f"Testing {source_config.name.value}...")
            
            try:
                start_time = time.time()
                data_point = await self._fetch_from_source(source_config, test_symbol, "1d", "1d")
                test_time = (time.time() - start_time) * 1000
                
                if data_point and data_point.status == DataStatus.SUCCESS:
                    test_results[source_config.name.value] = {
                        "status": "PASSED",
                        "latency_ms": round(test_time, 2),
                        "data_received": True,
                        "sample_price": data_point.close
                    }
                    logger.info(f"  ✓ {source_config.name.value}: PASSED ({test_time:.2f}ms)")
                else:
                    test_results[source_config.name.value] = {
                        "status": "FAILED",
                        "latency_ms": round(test_time, 2),
                        "data_received": False,
                        "error": "No data returned"
                    }
                    logger.warning(f"  ✗ {source_config.name.value}: FAILED")
                    
            except Exception as e:
                test_results[source_config.name.value] = {
                    "status": "ERROR",
                    "latency_ms": 0,
                    "data_received": False,
                    "error": str(e)
                }
                logger.error(f"  ✗ {source_config.name.value}: ERROR - {e}")
        
        return test_results
    
    async def cleanup(self):
        """Clean up active connections"""
        for source, connection in self.active_connections.items():
            try:
                if source == DataSource.IBKR and hasattr(connection, 'disconnect'):
                    connection.disconnect()
            except Exception as e:
                logger.error(f"Error cleaning up {source}: {e}")
        
        self.active_connections.clear()


# Test and demonstration functions
async def main():
    """Main function to test the multi-source data feed system"""
    logger.info("🚀 Multi-Source Data Feed Manager Test")
    logger.info("=" * 50)
    
    # Initialize data feed manager
    feed_manager = DataFeedManager()
    
    # Test all sources
    test_results = await feed_manager.test_all_sources("AAPL")
    
    # Test fallback mechanism
    logger.info("\n🔄 Testing Fallback Mechanism")
    logger.info("-" * 30)
    
    test_symbols = ["AAPL", "MSFT", "GOOGL"]
    
    for symbol in test_symbols:
        logger.info(f"\nTesting fallback for {symbol}:")
        data_point = await feed_manager.get_market_data(symbol)
        
        if data_point:
            logger.info(f"  ✓ Got data from {data_point.source.value}")
            logger.info(f"  Price: ${data_point.close:.2f}")
            logger.info(f"  Latency: {data_point.latency_ms:.2f}ms")
        else:
            logger.error(f"  ✗ Failed to get data for {symbol}")
    
    # Show source health
    logger.info("\n💊 Data Source Health Report")
    logger.info("-" * 30)
    
    health_report = feed_manager.get_source_health()
    for source, health in health_report.items():
        status_emoji = "🟢" if health["status"] == "healthy" else "🟡" if health["status"] == "degraded" else "🔴"
        logger.info(f"{status_emoji} {source}: {health['uptime_percentage']}% uptime, "
                   f"{health['avg_latency_ms']}ms avg latency")
    
    # Clean up
    await feed_manager.cleanup()
    
    # Save test results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"data_feeds_test_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump({
            "test_results": test_results,
            "health_report": health_report,
            "timestamp": datetime.now().isoformat()
        }, f, indent=2, default=str)
    
    logger.info(f"\n💾 Results saved to: {results_file}")


if __name__ == "__main__":
    asyncio.run(main())