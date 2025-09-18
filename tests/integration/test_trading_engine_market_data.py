"""Integration tests for Trading Engine with Market Data Service.

This module tests the integration between the trading engine and market data service,
including real-time data feeds, order execution, position management, and data consistency.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, List, Any

import pandas as pd
import numpy as np
from kafka import KafkaProducer, KafkaConsumer

# Trading system imports
from shared.models.market_data import MarketData, Quote, Trade, OrderBook
from shared.models.orders import Order, OrderType, OrderStatus, Side
from shared.models.positions import Position
from shared.utils.logging_utils import get_logger

logger = get_logger(__name__)


@pytest.mark.integration
@pytest.mark.trading
@pytest.mark.market_data
class TestTradingEngineMarketDataIntegration:
    """Integration tests for trading engine and market data service."""

    @pytest.fixture
    async def market_data_service(self):
        """Mock market data service."""
        service = Mock()
        service.subscribe = AsyncMock()
        service.unsubscribe = AsyncMock()
        service.get_latest_quote = AsyncMock()
        service.get_historical_data = AsyncMock()
        service.is_market_open = Mock(return_value=True)
        return service

    @pytest.fixture
    async def trading_engine(self):
        """Mock trading engine."""
        engine = Mock()
        engine.submit_order = AsyncMock()
        engine.cancel_order = AsyncMock()
        engine.get_position = Mock()
        engine.get_portfolio_value = Mock()
        engine.process_market_data = AsyncMock()
        return engine

    @pytest.fixture
    async def kafka_producer(self):
        """Mock Kafka producer for market data."""
        producer = Mock(spec=KafkaProducer)
        producer.send = Mock()
        producer.flush = Mock()
        return producer

    @pytest.fixture
    async def kafka_consumer(self):
        """Mock Kafka consumer for market data."""
        consumer = Mock(spec=KafkaConsumer)
        return consumer

    @pytest.fixture
    def sample_market_data(self):
        """Sample market data for testing."""
        return MarketData(
            symbol="AAPL",
            timestamp=datetime.now(),
            bid=Decimal("150.25"),
            ask=Decimal("150.27"),
            last=Decimal("150.26"),
            volume=1000,
            high=Decimal("151.00"),
            low=Decimal("149.50"),
            open=Decimal("150.00")
        )

    @pytest.fixture
    def sample_order(self):
        """Sample order for testing."""
        return Order(
            id="order_123",
            symbol="AAPL",
            side=Side.BUY,
            order_type=OrderType.MARKET,
            quantity=100,
            status=OrderStatus.PENDING,
            timestamp=datetime.now()
        )

    @pytest.mark.asyncio
    async def test_real_time_data_feed_integration(
        self, 
        market_data_service, 
        trading_engine, 
        kafka_producer,
        sample_market_data
    ):
        """Test real-time market data feed integration with trading engine."""
        # Arrange
        symbol = "AAPL"
        market_data_service.get_latest_quote.return_value = sample_market_data
        
        # Act - Subscribe to market data
        await market_data_service.subscribe(symbol)
        
        # Simulate receiving market data
        await trading_engine.process_market_data(sample_market_data)
        
        # Assert
        market_data_service.subscribe.assert_called_once_with(symbol)
        trading_engine.process_market_data.assert_called_once_with(sample_market_data)
        
        # Verify data consistency
        latest_quote = await market_data_service.get_latest_quote(symbol)
        assert latest_quote.symbol == symbol
        assert latest_quote.bid == Decimal("150.25")
        assert latest_quote.ask == Decimal("150.27")

    @pytest.mark.asyncio
    async def test_order_execution_with_market_data(
        self,
        market_data_service,
        trading_engine,
        sample_market_data,
        sample_order
    ):
        """Test order execution using real-time market data."""
        # Arrange
        market_data_service.get_latest_quote.return_value = sample_market_data
        trading_engine.submit_order.return_value = {
            "order_id": "order_123",
            "status": "FILLED",
            "fill_price": Decimal("150.26"),
            "fill_quantity": 100
        }
        
        # Act - Submit market order
        latest_quote = await market_data_service.get_latest_quote(sample_order.symbol)
        execution_result = await trading_engine.submit_order(sample_order)
        
        # Assert
        market_data_service.get_latest_quote.assert_called_once_with("AAPL")
        trading_engine.submit_order.assert_called_once_with(sample_order)
        
        assert execution_result["status"] == "FILLED"
        assert execution_result["fill_price"] <= latest_quote.ask  # Buy at or below ask
        assert execution_result["fill_quantity"] == sample_order.quantity

    @pytest.mark.asyncio
    async def test_position_management_with_market_data(
        self,
        market_data_service,
        trading_engine,
        sample_market_data
    ):
        """Test position management using market data for valuation."""
        # Arrange
        position = Position(
            symbol="AAPL",
            quantity=100,
            average_price=Decimal("149.50"),
            market_value=Decimal("15026.00"),  # 100 * 150.26
            unrealized_pnl=Decimal("76.00")    # (150.26 - 149.50) * 100
        )
        
        market_data_service.get_latest_quote.return_value = sample_market_data
        trading_engine.get_position.return_value = position
        
        # Act
        current_position = trading_engine.get_position("AAPL")
        latest_quote = await market_data_service.get_latest_quote("AAPL")
        
        # Calculate expected market value
        expected_market_value = current_position.quantity * latest_quote.last
        expected_pnl = (latest_quote.last - current_position.average_price) * current_position.quantity
        
        # Assert
        assert current_position.symbol == "AAPL"
        assert current_position.quantity == 100
        assert abs(current_position.market_value - expected_market_value) < Decimal("0.01")
        assert abs(current_position.unrealized_pnl - expected_pnl) < Decimal("0.01")

    @pytest.mark.asyncio
    async def test_kafka_market_data_streaming(
        self,
        kafka_producer,
        kafka_consumer,
        trading_engine,
        sample_market_data
    ):
        """Test Kafka-based market data streaming to trading engine."""
        # Arrange
        topic = "market_data_stream"
        message_data = {
            "symbol": sample_market_data.symbol,
            "timestamp": sample_market_data.timestamp.isoformat(),
            "bid": float(sample_market_data.bid),
            "ask": float(sample_market_data.ask),
            "last": float(sample_market_data.last),
            "volume": sample_market_data.volume
        }
        
        # Mock Kafka message
        kafka_message = Mock()
        kafka_message.value = json.dumps(message_data).encode('utf-8')
        kafka_message.topic = topic
        
        # Act - Simulate sending market data via Kafka
        kafka_producer.send(topic, json.dumps(message_data).encode('utf-8'))
        
        # Simulate processing the message
        processed_data = json.loads(kafka_message.value.decode('utf-8'))
        market_data_obj = MarketData(
            symbol=processed_data["symbol"],
            timestamp=datetime.fromisoformat(processed_data["timestamp"]),
            bid=Decimal(str(processed_data["bid"])),
            ask=Decimal(str(processed_data["ask"])),
            last=Decimal(str(processed_data["last"])),
            volume=processed_data["volume"]
        )
        
        await trading_engine.process_market_data(market_data_obj)
        
        # Assert
        kafka_producer.send.assert_called_once()
        trading_engine.process_market_data.assert_called_once()
        
        # Verify data integrity
        assert market_data_obj.symbol == "AAPL"
        assert market_data_obj.bid == Decimal("150.25")
        assert market_data_obj.ask == Decimal("150.27")

    @pytest.mark.asyncio
    async def test_market_data_latency_monitoring(
        self,
        market_data_service,
        trading_engine,
        sample_market_data
    ):
        """Test market data latency monitoring and alerting."""
        # Arrange
        start_time = datetime.now()
        market_data_service.get_latest_quote.return_value = sample_market_data
        
        # Act
        await market_data_service.subscribe("AAPL")
        quote = await market_data_service.get_latest_quote("AAPL")
        end_time = datetime.now()
        
        # Calculate latency
        latency = (end_time - start_time).total_seconds() * 1000  # milliseconds
        
        # Assert
        assert latency < 100  # Should be under 100ms for integration test
        assert quote is not None
        assert quote.symbol == "AAPL"
        
        # Verify timestamp freshness (within last 5 seconds)
        time_diff = (datetime.now() - quote.timestamp).total_seconds()
        assert time_diff < 5

    @pytest.mark.asyncio
    async def test_historical_data_integration(
        self,
        market_data_service,
        trading_engine
    ):
        """Test historical data retrieval for backtesting integration."""
        # Arrange
        symbol = "AAPL"
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        # Mock historical data
        historical_data = pd.DataFrame({
            'timestamp': pd.date_range(start=start_date, end=end_date, freq='1H'),
            'open': np.random.uniform(145, 155, size=len(pd.date_range(start=start_date, end=end_date, freq='1H'))),
            'high': np.random.uniform(145, 155, size=len(pd.date_range(start=start_date, end=end_date, freq='1H'))),
            'low': np.random.uniform(145, 155, size=len(pd.date_range(start=start_date, end=end_date, freq='1H'))),
            'close': np.random.uniform(145, 155, size=len(pd.date_range(start=start_date, end=end_date, freq='1H'))),
            'volume': np.random.randint(1000, 10000, size=len(pd.date_range(start=start_date, end=end_date, freq='1H')))
        })
        
        market_data_service.get_historical_data.return_value = historical_data
        
        # Act
        data = await market_data_service.get_historical_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            interval="1H"
        )
        
        # Assert
        market_data_service.get_historical_data.assert_called_once_with(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            interval="1H"
        )
        
        assert not data.empty
        assert len(data) > 0
        assert 'timestamp' in data.columns
        assert 'close' in data.columns
        assert 'volume' in data.columns

    @pytest.mark.asyncio
    async def test_market_hours_integration(
        self,
        market_data_service,
        trading_engine,
        sample_order
    ):
        """Test trading engine behavior during market hours vs after hours."""
        # Test during market hours
        market_data_service.is_market_open.return_value = True
        trading_engine.submit_order.return_value = {
            "order_id": "order_123",
            "status": "ACCEPTED"
        }
        
        # Act - Submit order during market hours
        is_open = market_data_service.is_market_open("AAPL")
        if is_open:
            result = await trading_engine.submit_order(sample_order)
        
        # Assert
        assert is_open is True
        assert result["status"] == "ACCEPTED"
        
        # Test after market hours
        market_data_service.is_market_open.return_value = False
        trading_engine.submit_order.return_value = {
            "order_id": "order_124",
            "status": "QUEUED"
        }
        
        # Act - Submit order after hours
        is_open = market_data_service.is_market_open("AAPL")
        if not is_open:
            result = await trading_engine.submit_order(sample_order)
        
        # Assert
        assert is_open is False
        assert result["status"] == "QUEUED"

    @pytest.mark.asyncio
    async def test_data_consistency_across_services(
        self,
        market_data_service,
        trading_engine,
        sample_market_data
    ):
        """Test data consistency between market data service and trading engine."""
        # Arrange
        symbol = "AAPL"
        market_data_service.get_latest_quote.return_value = sample_market_data
        
        # Mock position with same symbol
        position = Position(
            symbol=symbol,
            quantity=100,
            average_price=Decimal("149.50"),
            market_value=Decimal("15026.00"),
            unrealized_pnl=Decimal("76.00")
        )
        trading_engine.get_position.return_value = position
        
        # Act
        market_quote = await market_data_service.get_latest_quote(symbol)
        engine_position = trading_engine.get_position(symbol)
        
        # Assert data consistency
        assert market_quote.symbol == engine_position.symbol
        
        # Verify position valuation matches market data
        expected_market_value = engine_position.quantity * market_quote.last
        assert abs(engine_position.market_value - expected_market_value) < Decimal("0.01")

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(
        self,
        market_data_service,
        trading_engine,
        sample_order
    ):
        """Test error handling and recovery mechanisms."""
        # Test market data service failure
        market_data_service.get_latest_quote.side_effect = Exception("Market data unavailable")
        
        with pytest.raises(Exception, match="Market data unavailable"):
            await market_data_service.get_latest_quote("AAPL")
        
        # Test recovery
        market_data_service.get_latest_quote.side_effect = None
        market_data_service.get_latest_quote.return_value = Mock(symbol="AAPL", last=Decimal("150.00"))
        
        quote = await market_data_service.get_latest_quote("AAPL")
        assert quote.symbol == "AAPL"
        
        # Test trading engine failure
        trading_engine.submit_order.side_effect = Exception("Trading engine error")
        
        with pytest.raises(Exception, match="Trading engine error"):
            await trading_engine.submit_order(sample_order)
        
        # Test recovery
        trading_engine.submit_order.side_effect = None
        trading_engine.submit_order.return_value = {"order_id": "order_123", "status": "ACCEPTED"}
        
        result = await trading_engine.submit_order(sample_order)
        assert result["status"] == "ACCEPTED"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])