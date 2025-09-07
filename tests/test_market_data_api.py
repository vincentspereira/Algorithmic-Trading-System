"""Test Suite for Market Data Service API

Comprehensive tests for REST endpoints, provider management, data retrieval,
streaming functionality, and performance benchmarks.
"""

import asyncio
import json
import pytest
from datetime import datetime, timedelta
from typing import Dict, List, Any
from unittest.mock import Mock, AsyncMock, patch

from fastapi.testclient import TestClient
from httpx import AsyncClient
import httpx

from market_data_service.api import app
from market_data_service.data_feed_manager import (
    DataFeedManager, 
    AssetClass, 
    DataProvider,
    MarketDataPoint,
    DataType
)
from market_data_service.provider_configs import ProviderConfig, ProviderTier
from shared.utils.logging_utils import get_logger

logger = get_logger(__name__)

class TestMarketDataAPI:
    """Test suite for Market Data Service API"""
    
    def setup_method(self):
        """Set up test environment"""
        self.client = TestClient(app)
        self.mock_manager = Mock(spec=DataFeedManager)
        self.test_symbol = "AAPL"
        self.test_asset_class = AssetClass.STOCK
        
        # Mock data
        self.mock_data_point = MarketDataPoint(
            symbol=self.test_symbol,
            timestamp=datetime.now(),
            open=150.0,
            high=155.0,
            low=149.0,
            close=154.0,
            volume=1000000,
            asset_class=self.test_asset_class,
            provider=DataProvider.YAHOO_FINANCE,
            data_type=DataType.REAL_TIME,
            metadata={"exchange": "NASDAQ"}
        )
        
    def test_health_check(self):
        """Test health check endpoint"""
        response = self.client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["service"] == "Market Data Service"
        assert data["version"] == "1.0.0"
        
    @patch('market_data_service.api.get_available_providers')
    @patch('market_data_service.api.get_provider_config')
    @patch('market_data_service.api.validate_provider_credentials')
    def test_get_providers(self, mock_validate, mock_get_config, mock_get_available):
        """Test get providers endpoint"""
        # Mock provider configuration
        mock_config = ProviderConfig(
            name="yahoo_finance",
            display_name="Yahoo Finance",
            tier=ProviderTier.PRIMARY,
            api_key_required=False,
            supported_exchanges=["NYSE", "NASDAQ"],
            supported_countries=["US"],
            data_quality_score=0.85,
            free_tier_available=True
        )
        
        mock_get_available.return_value = ["yahoo_finance"]
        mock_get_config.return_value = mock_config
        mock_validate.return_value = {"yahoo_finance": True}
        
        response = self.client.get("/providers")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "yahoo_finance"
        assert data[0]["display_name"] == "Yahoo Finance"
        assert data[0]["tier"] == "primary"
        assert data[0]["has_api_key"] is True
        
    @patch('market_data_service.api.get_manager')
    def test_get_provider_health(self, mock_get_manager):
        """Test provider health status endpoint"""
        # Mock health status
        mock_health = {
            "timestamp": datetime.now().isoformat(),
            "providers": {
                "yahoo_finance": {
                    "status": "healthy",
                    "last_success": datetime.now().isoformat(),
                    "failure_count": 0,
                    "response_time_ms": 150.5
                }
            },
            "circuit_breakers": {
                "yahoo_finance": {
                    "active": False,
                    "failure_threshold": 5,
                    "current_failures": 0
                }
            }
        }
        
        self.mock_manager.get_provider_health_status = AsyncMock(return_value=mock_health)
        mock_get_manager.return_value = self.mock_manager
        
        response = self.client.get("/providers/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "timestamp" in data
        assert "providers" in data
        assert "circuit_breakers" in data
        assert "yahoo_finance" in data["providers"]
        
    @patch('market_data_service.api.get_providers_for_asset_class')
    def test_get_providers_for_asset(self, mock_get_providers):
        """Test get providers for specific asset class"""
        mock_providers = ["yahoo_finance", "alpha_vantage", "finnhub"]
        mock_get_providers.return_value = mock_providers
        
        response = self.client.get(f"/providers/{AssetClass.STOCK.value}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["asset_class"] == AssetClass.STOCK.value
        assert data["providers"] == mock_providers
        assert data["count"] == len(mock_providers)
        
    @patch('market_data_service.api.get_manager')
    def test_get_real_time_data_success(self, mock_get_manager):
        """Test successful real-time data retrieval"""
        self.mock_manager.get_real_time_data = AsyncMock(return_value=self.mock_data_point)
        mock_get_manager.return_value = self.mock_manager
        
        response = self.client.get(
            f"/data/real-time/{self.test_symbol}?asset_class={self.test_asset_class.value}"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["symbol"] == self.test_symbol
        assert data["close"] == 154.0
        assert data["volume"] == 1000000
        assert data["asset_class"] == self.test_asset_class.value
        assert data["provider"] == DataProvider.YAHOO_FINANCE.value
        
    @patch('market_data_service.api.get_manager')
    def test_get_real_time_data_not_found(self, mock_get_manager):
        """Test real-time data retrieval when no data available"""
        self.mock_manager.get_real_time_data = AsyncMock(return_value=None)
        mock_get_manager.return_value = self.mock_manager
        
        response = self.client.get(
            f"/data/real-time/INVALID?asset_class={self.test_asset_class.value}"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert "No real-time data available" in data["detail"]
        
    @patch('market_data_service.api.get_manager')
    def test_get_historical_data(self, mock_get_manager):
        """Test historical data retrieval"""
        # Create multiple data points for historical data
        historical_data = [
            MarketDataPoint(
                symbol=self.test_symbol,
                timestamp=datetime.now() - timedelta(days=i),
                open=150.0 + i,
                high=155.0 + i,
                low=149.0 + i,
                close=154.0 + i,
                volume=1000000 + i * 10000,
                asset_class=self.test_asset_class,
                provider=DataProvider.YAHOO_FINANCE,
                data_type=DataType.HISTORICAL,
                metadata={"exchange": "NASDAQ"}
            )
            for i in range(5)
        ]
        
        self.mock_manager.get_historical_data = AsyncMock(return_value=historical_data)
        mock_get_manager.return_value = self.mock_manager
        
        request_data = {
            "symbol": self.test_symbol,
            "asset_class": self.test_asset_class.value,
            "start_date": (datetime.now() - timedelta(days=7)).isoformat(),
            "end_date": datetime.now().isoformat(),
            "interval": "1d"
        }
        
        response = self.client.post("/data/historical", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 5
        assert all(point["symbol"] == self.test_symbol for point in data)
        assert all(point["asset_class"] == self.test_asset_class.value for point in data)
        
    @patch('market_data_service.api.get_manager')
    def test_get_bulk_data_real_time(self, mock_get_manager):
        """Test bulk real-time data retrieval"""
        symbols = ["AAPL", "GOOGL", "MSFT"]
        
        # Mock data for each symbol
        mock_data_points = {
            symbol: MarketDataPoint(
                symbol=symbol,
                timestamp=datetime.now(),
                open=150.0,
                high=155.0,
                low=149.0,
                close=154.0,
                volume=1000000,
                asset_class=self.test_asset_class,
                provider=DataProvider.YAHOO_FINANCE,
                data_type=DataType.REAL_TIME,
                metadata={"exchange": "NASDAQ"}
            )
            for symbol in symbols
        }
        
        async def mock_get_real_time(symbol, asset_class):
            return mock_data_points.get(symbol)
        
        self.mock_manager.get_real_time_data = mock_get_real_time
        mock_get_manager.return_value = self.mock_manager
        
        request_data = {
            "symbols": symbols,
            "asset_class": self.test_asset_class.value,
            "data_type": "real_time"
        }
        
        response = self.client.post("/data/bulk", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == len(symbols)
        for symbol in symbols:
            assert symbol in data
            assert len(data[symbol]) == 1
            assert data[symbol][0]["symbol"] == symbol
            
    @patch('market_data_service.api.get_manager')
    def test_test_provider(self, mock_get_manager):
        """Test provider testing endpoint"""
        provider_name = "yahoo_finance"
        
        # Mock provider with context manager support
        mock_provider = AsyncMock()
        mock_provider.__aenter__ = AsyncMock(return_value=mock_provider)
        mock_provider.__aexit__ = AsyncMock(return_value=None)
        mock_provider.get_real_time_data = AsyncMock(return_value=self.mock_data_point)
        
        self.mock_manager.providers = {provider_name: mock_provider}
        mock_get_manager.return_value = self.mock_manager
        
        response = self.client.post(f"/providers/test/{provider_name}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["provider"] == provider_name
        assert data["success"] is True
        assert "response_time_ms" in data
        assert data["data"]["symbol"] == self.test_symbol
        assert data["data"]["close"] == 154.0
        
    @patch('market_data_service.api.get_manager')
    def test_get_service_metrics(self, mock_get_manager):
        """Test service metrics endpoint"""
        # Mock Kafka producer metrics
        mock_kafka_producer = Mock()
        mock_kafka_producer.get_metrics.return_value = {
            "messages_sent": 1000,
            "messages_failed": 5,
            "avg_latency_ms": 2.5,
            "throughput_per_sec": 500.0
        }
        
        self.mock_manager.kafka_producer = mock_kafka_producer
        self.mock_manager.failure_counts = {
            DataProvider.YAHOO_FINANCE: 2,
            DataProvider.ALPHA_VANTAGE: 0
        }
        self.mock_manager.circuit_breaker_threshold = 5
        self.mock_manager.providers = {"yahoo_finance": Mock(), "alpha_vantage": Mock()}
        
        mock_get_manager.return_value = self.mock_manager
        
        response = self.client.get("/metrics")
        assert response.status_code == 200
        
        data = response.json()
        assert "timestamp" in data
        assert "kafka_producer" in data
        assert "providers" in data
        assert data["kafka_producer"]["messages_sent"] == 1000
        assert data["total_providers_configured"] == 2
        
    def test_invalid_asset_class(self):
        """Test handling of invalid asset class"""
        response = self.client.get("/data/real-time/AAPL?asset_class=INVALID")
        assert response.status_code == 422  # Validation error
        
    def test_missing_required_parameters(self):
        """Test handling of missing required parameters"""
        # Missing asset_class parameter
        response = self.client.get("/data/real-time/AAPL")
        assert response.status_code == 422
        
        # Missing required fields in historical data request
        response = self.client.post("/data/historical", json={"symbol": "AAPL"})
        assert response.status_code == 422
        
    @patch('market_data_service.api.get_manager')
    def test_bulk_data_historical_missing_dates(self, mock_get_manager):
        """Test bulk historical data request without required dates"""
        mock_get_manager.return_value = self.mock_manager
        
        request_data = {
            "symbols": ["AAPL"],
            "asset_class": self.test_asset_class.value,
            "data_type": "historical"
            # Missing start_date and end_date
        }
        
        response = self.client.post("/data/bulk", json=request_data)
        assert response.status_code == 400
        assert "start_date and end_date required" in response.json()["detail"]
        
    @patch('market_data_service.api.get_manager')
    def test_bulk_data_invalid_type(self, mock_get_manager):
        """Test bulk data request with invalid data type"""
        mock_get_manager.return_value = self.mock_manager
        
        request_data = {
            "symbols": ["AAPL"],
            "asset_class": self.test_asset_class.value,
            "data_type": "invalid_type"
        }
        
        response = self.client.post("/data/bulk", json=request_data)
        assert response.status_code == 400
        assert "data_type must be 'real_time' or 'historical'" in response.json()["detail"]

class TestMarketDataAPIPerformance:
    """Performance tests for Market Data Service API"""
    
    def setup_method(self):
        """Set up performance test environment"""
        self.client = TestClient(app)
        
    @pytest.mark.asyncio
    @patch('market_data_service.api.get_manager')
    async def test_concurrent_requests_performance(self, mock_get_manager):
        """Test API performance under concurrent load"""
        mock_manager = Mock(spec=DataFeedManager)
        mock_data_point = MarketDataPoint(
            symbol="AAPL",
            timestamp=datetime.now(),
            open=150.0,
            high=155.0,
            low=149.0,
            close=154.0,
            volume=1000000,
            asset_class=AssetClass.STOCK,
            provider=DataProvider.YAHOO_FINANCE,
            data_type=DataType.REAL_TIME,
            metadata={}
        )
        
        mock_manager.get_real_time_data = AsyncMock(return_value=mock_data_point)
        mock_get_manager.return_value = mock_manager
        
        # Test concurrent requests
        num_requests = 50
        start_time = datetime.now()
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            tasks = [
                ac.get(f"/data/real-time/AAPL?asset_class={AssetClass.STOCK.value}")
                for _ in range(num_requests)
            ]
            
            responses = await asyncio.gather(*tasks)
        
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        # Verify all requests succeeded
        assert all(response.status_code == 200 for response in responses)
        
        # Performance assertions
        avg_response_time = total_time / num_requests
        requests_per_second = num_requests / total_time
        
        logger.info(f"Concurrent requests performance:")
        logger.info(f"  Total requests: {num_requests}")
        logger.info(f"  Total time: {total_time:.3f}s")
        logger.info(f"  Average response time: {avg_response_time:.3f}s")
        logger.info(f"  Requests per second: {requests_per_second:.1f}")
        
        # Performance targets
        assert avg_response_time < 0.1  # Less than 100ms average
        assert requests_per_second > 100  # More than 100 RPS
        
    @pytest.mark.asyncio
    @patch('market_data_service.api.get_manager')
    async def test_bulk_request_performance(self, mock_get_manager):
        """Test bulk request performance"""
        mock_manager = Mock(spec=DataFeedManager)
        
        # Mock bulk data response
        async def mock_get_real_time(symbol, asset_class):
            return MarketDataPoint(
                symbol=symbol,
                timestamp=datetime.now(),
                open=150.0,
                high=155.0,
                low=149.0,
                close=154.0,
                volume=1000000,
                asset_class=asset_class,
                provider=DataProvider.YAHOO_FINANCE,
                data_type=DataType.REAL_TIME,
                metadata={}
            )
        
        mock_manager.get_real_time_data = mock_get_real_time
        mock_get_manager.return_value = mock_manager
        
        # Test bulk request with many symbols
        symbols = [f"SYMBOL{i:03d}" for i in range(100)]
        
        request_data = {
            "symbols": symbols,
            "asset_class": AssetClass.STOCK.value,
            "data_type": "real_time"
        }
        
        start_time = datetime.now()
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post("/data/bulk", json=request_data)
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == len(symbols)
        
        # Performance assertions
        symbols_per_second = len(symbols) / processing_time
        
        logger.info(f"Bulk request performance:")
        logger.info(f"  Symbols processed: {len(symbols)}")
        logger.info(f"  Processing time: {processing_time:.3f}s")
        logger.info(f"  Symbols per second: {symbols_per_second:.1f}")
        
        # Performance targets
        assert processing_time < 5.0  # Less than 5 seconds for 100 symbols
        assert symbols_per_second > 20  # More than 20 symbols per second

class TestMarketDataAPIIntegration:
    """Integration tests for Market Data Service API"""
    
    @pytest.mark.integration
    def test_full_service_lifecycle(self):
        """Test complete service lifecycle"""
        # This would test the actual service startup/shutdown
        # with real dependencies in an integration environment
        pass
        
    @pytest.mark.integration
    def test_real_provider_integration(self):
        """Test integration with real data providers"""
        # This would test actual API calls to real providers
        # in a controlled integration environment
        pass

if __name__ == "__main__":
    # Run the tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x"  # Stop on first failure
    ])