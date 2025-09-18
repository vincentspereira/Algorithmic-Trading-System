"""Risk Manager Test Suite

Comprehensive tests for the risk management system components.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import pytest
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List
from unittest.mock import Mock, AsyncMock, patch

# Import risk manager components
from ..models.risk_models import (
    RiskLevel, VaRMethod, RiskLimits, RiskMetric, RiskViolation,
    RiskAssessmentRequest, RiskAssessmentResponse, PortfolioRiskSummary,
    OrderRequest, Position, Portfolio
)
from ..calculators.var_calculator import VaRCalculator
from ..calculators.position_sizer import PositionSizer
from ..monitors.realtime_monitor import RealTimeRiskMonitor
from ..engine.risk_engine import RiskEngine
from ..config.risk_config import RiskManagerConfig, get_testing_config

class TestRiskModels:
    """Test risk model classes"""
    
    def test_risk_limits_creation(self):
        """Test RiskLimits creation and validation"""
        limits = RiskLimits(
            max_position_size=10000.0,
            max_portfolio_exposure=100000.0,
            max_leverage=2.0,
            max_daily_loss=5000.0
        )
        
        assert limits.max_position_size == 10000.0
        assert limits.max_portfolio_exposure == 100000.0
        assert limits.max_leverage == 2.0
        assert limits.max_daily_loss == 5000.0
    
    def test_risk_metric_creation(self):
        """Test RiskMetric creation"""
        metric = RiskMetric(
            name="VaR",
            value=1000.0,
            threshold=5000.0,
            level=RiskLevel.LOW,
            timestamp=datetime.now()
        )
        
        assert metric.name == "VaR"
        assert metric.value == 1000.0
        assert metric.threshold == 5000.0
        assert metric.level == RiskLevel.LOW
        assert isinstance(metric.timestamp, datetime)
    
    def test_order_request_validation(self):
        """Test OrderRequest validation"""
        order = OrderRequest(
            symbol="AAPL",
            quantity=100,
            price=150.0,
            order_type="MARKET",
            side="BUY"
        )
        
        assert order.symbol == "AAPL"
        assert order.quantity == 100
        assert order.price == 150.0
        assert order.order_type == "MARKET"
        assert order.side == "BUY"
    
    def test_position_creation(self):
        """Test Position creation"""
        position = Position(
            symbol="AAPL",
            quantity=100,
            average_price=150.0,
            market_value=15000.0,
            unrealized_pnl=500.0
        )
        
        assert position.symbol == "AAPL"
        assert position.quantity == 100
        assert position.average_price == 150.0
        assert position.market_value == 15000.0
        assert position.unrealized_pnl == 500.0

class TestVaRCalculator:
    """Test VaR calculator functionality"""
    
    @pytest.fixture
    def sample_returns(self):
        """Generate sample return data"""
        np.random.seed(42)
        dates = pd.date_range(start='2023-01-01', periods=252, freq='D')
        returns = pd.Series(
            np.random.normal(0.001, 0.02, 252),
            index=dates
        )
        return returns
    
    @pytest.fixture
    def var_calculator(self):
        """Create VaR calculator instance"""
        return VaRCalculator()
    
    def test_historical_var(self, var_calculator, sample_returns):
        """Test historical VaR calculation"""
        var = var_calculator.calculate_historical_var(
            returns=sample_returns,
            confidence_level=0.95,
            window=30
        )
        
        assert isinstance(var, float)
        assert var < 0  # VaR should be negative (loss)
        assert -0.1 < var < 0  # Reasonable range
    
    def test_parametric_var(self, var_calculator, sample_returns):
        """Test parametric VaR calculation"""
        var = var_calculator.calculate_parametric_var(
            returns=sample_returns,
            confidence_level=0.95,
            window=30
        )
        
        assert isinstance(var, float)
        assert var < 0  # VaR should be negative
    
    def test_monte_carlo_var(self, var_calculator, sample_returns):
        """Test Monte Carlo VaR calculation"""
        var = var_calculator.calculate_monte_carlo_var(
            returns=sample_returns,
            confidence_level=0.95,
            num_simulations=1000,
            window=30
        )
        
        assert isinstance(var, float)
        assert var < 0  # VaR should be negative
    
    def test_portfolio_var(self, var_calculator):
        """Test portfolio VaR calculation"""
        # Create sample portfolio data
        np.random.seed(42)
        returns = pd.DataFrame({
            'AAPL': np.random.normal(0.001, 0.02, 100),
            'GOOGL': np.random.normal(0.0008, 0.025, 100),
            'MSFT': np.random.normal(0.0012, 0.018, 100)
        })
        
        weights = np.array([0.4, 0.3, 0.3])
        
        var = var_calculator.calculate_portfolio_var(
            returns=returns,
            weights=weights,
            confidence_level=0.95
        )
        
        assert isinstance(var, float)
        assert var < 0  # VaR should be negative
    
    def test_var_summary(self, var_calculator, sample_returns):
        """Test VaR summary statistics"""
        summary = var_calculator.get_var_summary(
            returns=sample_returns,
            confidence_levels=[0.90, 0.95, 0.99]
        )
        
        assert isinstance(summary, dict)
        assert 'historical' in summary
        assert 'parametric' in summary
        assert 'monte_carlo' in summary
        
        for method in summary.values():
            assert len(method) == 3  # Three confidence levels
            assert all(var < 0 for var in method.values())  # All VaRs negative

class TestPositionSizer:
    """Test position sizing functionality"""
    
    @pytest.fixture
    def position_sizer(self):
        """Create position sizer instance"""
        return PositionSizer()
    
    @pytest.fixture
    def sample_data(self):
        """Generate sample market data"""
        np.random.seed(42)
        prices = pd.Series(
            100 + np.cumsum(np.random.normal(0, 1, 100)),
            index=pd.date_range('2023-01-01', periods=100)
        )
        returns = prices.pct_change().dropna()
        
        return {
            'prices': prices,
            'returns': returns,
            'current_price': prices.iloc[-1],
            'volatility': returns.std()
        }
    
    def test_fixed_amount_sizing(self, position_sizer):
        """Test fixed amount position sizing"""
        size = position_sizer.calculate_fixed_amount(
            amount=10000.0,
            price=100.0
        )
        
        assert size == 100  # 10000 / 100
    
    def test_fixed_percentage_sizing(self, position_sizer):
        """Test fixed percentage position sizing"""
        size = position_sizer.calculate_fixed_percentage(
            portfolio_value=100000.0,
            percentage=0.05,
            price=100.0
        )
        
        assert size == 50  # (100000 * 0.05) / 100
    
    def test_kelly_criterion_sizing(self, position_sizer, sample_data):
        """Test Kelly Criterion position sizing"""
        size = position_sizer.calculate_kelly_criterion(
            returns=sample_data['returns'],
            portfolio_value=100000.0,
            price=sample_data['current_price']
        )
        
        assert isinstance(size, int)
        assert size >= 0
    
    def test_volatility_adjusted_sizing(self, position_sizer, sample_data):
        """Test volatility-adjusted position sizing"""
        size = position_sizer.calculate_volatility_adjusted(
            target_volatility=0.02,
            asset_volatility=sample_data['volatility'],
            portfolio_value=100000.0,
            price=sample_data['current_price']
        )
        
        assert isinstance(size, int)
        assert size >= 0
    
    def test_var_based_sizing(self, position_sizer, sample_data):
        """Test VaR-based position sizing"""
        size = position_sizer.calculate_var_based(
            returns=sample_data['returns'],
            max_var_amount=1000.0,
            confidence_level=0.95,
            price=sample_data['current_price']
        )
        
        assert isinstance(size, int)
        assert size >= 0
    
    def test_optimal_position_size(self, position_sizer, sample_data):
        """Test optimal position size calculation"""
        size = position_sizer.calculate_optimal_position_size(
            symbol="AAPL",
            price=sample_data['current_price'],
            returns=sample_data['returns'],
            portfolio_value=100000.0,
            risk_tolerance=0.02
        )
        
        assert isinstance(size, int)
        assert size >= 0

@pytest.mark.asyncio
class TestRealTimeRiskMonitor:
    """Test real-time risk monitoring"""
    
    @pytest.fixture
    async def risk_monitor(self):
        """Create risk monitor instance"""
        config = get_testing_config()
        monitor = RealTimeRiskMonitor(config)
        await monitor.initialize()
        yield monitor
        await monitor.shutdown()
    
    async def test_monitor_initialization(self, risk_monitor):
        """Test monitor initialization"""
        assert risk_monitor.is_running
        assert risk_monitor.risk_metrics == {}
        assert risk_monitor.violation_history == []
    
    async def test_update_risk_metrics(self, risk_monitor):
        """Test risk metrics update"""
        metrics = {
            'portfolio_var': RiskMetric(
                name='VaR',
                value=1000.0,
                threshold=5000.0,
                level=RiskLevel.LOW,
                timestamp=datetime.now()
            )
        }
        
        await risk_monitor.update_risk_metrics('portfolio_1', metrics)
        
        assert 'portfolio_1' in risk_monitor.risk_metrics
        assert 'portfolio_var' in risk_monitor.risk_metrics['portfolio_1']
    
    async def test_check_violations(self, risk_monitor):
        """Test violation checking"""
        # Add metrics that should trigger violations
        metrics = {
            'high_var': RiskMetric(
                name='VaR',
                value=6000.0,  # Above threshold
                threshold=5000.0,
                level=RiskLevel.HIGH,
                timestamp=datetime.now()
            )
        }
        
        await risk_monitor.update_risk_metrics('portfolio_1', metrics)
        violations = await risk_monitor.check_violations('portfolio_1')
        
        assert len(violations) > 0
        assert violations[0].metric_name == 'VaR'
    
    async def test_risk_summary(self, risk_monitor):
        """Test risk summary generation"""
        # Add some metrics
        metrics = {
            'var': RiskMetric(
                name='VaR',
                value=1000.0,
                threshold=5000.0,
                level=RiskLevel.LOW,
                timestamp=datetime.now()
            ),
            'exposure': RiskMetric(
                name='Exposure',
                value=50000.0,
                threshold=100000.0,
                level=RiskLevel.MEDIUM,
                timestamp=datetime.now()
            )
        }
        
        await risk_monitor.update_risk_metrics('portfolio_1', metrics)
        summary = await risk_monitor.get_risk_summary('portfolio_1')
        
        assert isinstance(summary, dict)
        assert 'portfolio_id' in summary
        assert 'metrics' in summary
        assert 'overall_risk_level' in summary

@pytest.mark.asyncio
class TestRiskEngine:
    """Test risk engine functionality"""
    
    @pytest.fixture
    async def risk_engine(self):
        """Create risk engine instance"""
        config = get_testing_config()
        engine = RiskEngine(config)
        
        # Mock external dependencies
        with patch('risk_manager.engine.risk_engine.RiskEngine._get_portfolio_data') as mock_portfolio:
            mock_portfolio.return_value = {
                'positions': [],
                'cash': 100000.0,
                'total_value': 100000.0
            }
            
            await engine.initialize()
            yield engine
            await engine.shutdown()
    
    async def test_engine_initialization(self, risk_engine):
        """Test engine initialization"""
        assert risk_engine.var_calculator is not None
        assert risk_engine.position_sizer is not None
        assert risk_engine.monitor is not None
    
    async def test_order_risk_assessment(self, risk_engine):
        """Test order risk assessment"""
        request = RiskAssessmentRequest(
            order=OrderRequest(
                symbol="AAPL",
                quantity=100,
                price=150.0,
                order_type="MARKET",
                side="BUY"
            ),
            portfolio_id="portfolio_1",
            account_id="account_1"
        )
        
        response = await risk_engine.assess_order_risk(request)
        
        assert isinstance(response, RiskAssessmentResponse)
        assert response.approved is not None
        assert response.risk_level is not None
        assert isinstance(response.violations, list)
    
    async def test_position_size_check(self, risk_engine):
        """Test position size risk check"""
        order = OrderRequest(
            symbol="AAPL",
            quantity=1000000,  # Very large position
            price=150.0,
            order_type="MARKET",
            side="BUY"
        )
        
        violations = await risk_engine._check_position_size_risk(order, {})
        
        # Should have violations for large position
        assert len(violations) > 0
    
    async def test_exposure_check(self, risk_engine):
        """Test exposure risk check"""
        order = OrderRequest(
            symbol="AAPL",
            quantity=100,
            price=150.0,
            order_type="MARKET",
            side="BUY"
        )
        
        portfolio_data = {
            'total_value': 100000.0,
            'positions': []
        }
        
        violations = await risk_engine._check_exposure_risk(order, portfolio_data)
        
        # Should pass for reasonable exposure
        assert len(violations) == 0
    
    async def test_leverage_check(self, risk_engine):
        """Test leverage risk check"""
        order = OrderRequest(
            symbol="AAPL",
            quantity=100,
            price=150.0,
            order_type="MARKET",
            side="BUY"
        )
        
        portfolio_data = {
            'total_value': 100000.0,
            'cash': 50000.0,
            'positions': []
        }
        
        violations = await risk_engine._check_leverage_risk(order, portfolio_data)
        
        # Should pass for reasonable leverage
        assert len(violations) == 0

class TestRiskConfiguration:
    """Test risk configuration"""
    
    def test_config_creation(self):
        """Test configuration creation"""
        config = get_testing_config()
        
        assert config.environment.value == "testing"
        assert config.database.database == "trading_system_test"
        assert config.redis.database == 1
    
    def test_config_validation(self):
        """Test configuration validation"""
        config = get_testing_config()
        errors = config.validate()
        
        assert len(errors) == 0  # Should be valid
    
    def test_invalid_config(self):
        """Test invalid configuration"""
        config = get_testing_config()
        config.risk_limits.max_position_size = -1000.0  # Invalid
        
        errors = config.validate()
        assert len(errors) > 0
        assert any("max_position_size" in error for error in errors)

# Integration tests
@pytest.mark.asyncio
class TestRiskManagerIntegration:
    """Integration tests for the complete risk management system"""
    
    @pytest.fixture
    async def full_system(self):
        """Setup complete risk management system"""
        config = get_testing_config()
        engine = RiskEngine(config)
        
        # Mock external dependencies
        with patch.multiple(
            'risk_manager.engine.risk_engine.RiskEngine',
            _get_portfolio_data=AsyncMock(return_value={
                'positions': [],
                'cash': 100000.0,
                'total_value': 100000.0
            }),
            _get_market_data=AsyncMock(return_value={
                'price': 150.0,
                'volatility': 0.02
            })
        ):
            await engine.initialize()
            yield engine
            await engine.shutdown()
    
    async def test_end_to_end_risk_assessment(self, full_system):
        """Test complete risk assessment workflow"""
        # Create a realistic trading request
        request = RiskAssessmentRequest(
            order=OrderRequest(
                symbol="AAPL",
                quantity=100,
                price=150.0,
                order_type="MARKET",
                side="BUY"
            ),
            portfolio_id="test_portfolio",
            account_id="test_account"
        )
        
        # Assess risk
        response = await full_system.assess_order_risk(request)
        
        # Verify response
        assert isinstance(response, RiskAssessmentResponse)
        assert response.approved is not None
        assert response.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        assert response.approved_quantity >= 0
        assert isinstance(response.violations, list)
        assert isinstance(response.risk_metrics, dict)
    
    async def test_portfolio_risk_monitoring(self, full_system):
        """Test portfolio risk monitoring"""
        portfolio_id = "test_portfolio"
        
        # Get initial risk summary
        summary = await full_system.get_portfolio_risk_summary(portfolio_id)
        
        assert isinstance(summary, dict)
        assert 'portfolio_id' in summary
        assert 'risk_level' in summary
    
    async def test_risk_limit_updates(self, full_system):
        """Test dynamic risk limit updates"""
        new_limits = {
            'max_position_size': 25000.0,
            'max_leverage': 1.5
        }
        
        success = await full_system.update_risk_limits(new_limits)
        assert success
        
        # Verify limits were updated
        config = full_system.config
        assert config.risk_limits.max_position_size == 25000.0
        assert config.risk_limits.max_leverage == 1.5

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])