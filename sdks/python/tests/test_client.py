"""
Tests for Nautilus Trader Python SDK Client
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import aiohttp
from datetime import datetime

from nautilus_trader_sdk import NautilusTraderClient
from nautilus_trader_sdk.models import Order, Position, Portfolio, MarketData
from nautilus_trader_sdk.exceptions import APIError, NetworkError, ValidationError

class TestNautilusTraderClient:
    """Test Nautilus Trader Client"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return NautilusTraderClient(
            base_url="http://localhost:8000",
            api_key="test-api-key",
            timeout=10
        )
    
    def test_client_initialization(self, client):
        """Test client initialization"""
        assert client.base_url == "http://localhost:8000"
        assert client.api_key == "test-api-key"
        assert client.timeout == 10
        assert client.max_retries == 3
    
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check"""
        with patch.object(client.rest, '_request') as mock_request:
            mock_request.return_value = {
                'status': 'healthy',
                'timestamp': '2025-01-01T12:00:00Z'
            }
            
            health = await client.health_check()
            
            assert health['status'] == 'healthy'
            mock_request.assert_called_once_with('GET', '/health')
    
    @pytest.mark.asyncio
    async def test_create_order(self, client):
        """Test order creation"""
        with patch.object(client.rest, 'create_order') as mock_create:
            mock_order = Order.from_dict({
                'id': 'order-123',
                'symbol': 'AAPL',
                'side': 'buy',
                'quantity': 100,
                'order_type': 'limit',
                'price': 150.25,
                'status': 'pending',
                'created_at': '2025-01-01T12:00:00Z'
            })
            mock_create.return_value = mock_order
            
            order = await client.create_order(
                symbol="AAPL",
                side="buy",
                quantity=100,
                order_type="limit",
                price=150.25
            )
            
            assert order.id == 'order-123'
            assert order.symbol == 'AAPL'
            assert order.quantity == 100
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_portfolio(self, client):
        """Test get portfolio"""
        with patch.object(client.rest, 'get_portfolio') as mock_get:
            mock_portfolio = Portfolio.from_dict({
                'total_value': 100000.0,
                'cash_balance': 50000.0,
                'invested_value': 50000.0,
                'unrealized_pnl': 5000.0,
                'realized_pnl': 2000.0,
                'daily_pnl': 1000.0,
                'positions': []
            })
            mock_get.return_value = mock_portfolio
            
            portfolio = await client.get_portfolio()
            
            assert portfolio.total_value == 100000.0
            assert portfolio.cash_balance == 50000.0
            mock_get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_websocket_subscription(self, client):
        """Test WebSocket subscription"""
        callback_called = False
        received_order = None
        
        def order_callback(order):
            nonlocal callback_called, received_order
            callback_called = True
            received_order = order
        
        with patch.object(client.websocket, 'subscribe_orders') as mock_subscribe:
            await client.subscribe_orders(order_callback)
            mock_subscribe.assert_called_once_with(order_callback)
    
    @pytest.mark.asyncio
    async def test_graphql_query(self, client):
        """Test GraphQL query"""
        with patch.object(client.graphql, 'query') as mock_query:
            mock_query.return_value = {
                'orders': [
                    {'id': 'order-1', 'symbol': 'AAPL', 'quantity': 100}
                ]
            }
            
            result = await client.graphql_query(
                'query { orders { id symbol quantity } }'
            )
            
            assert 'orders' in result
            assert len(result['orders']) == 1
            mock_query.assert_called_once()
    
    def test_validate_order_params(self, client):
        """Test order parameter validation"""
        # Valid parameters
        assert client.validate_order_params(
            symbol="AAPL",
            side="buy",
            quantity=100,
            order_type="limit",
            price=150.25
        ) is True
        
        # Invalid side
        with pytest.raises(ValidationError):
            client.validate_order_params(
                symbol="AAPL",
                side="invalid",
                quantity=100,
                order_type="limit"
            )
        
        # Invalid quantity
        with pytest.raises(ValidationError):
            client.validate_order_params(
                symbol="AAPL",
                side="buy",
                quantity=-100,
                order_type="limit"
            )
    
    def test_format_symbol(self, client):
        """Test symbol formatting"""
        assert client.format_symbol("aapl") == "AAPL"
        assert client.format_symbol(" GOOGL ") == "GOOGL"
        assert client.format_symbol("MSFT") == "MSFT"
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test client as context manager"""
        async with NautilusTraderClient() as client:
            assert client.session is not None
        
        # Session should be closed after context exit
        assert client._closed is True

class TestClientIntegration:
    """Integration tests for client"""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test complete client workflow"""
        client = NautilusTraderClient(
            base_url="http://localhost:8000",
            api_key="test-key"
        )
        
        # Mock all the underlying methods
        with patch.object(client, 'health_check') as mock_health, \
             patch.object(client, 'create_order') as mock_create_order, \
             patch.object(client, 'get_portfolio') as mock_get_portfolio:
            
            # Setup mocks
            mock_health.return_value = {'status': 'healthy'}
            mock_create_order.return_value = Mock(id='order-123')
            mock_get_portfolio.return_value = Mock(total_value=100000.0)
            
            # Test workflow
            health = await client.health_check()
            assert health['status'] == 'healthy'
            
            order = await client.create_order(
                symbol="AAPL",
                side="buy",
                quantity=100,
                order_type="market"
            )
            assert order.id == 'order-123'
            
            portfolio = await client.get_portfolio()
            assert portfolio.total_value == 100000.0
            
            await client.close()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])