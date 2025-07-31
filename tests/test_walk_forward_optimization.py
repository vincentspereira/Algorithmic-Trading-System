"""
Tests for Walk-Forward Optimization
"""

import pytest
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from nautilus_trader_engine.backtesting.walk_forward_optimization import (
    WalkForwardOptimizer,
    OptimizationEngine,
    OverfittingDetector,
    ParameterStabilityAnalyzer,
    ParameterRange,
    OptimizationConfig,
    OptimizationResult,
    WalkForwardResults,
    OptimizationMethod,
    ValidationMethod
)


class TestParameterRange:
    """Test parameter range functionality"""
    
    def test_parameter_range_creation(self):
        """Test parameter range creation"""
        param_range = ParameterRange(
            name="test_param",
            min_value=1.0,
            max_value=10.0,
            step_size=1.0,
            parameter_type="float"
        )
        
        assert param_range.name == "test_param"
        assert param_range.min_value == 1.0
        assert param_range.max_value == 10.0
        assert param_range.step_size == 1.0
        assert param_range.parameter_type == "float"
    
    def test_categorical_parameter_range(self):
        """Test categorical parameter range"""
        param_range = ParameterRange(
            name="strategy_type",
            min_value=0,
            max_value=0,
            values=["momentum", "mean_reversion", "trend_following"],
            parameter_type="categorical"
        )
        
        assert param_range.values == ["momentum", "mean_reversion", "trend_following"]
        assert param_range.parameter_type == "categorical"


class TestOverfittingDetector:
    """Test overfitting detection"""
    
    @pytest.fixture
    def detector(self):
        return OverfittingDetector(threshold=0.3)
    
    def test_no_overfitting(self, detector):
        """Test case with no overfitting"""
        in_sample_score = 1.5
        out_of_sample_score = 1.4
        
        is_overfitted, overfitting_score = detector.detect_overfitting(
            in_sample_score, out_of_sample_score
        )
        
        assert not is_overfitted
        assert overfitting_score < 0.3
    
    def test_overfitting_detected(self, detector):
        """Test case with overfitting"""
        in_sample_score = 2.0
        out_of_sample_score = 1.0
        
        is_overfitted, overfitting_score = detector.detect_overfitting(
            in_sample_score, out_of_sample_score
        )
        
        assert is_overfitted
        assert overfitting_score > 0.3
    
    def test_invalid_scores(self, detector):
        """Test with invalid scores"""
        is_overfitted, overfitting_score = detector.detect_overfitting(0.0, -1.0)
        
        assert is_overfitted
        assert overfitting_score == 1.0
    
    def test_analyze_overfitting_pattern(self, detector):
        """Test overfitting pattern analysis"""
        results = []
        for i in range(5):
            result = OptimizationResult(
                parameters={"param1": i},
                in_sample_metrics={"sharpe_ratio": 1.5},
                out_of_sample_metrics={"sharpe_ratio": 1.0},
                training_period=(datetime.now(), datetime.now()),
                testing_period=(datetime.now(), datetime.now()),
                optimization_time=1.0,
                validation_score=1.0,
                overfitting_score=0.33,  # Slightly overfitted
                stability_score=0.8
            )
            results.append(result)
        
        analysis = detector.analyze_overfitting_pattern(results)
        
        assert "mean_overfitting" in analysis
        assert "median_overfitting" in analysis
        assert "overfitted_periods" in analysis
        assert analysis["overfitted_periods"] == 5  # All periods overfitted


class TestParameterStabilityAnalyzer:
    """Test parameter stability analysis"""
    
    @pytest.fixture
    def analyzer(self):
        return ParameterStabilityAnalyzer(stability_threshold=0.7)
    
    def test_stable_parameters(self, analyzer):
        """Test with stable parameters"""
        results = []
        for i in range(5):
            result = OptimizationResult(
                parameters={"param1": 10.0, "param2": "strategy_a"},  # Stable values
                in_sample_metrics={},
                out_of_sample_metrics={},
                training_period=(datetime.now(), datetime.now()),
                testing_period=(datetime.now(), datetime.now()),
                optimization_time=1.0,
                validation_score=1.0,
                overfitting_score=0.1,
                stability_score=0.8
            )
            results.append(result)
        
        stability = analyzer.analyze_stability(results)
        
        assert "param1" in stability
        assert "param2" in stability
        assert stability["param1"] == 1.0  # Perfect stability
        assert stability["param2"] == 1.0  # Perfect stability
    
    def test_unstable_parameters(self, analyzer):
        """Test with unstable parameters"""
        results = []
        for i in range(5):
            result = OptimizationResult(
                parameters={"param1": float(i * 10), "param2": f"strategy_{i}"},  # Varying values
                in_sample_metrics={},
                out_of_sample_metrics={},
                training_period=(datetime.now(), datetime.now()),
                testing_period=(datetime.now(), datetime.now()),
                optimization_time=1.0,
                validation_score=1.0,
                overfitting_score=0.1,
                stability_score=0.8
            )
            results.append(result)
        
        stability = analyzer.analyze_stability(results)
        
        assert "param1" in stability
        assert "param2" in stability
        assert stability["param1"] < 1.0  # Should be unstable
        assert stability["param2"] < 1.0  # Should be unstable
    
    def test_empty_results(self, analyzer):
        """Test with empty results"""
        stability = analyzer.analyze_stability([])
        assert stability == {}


class TestOptimizationEngine:
    """Test optimization engine"""
    
    @pytest.fixture
    def config(self):
        parameter_ranges = [
            ParameterRange(
                name="param1",
                min_value=1.0,
                max_value=5.0,
                step_size=1.0,
                parameter_type="float"
            ),
            ParameterRange(
                name="param2",
                min_value=10,
                max_value=20,
                step_size=5,
                parameter_type="int"
            )
        ]
        
        return OptimizationConfig(
            parameter_ranges=parameter_ranges,
            optimization_method=OptimizationMethod.GRID_SEARCH,
            max_iterations=10,
            random_seed=42
        )
    
    @pytest.fixture
    def engine(self, config):
        return OptimizationEngine(config)
    
    def test_grid_search_optimization(self, engine):
        """Test grid search optimization"""
        def objective_function(params, data):
            # Simple objective: maximize param1 + param2
            return params["param1"] + params["param2"]
        
        training_data = {"dummy": "data"}
        
        best_params, best_score = engine.optimize_parameters(
            objective_function, training_data
        )
        
        assert "param1" in best_params
        assert "param2" in best_params
        assert best_score > 0
        # Should find maximum values
        assert best_params["param1"] == 5.0
        assert best_params["param2"] == 20
    
    def test_random_search_optimization(self, config):
        """Test random search optimization"""
        config.optimization_method = OptimizationMethod.RANDOM_SEARCH
        config.max_iterations = 20
        
        engine = OptimizationEngine(config)
        
        def objective_function(params, data):
            # Simple objective: maximize param1 + param2
            return params["param1"] + params["param2"]
        
        training_data = {"dummy": "data"}
        
        best_params, best_score = engine.optimize_parameters(
            objective_function, training_data
        )
        
        assert "param1" in best_params
        assert "param2" in best_params
        assert best_score > 0
    
    def test_parameter_grid_generation(self, engine):
        """Test parameter grid generation"""
        param_grid = engine._generate_parameter_grid()
        
        assert len(param_grid) > 0
        
        # Check that all combinations are present
        param1_values = set()
        param2_values = set()
        
        for params in param_grid:
            param1_values.add(params["param1"])
            param2_values.add(params["param2"])
        
        assert len(param1_values) == 5  # 1.0, 2.0, 3.0, 4.0, 5.0
        assert len(param2_values) == 3  # 10, 15, 20
    
    def test_random_parameter_generation(self, engine):
        """Test random parameter generation"""
        for _ in range(10):
            params = engine._generate_random_parameters()
            
            assert "param1" in params
            assert "param2" in params
            assert 1.0 <= params["param1"] <= 5.0
            assert 10 <= params["param2"] <= 20
            assert isinstance(params["param2"], int)


class TestWalkForwardOptimizer:
    """Test walk-forward optimizer"""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing"""
        np.random.seed(42)
        dates = pd.date_range(start='2022-01-01', end='2022-12-31', freq='D')
        
        returns = np.random.normal(0.001, 0.02, len(dates))
        prices = [100.0]
        for ret in returns:
            prices.append(prices[-1] * (1 + ret))
        
        return pd.DataFrame({
            'timestamp': dates,
            'price': prices[1:],
            'returns': returns,
            'volume': np.random.randint(1000, 10000, len(dates))
        })
    
    @pytest.fixture
    def config(self):
        parameter_ranges = [
            ParameterRange(
                name="window",
                min_value=5,
                max_value=15,
                step_size=5,
                parameter_type="int"
            )
        ]
        
        return OptimizationConfig(
            parameter_ranges=parameter_ranges,
            optimization_method=OptimizationMethod.GRID_SEARCH,
            training_window_days=100,
            testing_window_days=30,
            step_size_days=30,
            min_training_samples=50,
            parallel_execution=False,
            random_seed=42
        )
    
    @pytest.fixture
    def optimizer(self, config):
        return WalkForwardOptimizer(config)
    
    def test_time_window_generation(self, optimizer, sample_data):
        """Test time window generation"""
        windows = optimizer._generate_time_windows(sample_data)
        
        assert len(windows) > 0
        
        for train_start, train_end, test_start, test_end in windows:
            assert train_start < train_end
            assert train_end == test_start
            assert test_start < test_end
            assert (train_end - train_start).days == optimizer.config.training_window_days
            assert (test_end - test_start).days == optimizer.config.testing_window_days
    
    @pytest.mark.asyncio
    async def test_single_window_optimization(self, optimizer, sample_data):
        """Test single window optimization"""
        def objective_function(params, data):
            # Simple objective based on window parameter
            window = params["window"]
            if len(data) < window:
                return -1.0
            
            # Calculate simple moving average return
            data = data.copy()
            data['ma'] = data['price'].rolling(window=window).mean()
            data['signal'] = (data['price'] > data['ma']).astype(int)
            data['strategy_return'] = data['signal'].shift(1) * data['returns']
            
            strategy_returns = data['strategy_return'].dropna()
            if len(strategy_returns) == 0 or strategy_returns.std() == 0:
                return -1.0
            
            return strategy_returns.mean() / strategy_returns.std()
        
        def evaluation_function(params, data):
            # Evaluation function
            window = params["window"]
            if len(data) < window:
                return {"sharpe_ratio": 0.0, "total_return": 0.0}
            
            data = data.copy()
            data['ma'] = data['price'].rolling(window=window).mean()
            data['signal'] = (data['price'] > data['ma']).astype(int)
            data['strategy_return'] = data['signal'].shift(1) * data['returns']
            
            strategy_returns = data['strategy_return'].dropna()
            if len(strategy_returns) == 0:
                return {"sharpe_ratio": 0.0, "total_return": 0.0}
            
            total_return = (1 + strategy_returns).prod() - 1
            sharpe_ratio = strategy_returns.mean() / strategy_returns.std() if strategy_returns.std() > 0 else 0.0
            
            return {"sharpe_ratio": sharpe_ratio, "total_return": total_return}
        
        # Get first time window
        windows = optimizer._generate_time_windows(sample_data)
        train_start, train_end, test_start, test_end = windows[0]
        
        result = await optimizer._optimize_single_window(
            sample_data, train_start, train_end, test_start, test_end,
            objective_function, evaluation_function
        )
        
        assert result is not None
        assert "window" in result.parameters
        assert "sharpe_ratio" in result.in_sample_metrics
        assert "sharpe_ratio" in result.out_of_sample_metrics
        assert result.optimization_time > 0
        assert 0 <= result.overfitting_score <= 1
        assert 0 <= result.stability_score <= 1
    
    @pytest.mark.asyncio
    async def test_full_walk_forward_optimization(self, optimizer, sample_data):
        """Test full walk-forward optimization"""
        def objective_function(params, data):
            window = params["window"]
            if len(data) < window:
                return -1.0
            
            # Simple moving average strategy
            data = data.copy()
            data['ma'] = data['price'].rolling(window=window).mean()
            data['signal'] = (data['price'] > data['ma']).astype(int)
            data['strategy_return'] = data['signal'].shift(1) * data['returns']
            
            strategy_returns = data['strategy_return'].dropna()
            if len(strategy_returns) == 0 or strategy_returns.std() == 0:
                return -1.0
            
            return strategy_returns.mean() / strategy_returns.std()
        
        def evaluation_function(params, data):
            window = params["window"]
            if len(data) < window:
                return {"sharpe_ratio": 0.0, "total_return": 0.0}
            
            data = data.copy()
            data['ma'] = data['price'].rolling(window=window).mean()
            data['signal'] = (data['price'] > data['ma']).astype(int)
            data['strategy_return'] = data['signal'].shift(1) * data['returns']
            
            strategy_returns = data['strategy_return'].dropna()
            if len(strategy_returns) == 0:
                return {"sharpe_ratio": 0.0, "total_return": 0.0}
            
            total_return = (1 + strategy_returns).prod() - 1
            sharpe_ratio = strategy_returns.mean() / strategy_returns.std() if strategy_returns.std() > 0 else 0.0
            
            return {"sharpe_ratio": sharpe_ratio, "total_return": total_return}
        
        results = await optimizer.run_walk_forward_optimization(
            sample_data, objective_function, evaluation_function
        )
        
        assert isinstance(results, WalkForwardResults)
        assert len(results.optimization_results) > 0
        assert "window" in results.best_parameters
        assert "window" in results.parameter_stability
        assert results.execution_time > 0
        assert "mean_validation_score" in results.performance_summary
        assert "mean_overfitting" in results.overfitting_analysis
    
    def test_invalid_data(self, optimizer):
        """Test with invalid data"""
        # Data without timestamp column
        invalid_data = pd.DataFrame({
            'price': [100, 101, 102],
            'returns': [0.01, 0.01, 0.01]
        })
        
        windows = optimizer._generate_time_windows(invalid_data)
        assert len(windows) == 0
    
    def test_insufficient_data(self, optimizer):
        """Test with insufficient data"""
        # Very small dataset
        small_data = pd.DataFrame({
            'timestamp': pd.date_range(start='2022-01-01', periods=10, freq='D'),
            'price': range(100, 110),
            'returns': [0.01] * 10
        })
        
        windows = optimizer._generate_time_windows(small_data)
        assert len(windows) == 0  # Not enough data for training + testing windows


@pytest.mark.asyncio
async def test_integration_scenario():
    """Test complete integration scenario"""
    print("Running walk-forward optimization integration test...")
    
    # Create sample data
    np.random.seed(42)
    dates = pd.date_range(start='2021-01-01', end='2022-12-31', freq='D')
    
    # Generate synthetic price data with trend and noise
    trend = np.linspace(0, 0.5, len(dates))  # Upward trend
    noise = np.random.normal(0, 0.02, len(dates))
    returns = trend / len(dates) + noise
    
    prices = [100.0]
    for ret in returns:
        prices.append(prices[-1] * (1 + ret))
    
    data = pd.DataFrame({
        'timestamp': dates,
        'price': prices[1:],
        'returns': returns,
        'volume': np.random.randint(1000, 10000, len(dates))
    })
    
    print(f"Generated {len(data)} days of synthetic data")
    
    # Define parameter ranges for simple momentum strategy
    parameter_ranges = [
        ParameterRange(
            name="lookback",
            min_value=5,
            max_value=20,
            step_size=5,
            parameter_type="int"
        ),
        ParameterRange(
            name="threshold",
            min_value=0.01,
            max_value=0.05,
            step_size=0.02,
            parameter_type="float"
        )
    ]
    
    # Create configuration
    config = OptimizationConfig(
        parameter_ranges=parameter_ranges,
        optimization_method=OptimizationMethod.GRID_SEARCH,
        training_window_days=180,  # 6 months
        testing_window_days=60,    # 2 months
        step_size_days=60,         # 2 months
        min_training_samples=100,
        parallel_execution=False,
        random_seed=42
    )
    
    # Define simple momentum strategy
    def objective_function(params, train_data):
        try:
            lookback = int(params['lookback'])
            threshold = float(params['threshold'])
            
            if len(train_data) < lookback + 1:
                return -1.0
            
            train_data = train_data.copy()
            
            # Calculate momentum signal
            train_data['momentum'] = train_data['returns'].rolling(window=lookback).mean()
            train_data['signal'] = 0
            train_data.loc[train_data['momentum'] > threshold, 'signal'] = 1
            train_data.loc[train_data['momentum'] < -threshold, 'signal'] = -1
            
            # Calculate strategy returns
            train_data['strategy_returns'] = train_data['signal'].shift(1) * train_data['returns']
            
            strategy_returns = train_data['strategy_returns'].dropna()
            if len(strategy_returns) == 0 or strategy_returns.std() == 0:
                return -1.0
            
            # Return Sharpe ratio
            sharpe_ratio = strategy_returns.mean() / strategy_returns.std() * np.sqrt(252)
            return sharpe_ratio
            
        except Exception as e:
            print(f"Error in objective function: {e}")
            return -1.0
    
    def evaluation_function(params, eval_data):
        try:
            lookback = int(params['lookback'])
            threshold = float(params['threshold'])
            
            if len(eval_data) < lookback + 1:
                return {
                    'sharpe_ratio': 0.0,
                    'total_return': 0.0,
                    'max_drawdown': 0.0,
                    'win_rate': 0.0
                }
            
            eval_data = eval_data.copy()
            
            # Calculate momentum signal
            eval_data['momentum'] = eval_data['returns'].rolling(window=lookback).mean()
            eval_data['signal'] = 0
            eval_data.loc[eval_data['momentum'] > threshold, 'signal'] = 1
            eval_data.loc[eval_data['momentum'] < -threshold, 'signal'] = -1
            
            # Calculate strategy returns
            eval_data['strategy_returns'] = eval_data['signal'].shift(1) * eval_data['returns']
            
            strategy_returns = eval_data['strategy_returns'].dropna()
            
            if len(strategy_returns) == 0:
                return {
                    'sharpe_ratio': 0.0,
                    'total_return': 0.0,
                    'max_drawdown': 0.0,
                    'win_rate': 0.0
                }
            
            # Calculate metrics
            total_return = (1 + strategy_returns).prod() - 1
            sharpe_ratio = strategy_returns.mean() / strategy_returns.std() * np.sqrt(252) if strategy_returns.std() > 0 else 0.0
            
            # Max drawdown
            cumulative_returns = (1 + strategy_returns).cumprod()
            rolling_max = cumulative_returns.expanding().max()
            drawdowns = (cumulative_returns - rolling_max) / rolling_max
            max_drawdown = drawdowns.min()
            
            # Win rate
            win_rate = (strategy_returns > 0).mean()
            
            return {
                'sharpe_ratio': sharpe_ratio,
                'total_return': total_return,
                'max_drawdown': max_drawdown,
                'win_rate': win_rate
            }
            
        except Exception as e:
            print(f"Error in evaluation function: {e}")
            return {
                'sharpe_ratio': 0.0,
                'total_return': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 0.0
            }
    
    # Run optimization
    optimizer = WalkForwardOptimizer(config)
    results = await optimizer.run_walk_forward_optimization(
        data, objective_function, evaluation_function
    )
    
    # Verify results
    assert isinstance(results, WalkForwardResults)
    assert len(results.optimization_results) > 0
    assert 'lookback' in results.best_parameters
    assert 'threshold' in results.best_parameters
    assert results.execution_time > 0
    
    # Check that we have stability analysis
    assert 'lookback' in results.parameter_stability
    assert 'threshold' in results.parameter_stability
    
    # Check performance summary
    assert 'mean_validation_score' in results.performance_summary
    assert 'robustness_score' in results.performance_summary
    
    # Check overfitting analysis
    assert 'mean_overfitting' in results.overfitting_analysis
    assert 'overfitted_periods' in results.overfitting_analysis
    
    # Verify individual results
    for result in results.optimization_results:
        assert 'lookback' in result.parameters
        assert 'threshold' in result.parameters
        assert 'sharpe_ratio' in result.in_sample_metrics
        assert 'sharpe_ratio' in result.out_of_sample_metrics
        assert 0 <= result.overfitting_score <= 1
        assert 0 <= result.stability_score <= 1
        assert result.optimization_time > 0
    
    print(f"Integration test completed successfully!")
    print(f"Total windows: {len(results.optimization_results)}")
    print(f"Best parameters: {results.best_parameters}")
    print(f"Execution time: {results.execution_time:.2f} seconds")
    print(f"Mean validation score: {results.performance_summary.get('mean_validation_score', 0):.4f}")
    print(f"Robustness score: {results.performance_summary.get('robustness_score', 0):.4f}")


if __name__ == "__main__":
    # Run the integration test
    asyncio.run(test_integration_scenario())