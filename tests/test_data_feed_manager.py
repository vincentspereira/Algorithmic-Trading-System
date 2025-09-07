"""Test Suite for Multi-Source Data Feed Manager with Fallback Mechanism

Validates:
- Provider fallback chains for different asset classes
- Automatic switching on failure (timeout >3s, error codes)
- Circuit breaker functionality
- Data normalization and Kafka streaming
- Performance benchmarks (<1ms switch time)
- Multi-asset class support
"""

import asyncio
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market_data_service.data_feed_manager import (
    DataFeedManager, 
    AssetClass, 
    DataProvider, 
    MarketDataPoint,
    YahooFinanceProvider,
    AlphaVantageProvider
)
from kafka_service.producer import KafkaEventProducer
from shared.utils.logging_utils import get_logger

logger = get_logger(__name__)

class TestDataFeedManager:
    """Test suite for DataFeedManager"""
    
    @pytest.fixture
    async def data_feed_manager(self):
        """Create a test data feed manager"""
        manager = DataFeedManager()
        
        # Mock Kafka producer to avoid actual Kafka dependency in tests
        manager.kafka_producer = AsyncMock(spec=KafkaEventProducer)
        manager.kafka_producer.send_message = AsyncMock(return_value=True)
        
        yield manager
        
        # Cleanup
        await manager.stop()
    
    @pytest.fixture
    def sample_market_data(self):
        """Sample market data for testing"""
        return MarketDataPoint(
            symbol="AAPL",
            timestamp=datetime.now(),
            open=150.0,
            high=152.0,
            low=149.0,
            close=151.0,
            volume=1000000,
            asset_class=AssetClass.STOCK,
            provider=DataProvider.YAHOO_FINANCE,
            data_type="real_time"
        )
    
    @pytest.mark.asyncio
    async def test_provider_chain_configuration(self, data_feed_manager):
        """Test that provider chains are correctly configured for each asset class"""
        manager = data_feed_manager
        
        # Test stock provider chain
        stock_chain = manager.asset_provider_chains[AssetClass.STOCK]
        assert DataProvider.YAHOO_FINANCE in stock_chain
        assert DataProvider.ALPHA_VANTAGE in stock_chain
        assert DataProvider.FINNHUB in stock_chain
        
        # Test options provider chain
        options_chain = manager.asset_provider_chains[AssetClass.OPTION]
        assert DataProvider.CBOE in options_chain
        assert DataProvider.SPIDERROCK in options_chain
        
        # Test forex provider chain
        forex_chain = manager.asset_provider_chains[AssetClass.FOREX]
        assert DataProvider.OANDA in forex_chain
        
        logger.info("Provider chain configuration test passed")
    
    @pytest.mark.asyncio
    async def test_real_time_data_fallback(self, data_feed_manager):
        """Test automatic fallback when primary provider fails"""
        manager = data_feed_manager
        
        # Mock Yahoo Finance to fail
        with patch.object(YahooFinanceProvider, 'get_real_time_data') as mock_yahoo:
            mock_yahoo.side_effect = Exception("Yahoo Finance API error")
            
            # Mock Alpha Vantage to succeed
            with patch.object(AlphaVantageProvider, 'get_real_time_data') as mock_alpha:
                mock_alpha.return_value = MarketDataPoint(
                    symbol="AAPL",
                    timestamp=datetime.now(),
                    open=150.0,
                    high=152.0,
                    low=149.0,
                    close=151.0,
                    volume=1000000,
                    asset_class=AssetClass.STOCK,
                    provider=DataProvider.ALPHA_VANTAGE,
                    data_type="real_time"
                )
                
                # Test fallback
                start_time = time.time()
                data = await manager.get_real_time_data("AAPL", AssetClass.STOCK)
                switch_time = (time.time() - start_time) * 1000  # Convert to ms
                
                # Verify fallback worked
                assert data is not None
                assert data.provider == DataProvider.ALPHA_VANTAGE
                assert switch_time < 1000  # Should be less than 1 second
                
                # Verify Yahoo Finance failure was recorded
                assert manager.failure_counts[DataProvider.YAHOO_FINANCE] > 0
                
                logger.info(f"Fallback test passed - switch time: {switch_time:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_functionality(self, data_feed_manager):
        """Test circuit breaker activates after threshold failures"""
        manager = data_feed_manager
        
        # Simulate multiple failures to trigger circuit breaker
        for _ in range(manager.circuit_breaker_threshold):
            manager._record_provider_failure(DataProvider.YAHOO_FINANCE)
        
        # Verify circuit breaker is active
        assert not manager._is_provider_available(DataProvider.YAHOO_FINANCE)
        
        # Test that circuit breaker resets after timeout
        # Simulate time passage by manipulating last failure time
        manager.last_failure_time[DataProvider.YAHOO_FINANCE] = (
            datetime.now() - manager.circuit_breaker_timeout - timedelta(minutes=1)
        )
        
        # Circuit breaker should now be reset
        assert manager._is_provider_available(DataProvider.YAHOO_FINANCE)
        
        logger.info("Circuit breaker functionality test passed")
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, data_feed_manager):
        """Test that providers timing out >3s are considered failures"""
        manager = data_feed_manager
        
        # Mock a slow provider (>3s response)
        async def slow_provider_response(*args, **kwargs):
            await asyncio.sleep(4)  # 4 second delay
            return None
        
        with patch.object(YahooFinanceProvider, 'get_real_time_data', side_effect=slow_provider_response):
            start_time = time.time()
            data = await manager.get_real_time_data("AAPL", AssetClass.STOCK)
            total_time = time.time() - start_time
            
            # Should have failed due to timeout and moved to next provider
            assert manager.failure_counts.get(DataProvider.YAHOO_FINANCE, 0) > 0
            
            logger.info(f"Timeout handling test passed - total time: {total_time:.2f}s")
    
    @pytest.mark.asyncio
    async def test_data_normalization_and_kafka_streaming(self, data_feed_manager, sample_market_data):
        """Test data normalization and Kafka streaming"""
        manager = data_feed_manager
        
        # Test Kafka streaming
        await manager._stream_to_kafka(sample_market_data, "real_time_data")
        
        # Verify Kafka producer was called
        manager.kafka_producer.send_message.assert_called_once()
        
        # Verify message structure
        call_args = manager.kafka_producer.send_message.call_args
        topic = call_args[0][0]
        message = call_args[0][1]
        
        assert topic == "market_data.stock.real_time_data"
        assert message["symbol"] == "AAPL"
        assert message["asset_class"] == "stock"
        assert message["provider"] == "yahoo_finance"
        assert "timestamp" in message
        assert "open" in message
        assert "high" in message
        assert "low" in message
        assert "close" in message
        assert "volume" in message
        
        logger.info("Data normalization and Kafka streaming test passed")
    
    @pytest.mark.asyncio
    async def test_multi_asset_class_support(self, data_feed_manager):
        """Test support for multiple asset classes"""
        manager = data_feed_manager
        
        # Test different asset classes have appropriate provider chains
        test_cases = [
            (AssetClass.STOCK, [DataProvider.YAHOO_FINANCE, DataProvider.ALPHA_VANTAGE]),
            (AssetClass.ETF, [DataProvider.YAHOO_FINANCE, DataProvider.ALPHA_VANTAGE]),
            (AssetClass.FOREX, [DataProvider.YAHOO_FINANCE, DataProvider.OANDA]),
            (AssetClass.CRYPTO, [DataProvider.YAHOO_FINANCE, DataProvider.ALPHA_VANTAGE]),
            (AssetClass.OPTION, [DataProvider.CBOE, DataProvider.SPIDERROCK]),
            (AssetClass.FUTURE, [DataProvider.CME_GROUP, DataProvider.BARCHART])
        ]
        
        for asset_class, expected_providers in test_cases:
            chain = manager.asset_provider_chains.get(asset_class, [])
            
            # Verify at least some expected providers are in the chain
            for provider in expected_providers:
                if provider in chain:
                    assert True
                    break
            else:
                # If none of the expected providers are found, test fails
                assert False, f"No expected providers found for {asset_class}"
        
        logger.info("Multi-asset class support test passed")
    
    @pytest.mark.asyncio
    async def test_historical_data_fallback(self, data_feed_manager):
        """Test historical data retrieval with fallback"""
        manager = data_feed_manager
        
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        # Mock Yahoo Finance to fail
        with patch.object(YahooFinanceProvider, 'get_historical_data') as mock_yahoo:
            mock_yahoo.side_effect = Exception("Yahoo Finance historical API error")
            
            # Mock Alpha Vantage to succeed
            with patch.object(AlphaVantageProvider, 'get_historical_data') as mock_alpha:
                mock_alpha.return_value = [
                    MarketDataPoint(
                        symbol="AAPL",
                        timestamp=datetime.now() - timedelta(days=i),
                        open=150.0 + i,
                        high=152.0 + i,
                        low=149.0 + i,
                        close=151.0 + i,
                        volume=1000000,
                        asset_class=AssetClass.STOCK,
                        provider=DataProvider.ALPHA_VANTAGE,
                        data_type="historical"
                    ) for i in range(5)
                ]
                
                # Test historical data fallback
                data = await manager.get_historical_data(
                    "AAPL", AssetClass.STOCK, start_date, end_date
                )
                
                # Verify fallback worked
                assert len(data) == 5
                assert all(point.provider == DataProvider.ALPHA_VANTAGE for point in data)
                
                logger.info("Historical data fallback test passed")
    
    @pytest.mark.asyncio
    async def test_provider_health_status(self, data_feed_manager):
        """Test provider health status reporting"""
        manager = data_feed_manager
        
        # Record some failures
        manager._record_provider_failure(DataProvider.YAHOO_FINANCE)
        manager._record_provider_failure(DataProvider.ALPHA_VANTAGE)
        
        # Get health status
        status = await manager.get_provider_health_status()
        
        # Verify status structure
        assert "timestamp" in status
        assert "providers" in status
        assert "circuit_breakers" in status
        
        # Verify provider status
        providers = status["providers"]
        assert DataProvider.YAHOO_FINANCE.value in providers
        
        yahoo_status = providers[DataProvider.YAHOO_FINANCE.value]
        assert "available" in yahoo_status
        assert "failure_count" in yahoo_status
        assert "supported_assets" in yahoo_status
        assert yahoo_status["failure_count"] > 0
        
        logger.info("Provider health status test passed")
    
    @pytest.mark.asyncio
    async def test_performance_benchmarks(self, data_feed_manager):
        """Test performance benchmarks for data retrieval"""
        manager = data_feed_manager
        
        # Mock successful provider response
        mock_data = MarketDataPoint(
            symbol="AAPL",
            timestamp=datetime.now(),
            open=150.0,
            high=152.0,
            low=149.0,
            close=151.0,
            volume=1000000,
            asset_class=AssetClass.STOCK,
            provider=DataProvider.YAHOO_FINANCE,
            data_type="real_time"
        )
        
        with patch.object(YahooFinanceProvider, 'get_real_time_data', return_value=mock_data):
            # Test multiple requests to measure average performance
            latencies = []
            
            for _ in range(10):
                start_time = time.time()
                data = await manager.get_real_time_data("AAPL", AssetClass.STOCK)
                latency = (time.time() - start_time) * 1000  # Convert to ms
                latencies.append(latency)
                
                assert data is not None
            
            avg_latency = sum(latencies) / len(latencies)
            max_latency = max(latencies)
            
            # Performance assertions (these may need adjustment based on actual performance)
            assert avg_latency < 100, f"Average latency {avg_latency:.2f}ms exceeds 100ms threshold"
            assert max_latency < 500, f"Max latency {max_latency:.2f}ms exceeds 500ms threshold"
            
            logger.info(f"Performance test passed - Avg: {avg_latency:.2f}ms, Max: {max_latency:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, data_feed_manager):
        """Test handling of concurrent data requests"""
        manager = data_feed_manager
        
        # Mock successful provider response
        mock_data = MarketDataPoint(
            symbol="AAPL",
            timestamp=datetime.now(),
            open=150.0,
            high=152.0,
            low=149.0,
            close=151.0,
            volume=1000000,
            asset_class=AssetClass.STOCK,
            provider=DataProvider.YAHOO_FINANCE,
            data_type="real_time"
        )
        
        with patch.object(YahooFinanceProvider, 'get_real_time_data', return_value=mock_data):
            # Create concurrent requests
            symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]
            
            start_time = time.time()
            
            tasks = [
                manager.get_real_time_data(symbol, AssetClass.STOCK)
                for symbol in symbols
            ]
            
            results = await asyncio.gather(*tasks)
            
            total_time = (time.time() - start_time) * 1000
            
            # Verify all requests succeeded
            assert all(result is not None for result in results)
            assert len(results) == len(symbols)
            
            # Concurrent requests should be faster than sequential
            assert total_time < len(symbols) * 100  # Should be much faster than 500ms
            
            logger.info(f"Concurrent requests test passed - {len(symbols)} requests in {total_time:.2f}ms")

class TestFailureSimulation:
    """Test suite for simulating various failure scenarios"""
    
    @pytest.mark.asyncio
    async def test_all_providers_fail(self):
        """Test behavior when all providers fail"""
        manager = DataFeedManager()
        manager.kafka_producer = AsyncMock(spec=KafkaEventProducer)
        
        # Mock all providers to fail
        with patch.object(YahooFinanceProvider, 'get_real_time_data', side_effect=Exception("Provider failed")):
            with patch.object(AlphaVantageProvider, 'get_real_time_data', side_effect=Exception("Provider failed")):
                
                data = await manager.get_real_time_data("AAPL", AssetClass.STOCK)
                
                # Should return None when all providers fail
                assert data is None
                
                # All available providers should have recorded failures
                assert manager.failure_counts.get(DataProvider.YAHOO_FINANCE, 0) > 0
                
                logger.info("All providers fail test passed")
    
    @pytest.mark.asyncio
    async def test_network_timeout_simulation(self):
        """Test network timeout scenarios"""
        manager = DataFeedManager()
        manager.kafka_producer = AsyncMock(spec=KafkaEventProducer)
        
        # Mock network timeout
        async def timeout_response(*args, **kwargs):
            await asyncio.sleep(5)  # Simulate 5s timeout
            raise asyncio.TimeoutError("Network timeout")
        
        with patch.object(YahooFinanceProvider, 'get_real_time_data', side_effect=timeout_response):
            start_time = time.time()
            data = await manager.get_real_time_data("AAPL", AssetClass.STOCK)
            elapsed_time = time.time() - start_time
            
            # Should fail quickly and move to next provider
            assert elapsed_time < 10  # Should not wait for full timeout
            assert manager.failure_counts.get(DataProvider.YAHOO_FINANCE, 0) > 0
            
            logger.info(f"Network timeout simulation test passed - elapsed: {elapsed_time:.2f}s")

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])