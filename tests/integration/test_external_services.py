#!/usr/bin/env python3
"""
External Services Integration Tests
Tests integration with external APIs, data providers, and third-party services.
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import logging
from typing import Dict, List, Any, Optional
from enum import Enum
import aiohttp
import requests
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ServiceType(Enum):
    """External service types"""
    MARKET_DATA_PROVIDER = "market_data_provider"
    BROKER_API = "broker_api"
    NEWS_FEED = "news_feed"
    RISK_DATA_PROVIDER = "risk_data_provider"
    REGULATORY_REPORTING = "regulatory_reporting"
    CLOUD_STORAGE = "cloud_storage"
    NOTIFICATION_SERVICE = "notification_service"
    AUTHENTICATION_SERVICE = "authentication_service"


@dataclass
class ServiceConfig:
    """External service configuration"""
    service_name: str
    service_type: ServiceType
    base_url: str
    api_key: Optional[str] = None
    timeout: int = 30
    retry_attempts: int = 3
    rate_limit: int = 100  # requests per minute
    enabled: bool = True


class MockMarketDataProvider:
    """Mock market data provider service"""
    
    def __init__(self, config: ServiceConfig):
        self.config = config
        self.connected = False
        self.request_count = 0
        self.last_request_time = None
        self.rate_limit_exceeded = False
        
    async def connect(self) -> Dict[str, Any]:
        """Connect to market data provider"""
        if not self.config.enabled:
            raise Exception("Service is disabled")
            
        # Simulate connection delay
        await asyncio.sleep(0.1)
        
        self.connected = True
        logger.info(f"Connected to {self.config.service_name}")
        
        return {
            "status": "connected",
            "service": self.config.service_name,
            "connection_time": datetime.now().isoformat()
        }
        
    async def disconnect(self):
        """Disconnect from service"""
        self.connected = False
        logger.info(f"Disconnected from {self.config.service_name}")
        
    async def get_market_data(self, symbols: List[str]) -> Dict[str, Any]:
        """Get market data for symbols"""
        if not self.connected:
            raise Exception("Not connected to market data provider")
            
        # Check rate limiting
        current_time = time.time()
        if self.last_request_time and (current_time - self.last_request_time) < 60:
            self.request_count += 1
            if self.request_count > self.config.rate_limit:
                self.rate_limit_exceeded = True
                raise Exception("Rate limit exceeded")
        else:
            self.request_count = 1
            
        self.last_request_time = current_time
        
        # Simulate API delay
        await asyncio.sleep(0.05)
        
        # Generate mock market data
        market_data = {}
        for symbol in symbols:
            market_data[symbol] = {
                "symbol": symbol,
                "price": 100.0 + hash(symbol) % 1000,
                "volume": 10000 + hash(symbol) % 50000,
                "bid": 99.95 + hash(symbol) % 1000,
                "ask": 100.05 + hash(symbol) % 1000,
                "timestamp": datetime.now().isoformat()
            }
            
        return {
            "status": "success",
            "data": market_data,
            "request_id": f"req_{int(time.time())}",
            "timestamp": datetime.now().isoformat()
        }
        
    async def get_historical_data(self, symbol: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get historical market data"""
        if not self.connected:
            raise Exception("Not connected to market data provider")
            
        # Simulate longer processing time for historical data
        await asyncio.sleep(0.2)
        
        # Generate mock historical data
        historical_data = []
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        current = start
        
        while current <= end:
            historical_data.append({
                "date": current.isoformat(),
                "open": 100.0 + (hash(symbol + str(current.day)) % 50),
                "high": 105.0 + (hash(symbol + str(current.day)) % 50),
                "low": 95.0 + (hash(symbol + str(current.day)) % 50),
                "close": 102.0 + (hash(symbol + str(current.day)) % 50),
                "volume": 10000 + (hash(symbol + str(current.day)) % 100000)
            })
            current += timedelta(days=1)
            
        return {
            "status": "success",
            "symbol": symbol,
            "data": historical_data,
            "count": len(historical_data)
        }


class MockBrokerAPI:
    """Mock broker API service"""
    
    def __init__(self, config: ServiceConfig):
        self.config = config
        self.authenticated = False
        self.orders = {}
        self.positions = {}
        self.account_balance = 100000.0
        
    async def authenticate(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Authenticate with broker API"""
        if not self.config.enabled:
            raise Exception("Broker API is disabled")
            
        # Simulate authentication
        await asyncio.sleep(0.1)
        
        if credentials.get("api_key") != self.config.api_key:
            raise Exception("Invalid API key")
            
        self.authenticated = True
        
        return {
            "status": "authenticated",
            "session_token": "mock_session_token_123",
            "expires_at": (datetime.now() + timedelta(hours=8)).isoformat()
        }
        
    async def place_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Place order through broker API"""
        if not self.authenticated:
            raise Exception("Not authenticated with broker")
            
        # Validate order data
        required_fields = ["symbol", "side", "quantity", "order_type"]
        for field in required_fields:
            if field not in order_data:
                raise Exception(f"Missing required field: {field}")
                
        # Generate order ID
        order_id = f"order_{int(time.time())}_{len(self.orders)}"
        
        # Create order
        order = {
            "order_id": order_id,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            **order_data
        }
        
        self.orders[order_id] = order
        
        # Simulate order processing delay
        await asyncio.sleep(0.1)
        
        return {
            "status": "order_placed",
            "order_id": order_id,
            "estimated_execution_time": "2-5 minutes"
        }
        
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status"""
        if not self.authenticated:
            raise Exception("Not authenticated with broker")
            
        if order_id not in self.orders:
            raise Exception(f"Order {order_id} not found")
            
        order = self.orders[order_id]
        
        # Simulate order execution for pending orders
        if order["status"] == "pending":
            # 80% chance of execution
            import random
            if random.random() < 0.8:
                order["status"] = "executed"
                order["executed_at"] = datetime.now().isoformat()
                order["executed_price"] = order.get("price", 100.0) * (0.99 + random.random() * 0.02)
                
        return order
        
    async def get_positions(self) -> Dict[str, Any]:
        """Get current positions"""
        if not self.authenticated:
            raise Exception("Not authenticated with broker")
            
        # Generate mock positions
        mock_positions = {
            "AAPL": {"quantity": 100, "avg_price": 150.0, "market_value": 15000.0},
            "GOOGL": {"quantity": 50, "avg_price": 2800.0, "market_value": 140000.0},
            "TSLA": {"quantity": 25, "avg_price": 800.0, "market_value": 20000.0}
        }
        
        return {
            "status": "success",
            "positions": mock_positions,
            "total_market_value": sum(p["market_value"] for p in mock_positions.values())
        }
        
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        if not self.authenticated:
            raise Exception("Not authenticated with broker")
            
        return {
            "account_id": "mock_account_123",
            "account_type": "margin",
            "cash_balance": self.account_balance,
            "buying_power": self.account_balance * 2,
            "day_trading_buying_power": self.account_balance * 4,
            "maintenance_margin": 25000.0
        }


class MockNewsService:
    """Mock news feed service"""
    
    def __init__(self, config: ServiceConfig):
        self.config = config
        self.connected = False
        
    async def connect(self) -> Dict[str, Any]:
        """Connect to news service"""
        await asyncio.sleep(0.1)
        self.connected = True
        
        return {
            "status": "connected",
            "service": self.config.service_name
        }
        
    async def get_news(self, symbols: List[str] = None, limit: int = 10) -> Dict[str, Any]:
        """Get news articles"""
        if not self.connected:
            raise Exception("Not connected to news service")
            
        # Generate mock news articles
        articles = []
        for i in range(limit):
            symbol = symbols[i % len(symbols)] if symbols else "MARKET"
            articles.append({
                "id": f"news_{i}",
                "headline": f"Breaking: {symbol} shows strong performance in latest quarter",
                "summary": f"Analysis of {symbol} indicates positive market sentiment...",
                "source": "Financial News Network",
                "published_at": (datetime.now() - timedelta(hours=i)).isoformat(),
                "symbols": [symbol] if symbols else [],
                "sentiment": "positive" if i % 3 == 0 else "neutral"
            })
            
        return {
            "status": "success",
            "articles": articles,
            "count": len(articles)
        }


class MockCloudStorage:
    """Mock cloud storage service"""
    
    def __init__(self, config: ServiceConfig):
        self.config = config
        self.storage = {}  # Mock storage
        
    async def upload_file(self, file_path: str, content: bytes) -> Dict[str, Any]:
        """Upload file to cloud storage"""
        # Simulate upload delay
        await asyncio.sleep(0.1)
        
        # Store in mock storage
        self.storage[file_path] = {
            "content": content,
            "uploaded_at": datetime.now().isoformat(),
            "size": len(content)
        }
        
        return {
            "status": "uploaded",
            "file_path": file_path,
            "size": len(content),
            "url": f"https://mock-storage.com/{file_path}"
        }
        
    async def download_file(self, file_path: str) -> Dict[str, Any]:
        """Download file from cloud storage"""
        if file_path not in self.storage:
            raise Exception(f"File {file_path} not found")
            
        # Simulate download delay
        await asyncio.sleep(0.1)
        
        file_data = self.storage[file_path]
        
        return {
            "status": "downloaded",
            "file_path": file_path,
            "content": file_data["content"],
            "size": file_data["size"]
        }
        
    async def list_files(self, prefix: str = "") -> Dict[str, Any]:
        """List files in cloud storage"""
        files = [
            {
                "path": path,
                "size": data["size"],
                "uploaded_at": data["uploaded_at"]
            }
            for path, data in self.storage.items()
            if path.startswith(prefix)
        ]
        
        return {
            "status": "success",
            "files": files,
            "count": len(files)
        }


class TestExternalServices:
    """Test suite for external services integration"""
    
    def setup_method(self):
        """Setup test environment"""
        # Create service configurations
        self.market_data_config = ServiceConfig(
            service_name="AlphaVantage",
            service_type=ServiceType.MARKET_DATA_PROVIDER,
            base_url="https://www.alphavantage.co/query",
            api_key="mock_api_key_123",
            rate_limit=5  # Low limit for testing
        )
        
        self.broker_config = ServiceConfig(
            service_name="InteractiveBrokers",
            service_type=ServiceType.BROKER_API,
            base_url="https://api.interactivebrokers.com",
            api_key="mock_broker_key_456"
        )
        
        self.news_config = ServiceConfig(
            service_name="NewsAPI",
            service_type=ServiceType.NEWS_FEED,
            base_url="https://newsapi.org/v2",
            api_key="mock_news_key_789"
        )
        
        self.storage_config = ServiceConfig(
            service_name="AWS_S3",
            service_type=ServiceType.CLOUD_STORAGE,
            base_url="https://s3.amazonaws.com",
            api_key="mock_aws_key_000"
        )
        
        # Create service instances
        self.market_data_service = MockMarketDataProvider(self.market_data_config)
        self.broker_service = MockBrokerAPI(self.broker_config)
        self.news_service = MockNewsService(self.news_config)
        self.storage_service = MockCloudStorage(self.storage_config)
        
        logger.info("External services test setup completed")
        
    async def teardown_method(self):
        """Cleanup test environment"""
        # Disconnect services
        if hasattr(self, 'market_data_service') and hasattr(self.market_data_service, 'connected') and self.market_data_service.connected:
            await self.market_data_service.disconnect()
            
        logger.info("External services test cleanup completed")
        
    @pytest.mark.asyncio
    async def test_market_data_provider_connection(self):
        """Test market data provider connection"""
        self.setup_method()  # Ensure setup is called
        # Test connection
        result = await self.market_data_service.connect()
        
        assert result["status"] == "connected"
        assert result["service"] == "AlphaVantage"
        assert self.market_data_service.connected is True
        
        # Test disconnection
        await self.market_data_service.disconnect()
        assert self.market_data_service.connected is False
        
    @pytest.mark.asyncio
    async def test_market_data_retrieval(self):
        """Test market data retrieval"""
        self.setup_method()  # Ensure setup is called
        # Connect first
        await self.market_data_service.connect()
        
        # Get market data
        symbols = ["AAPL", "GOOGL", "TSLA"]
        result = await self.market_data_service.get_market_data(symbols)
        
        assert result["status"] == "success"
        assert "data" in result
        assert len(result["data"]) == 3
        
        # Verify data structure
        for symbol in symbols:
            assert symbol in result["data"]
            data = result["data"][symbol]
            assert "price" in data
            assert "volume" in data
            assert "bid" in data
            assert "ask" in data
            
    @pytest.mark.asyncio
    async def test_historical_data_retrieval(self):
        """Test historical data retrieval"""
        self.setup_method()  # Ensure setup is called
        # Connect first
        await self.market_data_service.connect()
        
        # Get historical data
        start_date = "2024-01-01T00:00:00"
        end_date = "2024-01-05T00:00:00"
        
        result = await self.market_data_service.get_historical_data("AAPL", start_date, end_date)
        
        assert result["status"] == "success"
        assert result["symbol"] == "AAPL"
        assert "data" in result
        assert result["count"] == 5  # 5 days of data
        
        # Verify data structure
        for day_data in result["data"]:
            assert "date" in day_data
            assert "open" in day_data
            assert "high" in day_data
            assert "low" in day_data
            assert "close" in day_data
            assert "volume" in day_data
            
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting functionality"""
        self.setup_method()  # Ensure setup is called
        # Connect first
        await self.market_data_service.connect()
        
        # Make requests up to the limit
        symbols = ["AAPL"]
        for i in range(self.market_data_config.rate_limit):
            result = await self.market_data_service.get_market_data(symbols)
            assert result["status"] == "success"
            
        # Next request should fail due to rate limiting
        with pytest.raises(Exception, match="Rate limit exceeded"):
            await self.market_data_service.get_market_data(symbols)
            
    @pytest.mark.asyncio
    async def test_broker_authentication(self):
        """Test broker API authentication"""
        self.setup_method()  # Ensure setup is called
        # Test successful authentication
        credentials = {"api_key": "mock_broker_key_456"}
        result = await self.broker_service.authenticate(credentials)
        
        assert result["status"] == "authenticated"
        assert "session_token" in result
        assert "expires_at" in result
        assert self.broker_service.authenticated is True
        
        # Test failed authentication
        invalid_credentials = {"api_key": "invalid_key"}
        with pytest.raises(Exception, match="Invalid API key"):
            await self.broker_service.authenticate(invalid_credentials)
            
    @pytest.mark.asyncio
    async def test_order_placement_and_tracking(self):
        """Test order placement and tracking"""
        self.setup_method()  # Ensure setup is called
        # Authenticate first
        credentials = {"api_key": "mock_broker_key_456"}
        await self.broker_service.authenticate(credentials)
        
        # Place order
        order_data = {
            "symbol": "AAPL",
            "side": "buy",
            "quantity": 100,
            "order_type": "market"
        }
        
        result = await self.broker_service.place_order(order_data)
        
        assert result["status"] == "order_placed"
        assert "order_id" in result
        
        order_id = result["order_id"]
        
        # Check order status
        status_result = await self.broker_service.get_order_status(order_id)
        
        assert status_result["order_id"] == order_id
        assert status_result["symbol"] == "AAPL"
        assert status_result["status"] in ["pending", "executed"]
        
    @pytest.mark.asyncio
    async def test_account_information_retrieval(self):
        """Test account information retrieval"""
        self.setup_method()  # Ensure setup is called
        # Authenticate first
        credentials = {"api_key": "mock_broker_key_456"}
        await self.broker_service.authenticate(credentials)
        
        # Get positions
        positions_result = await self.broker_service.get_positions()
        
        assert positions_result["status"] == "success"
        assert "positions" in positions_result
        assert "total_market_value" in positions_result
        
        # Get account info
        account_result = await self.broker_service.get_account_info()
        
        assert "account_id" in account_result
        assert "cash_balance" in account_result
        assert "buying_power" in account_result
        
    @pytest.mark.asyncio
    async def test_news_service_integration(self):
        """Test news service integration"""
        self.setup_method()  # Ensure setup is called
        # Connect to news service
        result = await self.news_service.connect()
        assert result["status"] == "connected"
        
        # Get general news
        news_result = await self.news_service.get_news(limit=5)
        
        assert news_result["status"] == "success"
        assert "articles" in news_result
        assert news_result["count"] == 5
        
        # Get symbol-specific news
        symbols = ["AAPL", "GOOGL"]
        symbol_news = await self.news_service.get_news(symbols=symbols, limit=4)
        
        assert symbol_news["status"] == "success"
        assert len(symbol_news["articles"]) == 4
        
        # Verify article structure
        for article in symbol_news["articles"]:
            assert "id" in article
            assert "headline" in article
            assert "summary" in article
            assert "published_at" in article
            assert "sentiment" in article
            
    @pytest.mark.asyncio
    async def test_cloud_storage_operations(self):
        """Test cloud storage operations"""
        self.setup_method()  # Ensure setup is called
        # Upload file
        file_content = b"This is test trading data content"
        file_path = "trading_data/test_file.csv"
        
        upload_result = await self.storage_service.upload_file(file_path, file_content)
        
        assert upload_result["status"] == "uploaded"
        assert upload_result["file_path"] == file_path
        assert upload_result["size"] == len(file_content)
        
        # Download file
        download_result = await self.storage_service.download_file(file_path)
        
        assert download_result["status"] == "downloaded"
        assert download_result["content"] == file_content
        
        # List files
        list_result = await self.storage_service.list_files("trading_data/")
        
        assert list_result["status"] == "success"
        assert list_result["count"] == 1
        assert list_result["files"][0]["path"] == file_path
        
    @pytest.mark.asyncio
    async def test_service_error_handling(self):
        """Test service error handling"""
        self.setup_method()  # Ensure setup is called
        # Test disabled service
        self.market_data_config.enabled = False
        disabled_service = MockMarketDataProvider(self.market_data_config)
        
        with pytest.raises(Exception, match="Service is disabled"):
            await disabled_service.connect()
            
        # Test unauthenticated broker operations
        unauthenticated_broker = MockBrokerAPI(self.broker_config)
        
        with pytest.raises(Exception, match="Not authenticated"):
            await unauthenticated_broker.get_positions()
            
        # Test missing file in storage
        with pytest.raises(Exception, match="File .* not found"):
            await self.storage_service.download_file("nonexistent_file.txt")
            
    @pytest.mark.asyncio
    async def test_concurrent_service_operations(self):
        """Test concurrent operations across multiple services"""
        self.setup_method()  # Ensure setup is called
        # Setup services
        await self.market_data_service.connect()
        await self.news_service.connect()
        
        credentials = {"api_key": "mock_broker_key_456"}
        await self.broker_service.authenticate(credentials)
        
        # Create concurrent tasks
        tasks = [
            self.market_data_service.get_market_data(["AAPL", "GOOGL"]),
            self.news_service.get_news(["AAPL"], limit=3),
            self.broker_service.get_positions(),
            self.storage_service.upload_file("concurrent_test.txt", b"test data")
        ]
        
        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all operations completed successfully
        assert len(results) == 4
        for result in results:
            assert not isinstance(result, Exception)
            assert result["status"] in ["success", "uploaded"]
            
    @pytest.mark.asyncio
    async def test_service_performance_monitoring(self):
        """Test service performance monitoring"""
        self.setup_method()  # Ensure setup is called
        # Connect to market data service
        await self.market_data_service.connect()
        
        # Measure response times
        start_time = time.time()
        
        # Make multiple requests
        symbols = ["AAPL", "GOOGL", "TSLA", "NVDA", "MSFT"]
        tasks = []
        
        for symbol in symbols:
            task = self.market_data_service.get_market_data([symbol])
            tasks.append(task)
            
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify performance
        assert len(results) == 5
        assert all(r["status"] == "success" for r in results)
        assert total_time < 2.0  # Should complete within 2 seconds
        
        # Check request tracking
        assert self.market_data_service.request_count == 5
        
    @pytest.mark.asyncio
    async def test_service_retry_mechanism(self):
        """Test service retry mechanism"""
        self.setup_method()  # Ensure setup is called
        # Create a service that fails initially
        failing_service = MockMarketDataProvider(self.market_data_config)
        failing_service.connected = True
        
        # Mock temporary failure
        original_method = failing_service.get_market_data
        call_count = 0
        
        async def failing_get_market_data(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # Fail first 2 attempts
                raise Exception("Temporary service unavailable")
            return await original_method(*args, **kwargs)
            
        failing_service.get_market_data = failing_get_market_data
        
        # Implement retry logic
        max_retries = 3
        retry_delay = 0.1
        
        for attempt in range(max_retries):
            try:
                result = await failing_service.get_market_data(["AAPL"])
                assert result["status"] == "success"
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                await asyncio.sleep(retry_delay)
                
        # Verify it succeeded on the third attempt
        assert call_count == 3


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])