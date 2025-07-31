"""
Tests for Strategy Performance Attribution
"""

import pytest
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from nautilus_trader_engine.backtesting.strategy_performance_attribution import (
    StrategyPerformanceAttributor,
    PerformanceCalculator,
    BenchmarkAnalyzer,
    AttributionAnalyzer,
    FactorModelBuilder,
    Factor,
    AttributionResult,
    PerformanceMetrics,
    BenchmarkComparison,
    PerformanceAttribution,
    AttributionMethod,
    PerformanceMetric
)


class TestFactor:
    """Test Factor class"""
    
    def test_factor_creation(self):
        """Test factor creation"""
        dates = pd.date_range(start='2022-01-01', periods=100, freq='D')
        factor_data = pd.Series(np.random.normal(0, 0.01, 100), index=dates)
        
        factor = Factor(
            name="Market",
            description="Market factor",
            factor_type="market",
            data=factor_data,
            benchmark_exposure=1.0
        )
        
        assert factor.name == "Market"
        assert factor.description == "Market factor"
        assert factor.factor_type == "market"
        assert factor.benchmark_exposure == 1.0
        assert len(factor.data) == 100


class TestFactorModelBuilder:
    """Test factor model building"""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing"""
        np.random.seed(42)
        dates = pd.date_range(start='2022-01-01', periods=252, freq='D')
        
        # Market factor
        market_returns = np.random.normal(0.0008, 0.015, 252)
        
        # Strategy returns with beta = 1.2 and alpha = 0.0002
        strategy_returns = 0.0002 + 1.2 * market_returns + np.random.normal(0, 0.01, 252)
        
        return {
            'strategy_returns': pd.Series(strategy_returns, index=dates),
            'market_factor': Factor(
                name="Market",
                description="Market factor",
                factor_type="market",
                data=pd.Series(market_returns, index=dates)
            )
        }
    
    @pytest.fixture
    def builder(self):
        return FactorModelBuilder()
    
    def test_simple_factor_model(self, builder, sample_data):
        """Test simple factor model building"""
        strategy_returns = sample_data['strategy_returns']
        market_factor = sample_data['market_factor']
        
        model = builder.build_factor_model(strategy_returns, [market_factor])
        
        assert "factor_loadings" in model
        assert "alpha" in model
        assert "r_squared" in model
        assert "specific_risk" in model
        
        # Check that beta is approximately 1.2
        beta = model["factor_loadings"].get("Market", 0)
        assert 1.0 < beta < 1.5  # Should be close to 1.2
        
        # Check that alpha is positive (we added 0.0002)
        assert model["alpha"] > -0.001  # Allow for some noise
        
        # Check R-squared is reasonable
        assert 0.3 < model["r_squared"] < 1.0
    
    def test_multiple_factors(self, builder, sample_data):
        """Test factor model with multiple factors"""
        strategy_returns = sample_data['strategy_returns']
        
        # Create additional factors
        dates = strategy_returns.index
        value_factor = Factor(
            name="Value",
            description="Value factor",
            factor_type="style",
            data=pd.Series(np.random.normal(0.0003, 0.012, len(dates)), index=dates)
        )
        
        size_factor = Factor(
            name="Size",
            description="Size factor",
            factor_type="style",
            data=pd.Series(np.random.normal(-0.0001, 0.008, len(dates)), index=dates)
        )
        
        factors = [sample_data['market_factor'], value_factor, size_factor]
        
        model = builder.build_factor_model(strategy_returns, factors)
        
        assert len(model["factor_loadings"]) == 3
        assert "Market" in model["factor_loadings"]
        assert "Value" in model["factor_loadings"]
        assert "Size" in model["factor_loadings"]
    
    def test_insufficient_data(self, builder):
        """Test with insufficient data"""
        short_returns = pd.Series([0.01, 0.02], index=pd.date_range('2022-01-01', periods=2))
        short_factor = Factor(
            name="Market",
            description="Market factor",
            factor_type="market",
            data=pd.Series([0.005, 0.015], index=pd.date_range('2022-01-01', periods=2))
        )
        
        model = builder.build_factor_model(short_returns, [short_factor])
        
        # Should still return a model structure
        assert "factor_loadings" in model
        assert "alpha" in model


class TestPerformanceCalculator:
    """Test performance metrics calculation"""
    
    @pytest.fixture
    def calculator(self):
        return PerformanceCalculator()
    
    @pytest.fixture
    def sample_returns(self):
        """Create sample returns data"""
        np.random.seed(42)
        dates = pd.date_range(start='2022-01-01', periods=252, freq='D')
        
        # Generate returns with positive drift
        returns = np.random.normal(0.001, 0.02, 252)
        
        return pd.Series(returns, index=dates)
    
    def test_basic_performance_metrics(self, calculator, sample_returns):
        """Test basic performance metrics calculation"""
        metrics = calculator.calculate_performance_metrics(sample_returns)
        
        assert isinstance(metrics, PerformanceMetrics)
        assert metrics.total_return != 0
        assert metrics.annualized_return != 0
        assert metrics.volatility > 0
        assert -3 < metrics.sharpe_ratio < 3  # Reasonable range
        assert metrics.max_drawdown <= 0  # Should be negative
        assert 0 <= metrics.win_rate <= 1
        assert metrics.skewness != 0  # Should have some skewness
        assert metrics.kurtosis != 0  # Should have some kurtosis
    
    def test_benchmark_relative_metrics(self, calculator, sample_returns):
        """Test benchmark-relative metrics"""
        # Create benchmark returns
        benchmark_returns = sample_returns * 0.8 + np.random.normal(0, 0.005, len(sample_returns))
        benchmark_series = pd.Series(benchmark_returns, index=sample_returns.index)
        
        metrics = calculator.calculate_performance_metrics(sample_returns, benchmark_series)
        
        assert metrics.beta != 1.0  # Should be different from 1
        assert metrics.alpha != 0.0  # Should have some alpha
        assert metrics.tracking_error > 0  # Should have tracking error
        assert metrics.information_ratio != 0  # Should have information ratio
        assert metrics.up_capture != 1.0  # Should be different from 1
        assert metrics.down_capture != 1.0  # Should be different from 1
    
    def test_empty_returns(self, calculator):
        """Test with empty returns"""
        empty_returns = pd.Series([], dtype=float)
        metrics = calculator.calculate_performance_metrics(empty_returns)
        
        # Should return empty metrics without crashing
        assert metrics.total_return == 0.0
        assert metrics.volatility == 0.0
        assert metrics.sharpe_ratio == 0.0
    
    def test_risk_metrics(self, calculator, sample_returns):
        """Test risk-specific metrics"""
        metrics = calculator.calculate_performance_metrics(sample_returns)
        
        # VaR should be negative (loss)
        assert metrics.var_95 < 0
        
        # CVaR should be more negative than VaR
        assert metrics.cvar_95 <= metrics.var_95
        
        # Volatility should be positive
        assert metrics.volatility > 0
        
        # Max drawdown should be negative
        assert metrics.max_drawdown <= 0


class TestBenchmarkAnalyzer:
    """Test benchmark analysis"""
    
    @pytest.fixture
    def analyzer(self):
        return BenchmarkAnalyzer()
    
    @pytest.fixture
    def sample_data(self):
        """Create sample strategy and benchmark data"""
        np.random.seed(42)
        dates = pd.date_range(start='2022-01-01', periods=252, freq='D')
        
        benchmark_returns = np.random.normal(0.0008, 0.015, 252)
        strategy_returns = 0.0002 + 1.2 * benchmark_returns + np.random.normal(0, 0.01, 252)
        
        return {
            'strategy': pd.Series(strategy_returns, index=dates),
            'benchmark': pd.Series(benchmark_returns, index=dates)
        }
    
    def test_benchmark_comparison(self, analyzer, sample_data):
        """Test benchmark comparison"""
        comparison = analyzer.compare_to_benchmark(
            sample_data['strategy'],
            sample_data['benchmark'],
            "Test Benchmark"
        )
        
        assert isinstance(comparison, BenchmarkComparison)
        assert comparison.benchmark_name == "Test Benchmark"
        assert -1 <= comparison.correlation <= 1
        assert comparison.beta > 0  # Should be positive
        assert comparison.r_squared >= 0  # Should be non-negative
        assert comparison.tracking_error >= 0  # Should be non-negative
        assert 0 <= comparison.outperformance_ratio <= 1
    
    def test_high_correlation_strategy(self, analyzer):
        """Test with highly correlated strategy"""
        dates = pd.date_range(start='2022-01-01', periods=100, freq='D')
        benchmark_returns = np.random.normal(0.001, 0.02, 100)
        
        # Strategy that's very similar to benchmark
        strategy_returns = benchmark_returns + np.random.normal(0, 0.002, 100)
        
        strategy_series = pd.Series(strategy_returns, index=dates)
        benchmark_series = pd.Series(benchmark_returns, index=dates)
        
        comparison = analyzer.compare_to_benchmark(strategy_series, benchmark_series)
        
        # Should have high correlation and beta close to 1
        assert comparison.correlation > 0.8
        assert 0.8 < comparison.beta < 1.2
        assert comparison.r_squared > 0.6
    
    def test_uncorrelated_strategy(self, analyzer):
        """Test with uncorrelated strategy"""
        dates = pd.date_range(start='2022-01-01', periods=100, freq='D')
        benchmark_returns = np.random.normal(0.001, 0.02, 100)
        
        # Completely independent strategy
        np.random.seed(123)  # Different seed
        strategy_returns = np.random.normal(0.001, 0.02, 100)
        
        strategy_series = pd.Series(strategy_returns, index=dates)
        benchmark_series = pd.Series(benchmark_returns, index=dates)
        
        comparison = analyzer.compare_to_benchmark(strategy_series, benchmark_series)
        
        # Should have low correlation
        assert abs(comparison.correlation) < 0.5
        assert comparison.r_squared < 0.3
    
    def test_insufficient_data(self, analyzer):
        """Test with insufficient data"""
        single_return_strategy = pd.Series([0.01])
        single_return_benchmark = pd.Series([0.005])
        
        comparison = analyzer.compare_to_benchmark(single_return_strategy, single_return_benchmark)
        
        # Should return empty comparison without crashing
        assert comparison.benchmark_name == "Benchmark"
        assert comparison.correlation == 0.0


class TestAttributionAnalyzer:
    """Test attribution analysis"""
    
    @pytest.fixture
    def analyzer(self):
        return AttributionAnalyzer()
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data for attribution analysis"""
        np.random.seed(42)
        dates = pd.date_range(start='2022-01-01', periods=252, freq='D')
        
        # Create factors
        market_returns = np.random.normal(0.0008, 0.015, 252)
        value_returns = np.random.normal(0.0003, 0.012, 252)
        
        # Strategy with exposures to factors
        strategy_returns = (0.0002 +  # Alpha
                          1.2 * market_returns +  # Market exposure
                          0.3 * value_returns +   # Value exposure
                          np.random.normal(0, 0.008, 252))  # Specific risk
        
        # Benchmark (pure market exposure)
        benchmark_returns = market_returns
        
        factors = [
            Factor(
                name="Market",
                description="Market factor",
                factor_type="market",
                data=pd.Series(market_returns, index=dates)
            ),
            Factor(
                name="Value",
                description="Value factor",
                factor_type="style",
                data=pd.Series(value_returns, index=dates)
            )
        ]
        
        return {
            'strategy': pd.Series(strategy_returns, index=dates),
            'benchmark': pd.Series(benchmark_returns, index=dates),
            'factors': factors
        }
    
    def test_factor_based_attribution(self, analyzer, sample_data):
        """Test factor-based attribution"""
        attribution_results = analyzer.perform_attribution_analysis(
            sample_data['strategy'],
            sample_data['benchmark'],
            sample_data['factors'],
            AttributionMethod.FACTOR_MODEL
        )
        
        assert len(attribution_results) > 0
        
        result = attribution_results[0]
        assert isinstance(result, AttributionResult)
        assert result.attribution_method == AttributionMethod.FACTOR_MODEL
        assert "Market" in result.factor_contributions
        assert "Value" in result.factor_contributions
        assert result.selection_effect != 0  # Should have some selection effect
        assert result.total_return != 0
        assert result.excess_return == result.total_return - result.benchmark_return
    
    def test_returns_based_attribution(self, analyzer, sample_data):
        """Test simple returns-based attribution"""
        attribution_results = analyzer.perform_attribution_analysis(
            sample_data['strategy'],
            sample_data['benchmark'],
            [],  # No factors
            AttributionMethod.RETURNS_BASED
        )
        
        assert len(attribution_results) > 0
        
        result = attribution_results[0]
        assert result.attribution_method == AttributionMethod.RETURNS_BASED
        assert len(result.factor_contributions) == 0  # No factors
        assert result.selection_effect == result.excess_return  # All excess return is selection
        assert result.allocation_effect == 0.0
    
    def test_brinson_attribution(self, analyzer, sample_data):
        """Test Brinson attribution"""
        attribution_results = analyzer.perform_attribution_analysis(
            sample_data['strategy'],
            sample_data['benchmark'],
            sample_data['factors'],
            AttributionMethod.BRINSON
        )
        
        assert len(attribution_results) > 0
        
        result = attribution_results[0]
        assert result.attribution_method == AttributionMethod.BRINSON
        assert result.selection_effect != 0
        assert result.allocation_effect != 0
        # Selection + allocation should approximately equal excess return
        total_attribution = result.selection_effect + result.allocation_effect
        assert abs(total_attribution - result.excess_return) < 0.001


class TestStrategyPerformanceAttributor:
    """Test main attribution system"""
    
    @pytest.fixture
    def attributor(self):
        return StrategyPerformanceAttributor()
    
    @pytest.fixture
    def sample_data(self):
        """Create comprehensive sample data"""
        np.random.seed(42)
        dates = pd.date_range(start='2022-01-01', periods=252, freq='D')
        
        # Create factors
        market_returns = np.random.normal(0.0008, 0.015, 252)
        value_returns = np.random.normal(0.0003, 0.012, 252)
        momentum_returns = np.random.normal(0.0001, 0.010, 252)
        
        # Strategy with factor exposures
        strategy_returns = (0.0003 +  # Alpha
                          1.1 * market_returns +  # Market beta
                          0.2 * value_returns +   # Value tilt
                          -0.1 * momentum_returns +  # Momentum tilt
                          np.random.normal(0, 0.008, 252))  # Specific risk
        
        benchmark_returns = market_returns
        
        factors = [
            Factor(
                name="Market",
                description="Market factor",
                factor_type="market",
                data=pd.Series(market_returns, index=dates),
                benchmark_exposure=1.0
            ),
            Factor(
                name="Value",
                description="Value factor",
                factor_type="style",
                data=pd.Series(value_returns, index=dates),
                benchmark_exposure=0.0
            ),
            Factor(
                name="Momentum",
                description="Momentum factor",
                factor_type="style",
                data=pd.Series(momentum_returns, index=dates),
                benchmark_exposure=0.0
            )
        ]
        
        return {
            'strategy': pd.Series(strategy_returns, index=dates),
            'benchmark': pd.Series(benchmark_returns, index=dates),
            'factors': factors
        }
    
    @pytest.mark.asyncio
    async def test_comprehensive_attribution(self, attributor, sample_data):
        """Test comprehensive attribution analysis"""
        attribution = await attributor.analyze_strategy_performance(
            strategy_name="Test Strategy",
            strategy_returns=sample_data['strategy'],
            benchmark_returns=sample_data['benchmark'],
            factors=sample_data['factors'],
            benchmark_names=["Market Index"],
            attribution_method=AttributionMethod.FACTOR_MODEL
        )
        
        assert isinstance(attribution, PerformanceAttribution)
        assert attribution.strategy_name == "Test Strategy"
        assert len(attribution.analysis_period) == 2
        
        # Check performance metrics
        assert isinstance(attribution.performance_metrics, PerformanceMetrics)
        assert attribution.performance_metrics.total_return != 0
        assert attribution.performance_metrics.volatility > 0
        
        # Check benchmark comparisons
        assert len(attribution.benchmark_comparisons) == 1
        benchmark_comp = attribution.benchmark_comparisons[0]
        assert benchmark_comp.benchmark_name == "Market Index"
        assert benchmark_comp.beta > 0
        
        # Check factor exposures
        assert "Market" in attribution.factor_exposures
        assert "Value" in attribution.factor_exposures
        assert "Momentum" in attribution.factor_exposures
        
        # Market exposure should be close to 1.1
        market_exposure = attribution.factor_exposures["Market"]
        assert 0.8 < market_exposure < 1.4
        
        # Check risk decomposition
        assert "total_risk" in attribution.risk_decomposition
        assert "systematic_risk" in attribution.risk_decomposition
        assert "specific_risk" in attribution.risk_decomposition
        
        # Check attribution results
        assert len(attribution.attribution_results) > 0
        attr_result = attribution.attribution_results[0]
        assert attr_result.excess_return != 0
        assert len(attr_result.factor_contributions) == 3
    
    @pytest.mark.asyncio
    async def test_attribution_without_benchmark(self, attributor, sample_data):
        """Test attribution without benchmark"""
        attribution = await attributor.analyze_strategy_performance(
            strategy_name="Test Strategy",
            strategy_returns=sample_data['strategy'],
            benchmark_returns=None,
            factors=None
        )
        
        assert isinstance(attribution, PerformanceAttribution)
        assert len(attribution.benchmark_comparisons) == 0
        assert len(attribution.factor_exposures) == 0
        assert len(attribution.attribution_results) == 0
        
        # Should still have performance metrics
        assert isinstance(attribution.performance_metrics, PerformanceMetrics)
    
    @pytest.mark.asyncio
    async def test_attribution_with_single_factor(self, attributor, sample_data):
        """Test attribution with single factor"""
        single_factor = [sample_data['factors'][0]]  # Just market factor
        
        attribution = await attributor.analyze_strategy_performance(
            strategy_name="Single Factor Strategy",
            strategy_returns=sample_data['strategy'],
            benchmark_returns=sample_data['benchmark'],
            factors=single_factor
        )
        
        assert len(attribution.factor_exposures) == 1
        assert "Market" in attribution.factor_exposures
        
        if attribution.attribution_results:
            attr_result = attribution.attribution_results[0]
            assert len(attr_result.factor_contributions) == 1
            assert "Market" in attr_result.factor_contributions
    
    @pytest.mark.asyncio
    async def test_risk_decomposition(self, attributor, sample_data):
        """Test risk decomposition calculation"""
        attribution = await attributor.analyze_strategy_performance(
            strategy_name="Risk Test Strategy",
            strategy_returns=sample_data['strategy'],
            benchmark_returns=sample_data['benchmark'],
            factors=sample_data['factors']
        )
        
        risk_decomp = attribution.risk_decomposition
        
        assert "total_risk" in risk_decomp
        assert "systematic_risk" in risk_decomp
        assert "specific_risk" in risk_decomp
        
        # Total risk should be approximately equal to systematic + specific
        total_risk = risk_decomp["total_risk"]
        systematic_risk = risk_decomp["systematic_risk"]
        specific_risk = risk_decomp["specific_risk"]
        
        # Check that risks are non-negative
        assert total_risk >= 0
        assert systematic_risk >= 0
        assert specific_risk >= 0
        
        # Check percentage decomposition if available
        if "systematic_risk_pct" in risk_decomp:
            sys_pct = risk_decomp["systematic_risk_pct"]
            spec_pct = risk_decomp["specific_risk_pct"]
            assert 0 <= sys_pct <= 1
            assert 0 <= spec_pct <= 1
            assert abs(sys_pct + spec_pct - 1.0) < 0.01  # Should sum to ~1


@pytest.mark.asyncio
async def test_integration_scenario():
    """Test complete integration scenario"""
    print("Running strategy performance attribution integration test...")
    
    # Create realistic sample data
    np.random.seed(42)
    dates = pd.date_range(start='2021-01-01', end='2022-12-31', freq='D')
    
    # Market factor (broad market)
    market_returns = np.random.normal(0.0008, 0.016, len(dates))
    
    # Style factors
    value_returns = np.random.normal(0.0002, 0.012, len(dates))
    growth_returns = -0.5 * value_returns + np.random.normal(0, 0.008, len(dates))
    momentum_returns = np.random.normal(0.0001, 0.011, len(dates))
    size_returns = np.random.normal(-0.0001, 0.009, len(dates))
    
    # Create a strategy with specific factor exposures
    strategy_returns = (
        0.0004 +  # Alpha (40 bps annually)
        1.15 * market_returns +  # Market beta = 1.15
        0.25 * value_returns +   # Value tilt
        -0.10 * growth_returns + # Anti-growth tilt
        0.15 * momentum_returns + # Momentum tilt
        -0.05 * size_returns +   # Large cap tilt
        np.random.normal(0, 0.007, len(dates))  # Specific risk
    )
    
    # Benchmark is pure market exposure
    benchmark_returns = market_returns
    
    # Create factor objects
    factors = [
        Factor(
            name="Market",
            description="Broad market factor",
            factor_type="market",
            data=pd.Series(market_returns, index=dates),
            benchmark_exposure=1.0
        ),
        Factor(
            name="Value",
            description="Value vs Growth factor",
            factor_type="style",
            data=pd.Series(value_returns, index=dates),
            benchmark_exposure=0.0
        ),
        Factor(
            name="Growth",
            description="Growth factor",
            factor_type="style",
            data=pd.Series(growth_returns, index=dates),
            benchmark_exposure=0.0
        ),
        Factor(
            name="Momentum",
            description="Price momentum factor",
            factor_type="style",
            data=pd.Series(momentum_returns, index=dates),
            benchmark_exposure=0.0
        ),
        Factor(
            name="Size",
            description="Size factor (small vs large)",
            factor_type="style",
            data=pd.Series(size_returns, index=dates),
            benchmark_exposure=0.0
        )
    ]
    
    # Create pandas series
    strategy_series = pd.Series(strategy_returns, index=dates, name='Strategy')
    benchmark_series = pd.Series(benchmark_returns, index=dates, name='Benchmark')
    
    print(f"Generated {len(dates)} days of data")
    print(f"Strategy total return: {(1 + strategy_series).prod() - 1:.2%}")
    print(f"Benchmark total return: {(1 + benchmark_series).prod() - 1:.2%}")
    
    # Perform attribution analysis
    attributor = StrategyPerformanceAttributor()
    
    attribution = await attributor.analyze_strategy_performance(
        strategy_name="Integration Test Strategy",
        strategy_returns=strategy_series,
        benchmark_returns=benchmark_series,
        factors=factors,
        benchmark_names=["Market Benchmark"],
        attribution_method=AttributionMethod.FACTOR_MODEL
    )
    
    # Verify results
    assert isinstance(attribution, PerformanceAttribution)
    assert attribution.strategy_name == "Integration Test Strategy"
    
    # Check performance metrics
    metrics = attribution.performance_metrics
    assert metrics.total_return != 0
    assert metrics.volatility > 0
    assert metrics.sharpe_ratio != 0
    assert metrics.max_drawdown <= 0
    assert 0 <= metrics.win_rate <= 1
    
    # Check benchmark comparison
    assert len(attribution.benchmark_comparisons) == 1
    benchmark_comp = attribution.benchmark_comparisons[0]
    assert benchmark_comp.benchmark_name == "Market Benchmark"
    assert 1.0 < benchmark_comp.beta < 1.3  # Should be close to 1.15
    assert benchmark_comp.alpha != 0  # Should have some alpha
    assert benchmark_comp.correlation > 0.7  # Should be highly correlated
    
    # Check factor exposures
    assert len(attribution.factor_exposures) == 5
    assert "Market" in attribution.factor_exposures
    assert "Value" in attribution.factor_exposures
    
    # Market exposure should be close to 1.15
    market_exposure = attribution.factor_exposures["Market"]
    assert 1.0 < market_exposure < 1.4
    
    # Value exposure should be positive (around 0.25)
    value_exposure = attribution.factor_exposures["Value"]
    assert value_exposure > 0
    
    # Check attribution results
    assert len(attribution.attribution_results) > 0
    attr_result = attribution.attribution_results[0]
    
    assert attr_result.total_return != 0
    assert attr_result.benchmark_return != 0
    assert attr_result.excess_return == attr_result.total_return - attr_result.benchmark_return
    assert len(attr_result.factor_contributions) == 5
    
    # Check risk decomposition
    risk_decomp = attribution.risk_decomposition
    assert "total_risk" in risk_decomp
    assert "systematic_risk" in risk_decomp
    assert "specific_risk" in risk_decomp
    
    total_risk = risk_decomp["total_risk"]
    systematic_risk = risk_decomp["systematic_risk"]
    specific_risk = risk_decomp["specific_risk"]
    
    assert total_risk > 0
    assert systematic_risk >= 0
    assert specific_risk >= 0
    
    # Performance summary should contain key metrics
    summary = attribution.performance_summary
    assert "total_return" in summary
    assert "sharpe_ratio" in summary
    assert "alpha" in summary
    assert "beta" in summary
    
    print(f"Integration test completed successfully!")
    print(f"Strategy alpha: {benchmark_comp.alpha:.4f}")
    print(f"Strategy beta: {benchmark_comp.beta:.3f}")
    print(f"Information ratio: {benchmark_comp.information_ratio:.3f}")
    print(f"Market exposure: {market_exposure:.3f}")
    print(f"Value exposure: {value_exposure:.3f}")
    print(f"Total risk: {total_risk:.2%}")
    print(f"Systematic risk: {systematic_risk:.2%}")
    print(f"Specific risk: {specific_risk:.2%}")


if __name__ == "__main__":
    # Run the integration test
    asyncio.run(test_integration_scenario())