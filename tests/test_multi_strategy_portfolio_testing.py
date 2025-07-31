"""
Tests for Multi-Strategy Portfolio Testing
"""

import pytest
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from nautilus_trader_engine.backtesting.multi_strategy_portfolio_testing import (
    MultiStrategyPortfolioTester,
    CorrelationAnalyzer,
    PortfolioOptimizer,
    PerformanceCalculator,
    RiskAttributor,
    Strategy,
    PortfolioConstraints,
    AllocationResult,
    PortfolioPerformance,
    CorrelationAnalysis,
    RiskAttribution,
    PortfolioTestResult,
    AllocationMethod,
    RebalancingFrequency
)


class TestStrategy:
    """Test Strategy class"""
    
    def test_strategy_creation(self):
        """Test strategy creation"""
        dates = pd.date_range(start='2022-01-01', periods=100, freq='D')
        returns = pd.Series(np.random.normal(0.001, 0.02, 100), index=dates)
        
        strategy = Strategy(
            name="Test Strategy",
            returns=returns,
            description="Test strategy description",
            strategy_type="momentum",
            target_allocation=0.25,
            min_allocation=0.1,
            max_allocation=0.4,
            risk_budget=0.3
        )
        
        assert strategy.name == "Test Strategy"
        assert strategy.description == "Test strategy description"
        assert strategy.strategy_type == "momentum"
        assert strategy.target_allocation == 0.25
        assert strategy.min_allocation == 0.1
        assert strategy.max_allocation == 0.4
        assert strategy.risk_budget == 0.3
        assert len(strategy.returns) == 100


class TestCorrelationAnalyzer:
    """Test correlation analysis"""
    
    @pytest.fixture
    def analyzer(self):
        return CorrelationAnalyzer()
    
    @pytest.fixture
    def sample_strategies(self):
        """Create sample strategies for testing"""
        np.random.seed(42)
        dates = pd.date_range(start='2022-01-01', periods=252, freq='D')
        
        # Strategy 1: Independent returns
        returns1 = np.random.normal(0.001, 0.02, 252)
        
        # Strategy 2: Correlated with strategy 1
        returns2 = 0.7 * returns1 + 0.3 * np.random.normal(0.001, 0.02, 252)
        
        # Strategy 3: Anti-correlated with strategy 1
        returns3 = -0.5 * returns1 + np.random.normal(0.001, 0.02, 252)
        
        # Strategy 4: Independent
        np.random.seed(123)
        returns4 = np.random.normal(0.0008, 0.015, 252)
        
        strategies = [
            Strategy("Strategy1", pd.Series(returns1, index=dates)),
            Strategy("Strategy2", pd.Series(returns2, index=dates)),
            Strategy("Strategy3", pd.Series(returns3, index=dates)),
            Strategy("Strategy4", pd.Series(returns4, index=dates))
        ]
        
        return strategies
    
    def test_correlation_analysis(self, analyzer, sample_strategies):
        """Test basic correlation analysis"""
        analysis = analyzer.analyze_correlations(sample_strategies)
        
        assert isinstance(analysis, CorrelationAnalysis)
        assert analysis.correlation_matrix.shape == (4, 4)
        assert -1 <= analysis.average_correlation <= 1
        assert -1 <= analysis.max_correlation <= 1
        assert -1 <= analysis.min_correlation <= 1
        assert analysis.diversification_ratio > 0
        assert analysis.effective_strategies > 0
    
    def test_high_correlation_detection(self, analyzer):
        """Test detection of highly correlated strategies"""
        dates = pd.date_range(start='2022-01-01', periods=100, freq='D')
        
        # Create highly correlated strategies
        base_returns = np.random.normal(0.001, 0.02, 100)
        
        strategies = [
            Strategy("Strategy1", pd.Series(base_returns, index=dates)),
            Strategy("Strategy2", pd.Series(base_returns + np.random.normal(0, 0.005, 100), index=dates)),
            Strategy("Strategy3", pd.Series(base_returns + np.random.normal(0, 0.005, 100), index=dates))
        ]
        
        analysis = analyzer.analyze_correlations(strategies)
        
        # Should detect high correlations
        assert analysis.max_correlation > 0.8
        assert analysis.average_correlation > 0.5
        assert len(analysis.correlation_clusters) > 0
    
    def test_empty_strategies(self, analyzer):
        """Test with empty strategies list"""
        analysis = analyzer.analyze_correlations([])
        
        assert isinstance(analysis, CorrelationAnalysis)
        assert analysis.correlation_matrix.empty
        assert analysis.average_correlation == 0.0
        assert analysis.diversification_ratio == 1.0
    
    def test_single_strategy(self, analyzer):
        """Test with single strategy"""
        dates = pd.date_range(start='2022-01-01', periods=100, freq='D')
        returns = np.random.normal(0.001, 0.02, 100)
        
        strategy = Strategy("SingleStrategy", pd.Series(returns, index=dates))
        analysis = analyzer.analyze_correlations([strategy])
        
        assert analysis.correlation_matrix.shape == (1, 1)
        assert analysis.correlation_matrix.iloc[0, 0] == 1.0  # Self-correlation
        assert analysis.diversification_ratio == 1.0
    
    def test_insufficient_data(self, analyzer):
        """Test with insufficient data"""
        dates = pd.date_range(start='2022-01-01', periods=5, freq='D')
        returns = np.random.normal(0.001, 0.02, 5)
        
        strategy = Strategy("TestStrategy", pd.Series(returns, index=dates))
        analysis = analyzer.analyze_correlations([strategy])
        
        # Should return empty analysis for insufficient data
        assert analysis.correlation_matrix.empty or len(analysis.correlation_matrix) == 0


class TestPortfolioOptimizer:
    """Test portfolio optimization"""
    
    @pytest.fixture
    def optimizer(self):
        return PortfolioOptimizer()
    
    @pytest.fixture
    def sample_strategies(self):
        """Create sample strategies for testing"""
        np.random.seed(42)
        dates = pd.date_range(start='2022-01-01', periods=252, freq='D')
        
        strategies = []
        for i in range(4):
            returns = np.random.normal(0.001, 0.02, 252)
            strategy = Strategy(f"Strategy{i+1}", pd.Series(returns, index=dates))
            strategies.append(strategy)
        
        return strategies
    
    def test_equal_weight_allocation(self, optimizer, sample_strategies):
        """Test equal weight allocation"""
        result = optimizer.optimize_portfolio(
            sample_strategies, 
            AllocationMethod.EQUAL_WEIGHT
        )
        
        assert isinstance(result, AllocationResult)
        assert result.optimization_success
        assert len(result.weights) == 4
        
        # Check equal weights
        for weight in result.weights.values():
            assert abs(weight - 0.25) < 1e-6
        
        # Check weights sum to 1
        assert abs(sum(result.weights.values()) - 1.0) < 1e-6
    
    def test_risk_parity_allocation(self, optimizer, sample_strategies):
        """Test risk parity allocation"""
        result = optimizer.optimize_portfolio(
            sample_strategies, 
            AllocationMethod.RISK_PARITY
        )
        
        assert isinstance(result, AllocationResult)
        assert len(result.weights) == 4
        assert abs(sum(result.weights.values()) - 1.0) < 1e-6
        assert result.expected_return >= 0
        assert result.expected_volatility >= 0
    
    def test_minimum_variance_allocation(self, optimizer, sample_strategies):
        """Test minimum variance allocation"""
        result = optimizer.optimize_portfolio(
            sample_strategies, 
            AllocationMethod.MINIMUM_VARIANCE
        )
        
        assert isinstance(result, AllocationResult)
        assert len(result.weights) == 4
        assert abs(sum(result.weights.values()) - 1.0) < 1e-6
    
    def test_constraints_application(self, optimizer, sample_strategies):
        """Test portfolio constraints"""
        constraints = PortfolioConstraints(
            min_weight=0.1,
            max_weight=0.4,
            max_concentration=0.5
        )
        
        result = optimizer.optimize_portfolio(
            sample_strategies, 
            AllocationMethod.EQUAL_WEIGHT,
            constraints
        )
        
        assert isinstance(result, AllocationResult)
        # Equal weight (0.25) should violate min_weight constraint (0.1) but satisfy max_weight (0.4)
        # Since 0.25 > 0.1 and 0.25 < 0.4, constraints should be satisfied
        assert result.constraints_satisfied
    
    def test_empty_strategies(self, optimizer):
        """Test with empty strategies"""
        result = optimizer.optimize_portfolio([], AllocationMethod.EQUAL_WEIGHT)
        
        assert isinstance(result, AllocationResult)
        assert not result.optimization_success
        assert len(result.weights) == 0


class TestPerformanceCalculator:
    """Test performance calculation"""
    
    @pytest.fixture
    def calculator(self):
        return PerformanceCalculator()
    
    def test_performance_calculation(self, calculator):
        """Test basic performance calculation"""
        # Create sample returns
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0.001, 0.02, 252))
        
        performance = calculator.calculate_portfolio_performance(returns)
        
        assert isinstance(performance, PortfolioPerformance)
        assert performance.total_return != 0
        assert performance.volatility > 0
        assert performance.win_rate >= 0 and performance.win_rate <= 1
        assert performance.max_drawdown <= 0
    
    def test_positive_returns_performance(self, calculator):
        """Test performance with consistently positive returns"""
        returns = pd.Series([0.01] * 100)  # 1% daily returns
        
        performance = calculator.calculate_portfolio_performance(returns)
        
        assert performance.total_return > 0
        assert performance.annualized_return > 0
        assert performance.max_drawdown == 0  # No drawdowns
        assert performance.win_rate == 1.0  # All positive
    
    def test_empty_returns(self, calculator):
        """Test with empty returns"""
        returns = pd.Series(dtype=float)
        
        performance = calculator.calculate_portfolio_performance(returns)
        
        assert isinstance(performance, PortfolioPerformance)
        assert performance.total_return == 0
        assert performance.volatility == 0
        assert performance.sharpe_ratio == 0


class TestRiskAttributor:
    """Test risk attribution"""
    
    @pytest.fixture
    def attributor(self):
        return RiskAttributor()
    
    @pytest.fixture
    def sample_strategies_and_weights(self):
        """Create sample strategies and weights"""
        dates = pd.date_range(start='2022-01-01', periods=252, freq='D')
        
        strategies = []
        for i in range(3):
            returns = np.random.normal(0.001, 0.02, 252)
            strategy = Strategy(f"Strategy{i+1}", pd.Series(returns, index=dates))
            strategies.append(strategy)
        
        weights = {"Strategy1": 0.4, "Strategy2": 0.35, "Strategy3": 0.25}
        
        return strategies, weights
    
    def test_risk_attribution_calculation(self, attributor, sample_strategies_and_weights):
        """Test basic risk attribution calculation"""
        strategies, weights = sample_strategies_and_weights
        
        attribution = attributor.calculate_risk_attribution(strategies, weights)
        
        assert isinstance(attribution, RiskAttribution)
        assert len(attribution.strategy_risk_contributions) == 3
        assert len(attribution.strategy_risk_percentages) == 3
        
        # Risk percentages should sum to approximately 1
        total_risk_percentage = sum(attribution.strategy_risk_percentages.values())
        assert abs(total_risk_percentage - 1.0) < 0.1
    
    def test_equal_weight_risk_attribution(self, attributor):
        """Test risk attribution with equal weights"""
        dates = pd.date_range(start='2022-01-01', periods=100, freq='D')
        
        # Create strategies with different volatilities
        strategies = [
            Strategy("LowVol", pd.Series(np.random.normal(0.001, 0.01, 100), index=dates)),
            Strategy("HighVol", pd.Series(np.random.normal(0.001, 0.03, 100), index=dates))
        ]
        
        weights = {"LowVol": 0.5, "HighVol": 0.5}
        
        attribution = attributor.calculate_risk_attribution(strategies, weights)
        
        # High volatility strategy should contribute more risk
        assert attribution.strategy_risk_contributions["HighVol"] > attribution.strategy_risk_contributions["LowVol"]
    
    def test_empty_strategies_risk_attribution(self, attributor):
        """Test with empty strategies"""
        attribution = attributor.calculate_risk_attribution([], {})
        
        assert isinstance(attribution, RiskAttribution)
        assert len(attribution.strategy_risk_contributions) == 0
        assert attribution.diversification_benefit == 0.0


class TestMultiStrategyPortfolioTester:
    """Test main portfolio tester"""
    
    @pytest.fixture
    def tester(self):
        return MultiStrategyPortfolioTester()
    
    @pytest.fixture
    def sample_strategies(self):
        """Create sample strategies for testing"""
        np.random.seed(42)
        dates = pd.date_range(start='2022-01-01', periods=252, freq='D')
        
        strategies = []
        for i in range(3):
            returns = np.random.normal(0.001, 0.02, 252)
            strategy = Strategy(
                name=f"Strategy{i+1}",
                returns=pd.Series(returns, index=dates),
                description=f"Test strategy {i+1}",
                strategy_type="test"
            )
            strategies.append(strategy)
        
        return strategies
    
    @pytest.mark.asyncio
    async def test_portfolio_testing(self, tester, sample_strategies):
        """Test complete portfolio testing"""
        result = await tester.test_portfolio(
            portfolio_name="TestPortfolio",
            strategies=sample_strategies,
            allocation_method=AllocationMethod.EQUAL_WEIGHT,
            rebalancing_frequency=RebalancingFrequency.MONTHLY
        )
        
        assert isinstance(result, PortfolioTestResult)
        assert result.portfolio_name == "TestPortfolio"
        assert len(result.strategies) == 3
        assert isinstance(result.allocation_result, AllocationResult)
        assert isinstance(result.portfolio_performance, PortfolioPerformance)
        assert isinstance(result.correlation_analysis, CorrelationAnalysis)
        assert isinstance(result.risk_attribution, RiskAttribution)
    
    @pytest.mark.asyncio
    async def test_different_allocation_methods(self, tester, sample_strategies):
        """Test different allocation methods"""
        methods = [
            AllocationMethod.EQUAL_WEIGHT,
            AllocationMethod.RISK_PARITY,
            AllocationMethod.MINIMUM_VARIANCE
        ]
        
        for method in methods:
            result = await tester.test_portfolio(
                portfolio_name=f"Portfolio_{method.value}",
                strategies=sample_strategies,
                allocation_method=method
            )
            
            assert isinstance(result, PortfolioTestResult)
            assert result.allocation_result.allocation_method == method
    
    @pytest.mark.asyncio
    async def test_empty_strategies(self, tester):
        """Test with empty strategies"""
        result = await tester.test_portfolio(
            portfolio_name="EmptyPortfolio",
            strategies=[]
        )
        
        assert isinstance(result, PortfolioTestResult)
        assert len(result.strategies) == 0
        assert not result.allocation_result.optimization_success
    
    @pytest.mark.asyncio
    async def test_single_strategy(self, tester):
        """Test with single strategy"""
        dates = pd.date_range(start='2022-01-01', periods=100, freq='D')
        returns = np.random.normal(0.001, 0.02, 100)
        
        strategy = Strategy("SingleStrategy", pd.Series(returns, index=dates))
        
        result = await tester.test_portfolio(
            portfolio_name="SingleStrategyPortfolio",
            strategies=[strategy]
        )
        
        assert isinstance(result, PortfolioTestResult)
        assert len(result.strategies) == 1
        assert result.allocation_result.weights["SingleStrategy"] == 1.0


class TestIntegration:
    """Integration tests for the complete system"""
    
    @pytest.mark.asyncio
    async def test_complete_workflow(self):
        """Test complete multi-strategy portfolio testing workflow"""
        # Create realistic test data
        np.random.seed(42)
        dates = pd.date_range(start='2022-01-01', periods=252, freq='D')
        
        # Create strategies with different characteristics
        momentum_returns = np.random.normal(0.0008, 0.018, 252)
        mean_reversion_returns = np.random.normal(0.0006, 0.015, 252)
        # Add negative correlation
        mean_reversion_returns = mean_reversion_returns - 0.3 * momentum_returns + np.random.normal(0, 0.01, 252)
        
        strategies = [
            Strategy(
                name="Momentum",
                returns=pd.Series(momentum_returns, index=dates),
                description="Momentum strategy",
                strategy_type="momentum",
                risk_budget=0.6
            ),
            Strategy(
                name="MeanReversion", 
                returns=pd.Series(mean_reversion_returns, index=dates),
                description="Mean reversion strategy",
                strategy_type="mean_reversion",
                risk_budget=0.4
            )
        ]
        
        # Test portfolio
        tester = MultiStrategyPortfolioTester()
        
        result = await tester.test_portfolio(
            portfolio_name="IntegrationTestPortfolio",
            strategies=strategies,
            allocation_method=AllocationMethod.RISK_PARITY,
            rebalancing_frequency=RebalancingFrequency.MONTHLY,
            transaction_cost_bps=5.0
        )
        
        # Verify all components work together
        assert isinstance(result, PortfolioTestResult)
        assert result.portfolio_name == "IntegrationTestPortfolio"
        assert len(result.strategies) == 2
        
        # Check allocation
        assert result.allocation_result.optimization_success
        assert abs(sum(result.allocation_result.weights.values()) - 1.0) < 1e-6
        
        # Check performance metrics
        assert isinstance(result.portfolio_performance.total_return, float)
        assert result.portfolio_performance.volatility > 0
        
        # Check correlation analysis
        assert result.correlation_analysis.correlation_matrix.shape == (2, 2)
        
        # Check risk attribution
        assert len(result.risk_attribution.strategy_risk_contributions) == 2
        
        # Check transaction costs
        assert result.transaction_costs >= 0
        
        print(f"Integration test completed successfully!")
        print(f"Portfolio return: {result.portfolio_performance.total_return:.2%}")
        print(f"Portfolio volatility: {result.portfolio_performance.volatility:.2%}")
        print(f"Sharpe ratio: {result.portfolio_performance.sharpe_ratio:.3f}")
        print(f"Transaction costs: {result.transaction_costs:.4f}")


if __name__ == "__main__":
    pytest.main([__file__])