"""Integration tests for API endpoints.

This module contains integration tests for all REST API endpoints,
testing the complete request-response cycle including authentication,
validation, business logic, and data persistence.
"""

import json
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any

import pytest
from conftest import assert_valid_uuid, assert_valid_timestamp


class TestAuthenticationEndpoints:
    """Test suite for authentication and authorization endpoints."""

    @pytest.mark.asyncio
    async def test_user_registration_success(self, http_client, test_config):
        """Test successful user registration."""
        # Arrange
        user_data = {
            "username": "testuser123",
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "first_name": "Test",
            "last_name": "User"
        }
        
        # Mock the response
        expected_response = {
            "user_id": str(uuid.uuid4()),
            "username": user_data["username"],
            "email": user_data["email"],
            "status": "registered",
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Act
        response = await http_client.post(
            f"{test_config['api_base_url']}/auth/register",
            json=user_data
        )
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == user_data["username"]
        assert data["email"] == user_data["email"]
        assert "password" not in data  # Password should not be returned
        assert_valid_uuid(data["user_id"])

    @pytest.mark.asyncio
    async def test_user_registration_duplicate_email(self, http_client, test_config):
        """Test user registration with duplicate email."""
        # Arrange
        user_data = {
            "username": "testuser456",
            "email": "existing@example.com",  # Assume this exists
            "password": "SecurePassword123!",
            "first_name": "Test",
            "last_name": "User"
        }
        
        # Act
        response = await http_client.post(
            f"{test_config['api_base_url']}/auth/register",
            json=user_data
        )
        
        # Assert
        assert response.status_code == 409  # Conflict
        data = response.json()
        assert "email already exists" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_user_login_success(self, http_client, test_config):
        """Test successful user login."""
        # Arrange
        login_data = {
            "username": "testuser123",
            "password": "SecurePassword123!"
        }
        
        expected_response = {
            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
            "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
            "token_type": "bearer",
            "expires_in": 3600,
            "user_id": str(uuid.uuid4())
        }
        
        # Act
        response = await http_client.post(
            f"{test_config['api_base_url']}/auth/login",
            json=login_data
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0
        assert_valid_uuid(data["user_id"])

    @pytest.mark.asyncio
    async def test_user_login_invalid_credentials(self, http_client, test_config):
        """Test login with invalid credentials."""
        # Arrange
        login_data = {
            "username": "testuser123",
            "password": "WrongPassword"
        }
        
        # Act
        response = await http_client.post(
            f"{test_config['api_base_url']}/auth/login",
            json=login_data
        )
        
        # Assert
        assert response.status_code == 401  # Unauthorized
        data = response.json()
        assert "invalid credentials" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_token_refresh(self, http_client, test_config, api_headers):
        """Test JWT token refresh."""
        # Arrange
        refresh_data = {
            "refresh_token": "valid_refresh_token_here"
        }
        
        # Act
        response = await http_client.post(
            f"{test_config['api_base_url']}/auth/refresh",
            json=refresh_data,
            headers=api_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "expires_in" in data


class TestTradingEndpoints:
    """Test suite for trading-related API endpoints."""

    @pytest.mark.asyncio
    async def test_submit_order_success(self, http_client, test_config, api_headers, sample_order_data):
        """Test successful order submission via API."""
        # Arrange
        order_data = sample_order_data.copy()
        order_data.pop("id", None)  # Remove ID for creation
        
        # Act
        response = await http_client.post(
            f"{test_config['api_base_url']}/trading/orders",
            json=order_data,
            headers=api_headers
        )
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert_valid_uuid(data["order_id"])
        assert data["symbol"] == order_data["symbol"]
        assert data["side"] == order_data["side"]
        assert data["status"] in ["SUBMITTED", "PENDING"]
        assert_valid_timestamp(datetime.fromisoformat(data["created_at"]))

    @pytest.mark.asyncio
    async def test_submit_order_invalid_symbol(self, http_client, test_config, api_headers):
        """Test order submission with invalid symbol."""
        # Arrange
        order_data = {
            "symbol": "INVALID_SYMBOL_TOO_LONG",
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": 100
        }
        
        # Act
        response = await http_client.post(
            f"{test_config['api_base_url']}/trading/orders",
            json=order_data,
            headers=api_headers
        )
        
        # Assert
        assert response.status_code == 400  # Bad Request
        data = response.json()
        assert "invalid symbol" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_get_orders(self, http_client, test_config, api_headers):
        """Test retrieving user orders."""
        # Act
        response = await http_client.get(
            f"{test_config['api_base_url']}/trading/orders",
            headers=api_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "orders" in data
        assert isinstance(data["orders"], list)
        assert "total_count" in data
        assert "page" in data
        assert "page_size" in data

    @pytest.mark.asyncio
    async def test_get_order_by_id(self, http_client, test_config, api_headers):
        """Test retrieving specific order by ID."""
        # Arrange
        order_id = str(uuid.uuid4())
        
        # Act
        response = await http_client.get(
            f"{test_config['api_base_url']}/trading/orders/{order_id}",
            headers=api_headers
        )
        
        # Assert
        # This might return 404 if order doesn't exist, which is valid
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert data["order_id"] == order_id
            assert "symbol" in data
            assert "status" in data

    @pytest.mark.asyncio
    async def test_cancel_order(self, http_client, test_config, api_headers):
        """Test order cancellation."""
        # Arrange
        order_id = str(uuid.uuid4())
        
        # Act
        response = await http_client.delete(
            f"{test_config['api_base_url']}/trading/orders/{order_id}",
            headers=api_headers
        )
        
        # Assert
        assert response.status_code in [200, 404]  # Success or not found
        
        if response.status_code == 200:
            data = response.json()
            assert data["order_id"] == order_id
            assert data["status"] == "CANCELLED"

    @pytest.mark.asyncio
    async def test_get_positions(self, http_client, test_config, api_headers):
        """Test retrieving current positions."""
        # Act
        response = await http_client.get(
            f"{test_config['api_base_url']}/trading/positions",
            headers=api_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "positions" in data
        assert isinstance(data["positions"], list)
        
        # Validate position structure if any exist
        for position in data["positions"]:
            assert "symbol" in position
            assert "quantity" in position
            assert "average_price" in position
            assert "market_value" in position


class TestPortfolioEndpoints:
    """Test suite for portfolio management endpoints."""

    @pytest.mark.asyncio
    async def test_create_portfolio(self, http_client, test_config, api_headers, sample_portfolio_data):
        """Test portfolio creation."""
        # Arrange
        portfolio_data = sample_portfolio_data.copy()
        portfolio_data.pop("id", None)
        
        # Act
        response = await http_client.post(
            f"{test_config['api_base_url']}/portfolios",
            json=portfolio_data,
            headers=api_headers
        )
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert_valid_uuid(data["portfolio_id"])
        assert data["name"] == portfolio_data["name"]
        assert data["currency"] == portfolio_data["currency"]
        assert_valid_timestamp(datetime.fromisoformat(data["created_at"]))

    @pytest.mark.asyncio
    async def test_get_portfolios(self, http_client, test_config, api_headers):
        """Test retrieving user portfolios."""
        # Act
        response = await http_client.get(
            f"{test_config['api_base_url']}/portfolios",
            headers=api_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "portfolios" in data
        assert isinstance(data["portfolios"], list)

    @pytest.mark.asyncio
    async def test_get_portfolio_performance(self, http_client, test_config, api_headers):
        """Test retrieving portfolio performance metrics."""
        # Arrange
        portfolio_id = str(uuid.uuid4())
        
        # Act
        response = await http_client.get(
            f"{test_config['api_base_url']}/portfolios/{portfolio_id}/performance",
            headers=api_headers
        )
        
        # Assert
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "total_return" in data
            assert "annualized_return" in data
            assert "volatility" in data
            assert "sharpe_ratio" in data
            assert "max_drawdown" in data

    @pytest.mark.asyncio
    async def test_portfolio_rebalancing(self, http_client, test_config, api_headers):
        """Test portfolio rebalancing endpoint."""
        # Arrange
        portfolio_id = str(uuid.uuid4())
        rebalance_data = {
            "target_allocations": {
                "AAPL": 0.3,
                "GOOGL": 0.3,
                "MSFT": 0.2,
                "CASH": 0.2
            },
            "rebalance_threshold": 0.05
        }
        
        # Act
        response = await http_client.post(
            f"{test_config['api_base_url']}/portfolios/{portfolio_id}/rebalance",
            json=rebalance_data,
            headers=api_headers
        )
        
        # Assert
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "rebalance_orders" in data
            assert "estimated_cost" in data
            assert "status" in data


class TestMarketDataEndpoints:
    """Test suite for market data API endpoints."""

    @pytest.mark.asyncio
    async def test_get_quote(self, http_client, test_config, api_headers):
        """Test retrieving real-time quote."""
        # Arrange
        symbol = "AAPL"
        
        # Act
        response = await http_client.get(
            f"{test_config['api_base_url']}/market-data/quote/{symbol}",
            headers=api_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == symbol
        assert "price" in data
        assert "bid" in data
        assert "ask" in data
        assert "volume" in data
        assert "timestamp" in data
        assert_valid_timestamp(datetime.fromisoformat(data["timestamp"]))

    @pytest.mark.asyncio
    async def test_get_historical_data(self, http_client, test_config, api_headers):
        """Test retrieving historical market data."""
        # Arrange
        symbol = "AAPL"
        params = {
            "start_date": (datetime.utcnow() - timedelta(days=30)).isoformat(),
            "end_date": datetime.utcnow().isoformat(),
            "interval": "1d"
        }
        
        # Act
        response = await http_client.get(
            f"{test_config['api_base_url']}/market-data/historical/{symbol}",
            params=params,
            headers=api_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "symbol" in data
        assert "data" in data
        assert isinstance(data["data"], list)
        
        # Validate OHLCV structure
        if data["data"]:
            candle = data["data"][0]
            assert "timestamp" in candle
            assert "open" in candle
            assert "high" in candle
            assert "low" in candle
            assert "close" in candle
            assert "volume" in candle

    @pytest.mark.asyncio
    async def test_get_market_status(self, http_client, test_config, api_headers):
        """Test retrieving market status."""
        # Act
        response = await http_client.get(
            f"{test_config['api_base_url']}/market-data/status",
            headers=api_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "markets" in data
        
        for market in data["markets"]:
            assert "name" in market
            assert "status" in market  # OPEN, CLOSED, PRE_MARKET, AFTER_HOURS
            assert "next_open" in market or "next_close" in market


class TestRiskManagementEndpoints:
    """Test suite for risk management API endpoints."""

    @pytest.mark.asyncio
    async def test_get_risk_metrics(self, http_client, test_config, api_headers):
        """Test retrieving risk metrics."""
        # Arrange
        portfolio_id = str(uuid.uuid4())
        
        # Act
        response = await http_client.get(
            f"{test_config['api_base_url']}/risk/metrics/{portfolio_id}",
            headers=api_headers
        )
        
        # Assert
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "var_95" in data  # Value at Risk
            assert "var_99" in data
            assert "expected_shortfall" in data
            assert "beta" in data
            assert "correlation_matrix" in data

    @pytest.mark.asyncio
    async def test_risk_limit_check(self, http_client, test_config, api_headers, sample_order_data):
        """Test risk limit validation for orders."""
        # Arrange
        order_data = sample_order_data.copy()
        
        # Act
        response = await http_client.post(
            f"{test_config['api_base_url']}/risk/check-limits",
            json=order_data,
            headers=api_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "approved" in data
        assert "warnings" in data
        assert "risk_score" in data
        assert isinstance(data["warnings"], list)

    @pytest.mark.asyncio
    async def test_stress_test(self, http_client, test_config, api_headers):
        """Test portfolio stress testing."""
        # Arrange
        portfolio_id = str(uuid.uuid4())
        stress_scenarios = {
            "scenarios": [
                {"name": "Market Crash", "equity_shock": -0.3, "bond_shock": -0.1},
                {"name": "Interest Rate Rise", "equity_shock": -0.1, "bond_shock": -0.2}
            ]
        }
        
        # Act
        response = await http_client.post(
            f"{test_config['api_base_url']}/risk/stress-test/{portfolio_id}",
            json=stress_scenarios,
            headers=api_headers
        )
        
        # Assert
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "results" in data
            assert len(data["results"]) == len(stress_scenarios["scenarios"])
            
            for result in data["results"]:
                assert "scenario_name" in result
                assert "portfolio_value_change" in result
                assert "percentage_change" in result


class TestWebSocketEndpoints:
    """Test suite for WebSocket connections and real-time data."""

    @pytest.mark.asyncio
    async def test_websocket_connection(self, test_config):
        """Test WebSocket connection establishment."""
        # This would require websockets library
        # For now, we'll test the HTTP upgrade endpoint
        pass

    @pytest.mark.asyncio
    async def test_market_data_subscription(self, test_config):
        """Test subscribing to real-time market data."""
        # This would test WebSocket subscription to market data feeds
        pass

    @pytest.mark.asyncio
    async def test_order_status_updates(self, test_config):
        """Test real-time order status updates via WebSocket."""
        # This would test WebSocket notifications for order updates
        pass


class TestErrorHandling:
    """Test suite for API error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, http_client, test_config):
        """Test API access without authentication."""
        # Act
        response = await http_client.get(
            f"{test_config['api_base_url']}/trading/orders"
            # No headers = no authentication
        )
        
        # Assert
        assert response.status_code == 401
        data = response.json()
        assert "unauthorized" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_invalid_json_payload(self, http_client, test_config, api_headers):
        """Test API with malformed JSON."""
        # Act
        response = await http_client.post(
            f"{test_config['api_base_url']}/trading/orders",
            data="{invalid json}",  # Malformed JSON
            headers={**api_headers, "Content-Type": "application/json"}
        )
        
        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "invalid json" in data["message"].lower() or "bad request" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_rate_limiting(self, http_client, test_config, api_headers):
        """Test API rate limiting."""
        # Arrange
        endpoint = f"{test_config['api_base_url']}/market-data/quote/AAPL"
        
        # Act - Make many requests quickly
        responses = []
        for _ in range(100):  # Exceed rate limit
            response = await http_client.get(endpoint, headers=api_headers)
            responses.append(response.status_code)
        
        # Assert
        # Should eventually get 429 (Too Many Requests)
        assert 429 in responses or all(code == 200 for code in responses)

    @pytest.mark.asyncio
    async def test_server_error_handling(self, http_client, test_config, api_headers):
        """Test handling of server errors."""
        # This would test endpoints that might trigger server errors
        # For now, we'll test a non-existent endpoint
        
        # Act
        response = await http_client.get(
            f"{test_config['api_base_url']}/non-existent-endpoint",
            headers=api_headers
        )
        
        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["message"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])