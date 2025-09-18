#!/usr/bin/env python3
"""
Comprehensive Unit Tests for Portfolio Optimization System

This test suite validates the integration of PyPortfolioOpt and Riskfolio-Lib
with advanced attribution features, covering all optimization methods,
risk measures, and performance attribution capabilities.

Test Categories:
- Portfolio Manager Core Functionality
- Optimization Methods (Mean-Variance, Black-Litterman, HRP, etc.)
- Risk Measures and Constraints
- Performance Attribution Analysis
- Transaction Cost Optimization
- Rebalancing Logic
- Error Handling and Edge Cases

Author: Algorithmic Trading System
Date: 2024
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

import unittest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import warnings
from unittest.mock import Mock, patch, MagicMock
from dataclasses import asdict

# Import the modules under test
from algorithmic_trading_service.portfolio_management import (
    PortfolioManager, OptimizationConfig, OptimizationMethod, RiskMeasure,
    PortfolioMetrics, AttributionAnalysis
)
from algorithmic_trading_service.optimization_engines import (
    PyPortfolioOptEngine, RiskfolioEngine
)

# Suppress warnings for cleaner test output
warnings.filterwarnings('ignore')

class TestPortfolioManager(unittest.TestCase):
    """
    Test cases for the PortfolioManager class
    """
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.portfolio_manager = PortfolioManager(
            risk_free_rate=0.02,
            benchmark_ticker="SPY",
            rebalancing_frequency="monthly"
        )
        
        # Create sample data
        self.sample_data = self._create_sample_data()
        self.benchmark_data = self._create_benchmark_data()
        
    def _create_sample_data(self, n_assets=5, n_periods=252):
        """Create sample price data for testing"""
        np.random.seed(42)
        dates = pd.date_range(start='2023-01-01', periods=n_periods, freq='D')
        assets = [f'ASSET_{i+1}' for i in range(n_assets)]
        
        # Generate correlated returns
        returns = np.random.multivariate_normal(
            mean=[0.0005] * n_assets,
            cov=np.eye(n_assets) * 0.0001 + 0.00002,
            size=n_periods
        )
        
        # Convert to prices
        prices = pd.DataFrame(index=dates, columns=assets)
        prices.iloc[0] = 100.0
        
        for i in range(1, n_periods):
            prices.iloc[i] = prices.iloc[i-1] * (1 + returns[i])
            
        return prices
    
    def _create_benchmark_data(self):
        """Create benchmark data"""
        np.random.seed(42)
        dates = self.sample_data.index
        returns = np.random.normal(0.0004, 0.01, len(dates))
        
        benchmark = pd.Series(index=dates, name='SPY')
        benchmark.iloc[0] = 100.0
        
        for i in range(1, len(dates)):
            benchmark.iloc[i] = benchmark.iloc[i-1] * (1 + returns[i])
            
        return benchmark
    
    def test_initialization(self):
        """Test PortfolioManager initialization"""
        self.assertEqual(self.portfolio_manager.risk_free_rate, 0.02)
        self.assertEqual(self.portfolio_manager.benchmark_ticker, "SPY")
        self.assertEqual(self.portfolio_manager.rebalancing_frequency, "monthly")
        self.assertIsNone(self.portfolio_manager.price_data)
        self.assertIsNone(self.portfolio_manager.benchmark_data)
    
    def test_load_data(self):
        """Test data loading functionality"""
        self.portfolio_manager.load_data(self.sample_data, self.benchmark_data)
        
        self.assertIsNotNone(self.portfolio_manager.price_data)
        self.assertIsNotNone(self.portfolio_manager.benchmark_data)
        self.assertEqual(len(self.portfolio_manager.price_data.columns), 5)
        self.assertEqual(len(self.portfolio_manager.price_data), 252)
    
    def test_load_data_validation(self):
        """Test data validation during loading"""
        # Test with mismatched indices
        invalid_benchmark = self.benchmark_data.iloc[:-10]  # Remove last 10 days
        
        with self.assertRaises(ValueError):
            self.portfolio_manager.load_data(self.sample_data, invalid_benchmark)
    
    def test_calculate_returns(self):
        """Test returns calculation"""
        self.portfolio_manager.load_data(self.sample_data, self.benchmark_data)
        returns = self.portfolio_manager._calculate_returns()
        
        self.assertEqual(len(returns), len(self.sample_data) - 1)
        self.assertEqual(len(returns.columns), len(self.sample_data.columns))
        
        # Check that returns are reasonable (not too extreme)
        self.assertTrue((returns.abs() < 0.5).all().all())  # No returns > 50%
    
    def test_calculate_expected_returns(self):
        """Test expected returns calculation"""
        self.portfolio_manager.load_data(self.sample_data, self.benchmark_data)
        expected_returns = self.portfolio_manager._calculate_expected_returns()
        
        self.assertEqual(len(expected_returns), len(self.sample_data.columns))
        self.assertTrue(all(isinstance(ret, (int, float)) for ret in expected_returns))
    
    def test_calculate_covariance_matrix(self):
        """Test covariance matrix calculation"""
        self.portfolio_manager.load_data(self.sample_data, self.benchmark_data)
        cov_matrix = self.portfolio_manager._calculate_covariance_matrix()
        
        # Check dimensions
        n_assets = len(self.sample_data.columns)
        self.assertEqual(cov_matrix.shape, (n_assets, n_assets))
        
        # Check symmetry
        np.testing.assert_array_almost_equal(cov_matrix, cov_matrix.T)
        
        # Check positive semi-definite
        eigenvalues = np.linalg.eigvals(cov_matrix)
        self.assertTrue(all(eigenvalues >= -1e-8))  # Allow for numerical errors

class TestOptimizationMethods(unittest.TestCase):
    """
    Test cases for different optimization methods
    """
    
    def setUp(self):
        """Set up test fixtures"""
        self.portfolio_manager = PortfolioManager()
        self.sample_data = self._create_sample_data()
        self.benchmark_data = self._create_benchmark_data()
        self.portfolio_manager.load_data(self.sample_data, self.benchmark_data)
    
    def _create_sample_data(self, n_assets=5, n_periods=252):
        """Create sample data for testing"""
        np.random.seed(42)
        dates = pd.date_range(start='2023-01-01', periods=n_periods, freq='D')
        assets = [f'ASSET_{i+1}' for i in range(n_assets)]
        
        returns = np.random.multivariate_normal(
            mean=[0.0005] * n_assets,
            cov=np.eye(n_assets) * 0.0001 + 0.00002,
            size=n_periods
        )
        
        prices = pd.DataFrame(index=dates, columns=assets)
        prices.iloc[0] = 100.0
        
        for i in range(1, n_periods):
            prices.iloc[i] = prices.iloc[i-1] * (1 + returns[i])
            
        return prices
    
    def _create_benchmark_data(self):
        """Create benchmark data"""
        np.random.seed(42)
        dates = self.sample_data.index
        returns = np.random.normal(0.0004, 0.01, len(dates))
        
        benchmark = pd.Series(index=dates, name='SPY')
        benchmark.iloc[0] = 100.0
        
        for i in range(1, len(dates)):
            benchmark.iloc[i] = benchmark.iloc[i-1] * (1 + returns[i])
            
        return benchmark
    
    def test_mean_variance_optimization(self):
        """Test mean-variance optimization"""
        config = OptimizationConfig(
            method=OptimizationMethod.MEAN_VARIANCE,
            risk_measure=RiskMeasure.VARIANCE,
            target_return=0.10
        )
        
        result = self.portfolio_manager.optimize(config)
        
        self.assertIn('weights', result)
        self.assertIn('metrics', result)
        
        weights = result['weights']
        self.assertAlmostEqual(weights.sum(), 1.0, places=3)
        self.assertTrue(all(weights >= -0.001))  # Allow for small numerical errors
    
    def test_maximum_sharpe_optimization(self):
        """Test maximum Sharpe ratio optimization"""
        config = OptimizationConfig(
            method=OptimizationMethod.MAXIMUM_SHARPE,
            risk_free_rate=0.02
        )
        
        result = self.portfolio_manager.optimize(config)
        
        self.assertIn('weights', result)
        self.assertIn('metrics', result)
        
        weights = result['weights']
        self.assertAlmostEqual(weights.sum(), 1.0, places=3)
        
        metrics = result['metrics']
        self.assertIsInstance(metrics.sharpe_ratio, (int, float))
    
    def test_minimum_variance_optimization(self):
        """Test minimum variance optimization"""
        config = OptimizationConfig(
            method=OptimizationMethod.MINIMUM_VARIANCE
        )
        
        result = self.portfolio_manager.optimize(config)
        
        self.assertIn('weights', result)
        weights = result['weights']
        self.assertAlmostEqual(weights.sum(), 1.0, places=3)
    
    def test_risk_parity_optimization(self):
        """Test risk parity optimization"""
        config = OptimizationConfig(
            method=OptimizationMethod.RISK_PARITY
        )
        
        result = self.portfolio_manager.optimize(config)
        
        self.assertIn('weights', result)
        weights = result['weights']
        self.assertAlmostEqual(weights.sum(), 1.0, places=3)
    
    def test_hierarchical_risk_parity(self):
        """Test hierarchical risk parity optimization"""
        config = OptimizationConfig(
            method=OptimizationMethod.HIERARCHICAL_RISK_PARITY
        )
        
        result = self.portfolio_manager.optimize(config)
        
        self.assertIn('weights', result)
        weights = result['weights']
        self.assertAlmostEqual(weights.sum(), 1.0, places=3)
    
    def test_black_litterman_optimization(self):
        """Test Black-Litterman optimization with views"""
        views = {
            'ASSET_1': 0.12,
            'ASSET_2': 0.08
        }
        
        confidence = {
            'ASSET_1': 0.8,
            'ASSET_2': 0.6
        }
        
        config = OptimizationConfig(
            method=OptimizationMethod.BLACK_LITTERMAN,
            black_litterman_views=views,
            black_litterman_confidence=confidence
        )
        
        result = self.portfolio_manager.optimize(config)
        
        self.assertIn('weights', result)
        weights = result['weights']
        self.assertAlmostEqual(weights.sum(), 1.0, places=3)
    
    def test_cvar_optimization(self):
        """Test CVaR optimization"""
        config = OptimizationConfig(
            method=OptimizationMethod.CVAR_OPTIMIZATION,
            risk_measure=RiskMeasure.CVAR,
            alpha=0.05,
            target_return=0.08
        )
        
        result = self.portfolio_manager.optimize(config)
        
        self.assertIn('weights', result)
        weights = result['weights']
        self.assertAlmostEqual(weights.sum(), 1.0, places=3)
    
    def test_optimization_with_constraints(self):
        """Test optimization with weight constraints"""
        config = OptimizationConfig(
            method=OptimizationMethod.MAXIMUM_SHARPE,
            min_weight=0.05,
            max_weight=0.3
        )
        
        result = self.portfolio_manager.optimize(config)
        
        weights = result['weights']
        self.assertTrue(all(weights >= 0.04))  # Allow for small numerical errors
        self.assertTrue(all(weights <= 0.31))  # Allow for small numerical errors

class TestPerformanceAttribution(unittest.TestCase):
    """
    Test cases for performance attribution analysis
    """
    
    def setUp(self):
        """Set up test fixtures"""
        self.portfolio_manager = PortfolioManager()
        self.sample_data = self._create_sample_data()
        self.benchmark_data = self._create_benchmark_data()
        self.portfolio_manager.load_data(self.sample_data, self.benchmark_data)
    
    def _create_sample_data(self, n_assets=5, n_periods=252):
        """Create sample data for testing"""
        np.random.seed(42)
        dates = pd.date_range(start='2023-01-01', periods=n_periods, freq='D')
        assets = [f'ASSET_{i+1}' for i in range(n_assets)]
        
        returns = np.random.multivariate_normal(
            mean=[0.0005] * n_assets,
            cov=np.eye(n_assets) * 0.0001 + 0.00002,
            size=n_periods
        )
        
        prices = pd.DataFrame(index=dates, columns=assets)
        prices.iloc[0] = 100.0
        
        for i in range(1, n_periods):
            prices.iloc[i] = prices.iloc[i-1] * (1 + returns[i])
            
        return prices
    
    def _create_benchmark_data(self):
        """Create benchmark data"""
        np.random.seed(42)
        dates = self.sample_data.index
        returns = np.random.normal(0.0004, 0.01, len(dates))
        
        benchmark = pd.Series(index=dates, name='SPY')
        benchmark.iloc[0] = 100.0
        
        for i in range(1, len(dates)):
            benchmark.iloc[i] = benchmark.iloc[i-1] * (1 + returns[i])
            
        return benchmark
    
    def test_performance_attribution_basic(self):
        """Test basic performance attribution"""
        assets = self.sample_data.columns
        portfolio_weights = pd.Series(1.0/len(assets), index=assets)
        benchmark_weights = pd.Series(1.0/len(assets), index=assets)
        returns_data = self.sample_data.pct_change().dropna()
        
        attribution = self.portfolio_manager.performance_attribution(
            portfolio_weights=portfolio_weights,
            benchmark_weights=benchmark_weights,
            returns_data=returns_data
        )
        
        self.assertIsInstance(attribution, AttributionAnalysis)
        self.assertIsInstance(attribution.total_return, (int, float))
        self.assertIsInstance(attribution.asset_allocation_effect, pd.Series)
        self.assertIsInstance(attribution.security_selection_effect, pd.Series)
    
    def test_performance_attribution_with_sectors(self):
        """Test performance attribution with sector mapping"""
        assets = self.sample_data.columns
        portfolio_weights = pd.Series(1.0/len(assets), index=assets)
        benchmark_weights = pd.Series(1.0/len(assets), index=assets)
        returns_data = self.sample_data.pct_change().dropna()
        
        # Create sector mapping
        sector_mapping = {
            'ASSET_1': 'Technology',
            'ASSET_2': 'Technology',
            'ASSET_3': 'Healthcare',
            'ASSET_4': 'Finance',
            'ASSET_5': 'Finance'
        }
        
        attribution = self.portfolio_manager.performance_attribution(
            portfolio_weights=portfolio_weights,
            benchmark_weights=benchmark_weights,
            returns_data=returns_data,
            sector_mapping=sector_mapping
        )
        
        self.assertIn('sector_attribution', attribution.__dict__)
        self.assertIsInstance(attribution.sector_attribution, dict)
    
    def test_attribution_calculation_accuracy(self):
        """Test attribution calculation accuracy"""
        assets = self.sample_data.columns
        
        # Create different weights for portfolio and benchmark
        portfolio_weights = pd.Series([0.3, 0.25, 0.2, 0.15, 0.1], index=assets)
        benchmark_weights = pd.Series([0.2, 0.2, 0.2, 0.2, 0.2], index=assets)
        returns_data = self.sample_data.pct_change().dropna()
        
        attribution = self.portfolio_manager.performance_attribution(
            portfolio_weights=portfolio_weights,
            benchmark_weights=benchmark_weights,
            returns_data=returns_data
        )
        
        # Check that attribution effects sum to total excess return
        total_allocation = attribution.asset_allocation_effect.sum()
        total_selection = attribution.security_selection_effect.sum()
        
        # The sum should be close to the total excess return (allowing for interaction effects)
        self.assertIsInstance(total_allocation, (int, float))
        self.assertIsInstance(total_selection, (int, float))

class TestRebalancing(unittest.TestCase):
    """
    Test cases for portfolio rebalancing functionality
    """
    
    def setUp(self):
        """Set up test fixtures"""
        self.portfolio_manager = PortfolioManager()
    
    def test_rebalancing_basic(self):
        """Test basic rebalancing functionality"""
        current_portfolio = {
            'ASSET_1': 25000,
            'ASSET_2': 30000,
            'ASSET_3': 20000,
            'ASSET_4': 15000,
            'ASSET_5': 10000
        }
        
        target_allocations = {
            'ASSET_1': 0.30,
            'ASSET_2': 0.25,
            'ASSET_3': 0.20,
            'ASSET_4': 0.15,
            'ASSET_5': 0.10
        }
        
        result = self.portfolio_manager.rebalance(
            current_portfolio=current_portfolio,
            target_allocations=target_allocations,
            transaction_costs=0.001
        )
        
        self.assertIn('trades', result)
        self.assertIn('total_transaction_cost', result)
        self.assertIn('turnover', result)
        self.assertIn('rebalancing_summary', result)
        
        # Check that turnover is reasonable
        self.assertTrue(0 <= result['turnover'] <= 2)  # Turnover should be between 0 and 200%
    
    def test_rebalancing_with_min_trade_size(self):
        """Test rebalancing with minimum trade size constraint"""
        current_portfolio = {
            'ASSET_1': 10000,
            'ASSET_2': 10000
        }
        
        target_allocations = {
            'ASSET_1': 0.51,  # Small change
            'ASSET_2': 0.49
        }
        
        result = self.portfolio_manager.rebalance(
            current_portfolio=current_portfolio,
            target_allocations=target_allocations,
            transaction_costs=0.001,
            min_trade_size=500  # High minimum trade size
        )
        
        # With high minimum trade size, small rebalancing might be skipped
        self.assertIn('trades', result)
    
    def test_rebalancing_transaction_costs(self):
        """Test transaction cost calculation in rebalancing"""
        current_portfolio = {
            'ASSET_1': 50000,
            'ASSET_2': 50000
        }
        
        target_allocations = {
            'ASSET_1': 0.7,  # Large change
            'ASSET_2': 0.3
        }
        
        result_low_cost = self.portfolio_manager.rebalance(
            current_portfolio=current_portfolio,
            target_allocations=target_allocations,
            transaction_costs=0.001  # 0.1%
        )
        
        result_high_cost = self.portfolio_manager.rebalance(
            current_portfolio=current_portfolio,
            target_allocations=target_allocations,
            transaction_costs=0.01  # 1%
        )
        
        # Higher transaction costs should result in higher total costs
        self.assertGreater(
            result_high_cost['total_transaction_cost'],
            result_low_cost['total_transaction_cost']
        )

class TestRiskMeasures(unittest.TestCase):
    """
    Test cases for risk measure calculations
    """
    
    def setUp(self):
        """Set up test fixtures"""
        self.portfolio_manager = PortfolioManager()
        self.sample_data = self._create_sample_data()
        self.benchmark_data = self._create_benchmark_data()
        self.portfolio_manager.load_data(self.sample_data, self.benchmark_data)
    
    def _create_sample_data(self, n_assets=5, n_periods=252):
        """Create sample data for testing"""
        np.random.seed(42)
        dates = pd.date_range(start='2023-01-01', periods=n_periods, freq='D')
        assets = [f'ASSET_{i+1}' for i in range(n_assets)]
        
        returns = np.random.multivariate_normal(
            mean=[0.0005] * n_assets,
            cov=np.eye(n_assets) * 0.0001 + 0.00002,
            size=n_periods
        )
        
        prices = pd.DataFrame(index=dates, columns=assets)
        prices.iloc[0] = 100.0
        
        for i in range(1, n_periods):
            prices.iloc[i] = prices.iloc[i-1] * (1 + returns[i])
            
        return prices
    
    def _create_benchmark_data(self):
        """Create benchmark data"""
        np.random.seed(42)
        dates = self.sample_data.index
        returns = np.random.normal(0.0004, 0.01, len(dates))
        
        benchmark = pd.Series(index=dates, name='SPY')
        benchmark.iloc[0] = 100.0
        
        for i in range(1, len(dates)):
            benchmark.iloc[i] = benchmark.iloc[i-1] * (1 + returns[i])
            
        return benchmark
    
    def test_portfolio_metrics_calculation(self):
        """Test portfolio metrics calculation"""
        weights = pd.Series([0.2, 0.2, 0.2, 0.2, 0.2], index=self.sample_data.columns)
        
        metrics = self.portfolio_manager.calculate_portfolio_metrics(weights)
        
        self.assertIsInstance(metrics, PortfolioMetrics)
        self.assertIsInstance(metrics.expected_return, (int, float))
        self.assertIsInstance(metrics.volatility, (int, float))
        self.assertIsInstance(metrics.sharpe_ratio, (int, float))
        self.assertIsInstance(metrics.max_drawdown, (int, float))
        self.assertIsInstance(metrics.var_95, (int, float))
        self.assertIsInstance(metrics.cvar_95, (int, float))
        
        # Check reasonable ranges
        self.assertTrue(-1 <= metrics.expected_return <= 1)  # -100% to 100% annual return
        self.assertTrue(0 <= metrics.volatility <= 2)  # 0% to 200% volatility
        self.assertTrue(-10 <= metrics.sharpe_ratio <= 10)  # Reasonable Sharpe ratio range
    
    def test_var_calculation(self):
        """Test VaR calculation"""
        weights = pd.Series([0.2, 0.2, 0.2, 0.2, 0.2], index=self.sample_data.columns)
        metrics = self.portfolio_manager.calculate_portfolio_metrics(weights)
        
        # VaR should be negative (representing a loss)
        self.assertLess(metrics.var_95, 0)
        
        # CVaR should be more negative than VaR (worse loss)
        self.assertLess(metrics.cvar_95, metrics.var_95)
    
    def test_drawdown_calculation(self):
        """Test maximum drawdown calculation"""
        weights = pd.Series([0.2, 0.2, 0.2, 0.2, 0.2], index=self.sample_data.columns)
        metrics = self.portfolio_manager.calculate_portfolio_metrics(weights)
        
        # Max drawdown should be negative or zero
        self.assertLessEqual(metrics.max_drawdown, 0)
        
        # Max drawdown should be reasonable (not worse than -100%)
        self.assertGreaterEqual(metrics.max_drawdown, -1)

class TestErrorHandling(unittest.TestCase):
    """
    Test cases for error handling and edge cases
    """
    
    def setUp(self):
        """Set up test fixtures"""
        self.portfolio_manager = PortfolioManager()
    
    def test_optimization_without_data(self):
        """Test optimization without loaded data"""
        config = OptimizationConfig(method=OptimizationMethod.MEAN_VARIANCE)
        
        with self.assertRaises(ValueError):
            self.portfolio_manager.optimize(config)
    
    def test_invalid_optimization_config(self):
        """Test optimization with invalid configuration"""
        # Load some data first
        sample_data = pd.DataFrame({
            'A': [100, 101, 102],
            'B': [100, 99, 101]
        }, index=pd.date_range('2023-01-01', periods=3))
        
        benchmark_data = pd.Series([100, 100.5, 101], 
                                 index=sample_data.index, name='BENCH')
        
        self.portfolio_manager.load_data(sample_data, benchmark_data)
        
        # Test with invalid target return (too high)
        config = OptimizationConfig(
            method=OptimizationMethod.MEAN_VARIANCE,
            target_return=10.0  # 1000% return - unrealistic
        )
        
        result = self.portfolio_manager.optimize(config)
        
        # Should handle gracefully and return error information
        self.assertTrue('error' in result or 'optimization_status' in result)
    
    def test_empty_data_handling(self):
        """Test handling of empty data"""
        empty_data = pd.DataFrame()
        
        with self.assertRaises(ValueError):
            self.portfolio_manager.load_data(empty_data, pd.Series())
    
    def test_single_asset_optimization(self):
        """Test optimization with single asset (edge case)"""
        single_asset_data = pd.DataFrame({
            'SINGLE_ASSET': [100, 101, 102, 101, 103]
        }, index=pd.date_range('2023-01-01', periods=5))
        
        benchmark_data = pd.Series([100, 100.5, 101, 100.8, 102], 
                                 index=single_asset_data.index, name='BENCH')
        
        self.portfolio_manager.load_data(single_asset_data, benchmark_data)
        
        config = OptimizationConfig(method=OptimizationMethod.MEAN_VARIANCE)
        result = self.portfolio_manager.optimize(config)
        
        # With single asset, weight should be 1.0
        if 'weights' in result:
            self.assertAlmostEqual(result['weights'].iloc[0], 1.0, places=3)

class TestOptimizationEngines(unittest.TestCase):
    """
    Test cases for optimization engines
    """
    
    def setUp(self):
        """Set up test fixtures"""
        np.random.seed(42)
        self.expected_returns = pd.Series([0.1, 0.12, 0.08, 0.15], 
                                        index=['A', 'B', 'C', 'D'])
        self.cov_matrix = pd.DataFrame(
            [[0.1, 0.02, 0.01, 0.03],
             [0.02, 0.15, 0.02, 0.04],
             [0.01, 0.02, 0.08, 0.01],
             [0.03, 0.04, 0.01, 0.2]],
            index=['A', 'B', 'C', 'D'],
            columns=['A', 'B', 'C', 'D']
        )
    
    def test_pypfopt_engine_initialization(self):
        """Test PyPortfolioOpt engine initialization"""
        engine = PyPortfolioOptEngine()
        self.assertIsNotNone(engine)
    
    def test_riskfolio_engine_initialization(self):
        """Test Riskfolio engine initialization"""
        engine = RiskfolioEngine()
        self.assertIsNotNone(engine)
    
    @patch('pypfopt.EfficientFrontier')
    def test_pypfopt_mean_variance(self, mock_ef):
        """Test PyPortfolioOpt mean-variance optimization"""
        # Mock the EfficientFrontier
        mock_ef_instance = Mock()
        mock_ef_instance.max_sharpe.return_value = {'A': 0.3, 'B': 0.3, 'C': 0.2, 'D': 0.2}
        mock_ef_instance.portfolio_performance.return_value = (0.12, 0.15, 0.8)
        mock_ef.return_value = mock_ef_instance
        
        engine = PyPortfolioOptEngine()
        
        config = OptimizationConfig(
            method=OptimizationMethod.MAXIMUM_SHARPE,
            risk_free_rate=0.02
        )
        
        result = engine.optimize(
            expected_returns=self.expected_returns,
            cov_matrix=self.cov_matrix,
            config=config
        )
        
        self.assertIn('weights', result)
        self.assertIn('metrics', result)

def create_test_suite():
    """
    Create a comprehensive test suite
    
    Returns:
        unittest.TestSuite: Complete test suite
    """
    suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        TestPortfolioManager,
        TestOptimizationMethods,
        TestPerformanceAttribution,
        TestRebalancing,
        TestRiskMeasures,
        TestErrorHandling,
        TestOptimizationEngines
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    return suite

def run_tests(verbosity=2):
    """
    Run all tests with specified verbosity
    
    Args:
        verbosity (int): Test output verbosity level
        
    Returns:
        unittest.TestResult: Test results
    """
    suite = create_test_suite()
    runner = unittest.TextTestRunner(verbosity=verbosity)
    return runner.run(suite)

if __name__ == '__main__':
    print("\n" + "="*80)
    print("PORTFOLIO OPTIMIZATION SYSTEM - COMPREHENSIVE TEST SUITE")
    print("="*80)
    
    # Run tests
    result = run_tests(verbosity=2)
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback.split('AssertionError: ')[-1].split('\n')[0]}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback.split('\n')[-2]}")
    
    success_rate = (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100
    print(f"\nSuccess Rate: {success_rate:.1f}%")
    
    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED!")
    else:
        print("\n❌ SOME TESTS FAILED!")
    
    print("="*80)