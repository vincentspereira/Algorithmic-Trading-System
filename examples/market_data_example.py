"""Market Data Service Example

Demonstrates the usage of the market data service with multi-source feeds,
fallback mechanisms, and real-time streaming capabilities.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Market data service imports
from market_data_service import (
    DataFeedManager,
    MarketDataAPI,
    create_data_feed_manager,
    start_market_data_service,
    AssetClass,
    DataProvider,
    DataType,
    MarketDataPoint
)

# Configuration
from market_data_service.config import MarketDataConfig
from shared.utils.logging_utils import get_logger

logger = get_logger(__name__)


class MarketDataExample:
    """Example demonstrating market data service capabilities"""
    
    def __init__(self):
        self.data_feed_manager: DataFeedManager = None
        self.api: MarketDataAPI = None
        self.config = MarketDataConfig.from_env()
    
    async def initialize(self):
        """Initialize the market data service"""
        logger.info("Initializing market data service...")
        
        # Create and start data feed manager
        self.data_feed_manager = await start_market_data_service({
            "primary_provider": "yahoo_finance",
            "fallback_enabled": True,
            "kafka_streaming_enabled": True
        })
        
        # Create API instance
        self.api = MarketDataAPI(self.data_feed_manager)
        
        logger.info("Market data service initialized successfully")
    
    async def demonstrate_real_time_data(self):
        """Demonstrate real-time data fetching with fallback"""
        logger.info("=== Real-Time Data Demonstration ===")
        
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA"]
        
        for symbol in symbols:
            try:
                # Get real-time quote
                data_point = await self.data_feed_manager.get_real_time_data(
                    symbol=symbol,
                    asset_class=AssetClass.STOCKS,
                    data_type=DataType.QUOTE
                )
                
                if data_point:
                    logger.info(f"Real-time data for {symbol}:")
                    logger.info(f"  Provider: {data_point.provider}")
                    logger.info(f"  Price: ${data_point.data.get('current_price', 'N/A')}")
                    logger.info(f"  Change: {data_point.data.get('change', 'N/A')}")
                    logger.info(f"  Timestamp: {data_point.timestamp}")
                else:
                    logger.warning(f"No real-time data available for {symbol}")
                    
            except Exception as e:
                logger.error(f"Error fetching data for {symbol}: {e}")
            
            # Small delay between requests
            await asyncio.sleep(0.5)
    
    async def demonstrate_historical_data(self):
        """Demonstrate historical data fetching"""
        logger.info("=== Historical Data Demonstration ===")
        
        symbol = "AAPL"
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        try:
            # Get historical data
            historical_data = await self.data_feed_manager.get_historical_data(
                symbol=symbol,
                asset_class=AssetClass.STOCKS,
                start_date=start_date,
                end_date=end_date,
                interval="1D"
            )
            
            if historical_data:
                logger.info(f"Historical data for {symbol} (last 30 days):")
                logger.info(f"  Total data points: {len(historical_data)}")
                logger.info(f"  Provider: {historical_data[0].provider}")
                
                # Show first and last data points
                first_point = historical_data[0]
                last_point = historical_data[-1]
                
                logger.info(f"  First point ({first_point.timestamp.date()}):")
                logger.info(f"    Open: ${first_point.data.get('open', 'N/A')}")
                logger.info(f"    Close: ${first_point.data.get('close', 'N/A')}")
                
                logger.info(f"  Last point ({last_point.timestamp.date()}):")
                logger.info(f"    Open: ${last_point.data.get('open', 'N/A')}")
                logger.info(f"    Close: ${last_point.data.get('close', 'N/A')}")
            else:
                logger.warning(f"No historical data available for {symbol}")
                
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
    
    async def demonstrate_multi_asset_classes(self):
        """Demonstrate data fetching across different asset classes"""
        logger.info("=== Multi-Asset Class Demonstration ===")
        
        test_symbols = {
            AssetClass.STOCKS: ["AAPL", "GOOGL"],
            AssetClass.ETF: ["SPY", "QQQ"],
            AssetClass.FOREX: ["EURUSD", "GBPUSD"],
            AssetClass.CRYPTO: ["BTC", "ETH"]
        }
        
        for asset_class, symbols in test_symbols.items():
            logger.info(f"Testing {asset_class.value} data:")
            
            for symbol in symbols:
                try:
                    data_point = await self.data_feed_manager.get_real_time_data(
                        symbol=symbol,
                        asset_class=asset_class,
                        data_type=DataType.QUOTE
                    )
                    
                    if data_point:
                        logger.info(f"  {symbol}: Provider={data_point.provider}, "
                                   f"Price=${data_point.data.get('current_price', 'N/A')}")
                    else:
                        logger.warning(f"  {symbol}: No data available")
                        
                except Exception as e:
                    logger.error(f"  {symbol}: Error - {e}")
                
                await asyncio.sleep(0.3)
    
    async def demonstrate_fallback_mechanism(self):
        """Demonstrate provider fallback mechanism"""
        logger.info("=== Fallback Mechanism Demonstration ===")
        
        # Get provider health status
        health_status = await self.data_feed_manager.get_provider_health_status()
        
        logger.info("Provider Health Status:")
        for provider, status in health_status.items():
            logger.info(f"  {provider}: {status['status']} "
                       f"(Last check: {status.get('last_check', 'N/A')})")
        
        # Test fallback chain for stocks
        symbol = "AAPL"
        logger.info(f"\nTesting fallback chain for {symbol}:")
        
        # Get fallback chain for stocks
        fallback_chain = self.data_feed_manager.get_fallback_chain(AssetClass.STOCKS)
        logger.info(f"Fallback chain: {' -> '.join(fallback_chain)}")
        
        # Attempt to get data (will use fallback if primary fails)
        data_point = await self.data_feed_manager.get_real_time_data(
            symbol=symbol,
            asset_class=AssetClass.STOCKS,
            data_type=DataType.QUOTE
        )
        
        if data_point:
            logger.info(f"Successfully retrieved data using provider: {data_point.provider}")
        else:
            logger.warning("All providers in fallback chain failed")
    
    async def demonstrate_streaming_data(self):
        """Demonstrate real-time data streaming"""
        logger.info("=== Real-Time Streaming Demonstration ===")
        
        symbols = ["AAPL", "GOOGL", "MSFT"]
        
        # Start streaming for multiple symbols
        logger.info(f"Starting real-time streaming for: {', '.join(symbols)}")
        
        async def data_handler(data_point: MarketDataPoint):
            """Handle incoming streaming data"""
            logger.info(f"Stream update - {data_point.symbol}: "
                       f"${data_point.data.get('current_price', 'N/A')} "
                       f"({data_point.provider})")
        
        # Subscribe to streaming data
        for symbol in symbols:
            await self.data_feed_manager.subscribe_real_time(
                symbol=symbol,
                asset_class=AssetClass.STOCKS,
                callback=data_handler
            )
        
        # Let it stream for 30 seconds
        logger.info("Streaming data for 30 seconds...")
        await asyncio.sleep(30)
        
        # Unsubscribe
        for symbol in symbols:
            await self.data_feed_manager.unsubscribe_real_time(symbol)
        
        logger.info("Streaming demonstration completed")
    
    async def demonstrate_performance_monitoring(self):
        """Demonstrate performance monitoring capabilities"""
        logger.info("=== Performance Monitoring Demonstration ===")
        
        # Get performance metrics
        metrics = await self.data_feed_manager.get_performance_metrics()
        
        logger.info("Performance Metrics:")
        logger.info(f"  Total requests: {metrics.get('total_requests', 0)}")
        logger.info(f"  Successful requests: {metrics.get('successful_requests', 0)}")
        logger.info(f"  Failed requests: {metrics.get('failed_requests', 0)}")
        logger.info(f"  Average response time: {metrics.get('avg_response_time', 0):.2f}ms")
        logger.info(f"  Cache hit rate: {metrics.get('cache_hit_rate', 0):.1%}")
        
        # Get provider-specific metrics
        provider_metrics = await self.data_feed_manager.get_provider_metrics()
        
        logger.info("\nProvider-Specific Metrics:")
        for provider, provider_data in provider_metrics.items():
            logger.info(f"  {provider}:")
            logger.info(f"    Requests: {provider_data.get('requests', 0)}")
            logger.info(f"    Success rate: {provider_data.get('success_rate', 0):.1%}")
            logger.info(f"    Avg latency: {provider_data.get('avg_latency', 0):.2f}ms")
    
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up resources...")
        
        if self.data_feed_manager:
            await self.data_feed_manager.stop()
        
        logger.info("Cleanup completed")


async def run_comprehensive_example():
    """Run comprehensive market data service example"""
    example = MarketDataExample()
    
    try:
        # Initialize
        await example.initialize()
        
        # Run demonstrations
        await example.demonstrate_real_time_data()
        await asyncio.sleep(2)
        
        await example.demonstrate_historical_data()
        await asyncio.sleep(2)
        
        await example.demonstrate_multi_asset_classes()
        await asyncio.sleep(2)
        
        await example.demonstrate_fallback_mechanism()
        await asyncio.sleep(2)
        
        await example.demonstrate_performance_monitoring()
        await asyncio.sleep(2)
        
        # Optional: Uncomment to test streaming (takes 30+ seconds)
        # await example.demonstrate_streaming_data()
        
    except Exception as e:
        logger.error(f"Example execution failed: {e}")
    finally:
        await example.cleanup()


async def run_basic_example():
    """Run basic market data service example"""
    logger.info("=== Basic Market Data Service Example ===")
    
    # Create data feed manager
    data_feed_manager = create_data_feed_manager()
    
    try:
        # Start the service
        await data_feed_manager.start()
        
        # Get real-time data for a single symbol
        symbol = "AAPL"
        data_point = await data_feed_manager.get_real_time_data(
            symbol=symbol,
            asset_class=AssetClass.STOCKS,
            data_type=DataType.QUOTE
        )
        
        if data_point:
            logger.info(f"Real-time data for {symbol}:")
            logger.info(f"  Provider: {data_point.provider}")
            logger.info(f"  Price: ${data_point.data.get('current_price', 'N/A')}")
            logger.info(f"  Timestamp: {data_point.timestamp}")
        else:
            logger.warning(f"No data available for {symbol}")
        
        # Get historical data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        historical_data = await data_feed_manager.get_historical_data(
            symbol=symbol,
            asset_class=AssetClass.STOCKS,
            start_date=start_date,
            end_date=end_date,
            interval="1D"
        )
        
        if historical_data:
            logger.info(f"\nHistorical data for {symbol} (last 7 days):")
            logger.info(f"  Data points: {len(historical_data)}")
            logger.info(f"  Provider: {historical_data[0].provider}")
        
    except Exception as e:
        logger.error(f"Basic example failed: {e}")
    finally:
        await data_feed_manager.stop()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("Market Data Service Examples")
    print("1. Basic Example (Quick test)")
    print("2. Comprehensive Example (Full demonstration)")
    
    choice = input("\nSelect example (1 or 2): ").strip()
    
    if choice == "1":
        asyncio.run(run_basic_example())
    elif choice == "2":
        asyncio.run(run_comprehensive_example())
    else:
        print("Invalid choice. Running basic example...")
        asyncio.run(run_basic_example())