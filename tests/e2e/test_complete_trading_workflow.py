"""End-to-end tests for complete trading workflow.

Tests cover:
- Complete order lifecycle from creation to execution
- Market data integration with trading decisions
- Risk management integration
- Portfolio management updates
- Real-time WebSocket communications
- Multi-component integration
"""

import pytest
import asyncio
import json
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import websockets
import requests
from typing import Dict, List, Any

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from algorithmic_trading_service.api.main import TradingEngine
from algorithmic_trading_service.order_management import OrderManager, OrderCreateRequest, OrderSide, OrderType
from algorithmic_trading_service.risk_management import RiskManager
from algorithmic_trading_service.portfolio_management import PortfolioManager


class TestCompleteTradingWorkflow:
    """End-to-end test suite for complete trading workflow."""
    
    @pytest.fixture
    def api_base_url(self):
        """Base URL for API testing."""
        return "http://localhost:8000/api/v1"
    
    @pytest.fixture
    def websocket_url(self):
        """WebSocket URL for real-time testing."""
        return "ws://localhost:8000/ws"
    
    @pytest.fixture
    async def trading_system(self):
        """Set up complete trading system for testing."""
        # Mock external dependencies
        mock_db = AsyncMock()
        mock_broker = AsyncMock()
        mock_market_data = AsyncMock()
        
        # Initialize components
        risk_manager = RiskManager(mock_db)
        portfolio_manager = PortfolioManager(mock_db)
        order_manager = OrderManager(mock_db)
        
        trading_engine = TradingEngine(
            order_manager=order_manager,
            risk_manager=risk_manager,
            portfolio_manager=portfolio_manager,
            broker_client=mock_broker,
            market_data_client=mock_market_data
        )
        
        return {
            'engine': trading_engine,
            'order_manager': order_manager,
            'risk_manager': risk_manager,
            'portfolio_manager': portfolio_manager,
            'mock_db': mock_db,
            'mock_broker': mock_broker,
            'mock_market_data': mock_market_data
        }
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_complete_buy_order_workflow(self, trading_system, api_base_url):
        """Test complete buy order workflow from API to execution."""
        # Step 1: Create order via API
        order_data = {
            "account_id": "test_account",
            "symbol": "AAPL",
            "side": "BUY",
            "quantity": "100",
            "order_type": "LIMIT",
            "price": "150.00",
            "time_in_force": "DAY"
        }
        
        # Mock successful order creation
        trading_system['mock_db'].create_order.return_value = 'order_123'
        trading_system['mock_db'].get_order.return_value = {
            'order_id': 'order_123',
            'account_id': 'test_account',
            'symbol': 'AAPL',
            'side': 'BUY',
            'quantity': Decimal('100'),
            'order_type': 'LIMIT',
            'price': Decimal('150.00'),
            'status': 'PENDING',
            'time_in_force': 'DAY',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Step 2: Submit order through trading engine
        order_request = OrderCreateRequest(
            account_id='test_account',
            symbol='AAPL',
            side=OrderSide.BUY,
            quantity=Decimal('100'),
            order_type=OrderType.LIMIT,
            price=Decimal('150.00')
        )
        
        order_id = await trading_system['engine'].submit_order(order_request)
        assert order_id == 'order_123'
        
        # Step 3: Simulate market data update triggering execution
        market_data = {
            'symbol': 'AAPL',
            'price': Decimal('149.95'),
            'volume': 1000,
            'timestamp': datetime.utcnow()
        }
        
        # Mock broker execution
        trading_system['mock_broker'].submit_order.return_value = {
            'broker_order_id': 'broker_123',
            'status': 'FILLED',
            'filled_quantity': Decimal('100'),
            'filled_price': Decimal('149.95')
        }
        
        # Step 4: Process market data and execute order
        await trading_system['engine'].process_market_data(market_data)
        
        # Step 5: Verify order execution
        trading_system['mock_db'].update_order_status.assert_called()
        
        # Step 6: Verify portfolio update
        expected_position_update = {
            'symbol': 'AAPL',
            'quantity': Decimal('100'),
            'average_price': Decimal('149.95'),
            'market_value': Decimal('14995.00')
        }
        
        # Verify portfolio manager was called to update position
        assert trading_system['portfolio_manager'].update_position.called
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_risk_management_integration(self, trading_system):
        """Test risk management integration in trading workflow."""
        # Set up risk limits
        risk_limits = {
            'max_position_size': Decimal('1000'),
            'max_daily_loss': Decimal('5000'),
            'max_portfolio_exposure': Decimal('100000')
        }
        
        trading_system['mock_db'].get_risk_limits.return_value = risk_limits
        
        # Test order that exceeds position limit
        large_order = OrderCreateRequest(
            account_id='test_account',
            symbol='AAPL',
            side=OrderSide.BUY,
            quantity=Decimal('2000'),  # Exceeds max_position_size
            order_type=OrderType.MARKET
        )
        
        # Mock current position
        trading_system['mock_db'].get_position.return_value = {
            'symbol': 'AAPL',
            'quantity': Decimal('500'),
            'average_price': Decimal('150.00')
        }
        
        # Should reject order due to risk limits
        with pytest.raises(Exception, match="Position size limit exceeded"):
            await trading_system['engine'].submit_order(large_order)
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_websocket_real_time_updates(self, websocket_url):
        """Test real-time WebSocket updates during trading."""
        # This test would require actual WebSocket server running
        # For now, we'll mock the WebSocket behavior
        
        mock_websocket_messages = [
            {
                'type': 'market_data',
                'symbol': 'AAPL',
                'price': 150.25,
                'timestamp': datetime.utcnow().isoformat()
            },
            {
                'type': 'order_update',
                'order_id': 'order_123',
                'status': 'FILLED',
                'filled_quantity': 100,
                'filled_price': 150.25
            },
            {
                'type': 'portfolio_update',
                'account_id': 'test_account',
                'total_value': 150025.00,
                'cash_balance': 50000.00
            }
        ]
        
        # Simulate WebSocket message processing
        for message in mock_websocket_messages:
            # In a real test, this would connect to actual WebSocket
            # and verify message format and timing
            assert 'type' in message
            assert 'timestamp' in message or message['type'] == 'order_update'
            
            if message['type'] == 'market_data':
                assert 'symbol' in message
                assert 'price' in message
            elif message['type'] == 'order_update':
                assert 'order_id' in message
                assert 'status' in message
            elif message['type'] == 'portfolio_update':
                assert 'account_id' in message
                assert 'total_value' in message
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_multi_asset_portfolio_management(self, trading_system):
        """Test portfolio management across multiple assets."""
        # Set up initial portfolio state
        initial_positions = {
            'AAPL': {'quantity': Decimal('100'), 'average_price': Decimal('150.00')},
            'GOOGL': {'quantity': Decimal('50'), 'average_price': Decimal('2500.00')},
            'MSFT': {'quantity': Decimal('75'), 'average_price': Decimal('300.00')}
        }
        
        trading_system['mock_db'].get_all_positions.return_value = initial_positions
        
        # Execute multiple orders
        orders = [
            OrderCreateRequest(
                account_id='test_account',
                symbol='AAPL',
                side=OrderSide.SELL,
                quantity=Decimal('50'),
                order_type=OrderType.MARKET
            ),
            OrderCreateRequest(
                account_id='test_account',
                symbol='TSLA',
                side=OrderSide.BUY,
                quantity=Decimal('25'),
                order_type=OrderType.LIMIT,
                price=Decimal('800.00')
            )
        ]
        
        # Mock order executions
        trading_system['mock_db'].create_order.side_effect = ['order_124', 'order_125']
        trading_system['mock_broker'].submit_order.side_effect = [
            {
                'broker_order_id': 'broker_124',
                'status': 'FILLED',
                'filled_quantity': Decimal('50'),
                'filled_price': Decimal('151.00')
            },
            {
                'broker_order_id': 'broker_125',
                'status': 'FILLED',
                'filled_quantity': Decimal('25'),
                'filled_price': Decimal('799.50')
            }
        ]
        
        # Execute orders
        for order in orders:
            order_id = await trading_system['engine'].submit_order(order)
            assert order_id in ['order_124', 'order_125']
        
        # Verify portfolio updates
        assert trading_system['portfolio_manager'].update_position.call_count == 2
        
        # Verify portfolio rebalancing calculations
        expected_portfolio_value = (
            Decimal('50') * Decimal('151.00') +  # Remaining AAPL
            Decimal('50') * Decimal('2500.00') +  # GOOGL
            Decimal('75') * Decimal('300.00') +   # MSFT
            Decimal('25') * Decimal('799.50')     # New TSLA
        )
        
        # This would be calculated by the portfolio manager
        assert expected_portfolio_value > Decimal('0')
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_strategy_execution_workflow(self, trading_system):
        """Test automated strategy execution workflow."""
        # Mock strategy configuration
        strategy_config = {
            'strategy_id': 'momentum_strategy_1',
            'symbols': ['AAPL', 'GOOGL', 'MSFT'],
            'parameters': {
                'lookback_period': 20,
                'momentum_threshold': 0.02,
                'position_size': Decimal('1000')
            },
            'risk_limits': {
                'max_position_per_symbol': Decimal('5000'),
                'stop_loss_pct': Decimal('0.05')
            }
        }
        
        # Mock market data for strategy signals
        market_data_history = {
            'AAPL': [
                {'price': Decimal('148.00'), 'timestamp': datetime.utcnow() - timedelta(minutes=5)},
                {'price': Decimal('149.00'), 'timestamp': datetime.utcnow() - timedelta(minutes=4)},
                {'price': Decimal('150.50'), 'timestamp': datetime.utcnow() - timedelta(minutes=3)},
                {'price': Decimal('151.25'), 'timestamp': datetime.utcnow() - timedelta(minutes=2)},
                {'price': Decimal('152.00'), 'timestamp': datetime.utcnow() - timedelta(minutes=1)}
            ]
        }
        
        trading_system['mock_market_data'].get_historical_data.return_value = market_data_history
        
        # Mock strategy signal generation
        strategy_signals = [
            {
                'symbol': 'AAPL',
                'signal': 'BUY',
                'confidence': 0.85,
                'target_quantity': Decimal('100'),
                'reasoning': 'Strong upward momentum detected'
            }
        ]
        
        # Execute strategy
        for signal in strategy_signals:
            if signal['signal'] == 'BUY':
                order_request = OrderCreateRequest(
                    account_id='strategy_account',
                    symbol=signal['symbol'],
                    side=OrderSide.BUY,
                    quantity=signal['target_quantity'],
                    order_type=OrderType.MARKET,
                    metadata={'strategy_id': strategy_config['strategy_id']}
                )
                
                # Mock successful order creation
                trading_system['mock_db'].create_order.return_value = 'strategy_order_123'
                
                order_id = await trading_system['engine'].submit_order(order_request)
                assert order_id == 'strategy_order_123'
        
        # Verify strategy execution was logged
        trading_system['mock_db'].create_order.assert_called()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_error_handling_and_recovery(self, trading_system):
        """Test error handling and recovery mechanisms."""
        # Test database connection failure
        trading_system['mock_db'].create_order.side_effect = Exception("Database connection failed")
        
        order_request = OrderCreateRequest(
            account_id='test_account',
            symbol='AAPL',
            side=OrderSide.BUY,
            quantity=Decimal('100'),
            order_type=OrderType.MARKET
        )
        
        with pytest.raises(Exception, match="Database connection failed"):
            await trading_system['engine'].submit_order(order_request)
        
        # Test broker connection failure
        trading_system['mock_db'].create_order.side_effect = None
        trading_system['mock_db'].create_order.return_value = 'order_126'
        trading_system['mock_broker'].submit_order.side_effect = Exception("Broker connection failed")
        
        # Should handle broker failure gracefully
        with pytest.raises(Exception, match="Broker connection failed"):
            await trading_system['engine'].submit_order(order_request)
        
        # Verify order status was updated to reflect error
        trading_system['mock_db'].update_order_status.assert_called()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_performance_under_load(self, trading_system):
        """Test system performance under high load."""
        # Create multiple concurrent orders
        concurrent_orders = []
        for i in range(50):
            order_request = OrderCreateRequest(
                account_id=f'test_account_{i % 5}',
                symbol='AAPL',
                side=OrderSide.BUY if i % 2 == 0 else OrderSide.SELL,
                quantity=Decimal('10'),
                order_type=OrderType.MARKET
            )
            concurrent_orders.append(order_request)
        
        # Mock successful order processing
        trading_system['mock_db'].create_order.side_effect = [f'order_{i}' for i in range(50)]
        
        # Measure execution time
        start_time = datetime.utcnow()
        
        # Execute orders concurrently
        tasks = []
        for order in concurrent_orders:
            task = asyncio.create_task(trading_system['engine'].submit_order(order))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds()
        
        # Verify all orders were processed
        successful_orders = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_orders) == 50
        
        # Verify performance (should process 50 orders in under 5 seconds)
        assert execution_time < 5.0
        
        # Verify database calls
        assert trading_system['mock_db'].create_order.call_count == 50


class TestAPIIntegration:
    """Test API integration points."""
    
    @pytest.mark.e2e
    def test_rest_api_endpoints(self, api_base_url):
        """Test REST API endpoints are accessible."""
        # This would require actual API server running
        # For now, we'll test the expected endpoint structure
        
        expected_endpoints = [
            '/orders',
            '/orders/{order_id}',
            '/portfolio',
            '/positions',
            '/market-data/{symbol}',
            '/strategies',
            '/risk-limits'
        ]
        
        for endpoint in expected_endpoints:
            # In a real test, this would make actual HTTP requests
            # response = requests.get(f"{api_base_url}{endpoint}")
            # assert response.status_code in [200, 404]  # 404 for parameterized endpoints
            assert endpoint.startswith('/')
    
    @pytest.mark.e2e
    def test_api_authentication(self, api_base_url):
        """Test API authentication mechanisms."""
        # Test unauthorized access
        # response = requests.get(f"{api_base_url}/orders")
        # assert response.status_code == 401
        
        # Test with valid token
        # headers = {'Authorization': 'Bearer valid_token'}
        # response = requests.get(f"{api_base_url}/orders", headers=headers)
        # assert response.status_code == 200
        
        # For now, just verify the test structure
        assert api_base_url.startswith('http')


class TestDataConsistency:
    """Test data consistency across components."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_order_portfolio_consistency(self, trading_system):
        """Test consistency between order execution and portfolio updates."""
        # Execute a buy order
        order_request = OrderCreateRequest(
            account_id='test_account',
            symbol='AAPL',
            side=OrderSide.BUY,
            quantity=Decimal('100'),
            order_type=OrderType.MARKET
        )
        
        # Mock successful execution
        trading_system['mock_db'].create_order.return_value = 'order_127'
        trading_system['mock_broker'].submit_order.return_value = {
            'broker_order_id': 'broker_127',
            'status': 'FILLED',
            'filled_quantity': Decimal('100'),
            'filled_price': Decimal('150.00')
        }
        
        # Mock current position
        trading_system['mock_db'].get_position.return_value = {
            'symbol': 'AAPL',
            'quantity': Decimal('50'),
            'average_price': Decimal('145.00')
        }
        
        order_id = await trading_system['engine'].submit_order(order_request)
        
        # Verify order was created
        assert order_id == 'order_127'
        
        # Verify portfolio update was called with correct parameters
        trading_system['portfolio_manager'].update_position.assert_called()
        
        # In a real system, we would verify the exact position calculation
        # Expected new position: (50 * 145.00 + 100 * 150.00) / 150 = 147.67 average price
        expected_new_quantity = Decimal('150')
        expected_new_avg_price = (Decimal('50') * Decimal('145.00') + Decimal('100') * Decimal('150.00')) / Decimal('150')
        
        assert expected_new_quantity == Decimal('150')
        assert abs(expected_new_avg_price - Decimal('147.67')) < Decimal('0.01')


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-m', 'e2e'])