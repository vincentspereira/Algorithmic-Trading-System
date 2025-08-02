"""
Mock configuration and utilities for integration tests
"""
import asyncio
from unittest.mock import Mock, AsyncMock
import json
from typing import Dict, Any, List


class MockApiClient:
    """Mock API client for testing without real connections"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.responses = {}
        self.call_history = []
    
    def set_response(self, endpoint: str, method: str, response: Dict[str, Any]):
        """Set mock response for an endpoint"""
        key = f"{method.upper()}:{endpoint}"
        self.responses[key] = response
    
    async def request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Mock HTTP request"""
        key = f"{method.upper()}:{endpoint}"
        self.call_history.append({
            'method': method,
            'endpoint': endpoint,
            'kwargs': kwargs
        })
        
        if key in self.responses:
            response = self.responses[key]
            # Simulate network delay
            await asyncio.sleep(0.01)
            return response
        
        # Default responses for common endpoints
        if endpoint == "/auth/login":
            return {
                "access_token": "mock-token-123",
                "user_id": "mock-user-456",
                "expires_in": 3600
            }
        elif endpoint == "/health":
            return {"status": "healthy", "timestamp": "2025-01-01T00:00:00Z"}
        elif endpoint == "/strategies" and method.upper() == "POST":
            return {"strategy_id": "mock-strategy-789", "id": "mock-strategy-789", "status": "created"}
        elif endpoint.startswith("/strategies") and method.upper() == "GET":
            return {"strategies": [{"id": "mock-strategy-789", "status": "active"}]}
        elif endpoint.startswith("/strategies") and "deploy" in endpoint:
            return {"deployment_id": "mock-deploy-123", "status": "deployed"}
        elif endpoint.startswith("/backtesting/run"):
            return {"backtest_id": "mock-backtest-456", "status": "running"}
        elif endpoint.startswith("/backtesting/"):
            return {"backtest_id": "mock-backtest-456", "status": "completed", "results": {"sharpe_ratio": 1.5}}
        elif endpoint == "/orders" and method.upper() == "POST":
            return {"order_id": "mock-order-101", "status": "pending"}
        elif endpoint.startswith("/orders/") and method.upper() == "GET":
            return {"order_id": "mock-order-101", "status": "filled"}
        elif endpoint == "/orders" and method.upper() == "GET":
            return {"orders": [{"id": "mock-order-101", "status": "filled"}]}
        elif endpoint == "/portfolio":
            return {
                "total_value": 100000.0,
                "positions": [
                    {"symbol": "AAPL", "quantity": 100, "value": 15000.0}
                ]
            }
        elif endpoint.startswith("/risk/limits"):
            return {"limits": {"max_position_size": 0.02}, "status": "active"}
        else:
            return {"message": "Mock response", "endpoint": endpoint, "status": "success"}


class MockWebSocketClient:
    """Mock WebSocket client for testing"""
    
    def __init__(self, url: str = "ws://localhost:8000/ws"):
        self.url = url
        self.messages = []
        self.connected = False
    
    async def connect(self):
        """Mock connection"""
        await asyncio.sleep(0.01)
        self.connected = True
    
    async def send(self, message: str):
        """Mock send message"""
        if not self.connected:
            raise ConnectionError("Not connected")
        self.messages.append({"type": "sent", "message": message})
    
    async def receive(self) -> str:
        """Mock receive message"""
        if not self.connected:
            raise ConnectionError("Not connected")
        
        # Return mock market data
        mock_data = {
            "type": "market_data",
            "symbol": "AAPL",
            "price": 150.0,
            "timestamp": "2025-01-01T00:00:00Z"
        }
        return json.dumps(mock_data)
    
    async def close(self):
        """Mock close connection"""
        self.connected = False


class MockDatabaseClient:
    """Mock database client for testing"""
    
    def __init__(self):
        self.data = {}
        self.queries = []
    
    def set_data(self, table: str, data: List[Dict[str, Any]]):
        """Set mock data for a table"""
        self.data[table] = data
    
    async def query(self, sql: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Mock database query"""
        self.queries.append({"sql": sql, "params": params})
        
        # Simple mock responses based on common patterns
        if "SELECT COUNT" in sql.upper():
            return [{"count": len(self.data.get("orders", []))}]
        elif "orders" in sql.lower():
            return self.data.get("orders", [])
        elif "portfolio" in sql.lower():
            return self.data.get("portfolio", [])
        else:
            return []


def setup_mock_environment():
    """Setup mock environment for integration tests"""
    mock_api = MockApiClient()
    mock_ws = MockWebSocketClient()
    mock_db = MockDatabaseClient()
    
    # Setup default mock data
    mock_db.set_data("orders", [
        {"id": 1, "symbol": "AAPL", "quantity": 100, "status": "filled"},
        {"id": 2, "symbol": "GOOGL", "quantity": 50, "status": "pending"}
    ])
    
    mock_db.set_data("portfolio", [
        {"symbol": "AAPL", "quantity": 100, "value": 15000.0},
        {"symbol": "GOOGL", "quantity": 50, "value": 8000.0}
    ])
    
    return {
        "api_client": mock_api,
        "websocket_client": mock_ws,
        "database_client": mock_db
    }


class MockIntegrationTestBase:
    """Base class for mock integration tests"""
    
    def setup_mock_environment_for_test(self):
        """Setup mock environment for tests"""
        self.mocks = setup_mock_environment()
        self.base_url = "http://localhost:8000"
        self.websocket_url = "ws://localhost:8000/ws"
    
    async def authenticate_test_user(self) -> bool:
        """Mock authentication"""
        response = await self.mocks["api_client"].request("POST", "/auth/login")
        return "access_token" in response
    
    async def cleanup_test_data(self):
        """Mock cleanup"""
        pass
    
    async def make_api_request(self, method: str, endpoint: str, data: dict = None):
        """Make API request using mock client"""
        return await self.mocks["api_client"].request(method, endpoint, json=data)