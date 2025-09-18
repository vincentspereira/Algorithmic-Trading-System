"""Unit tests for Market Data Service.

This module contains comprehensive unit tests for the market data service,
including data ingestion, processing, validation, and distribution.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from decimal import Decimal

# Trading system imports
from src.market_data.service import MarketDataService
from src.market_data.models import (
    MarketData, Quote, Trade, OrderBook, Candle,
    DataSource, AssetClass, Symbol
)
from src.market_data.exceptions import (
    DataSourceError, ValidationError, RateLimitError
)
from src.common.events import MarketDataEvent
from src.common.config import MarketDataConfig


@pytest.fixture
def market_data_config():
    """Create market data configuration for testing."""
    return MarketDataConfig(
        primary_source="yahoo",
        fallback_sources=["alpha_vantage", "finnhub"],
        rate_limit_per_minute=60,
        cache_ttl_seconds=300,
        enable_real_time=True,
        enable_historical=True,
        max_retries=3,
        retry_delay=1.0
    )


@pytest.fixture
def mock_kafka_producer():
    """Create mock Kafka producer."""
    producer = AsyncMock()
    producer.send = AsyncMock()
    producer.flush = AsyncMock()
    return producer


@pytest.fixture
def mock_redis_client():
    """Create mock Redis client."""
    redis_client = AsyncMock()
    redis_client.get = AsyncMock()
    redis_client.set = AsyncMock()
    redis_client.delete = AsyncMock()
    return redis_client


@pytest.fixture
def sample_quote():
    """Create sample quote data."""
    return Quote(
        symbol="AAPL",
        bid=Decimal("150.25"),
        ask=Decimal("150.27"),
        bid_size=100,
        ask_size=200,
        timestamp=datetime.utcnow()
    )


@pytest.fixture
def sample_trade():
    """Create sample trade data."""
    return Trade(
        symbol="AAPL",
        price=Decimal("150.26"),
        size=500,
        timestamp=datetime.utcnow(),
        trade_id="T123456"
    )


@pytest.fixture
def sample_candle():
    """Create sample candle data."""
    return Candle(
        symbol="AAPL",
        open=Decimal("150.00"),
        high=Decimal("151.00"),
        low=Decimal("149.50"),
        close=Decimal("150.75"),
        volume=1000000,
        timestamp=datetime.utcnow(),
        timeframe="1m"
    )


@pytest.fixture
def sample_order_book():
    """Create sample order book data."""
    return OrderBook(
        symbol="AAPL",
        bids=[
            (Decimal("150.25"), 100),
            (Decimal("150.24"), 200),
            (Decimal("150.23"), 150)
        ],
        asks=[
            (Decimal("150.27"), 150),
            (Decimal("150.28"), 100),
            (Decimal("150.29"), 250)
        ],
        timestamp=datetime.utcnow()
    )


@pytest.fixture
def market_data_service(market_data_config, mock_kafka_producer, mock_redis_client):
    """Create market data service instance for testing."""
    service = MarketDataService(
        config=market_data_config,
        kafka_producer=mock_kafka_producer,
        redis_client=mock_redis_client
    )
    return service


class TestMarketDataService:
    """Test cases for MarketDataService."""

    @pytest.mark.asyncio
    async def test_service_initialization(self, market_data_service):
        """Test service initialization."""
        assert market_data_service.config.primary_source == "yahoo"
        assert len(market_data_service.config.fallback_sources) == 2
        assert market_data_service.is_running is False

    @pytest.mark.asyncio
    async def test_start_service(self, market_data_service):
        """Test starting the market data service."""
        with patch.object(market_data_service, '_initialize_data_sources') as mock_init:
            await market_data_service.start()
            assert market_data_service.is_running is True
            mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_service(self, market_data_service):
        """Test stopping the market data service."""
        market_data_service.is_running = True
        with patch.object(market_data_service, '_cleanup_resources') as mock_cleanup:
            await market_data_service.stop()
            assert market_data_service.is_running is False
            mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_subscribe_to_symbol(self, market_data_service):
        """Test subscribing to market data for a symbol."""
        symbol = "AAPL"
        data_types = ["quotes", "trades"]
        
        with patch.object(market_data_service, '_add_subscription') as mock_add:
            await market_data_service.subscribe(symbol, data_types)
            mock_add.assert_called_once_with(symbol, data_types)

    @pytest.mark.asyncio
    async def test_unsubscribe_from_symbol(self, market_data_service):
        """Test unsubscribing from market data for a symbol."""
        symbol = "AAPL"
        
        with patch.object(market_data_service, '_remove_subscription') as mock_remove:
            await market_data_service.unsubscribe(symbol)
            mock_remove.assert_called_once_with(symbol)

    @pytest.mark.asyncio
    async def test_get_quote_success(self, market_data_service, sample_quote):
        """Test successful quote retrieval."""
        symbol = "AAPL"
        
        with patch.object(market_data_service, '_fetch_from_primary_source') as mock_fetch:
            mock_fetch.return_value = sample_quote
            
            result = await market_data_service.get_quote(symbol)
            
            assert result == sample_quote
            assert result.symbol == symbol
            mock_fetch.assert_called_once_with(symbol, "quote")

    @pytest.mark.asyncio
    async def test_get_quote_with_fallback(self, market_data_service, sample_quote):
        """Test quote retrieval with fallback to secondary source."""
        symbol = "AAPL"
        
        with patch.object(market_data_service, '_fetch_from_primary_source') as mock_primary:
            with patch.object(market_data_service, '_fetch_from_fallback_sources') as mock_fallback:
                mock_primary.side_effect = DataSourceError("Primary source failed")
                mock_fallback.return_value = sample_quote
                
                result = await market_data_service.get_quote(symbol)
                
                assert result == sample_quote
                mock_primary.assert_called_once()
                mock_fallback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_historical_data(self, market_data_service):
        """Test historical data retrieval."""
        symbol = "AAPL"
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        timeframe = "1d"
        
        expected_data = pd.DataFrame({
            'timestamp': pd.date_range(start_date, end_date, freq='D'),
            'open': np.random.uniform(140, 160, 31),
            'high': np.random.uniform(145, 165, 31),
            'low': np.random.uniform(135, 155, 31),
            'close': np.random.uniform(140, 160, 31),
            'volume': np.random.randint(1000000, 10000000, 31)
        })
        
        with patch.object(market_data_service, '_fetch_historical_data') as mock_fetch:
            mock_fetch.return_value = expected_data
            
            result = await market_data_service.get_historical_data(
                symbol, start_date, end_date, timeframe
            )
            
            assert isinstance(result, pd.DataFrame)
            assert len(result) == len(expected_data)
            mock_fetch.assert_called_once_with(symbol, start_date, end_date, timeframe)

    @pytest.mark.asyncio
    async def test_process_market_data_event(self, market_data_service, sample_quote):
        """Test processing of market data events."""
        event = MarketDataEvent(
            event_type="quote_update",
            symbol="AAPL",
            data=sample_quote,
            timestamp=datetime.utcnow()
        )
        
        with patch.object(market_data_service, '_validate_data') as mock_validate:
            with patch.object(market_data_service, '_publish_to_kafka') as mock_publish:
                mock_validate.return_value = True
                
                await market_data_service.process_event(event)
                
                mock_validate.assert_called_once_with(sample_quote)
                mock_publish.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_data_validation_success(self, market_data_service, sample_quote):
        """Test successful data validation."""
        result = market_data_service._validate_data(sample_quote)
        assert result is True

    @pytest.mark.asyncio
    async def test_data_validation_failure(self, market_data_service):
        """Test data validation failure."""
        invalid_quote = Quote(
            symbol="",  # Invalid empty symbol
            bid=Decimal("-1.0"),  # Invalid negative bid
            ask=Decimal("0.0"),  # Invalid zero ask
            bid_size=0,
            ask_size=0,
            timestamp=None  # Invalid timestamp
        )
        
        with pytest.raises(ValidationError):
            market_data_service._validate_data(invalid_quote)

    @pytest.mark.asyncio
    async def test_rate_limiting(self, market_data_service):
        """Test rate limiting functionality."""
        symbol = "AAPL"
        
        # Simulate rate limit exceeded
        with patch.object(market_data_service, '_check_rate_limit') as mock_check:
            mock_check.return_value = False
            
            with pytest.raises(RateLimitError):
                await market_data_service.get_quote(symbol)

    @pytest.mark.asyncio
    async def test_caching_mechanism(self, market_data_service, sample_quote, mock_redis_client):
        """Test data caching mechanism."""
        symbol = "AAPL"
        cache_key = f"quote:{symbol}"
        
        # Test cache miss and set
        mock_redis_client.get.return_value = None
        
        with patch.object(market_data_service, '_fetch_from_primary_source') as mock_fetch:
            mock_fetch.return_value = sample_quote
            
            result = await market_data_service.get_quote(symbol)
            
            assert result == sample_quote
            mock_redis_client.get.assert_called_with(cache_key)
            mock_redis_client.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_hit(self, market_data_service, sample_quote, mock_redis_client):
        """Test cache hit scenario."""
        symbol = "AAPL"
        cache_key = f"quote:{symbol}"
        
        # Simulate cache hit
        mock_redis_client.get.return_value = sample_quote.json()
        
        with patch.object(market_data_service, '_fetch_from_primary_source') as mock_fetch:
            result = await market_data_service.get_quote(symbol)
            
            # Should not call primary source when cache hit
            mock_fetch.assert_not_called()
            mock_redis_client.get.assert_called_with(cache_key)

    @pytest.mark.asyncio
    async def test_multiple_symbol_subscription(self, market_data_service):
        """Test subscribing to multiple symbols."""
        symbols = ["AAPL", "GOOGL", "MSFT"]
        data_types = ["quotes", "trades"]
        
        with patch.object(market_data_service, '_add_subscription') as mock_add:
            for symbol in symbols:
                await market_data_service.subscribe(symbol, data_types)
            
            assert mock_add.call_count == len(symbols)

    @pytest.mark.asyncio
    async def test_data_source_failover(self, market_data_service, sample_quote):
        """Test automatic failover between data sources."""
        symbol = "AAPL"
        
        with patch.object(market_data_service, '_fetch_from_source') as mock_fetch:
            # First source fails, second succeeds
            mock_fetch.side_effect = [
                DataSourceError("Yahoo failed"),
                sample_quote
            ]
            
            result = await market_data_service.get_quote(symbol)
            
            assert result == sample_quote
            assert mock_fetch.call_count == 2

    @pytest.mark.asyncio
    async def test_real_time_data_streaming(self, market_data_service, sample_quote):
        """Test real-time data streaming."""
        symbol = "AAPL"
        
        with patch.object(market_data_service, '_start_real_time_stream') as mock_stream:
            await market_data_service.start_real_time_feed(symbol)
            mock_stream.assert_called_once_with(symbol)

    @pytest.mark.asyncio
    async def test_order_book_processing(self, market_data_service, sample_order_book):
        """Test order book data processing."""
        with patch.object(market_data_service, '_process_order_book') as mock_process:
            await market_data_service.update_order_book(sample_order_book)
            mock_process.assert_called_once_with(sample_order_book)

    @pytest.mark.asyncio
    async def test_market_hours_validation(self, market_data_service):
        """Test market hours validation."""
        symbol = "AAPL"
        
        with patch.object(market_data_service, '_is_market_open') as mock_market_hours:
            mock_market_hours.return_value = False
            
            # Should handle closed market gracefully
            result = await market_data_service.get_quote(symbol)
            
            # Should return cached data or None when market is closed
            mock_market_hours.assert_called_once_with(symbol)

    @pytest.mark.asyncio
    async def test_error_handling_and_logging(self, market_data_service, caplog):
        """Test error handling and logging."""
        symbol = "INVALID_SYMBOL"
        
        with patch.object(market_data_service, '_fetch_from_primary_source') as mock_fetch:
            mock_fetch.side_effect = Exception("Unexpected error")
            
            with pytest.raises(Exception):
                await market_data_service.get_quote(symbol)
            
            # Check that error was logged
            assert "Unexpected error" in caplog.text

    @pytest.mark.asyncio
    async def test_metrics_collection(self, market_data_service):
        """Test metrics collection for monitoring."""
        symbol = "AAPL"
        
        with patch.object(market_data_service, '_record_metrics') as mock_metrics:
            with patch.object(market_data_service, '_fetch_from_primary_source') as mock_fetch:
                mock_fetch.return_value = Mock()
                
                await market_data_service.get_quote(symbol)
                
                mock_metrics.assert_called()

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, market_data_service, sample_quote):
        """Test handling of concurrent requests."""
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]
        
        with patch.object(market_data_service, '_fetch_from_primary_source') as mock_fetch:
            mock_fetch.return_value = sample_quote
            
            # Execute concurrent requests
            tasks = [market_data_service.get_quote(symbol) for symbol in symbols]
            results = await asyncio.gather(*tasks)
            
            assert len(results) == len(symbols)
            assert all(result == sample_quote for result in results)


@pytest.mark.integration
class TestMarketDataServiceIntegration:
    """Integration tests for MarketDataService."""

    @pytest.mark.asyncio
    async def test_end_to_end_data_flow(self, market_data_service, sample_quote):
        """Test complete data flow from source to Kafka."""
        symbol = "AAPL"
        
        with patch.object(market_data_service, '_fetch_from_primary_source') as mock_fetch:
            with patch.object(market_data_service.kafka_producer, 'send') as mock_send:
                mock_fetch.return_value = sample_quote
                
                # Subscribe and get data
                await market_data_service.subscribe(symbol, ["quotes"])
                result = await market_data_service.get_quote(symbol)
                
                assert result == sample_quote
                # Verify data was published to Kafka
                mock_send.assert_called()

    @pytest.mark.asyncio
    async def test_failover_recovery(self, market_data_service, sample_quote):
        """Test recovery after data source failure."""
        symbol = "AAPL"
        
        with patch.object(market_data_service, '_fetch_from_source') as mock_fetch:
            # Simulate primary failure, then recovery
            mock_fetch.side_effect = [
                DataSourceError("Primary failed"),
                sample_quote,  # Fallback succeeds
                sample_quote   # Primary recovered
            ]
            
            # First call should use fallback
            result1 = await market_data_service.get_quote(symbol)
            assert result1 == sample_quote
            
            # Second call should use recovered primary
            result2 = await market_data_service.get_quote(symbol)
            assert result2 == sample_quote


@pytest.mark.performance
class TestMarketDataServicePerformance:
    """Performance tests for MarketDataService."""

    @pytest.mark.asyncio
    async def test_high_frequency_requests(self, market_data_service, sample_quote):
        """Test performance under high frequency requests."""
        symbol = "AAPL"
        num_requests = 1000
        
        with patch.object(market_data_service, '_fetch_from_primary_source') as mock_fetch:
            mock_fetch.return_value = sample_quote
            
            start_time = datetime.utcnow()
            
            # Execute high frequency requests
            tasks = [market_data_service.get_quote(symbol) for _ in range(num_requests)]
            results = await asyncio.gather(*tasks)
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            assert len(results) == num_requests
            assert duration < 10.0  # Should complete within 10 seconds
            
            # Calculate requests per second
            rps = num_requests / duration
            assert rps > 100  # Should handle at least 100 RPS

    @pytest.mark.asyncio
    async def test_memory_usage(self, market_data_service, sample_quote):
        """Test memory usage under load."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        symbol = "AAPL"
        num_requests = 5000
        
        with patch.object(market_data_service, '_fetch_from_primary_source') as mock_fetch:
            mock_fetch.return_value = sample_quote
            
            # Execute many requests
            for _ in range(num_requests):
                await market_data_service.get_quote(symbol)
            
            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory
            
            # Memory increase should be reasonable (less than 100MB)
            assert memory_increase < 100 * 1024 * 1024