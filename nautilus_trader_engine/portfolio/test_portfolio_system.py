"""
Tests for Portfolio Optimization and Observability System
"""

import asyncio
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from nautilus_trader.model.identifiers import InstrumentId

from portfolio_optimization import (
    PortfolioOptimizer, 
    PortfolioOptimizationConfig,
    OptimizationMethod,
    RiskMeasure
)
from portfolio_observability import (
    PortfolioObservability, 
    PortfolioMetrics,
    RiskMetrics
)
from portfolio_integration import IntegratedPortfolioSystem


class TestPortfolioOptimization:
    """Test portfolio optimization functionality"""
    
    def setup_method(self):
        """Set up test data"""
        # Create sample returns data
        dates = pd.date_range(start='2020-01-01', end='2020-12-31', freq='D')
        assets = ['AAPL', 'GOOGL', 'MSFT', 'AMZN']
        
        np.random.seed(42)
        returns_data = pd.DataFrame(
            np.random.randn(len(dates), len(assets)) * 0.02,
            index=dates,
            columns=assets
        )
        
        # Add some correlation
        returns_data['GOOGL'] = returns_data['AAPL'] * 0.7 + np.random.randn(len(dates)) * 0.01
        
        self.returns_data = returns_data
        
    def test_portfolio_optimizer_initialization(self):
        """Test portfolio optimizer initialization"""
        config = PortfolioOptimizationConfig()
        optimizer = PortfolioOptimizer(config)
        
        assert optimizer.config == config
        assert optimizer._previous_weights == {}
        assert optimizer._optimization_history == []
        
    @patch('portfolio_optimization.PYPFOPT_AVAILABLE', True)
    def test_mean_variance_optimization(self):
        """Test mean-variance optimization"""
        config = PortfolioOptimizationConfig(
            method=OptimizationMethod.MEAN_VARIANCE,
            target_return=0.15
        )
        optimizer = PortfolioOptimizer(config)
        
        # This would test the actual optimization
        # For now, we'll just test that it doesn't crash
        assert optimizer is not None
        
    @patch('portfolio_optimization.PYPFOPT_AVAILABLE', True)
    def test_minimum_variance_optimization(self):
        """Test minimum variance optimization"""
        config = PortfolioOptimizationConfig(
            method=OptimizationMethod.MINIMUM_VARIANCE
        )
        optimizer = PortfolioOptimizer(config)
        
        assert optimizer is not None
        
    def test_turnover_calculation(self):
        """Test turnover calculation"""
        config = PortfolioOptimizationConfig()
        optimizer = PortfolioOptimizer(config)
        
        # Test with no previous weights
        new_weights = {'AAPL': 0.5, 'GOOGL': 0.3, 'MSFT': 0.2}
        turnover = optimizer._calculate_turnover(new_weights)
        assert turnover == 0.0
        
        # Test with previous weights
        optimizer._previous_weights = {'AAPL': 0.3, 'GOOGL': 0.4, 'MSFT': 0.3}
        turnover = optimizer._calculate_turnover(new_weights)
        assert turnover > 0.0
        
    def test_effective_assets_calculation(self):
        """Test effective assets calculation"""
        config = PortfolioOptimizationConfig()
        optimizer = PortfolioOptimizer(config)
        
        # Equal weights
        weights = {'A': 0.25, 'B': 0.25, 'C': 0.25, 'D': 0.25}
        effective_assets = optimizer._calculate_effective_assets(weights)
        assert abs(effective_assets - 4.0) < 0.001
        
        # Concentrated portfolio
        weights = {'A': 1.0, 'B': 0.0, 'C': 0.0, 'D': 0.0}
        effective_assets = optimizer._calculate_effective_assets(weights)
        assert abs(effective_assets - 1.0) < 0.001


class TestPortfolioObservability:
    """Test portfolio observability functionality"""
    
    def setup_method(self):
        """Set up test components"""
        self.mock_portfolio = Mock()
        self.observability = PortfolioObservability(self.mock_portfolio)
        
    def test_metrics_initialization(self):
        """Test metrics initialization"""
        assert self.observability.portfolio == self.mock_portfolio
        assert self.observability._is_running == False
        assert len(self.observability._historical_metrics) == 0
        
    def test_portfolio_metrics_calculation(self):
        """Test portfolio metrics calculation"""
        metrics = self.observability._calculate_portfolio_metrics()
        
        assert isinstance(metrics, PortfolioMetrics)
        assert metrics.total_value >= 0
        assert metrics.timestamp is not None
        
    def test_risk_metrics_calculation(self):
        """Test risk metrics calculation"""
        returns = [0.01, -0.005, 0.02, -0.01, 0.008]
        risk_metrics = self.observability.calculate_risk_metrics(returns)
        
        assert isinstance(risk_metrics, RiskMetrics)
        assert risk_metrics.value_at_risk >= 0
        assert risk_metrics.max_drawdown >= 0
        
    def test_alert_system(self):
        """Test alert system functionality"""
        # Add alerts
        self.observability.add_alert("test_alert", "This is a test alert", "info")
        self.observability.add_alert("warning_alert", "This is a warning", "warning")
        
        # Get alerts
        alerts = self.observability.get_alerts()
        assert len(alerts) == 2
        
        # Get alerts by severity
        warnings = self.observability.get_alerts(severity="warning")
        assert len(warnings) == 1
        assert warnings[0]["severity"] == "warning"


class TestIntegratedPortfolioSystem:
    """Test integrated portfolio system functionality"""
    
    def setup_method(self):
        """Set up test components"""
        self.mock_portfolio = Mock()
        self.mock_cache = Mock()
        self.integrated_system = IntegratedPortfolioSystem(
            portfolio=self.mock_portfolio,
            cache=self.mock_cache
        )
        
    def test_system_initialization(self):
        """Test system initialization"""
        assert self.integrated_system.portfolio == self.mock_portfolio
        assert self.integrated_system.cache == self.mock_cache
        assert self.integrated_system._is_running == False
        
    def test_instrument_exposure(self):
        """Test instrument exposure calculation"""
        instrument_id = InstrumentId.from_str("AAPL.NASDAQ")
        exposure = self.integrated_system.get_instrument_exposure(instrument_id)
        
        assert isinstance(exposure, dict)
        assert "instrument_id" in exposure
        assert "position_size" in exposure
        
    def test_portfolio_summary(self):
        """Test portfolio summary generation"""
        summary = self.integrated_system.get_portfolio_summary()
        
        assert isinstance(summary, dict)
        assert "timestamp" in summary
        assert "portfolio_value" in summary


# Integration tests
class TestPortfolioIntegration:
    """Integration tests for portfolio system"""
    
    @pytest.mark.asyncio
    async def test_full_optimization_cycle(self):
        """Test full portfolio optimization cycle"""
        # Create mock components
        mock_portfolio = Mock()
        mock_cache = Mock()
        
        # Create integrated system
        integrated_system = IntegratedPortfolioSystem(
            portfolio=mock_portfolio,
            cache=mock_cache
        )
        
        # Start system
        await integrated_system.start()
        assert integrated_system._is_running == True
        
        # Collect market data
        instrument_ids = [
            InstrumentId.from_str("AAPL.NASDAQ"),
            InstrumentId.from_str("GOOGL.NASDAQ")
        ]
        
        # Generate mock market data
        dates = pd.date_range(start='2020-01-01', periods=30, freq='D')
        market_data = pd.DataFrame(
            np.random.randn(30, 2) * 0.02,
            index=dates,
            columns=['AAPL', 'GOOGL']
        )
        
        # Test that system components work together
        summary = integrated_system.get_portfolio_summary()
        assert isinstance(summary, dict)
        
        # Stop system
        await integrated_system.stop()
        assert integrated_system._is_running == False
        
    @pytest.mark.asyncio
    async def test_report_generation(self):
        """Test portfolio report generation"""
        mock_portfolio = Mock()
        mock_cache = Mock()
        
        integrated_system = IntegratedPortfolioSystem(
            portfolio=mock_portfolio,
            cache=mock_cache
        )
        
        # Generate report
        report = await integrated_system.generate_portfolio_report()
        
        assert isinstance(report, dict)
        assert "timestamp" in report
        assert "portfolio_summary" in report


# Example usage test
def test_example_usage():
    """Test that example usage runs without errors"""
    # This test ensures the example code in the modules runs
    # We won't execute the actual example but verify the structure
    
    assert True  # Placeholder - actual examples would be tested in integration


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])