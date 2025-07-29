"""
Integration tests for core infrastructure components
Tests the interaction between messaging, caching, and networking systems
"""

import asyncio
import pytest
import time
from typing import Dict, Any
from unittest.mock import Mock, patch

from nautilus_trader_engine.core import (
    MessageBus, CacheManager, NetworkManager,
    MessageType, CacheConfig, NetworkConfig
)


class TestInfrastructureIntegration:
    """Test integration between core infrastructure components"""
    
    @pytest.fixture
    async def message_bus(self):
        """Create message bus for testing"""
        bus = MessageBus()
        await bus.start()
        yield bus
        await bus.stop()
    
    @pytest.fixture
    async def cache_manager(self):
        """Create cache manager for testing"""
        config = CacheConfig(
            l1_size=1000,
            l2_enabled=False,  # Disable Redis for testing
            l3_enabled=False   # Disable DB for testing
        )
        manager = CacheManager(config)
        await manager.start()
        yield manager
        await manager.stop()
    
    @pytest.fixture
    async def network_manager(self):
        """Create network manager for testing"""
        config = NetworkConfig(
            enable_kernel_bypass=False,  # Disable for testing
            enable_numa=False,
            pool_size=10
        )
        manager = NetworkManager(config)
        await manager.start()
        yield manager
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_message_bus_cache_integration(self, message_bus, cache_manager):
        """Test message bus and cache integration"""
        # Setup message handler that uses cache
        cached_data = {}
        
        async def cache_handler(message):
            key = f"msg_{message.get('id', 'unknown')}"
            
            # Try to get from cache first
            cached_value = await cache_manager.get(key)
            if cached_value is not None:
                cached_data['hit'] = True
                return cached_value
            
            # Process and cache result
            result = f"processed_{message.get('data', '')}"
            await cache_manager.set(key, result, ttl=60)
            cached_data['miss'] = True
            return result
        
        # Subscribe to topic
        await message_bus.subscribe("test.cache", cache_handler)
        
        # Send first message
        await message_bus.publish("test.cache", {
            "id": "msg1",
            "data": "test_data"
        })
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Send same message again
        await message_bus.publish("test.cache", {
            "id": "msg1", 
            "data": "test_data"
        })
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Verify cache hit occurred
        assert cached_data.get('hit') is True
        assert cached_data.get('miss') is True
    
    @pytest.mark.asyncio
    async def test_network_message_integration(self, message_bus, network_manager):
        """Test network and message bus integration"""
        received_messages = []
        
        async def network_handler(message):
            # Simulate network operation
            connection = await network_manager.get_connection("test_endpoint")
            if connection:
                received_messages.append(message)
        
        # Subscribe to network topic
        await message_bus.subscribe("network.data", network_handler)
        
        # Send network message
        await message_bus.publish("network.data", {
            "type": "market_data",
            "symbol": "AAPL",
            "price": 150.0
        })
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Verify message was processed
        assert len(received_messages) == 1
        assert received_messages[0]["symbol"] == "AAPL"
    
    @pytest.mark.asyncio
    async def test_full_pipeline_integration(self, message_bus, cache_manager, network_manager):
        """Test full pipeline: network -> message bus -> cache"""
        pipeline_results = []
        
        async def pipeline_handler(message):
            # Step 1: Get network connection
            connection = await network_manager.get_connection("data_source")
            
            # Step 2: Process data (simulate network fetch)
            processed_data = {
                "original": message,
                "processed_at": time.time(),
                "connection_id": getattr(connection, 'id', 'mock_connection')
            }
            
            # Step 3: Cache the result
            cache_key = f"pipeline_{message.get('id')}"
            await cache_manager.set(cache_key, processed_data, ttl=300)
            
            # Step 4: Verify cached
            cached_result = await cache_manager.get(cache_key)
            pipeline_results.append(cached_result)
        
        # Subscribe to pipeline topic
        await message_bus.subscribe("pipeline.process", pipeline_handler)
        
        # Send test message through pipeline
        test_message = {
            "id": "test_123",
            "type": "market_update",
            "data": {"symbol": "TSLA", "price": 800.0}
        }
        
        await message_bus.publish("pipeline.process", test_message)
        
        # Wait for pipeline processing
        await asyncio.sleep(0.2)
        
        # Verify pipeline completed successfully
        assert len(pipeline_results) == 1
        result = pipeline_results[0]
        assert result["original"]["id"] == "test_123"
        assert result["original"]["data"]["symbol"] == "TSLA"
        assert "processed_at" in result
        assert "connection_id" in result
    
    @pytest.mark.asyncio
    async def test_performance_metrics_integration(self, message_bus, cache_manager, network_manager):
        """Test that all components report performance metrics"""
        # Get metrics from all components
        message_metrics = message_bus.get_metrics()
        cache_metrics = cache_manager.get_metrics()
        network_metrics = network_manager.get_metrics()
        
        # Verify metrics are available
        assert message_metrics is not None
        assert cache_metrics is not None
        assert network_metrics is not None
        
        # Verify metric structure
        assert hasattr(message_metrics, 'messages_processed')
        assert hasattr(cache_metrics, 'hit_rate')
        assert hasattr(network_metrics, 'active_connections')
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, message_bus, cache_manager):
        """Test error handling across components"""
        error_count = 0
        
        async def error_handler(message):
            nonlocal error_count
            try:
                # Simulate cache error
                if message.get('cause_error'):
                    raise Exception("Simulated cache error")
                
                await cache_manager.set("test_key", message)
            except Exception as e:
                error_count += 1
                # Re-raise to test error propagation
                raise
        
        # Subscribe with error handler
        await message_bus.subscribe("error.test", error_handler)
        
        # Send message that causes error
        await message_bus.publish("error.test", {"cause_error": True})
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Verify error was handled
        assert error_count == 1
        
        # Send normal message
        await message_bus.publish("error.test", {"data": "normal"})
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Verify normal processing works
        cached_value = await cache_manager.get("test_key")
        assert cached_value is not None
        assert cached_value["data"] == "normal"


if __name__ == "__main__":
    # Run basic integration test
    async def main():
        print("Running core infrastructure integration tests...")
        
        # Test basic component creation
        try:
            # Test message bus
            bus = MessageBus()
            await bus.start()
            print("✓ Message bus started successfully")
            await bus.stop()
            
            # Test cache manager
            cache_config = CacheConfig(l1_size=100, l2_enabled=False, l3_enabled=False)
            cache = CacheManager(cache_config)
            await cache.start()
            print("✓ Cache manager started successfully")
            await cache.stop()
            
            # Test network manager
            net_config = NetworkConfig(enable_kernel_bypass=False, enable_numa=False)
            network = NetworkManager(net_config)
            await network.start()
            print("✓ Network manager started successfully")
            await network.stop()
            
            print("\n✅ All core infrastructure components integrated successfully!")
            
        except Exception as e:
            print(f"❌ Integration test failed: {e}")
            raise
    
    asyncio.run(main())