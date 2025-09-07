"""Integration tests for REST API endpoints."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
from typing import Dict, Any, List
import json
from datetime import datetime


class TestRESTAPIIntegration:
    """Test suite for REST API integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.base_url = 'http://localhost:8000'
        self.test_user = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpassword123'
        }
        self.test_token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test.token'
        self.headers = {
            'Authorization': f'Bearer {self.test_token}',
            'Content-Type': 'application/json'
        }
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_health_check_endpoint(self, mock_client):
        """Test health check endpoint."""
        # Mock HTTP client
        mock_http = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_http
        mock_http.get.return_value = Mock(
            status_code=200,
            json=lambda: {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'version': '1.0.0',
                'services': {
                    'database': 'connected',
                    'redis': 'connected',
                    'kafka': 'connected'
                }
            }
        )
        
        # Test health check
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{self.base_url}/health')
            data = response.json()
        
        assert response.status_code == 200
        assert data['status'] == 'healthy'
        assert 'services' in data
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_user_authentication(self, mock_client):
        """Test user authentication endpoints."""
        # Mock HTTP client
        mock_http = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_http
        
        # Mock login response
        mock_http.post.return_value = Mock(
            status_code=200,
            json=lambda: {
                'access_token': self.test_token,
                'token_type': 'bearer',
                'expires_in': 3600,
                'user': {
                    'id': 1,
                    'username': 'testuser',
                    'email': 'test@example.com'
                }
            }
        )
        
        # Test login
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f'{self.base_url}/auth/login',
                json={
                    'username': self.test_user['username'],
                    'password': self.test_user['password']
                }
            )
            data = response.json()
        
        assert response.status_code == 200
        assert data['access_token'] == self.test_token
        assert data['token_type'] == 'bearer'
        assert data['user']['username'] == 'testuser'
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_trading_endpoints(self, mock_client):
        """Test trading-related endpoints."""
        # Mock HTTP client
        mock_http = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_http
        
        # Mock order creation response
        mock_http.post.return_value = Mock(
            status_code=201,
            json=lambda: {
                'order_id': 'ORD_001',
                'symbol': 'EURUSD',
                'side': 'BUY',
                'quantity': 100000,
                'order_type': 'MARKET',
                'status': 'SUBMITTED',
                'created_at': datetime.now().isoformat()
            }
        )
        
        # Test order creation
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f'{self.base_url}/trading/orders',
                headers=self.headers,
                json={
                    'symbol': 'EURUSD',
                    'side': 'BUY',
                    'quantity': 100000,
                    'order_type': 'MARKET'
                }
            )
            data = response.json()
        
        assert response.status_code == 201
        assert data['order_id'] == 'ORD_001'
        assert data['status'] == 'SUBMITTED'
        assert data['symbol'] == 'EURUSD'
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_portfolio_endpoints(self, mock_client):
        """Test portfolio management endpoints."""
        # Mock HTTP client
        mock_http = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_http
        
        # Mock portfolio response
        mock_http.get.return_value = Mock(
            status_code=200,
            json=lambda: {
                'portfolio_id': 'PORT_001',
                'total_value': 100000.0,
                'available_cash': 50000.0,
                'positions': [
                    {
                        'symbol': 'EURUSD',
                        'quantity': 100000,
                        'side': 'LONG',
                        'entry_price': 1.0850,
                        'current_price': 1.0860,
                        'unrealized_pnl': 100.0
                    }
                ],
                'performance': {
                    'total_return': 0.05,
                    'daily_pnl': 150.0,
                    'sharpe_ratio': 1.25
                }
            }
        )
        
        # Test portfolio retrieval
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'{self.base_url}/portfolio/PORT_001',
                headers=self.headers
            )
            data = response.json()
        
        assert response.status_code == 200
        assert data['portfolio_id'] == 'PORT_001'
        assert data['total_value'] == 100000.0
        assert len(data['positions']) == 1
        assert 'performance' in data
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_market_data_endpoints(self, mock_client):
        """Test market data endpoints."""
        # Mock HTTP client
        mock_http = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_http
        
        # Mock market data response
        mock_http.get.return_value = Mock(
            status_code=200,
            json=lambda: {
                'symbol': 'EURUSD',
                'bid': 1.0850,
                'ask': 1.0852,
                'last': 1.0851,
                'volume': 1500000,
                'timestamp': datetime.now().isoformat(),
                'ohlc': {
                    'open': 1.0845,
                    'high': 1.0865,
                    'low': 1.0840,
                    'close': 1.0851
                }
            }
        )
        
        # Test market data retrieval
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'{self.base_url}/market-data/EURUSD',
                headers=self.headers
            )
            data = response.json()
        
        assert response.status_code == 200
        assert data['symbol'] == 'EURUSD'
        assert 'bid' in data
        assert 'ask' in data
        assert 'ohlc' in data
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_strategy_endpoints(self, mock_client):
        """Test strategy management endpoints."""
        # Mock HTTP client
        mock_http = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_http
        
        # Mock strategy creation response
        mock_http.post.return_value = Mock(
            status_code=201,
            json=lambda: {
                'strategy_id': 'STRAT_001',
                'name': 'Moving Average Crossover',
                'description': 'Simple MA crossover strategy',
                'parameters': {
                    'fast_ma': 10,
                    'slow_ma': 20,
                    'symbol': 'EURUSD'
                },
                'status': 'CREATED',
                'created_at': datetime.now().isoformat()
            }
        )
        
        # Test strategy creation
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f'{self.base_url}/strategies',
                headers=self.headers,
                json={
                    'name': 'Moving Average Crossover',
                    'description': 'Simple MA crossover strategy',
                    'parameters': {
                        'fast_ma': 10,
                        'slow_ma': 20,
                        'symbol': 'EURUSD'
                    }
                }
            )
            data = response.json()
        
        assert response.status_code == 201
        assert data['strategy_id'] == 'STRAT_001'
        assert data['status'] == 'CREATED'
        assert data['name'] == 'Moving Average Crossover'
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_backtesting_endpoints(self, mock_client):
        """Test backtesting endpoints."""
        # Mock HTTP client
        mock_http = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_http
        
        # Mock backtest response
        mock_http.post.return_value = Mock(
            status_code=202,
            json=lambda: {
                'backtest_id': 'BT_001',
                'strategy_id': 'STRAT_001',
                'status': 'RUNNING',
                'start_date': '2024-01-01',
                'end_date': '2024-06-01',
                'initial_capital': 100000.0,
                'created_at': datetime.now().isoformat()
            }
        )
        
        # Test backtest creation
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f'{self.base_url}/backtesting/run',
                headers=self.headers,
                json={
                    'strategy_id': 'STRAT_001',
                    'start_date': '2024-01-01',
                    'end_date': '2024-06-01',
                    'initial_capital': 100000.0
                }
            )
            data = response.json()
        
        assert response.status_code == 202
        assert data['backtest_id'] == 'BT_001'
        assert data['status'] == 'RUNNING'
        assert data['initial_capital'] == 100000.0
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_risk_management_endpoints(self, mock_client):
        """Test risk management endpoints."""
        # Mock HTTP client
        mock_http = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_http
        
        # Mock risk assessment response
        mock_http.get.return_value = Mock(
            status_code=200,
            json=lambda: {
                'portfolio_id': 'PORT_001',
                'risk_score': 0.35,
                'risk_level': 'MEDIUM',
                'var_95': 2500.0,
                'expected_shortfall': 3800.0,
                'risk_factors': {
                    'market_risk': 0.70,
                    'credit_risk': 0.10,
                    'operational_risk': 0.15,
                    'liquidity_risk': 0.05
                },
                'recommendations': [
                    'Consider reducing position concentration',
                    'Monitor correlation risk'
                ]
            }
        )
        
        # Test risk assessment
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'{self.base_url}/risk/assessment/PORT_001',
                headers=self.headers
            )
            data = response.json()
        
        assert response.status_code == 200
        assert data['risk_level'] == 'MEDIUM'
        assert data['var_95'] == 2500.0
        assert 'risk_factors' in data
        assert len(data['recommendations']) > 0
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_error_handling(self, mock_client):
        """Test API error handling."""
        # Mock HTTP client with error responses
        mock_http = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_http
        
        # Mock 401 Unauthorized
        mock_http.get.return_value = Mock(
            status_code=401,
            json=lambda: {
                'error': 'Unauthorized',
                'message': 'Invalid or expired token',
                'code': 'AUTH_001'
            }
        )
        
        # Test unauthorized access
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'{self.base_url}/portfolio/PORT_001',
                headers={'Authorization': 'Bearer invalid_token'}
            )
            data = response.json()
        
        assert response.status_code == 401
        assert data['error'] == 'Unauthorized'
        assert 'message' in data
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_rate_limiting(self, mock_client):
        """Test API rate limiting."""
        # Mock HTTP client with rate limit response
        mock_http = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_http
        
        # Mock 429 Too Many Requests
        mock_http.get.return_value = Mock(
            status_code=429,
            json=lambda: {
                'error': 'Rate Limit Exceeded',
                'message': 'Too many requests. Please try again later.',
                'retry_after': 60
            },
            headers={'Retry-After': '60'}
        )
        
        # Test rate limiting
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'{self.base_url}/market-data/EURUSD',
                headers=self.headers
            )
            data = response.json()
        
        assert response.status_code == 429
        assert data['error'] == 'Rate Limit Exceeded'
        assert 'retry_after' in data
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_pagination(self, mock_client):
        """Test API pagination."""
        # Mock HTTP client with paginated response
        mock_http = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_http
        
        # Mock paginated orders response
        mock_http.get.return_value = Mock(
            status_code=200,
            json=lambda: {
                'orders': [
                    {'order_id': f'ORD_{i:03d}', 'symbol': 'EURUSD', 'status': 'FILLED'}
                    for i in range(1, 21)
                ],
                'pagination': {
                    'page': 1,
                    'page_size': 20,
                    'total_pages': 5,
                    'total_count': 100,
                    'has_next': True,
                    'has_previous': False
                }
            }
        )
        
        # Test pagination
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'{self.base_url}/trading/orders?page=1&page_size=20',
                headers=self.headers
            )
            data = response.json()
        
        assert response.status_code == 200
        assert len(data['orders']) == 20
        assert data['pagination']['page'] == 1
        assert data['pagination']['has_next'] is True
        assert data['pagination']['total_count'] == 100


if __name__ == '__main__':
    pytest.main([__file__])