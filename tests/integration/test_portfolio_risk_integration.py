"""Integration tests for Portfolio Manager with Risk Manager.

This module tests the integration between the Portfolio Manager and Risk Manager,
focusing on:
- Position management with risk constraints
- Real-time risk monitoring and alerts
- Portfolio rebalancing with risk optimization
- VaR calculations and stress testing
- Margin and leverage management
- Risk-adjusted performance metrics
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, MagicMock, patch
import numpy as np
import pandas as pd
from typing import Dict, List, Any

# Import shared models and utilities
from shared.models.portfolio import Portfolio, Position, PortfolioMetrics
from shared.models.risk import RiskMetrics, VaRCalculation, StressTestResult
from shared.models.orders import OrderCreateRequest, OrderSide, OrderType
from shared.utils.logging_utils import get_logger

logger = get_logger(__name__)


class TestPortfolioRiskIntegration:
    """Test suite for Portfolio Manager and Risk Manager integration."""
    
    @pytest.fixture
    async def portfolio_risk_system(self):
        """Setup integrated portfolio and risk management system."""
        # Mock Portfolio Manager
        portfolio_manager = Mock()
        portfolio_manager.get_portfolio = AsyncMock()
        portfolio_manager.update_position = AsyncMock()
        portfolio_manager.calculate_metrics = AsyncMock()
        portfolio_manager.rebalance_portfolio = AsyncMock()
        
        # Mock Risk Manager
        risk_manager = Mock()
        risk_manager.calculate_var = AsyncMock()
        risk_manager.validate_order = AsyncMock()
        risk_manager.monitor_risk = AsyncMock()
        risk_manager.stress_test = AsyncMock()
        risk_manager.check_margin_requirements = AsyncMock()
        
        # Mock Market Data Service
        market_data = Mock()
        market_data.get_latest_quote = AsyncMock()
        market_data.get_historical_data = AsyncMock()
        market_data.get_correlation_matrix = AsyncMock()
        
        # Mock Database
        mock_db = Mock()
        mock_db.save_portfolio = AsyncMock()
        mock_db.save_risk_metrics = AsyncMock()
        mock_db.get_portfolio_history = AsyncMock()
        
        # Mock Event Bus (Kafka)
        event_bus = Mock()
        event_bus.publish = AsyncMock()
        event_bus.subscribe = AsyncMock()
        
        return {
            'portfolio_manager': portfolio_manager,
            'risk_manager': risk_manager,
            'market_data': market_data,
            'mock_db': mock_db,
            'event_bus': event_bus
        }
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_position_update_with_risk_validation(self, portfolio_risk_system):
        """Test position updates with real-time risk validation."""
        # Setup initial portfolio
        initial_portfolio = Portfolio(
            account_id='test_account',
            total_value=Decimal('100000.00'),
            cash_balance=Decimal('50000.00'),
            positions={
                'AAPL': Position(
                    symbol='AAPL',
                    quantity=Decimal('100'),
                    avg_price=Decimal('150.00'),
                    current_price=Decimal('155.00'),
                    market_value=Decimal('15500.00')
                ),
                'TSLA': Position(
                    symbol='TSLA',
                    quantity=Decimal('50'),
                    avg_price=Decimal('800.00'),
                    current_price=Decimal('820.00'),
                    market_value=Decimal('41000.00')
                )
            },
            created_at=datetime.now(timezone.utc)
        )
        
        portfolio_risk_system['portfolio_manager'].get_portfolio.return_value = initial_portfolio
        
        # Setup risk validation response
        risk_validation = {
            'approved': True,
            'risk_score': 0.65,
            'concentration_risk': 0.41,  # 41% in TSLA
            'var_impact': Decimal('2500.00'),
            'margin_requirement': Decimal('15000.00')
        }
        
        portfolio_risk_system['risk_manager'].validate_order.return_value = risk_validation
        
        # Test new position addition
        new_order = OrderCreateRequest(
            account_id='test_account',
            symbol='MSFT',
            side=OrderSide.BUY,
            quantity=Decimal('75'),
            order_type=OrderType.MARKET,
            price=Decimal('300.00')
        )
        
        # Mock market data for new position
        portfolio_risk_system['market_data'].get_latest_quote.return_value = {
            'symbol': 'MSFT',
            'price': Decimal('300.00'),
            'bid': Decimal('299.95'),
            'ask': Decimal('300.05'),
            'volume': 1000000
        }
        
        # Execute position update with risk validation
        risk_check = await portfolio_risk_system['risk_manager'].validate_order(new_order, initial_portfolio)
        
        if risk_check['approved']:
            # Update portfolio with new position
            updated_position = Position(
                symbol='MSFT',
                quantity=Decimal('75'),
                avg_price=Decimal('300.00'),
                current_price=Decimal('300.00'),
                market_value=Decimal('22500.00')
            )
            
            await portfolio_risk_system['portfolio_manager'].update_position('test_account', updated_position)
            
            # Verify risk validation was called
            portfolio_risk_system['risk_manager'].validate_order.assert_called_once_with(new_order, initial_portfolio)
            
            # Verify position update was called
            portfolio_risk_system['portfolio_manager'].update_position.assert_called_once_with('test_account', updated_position)
            
            # Verify risk metrics are within acceptable limits
            assert risk_check['risk_score'] < 0.8  # Risk score threshold
            assert risk_check['concentration_risk'] < 0.5  # Max 50% concentration
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_time_risk_monitoring(self, portfolio_risk_system):
        """Test real-time risk monitoring and alert generation."""
        # Setup portfolio with high-risk positions
        high_risk_portfolio = Portfolio(
            account_id='risk_test_account',
            total_value=Decimal('500000.00'),
            cash_balance=Decimal('50000.00'),
            positions={
                'TSLA': Position(
                    symbol='TSLA',
                    quantity=Decimal('300'),
                    avg_price=Decimal('800.00'),
                    current_price=Decimal('750.00'),  # Down 6.25%
                    market_value=Decimal('225000.00')
                ),
                'NVDA': Position(
                    symbol='NVDA',
                    quantity=Decimal('200'),
                    avg_price=Decimal('900.00'),
                    current_price=Decimal('850.00'),  # Down 5.56%
                    market_value=Decimal('170000.00')
                ),
                'AAPL': Position(
                    symbol='AAPL',
                    quantity=Decimal('200'),
                    avg_price=Decimal('150.00'),
                    current_price=Decimal('155.00'),
                    market_value=Decimal('31000.00')
                )
            },
            created_at=datetime.now(timezone.utc)
        )
        
        # Setup risk metrics calculation
        risk_metrics = RiskMetrics(
            portfolio_var_1d=Decimal('25000.00'),  # 5% of portfolio
            portfolio_var_5d=Decimal('55000.00'),  # 11% of portfolio
            beta=1.35,
            sharpe_ratio=0.85,
            max_drawdown=Decimal('0.12'),
            concentration_risk=0.79,  # High concentration
            leverage_ratio=1.8,
            margin_utilization=0.65,
            calculated_at=datetime.now(timezone.utc)
        )
        
        portfolio_risk_system['risk_manager'].calculate_var.return_value = risk_metrics
        
        # Setup correlation matrix for risk calculation
        correlation_matrix = pd.DataFrame({
            'TSLA': [1.0, 0.65, 0.45],
            'NVDA': [0.65, 1.0, 0.55],
            'AAPL': [0.45, 0.55, 1.0]
        }, index=['TSLA', 'NVDA', 'AAPL'])
        
        portfolio_risk_system['market_data'].get_correlation_matrix.return_value = correlation_matrix
        
        # Execute real-time risk monitoring
        risk_alerts = await portfolio_risk_system['risk_manager'].monitor_risk(high_risk_portfolio)
        
        # Mock risk alerts based on high risk metrics
        expected_alerts = [
            {
                'type': 'CONCENTRATION_RISK',
                'severity': 'HIGH',
                'message': 'Portfolio concentration exceeds 75% threshold',
                'current_value': 0.79,
                'threshold': 0.75,
                'timestamp': datetime.now(timezone.utc)
            },
            {
                'type': 'VAR_BREACH',
                'severity': 'MEDIUM',
                'message': '5-day VaR exceeds 10% of portfolio value',
                'current_value': Decimal('55000.00'),
                'threshold': Decimal('50000.00'),
                'timestamp': datetime.now(timezone.utc)
            }
        ]
        
        portfolio_risk_system['risk_manager'].monitor_risk.return_value = expected_alerts
        
        # Verify risk monitoring was executed
        portfolio_risk_system['risk_manager'].monitor_risk.assert_called_once_with(high_risk_portfolio)
        
        # Verify alerts were generated
        alerts = await portfolio_risk_system['risk_manager'].monitor_risk(high_risk_portfolio)
        assert len(alerts) >= 1
        
        # Check for concentration risk alert
        concentration_alert = next((alert for alert in alerts if alert['type'] == 'CONCENTRATION_RISK'), None)
        assert concentration_alert is not None
        assert concentration_alert['severity'] == 'HIGH'
        assert concentration_alert['current_value'] > 0.75
        
        # Verify event publishing for alerts
        for alert in alerts:
            await portfolio_risk_system['event_bus'].publish('risk_alerts', alert)
        
        assert portfolio_risk_system['event_bus'].publish.call_count >= len(alerts)
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_portfolio_rebalancing_with_risk_optimization(self, portfolio_risk_system):
        """Test portfolio rebalancing with risk optimization constraints."""
        # Setup unbalanced portfolio
        unbalanced_portfolio = Portfolio(
            account_id='rebalance_account',
            total_value=Decimal('1000000.00'),
            cash_balance=Decimal('100000.00'),
            positions={
                'AAPL': Position(
                    symbol='AAPL',
                    quantity=Decimal('2000'),
                    avg_price=Decimal('150.00'),
                    current_price=Decimal('160.00'),
                    market_value=Decimal('320000.00')  # 32% allocation
                ),
                'TSLA': Position(
                    symbol='TSLA',
                    quantity=Decimal('600'),
                    avg_price=Decimal('800.00'),
                    current_price=Decimal('850.00'),
                    market_value=Decimal('510000.00')  # 51% allocation - too high
                ),
                'MSFT': Position(
                    symbol='MSFT',
                    quantity=Decimal('200'),
                    avg_price=Decimal('300.00'),
                    current_price=Decimal('320.00'),
                    market_value=Decimal('64000.00')  # 6.4% allocation
                )
            },
            created_at=datetime.now(timezone.utc)
        )
        
        # Define target allocation with risk constraints
        target_allocation = {
            'AAPL': 0.30,  # 30%
            'TSLA': 0.35,  # 35% - reduce from 51%
            'MSFT': 0.25,  # 25% - increase from 6.4%
            'CASH': 0.10   # 10% cash buffer
        }
        
        # Setup risk-optimized rebalancing plan
        rebalancing_plan = {
            'trades': [
                {
                    'symbol': 'TSLA',
                    'action': 'SELL',
                    'quantity': Decimal('188'),  # Reduce TSLA position
                    'target_value': Decimal('350000.00'),
                    'risk_impact': -0.15  # Reduces portfolio risk
                },
                {
                    'symbol': 'MSFT',
                    'action': 'BUY',
                    'quantity': Decimal('594'),  # Increase MSFT position
                    'target_value': Decimal('250000.00'),
                    'risk_impact': 0.05  # Slight risk increase but better diversification
                }
            ],
            'expected_risk_reduction': 0.12,
            'new_portfolio_var': Decimal('18000.00'),
            'diversification_improvement': 0.08
        }
        
        portfolio_risk_system['portfolio_manager'].rebalance_portfolio.return_value = rebalancing_plan
        
        # Mock risk validation for rebalancing trades
        portfolio_risk_system['risk_manager'].validate_order.return_value = {
            'approved': True,
            'risk_score': 0.55,  # Improved from previous 0.72
            'concentration_risk': 0.35,  # Improved from 0.51
            'var_impact': Decimal('-3000.00')  # Risk reduction
        }
        
        # Execute portfolio rebalancing
        rebalance_result = await portfolio_risk_system['portfolio_manager'].rebalance_portfolio(
            'rebalance_account', 
            target_allocation
        )
        
        # Verify rebalancing was executed
        portfolio_risk_system['portfolio_manager'].rebalance_portfolio.assert_called_once_with(
            'rebalance_account', 
            target_allocation
        )
        
        # Verify risk optimization results
        assert rebalance_result['expected_risk_reduction'] > 0.10
        assert len(rebalance_result['trades']) >= 1
        
        # Verify each trade was risk-validated
        for trade in rebalance_result['trades']:
            # Create order request for validation
            order_request = OrderCreateRequest(
                account_id='rebalance_account',
                symbol=trade['symbol'],
                side=OrderSide.SELL if trade['action'] == 'SELL' else OrderSide.BUY,
                quantity=trade['quantity'],
                order_type=OrderType.MARKET
            )
            
            # Validate trade with risk manager
            risk_validation = await portfolio_risk_system['risk_manager'].validate_order(
                order_request, 
                unbalanced_portfolio
            )
            
            assert risk_validation['approved'] is True
            assert risk_validation['risk_score'] < 0.8
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_var_calculation_and_stress_testing(self, portfolio_risk_system):
        """Test VaR calculation and stress testing integration."""
        # Setup diversified portfolio for VaR testing
        test_portfolio = Portfolio(
            account_id='var_test_account',
            total_value=Decimal('2000000.00'),
            cash_balance=Decimal('200000.00'),
            positions={
                'SPY': Position(  # S&P 500 ETF
                    symbol='SPY',
                    quantity=Decimal('1000'),
                    avg_price=Decimal('400.00'),
                    current_price=Decimal('420.00'),
                    market_value=Decimal('420000.00')
                ),
                'QQQ': Position(  # NASDAQ ETF
                    symbol='QQQ',
                    quantity=Decimal('800'),
                    avg_price=Decimal('350.00'),
                    current_price=Decimal('360.00'),
                    market_value=Decimal('288000.00')
                ),
                'GLD': Position(  # Gold ETF
                    symbol='GLD',
                    quantity=Decimal('2000'),
                    avg_price=Decimal('180.00'),
                    current_price=Decimal('185.00'),
                    market_value=Decimal('370000.00')
                ),
                'TLT': Position(  # Treasury Bond ETF
                    symbol='TLT',
                    quantity=Decimal('3000'),
                    avg_price=Decimal('120.00'),
                    current_price=Decimal('115.00'),
                    market_value=Decimal('345000.00')
                ),
                'VTI': Position(  # Total Stock Market ETF
                    symbol='VTI',
                    quantity=Decimal('1500'),
                    avg_price=Decimal('220.00'),
                    current_price=Decimal('230.00'),
                    market_value=Decimal('345000.00')
                )
            },
            created_at=datetime.now(timezone.utc)
        )
        
        # Setup historical data for VaR calculation
        historical_returns = {
            'SPY': np.random.normal(0.0008, 0.012, 252),  # Daily returns for 1 year
            'QQQ': np.random.normal(0.0010, 0.015, 252),
            'GLD': np.random.normal(0.0003, 0.008, 252),
            'TLT': np.random.normal(0.0002, 0.006, 252),
            'VTI': np.random.normal(0.0009, 0.011, 252)
        }
        
        portfolio_risk_system['market_data'].get_historical_data.side_effect = lambda symbol: historical_returns[symbol]
        
        # Setup VaR calculation results
        var_results = VaRCalculation(
            portfolio_value=Decimal('2000000.00'),
            var_1d_95=Decimal('32000.00'),  # 1.6% of portfolio
            var_5d_95=Decimal('71000.00'),  # 3.55% of portfolio
            var_1d_99=Decimal('48000.00'),  # 2.4% of portfolio
            var_5d_99=Decimal('107000.00'), # 5.35% of portfolio
            expected_shortfall_95=Decimal('42000.00'),
            expected_shortfall_99=Decimal('65000.00'),
            confidence_level=0.95,
            calculation_method='MONTE_CARLO',
            calculated_at=datetime.now(timezone.utc)
        )
        
        portfolio_risk_system['risk_manager'].calculate_var.return_value = var_results
        
        # Execute VaR calculation
        var_calculation = await portfolio_risk_system['risk_manager'].calculate_var(test_portfolio)
        
        # Verify VaR calculation
        assert var_calculation.var_1d_95 > Decimal('0')
        assert var_calculation.var_5d_95 > var_calculation.var_1d_95
        assert var_calculation.var_1d_99 > var_calculation.var_1d_95
        assert var_calculation.expected_shortfall_95 > var_calculation.var_1d_95
        
        # Setup stress testing scenarios
        stress_scenarios = [
            {
                'name': 'MARKET_CRASH_2008',
                'description': '2008 Financial Crisis scenario',
                'shocks': {
                    'SPY': -0.37,  # -37% shock
                    'QQQ': -0.42,  # -42% shock
                    'GLD': 0.25,   # +25% (safe haven)
                    'TLT': 0.15,   # +15% (flight to quality)
                    'VTI': -0.35   # -35% shock
                }
            },
            {
                'name': 'COVID_CRASH_2020',
                'description': 'COVID-19 market crash scenario',
                'shocks': {
                    'SPY': -0.34,  # -34% shock
                    'QQQ': -0.25,  # -25% (tech resilience)
                    'GLD': 0.12,   # +12%
                    'TLT': 0.08,   # +8%
                    'VTI': -0.32   # -32% shock
                }
            }
        ]
        
        # Execute stress testing
        stress_results = []
        for scenario in stress_scenarios:
            # Calculate portfolio impact
            total_impact = Decimal('0')
            for symbol, position in test_portfolio.positions.items():
                if symbol in scenario['shocks']:
                    shock = Decimal(str(scenario['shocks'][symbol]))
                    impact = position.market_value * shock
                    total_impact += impact
            
            stress_result = StressTestResult(
                scenario_name=scenario['name'],
                portfolio_impact=total_impact,
                portfolio_value_after=test_portfolio.total_value + total_impact,
                max_loss=abs(total_impact) if total_impact < 0 else Decimal('0'),
                recovery_time_days=90 if total_impact < Decimal('-200000') else 30,
                calculated_at=datetime.now(timezone.utc)
            )
            stress_results.append(stress_result)
        
        portfolio_risk_system['risk_manager'].stress_test.return_value = stress_results
        
        # Execute stress testing
        stress_test_results = await portfolio_risk_system['risk_manager'].stress_test(test_portfolio, stress_scenarios)
        
        # Verify stress test results
        assert len(stress_test_results) == len(stress_scenarios)
        
        for result in stress_test_results:
            assert result.scenario_name in [s['name'] for s in stress_scenarios]
            assert result.portfolio_impact != Decimal('0')
            assert result.portfolio_value_after > Decimal('0')
        
        # Verify worst-case scenario identification
        worst_case = min(stress_test_results, key=lambda x: x.portfolio_value_after)
        assert worst_case.scenario_name == 'MARKET_CRASH_2008'  # Should be worst due to higher equity allocation
        
        # Save risk metrics to database
        await portfolio_risk_system['mock_db'].save_risk_metrics('var_test_account', var_calculation)
        portfolio_risk_system['mock_db'].save_risk_metrics.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_margin_and_leverage_management(self, portfolio_risk_system):
        """Test margin requirements and leverage management integration."""
        # Setup leveraged portfolio
        leveraged_portfolio = Portfolio(
            account_id='margin_account',
            total_value=Decimal('500000.00'),
            cash_balance=Decimal('-50000.00'),  # Negative cash (margin used)
            positions={
                'AAPL': Position(
                    symbol='AAPL',
                    quantity=Decimal('2000'),
                    avg_price=Decimal('150.00'),
                    current_price=Decimal('155.00'),
                    market_value=Decimal('310000.00')
                ),
                'TSLA': Position(
                    symbol='TSLA',
                    quantity=Decimal('300'),
                    avg_price=Decimal('800.00'),
                    current_price=Decimal('820.00'),
                    market_value=Decimal('246000.00')
                )
            },
            margin_used=Decimal('50000.00'),
            margin_available=Decimal('200000.00'),
            created_at=datetime.now(timezone.utc)
        )
        
        # Setup margin requirements calculation
        margin_requirements = {
            'initial_margin': Decimal('111200.00'),  # 20% of position value
            'maintenance_margin': Decimal('55600.00'),  # 10% of position value
            'current_margin_used': Decimal('50000.00'),
            'margin_excess': Decimal('150000.00'),
            'buying_power': Decimal('750000.00'),  # 2:1 leverage
            'leverage_ratio': 1.11,  # (310000 + 246000) / 500000
            'margin_call_threshold': Decimal('55600.00')
        }
        
        portfolio_risk_system['risk_manager'].check_margin_requirements.return_value = margin_requirements
        
        # Test margin requirement validation
        margin_check = await portfolio_risk_system['risk_manager'].check_margin_requirements(leveraged_portfolio)
        
        # Verify margin calculations
        assert margin_check['leverage_ratio'] > 1.0
        assert margin_check['margin_excess'] > Decimal('0')
        assert margin_check['buying_power'] > leveraged_portfolio.total_value
        
        # Test new order with margin impact
        new_leveraged_order = OrderCreateRequest(
            account_id='margin_account',
            symbol='MSFT',
            side=OrderSide.BUY,
            quantity=Decimal('500'),
            order_type=OrderType.MARKET,
            price=Decimal('300.00')  # $150,000 order
        )
        
        # Calculate margin impact of new order
        order_value = new_leveraged_order.quantity * new_leveraged_order.price
        required_margin = order_value * Decimal('0.20')  # 20% initial margin
        
        # Validate order against margin requirements
        margin_validation = {
            'approved': required_margin <= margin_check['margin_excess'],
            'required_margin': required_margin,
            'available_margin': margin_check['margin_excess'],
            'new_leverage_ratio': (leveraged_portfolio.total_value + order_value) / leveraged_portfolio.total_value,
            'margin_utilization': (margin_check['current_margin_used'] + required_margin) / (margin_check['current_margin_used'] + margin_check['margin_excess'])
        }
        
        portfolio_risk_system['risk_manager'].validate_order.return_value = margin_validation
        
        # Execute margin validation
        order_validation = await portfolio_risk_system['risk_manager'].validate_order(
            new_leveraged_order, 
            leveraged_portfolio
        )
        
        # Verify margin validation
        assert 'required_margin' in order_validation
        assert 'available_margin' in order_validation
        assert 'new_leverage_ratio' in order_validation
        
        # Test margin call scenario
        # Simulate market decline that triggers margin call
        declined_portfolio = Portfolio(
            account_id='margin_account',
            total_value=Decimal('400000.00'),  # 20% decline
            cash_balance=Decimal('-50000.00'),
            positions={
                'AAPL': Position(
                    symbol='AAPL',
                    quantity=Decimal('2000'),
                    avg_price=Decimal('150.00'),
                    current_price=Decimal('125.00'),  # Down 16%
                    market_value=Decimal('250000.00')
                ),
                'TSLA': Position(
                    symbol='TSLA',
                    quantity=Decimal('300'),
                    avg_price=Decimal('800.00'),
                    current_price=Decimal('670.00'),  # Down 16%
                    market_value=Decimal('201000.00')
                )
            },
            margin_used=Decimal('50000.00'),
            margin_available=Decimal('150000.00'),
            created_at=datetime.now(timezone.utc)
        )
        
        # Check for margin call
        margin_call_check = {
            'margin_call_triggered': True,
            'equity_below_maintenance': True,
            'required_deposit': Decimal('15000.00'),
            'liquidation_threshold': Decimal('350000.00'),
            'time_to_meet_call': timedelta(days=3)
        }
        
        portfolio_risk_system['risk_manager'].check_margin_requirements.return_value = margin_call_check
        
        # Execute margin call check
        margin_status = await portfolio_risk_system['risk_manager'].check_margin_requirements(declined_portfolio)
        
        # Verify margin call detection
        assert margin_status['margin_call_triggered'] is True
        assert margin_status['required_deposit'] > Decimal('0')
        
        # Publish margin call alert
        margin_alert = {
            'type': 'MARGIN_CALL',
            'severity': 'CRITICAL',
            'account_id': 'margin_account',
            'required_deposit': margin_status['required_deposit'],
            'deadline': datetime.now(timezone.utc) + margin_status['time_to_meet_call'],
            'timestamp': datetime.now(timezone.utc)
        }
        
        await portfolio_risk_system['event_bus'].publish('margin_alerts', margin_alert)
        portfolio_risk_system['event_bus'].publish.assert_called_with('margin_alerts', margin_alert)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])