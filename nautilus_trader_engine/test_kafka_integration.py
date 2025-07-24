"""
Kafka Integration Test Script

This script demonstrates and tests the Kafka integration functionality
for the algorithmic trading system.

Author: Kilo Code
Version: 1.0.0
"""

import asyncio
import json
import time
from typing import Dict, Any
import logging

from kafka_integration import (
    MarketDataStreamer, 
    KafkaConfig, 
    MarketDataTopic, 
    AssetClass
)
from data_feeds import DataFeedManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_kafka_producer():
    """Test Kafka producer functionality"""
    print("\n=== Testing Kafka Producer ===")
    
    try:
        # Create streamer
        config = KafkaConfig(bootstrap_servers="kafka:9092")
        streamer = MarketDataStreamer(config)
        
        # Initialize
        if not await streamer.initialize():
            print("❌ Failed to initialize streamer")
            return False
        
        print("✅ Streamer initialized successfully")
        
        # Test data publishing
        symbols = ["AAPL", "GOOGL", "MSFT"]
        
        for symbol in symbols:
            # Start streaming
            success = await streamer.start_streaming_symbol(
                symbol, AssetClass.STOCK, "1d"
            )
            
            if success:
                print(f"✅ Started streaming for {symbol}")
                
                # Publish data
                published = await streamer.publish_market_data_for_symbol(symbol)
                if published:
                    print(f"✅ Published data for {symbol}")
                else:
                    print(f"❌ Failed to publish data for {symbol}")
            else:
                print(f"❌ Failed to start streaming for {symbol}")
        
        # Test trading signal
        test_signal = {
            "type": "buy",
            "symbol": "AAPL",
            "price": 150.00,
            "quantity": 100,
            "timestamp": time.time(),
            "strategy": "test_strategy"
        }
        
        signal_published = await streamer.producer.publish_trading_signal(test_signal)
        if signal_published:
            print("✅ Published trading signal")
        else:
            print("❌ Failed to publish trading signal")
        
        # Get status
        status = await streamer.get_streaming_status()
        print(f"📊 Streaming Status: {json.dumps(status, indent=2)}")
        
        # Close
        await streamer.close()
        print("✅ Producer test completed")
        return True
        
    except Exception as e:
        print(f"❌ Producer test failed: {e}")
        return False


async def test_kafka_consumer():
    """Test Kafka consumer functionality"""
    print("\n=== Testing Kafka Consumer ===")
    
    try:
        # Create streamer
        config = KafkaConfig(bootstrap_servers="kafka:9092")
        streamer = MarketDataStreamer(config)
        
        # Initialize
        if not await streamer.initialize():
            print("❌ Failed to initialize streamer")
            return False
        
        print("✅ Consumer initialized successfully")
        
        # Register custom handlers
        message_count = 0
        
        async def test_handler(message_data: Dict[str, Any]):
            nonlocal message_count
            message_count += 1
            print(f"📨 Received message {message_count}: {message_data.get('symbol', 'unknown')}")
        
        # Register handlers for different topics
        streamer.consumer.register_handler(MarketDataTopic.STOCK_PRICES, test_handler)
        streamer.consumer.register_handler(MarketDataTopic.TRADING_SIGNALS, test_handler)
        
        # Start consumer for a short time
        print("🔄 Starting consumer for 10 seconds...")
        
        # Start consumer in background
        consumer_task = asyncio.create_task(streamer.start_consumer())
        
        # Wait for messages
        await asyncio.sleep(10)
        
        # Stop consumer
        await streamer.stop_consumer()
        consumer_task.cancel()
        
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass
        
        print(f"📊 Received {message_count} messages")
        
        # Close
        await streamer.close()
        print("✅ Consumer test completed")
        return True
        
    except Exception as e:
        print(f"❌ Consumer test failed: {e}")
        return False


async def test_data_feed_integration():
    """Test integration between data feeds and Kafka"""
    print("\n=== Testing Data Feed Integration ===")
    
    try:
        # Create data feed manager
        data_manager = DataFeedManager()
        
        # Create Kafka streamer
        config = KafkaConfig(bootstrap_servers="kafka:9092")
        streamer = MarketDataStreamer(config)
        
        if not await streamer.initialize():
            print("❌ Failed to initialize streamer")
            return False
        
        # Test symbols
        test_symbols = [
            ("AAPL", AssetClass.STOCK),
            ("EURUSD=X", AssetClass.FOREX),
            ("BTC-USD", AssetClass.CRYPTO)
        ]
        
        for symbol, asset_class in test_symbols:
            print(f"🔄 Testing {symbol} ({asset_class.value})")
            
            # Fetch data using data feed manager
            response = data_manager.get_data(
                ticker=symbol,
                asset_class=asset_class,
                period="5d"
            )
            
            if response.success:
                print(f"✅ Fetched data for {symbol}: {len(response.data)} rows")
                
                # Determine topic based on asset class
                topic_map = {
                    AssetClass.STOCK: MarketDataTopic.STOCK_PRICES,
                    AssetClass.FOREX: MarketDataTopic.FOREX_RATES,
                    AssetClass.CRYPTO: MarketDataTopic.CRYPTO_PRICES
                }
                
                topic = topic_map.get(asset_class, MarketDataTopic.STOCK_PRICES)
                
                # Publish to Kafka
                published = await streamer.producer.publish_market_data(topic, response)
                
                if published:
                    print(f"✅ Published {symbol} data to Kafka topic: {topic.value}")
                else:
                    print(f"❌ Failed to publish {symbol} data to Kafka")
            else:
                print(f"❌ Failed to fetch data for {symbol}: {response.error_message}")
        
        # Close
        await streamer.close()
        print("✅ Data feed integration test completed")
        return True
        
    except Exception as e:
        print(f"❌ Data feed integration test failed: {e}")
        return False


async def test_kafka_topics():
    """Test Kafka topic management"""
    print("\n=== Testing Kafka Topics ===")
    
    try:
        config = KafkaConfig(bootstrap_servers="kafka:9092")
        streamer = MarketDataStreamer(config)
        
        if not await streamer.initialize():
            print("❌ Failed to initialize streamer")
            return False
        
        # List available topics
        if streamer.producer.producer:
            metadata = streamer.producer.producer.list_topics(timeout=5)
            
            print("📋 Available Kafka Topics:")
            for topic_name in metadata.topics:
                topic_metadata = metadata.topics[topic_name]
                print(f"  - {topic_name} (partitions: {len(topic_metadata.partitions)})")
        
        # Test all market data topics
        print("\n🔄 Testing market data topics:")
        market_topics = [
            MarketDataTopic.STOCK_PRICES,
            MarketDataTopic.FOREX_RATES,
            MarketDataTopic.CRYPTO_PRICES,
            MarketDataTopic.TRADING_SIGNALS
        ]
        
        for topic in market_topics:
            print(f"  - {topic.value}")
        
        await streamer.close()
        print("✅ Topic test completed")
        return True
        
    except Exception as e:
        print(f"❌ Topic test failed: {e}")
        return False


async def run_all_tests():
    """Run all Kafka integration tests"""
    print("🚀 Starting Kafka Integration Tests")
    print("=" * 50)
    
    tests = [
        ("Kafka Producer", test_kafka_producer),
        ("Data Feed Integration", test_data_feed_integration),
        ("Kafka Topics", test_kafka_topics),
        ("Kafka Consumer", test_kafka_consumer)  # Run consumer last
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} test...")
        try:
            result = await test_func()
            results[test_name] = result
            if result:
                print(f"✅ {test_name} test PASSED")
            else:
                print(f"❌ {test_name} test FAILED")
        except Exception as e:
            print(f"❌ {test_name} test ERROR: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Kafka integration is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the logs above for details.")
    
    return passed == total


if __name__ == "__main__":
    # Run tests
    asyncio.run(run_all_tests())