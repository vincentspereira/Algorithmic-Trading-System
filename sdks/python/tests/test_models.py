"""
Tests for Nautilus Trader Python SDK Models
"""

import pytest
from datetime import datetime

from nautilus_trader_sdk.models import (
    Order, Position, Trade, Portfolio, MarketData, Strategy, Backtest,
    RiskMetrics, Analytics, OrderSide, OrderType, OrderStatus, TimeInForce,
    PositionSide, StrategyStatus
)

class TestOrder:
    """Test Order model"""
    
    def test_order_creation(self):
        """Test order creation from dict"""
        order_data = {
            'id': 'order-123',
            'symbol': 'AAPL',
            'side': 'buy',
            'quantity': 100,
            'order_type': 'limit',
            'price': 150.25,
            'status': 'pending',
            'created_at': '2025-01-01T12:00:00',
            'filled_quantity': 0,
            'time_in_force': 'DAY'
        }
        
        order = Order.from_dict(order_data)
        
        assert order.id == 'order-123'
        assert order.symbol == 'AAPL'
        assert order.side == OrderSide.BUY
        assert order.quantity == 100
        assert order.order_type == OrderType.LIMIT
        assert order.price == 150.25
        assert order.status == OrderStatus.PENDING
        assert order.filled_quantity == 0
        assert order.time_in_force == TimeInForce.DAY
    
    def test_order_properties(self):
        """Test order properties"""
        order_data = {
            'id': 'order-123',
            'symbol': 'AAPL',
            'side': 'buy',
            'quantity': 100,
            'order_type': 'limit',
            'price': 150.25,
            'status': 'filled',
            'created_at': '2025-01-01T12:00:00',
            'filled_quantity': 100
        }
        
        order = Order.from_dict(order_data)
        
        assert order.is_filled is True
        assert order.is_active is False
        assert order.remaining_quantity == 0
    
    def test_order_to_dict(self):
        """Test order serialization"""
        order_data = {
            'id': 'order-123',
            'symbol': 'AAPL',
            'side': 'buy',
            'quantity': 100,
            'order_type': 'limit',
            'price': 150.25,
            'status': 'pending',
            'created_at': '2025-01-01T12:00:00'
        }
        
        order = Order.from_dict(order_data)
        serialized = order.to_dict()
        
        assert serialized['id'] == 'order-123'
        assert serialized['side'] == 'buy'
        assert serialized['quantity'] == 100

class TestPosition:
    """Test Position model"""
    
    def test_position_creation(self):
        """Test position creation"""
        position_data = {
            'symbol': 'AAPL',
            'quantity': 100,
            'average_price': 150.0,
            'market_price': 155.0,
            'side': 'long',
            'unrealized_pnl': 500.0
        }
        
        position = Position.from_dict(position_data)
        
        assert position.symbol == 'AAPL'
        assert position.quantity == 100
        assert position.side == PositionSide.LONG
        assert position.unrealized_pnl == 500.0
    
    def test_position_properties(self):
        """Test position calculated properties"""
        position_data = {
            'symbol': 'AAPL',
            'quantity': 100,
            'average_price': 150.0,
            'market_price': 155.0,
            'side': 'long',
            'unrealized_pnl': 500.0
        }
        
        position = Position.from_dict(position_data)
        
        assert position.market_value == 15500.0  # 100 * 155.0
        assert position.percentage_change == pytest.approx(3.33, rel=1e-2)
        assert position.is_long is True
        assert position.is_short is False

class TestPortfolio:
    """Test Portfolio model"""
    
    def test_portfolio_creation(self):
        """Test portfolio creation"""
        portfolio_data = {
            'total_value': 100000.0,
            'cash_balance': 50000.0,
            'invested_value': 50000.0,
            'unrealized_pnl': 5000.0,
            'realized_pnl': 2000.0,
            'daily_pnl': 1000.0,
            'positions': [
                {
                    'symbol': 'AAPL',
                    'quantity': 100,
                    'average_price': 150.0,
                    'market_price': 155.0,
                    'side': 'long',
                    'unrealized_pnl': 500.0
                }
            ]
        }
        
        portfolio = Portfolio.from_dict(portfolio_data)
        
        assert portfolio.total_value == 100000.0
        assert portfolio.cash_balance == 50000.0
        assert len(portfolio.positions) == 1
        assert portfolio.positions[0].symbol == 'AAPL'
    
    def test_portfolio_properties(self):
        """Test portfolio calculated properties"""
        portfolio_data = {
            'total_value': 100000.0,
            'cash_balance': 50000.0,
            'invested_value': 50000.0,
            'unrealized_pnl': 5000.0,
            'realized_pnl': 2000.0,
            'daily_pnl': 1000.0,
            'positions': [
                {
                    'symbol': 'AAPL',
                    'quantity': 100,
                    'average_price': 150.0,
                    'market_price': 155.0,
                    'side': 'long',
                    'unrealized_pnl': 500.0
                },
                {
                    'symbol': 'GOOGL',
                    'quantity': -50,
                    'average_price': 2500.0,
                    'market_price': 2450.0,
                    'side': 'short',
                    'unrealized_pnl': 2500.0
                }
            ]
        }
        
        portfolio = Portfolio.from_dict(portfolio_data)
        
        assert portfolio.total_pnl == 7000.0  # 5000 + 2000
        assert portfolio.positions_count == 2
        assert len(portfolio.long_positions) == 1
        assert len(portfolio.short_positions) == 1

class TestMarketData:
    """Test MarketData model"""
    
    def test_market_data_creation(self):
        """Test market data creation"""
        market_data = {
            'symbol': 'AAPL',
            'last_price': 155.0,
            'bid_price': 154.95,
            'ask_price': 155.05,
            'volume': 1000000,
            'change': 5.0,
            'change_percent': 3.33,
            'timestamp': '2025-01-01T12:00:00'
        }
        
        md = MarketData.from_dict(market_data)
        
        assert md.symbol == 'AAPL'
        assert md.last_price == 155.0
        assert md.bid_price == 154.95
        assert md.ask_price == 155.05
        assert md.volume == 1000000
    
    def test_market_data_properties(self):
        """Test market data calculated properties"""
        market_data = {
            'symbol': 'AAPL',
            'last_price': 155.0,
            'bid_price': 154.95,
            'ask_price': 155.05,
            'timestamp': '2025-01-01T12:00:00'
        }
        
        md = MarketData.from_dict(market_data)
        
        assert md.spread == pytest.approx(0.10, rel=1e-6)
        assert md.mid_price == 155.0

class TestAnalytics:
    """Test Analytics model"""
    
    def test_analytics_creation(self):
        """Test analytics creation"""
        analytics_data = {
            'total_trades': 100,
            'winning_trades': 60,
            'losing_trades': 40,
            'win_rate': 60.0,
            'average_win': 250.0,
            'average_loss': -150.0,
            'profit_factor': 1.67,
            'max_consecutive_wins': 8,
            'max_consecutive_losses': 5
        }
        
        analytics = Analytics.from_dict(analytics_data)
        
        assert analytics.total_trades == 100
        assert analytics.winning_trades == 60
        assert analytics.win_rate == 60.0
        assert analytics.profit_factor == 1.67

if __name__ == "__main__":
    pytest.main([__file__, "-v"])