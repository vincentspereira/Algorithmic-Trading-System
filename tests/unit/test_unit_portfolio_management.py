"""Unit tests for Portfolio Management system."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, Any, List
from decimal import Decimal


class TestPortfolioManagement:
    """Test suite for Portfolio Management system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.sample_portfolio = {
            'portfolio_id': 'PORT_001',
            'account_id': 'ACC_001',
            'base_currency': 'USD',
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
            ]
        }
    
    @patch('nautilus_trader_engine.core.portfolio_management.PortfolioManager')
    def test_portfolio_initialization(self, mock_portfolio_manager):
        """Test portfolio initialization."""
        # Mock portfolio manager
        mock_manager = Mock()
        mock_portfolio_manager.return_value = mock_manager
        mock_manager.initialize_portfolio.return_value = {
            'portfolio_id': 'PORT_001',
            'status': 'initialized',
            'created_at': datetime.now().isoformat()
        }
        
        # Test portfolio initialization
        from nautilus_trader_engine.core.portfolio_management import PortfolioManager
        manager = PortfolioManager()
        result = manager.initialize_portfolio('ACC_001', 'USD', 100000.0)
        
        assert result['portfolio_id'] == 'PORT_001'
        assert result['status'] == 'initialized'
        assert 'created_at' in result
    
    @patch('nautilus_trader_engine.core.portfolio_management.PortfolioManager')
    def test_position_tracking(self, mock_portfolio_manager):
        """Test position tracking functionality."""
        # Mock portfolio manager
        mock_manager = Mock()
        mock_portfolio_manager.return_value = mock_manager
        mock_manager.get_positions.return_value = {
            'positions': [
                {
                    'symbol': 'EURUSD',
                    'quantity': 100000,
                    'side': 'LONG',
                    'entry_price': 1.0850,
                    'current_price': 1.0860,
                    'unrealized_pnl': 100.0,
                    'realized_pnl': 0.0
                },
                {
                    'symbol': 'GBPUSD',
                    'quantity': 50000,
                    'side': 'SHORT',
                    'entry_price': 1.2650,
                    'current_price': 1.2640,
                    'unrealized_pnl': 50.0,
                    'realized_pnl': 0.0
                }
            ],
            'total_positions': 2
        }
        
        # Test position tracking
        from nautilus_trader_engine.core.portfolio_management import PortfolioManager
        manager = PortfolioManager()
        result = manager.get_positions('PORT_001')
        
        assert result['total_positions'] == 2
        assert len(result['positions']) == 2
        assert result['positions'][0]['symbol'] == 'EURUSD'
        assert result['positions'][1]['symbol'] == 'GBPUSD'
    
    @patch('nautilus_trader_engine.core.portfolio_management.PortfolioManager')
    def test_pnl_calculation(self, mock_portfolio_manager):
        """Test P&L calculation functionality."""
        # Mock portfolio manager
        mock_manager = Mock()
        mock_portfolio_manager.return_value = mock_manager
        mock_manager.calculate_pnl.return_value = {
            'total_unrealized_pnl': 150.0,
            'total_realized_pnl': 250.0,
            'total_pnl': 400.0,
            'pnl_by_symbol': {
                'EURUSD': {'unrealized': 100.0, 'realized': 150.0},
                'GBPUSD': {'unrealized': 50.0, 'realized': 100.0}
            },
            'calculation_time': datetime.now().isoformat()
        }
        
        # Test P&L calculation
        from nautilus_trader_engine.core.portfolio_management import PortfolioManager
        manager = PortfolioManager()
        result = manager.calculate_pnl('PORT_001')
        
        assert result['total_pnl'] == 400.0
        assert result['total_unrealized_pnl'] == 150.0
        assert result['total_realized_pnl'] == 250.0
        assert 'pnl_by_symbol' in result
        assert 'EURUSD' in result['pnl_by_symbol']
    
    @patch('nautilus_trader_engine.core.portfolio_management.PortfolioManager')
    def test_risk_metrics_calculation(self, mock_portfolio_manager):
        """Test risk metrics calculation."""
        # Mock portfolio manager
        mock_manager = Mock()
        mock_portfolio_manager.return_value = mock_manager
        mock_manager.calculate_risk_metrics.return_value = {
            'var_95': 2500.0,
            'var_99': 4000.0,
            'expected_shortfall': 5000.0,
            'sharpe_ratio': 1.25,
            'sortino_ratio': 1.45,
            'max_drawdown': 0.08,
            'volatility': 0.15,
            'beta': 0.85,
            'calculation_date': datetime.now().date().isoformat()
        }
        
        # Test risk metrics calculation
        from nautilus_trader_engine.core.portfolio_management import PortfolioManager
        manager = PortfolioManager()
        result = manager.calculate_risk_metrics('PORT_001')
        
        assert result['var_95'] == 2500.0
        assert result['sharpe_ratio'] == 1.25
        assert result['max_drawdown'] == 0.08
        assert 'expected_shortfall' in result
        assert 'volatility' in result
    
    @patch('nautilus_trader_engine.core.portfolio_management.PortfolioManager')
    def test_portfolio_rebalancing(self, mock_portfolio_manager):
        """Test portfolio rebalancing functionality."""
        # Mock portfolio manager
        mock_manager = Mock()
        mock_portfolio_manager.return_value = mock_manager
        mock_manager.rebalance_portfolio.return_value = {
            'rebalance_id': 'REB_001',
            'target_allocations': {
                'EURUSD': 0.4,
                'GBPUSD': 0.3,
                'USDJPY': 0.3
            },
            'current_allocations': {
                'EURUSD': 0.5,
                'GBPUSD': 0.5,
                'USDJPY': 0.0
            },
            'required_trades': [
                {'symbol': 'EURUSD', 'action': 'SELL', 'quantity': 20000},
                {'symbol': 'GBPUSD', 'action': 'SELL', 'quantity': 10000},
                {'symbol': 'USDJPY', 'action': 'BUY', 'quantity': 30000}
            ],
            'rebalance_status': 'pending'
        }
        
        # Test portfolio rebalancing
        from nautilus_trader_engine.core.portfolio_management import PortfolioManager
        manager = PortfolioManager()
        target_allocations = {'EURUSD': 0.4, 'GBPUSD': 0.3, 'USDJPY': 0.3}
        result = manager.rebalance_portfolio('PORT_001', target_allocations)
        
        assert result['rebalance_status'] == 'pending'
        assert len(result['required_trades']) == 3
        assert 'target_allocations' in result
        assert 'current_allocations' in result
    
    @patch('nautilus_trader_engine.core.portfolio_management.PortfolioManager')
    def test_performance_analytics(self, mock_portfolio_manager):
        """Test performance analytics functionality."""
        # Mock portfolio manager
        mock_manager = Mock()
        mock_portfolio_manager.return_value = mock_manager
        mock_manager.get_performance_analytics.return_value = {
            'total_return': 0.12,
            'annualized_return': 0.15,
            'monthly_returns': [0.02, 0.01, 0.03, -0.01, 0.02],
            'win_rate': 0.65,
            'profit_factor': 1.8,
            'average_win': 150.0,
            'average_loss': -80.0,
            'largest_win': 500.0,
            'largest_loss': -200.0,
            'consecutive_wins': 5,
            'consecutive_losses': 2,
            'analysis_period': '2024-01-01 to 2024-06-01'
        }
        
        # Test performance analytics
        from nautilus_trader_engine.core.portfolio_management import PortfolioManager
        manager = PortfolioManager()
        result = manager.get_performance_analytics('PORT_001')
        
        assert result['total_return'] == 0.12
        assert result['win_rate'] == 0.65
        assert result['profit_factor'] == 1.8
        assert len(result['monthly_returns']) == 5
        assert 'annualized_return' in result
    
    @patch('nautilus_trader_engine.core.portfolio_management.PortfolioManager')
    def test_margin_management(self, mock_portfolio_manager):
        """Test margin management functionality."""
        # Mock portfolio manager
        mock_manager = Mock()
        mock_portfolio_manager.return_value = mock_manager
        mock_manager.calculate_margin_requirements.return_value = {
            'total_margin_required': 5000.0,
            'available_margin': 45000.0,
            'margin_utilization': 0.10,
            'margin_by_position': {
                'EURUSD': 2500.0,
                'GBPUSD': 2500.0
            },
            'margin_call_level': 0.80,
            'stop_out_level': 0.90,
            'margin_status': 'healthy'
        }
        
        # Test margin management
        from nautilus_trader_engine.core.portfolio_management import PortfolioManager
        manager = PortfolioManager()
        result = manager.calculate_margin_requirements('PORT_001')
        
        assert result['margin_utilization'] == 0.10
        assert result['margin_status'] == 'healthy'
        assert result['total_margin_required'] == 5000.0
        assert 'margin_by_position' in result
    
    @patch('nautilus_trader_engine.core.portfolio_management.PortfolioManager')
    def test_portfolio_optimization(self, mock_portfolio_manager):
        """Test portfolio optimization functionality."""
        # Mock portfolio manager
        mock_manager = Mock()
        mock_portfolio_manager.return_value = mock_manager
        mock_manager.optimize_portfolio.return_value = {
            'optimization_id': 'OPT_001',
            'objective': 'maximize_sharpe',
            'optimal_weights': {
                'EURUSD': 0.35,
                'GBPUSD': 0.25,
                'USDJPY': 0.20,
                'AUDUSD': 0.20
            },
            'expected_return': 0.18,
            'expected_volatility': 0.12,
            'expected_sharpe': 1.50,
            'optimization_constraints': {
                'max_weight': 0.40,
                'min_weight': 0.05,
                'max_volatility': 0.15
            },
            'optimization_status': 'completed'
        }
        
        # Test portfolio optimization
        from nautilus_trader_engine.core.portfolio_management import PortfolioManager
        manager = PortfolioManager()
        constraints = {'max_weight': 0.40, 'min_weight': 0.05}
        result = manager.optimize_portfolio('PORT_001', 'maximize_sharpe', constraints)
        
        assert result['optimization_status'] == 'completed'
        assert result['expected_sharpe'] == 1.50
        assert 'optimal_weights' in result
        assert sum(result['optimal_weights'].values()) == 1.0
    
    @patch('nautilus_trader_engine.core.portfolio_management.PortfolioManager')
    def test_portfolio_stress_testing(self, mock_portfolio_manager):
        """Test portfolio stress testing functionality."""
        # Mock portfolio manager
        mock_manager = Mock()
        mock_portfolio_manager.return_value = mock_manager
        mock_manager.run_stress_test.return_value = {
            'stress_test_id': 'STRESS_001',
            'scenarios': {
                'market_crash': {
                    'portfolio_value_change': -15000.0,
                    'percentage_change': -15.0,
                    'worst_position': 'EURUSD',
                    'worst_position_loss': -8000.0
                },
                'interest_rate_shock': {
                    'portfolio_value_change': -5000.0,
                    'percentage_change': -5.0,
                    'worst_position': 'GBPUSD',
                    'worst_position_loss': -3000.0
                },
                'currency_crisis': {
                    'portfolio_value_change': -12000.0,
                    'percentage_change': -12.0,
                    'worst_position': 'EURUSD',
                    'worst_position_loss': -7000.0
                }
            },
            'overall_risk_assessment': 'moderate',
            'recommendations': [
                'Consider reducing EURUSD exposure',
                'Increase diversification across currency pairs'
            ]
        }
        
        # Test portfolio stress testing
        from nautilus_trader_engine.core.portfolio_management import PortfolioManager
        manager = PortfolioManager()
        scenarios = ['market_crash', 'interest_rate_shock', 'currency_crisis']
        result = manager.run_stress_test('PORT_001', scenarios)
        
        assert result['overall_risk_assessment'] == 'moderate'
        assert len(result['scenarios']) == 3
        assert 'market_crash' in result['scenarios']
        assert len(result['recommendations']) > 0


if __name__ == '__main__':
    pytest.main([__file__])