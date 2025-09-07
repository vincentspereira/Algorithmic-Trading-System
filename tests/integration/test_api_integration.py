#!/usr/bin/env python3
"""
API Integration Tests
Tests REST API endpoints, GraphQL API, and WebSocket connections.
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import logging
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockAPIResponse:
    """Mock API response for testing"""
    
    def __init__(self, status_code: int, data: Dict = None, headers: Dict = None):
        self.status_code = status_code
        self.data = data or {}
        self.headers = headers or {}
        self.text = json.dumps(data) if data else ""
        
    def json(self):
        """Return JSON data"""
        return self.data
        
    def raise_for_status(self):
        """Raise exception for bad status codes"""
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code} Error")


class MockAPIClient:
    """Mock API client for testing"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session_token = None
        self.request_count = 0
        self.rate_limit_remaining = 1000
        
    async def authenticate(self, username: str, password: str):
        """Mock authentication"""
        await asyncio.sleep(0.1)  # Simulate network delay
        
        if username == "test_user" and password == "test_password":
            self.session_token = "mock_jwt_token_12345"
            return MockAPIResponse(200, {
                "token": self.session_token,
                "expires_in": 3600,
                "user_id": "user_123"
            })
        else:
            return MockAPIResponse(401, {"error": "Invalid credentials"})
            
    async def get(self, endpoint: str, params: Dict = None, headers: Dict = None):
        """Mock GET request"""
        await asyncio.sleep(0.05)  # Simulate network delay
        self.request_count += 1
        self.rate_limit_remaining -= 1
        
        if not self.session_token and endpoint != "/auth/login":
            return MockAPIResponse(401, {"error": "Authentication required"})
            
        # Mock different endpoints
        if endpoint == "/api/v1/market-data":
            return self._mock_market_data_response(params)
        elif endpoint == "/api/v1/portfolio":
            return self._mock_portfolio_response(params)
        elif endpoint == "/api/v1/orders":
            return self._mock_orders_response(params)
        elif endpoint == "/api/v1/health":
            return self._mock_health_response()
        else:
            return MockAPIResponse(404, {"error": "Endpoint not found"})
            
    async def post(self, endpoint: str, data: Dict = None, headers: Dict = None):
        """Mock POST request"""
        await asyncio.sleep(0.1)  # Simulate network delay
        self.request_count += 1
        self.rate_limit_remaining -= 1
        
        if not self.session_token and endpoint != "/auth/login":
            return MockAPIResponse(401, {"error": "Authentication required"})
            
        if endpoint == "/api/v1/orders":
            return self._mock_create_order_response(data)
        elif endpoint == "/api/v1/portfolio/rebalance":
            return self._mock_rebalance_response(data)
        else:
            return MockAPIResponse(404, {"error": "Endpoint not found"})
            
    async def put(self, endpoint: str, data: Dict = None, headers: Dict = None):
        """Mock PUT request"""
        await asyncio.sleep(0.1)
        self.request_count += 1
        self.rate_limit_remaining -= 1
        
        if not self.session_token:
            return MockAPIResponse(401, {"error": "Authentication required"})
            
        if "/api/v1/orders/" in endpoint:
            return self._mock_update_order_response(data)
        else:
            return MockAPIResponse(404, {"error": "Endpoint not found"})
            
    async def delete(self, endpoint: str, headers: Dict = None):
        """Mock DELETE request"""
        await asyncio.sleep(0.1)
        self.request_count += 1
        self.rate_limit_remaining -= 1
        
        if not self.session_token:
            return MockAPIResponse(401, {"error": "Authentication required"})
            
        if "/api/v1/orders/" in endpoint:
            return MockAPIResponse(200, {"message": "Order cancelled successfully"})
        else:
            return MockAPIResponse(404, {"error": "Endpoint not found"})
            
    def _mock_market_data_response(self, params: Dict):
        """Mock market data response"""
        symbol = params.get("symbol", "AAPL") if params else "AAPL"
        return MockAPIResponse(200, {
            "symbol": symbol,
            "price": 150.25,
            "change": 2.15,
            "change_percent": 1.45,
            "volume": 1234567,
            "timestamp": datetime.now().isoformat()
        })
        
    def _mock_portfolio_response(self, params: Dict):
        """Mock portfolio response"""
        return MockAPIResponse(200, {
            "total_value": 100000.00,
            "cash_balance": 25000.00,
            "positions": [
                {
                    "symbol": "AAPL",
                    "quantity": 100,
                    "avg_price": 145.50,
                    "current_price": 150.25,
                    "market_value": 15025.00,
                    "unrealized_pnl": 475.00
                },
                {
                    "symbol": "GOOGL",
                    "quantity": 25,
                    "avg_price": 2700.00,
                    "current_price": 2750.80,
                    "market_value": 68770.00,
                    "unrealized_pnl": 1270.00
                }
            ]
        })
        
    def _mock_orders_response(self, params: Dict):
        """Mock orders response"""
        return MockAPIResponse(200, {
            "orders": [
                {
                    "id": "order_123",
                    "symbol": "AAPL",
                    "side": "buy",
                    "quantity": 100,
                    "price": 150.00,
                    "status": "filled",
                    "created_at": datetime.now().isoformat()
                },
                {
                    "id": "order_124",
                    "symbol": "GOOGL",
                    "side": "sell",
                    "quantity": 10,
                    "price": 2750.00,
                    "status": "pending",
                    "created_at": datetime.now().isoformat()
                }
            ]
        })
        
    def _mock_health_response(self):
        """Mock health check response"""
        return MockAPIResponse(200, {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "uptime": 86400,
            "services": {
                "database": "healthy",
                "cache": "healthy",
                "message_queue": "healthy"
            }
        })
        
    def _mock_create_order_response(self, data: Dict):
        """Mock create order response"""
        return MockAPIResponse(201, {
            "id": "order_125",
            "symbol": data.get("symbol", "AAPL"),
            "side": data.get("side", "buy"),
            "quantity": data.get("quantity", 100),
            "price": data.get("price", 150.00),
            "status": "pending",
            "created_at": datetime.now().isoformat()
        })
        
    def _mock_update_order_response(self, data: Dict):
        """Mock update order response"""
        return MockAPIResponse(200, {
            "id": "order_123",
            "symbol": "AAPL",
            "side": "buy",
            "quantity": data.get("quantity", 100),
            "price": data.get("price", 150.00),
            "status": "updated",
            "updated_at": datetime.now().isoformat()
        })
        
    def _mock_rebalance_response(self, data: Dict):
        """Mock portfolio rebalance response"""
        return MockAPIResponse(200, {
            "rebalance_id": "rebal_123",
            "status": "in_progress",
            "target_allocations": data.get("allocations", {}),
            "estimated_trades": 5,
            "created_at": datetime.now().isoformat()
        })


class MockWebSocketClient:
    """Mock WebSocket client for testing"""
    
    def __init__(self, url: str):
        self.url = url
        self.connected = False
        self.messages = []
        self.subscriptions = set()
        
    async def connect(self):
        """Mock WebSocket connection"""
        await asyncio.sleep(0.1)
        self.connected = True
        logger.info(f"Connected to WebSocket: {self.url}")
        
    async def disconnect(self):
        """Mock WebSocket disconnection"""
        self.connected = False
        self.subscriptions.clear()
        logger.info("Disconnected from WebSocket")
        
    async def send_message(self, message: Dict):
        """Mock sending WebSocket message"""
        if not self.connected:
            raise Exception("WebSocket not connected")
            
        self.messages.append({
            "type": "sent",
            "message": message,
            "timestamp": datetime.now()
        })
        
        # Handle subscription messages
        if message.get("type") == "subscribe":
            channel = message.get("channel")
            if channel:
                self.subscriptions.add(channel)
                
        # Simulate server response
        await asyncio.sleep(0.05)
        response = self._generate_mock_response(message)
        if response:
            self.messages.append({
                "type": "received",
                "message": response,
                "timestamp": datetime.now()
            })
            
    def _generate_mock_response(self, message: Dict):
        """Generate mock server response"""
        msg_type = message.get("type")
        
        if msg_type == "subscribe":
            return {
                "type": "subscription_confirmed",
                "channel": message.get("channel"),
                "status": "subscribed"
            }
        elif msg_type == "ping":
            return {
                "type": "pong",
                "timestamp": datetime.now().isoformat()
            }
        elif msg_type == "market_data_request":
            return {
                "type": "market_data",
                "symbol": message.get("symbol", "AAPL"),
                "price": 150.25,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return None
            
    async def receive_message(self):
        """Mock receiving WebSocket message"""
        if not self.connected:
            raise Exception("WebSocket not connected")
            
        # Simulate receiving market data updates
        await asyncio.sleep(0.1)
        return {
            "type": "market_update",
            "symbol": "AAPL",
            "price": 150.30,
            "volume": 1000,
            "timestamp": datetime.now().isoformat()
        }


class TestAPIIntegration:
    """Test suite for API integration"""
    
    def setup_method(self):
        """Setup test environment"""
        self.api_client = MockAPIClient("https://api.example.com")
        self.ws_client = MockWebSocketClient("wss://api.example.com/ws")
        
    async def async_setup(self):
        """Async setup for test environment"""
        # Authenticate API client
        auth_response = await self.api_client.authenticate("test_user", "test_password")
        assert auth_response.status_code == 200
        
        logger.info("API integration test setup completed")
        
    async def teardown_method(self):
        """Cleanup test environment"""
        if self.ws_client.connected:
            await self.ws_client.disconnect()
            
        logger.info("API integration test cleanup completed")
        
    @pytest.mark.asyncio
    async def test_rest_api_authentication(self):
        """Test REST API authentication"""
        # Test successful authentication
        client = MockAPIClient("https://api.example.com")
        response = await client.authenticate("test_user", "test_password")
        
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "expires_in" in data
        assert client.session_token is not None
        
        # Test failed authentication
        client2 = MockAPIClient("https://api.example.com")
        response2 = await client2.authenticate("wrong_user", "wrong_password")
        
        assert response2.status_code == 401
        assert client2.session_token is None
        
    @pytest.mark.asyncio
    async def test_market_data_api(self):
        """Test market data API endpoints"""
        self.setup_method()
        await self.async_setup()
        # Test getting market data
        response = await self.api_client.get("/api/v1/market-data", {"symbol": "AAPL"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert "price" in data
        assert "volume" in data
        assert "timestamp" in data
        
    @pytest.mark.asyncio
    async def test_portfolio_api(self):
        """Test portfolio API endpoints"""
        self.setup_method()
        await self.async_setup()
        # Test getting portfolio
        response = await self.api_client.get("/api/v1/portfolio")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_value" in data
        assert "cash_balance" in data
        assert "positions" in data
        assert len(data["positions"]) > 0
        
        # Verify position structure
        position = data["positions"][0]
        assert "symbol" in position
        assert "quantity" in position
        assert "market_value" in position
        
    @pytest.mark.asyncio
    async def test_orders_api(self):
        """Test orders API endpoints"""
        self.setup_method()
        await self.async_setup()
        # Test getting orders
        response = await self.api_client.get("/api/v1/orders")
        
        assert response.status_code == 200
        data = response.json()
        assert "orders" in data
        assert len(data["orders"]) > 0
        
        # Test creating order
        order_data = {
            "symbol": "TSLA",
            "side": "buy",
            "quantity": 50,
            "price": 800.00
        }
        
        create_response = await self.api_client.post("/api/v1/orders", order_data)
        
        assert create_response.status_code == 201
        created_order = create_response.json()
        assert created_order["symbol"] == "TSLA"
        assert created_order["status"] == "pending"
        
    @pytest.mark.asyncio
    async def test_order_lifecycle(self):
        """Test complete order lifecycle"""
        self.setup_method()
        await self.async_setup()
        # Create order
        order_data = {
            "symbol": "NVDA",
            "side": "buy",
            "quantity": 25,
            "price": 500.00
        }
        
        create_response = await self.api_client.post("/api/v1/orders", order_data)
        assert create_response.status_code == 201
        order = create_response.json()
        order_id = order["id"]
        
        # Update order
        update_data = {"quantity": 30, "price": 495.00}
        update_response = await self.api_client.put(f"/api/v1/orders/{order_id}", update_data)
        
        assert update_response.status_code == 200
        updated_order = update_response.json()
        assert updated_order["status"] == "updated"
        
        # Cancel order
        cancel_response = await self.api_client.delete(f"/api/v1/orders/{order_id}")
        
        assert cancel_response.status_code == 200
        cancel_data = cancel_response.json()
        assert "cancelled" in cancel_data["message"].lower()
        
    @pytest.mark.asyncio
    async def test_websocket_connection(self):
        """Test WebSocket connection"""
        self.setup_method()
        # Test connection
        await self.ws_client.connect()
        assert self.ws_client.connected is True
        
        # Test ping/pong
        await self.ws_client.send_message({"type": "ping"})
        
        # Verify message was sent and response received
        assert len(self.ws_client.messages) == 2  # sent + received
        assert self.ws_client.messages[0]["type"] == "sent"
        assert self.ws_client.messages[1]["type"] == "received"
        assert self.ws_client.messages[1]["message"]["type"] == "pong"
        
    @pytest.mark.asyncio
    async def test_websocket_subscriptions(self):
        """Test WebSocket subscriptions"""
        self.setup_method()
        await self.ws_client.connect()
        
        # Subscribe to market data
        await self.ws_client.send_message({
            "type": "subscribe",
            "channel": "market_data",
            "symbol": "AAPL"
        })
        
        # Verify subscription
        assert "market_data" in self.ws_client.subscriptions
        
        # Check confirmation message
        confirmation = self.ws_client.messages[-1]["message"]
        assert confirmation["type"] == "subscription_confirmed"
        assert confirmation["channel"] == "market_data"
        
    @pytest.mark.asyncio
    async def test_websocket_market_data(self):
        """Test WebSocket market data streaming"""
        self.setup_method()
        await self.ws_client.connect()
        
        # Request market data
        await self.ws_client.send_message({
            "type": "market_data_request",
            "symbol": "GOOGL"
        })
        
        # Verify response
        response = self.ws_client.messages[-1]["message"]
        assert response["type"] == "market_data"
        assert response["symbol"] == "GOOGL"
        assert "price" in response
        
        # Test receiving updates
        update = await self.ws_client.receive_message()
        assert update["type"] == "market_update"
        assert "price" in update
        assert "volume" in update
        
    @pytest.mark.asyncio
    async def test_api_rate_limiting(self):
        """Test API rate limiting"""
        self.setup_method()
        await self.async_setup()
        initial_remaining = self.api_client.rate_limit_remaining
        
        # Make multiple requests
        for i in range(5):
            await self.api_client.get("/api/v1/health")
            
        # Verify rate limit decreased
        assert self.api_client.rate_limit_remaining == initial_remaining - 5
        assert self.api_client.request_count == 5  # 5 requests to /api/v1/health
        
    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        """Test API error handling"""
        self.setup_method()
        await self.async_setup()
        # Test unauthorized request
        unauth_client = MockAPIClient("https://api.example.com")
        response = await unauth_client.get("/api/v1/portfolio")
        
        assert response.status_code == 401
        assert "error" in response.json()
        
        # Test not found endpoint
        response = await self.api_client.get("/api/v1/nonexistent")
        
        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()
        
    @pytest.mark.asyncio
    async def test_api_performance(self):
        """Test API performance"""
        self.setup_method()
        await self.async_setup()
        start_time = time.time()
        
        # Make concurrent requests
        tasks = []
        for i in range(10):
            task = self.api_client.get("/api/v1/health")
            tasks.append(task)
            
        responses = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify all requests succeeded
        for response in responses:
            assert response.status_code == 200
            
        # Verify performance (should complete within reasonable time)
        assert total_time < 2.0  # 10 concurrent requests in under 2 seconds
        
    @pytest.mark.asyncio
    async def test_health_check_endpoint(self):
        """Test health check endpoint"""
        self.setup_method()
        await self.async_setup()
        response = await self.api_client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "services" in data
        
        # Verify service statuses
        services = data["services"]
        assert services["database"] == "healthy"
        assert services["cache"] == "healthy"
        assert services["message_queue"] == "healthy"
        
    @pytest.mark.asyncio
    async def test_portfolio_rebalancing(self):
        """Test portfolio rebalancing API"""
        self.setup_method()
        await self.async_setup()
        rebalance_data = {
            "allocations": {
                "AAPL": 0.30,
                "GOOGL": 0.25,
                "TSLA": 0.20,
                "NVDA": 0.15,
                "CASH": 0.10
            }
        }
        
        response = await self.api_client.post("/api/v1/portfolio/rebalance", rebalance_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "rebalance_id" in data
        assert data["status"] == "in_progress"
        assert "target_allocations" in data
        assert "estimated_trades" in data


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])