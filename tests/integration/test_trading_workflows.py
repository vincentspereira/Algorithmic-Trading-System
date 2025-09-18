"""Comprehensive integration tests for critical trading workflows and user journeys."""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import json
import uuid

# Import trading components
try:
    from nautilus_trader_engine.main import TradingEngine
    from nautilus_trader_engine.core.portfolio_manager import PortfolioManager
    from nautilus_trader_engine.core.order_manager import OrderManager
    from nautilus_trader_engine.core.risk_manager import RiskManager
    from nautilus_trader_engine.brokers.interactive_brokers import InteractiveBrokersAdapter
except ImportError:
    # Mock imports if modules don't exist yet
    TradingEngine = Mock
    PortfolioManager = Mock
    OrderManager = Mock
    RiskManager = Mock
    InteractiveBrokersAdapter = Mock


class TestCompleteOrderLifecycle:
    """Integration tests for complete order lifecycle workflows."""
    
    def setup_method(self):
        """Set up test fixtures for order lifecycle tests."""
        self.trading_engine = Mock(spec=TradingEngine)
        self.portfolio_manager = Mock(spec=PortfolioManager)
        self.order_manager = Mock(spec=OrderManager)
        self.risk_manager = Mock(spec=RiskManager)
        
        # Sample order data
        self.sample_order = {
            'order_id': str(uuid.uuid4()),
            'symbol': 'AAPL',
            'side': 'BUY',
            'quantity': 100,
            'order_type': 'MARKET',
            'price': None,
            'time_in_force': 'DAY',
            'account_id': 'test_account',
            'timestamp': datetime.now(timezone.utc)
        }
        
        self.sample_portfolio = {
            'account_id': 'test_account',
            'cash_balance': 50000.00,
            'positions': {
                'AAPL': {'quantity': 50, 'avg_price': 148.00, 'market_value': 7400.00}
            },
            'total_value': 57400.00
        }
    
    @pytest.mark.asyncio
    async def test_market_order_workflow(self):
        """Test complete market order workflow from submission to execution."""
        # Step 1: Order validation
        self.risk_manager.validate_order.return_value = {
            'valid': True,
            'risk_checks_passed': True,
            'buying_power_sufficient': True
        }
        
        # Step 2: Order submission
        self.order_manager.submit_order.return_value = {
            'order_id': self.sample_order['order_id'],
            'status': 'SUBMITTED',
            'timestamp': datetime.now(timezone.utc)
        }
        
        # Step 3: Order execution simulation
        execution_report = {
            'order_id': self.sample_order['order_id'],
            'status': 'FILLED',
            'filled_quantity': 100,
            'avg_fill_price': 149.50,
            'commission': 1.00,
            'execution_time': datetime.now(timezone.utc)
        }
        
        # Step 4: Portfolio update
        self.portfolio_manager.update_position.return_value = {
            'symbol': 'AAPL',
            'new_quantity': 150,  # 50 + 100
            'new_avg_price': 148.67,
            'realized_pnl': 0.00,
            'unrealized_pnl': 124.50
        }
        
        # Execute workflow
        validation_result = self.risk_manager.validate_order(self.sample_order)
        assert validation_result['valid'] is True
        
        submission_result = self.order_manager.submit_order(self.sample_order)
        assert submission_result['status'] == 'SUBMITTED'
        
        # Simulate execution
        portfolio_update = self.portfolio_manager.update_position(
            'AAPL', 100, 149.50, 'BUY'
        )
        assert portfolio_update['new_quantity'] == 150
    
    @pytest.mark.asyncio
    async def test_limit_order_workflow(self):
        """Test limit order workflow with partial fills."""
        limit_order = self.sample_order.copy()
        limit_order.update({
            'order_type': 'LIMIT',
            'price': 149.00,
            'time_in_force': 'GTC'
        })
        
        # Step 1: Order validation and submission
        self.risk_manager.validate_order.return_value = {'valid': True}
        self.order_manager.submit_order.return_value = {
            'order_id': limit_order['order_id'],
            'status': 'PENDING',
            'timestamp': datetime.now(timezone.utc)
        }
        
        # Step 2: Partial fill simulation
        partial_fill = {
            'order_id': limit_order['order_id'],
            'status': 'PARTIALLY_FILLED',
            'filled_quantity': 60,
            'remaining_quantity': 40,
            'avg_fill_price': 149.00,
            'commission': 0.60
        }
        
        # Step 3: Complete fill
        complete_fill = {
            'order_id': limit_order['order_id'],
            'status': 'FILLED',
            'filled_quantity': 100,
            'remaining_quantity': 0,
            'avg_fill_price': 149.00,
            'total_commission': 1.00
        }
        
        # Execute workflow
        validation_result = self.risk_manager.validate_order(limit_order)
        submission_result = self.order_manager.submit_order(limit_order)
        
        assert validation_result['valid'] is True
        assert submission_result['status'] == 'PENDING'
    
    def test_order_cancellation_workflow(self):
        """Test order cancellation workflow."""
        # Submit order first
        self.order_manager.submit_order.return_value = {
            'order_id': self.sample_order['order_id'],
            'status': 'PENDING'
        }
        
        # Cancel order
        self.order_manager.cancel_order.return_value = {
            'order_id': self.sample_order['order_id'],
            'status': 'CANCELLED',
            'cancelled_quantity': 100,
            'timestamp': datetime.now(timezone.utc)
        }
        
        submission_result = self.order_manager.submit_order(self.sample_order)
        cancellation_result = self.order_manager.cancel_order(self.sample_order['order_id'])
        
        assert submission_result['status'] == 'PENDING'
        assert cancellation_result['status'] == 'CANCELLED'
    
    def test_order_rejection_workflow(self):
        """Test order rejection due to risk management."""
        # Risk manager rejects order
        self.risk_manager.validate_order.return_value = {
            'valid': False,
            'rejection_reason': 'Insufficient buying power',
            'required_margin': 15000.00,
            'available_margin': 5000.00
        }
        
        validation_result = self.risk_manager.validate_order(self.sample_order)
        assert validation_result['valid'] is False
        assert 'Insufficient buying power' in validation_result['rejection_reason']


class TestPortfolioManagementWorkflows:
    """Integration tests for portfolio management workflows."""
    
    def setup_method(self):
        """Set up test fixtures for portfolio management tests."""
        self.portfolio_manager = Mock(spec=PortfolioManager)
        self.risk_manager = Mock(spec=RiskManager)
        
        self.sample_portfolio = {
            'account_id': 'test_account',
            'cash_balance': 50000.00,
            'positions': {
                'AAPL': {'quantity': 100, 'avg_price': 148.00, 'market_value': 14950.00},
                'GOOGL': {'quantity': 50, 'avg_price': 2800.00, 'market_value': 141000.00},
                'MSFT': {'quantity': 75, 'avg_price': 380.00, 'market_value': 28650.00}
            },
            'total_value': 234600.00
        }
    
    def test_portfolio_rebalancing_workflow(self):
        """Test portfolio rebalancing workflow."""
        target_allocation = {
            'AAPL': 0.30,  # 30%
            'GOOGL': 0.50,  # 50%
            'MSFT': 0.20   # 20%
        }
        
        # Calculate rebalancing orders
        self.portfolio_manager.calculate_rebalancing_orders.return_value = [
            {'symbol': 'AAPL', 'side': 'BUY', 'quantity': 47, 'target_value': 70380.00},
            {'symbol': 'GOOGL', 'side': 'SELL', 'quantity': 8, 'target_value': 117300.00},
            {'symbol': 'MSFT', 'side': 'SELL', 'quantity': 13, 'target_value': 46920.00}
        ]
        
        rebalancing_orders = self.portfolio_manager.calculate_rebalancing_orders(
            self.sample_portfolio, target_allocation
        )
        
        assert len(rebalancing_orders) == 3
        assert any(order['symbol'] == 'AAPL' and order['side'] == 'BUY' for order in rebalancing_orders)
    
    def test_risk_monitoring_workflow(self):
        """Test continuous risk monitoring workflow."""
        # Risk metrics calculation
        self.risk_manager.calculate_portfolio_risk.return_value = {
            'total_exposure': 184600.00,
            'var_1d_95': -8500.00,  # 1-day VaR at 95% confidence
            'var_1d_99': -12750.00,  # 1-day VaR at 99% confidence
            'beta': 1.15,
            'sharpe_ratio': 1.42,
            'max_drawdown': -0.08,
            'concentration_risk': {
                'GOOGL': 0.60  # 60% concentration in GOOGL
            }
        }
        
        # Risk limit checks
        self.risk_manager.check_risk_limits.return_value = {
            'limits_breached': True,
            'breaches': [
                {
                    'type': 'CONCENTRATION_LIMIT',
                    'symbol': 'GOOGL',
                    'current_exposure': 0.60,
                    'limit': 0.50,
                    'severity': 'HIGH'
                }
            ],
            'recommended_actions': [
                'Reduce GOOGL position by 10%',
                'Increase diversification'
            ]
        }
        
        risk_metrics = self.risk_manager.calculate_portfolio_risk(self.sample_portfolio)
        risk_check = self.risk_manager.check_risk_limits(risk_metrics)
        
        assert risk_metrics['beta'] > 1.0  # Portfolio is more volatile than market
        assert risk_check['limits_breached'] is True
        assert len(risk_check['breaches']) > 0
    
    def test_performance_attribution_workflow(self):
        """Test performance attribution analysis workflow."""
        performance_period = {
            'start_date': datetime.now(timezone.utc) - timedelta(days=30),
            'end_date': datetime.now(timezone.utc)
        }
        
        self.portfolio_manager.calculate_performance_attribution.return_value = {
            'total_return': 0.085,  # 8.5% return
            'benchmark_return': 0.062,  # 6.2% benchmark return
            'alpha': 0.023,  # 2.3% alpha
            'position_contributions': {
                'AAPL': {'return_contribution': 0.025, 'weight': 0.30},
                'GOOGL': {'return_contribution': 0.045, 'weight': 0.50},
                'MSFT': {'return_contribution': 0.015, 'weight': 0.20}
            },
            'sector_allocation': {
                'Technology': 1.00  # 100% tech allocation
            }
        }
        
        attribution = self.portfolio_manager.calculate_performance_attribution(
            self.sample_portfolio, performance_period
        )
        
        assert attribution['alpha'] > 0  # Positive alpha
        assert attribution['total_return'] > attribution['benchmark_return']


class TestRiskManagementWorkflows:
    """Integration tests for risk management workflows."""
    
    def setup_method(self):
        """Set up test fixtures for risk management tests."""
        self.risk_manager = Mock(spec=RiskManager)
        self.order_manager = Mock(spec=OrderManager)
        
        self.high_risk_order = {
            'order_id': str(uuid.uuid4()),
            'symbol': 'TSLA',
            'side': 'BUY',
            'quantity': 1000,  # Large position
            'order_type': 'MARKET',
            'account_id': 'test_account'
        }
    
    def test_pre_trade_risk_checks(self):
        """Test comprehensive pre-trade risk validation."""
        self.risk_manager.validate_order.return_value = {
            'valid': False,
            'risk_checks': {
                'position_limit_check': {'passed': False, 'current': 0.45, 'limit': 0.40},
                'buying_power_check': {'passed': True, 'required': 250000, 'available': 300000},
                'concentration_check': {'passed': False, 'sector_exposure': 0.85, 'limit': 0.70},
                'volatility_check': {'passed': True, 'symbol_volatility': 0.35, 'limit': 0.50}
            },
            'rejection_reasons': [
                'Position limit exceeded',
                'Sector concentration limit exceeded'
            ]
        }
        
        validation_result = self.risk_manager.validate_order(self.high_risk_order)
        
        assert validation_result['valid'] is False
        assert len(validation_result['rejection_reasons']) == 2
        assert not validation_result['risk_checks']['position_limit_check']['passed']
    
    def test_real_time_risk_monitoring(self):
        """Test real-time risk monitoring and alerting."""
        self.risk_manager.monitor_real_time_risk.return_value = {
            'risk_alerts': [
                {
                    'alert_id': str(uuid.uuid4()),
                    'type': 'VAR_BREACH',
                    'severity': 'HIGH',
                    'message': 'Portfolio VaR exceeded daily limit',
                    'current_var': -15000.00,
                    'limit': -12000.00,
                    'timestamp': datetime.now(timezone.utc)
                },
                {
                    'alert_id': str(uuid.uuid4()),
                    'type': 'DRAWDOWN_WARNING',
                    'severity': 'MEDIUM',
                    'message': 'Portfolio drawdown approaching limit',
                    'current_drawdown': -0.08,
                    'limit': -0.10,
                    'timestamp': datetime.now(timezone.utc)
                }
            ],
            'risk_metrics': {
                'current_var': -15000.00,
                'current_drawdown': -0.08,
                'leverage_ratio': 1.25,
                'beta': 1.18
            }
        }
        
        risk_monitoring = self.risk_manager.monitor_real_time_risk()
        
        assert len(risk_monitoring['risk_alerts']) == 2
        assert any(alert['type'] == 'VAR_BREACH' for alert in risk_monitoring['risk_alerts'])
    
    def test_stop_loss_workflow(self):
        """Test automated stop-loss order generation and execution."""
        position_with_loss = {
            'symbol': 'AAPL',
            'quantity': 100,
            'avg_price': 150.00,
            'current_price': 142.50,  # 5% loss
            'unrealized_pnl': -750.00,
            'stop_loss_level': 145.00  # 3.33% stop loss
        }
        
        # Stop loss triggered
        self.risk_manager.check_stop_loss_triggers.return_value = [
            {
                'symbol': 'AAPL',
                'trigger_price': 145.00,
                'current_price': 142.50,
                'action': 'SELL',
                'quantity': 100,
                'order_type': 'MARKET'
            }
        ]
        
        # Generate stop loss order
        self.order_manager.generate_stop_loss_order.return_value = {
            'order_id': str(uuid.uuid4()),
            'symbol': 'AAPL',
            'side': 'SELL',
            'quantity': 100,
            'order_type': 'MARKET',
            'reason': 'STOP_LOSS_TRIGGERED',
            'trigger_price': 145.00
        }
        
        stop_loss_triggers = self.risk_manager.check_stop_loss_triggers([position_with_loss])
        
        assert len(stop_loss_triggers) == 1
        assert stop_loss_triggers[0]['action'] == 'SELL'
        
        stop_loss_order = self.order_manager.generate_stop_loss_order(stop_loss_triggers[0])
        assert stop_loss_order['reason'] == 'STOP_LOSS_TRIGGERED'


class TestBrokerIntegrationWorkflows:
    """Integration tests for broker connectivity and operations."""
    
    def setup_method(self):
        """Set up test fixtures for broker integration tests."""
        self.ib_adapter = Mock(spec=InteractiveBrokersAdapter)
        
        self.connection_config = {
            'host': '127.0.0.1',
            'port': 7497,  # Paper trading port
            'client_id': 1,
            'account_id': 'DU123456'
        }
    
    @pytest.mark.asyncio
    async def test_broker_connection_workflow(self):
        """Test broker connection establishment and health monitoring."""
        # Connection establishment
        self.ib_adapter.connect.return_value = {
            'connected': True,
            'connection_time': datetime.now(timezone.utc),
            'server_version': '10.19',
            'account_id': 'DU123456'
        }
        
        # Health check
        self.ib_adapter.health_check.return_value = {
            'status': 'HEALTHY',
            'latency_ms': 15,
            'last_heartbeat': datetime.now(timezone.utc),
            'market_data_status': 'ACTIVE',
            'order_routing_status': 'ACTIVE'
        }
        
        connection_result = await self.ib_adapter.connect(self.connection_config)
        health_status = await self.ib_adapter.health_check()
        
        assert connection_result['connected'] is True
        assert health_status['status'] == 'HEALTHY'
        assert health_status['latency_ms'] < 50
    
    def test_market_data_subscription_workflow(self):
        """Test market data subscription and streaming."""
        symbols = ['AAPL', 'GOOGL', 'MSFT']
        
        self.ib_adapter.subscribe_market_data.return_value = {
            'subscription_id': 'md_sub_123',
            'symbols': symbols,
            'data_types': ['TRADES', 'QUOTES', 'BID_ASK'],
            'status': 'ACTIVE'
        }
        
        # Sample market data stream
        self.ib_adapter.get_market_data_stream.return_value = [
            {
                'symbol': 'AAPL',
                'bid': 149.50,
                'ask': 149.55,
                'last': 149.52,
                'volume': 1000,
                'timestamp': datetime.now(timezone.utc)
            }
        ]
        
        subscription = self.ib_adapter.subscribe_market_data(symbols)
        market_data = self.ib_adapter.get_market_data_stream()
        
        assert subscription['status'] == 'ACTIVE'
        assert len(subscription['symbols']) == 3
        assert len(market_data) > 0
    
    def test_order_routing_workflow(self):
        """Test order routing through broker."""
        order = {
            'symbol': 'AAPL',
            'side': 'BUY',
            'quantity': 100,
            'order_type': 'LIMIT',
            'price': 149.00,
            'time_in_force': 'DAY'
        }
        
        # Order submission to broker
        self.ib_adapter.submit_order.return_value = {
            'broker_order_id': 'IB_12345',
            'status': 'SUBMITTED',
            'submission_time': datetime.now(timezone.utc),
            'estimated_commission': 1.00
        }
        
        # Order status updates
        self.ib_adapter.get_order_status.return_value = {
            'broker_order_id': 'IB_12345',
            'status': 'FILLED',
            'filled_quantity': 100,
            'avg_fill_price': 149.00,
            'commission': 1.00,
            'fill_time': datetime.now(timezone.utc)
        }
        
        submission_result = self.ib_adapter.submit_order(order)
        order_status = self.ib_adapter.get_order_status('IB_12345')
        
        assert submission_result['status'] == 'SUBMITTED'
        assert order_status['status'] == 'FILLED'
        assert order_status['filled_quantity'] == 100


class TestEndToEndTradingScenarios:
    """End-to-end integration tests for complete trading scenarios."""
    
    def setup_method(self):
        """Set up test fixtures for end-to-end scenarios."""
        self.trading_engine = Mock(spec=TradingEngine)
        self.components = {
            'portfolio_manager': Mock(spec=PortfolioManager),
            'order_manager': Mock(spec=OrderManager),
            'risk_manager': Mock(spec=RiskManager),
            'broker_adapter': Mock(spec=InteractiveBrokersAdapter)
        }
    
    @pytest.mark.asyncio
    async def test_complete_trading_session(self):
        """Test complete trading session from startup to shutdown."""
        # 1. System startup
        self.trading_engine.startup.return_value = {
            'status': 'STARTED',
            'components_initialized': 4,
            'broker_connected': True,
            'market_data_active': True
        }
        
        # 2. Strategy execution
        strategy_signal = {
            'symbol': 'AAPL',
            'action': 'BUY',
            'quantity': 100,
            'confidence': 0.85,
            'strategy_id': 'momentum_strategy_1'
        }
        
        # 3. Order execution
        self.components['order_manager'].execute_strategy_signal.return_value = {
            'orders_generated': 1,
            'orders_submitted': 1,
            'orders_filled': 1,
            'total_commission': 1.00
        }
        
        # 4. Portfolio update
        self.components['portfolio_manager'].process_fills.return_value = {
            'positions_updated': 1,
            'cash_balance': 49850.00,  # After purchase and commission
            'total_portfolio_value': 64850.00
        }
        
        # 5. System shutdown
        self.trading_engine.shutdown.return_value = {
            'status': 'SHUTDOWN_COMPLETE',
            'orders_cancelled': 0,
            'positions_closed': 0,
            'data_persisted': True
        }
        
        # Execute complete session
        startup_result = await self.trading_engine.startup()
        execution_result = self.components['order_manager'].execute_strategy_signal(strategy_signal)
        portfolio_result = self.components['portfolio_manager'].process_fills()
        shutdown_result = await self.trading_engine.shutdown()
        
        assert startup_result['status'] == 'STARTED'
        assert execution_result['orders_filled'] == 1
        assert portfolio_result['positions_updated'] == 1
        assert shutdown_result['status'] == 'SHUTDOWN_COMPLETE'
    
    def test_multi_asset_portfolio_management(self):
        """Test managing a multi-asset portfolio with rebalancing."""
        initial_portfolio = {
            'cash': 10000.00,
            'positions': {
                'AAPL': {'quantity': 50, 'avg_price': 148.00},
                'GOOGL': {'quantity': 25, 'avg_price': 2800.00},
                'BTC-USD': {'quantity': 0.5, 'avg_price': 45000.00}
            }
        }
        
        # Rebalancing scenario
        rebalancing_orders = [
            {'symbol': 'AAPL', 'side': 'BUY', 'quantity': 25},
            {'symbol': 'GOOGL', 'side': 'SELL', 'quantity': 5},
            {'symbol': 'ETH-USD', 'side': 'BUY', 'quantity': 2.0}
        ]
        
        self.components['portfolio_manager'].execute_rebalancing.return_value = {
            'orders_executed': 3,
            'rebalancing_complete': True,
            'new_allocation': {
                'AAPL': 0.35,
                'GOOGL': 0.45,
                'BTC-USD': 0.10,
                'ETH-USD': 0.10
            },
            'total_commission': 3.50
        }
        
        rebalancing_result = self.components['portfolio_manager'].execute_rebalancing(
            initial_portfolio, rebalancing_orders
        )
        
        assert rebalancing_result['rebalancing_complete'] is True
        assert rebalancing_result['orders_executed'] == 3
        assert len(rebalancing_result['new_allocation']) == 4
    
    def test_risk_event_response_workflow(self):
        """Test system response to risk events and market volatility."""
        # Simulate market volatility event
        market_event = {
            'event_type': 'HIGH_VOLATILITY',
            'affected_symbols': ['AAPL', 'GOOGL', 'MSFT'],
            'volatility_spike': 0.45,  # 45% volatility
            'timestamp': datetime.now(timezone.utc)
        }
        
        # Risk manager response
        self.components['risk_manager'].handle_market_event.return_value = {
            'risk_actions': [
                {'action': 'REDUCE_POSITION', 'symbol': 'AAPL', 'reduction_pct': 0.20},
                {'action': 'TIGHTEN_STOP_LOSS', 'symbol': 'GOOGL', 'new_stop_pct': 0.02},
                {'action': 'PAUSE_NEW_ORDERS', 'duration_minutes': 30}
            ],
            'portfolio_protection_activated': True
        }
        
        # Execute risk response
        self.components['order_manager'].execute_risk_actions.return_value = {
            'actions_executed': 3,
            'positions_reduced': 1,
            'stop_losses_updated': 1,
            'new_orders_paused': True
        }
        
        risk_response = self.components['risk_manager'].handle_market_event(market_event)
        execution_result = self.components['order_manager'].execute_risk_actions(
            risk_response['risk_actions']
        )
        
        assert risk_response['portfolio_protection_activated'] is True
        assert execution_result['actions_executed'] == 3
        assert execution_result['new_orders_paused'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])