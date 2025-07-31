"""
Walk-Forward Optimization Framework

This module provides comprehensive walk-forward optimization capabilities including:
- Rolling window optimization framework
- Out-of-sample testing
- Overfitting detection and prevention
- Parameter stability analysis
"""

import logging
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import statistics
import itertools
import warnings
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing as mp

# Try to import optional dependencies
try:
    import scipy.stats as stats
    import scipy.optimize as optimize
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

try:
    import sklearn.model_selection as model_selection
    import sklearn.metrics as metrics
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


class OptimizationMethod(Enum):
    """Optimization methods"""
    GRID_SEARCH = "grid_search"
    RANDOM_SEARCH = "random_search"
    BAYESIAN = "bayesian"
    GENETIC_ALGORITHM = "genetic_algorithm"
    PARTICLE_SWARM = "particle_swarm"


class ValidationMethod(Enum):
    """Validation methods"""
    WALK_FORWARD = "walk_forward"
    EXPANDING_WINDOW = "expanding_window"
    SLIDING_WINDOW = "sliding_window"
    PURGED_CROSS_VALIDATION = "purged_cross_validation"


@dataclass
class ParameterRange:
    """Parameter range definition"""
    name: str
    min_value: float
    max_value: float
    step_size: Optional[float] = None
    values: Optional[List[Any]] = None
    parameter_type: str = "float"  # "float", "int", "categorical"
    distribution: str = "uniform"  # "uniform", "normal", "log_uniform"


@dataclass
class OptimizationResult:
    """Single optimization result"""
    parameters: Dict[str, Any]
    in_sample_metrics: Dict[str, float]
    out_of_sample_metrics: Dict[str, float]
    training_period: Tuple[datetime, datetime]
    testing_period: Tuple[datetime, datetime]
    optimization_time: float
    validation_score: float
    overfitting_score: float
    stability_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WalkForwardResults:
    """Complete walk-forward optimization results"""
    optimization_results: List[OptimizationResult]
    best_parameters: Dict[str, Any]
    parameter_stability: Dict[str, float]
    overfitting_analysis: Dict[str, Any]
    performance_summary: Dict[str, float]
    execution_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizationConfig:
    """Walk-forward optimization configuration"""
    parameter_ranges: List[ParameterRange]
    optimization_method: OptimizationMethod = OptimizationMethod.GRID_SEARCH
    validation_method: ValidationMethod = ValidationMethod.WALK_FORWARD
    training_window_days: int = 252  # 1 year
    testing_window_days: int = 63   # 3 months
    step_size_days: int = 21        # 1 month
    min_training_samples: int = 100
    max_iterations: int = 1000
    convergence_threshold: float = 1e-6
    overfitting_threshold: float = 0.3
    stability_threshold: float = 0.7
    parallel_execution: bool = True
    max_workers: Optional[int] = None
    random_seed: Optional[int] = None


class OverfittingDetector:
    """Detects overfitting in optimization results"""
    
    def __init__(self, threshold: float = 0.3):
        self.threshold = threshold
        self.logger = logging.getLogger(__name__)
    
    def detect_overfitting(self, in_sample_score: float, 
                          out_of_sample_score: float) -> Tuple[bool, float]:
        """Detect overfitting based on performance gap"""
        try:
            if in_sample_score <= 0 or out_of_sample_score <= 0:
                return True, 1.0  # Invalid scores indicate overfitting
            
            # Calculate relative performance degradation
            degradation = (in_sample_score - out_of_sample_score) / in_sample_score
            
            is_overfitted = degradation > self.threshold
            overfitting_score = max(0.0, min(1.0, degradation))
            
            return is_overfitted, overfitting_score
            
        except Exception as e:
            self.logger.error(f"Error detecting overfitting: {e}")
            return True, 1.0
    
    def analyze_overfitting_pattern(self, results: List[OptimizationResult]) -> Dict[str, Any]:
        """Analyze overfitting patterns across multiple results"""
        try:
            overfitting_scores = [r.overfitting_score for r in results]
            
            analysis = {
                "mean_overfitting": statistics.mean(overfitting_scores),
                "median_overfitting": statistics.median(overfitting_scores),
                "max_overfitting": max(overfitting_scores),
                "overfitted_periods": sum(1 for score in overfitting_scores if score > self.threshold),
                "overfitting_trend": self._calculate_trend(overfitting_scores),
                "stability_over_time": 1.0 - statistics.stdev(overfitting_scores) if len(overfitting_scores) > 1 else 1.0
            }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing overfitting pattern: {e}")
            return {"error": str(e)}
    
    def _calculate_trend(self, scores: List[float]) -> str:
        """Calculate trend in overfitting scores"""
        if len(scores) < 3:
            return "insufficient_data"
        
        # Simple linear trend
        x = list(range(len(scores)))
        if SCIPY_AVAILABLE:
            slope, _, _, _, _ = stats.linregress(x, scores)
            if slope > 0.01:
                return "increasing"
            elif slope < -0.01:
                return "decreasing"
            else:
                return "stable"
        else:
            # Simple trend calculation
            first_half = statistics.mean(scores[:len(scores)//2])
            second_half = statistics.mean(scores[len(scores)//2:])
            
            if second_half > first_half * 1.1:
                return "increasing"
            elif second_half < first_half * 0.9:
                return "decreasing"
            else:
                return "stable"


class ParameterStabilityAnalyzer:
    """Analyzes parameter stability across optimization periods"""
    
    def __init__(self, stability_threshold: float = 0.7):
        self.stability_threshold = stability_threshold
        self.logger = logging.getLogger(__name__)
    
    def analyze_stability(self, results: List[OptimizationResult]) -> Dict[str, float]:
        """Analyze parameter stability across results"""
        try:
            if not results:
                return {}
            
            # Get all parameter names
            param_names = set()
            for result in results:
                param_names.update(result.parameters.keys())
            
            stability_scores = {}
            
            for param_name in param_names:
                param_values = []
                for result in results:
                    if param_name in result.parameters:
                        param_values.append(result.parameters[param_name])
                
                if len(param_values) > 1:
                    stability_scores[param_name] = self._calculate_parameter_stability(param_values)
                else:
                    stability_scores[param_name] = 1.0
            
            return stability_scores
            
        except Exception as e:
            self.logger.error(f"Error analyzing parameter stability: {e}")
            return {}
    
    def _calculate_parameter_stability(self, values: List[Any]) -> float:
        """Calculate stability score for a parameter"""
        try:
            if len(values) <= 1:
                return 1.0
            
            # Handle different parameter types
            if all(isinstance(v, (int, float)) for v in values):
                # Numerical parameter
                if all(v == values[0] for v in values):
                    return 1.0  # Perfect stability
                
                # Calculate coefficient of variation
                mean_val = statistics.mean(values)
                if mean_val == 0:
                    return 0.0
                
                std_val = statistics.stdev(values)
                cv = std_val / abs(mean_val)
                
                # Convert CV to stability score (lower CV = higher stability)
                stability = max(0.0, 1.0 - cv)
                return stability
                
            else:
                # Categorical parameter
                unique_values = len(set(values))
                total_values = len(values)
                
                # Stability based on frequency of most common value
                from collections import Counter
                counter = Counter(values)
                most_common_freq = counter.most_common(1)[0][1]
                
                stability = most_common_freq / total_values
                return stability
                
        except Exception as e:
            self.logger.error(f"Error calculating parameter stability: {e}")
            return 0.0


class OptimizationEngine:
    """Core optimization engine with multiple algorithms"""
    
    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        if config.random_seed is not None:
            np.random.seed(config.random_seed)
    
    def optimize_parameters(self, objective_function: Callable,
                          training_data: Any) -> Tuple[Dict[str, Any], float]:
        """Optimize parameters using specified method"""
        try:
            if self.config.optimization_method == OptimizationMethod.GRID_SEARCH:
                return self._grid_search_optimization(objective_function, training_data)
            elif self.config.optimization_method == OptimizationMethod.RANDOM_SEARCH:
                return self._random_search_optimization(objective_function, training_data)
            elif self.config.optimization_method == OptimizationMethod.BAYESIAN:
                return self._bayesian_optimization(objective_function, training_data)
            else:
                # Default to grid search
                return self._grid_search_optimization(objective_function, training_data)
                
        except Exception as e:
            self.logger.error(f"Error in parameter optimization: {e}")
            # Return default parameters
            default_params = {}
            for param_range in self.config.parameter_ranges:
                if param_range.values:
                    default_params[param_range.name] = param_range.values[0]
                else:
                    default_params[param_range.name] = param_range.min_value
            return default_params, 0.0
    
    def _grid_search_optimization(self, objective_function: Callable,
                                training_data: Any) -> Tuple[Dict[str, Any], float]:
        """Grid search optimization"""
        try:
            # Generate parameter grid
            param_grid = self._generate_parameter_grid()
            
            best_params = None
            best_score = float('-inf')
            
            for params in param_grid:
                try:
                    score = objective_function(params, training_data)
                    if score > best_score:
                        best_score = score
                        best_params = params.copy()
                except Exception as e:
                    self.logger.warning(f"Error evaluating parameters {params}: {e}")
                    continue
            
            return best_params or {}, best_score
            
        except Exception as e:
            self.logger.error(f"Error in grid search: {e}")
            return {}, 0.0
    
    def _random_search_optimization(self, objective_function: Callable,
                                  training_data: Any) -> Tuple[Dict[str, Any], float]:
        """Random search optimization"""
        try:
            best_params = None
            best_score = float('-inf')
            
            for _ in range(min(self.config.max_iterations, 100)):
                params = self._generate_random_parameters()
                
                try:
                    score = objective_function(params, training_data)
                    if score > best_score:
                        best_score = score
                        best_params = params.copy()
                except Exception as e:
                    self.logger.warning(f"Error evaluating parameters {params}: {e}")
                    continue
            
            return best_params or {}, best_score
            
        except Exception as e:
            self.logger.error(f"Error in random search: {e}")
            return {}, 0.0
    
    def _bayesian_optimization(self, objective_function: Callable,
                             training_data: Any) -> Tuple[Dict[str, Any], float]:
        """Bayesian optimization (simplified implementation)"""
        try:
            # For now, fall back to random search with some intelligence
            # In a full implementation, this would use Gaussian processes
            return self._random_search_optimization(objective_function, training_data)
            
        except Exception as e:
            self.logger.error(f"Error in Bayesian optimization: {e}")
            return {}, 0.0
    
    def _generate_parameter_grid(self) -> List[Dict[str, Any]]:
        """Generate parameter grid for grid search"""
        try:
            param_lists = []
            param_names = []
            
            for param_range in self.config.parameter_ranges:
                param_names.append(param_range.name)
                
                if param_range.values:
                    param_lists.append(param_range.values)
                else:
                    if param_range.parameter_type == "int":
                        step = int(param_range.step_size or 1)
                        values = list(range(int(param_range.min_value), 
                                          int(param_range.max_value) + 1, step))
                    else:
                        step = param_range.step_size or (param_range.max_value - param_range.min_value) / 10
                        values = []
                        current = param_range.min_value
                        while current <= param_range.max_value:
                            values.append(current)
                            current += step
                    
                    param_lists.append(values)
            
            # Generate all combinations
            param_grid = []
            for combination in itertools.product(*param_lists):
                params = dict(zip(param_names, combination))
                param_grid.append(params)
            
            return param_grid
            
        except Exception as e:
            self.logger.error(f"Error generating parameter grid: {e}")
            return []
    
    def _generate_random_parameters(self) -> Dict[str, Any]:
        """Generate random parameters"""
        try:
            params = {}
            
            for param_range in self.config.parameter_ranges:
                if param_range.values:
                    params[param_range.name] = np.random.choice(param_range.values)
                else:
                    if param_range.parameter_type == "int":
                        params[param_range.name] = np.random.randint(
                            int(param_range.min_value), 
                            int(param_range.max_value) + 1
                        )
                    else:
                        if param_range.distribution == "uniform":
                            params[param_range.name] = np.random.uniform(
                                param_range.min_value, param_range.max_value
                            )
                        elif param_range.distribution == "normal":
                            mean = (param_range.min_value + param_range.max_value) / 2
                            std = (param_range.max_value - param_range.min_value) / 6
                            value = np.random.normal(mean, std)
                            params[param_range.name] = np.clip(
                                value, param_range.min_value, param_range.max_value
                            )
                        else:
                            params[param_range.name] = np.random.uniform(
                                param_range.min_value, param_range.max_value
                            )
            
            return params
            
        except Exception as e:
            self.logger.error(f"Error generating random parameters: {e}")
            return {}


class WalkForwardOptimizer:
    """Main walk-forward optimization framework"""
    
    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.optimization_engine = OptimizationEngine(config)
        self.overfitting_detector = OverfittingDetector(config.overfitting_threshold)
        self.stability_analyzer = ParameterStabilityAnalyzer(config.stability_threshold)
        self.logger = logging.getLogger(__name__)
    
    async def run_walk_forward_optimization(self,
                                          data: pd.DataFrame,
                                          objective_function: Callable,
                                          evaluation_function: Callable) -> WalkForwardResults:
        """Run complete walk-forward optimization"""
        try:
            start_time = datetime.now()
            
            # Generate time windows
            time_windows = self._generate_time_windows(data)
            
            if not time_windows:
                raise ValueError("No valid time windows generated")
            
            # Run optimization for each window
            optimization_results = []
            
            if self.config.parallel_execution and len(time_windows) > 1:
                # Parallel execution
                optimization_results = await self._run_parallel_optimization(
                    time_windows, data, objective_function, evaluation_function
                )
            else:
                # Sequential execution
                for i, (train_start, train_end, test_start, test_end) in enumerate(time_windows):
                    self.logger.info(f"Processing window {i+1}/{len(time_windows)}")
                    
                    result = await self._optimize_single_window(
                        data, train_start, train_end, test_start, test_end,
                        objective_function, evaluation_function
                    )
                    
                    if result:
                        optimization_results.append(result)
            
            # Analyze results
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return self._analyze_results(optimization_results, execution_time)
            
        except Exception as e:
            self.logger.error(f"Error in walk-forward optimization: {e}")
            return WalkForwardResults(
                optimization_results=[],
                best_parameters={},
                parameter_stability={},
                overfitting_analysis={},
                performance_summary={},
                execution_time=0.0,
                metadata={"error": str(e)}
            )
    
    def _generate_time_windows(self, data: pd.DataFrame) -> List[Tuple[datetime, datetime, datetime, datetime]]:
        """Generate time windows for walk-forward optimization"""
        try:
            if 'timestamp' not in data.columns:
                raise ValueError("Data must have 'timestamp' column")
            
            data_sorted = data.sort_values('timestamp')
            start_date = data_sorted['timestamp'].iloc[0]
            end_date = data_sorted['timestamp'].iloc[-1]
            
            windows = []
            current_date = start_date
            
            while current_date + timedelta(days=self.config.training_window_days + self.config.testing_window_days) <= end_date:
                train_start = current_date
                train_end = current_date + timedelta(days=self.config.training_window_days)
                test_start = train_end
                test_end = test_start + timedelta(days=self.config.testing_window_days)
                
                # Check if we have enough data
                train_data = data_sorted[
                    (data_sorted['timestamp'] >= train_start) & 
                    (data_sorted['timestamp'] < train_end)
                ]
                
                if len(train_data) >= self.config.min_training_samples:
                    windows.append((train_start, train_end, test_start, test_end))
                
                current_date += timedelta(days=self.config.step_size_days)
            
            return windows
            
        except Exception as e:
            self.logger.error(f"Error generating time windows: {e}")
            return []
    
    async def _optimize_single_window(self,
                                    data: pd.DataFrame,
                                    train_start: datetime,
                                    train_end: datetime,
                                    test_start: datetime,
                                    test_end: datetime,
                                    objective_function: Callable,
                                    evaluation_function: Callable) -> Optional[OptimizationResult]:
        """Optimize parameters for a single time window"""
        try:
            window_start_time = datetime.now()
            
            # Split data
            train_data = data[
                (data['timestamp'] >= train_start) & 
                (data['timestamp'] < train_end)
            ].copy()
            
            test_data = data[
                (data['timestamp'] >= test_start) & 
                (data['timestamp'] < test_end)
            ].copy()
            
            if len(train_data) < self.config.min_training_samples or len(test_data) == 0:
                return None
            
            # Optimize parameters
            best_params, best_score = self.optimization_engine.optimize_parameters(
                objective_function, train_data
            )
            
            # Evaluate on training data
            in_sample_metrics = evaluation_function(best_params, train_data)
            
            # Evaluate on testing data
            out_of_sample_metrics = evaluation_function(best_params, test_data)
            
            # Calculate scores
            validation_score = out_of_sample_metrics.get('sharpe_ratio', 0.0)
            
            is_overfitted, overfitting_score = self.overfitting_detector.detect_overfitting(
                in_sample_metrics.get('sharpe_ratio', 0.0),
                out_of_sample_metrics.get('sharpe_ratio', 0.0)
            )
            
            # Calculate stability score (will be updated later with full results)
            stability_score = 1.0  # Placeholder
            
            optimization_time = (datetime.now() - window_start_time).total_seconds()
            
            return OptimizationResult(
                parameters=best_params,
                in_sample_metrics=in_sample_metrics,
                out_of_sample_metrics=out_of_sample_metrics,
                training_period=(train_start, train_end),
                testing_period=(test_start, test_end),
                optimization_time=optimization_time,
                validation_score=validation_score,
                overfitting_score=overfitting_score,
                stability_score=stability_score,
                metadata={
                    "train_samples": len(train_data),
                    "test_samples": len(test_data),
                    "is_overfitted": is_overfitted
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error optimizing single window: {e}")
            return None
    
    async def _run_parallel_optimization(self,
                                       time_windows: List[Tuple[datetime, datetime, datetime, datetime]],
                                       data: pd.DataFrame,
                                       objective_function: Callable,
                                       evaluation_function: Callable) -> List[OptimizationResult]:
        """Run optimization in parallel"""
        try:
            max_workers = self.config.max_workers or min(len(time_windows), mp.cpu_count())
            
            # For now, run sequentially as parallel execution of complex functions
            # requires careful serialization handling
            results = []
            for train_start, train_end, test_start, test_end in time_windows:
                result = await self._optimize_single_window(
                    data, train_start, train_end, test_start, test_end,
                    objective_function, evaluation_function
                )
                if result:
                    results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in parallel optimization: {e}")
            return []
    
    def _analyze_results(self, results: List[OptimizationResult], 
                        execution_time: float) -> WalkForwardResults:
        """Analyze optimization results"""
        try:
            if not results:
                return WalkForwardResults(
                    optimization_results=[],
                    best_parameters={},
                    parameter_stability={},
                    overfitting_analysis={},
                    performance_summary={},
                    execution_time=execution_time
                )
            
            # Parameter stability analysis
            parameter_stability = self.stability_analyzer.analyze_stability(results)
            
            # Update stability scores in results
            for result in results:
                param_stabilities = []
                for param_name in result.parameters.keys():
                    if param_name in parameter_stability:
                        param_stabilities.append(parameter_stability[param_name])
                
                result.stability_score = statistics.mean(param_stabilities) if param_stabilities else 1.0
            
            # Overfitting analysis
            overfitting_analysis = self.overfitting_detector.analyze_overfitting_pattern(results)
            
            # Find best parameters (highest average out-of-sample performance)
            best_parameters = self._find_best_parameters(results)
            
            # Performance summary
            performance_summary = self._calculate_performance_summary(results)
            
            return WalkForwardResults(
                optimization_results=results,
                best_parameters=best_parameters,
                parameter_stability=parameter_stability,
                overfitting_analysis=overfitting_analysis,
                performance_summary=performance_summary,
                execution_time=execution_time,
                metadata={
                    "total_windows": len(results),
                    "optimization_method": self.config.optimization_method.value,
                    "validation_method": self.config.validation_method.value
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing results: {e}")
            return WalkForwardResults(
                optimization_results=results,
                best_parameters={},
                parameter_stability={},
                overfitting_analysis={},
                performance_summary={},
                execution_time=execution_time,
                metadata={"error": str(e)}
            )
    
    def _find_best_parameters(self, results: List[OptimizationResult]) -> Dict[str, Any]:
        """Find best parameters based on out-of-sample performance"""
        try:
            if not results:
                return {}
            
            # Weight by out-of-sample performance and stability
            best_result = max(results, key=lambda r: (
                r.validation_score * r.stability_score * (1 - r.overfitting_score)
            ))
            
            return best_result.parameters.copy()
            
        except Exception as e:
            self.logger.error(f"Error finding best parameters: {e}")
            return {}
    
    def _calculate_performance_summary(self, results: List[OptimizationResult]) -> Dict[str, float]:
        """Calculate performance summary statistics"""
        try:
            if not results:
                return {}
            
            validation_scores = [r.validation_score for r in results]
            overfitting_scores = [r.overfitting_score for r in results]
            stability_scores = [r.stability_score for r in results]
            
            # Extract common metrics
            in_sample_returns = [r.in_sample_metrics.get('total_return', 0.0) for r in results]
            out_of_sample_returns = [r.out_of_sample_metrics.get('total_return', 0.0) for r in results]
            
            summary = {
                "mean_validation_score": statistics.mean(validation_scores),
                "median_validation_score": statistics.median(validation_scores),
                "std_validation_score": statistics.stdev(validation_scores) if len(validation_scores) > 1 else 0.0,
                "mean_overfitting_score": statistics.mean(overfitting_scores),
                "mean_stability_score": statistics.mean(stability_scores),
                "mean_in_sample_return": statistics.mean(in_sample_returns),
                "mean_out_of_sample_return": statistics.mean(out_of_sample_returns),
                "consistency_score": self._calculate_consistency_score(validation_scores),
                "robustness_score": self._calculate_robustness_score(results)
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error calculating performance summary: {e}")
            return {}
    
    def _calculate_consistency_score(self, scores: List[float]) -> float:
        """Calculate consistency score based on score stability"""
        try:
            if len(scores) <= 1:
                return 1.0
            
            mean_score = statistics.mean(scores)
            if mean_score == 0:
                return 0.0
            
            cv = statistics.stdev(scores) / abs(mean_score)
            consistency = max(0.0, 1.0 - cv)
            
            return consistency
            
        except Exception as e:
            self.logger.error(f"Error calculating consistency score: {e}")
            return 0.0
    
    def _calculate_robustness_score(self, results: List[OptimizationResult]) -> float:
        """Calculate robustness score based on multiple factors"""
        try:
            if not results:
                return 0.0
            
            # Factors: low overfitting, high stability, consistent performance
            overfitting_factor = 1.0 - statistics.mean([r.overfitting_score for r in results])
            stability_factor = statistics.mean([r.stability_score for r in results])
            
            validation_scores = [r.validation_score for r in results]
            consistency_factor = self._calculate_consistency_score(validation_scores)
            
            # Weighted average
            robustness = (overfitting_factor * 0.4 + 
                         stability_factor * 0.4 + 
                         consistency_factor * 0.2)
            
            return max(0.0, min(1.0, robustness))
            
        except Exception as e:
            self.logger.error(f"Error calculating robustness score: {e}")
            return 0.0


# Example usage and testing
async def example_usage():
    """Demonstrate walk-forward optimization"""
    print("=== Walk-Forward Optimization Demo ===")
    
    # Create sample data
    np.random.seed(42)
    dates = pd.date_range(start='2020-01-01', end='2023-12-31', freq='D')
    
    # Generate synthetic price data with some patterns
    returns = np.random.normal(0.0005, 0.02, len(dates))  # Daily returns
    prices = [100.0]
    for ret in returns:
        prices.append(prices[-1] * (1 + ret))
    
    data = pd.DataFrame({
        'timestamp': dates,
        'price': prices[1:],  # Remove initial price
        'volume': np.random.randint(1000, 10000, len(dates)),
        'returns': returns
    })
    
    print(f"Generated {len(data)} days of synthetic data")
    
    # Define parameter ranges for a simple moving average strategy
    parameter_ranges = [
        ParameterRange(
            name="short_window",
            min_value=5,
            max_value=20,
            step_size=5,
            parameter_type="int"
        ),
        ParameterRange(
            name="long_window",
            min_value=20,
            max_value=100,
            step_size=20,
            parameter_type="int"
        ),
        ParameterRange(
            name="threshold",
            min_value=0.001,
            max_value=0.01,
            step_size=0.002,
            parameter_type="float"
        )
    ]
    
    # Create optimization configuration
    config = OptimizationConfig(
        parameter_ranges=parameter_ranges,
        optimization_method=OptimizationMethod.GRID_SEARCH,
        training_window_days=252,  # 1 year
        testing_window_days=63,    # 3 months
        step_size_days=63,         # 3 months
        min_training_samples=100,
        max_iterations=100,
        parallel_execution=False,  # For demo
        random_seed=42
    )
    
    # Define objective function (simple moving average strategy)
    def objective_function(params: Dict[str, Any], train_data: pd.DataFrame) -> float:
        """Simple moving average strategy objective function"""
        try:
            short_window = int(params['short_window'])
            long_window = int(params['long_window'])
            threshold = float(params['threshold'])
            
            if short_window >= long_window:
                return -1.0  # Invalid parameters
            
            # Calculate moving averages
            train_data = train_data.copy()
            train_data['short_ma'] = train_data['price'].rolling(window=short_window).mean()
            train_data['long_ma'] = train_data['price'].rolling(window=long_window).mean()
            
            # Generate signals
            train_data['signal'] = 0
            train_data.loc[train_data['short_ma'] > train_data['long_ma'] * (1 + threshold), 'signal'] = 1
            train_data.loc[train_data['short_ma'] < train_data['long_ma'] * (1 - threshold), 'signal'] = -1
            
            # Calculate strategy returns
            train_data['strategy_returns'] = train_data['signal'].shift(1) * train_data['returns']
            
            # Calculate Sharpe ratio
            strategy_returns = train_data['strategy_returns'].dropna()
            if len(strategy_returns) == 0 or strategy_returns.std() == 0:
                return -1.0
            
            sharpe_ratio = strategy_returns.mean() / strategy_returns.std() * np.sqrt(252)
            return sharpe_ratio
            
        except Exception as e:
            print(f"Error in objective function: {e}")
            return -1.0
    
    # Define evaluation function
    def evaluation_function(params: Dict[str, Any], eval_data: pd.DataFrame) -> Dict[str, float]:
        """Evaluate strategy performance"""
        try:
            short_window = int(params['short_window'])
            long_window = int(params['long_window'])
            threshold = float(params['threshold'])
            
            # Calculate moving averages
            eval_data = eval_data.copy()
            eval_data['short_ma'] = eval_data['price'].rolling(window=short_window).mean()
            eval_data['long_ma'] = eval_data['price'].rolling(window=long_window).mean()
            
            # Generate signals
            eval_data['signal'] = 0
            eval_data.loc[eval_data['short_ma'] > eval_data['long_ma'] * (1 + threshold), 'signal'] = 1
            eval_data.loc[eval_data['short_ma'] < eval_data['long_ma'] * (1 - threshold), 'signal'] = -1
            
            # Calculate strategy returns
            eval_data['strategy_returns'] = eval_data['signal'].shift(1) * eval_data['returns']
            
            # Calculate metrics
            strategy_returns = eval_data['strategy_returns'].dropna()
            
            if len(strategy_returns) == 0:
                return {
                    'total_return': 0.0,
                    'sharpe_ratio': 0.0,
                    'max_drawdown': 0.0,
                    'win_rate': 0.0
                }
            
            total_return = (1 + strategy_returns).prod() - 1
            sharpe_ratio = strategy_returns.mean() / strategy_returns.std() * np.sqrt(252) if strategy_returns.std() > 0 else 0.0
            
            # Calculate max drawdown
            cumulative_returns = (1 + strategy_returns).cumprod()
            rolling_max = cumulative_returns.expanding().max()
            drawdowns = (cumulative_returns - rolling_max) / rolling_max
            max_drawdown = drawdowns.min()
            
            # Calculate win rate
            win_rate = (strategy_returns > 0).mean()
            
            return {
                'total_return': total_return,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'win_rate': win_rate
            }
            
        except Exception as e:
            print(f"Error in evaluation function: {e}")
            return {
                'total_return': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 0.0
            }
    
    # Run walk-forward optimization
    print("\\nRunning walk-forward optimization...")
    optimizer = WalkForwardOptimizer(config)
    
    results = await optimizer.run_walk_forward_optimization(
        data, objective_function, evaluation_function
    )
    
    # Display results
    print(f"\\n=== Optimization Results ===")
    print(f"Execution time: {results.execution_time:.2f} seconds")
    print(f"Total windows: {len(results.optimization_results)}")
    
    print(f"\\nBest parameters:")
    for param, value in results.best_parameters.items():
        print(f"  {param}: {value}")
    
    print(f"\\nParameter stability:")
    for param, stability in results.parameter_stability.items():
        print(f"  {param}: {stability:.3f}")
    
    print(f"\\nPerformance summary:")
    for metric, value in results.performance_summary.items():
        print(f"  {metric}: {value:.4f}")
    
    print(f"\\nOverfitting analysis:")
    for metric, value in results.overfitting_analysis.items():
        print(f"  {metric}: {value}")
    
    # Show individual window results
    print(f"\\n=== Individual Window Results ===")
    for i, result in enumerate(results.optimization_results[:3]):  # Show first 3
        print(f"\\nWindow {i+1}:")
        print(f"  Training: {result.training_period[0].date()} to {result.training_period[1].date()}")
        print(f"  Testing: {result.testing_period[0].date()} to {result.testing_period[1].date()}")
        print(f"  Parameters: {result.parameters}")
        print(f"  In-sample Sharpe: {result.in_sample_metrics.get('sharpe_ratio', 0):.3f}")
        print(f"  Out-of-sample Sharpe: {result.out_of_sample_metrics.get('sharpe_ratio', 0):.3f}")
        print(f"  Overfitting score: {result.overfitting_score:.3f}")
        print(f"  Stability score: {result.stability_score:.3f}")
    
    print("\\nWalk-forward optimization demo completed!")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run example
    asyncio.run(example_usage())