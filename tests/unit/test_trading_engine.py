"""Unit tests for the core trading engine.

Tests cover:
- Order placement and validation
- Risk checks and position management
- Strategy execution and lifecycle
- WebSocket connections and real-time updates
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from decimal import Decimal

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from algorithmic_trading_service.api.main import (
    TradingEngine, OrderSide, OrderType, OrderStatus, TimeInForce,
    OrderRequest, Order, Position, RiskMetrics
)


class TestTradingEngine:
    """Test suite for TradingEngine class."""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Mock database manager."""
        mock = AsyncMock()
        mock.get_account.return_value = {
            'account_id': 'test_account',
            'balance': Decimal('100000.00'),
            'buying_power': Decimal('200000.00')
        }
        return mock
    
    @pytest.fixture
    def mock_order_manager(self):
        """Mock order manager."""
        mock = AsyncMock()
        mock.create_order.return_value = 'order_123'
        mock.get_order.return_value = Order(
            order_id='order_123',
            account_id='test_account',
            symbol='AAPL',
            side=OrderSide.BUY,
            quantity=Decimal('100'),
            order_type=OrderType.LIMIT,
            price=Decimal('150.00'),
            status=OrderStatus.PENDING,
            time_in_force=TimeInForce.DAY,
            created_at=datetime.utcnow()
        )
        return mock
    
    @pytest.fixture
    def mock_risk_manager(self):
        """Mock risk manager."""
        mock = AsyncMock()
        mock.validate_order.return_value = True
        mock.calculate_position_risk.return_value = RiskMetrics(
            position_value=Decimal('15000.00'),
            portfolio_weight=Decimal('0.15'),
            var_1d=Decimal('750.00'),
            max_drawdown=Decimal('0.05')
        )
        return mock
    
    @pytest.fixture
    def trading_engine(self, mock_db_manager, mock_order_manager, mock_risk_manager):
        """Create trading engine with mocked dependencies."""
        engine = TradingEngine()
        engine.db_manager = mock_db_manager
        engine.order_manager = mock_order_manager
        engine.risk_manager = mock_risk_manager
        return engine
    
    @pytest.mark.asyncio
    async def test_place_order_success(self, trading_engine):
        """Test successful order placement."""
        order_request = OrderRequest(
            account_id='test_account',
            symbol='AAPL',
            side=OrderSide.BUY,
            quantity=Decimal('100'),
            order_type=OrderType.LIMIT,
            price=Decimal('150.00'),
            time_in_force=TimeInForce.DAY
        )
        
        result = await trading_engine.place_order(order_request)
        
        assert result['order_id'] == 'order_123'
        assert result['status'] == 'PENDING'
        trading_engine.risk_manager.validate_order.assert_called_once()
        trading_engine.order_manager.create_order.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_place_order_risk_check_failed(self, trading_engine):
        """Test order placement with failed risk check."""
        trading_engine.risk_manager.validate_order.return_value = False
        
        order_request = OrderRequest(
            account_id='test_account',
            symbol='AAPL',
            side=OrderSide.BUY,
            quantity=Decimal('10000'),  # Large quantity
            order_type=OrderType.MARKET
        )
        
        with pytest.raises(ValueError, match="Risk check failed"):
            await trading_engine.place_order(order_request)
    
    @pytest.mark.asyncio
    async def test_cancel_order_success(self, trading_engine):
        """Test successful order cancellation."""
        trading_engine.order_manager.cancel_order.return_value = True
        
        result = await trading_engine.cancel_order('order_123')
        
        assert result['status'] == 'CANCELLED'
        trading_engine.order_manager.cancel_order.assert_called_once_with('order_123')
    
    @pytest.mark.asyncio
    async def test_get_positions(self, trading_engine):
        """Test position retrieval."""
        mock_positions = [
            Position(
                account_id='test_account',
                symbol='AAPL',
                quantity=Decimal('100'),
                average_price=Decimal('149.50'),
                market_value=Decimal('15000.00'),
                unrealized_pnl=Decimal('50.00')
            )
        ]
        trading_engine.db_manager.get_positions.return_value = mock_positions
        
        positions = await trading_engine.get_positions('test_account')
        
        assert len(positions) == 1
        assert positions[0].symbol == 'AAPL'
        assert positions[0].quantity == Decimal('100')
    
    @pytest.mark.asyncio
    async def test_get_orders_with_filters(self, trading_engine):
        """Test order retrieval with filters."""
        mock_orders = [
            Order(
                order_id='order_123',
                account_id='test_account',
                symbol='AAPL',
                side=OrderSide.BUY,
                quantity=Decimal('100'),
                order_type=OrderType.LIMIT,
                price=Decimal('150.00'),
                status=OrderStatus.FILLED,
                time_in_force=TimeInForce.DAY,
                created_at=datetime.utcnow()
            )
        ]
        trading_engine.order_manager.get_orders.return_value = mock_orders
        
        orders = await trading_engine.get_orders(
            account_id='test_account',
            status=OrderStatus.FILLED,
            symbol='AAPL'
        )
        
        assert len(orders) == 1
        assert orders[0].status == OrderStatus.FILLED
        assert orders[0].symbol == 'AAPL'
    
    def test_websocket_connection_manager(self, trading_engine):
        """Test WebSocket connection management."""
        mock_websocket = Mock()
        
        # Test adding connection
        trading_engine.add_websocket_connection('test_account', mock_websocket)
        assert 'test_account' in trading_engine.websocket_connections
        
        # Test removing connection
        trading_engine.remove_websocket_connection('test_account')
        assert 'test_account' not in trading_engine.websocket_connections
    
    @pytest.mark.asyncio
    async def test_broadcast_order_update(self, trading_engine):
        """Test broadcasting order updates via WebSocket."""
        mock_websocket = AsyncMock()
        trading_engine.websocket_connections['test_account'] = mock_websocket
        
        order_update = {
            'order_id': 'order_123',
            'status': 'FILLED',
            'filled_quantity': '100',
            'filled_price': '149.95'
        }
        
        await trading_engine.broadcast_order_update('test_account', order_update)
        
        mock_websocket.send_text.assert_called_once()
        call_args = mock_websocket.send_text.call_args[0][0]
        assert 'order_123' in call_args
        assert 'FILLED' in call_args


class TestOrderValidation:
    """Test suite for order validation logic."""
    
    def test_order_request_validation_success(self):
        """Test valid order request creation."""
        order_request = OrderRequest(
            account_id='test_account',
            symbol='AAPL',
            side=OrderSide.BUY,
            quantity=Decimal('100'),
            order_type=OrderType.LIMIT,
            price=Decimal('150.00')
        )
        
        assert order_request.account_id == 'test_account'
        assert order_request.symbol == 'AAPL'
        assert order_request.side == OrderSide.BUY
        assert order_request.quantity == Decimal('100')
    
    def test_order_request_validation_negative_quantity(self):
        """Test order request with negative quantity."""
        with pytest.raises(ValueError, match="Quantity must be positive"):
            OrderRequest(
                account_id='test_account',
                symbol='AAPL',
                side=OrderSide.BUY,
                quantity=Decimal('-100'),
                order_type=OrderType.MARKET
            )
    
    def test_order_request_validation_missing_price_for_limit(self):
        """Test limit order without price."""
        with pytest.raises(ValueError, match="Price required for LIMIT orders"):
            OrderRequest(
                account_id='test_account',
                symbol='AAPL',
                side=OrderSide.BUY,
                quantity=Decimal('100'),
                order_type=OrderType.LIMIT
            )
    
    def test_order_request_validation_invalid_symbol(self):
        """Test order request with invalid symbol."""
        with pytest.raises(ValueError, match="Invalid symbol format"):
            OrderRequest(
                account_id='test_account',
                symbol='',  # Empty symbol
                side=OrderSide.BUY,
                quantity=Decimal('100'),
                order_type=OrderType.MARKET
            )


class TestRiskMetrics:
    """Test suite for risk metrics calculations."""
    
    def test_risk_metrics_creation(self):
        """Test risk metrics object creation."""
        metrics = RiskMetrics(
            position_value=Decimal('15000.00'),
            portfolio_weight=Decimal('0.15'),
            var_1d=Decimal('750.00'),
            max_drawdown=Decimal('0.05')
        )
        
        assert metrics.position_value == Decimal('15000.00')
        assert metrics.portfolio_weight == Decimal('0.15')
        assert metrics.var_1d == Decimal('750.00')
        assert metrics.max_drawdown == Decimal('0.05')
    
    def test_risk_metrics_validation(self):
        """Test risk metrics validation."""
        with pytest.raises(ValueError, match="Portfolio weight must be between 0 and 1"):
            RiskMetrics(
                position_value=Decimal('15000.00'),
                portfolio_weight=Decimal('1.5'),  # Invalid weight > 1
                var_1d=Decimal('750.00'),
                max_drawdown=Decimal('0.05')
            )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])