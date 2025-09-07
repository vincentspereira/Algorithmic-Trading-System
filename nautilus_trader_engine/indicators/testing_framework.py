"""Comprehensive Testing Framework for Volume-Weighted Indicators

Provides unit testing, integration testing, performance benchmarking,
and stress testing capabilities for institutional-grade trading indicators.
"""

import unittest
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Tuple
from collections import defaultdict
import threading
import multiprocessing
import gc
import psutil
import logging
from dataclasses import dataclass
from abc import ABC, abstractmethod

from .base import VolumeWeightedIndicator, IndicatorConfig
from .error_handling import get_error_manager, ErrorSeverity
from .hft_optimizations import HFTPerformanceMonitor

logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Test result container"""
    test_name: str
    passed: bool
    execution_time: float
    memory_usage: float
    error_message: str = ""
    performance_metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.performance_metrics is None:
            self.performance_metrics = {}

@dataclass
class BenchmarkResult:
    """Benchmark result container"""
    indicator_name: str
    data_points: int
    avg_execution_time: float
    min_execution_time: float
    max_execution_time: float
    std_execution_time: float
    throughput_ops_per_sec: float
    memory_usage_mb: float
    cpu_usage_percent: float
    error_rate: float
    
class MarketDataGenerator:
    """Generate realistic market data for testing"""
    
    def __init__(self, seed: int = 42):
        np.random.seed(seed)
        self.seed = seed
    
    def generate_ohlcv_data(self, num_points: int, 
                           base_price: float = 100.0,
                           volatility: float = 0.02,
                           trend: float = 0.0,
                           volume_base: float = 1000000) -> pd.DataFrame:
        """Generate realistic OHLCV data"""
        timestamps = pd.date_range(
            start=datetime.now() - timedelta(minutes=num_points),
            periods=num_points,
            freq='1min'
        )
        
        # Generate price series with trend and volatility
        returns = np.random.normal(trend/num_points, volatility, num_points)
        prices = [base_price]
        
        for i in range(1, num_points):
            new_price = prices[-1] * (1 + returns[i])
            prices.append(max(new_price, 0.01))  # Prevent negative prices
        
        # Generate OHLC from price series
        data = []
        for i, price in enumerate(prices):
            # Add some intrabar volatility
            noise = np.random.normal(0, volatility * 0.5, 4)
            high = price * (1 + abs(noise[0]))
            low = price * (1 - abs(noise[1]))
            open_price = price * (1 + noise[2])
            close_price = price * (1 + noise[3])
            
            # Ensure OHLC consistency
            high = max(high, open_price, close_price)
            low = min(low, open_price, close_price)
            
            # Generate volume with some correlation to price movement
            volume_multiplier = 1 + abs(returns[i]) * 5  # Higher volume on big moves
            volume = volume_base * volume_multiplier * np.random.uniform(0.5, 2.0)
            
            data.append({
                'timestamp': timestamps[i],
                'open': open_price,
                'high': high,
                'low': low,
                'close': close_price,
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
    def generate_tick_data(self, num_ticks: int,
                          base_price: float = 100.0,
                          volatility: float = 0.001) -> pd.DataFrame:
        """Generate high-frequency tick data"""
        timestamps = pd.date_range(
            start=datetime.now() - timedelta(seconds=num_ticks),
            periods=num_ticks,
            freq='1s'
        )
        
        # Generate tick prices
        returns = np.random.normal(0, volatility, num_ticks)
        prices = [base_price]
        
        for i in range(1, num_ticks):
            new_price = prices[-1] * (1 + returns[i])
            prices.append(max(new_price, 0.01))
        
        # Generate volumes
        volumes = np.random.exponential(1000, num_ticks)
        
        data = []
        for i in range(num_ticks):
            data.append({
                'timestamp': timestamps[i],
                'price': prices[i],
                'volume': volumes[i]
            })
        
        return pd.DataFrame(data)
    
    def generate_stress_test_data(self, scenario: str) -> pd.DataFrame:
        """Generate data for specific stress test scenarios"""
        if scenario == "flash_crash":
            return self._generate_flash_crash_data()
        elif scenario == "high_volatility":
            return self._generate_high_volatility_data()
        elif scenario == "low_liquidity":
            return self._generate_low_liquidity_data()
        elif scenario == "market_gaps":
            return self._generate_gap_data()
        elif scenario == "extreme_volumes":
            return self._generate_extreme_volume_data()
        else:
            raise ValueError(f"Unknown stress test scenario: {scenario}")
    
    def _generate_flash_crash_data(self) -> pd.DataFrame:
        """Generate flash crash scenario data"""
        data = self.generate_ohlcv_data(1000, volatility=0.01)
        
        # Insert flash crash at 30% point
        crash_point = int(len(data) * 0.3)
        crash_magnitude = 0.15  # 15% drop
        
        for i in range(crash_point, crash_point + 10):
            if i < len(data):
                data.loc[i, 'close'] *= (1 - crash_magnitude * (i - crash_point + 1) / 10)
                data.loc[i, 'low'] = min(data.loc[i, 'low'], data.loc[i, 'close'])
                data.loc[i, 'volume'] *= 10  # Spike in volume
        
        return data
    
    def _generate_high_volatility_data(self) -> pd.DataFrame:
        """Generate high volatility scenario data"""
        return self.generate_ohlcv_data(1000, volatility=0.05)
    
    def _generate_low_liquidity_data(self) -> pd.DataFrame:
        """Generate low liquidity scenario data"""
        data = self.generate_ohlcv_data(1000, volume_base=10000)  # Very low volume
        # Add some zero volume periods
        zero_volume_indices = np.random.choice(len(data), size=int(len(data) * 0.1), replace=False)
        data.loc[zero_volume_indices, 'volume'] = 0
        return data
    
    def _generate_gap_data(self) -> pd.DataFrame:
        """Generate data with price gaps"""
        data = self.generate_ohlcv_data(1000)
        
        # Insert gaps at random points
        gap_points = np.random.choice(len(data) - 1, size=5, replace=False)
        
        for gap_point in gap_points:
            gap_size = np.random.uniform(0.02, 0.05)  # 2-5% gap
            gap_direction = np.random.choice([-1, 1])
            
            for i in range(gap_point + 1, len(data)):
                data.loc[i, ['open', 'high', 'low', 'close']] *= (1 + gap_size * gap_direction)
        
        return data
    
    def _generate_extreme_volume_data(self) -> pd.DataFrame:
        """Generate data with extreme volume spikes"""
        data = self.generate_ohlcv_data(1000)
        
        # Add extreme volume spikes
        spike_points = np.random.choice(len(data), size=10, replace=False)
        
        for spike_point in spike_points:
            data.loc[spike_point, 'volume'] *= np.random.uniform(50, 200)
        
        return data

class IndicatorTester:
    """Comprehensive indicator testing framework"""
    
    def __init__(self):
        self.data_generator = MarketDataGenerator()
        self.performance_monitor = HFTPerformanceMonitor()
        self.test_results = []
        self.benchmark_results = []
        
    def run_unit_tests(self, indicator_class, config: IndicatorConfig) -> List[TestResult]:
        """Run comprehensive unit tests for an indicator"""
        results = []
        
        # Test basic functionality
        results.extend(self._test_basic_functionality(indicator_class, config))
        
        # Test edge cases
        results.extend(self._test_edge_cases(indicator_class, config))
        
        # Test error handling
        results.extend(self._test_error_handling(indicator_class, config))
        
        # Test configuration validation
        results.extend(self._test_config_validation(indicator_class, config))
        
        return results
    
    def _test_basic_functionality(self, indicator_class, config: IndicatorConfig) -> List[TestResult]:
        """Test basic indicator functionality"""
        results = []
        
        # Test initialization
        start_time = time.time()
        try:
            indicator = indicator_class(config)
            execution_time = time.time() - start_time
            memory_usage = psutil.Process().memory_info().rss / 1024 / 1024
            
            results.append(TestResult(
                test_name="initialization",
                passed=True,
                execution_time=execution_time,
                memory_usage=memory_usage
            ))
        except Exception as e:
            results.append(TestResult(
                test_name="initialization",
                passed=False,
                execution_time=time.time() - start_time,
                memory_usage=0,
                error_message=str(e)
            ))
        
        # Test calculation with normal data
        if results[-1].passed:
            try:
                data = self.data_generator.generate_ohlcv_data(100)
                
                start_time = time.time()
                for _, row in data.iterrows():
                    result = indicator.calculate(
                        price=row['close'],
                        volume=row['volume'],
                        timestamp=row['timestamp']
                    )
                
                execution_time = time.time() - start_time
                memory_usage = psutil.Process().memory_info().rss / 1024 / 1024
                
                results.append(TestResult(
                    test_name="normal_calculation",
                    passed=True,
                    execution_time=execution_time,
                    memory_usage=memory_usage,
                    performance_metrics={
                        'data_points': len(data),
                        'avg_time_per_point': execution_time / len(data)
                    }
                ))
            except Exception as e:
                results.append(TestResult(
                    test_name="normal_calculation",
                    passed=False,
                    execution_time=time.time() - start_time,
                    memory_usage=0,
                    error_message=str(e)
                ))
        
        return results
    
    def _test_edge_cases(self, indicator_class, config: IndicatorConfig) -> List[TestResult]:
        """Test edge cases"""
        results = []
        
        edge_cases = [
            ("zero_volume", {"price": 100.0, "volume": 0.0}),
            ("zero_price", {"price": 0.0, "volume": 1000.0}),
            ("negative_price", {"price": -100.0, "volume": 1000.0}),
            ("very_large_price", {"price": 1e10, "volume": 1000.0}),
            ("very_small_price", {"price": 1e-10, "volume": 1000.0}),
            ("very_large_volume", {"price": 100.0, "volume": 1e12}),
            ("nan_price", {"price": np.nan, "volume": 1000.0}),
            ("inf_price", {"price": np.inf, "volume": 1000.0}),
            ("nan_volume", {"price": 100.0, "volume": np.nan}),
        ]
        
        for case_name, params in edge_cases:
            try:
                indicator = indicator_class(config)
                start_time = time.time()
                
                result = indicator.calculate(
                    price=params["price"],
                    volume=params["volume"],
                    timestamp=datetime.now()
                )
                
                execution_time = time.time() - start_time
                memory_usage = psutil.Process().memory_info().rss / 1024 / 1024
                
                # Check if result is reasonable
                passed = True
                if result is not None:
                    if isinstance(result, (int, float)):
                        passed = not (np.isnan(result) or np.isinf(result))
                
                results.append(TestResult(
                    test_name=f"edge_case_{case_name}",
                    passed=passed,
                    execution_time=execution_time,
                    memory_usage=memory_usage
                ))
                
            except Exception as e:
                results.append(TestResult(
                    test_name=f"edge_case_{case_name}",
                    passed=False,
                    execution_time=0,
                    memory_usage=0,
                    error_message=str(e)
                ))
        
        return results
    
    def _test_error_handling(self, indicator_class, config: IndicatorConfig) -> List[TestResult]:
        """Test error handling capabilities"""
        results = []
        
        try:
            indicator = indicator_class(config)
            
            # Test with invalid input types
            invalid_inputs = [
                ("string_price", {"price": "invalid", "volume": 1000.0}),
                ("string_volume", {"price": 100.0, "volume": "invalid"}),
                ("none_price", {"price": None, "volume": 1000.0}),
                ("none_volume", {"price": 100.0, "volume": None}),
            ]
            
            for case_name, params in invalid_inputs:
                start_time = time.time()
                try:
                    result = indicator.calculate(
                        price=params["price"],
                        volume=params["volume"],
                        timestamp=datetime.now()
                    )
                    
                    # Should either handle gracefully or raise appropriate error
                    passed = True
                    
                except (ValueError, TypeError) as e:
                    # Expected error types
                    passed = True
                except Exception as e:
                    # Unexpected error
                    passed = False
                
                execution_time = time.time() - start_time
                
                results.append(TestResult(
                    test_name=f"error_handling_{case_name}",
                    passed=passed,
                    execution_time=execution_time,
                    memory_usage=0
                ))
        
        except Exception as e:
            results.append(TestResult(
                test_name="error_handling_setup",
                passed=False,
                execution_time=0,
                memory_usage=0,
                error_message=str(e)
            ))
        
        return results
    
    def _test_config_validation(self, indicator_class, config: IndicatorConfig) -> List[TestResult]:
        """Test configuration validation"""
        results = []
        
        # Test with invalid configurations
        invalid_configs = [
            ("negative_period", {"period": -1}),
            ("zero_period", {"period": 0}),
            ("very_large_period", {"period": 10000}),
        ]
        
        for case_name, invalid_params in invalid_configs:
            try:
                # Create invalid config
                invalid_config = IndicatorConfig(
                    name=config.name,
                    **{**config.__dict__, **invalid_params}
                )
                
                start_time = time.time()
                try:
                    indicator = indicator_class(invalid_config)
                    passed = False  # Should have raised an error
                except (ValueError, TypeError):
                    passed = True  # Expected validation error
                except Exception:
                    passed = False  # Unexpected error type
                
                execution_time = time.time() - start_time
                
                results.append(TestResult(
                    test_name=f"config_validation_{case_name}",
                    passed=passed,
                    execution_time=execution_time,
                    memory_usage=0
                ))
                
            except Exception as e:
                results.append(TestResult(
                    test_name=f"config_validation_{case_name}",
                    passed=False,
                    execution_time=0,
                    memory_usage=0,
                    error_message=str(e)
                ))
        
        return results
    
    def run_performance_benchmark(self, indicator_class, config: IndicatorConfig,
                                data_sizes: List[int] = None) -> List[BenchmarkResult]:
        """Run performance benchmarks"""
        if data_sizes is None:
            data_sizes = [100, 1000, 10000, 100000]
        
        results = []
        
        for data_size in data_sizes:
            logger.info(f"Running benchmark for {indicator_class.__name__} with {data_size} data points")
            
            # Generate test data
            data = self.data_generator.generate_ohlcv_data(data_size)
            
            # Initialize indicator
            indicator = indicator_class(config)
            
            # Warm up
            for i in range(min(10, len(data))):
                row = data.iloc[i]
                indicator.calculate(
                    price=row['close'],
                    volume=row['volume'],
                    timestamp=row['timestamp']
                )
            
            # Reset for actual benchmark
            indicator.reset()
            
            # Benchmark
            execution_times = []
            error_count = 0
            
            # Monitor system resources
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024
            cpu_percent_start = process.cpu_percent()
            
            start_time = time.time()
            
            for _, row in data.iterrows():
                calc_start = time.time()
                try:
                    result = indicator.calculate(
                        price=row['close'],
                        volume=row['volume'],
                        timestamp=row['timestamp']
                    )
                    calc_time = time.time() - calc_start
                    execution_times.append(calc_time)
                except Exception as e:
                    error_count += 1
                    logger.warning(f"Calculation error: {e}")
            
            total_time = time.time() - start_time
            final_memory = process.memory_info().rss / 1024 / 1024
            cpu_percent_end = process.cpu_percent()
            
            # Calculate statistics
            if execution_times:
                avg_time = np.mean(execution_times)
                min_time = np.min(execution_times)
                max_time = np.max(execution_times)
                std_time = np.std(execution_times)
                throughput = len(execution_times) / total_time
            else:
                avg_time = min_time = max_time = std_time = throughput = 0
            
            results.append(BenchmarkResult(
                indicator_name=indicator_class.__name__,
                data_points=data_size,
                avg_execution_time=avg_time,
                min_execution_time=min_time,
                max_execution_time=max_time,
                std_execution_time=std_time,
                throughput_ops_per_sec=throughput,
                memory_usage_mb=final_memory - initial_memory,
                cpu_usage_percent=(cpu_percent_end - cpu_percent_start),
                error_rate=error_count / data_size if data_size > 0 else 0
            ))
        
        return results
    
    def run_stress_tests(self, indicator_class, config: IndicatorConfig) -> List[TestResult]:
        """Run stress tests with extreme market conditions"""
        results = []
        
        stress_scenarios = [
            "flash_crash",
            "high_volatility",
            "low_liquidity",
            "market_gaps",
            "extreme_volumes"
        ]
        
        for scenario in stress_scenarios:
            logger.info(f"Running stress test: {scenario}")
            
            try:
                # Generate stress test data
                data = self.data_generator.generate_stress_test_data(scenario)
                
                # Initialize indicator
                indicator = indicator_class(config)
                
                start_time = time.time()
                error_count = 0
                
                for _, row in data.iterrows():
                    try:
                        result = indicator.calculate(
                            price=row['close'],
                            volume=row['volume'],
                            timestamp=row['timestamp']
                        )
                    except Exception as e:
                        error_count += 1
                        logger.debug(f"Error in {scenario}: {e}")
                
                execution_time = time.time() - start_time
                memory_usage = psutil.Process().memory_info().rss / 1024 / 1024
                
                # Consider test passed if error rate is below 10%
                error_rate = error_count / len(data)
                passed = error_rate < 0.1
                
                results.append(TestResult(
                    test_name=f"stress_test_{scenario}",
                    passed=passed,
                    execution_time=execution_time,
                    memory_usage=memory_usage,
                    performance_metrics={
                        'data_points': len(data),
                        'error_count': error_count,
                        'error_rate': error_rate
                    }
                ))
                
            except Exception as e:
                results.append(TestResult(
                    test_name=f"stress_test_{scenario}",
                    passed=False,
                    execution_time=0,
                    memory_usage=0,
                    error_message=str(e)
                ))
        
        return results
    
    def run_concurrent_tests(self, indicator_class, config: IndicatorConfig,
                           num_threads: int = 4) -> List[TestResult]:
        """Run concurrent access tests"""
        results = []
        
        def worker_function(worker_id: int, shared_results: List):
            """Worker function for concurrent testing"""
            try:
                # Each worker gets its own indicator instance
                indicator = indicator_class(config)
                data = self.data_generator.generate_ohlcv_data(1000)
                
                start_time = time.time()
                error_count = 0
                
                for _, row in data.iterrows():
                    try:
                        result = indicator.calculate(
                            price=row['close'],
                            volume=row['volume'],
                            timestamp=row['timestamp']
                        )
                    except Exception as e:
                        error_count += 1
                
                execution_time = time.time() - start_time
                
                shared_results.append({
                    'worker_id': worker_id,
                    'execution_time': execution_time,
                    'error_count': error_count,
                    'data_points': len(data)
                })
                
            except Exception as e:
                shared_results.append({
                    'worker_id': worker_id,
                    'error': str(e)
                })
        
        # Run concurrent test
        shared_results = []
        threads = []
        
        start_time = time.time()
        
        for i in range(num_threads):
            thread = threading.Thread(
                target=worker_function,
                args=(i, shared_results)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Analyze results
        successful_workers = [r for r in shared_results if 'error' not in r]
        failed_workers = [r for r in shared_results if 'error' in r]
        
        passed = len(failed_workers) == 0
        total_errors = sum(r.get('error_count', 0) for r in successful_workers)
        total_data_points = sum(r.get('data_points', 0) for r in successful_workers)
        
        results.append(TestResult(
            test_name="concurrent_access",
            passed=passed,
            execution_time=total_time,
            memory_usage=psutil.Process().memory_info().rss / 1024 / 1024,
            performance_metrics={
                'num_threads': num_threads,
                'successful_workers': len(successful_workers),
                'failed_workers': len(failed_workers),
                'total_errors': total_errors,
                'total_data_points': total_data_points,
                'error_rate': total_errors / total_data_points if total_data_points > 0 else 0
            }
        ))
        
        return results
    
    def generate_test_report(self, test_results: List[TestResult],
                           benchmark_results: List[BenchmarkResult] = None) -> str:
        """Generate comprehensive test report"""
        report = []
        report.append("# Indicator Testing Report")
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")
        
        # Summary statistics
        total_tests = len(test_results)
        passed_tests = sum(1 for r in test_results if r.passed)
        failed_tests = total_tests - passed_tests
        
        report.append("## Test Summary")
        report.append(f"- Total Tests: {total_tests}")
        report.append(f"- Passed: {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
        report.append(f"- Failed: {failed_tests} ({failed_tests/total_tests*100:.1f}%)")
        report.append("")
        
        # Detailed test results
        report.append("## Detailed Test Results")
        for result in test_results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            report.append(f"### {result.test_name} - {status}")
            report.append(f"- Execution Time: {result.execution_time:.4f}s")
            report.append(f"- Memory Usage: {result.memory_usage:.2f}MB")
            
            if result.error_message:
                report.append(f"- Error: {result.error_message}")
            
            if result.performance_metrics:
                report.append("- Performance Metrics:")
                for key, value in result.performance_metrics.items():
                    report.append(f"  - {key}: {value}")
            
            report.append("")
        
        # Benchmark results
        if benchmark_results:
            report.append("## Performance Benchmarks")
            for result in benchmark_results:
                report.append(f"### {result.indicator_name} - {result.data_points} data points")
                report.append(f"- Average Execution Time: {result.avg_execution_time*1000:.3f}ms")
                report.append(f"- Min/Max Time: {result.min_execution_time*1000:.3f}ms / {result.max_execution_time*1000:.3f}ms")
                report.append(f"- Throughput: {result.throughput_ops_per_sec:.0f} ops/sec")
                report.append(f"- Memory Usage: {result.memory_usage_mb:.2f}MB")
                report.append(f"- CPU Usage: {result.cpu_usage_percent:.1f}%")
                report.append(f"- Error Rate: {result.error_rate*100:.2f}%")
                report.append("")
        
        return "\n".join(report)

def run_comprehensive_test_suite(indicator_class, config: IndicatorConfig) -> str:
    """Run complete test suite for an indicator"""
    logger.info(f"Starting comprehensive test suite for {indicator_class.__name__}")
    
    tester = IndicatorTester()
    all_results = []
    
    # Run unit tests
    logger.info("Running unit tests...")
    unit_results = tester.run_unit_tests(indicator_class, config)
    all_results.extend(unit_results)
    
    # Run stress tests
    logger.info("Running stress tests...")
    stress_results = tester.run_stress_tests(indicator_class, config)
    all_results.extend(stress_results)
    
    # Run concurrent tests
    logger.info("Running concurrent tests...")
    concurrent_results = tester.run_concurrent_tests(indicator_class, config)
    all_results.extend(concurrent_results)
    
    # Run performance benchmarks
    logger.info("Running performance benchmarks...")
    benchmark_results = tester.run_performance_benchmark(indicator_class, config)
    
    # Generate report
    report = tester.generate_test_report(all_results, benchmark_results)
    
    logger.info(f"Test suite completed for {indicator_class.__name__}")
    return report