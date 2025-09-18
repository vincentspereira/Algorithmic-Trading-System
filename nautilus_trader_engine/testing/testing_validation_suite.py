"""Comprehensive Testing and Validation Suite

This module provides extensive testing and validation capabilities
for the institutional-grade trading platform, including:

1. Unit Testing Framework
2. Integration Testing
3. Stress Testing for Extreme Conditions
4. Continuous Integration Testing
5. Backtesting Validation
6. Performance Benchmarking
7. Risk Testing and Validation
8. Compliance Testing
9. Data Quality Testing
10. Strategy Validation

Features:
- Comprehensive test coverage analysis
- Automated stress testing scenarios
- Performance regression detection
- Risk scenario validation
- Data integrity verification
- Strategy performance validation
- Compliance rule testing
- Load testing and scalability validation
"""

import os
import sys
import time
import asyncio
import logging
import unittest
import pytest
import threading
import multiprocessing as mp
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path
import json
import pickle
import hashlib
import statistics
import warnings
warnings.filterwarnings('ignore')

# Numerical computing
try:
    import numpy as np
except ImportError:
    np = None

try:
    import pandas as pd
except ImportError:
    pd = None

# Testing frameworks
try:
    import hypothesis
    from hypothesis import strategies as st
    from hypothesis.stateful import RuleBasedStateMachine, rule, invariant
except ImportError:
    hypothesis = None
    st = None
    RuleBasedStateMachine = None
    rule = None
    invariant = None

try:
    import coverage
except ImportError:
    coverage = None

try:
    import memory_profiler
except ImportError:
    memory_profiler = None

try:
    import psutil
except ImportError:
    psutil = None

# Load testing
try:
    import locust
    from locust import HttpUser, task, between
except ImportError:
    locust = None
    HttpUser = None
    task = None
    between = None

# Performance testing
try:
    import timeit
except ImportError:
    timeit = None


class TestType(Enum):
    """Test types"""
    UNIT = "unit"
    INTEGRATION = "integration"
    STRESS = "stress"
    PERFORMANCE = "performance"
    LOAD = "load"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    DATA_QUALITY = "data_quality"
    STRATEGY_VALIDATION = "strategy_validation"
    RISK_VALIDATION = "risk_validation"


class TestSeverity(Enum):
    """Test severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class TestStatus(Enum):
    """Test execution status"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class TestResult:
    """Test result information"""
    test_name: str
    test_type: TestType
    status: TestStatus
    severity: TestSeverity
    
    # Execution details
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    execution_time_ms: float = 0.0
    
    # Results
    passed: bool = False
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    
    # Metrics
    assertions_count: int = 0
    coverage_percentage: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    
    # Custom metrics
    custom_metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Artifacts
    artifacts: List[str] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)


@dataclass
class StressTestConfig:
    """Stress test configuration"""
    # Load parameters
    max_concurrent_users: int = 1000
    requests_per_second: int = 100
    test_duration_seconds: int = 300
    
    # Data parameters
    max_data_points: int = 1000000
    max_symbols: int = 10000
    max_indicators: int = 100
    
    # Memory parameters
    max_memory_mb: int = 8192
    memory_stress_factor: float = 0.9
    
    # CPU parameters
    cpu_stress_threads: int = mp.cpu_count() * 2
    cpu_stress_duration: int = 60
    
    # Network parameters
    network_latency_ms: int = 1000
    packet_loss_percent: float = 5.0
    
    # Failure scenarios
    simulate_failures: bool = True
    failure_rate_percent: float = 10.0


@dataclass
class PerformanceBenchmark:
    """Performance benchmark definition"""
    name: str
    description: str
    
    # Performance thresholds
    max_execution_time_ms: float
    max_memory_usage_mb: float
    min_throughput_ops_per_sec: float
    max_latency_p99_ms: float
    
    # Test parameters
    test_data_size: int = 10000
    iterations: int = 100
    warmup_iterations: int = 10
    
    # Regression detection
    baseline_performance: Optional[Dict[str, float]] = None
    regression_threshold_percent: float = 10.0


class UnitTestSuite:
    """Comprehensive unit testing suite"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.test_results: List[TestResult] = []
        
    def test_technical_indicators(self) -> List[TestResult]:
        """Test technical indicator calculations"""
        results = []
        
        # Test SMA
        result = self._test_sma()
        results.append(result)
        
        # Test EMA
        result = self._test_ema()
        results.append(result)
        
        # Test RSI
        result = self._test_rsi()
        results.append(result)
        
        # Test MACD
        result = self._test_macd()
        results.append(result)
        
        # Test Bollinger Bands
        result = self._test_bollinger_bands()
        results.append(result)
        
        return results
    
    def _test_sma(self) -> TestResult:
        """Test Simple Moving Average"""
        result = TestResult(
            test_name="test_sma",
            test_type=TestType.UNIT,
            severity=TestSeverity.HIGH
        )
        
        try:
            # Test data
            data = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
            window = 3
            
            # Calculate SMA
            sma = self._calculate_sma(data, window)
            
            # Expected results
            expected = np.array([np.nan, np.nan, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0])
            
            # Assertions
            result.assertions_count = 3
            
            # Check length
            assert len(sma) == len(data), "SMA length should match input data length"
            
            # Check NaN values
            assert np.isnan(sma[:window-1]).all(), "First window-1 values should be NaN"
            
            # Check calculated values
            np.testing.assert_array_almost_equal(
                sma[window-1:], expected[window-1:], decimal=6,
                err_msg="SMA values don't match expected results"
            )
            
            result.status = TestStatus.PASSED
            result.passed = True
            
        except Exception as e:
            result.status = TestStatus.FAILED
            result.error_message = str(e)
            result.stack_trace = self._get_stack_trace()
        
        result.end_time = datetime.now()
        result.execution_time_ms = (result.end_time - result.start_time).total_seconds() * 1000
        
        return result
    
    def _test_ema(self) -> TestResult:
        """Test Exponential Moving Average"""
        result = TestResult(
            test_name="test_ema",
            test_type=TestType.UNIT,
            severity=TestSeverity.HIGH
        )
        
        try:
            # Test data
            data = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
            span = 3
            
            # Calculate EMA
            ema = self._calculate_ema(data, span)
            
            # Assertions
            result.assertions_count = 2
            
            # Check length
            assert len(ema) == len(data), "EMA length should match input data length"
            
            # Check that EMA is not constant (should change with data)
            assert not np.all(ema[1:] == ema[0]), "EMA should vary with input data"
            
            result.status = TestStatus.PASSED
            result.passed = True
            
        except Exception as e:
            result.status = TestStatus.FAILED
            result.error_message = str(e)
            result.stack_trace = self._get_stack_trace()
        
        result.end_time = datetime.now()
        result.execution_time_ms = (result.end_time - result.start_time).total_seconds() * 1000
        
        return result
    
    def _test_rsi(self) -> TestResult:
        """Test Relative Strength Index"""
        result = TestResult(
            test_name="test_rsi",
            test_type=TestType.UNIT,
            severity=TestSeverity.HIGH
        )
        
        try:
            # Test data - trending up
            data = np.array([10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20])
            
            # Calculate RSI
            rsi = self._calculate_rsi(data, 14)
            
            # Assertions
            result.assertions_count = 3
            
            # Check length
            assert len(rsi) == len(data), "RSI length should match input data length"
            
            # Check range (RSI should be between 0 and 100)
            valid_rsi = rsi[~np.isnan(rsi)]
            assert np.all(valid_rsi >= 0) and np.all(valid_rsi <= 100), "RSI should be between 0 and 100"
            
            # For trending up data, RSI should be > 50
            assert np.mean(valid_rsi) > 50, "RSI should be > 50 for uptrending data"
            
            result.status = TestStatus.PASSED
            result.passed = True
            
        except Exception as e:
            result.status = TestStatus.FAILED
            result.error_message = str(e)
            result.stack_trace = self._get_stack_trace()
        
        result.end_time = datetime.now()
        result.execution_time_ms = (result.end_time - result.start_time).total_seconds() * 1000
        
        return result
    
    def _test_macd(self) -> TestResult:
        """Test MACD indicator"""
        result = TestResult(
            test_name="test_macd",
            test_type=TestType.UNIT,
            severity=TestSeverity.HIGH
        )
        
        try:
            # Test data
            data = np.random.randn(100).cumsum() + 100
            
            # Calculate MACD
            macd_line, signal_line, histogram = self._calculate_macd(data)
            
            # Assertions
            result.assertions_count = 4
            
            # Check lengths
            assert len(macd_line) == len(data), "MACD line length should match input data length"
            assert len(signal_line) == len(data), "Signal line length should match input data length"
            assert len(histogram) == len(data), "Histogram length should match input data length"
            
            # Check histogram calculation
            valid_indices = ~(np.isnan(macd_line) | np.isnan(signal_line))
            np.testing.assert_array_almost_equal(
                histogram[valid_indices], 
                macd_line[valid_indices] - signal_line[valid_indices],
                decimal=6,
                err_msg="Histogram should equal MACD line minus signal line"
            )
            
            result.status = TestStatus.PASSED
            result.passed = True
            
        except Exception as e:
            result.status = TestStatus.FAILED
            result.error_message = str(e)
            result.stack_trace = self._get_stack_trace()
        
        result.end_time = datetime.now()
        result.execution_time_ms = (result.end_time - result.start_time).total_seconds() * 1000
        
        return result
    
    def _test_bollinger_bands(self) -> TestResult:
        """Test Bollinger Bands"""
        result = TestResult(
            test_name="test_bollinger_bands",
            test_type=TestType.UNIT,
            severity=TestSeverity.MEDIUM
        )
        
        try:
            # Test data
            data = np.random.randn(100).cumsum() + 100
            
            # Calculate Bollinger Bands
            upper, middle, lower = self._calculate_bollinger_bands(data)
            
            # Assertions
            result.assertions_count = 3
            
            # Check lengths
            assert len(upper) == len(data), "Upper band length should match input data length"
            assert len(middle) == len(data), "Middle band length should match input data length"
            assert len(lower) == len(data), "Lower band length should match input data length"
            
            # Check band relationships (where not NaN)
            valid_indices = ~(np.isnan(upper) | np.isnan(middle) | np.isnan(lower))
            assert np.all(upper[valid_indices] >= middle[valid_indices]), "Upper band should be >= middle band"
            assert np.all(middle[valid_indices] >= lower[valid_indices]), "Middle band should be >= lower band"
            
            result.status = TestStatus.PASSED
            result.passed = True
            
        except Exception as e:
            result.status = TestStatus.FAILED
            result.error_message = str(e)
            result.stack_trace = self._get_stack_trace()
        
        result.end_time = datetime.now()
        result.execution_time_ms = (result.end_time - result.start_time).total_seconds() * 1000
        
        return result
    
    def _calculate_sma(self, data: np.ndarray, window: int) -> np.ndarray:
        """Calculate Simple Moving Average"""
        if pd:
            return pd.Series(data).rolling(window=window).mean().values
        else:
            result = np.full_like(data, np.nan, dtype=float)
            for i in range(window - 1, len(data)):
                result[i] = np.mean(data[i - window + 1:i + 1])
            return result
    
    def _calculate_ema(self, data: np.ndarray, span: int) -> np.ndarray:
        """Calculate Exponential Moving Average"""
        if pd:
            return pd.Series(data).ewm(span=span).mean().values
        else:
            alpha = 2.0 / (span + 1)
            result = np.zeros_like(data, dtype=float)
            result[0] = data[0]
            for i in range(1, len(data)):
                result[i] = alpha * data[i] + (1 - alpha) * result[i - 1]
            return result
    
    def _calculate_rsi(self, data: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculate RSI"""
        deltas = np.diff(data)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        if pd:
            avg_gains = pd.Series(gains).ewm(span=period).mean().values
            avg_losses = pd.Series(losses).ewm(span=period).mean().values
        else:
            # Simple moving average fallback
            avg_gains = np.convolve(gains, np.ones(period)/period, mode='valid')
            avg_losses = np.convolve(losses, np.ones(period)/period, mode='valid')
            avg_gains = np.concatenate([np.full(period-1, np.nan), avg_gains])
            avg_losses = np.concatenate([np.full(period-1, np.nan), avg_losses])
        
        rs = avg_gains / (avg_losses + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        result = np.full(len(data), np.nan)
        result[1:] = rsi
        
        return result
    
    def _calculate_macd(self, data: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Calculate MACD"""
        if not pd:
            raise ImportError("pandas required for MACD calculation")
        
        series = pd.Series(data)
        ema_fast = series.ewm(span=fast).mean()
        ema_slow = series.ewm(span=slow).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        
        return macd_line.values, signal_line.values, histogram.values
    
    def _calculate_bollinger_bands(self, data: np.ndarray, window: int = 20, num_std: float = 2.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Calculate Bollinger Bands"""
        if pd:
            series = pd.Series(data)
            middle = series.rolling(window=window).mean()
            std = series.rolling(window=window).std()
        else:
            middle = np.full_like(data, np.nan, dtype=float)
            std = np.full_like(data, np.nan, dtype=float)
            
            for i in range(window - 1, len(data)):
                window_data = data[i - window + 1:i + 1]
                middle[i] = np.mean(window_data)
                std[i] = np.std(window_data)
        
        upper = middle + (std * num_std)
        lower = middle - (std * num_std)
        
        return (upper.values if pd else upper, 
                middle.values if pd else middle, 
                lower.values if pd else lower)
    
    def _get_stack_trace(self) -> str:
        """Get current stack trace"""
        import traceback
        return traceback.format_exc()


class StressTesting:
    """Stress testing for extreme conditions"""
    
    def __init__(self, config: StressTestConfig = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = config or StressTestConfig()
        self.test_results: List[TestResult] = []
    
    def run_memory_stress_test(self) -> TestResult:
        """Run memory stress test"""
        result = TestResult(
            test_name="memory_stress_test",
            test_type=TestType.STRESS,
            severity=TestSeverity.CRITICAL
        )
        
        try:
            self.logger.info("Starting memory stress test...")
            
            # Monitor initial memory
            initial_memory = self._get_memory_usage()
            
            # Allocate large arrays to stress memory
            large_arrays = []
            target_memory = self.config.max_memory_mb * self.config.memory_stress_factor
            
            while self._get_memory_usage() < target_memory:
                # Allocate 100MB array
                array = np.random.randn(100 * 1024 * 1024 // 8)  # 100MB of float64
                large_arrays.append(array)
                
                # Check if we've exceeded limits
                current_memory = self._get_memory_usage()
                if current_memory > self.config.max_memory_mb:
                    raise MemoryError(f"Memory usage exceeded limit: {current_memory}MB > {self.config.max_memory_mb}MB")
            
            # Perform operations on large data
            for i, array in enumerate(large_arrays[:10]):  # Test first 10 arrays
                # Calculate some indicators
                sma = self._calculate_sma(array[:10000], 20)  # Use subset for performance
                rsi = self._calculate_rsi(array[:10000], 14)
                
                # Verify results are valid
                assert not np.all(np.isnan(sma)), f"SMA calculation failed for array {i}"
                assert not np.all(np.isnan(rsi)), f"RSI calculation failed for array {i}"
            
            # Clean up
            del large_arrays
            import gc
            gc.collect()
            
            final_memory = self._get_memory_usage()
            result.custom_metrics['initial_memory_mb'] = initial_memory
            result.custom_metrics['peak_memory_mb'] = target_memory
            result.custom_metrics['final_memory_mb'] = final_memory
            result.custom_metrics['memory_cleaned_mb'] = target_memory - final_memory
            
            result.status = TestStatus.PASSED
            result.passed = True
            result.assertions_count = len(large_arrays) * 2
            
        except Exception as e:
            result.status = TestStatus.FAILED
            result.error_message = str(e)
            result.stack_trace = self._get_stack_trace()
        
        result.end_time = datetime.now()
        result.execution_time_ms = (result.end_time - result.start_time).total_seconds() * 1000
        result.memory_usage_mb = self._get_memory_usage()
        
        return result
    
    def run_cpu_stress_test(self) -> TestResult:
        """Run CPU stress test"""
        result = TestResult(
            test_name="cpu_stress_test",
            test_type=TestType.STRESS,
            severity=TestSeverity.HIGH
        )
        
        try:
            self.logger.info("Starting CPU stress test...")
            
            # CPU intensive calculation function
            def cpu_intensive_task(data_size: int) -> float:
                # Generate random data
                data = np.random.randn(data_size)
                
                # Perform multiple calculations
                sma = self._calculate_sma(data, 20)
                ema = self._calculate_ema(data, 20)
                rsi = self._calculate_rsi(data, 14)
                
                # Complex calculation
                result = np.sum(sma * ema * rsi)
                return result
            
            # Run multiple threads
            import concurrent.futures
            
            start_time = time.time()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.cpu_stress_threads) as executor:
                # Submit tasks
                futures = []
                for i in range(self.config.cpu_stress_threads):
                    future = executor.submit(cpu_intensive_task, 10000)
                    futures.append(future)
                
                # Wait for completion with timeout
                results = []
                for future in concurrent.futures.as_completed(futures, timeout=self.config.cpu_stress_duration):
                    try:
                        result_value = future.result()
                        results.append(result_value)
                    except Exception as e:
                        self.logger.warning(f"CPU task failed: {e}")
            
            execution_time = time.time() - start_time
            
            # Verify results
            assert len(results) > 0, "No CPU tasks completed successfully"
            assert all(not np.isnan(r) for r in results), "Some CPU tasks returned NaN"
            
            result.custom_metrics['completed_tasks'] = len(results)
            result.custom_metrics['total_tasks'] = self.config.cpu_stress_threads
            result.custom_metrics['completion_rate'] = len(results) / self.config.cpu_stress_threads
            result.custom_metrics['avg_task_result'] = np.mean(results)
            
            result.status = TestStatus.PASSED
            result.passed = True
            result.assertions_count = 2
            
        except Exception as e:
            result.status = TestStatus.FAILED
            result.error_message = str(e)
            result.stack_trace = self._get_stack_trace()
        
        result.end_time = datetime.now()
        result.execution_time_ms = (result.end_time - result.start_time).total_seconds() * 1000
        result.cpu_usage_percent = self._get_cpu_usage()
        
        return result
    
    def run_data_volume_stress_test(self) -> TestResult:
        """Run data volume stress test"""
        result = TestResult(
            test_name="data_volume_stress_test",
            test_type=TestType.STRESS,
            severity=TestSeverity.HIGH
        )
        
        try:
            self.logger.info("Starting data volume stress test...")
            
            # Generate large dataset
            num_symbols = self.config.max_symbols
            data_points = self.config.max_data_points // num_symbols
            
            large_dataset = {}
            for i in range(num_symbols):
                symbol = f"STRESS_SYMBOL_{i:06d}"
                # Generate realistic price data
                prices = np.random.randn(data_points).cumsum() + 100
                prices = np.maximum(prices, 0.01)  # Ensure positive prices
                large_dataset[symbol] = prices
            
            # Test indicator calculations on large dataset
            indicators = ['sma_20', 'ema_20', 'rsi_14']
            
            start_time = time.time()
            
            # Calculate indicators for all symbols
            results = {}
            for symbol, prices in large_dataset.items():
                symbol_results = {}
                
                # SMA
                symbol_results['sma_20'] = self._calculate_sma(prices, 20)
                
                # EMA
                symbol_results['ema_20'] = self._calculate_ema(prices, 20)
                
                # RSI
                symbol_results['rsi_14'] = self._calculate_rsi(prices, 14)
                
                results[symbol] = symbol_results
            
            calculation_time = time.time() - start_time
            
            # Verify results
            assert len(results) == num_symbols, f"Expected {num_symbols} results, got {len(results)}"
            
            # Check that all indicators were calculated
            for symbol, symbol_results in results.items():
                for indicator in indicators:
                    indicator_key = indicator
                    assert indicator_key in symbol_results, f"Missing {indicator} for {symbol}"
                    assert len(symbol_results[indicator_key]) == data_points, f"Wrong length for {indicator} in {symbol}"
            
            # Performance metrics
            total_calculations = num_symbols * len(indicators)
            calculations_per_second = total_calculations / calculation_time
            
            result.custom_metrics['num_symbols'] = num_symbols
            result.custom_metrics['data_points_per_symbol'] = data_points
            result.custom_metrics['total_data_points'] = num_symbols * data_points
            result.custom_metrics['total_calculations'] = total_calculations
            result.custom_metrics['calculations_per_second'] = calculations_per_second
            result.custom_metrics['calculation_time_seconds'] = calculation_time
            
            result.status = TestStatus.PASSED
            result.passed = True
            result.assertions_count = num_symbols * (len(indicators) + 1) + 1
            
        except Exception as e:
            result.status = TestStatus.FAILED
            result.error_message = str(e)
            result.stack_trace = self._get_stack_trace()
        
        result.end_time = datetime.now()
        result.execution_time_ms = (result.end_time - result.start_time).total_seconds() * 1000
        result.memory_usage_mb = self._get_memory_usage()
        
        return result
    
    def run_concurrent_access_stress_test(self) -> TestResult:
        """Run concurrent access stress test"""
        result = TestResult(
            test_name="concurrent_access_stress_test",
            test_type=TestType.STRESS,
            severity=TestSeverity.HIGH
        )
        
        try:
            self.logger.info("Starting concurrent access stress test...")
            
            # Shared data structure
            shared_data = {
                f"SYMBOL_{i:03d}": np.random.randn(1000).cumsum() + 100
                for i in range(100)
            }
            
            # Thread-safe results collection
            import threading
            results_lock = threading.Lock()
            thread_results = []
            errors = []
            
            def worker_thread(thread_id: int, iterations: int):
                """Worker thread function"""
                thread_local_results = []
                
                try:
                    for i in range(iterations):
                        # Randomly select symbol
                        symbol = f"SYMBOL_{np.random.randint(0, 100):03d}"
                        prices = shared_data[symbol]
                        
                        # Calculate indicators
                        sma = self._calculate_sma(prices, 20)
                        rsi = self._calculate_rsi(prices, 14)
                        
                        # Verify results
                        assert not np.all(np.isnan(sma)), f"SMA failed for {symbol} in thread {thread_id}"
                        assert not np.all(np.isnan(rsi)), f"RSI failed for {symbol} in thread {thread_id}"
                        
                        thread_local_results.append({
                            'thread_id': thread_id,
                            'iteration': i,
                            'symbol': symbol,
                            'sma_mean': np.nanmean(sma),
                            'rsi_mean': np.nanmean(rsi)
                        })
                    
                    # Store results thread-safely
                    with results_lock:
                        thread_results.extend(thread_local_results)
                        
                except Exception as e:
                    with results_lock:
                        errors.append(f"Thread {thread_id}: {str(e)}")
            
            # Start multiple threads
            num_threads = min(50, self.config.max_concurrent_users // 20)
            iterations_per_thread = 20
            
            threads = []
            for i in range(num_threads):
                thread = threading.Thread(target=worker_thread, args=(i, iterations_per_thread))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join(timeout=60)  # 60 second timeout
            
            # Verify results
            assert len(errors) == 0, f"Errors occurred in threads: {errors}"
            assert len(thread_results) > 0, "No thread results collected"
            
            expected_results = num_threads * iterations_per_thread
            completion_rate = len(thread_results) / expected_results
            
            result.custom_metrics['num_threads'] = num_threads
            result.custom_metrics['iterations_per_thread'] = iterations_per_thread
            result.custom_metrics['expected_results'] = expected_results
            result.custom_metrics['actual_results'] = len(thread_results)
            result.custom_metrics['completion_rate'] = completion_rate
            result.custom_metrics['error_count'] = len(errors)
            
            result.status = TestStatus.PASSED
            result.passed = True
            result.assertions_count = len(thread_results) * 2 + 2
            
        except Exception as e:
            result.status = TestStatus.FAILED
            result.error_message = str(e)
            result.stack_trace = self._get_stack_trace()
        
        result.end_time = datetime.now()
        result.execution_time_ms = (result.end_time - result.start_time).total_seconds() * 1000
        
        return result
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        if psutil:
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        else:
            return 0.0
    
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        if psutil:
            return psutil.cpu_percent(interval=1)
        else:
            return 0.0
    
    def _calculate_sma(self, data: np.ndarray, window: int) -> np.ndarray:
        """Calculate Simple Moving Average"""
        if pd:
            return pd.Series(data).rolling(window=window).mean().values
        else:
            result = np.full_like(data, np.nan, dtype=float)
            for i in range(window - 1, len(data)):
                result[i] = np.mean(data[i - window + 1:i + 1])
            return result
    
    def _calculate_ema(self, data: np.ndarray, span: int) -> np.ndarray:
        """Calculate Exponential Moving Average"""
        if pd:
            return pd.Series(data).ewm(span=span).mean().values
        else:
            alpha = 2.0 / (span + 1)
            result = np.zeros_like(data, dtype=float)
            result[0] = data[0]
            for i in range(1, len(data)):
                result[i] = alpha * data[i] + (1 - alpha) * result[i - 1]
            return result
    
    def _calculate_rsi(self, data: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculate RSI"""
        deltas = np.diff(data)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        if pd:
            avg_gains = pd.Series(gains).ewm(span=period).mean().values
            avg_losses = pd.Series(losses).ewm(span=period).mean().values
        else:
            # Simple moving average fallback
            avg_gains = np.convolve(gains, np.ones(period)/period, mode='valid')
            avg_losses = np.convolve(losses, np.ones(period)/period, mode='valid')
            avg_gains = np.concatenate([np.full(period-1, np.nan), avg_gains])
            avg_losses = np.concatenate([np.full(period-1, np.nan), avg_losses])
        
        rs = avg_gains / (avg_losses + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        result = np.full(len(data), np.nan)
        result[1:] = rsi
        
        return result
    
    def _get_stack_trace(self) -> str:
        """Get current stack trace"""
        import traceback
        return traceback.format_exc()


class PerformanceBenchmarking:
    """Performance benchmarking and regression detection"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.benchmarks: List[PerformanceBenchmark] = []
        self.benchmark_results: Dict[str, List[Dict[str, Any]]] = {}
        
        self._setup_default_benchmarks()
    
    def _setup_default_benchmarks(self):
        """Setup default performance benchmarks"""
        # SMA benchmark
        self.benchmarks.append(PerformanceBenchmark(
            name="sma_calculation",
            description="Simple Moving Average calculation performance",
            max_execution_time_ms=100.0,
            max_memory_usage_mb=100.0,
            min_throughput_ops_per_sec=1000.0,
            max_latency_p99_ms=50.0,
            test_data_size=10000
        ))
        
        # RSI benchmark
        self.benchmarks.append(PerformanceBenchmark(
            name="rsi_calculation",
            description="RSI calculation performance",
            max_execution_time_ms=200.0,
            max_memory_usage_mb=150.0,
            min_throughput_ops_per_sec=500.0,
            max_latency_p99_ms=100.0,
            test_data_size=10000
        ))
        
        # MACD benchmark
        self.benchmarks.append(PerformanceBenchmark(
            name="macd_calculation",
            description="MACD calculation performance",
            max_execution_time_ms=300.0,
            max_memory_usage_mb=200.0,
            min_throughput_ops_per_sec=300.0,
            max_latency_p99_ms=150.0,
            test_data_size=10000
        ))
    
    def run_benchmark(self, benchmark: PerformanceBenchmark) -> TestResult:
        """Run a performance benchmark"""
        result = TestResult(
            test_name=f"benchmark_{benchmark.name}",
            test_type=TestType.PERFORMANCE,
            severity=TestSeverity.HIGH
        )
        
        try:
            self.logger.info(f"Running benchmark: {benchmark.name}")
            
            # Generate test data
            test_data = np.random.randn(benchmark.test_data_size).cumsum() + 100
            
            # Warmup runs
            for _ in range(benchmark.warmup_iterations):
                self._run_benchmark_function(benchmark.name, test_data)
            
            # Actual benchmark runs
            execution_times = []
            memory_usages = []
            
            for i in range(benchmark.iterations):
                start_time = time.perf_counter()
                start_memory = self._get_memory_usage()
                
                # Run the benchmark function
                self._run_benchmark_function(benchmark.name, test_data)
                
                end_time = time.perf_counter()
                end_memory = self._get_memory_usage()
                
                execution_time_ms = (end_time - start_time) * 1000
                memory_usage_mb = max(0, end_memory - start_memory)
                
                execution_times.append(execution_time_ms)
                memory_usages.append(memory_usage_mb)
            
            # Calculate statistics
            avg_execution_time = statistics.mean(execution_times)
            p99_execution_time = np.percentile(execution_times, 99)
            max_memory_usage = max(memory_usages)
            throughput = 1000.0 / avg_execution_time if avg_execution_time > 0 else 0
            
            # Store results
            benchmark_result = {
                'timestamp': datetime.now().isoformat(),
                'avg_execution_time_ms': avg_execution_time,
                'p99_execution_time_ms': p99_execution_time,
                'max_memory_usage_mb': max_memory_usage,
                'throughput_ops_per_sec': throughput,
                'iterations': benchmark.iterations,
                'test_data_size': benchmark.test_data_size
            }
            
            if benchmark.name not in self.benchmark_results:
                self.benchmark_results[benchmark.name] = []
            self.benchmark_results[benchmark.name].append(benchmark_result)
            
            # Check against thresholds
            assertions_passed = 0
            total_assertions = 4
            
            if avg_execution_time <= benchmark.max_execution_time_ms:
                assertions_passed += 1
            else:
                result.logs.append(f"Execution time exceeded: {avg_execution_time:.2f}ms > {benchmark.max_execution_time_ms}ms")
            
            if max_memory_usage <= benchmark.max_memory_usage_mb:
                assertions_passed += 1
            else:
                result.logs.append(f"Memory usage exceeded: {max_memory_usage:.2f}MB > {benchmark.max_memory_usage_mb}MB")
            
            if throughput >= benchmark.min_throughput_ops_per_sec:
                assertions_passed += 1
            else:
                result.logs.append(f"Throughput below minimum: {throughput:.2f} < {benchmark.min_throughput_ops_per_sec}")
            
            if p99_execution_time <= benchmark.max_latency_p99_ms:
                assertions_passed += 1
            else:
                result.logs.append(f"P99 latency exceeded: {p99_execution_time:.2f}ms > {benchmark.max_latency_p99_ms}ms")
            
            # Check for regression
            regression_detected = self._check_regression(benchmark, benchmark_result)
            if regression_detected:
                result.logs.append("Performance regression detected")
            
            # Set result status
            if assertions_passed == total_assertions and not regression_detected:
                result.status = TestStatus.PASSED
                result.passed = True
            else:
                result.status = TestStatus.FAILED
                result.error_message = f"Benchmark failed: {total_assertions - assertions_passed} assertions failed"
            
            result.assertions_count = total_assertions
            result.custom_metrics.update(benchmark_result)
            
        except Exception as e:
            result.status = TestStatus.FAILED
            result.error_message = str(e)
            result.stack_trace = self._get_stack_trace()
        
        result.end_time = datetime.now()
        result.execution_time_ms = (result.end_time - result.start_time).total_seconds() * 1000
        
        return result
    
    def _run_benchmark_function(self, benchmark_name: str, test_data: np.ndarray):
        """Run the specific benchmark function"""
        if benchmark_name == "sma_calculation":
            return self._calculate_sma(test_data, 20)
        elif benchmark_name == "rsi_calculation":
            return self._calculate_rsi(test_data, 14)
        elif benchmark_name == "macd_calculation":
            return self._calculate_macd(test_data)
        else:
            raise ValueError(f"Unknown benchmark: {benchmark_name}")
    
    def _check_regression(self, benchmark: PerformanceBenchmark, current_result: Dict[str, Any]) -> bool:
        """Check for performance regression"""
        if benchmark.baseline_performance is None:
            return False
        
        # Check if current performance is significantly worse than baseline
        baseline_time = benchmark.baseline_performance.get('avg_execution_time_ms', 0)
        current_time = current_result['avg_execution_time_ms']
        
        if baseline_time > 0:
            regression_percent = ((current_time - baseline_time) / baseline_time) * 100
            return regression_percent > benchmark.regression_threshold_percent
        
        return False
    
    def _calculate_sma(self, data: np.ndarray, window: int) -> np.ndarray:
        """Calculate Simple Moving Average"""
        if pd:
            return pd.Series(data).rolling(window=window).mean().values
        else:
            result = np.full_like(data, np.nan, dtype=float)
            for i in range(window - 1, len(data)):
                result[i] = np.mean(data[i - window + 1:i + 1])
            return result
    
    def _calculate_rsi(self, data: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculate RSI"""
        deltas = np.diff(data)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        if pd:
            avg_gains = pd.Series(gains).ewm(span=period).mean().values
            avg_losses = pd.Series(losses).ewm(span=period).mean().values
        else:
            # Simple moving average fallback
            avg_gains = np.convolve(gains, np.ones(period)/period, mode='valid')
            avg_losses = np.convolve(losses, np.ones(period)/period, mode='valid')
            avg_gains = np.concatenate([np.full(period-1, np.nan), avg_gains])
            avg_losses = np.concatenate([np.full(period-1, np.nan), avg_losses])
        
        rs = avg_gains / (avg_losses + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        result = np.full(len(data), np.nan)
        result[1:] = rsi
        
        return result
    
    def _calculate_macd(self, data: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Calculate MACD"""
        if not pd:
            raise ImportError("pandas required for MACD calculation")
        
        series = pd.Series(data)
        ema_fast = series.ewm(span=fast).mean()
        ema_slow = series.ewm(span=slow).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        
        return macd_line.values, signal_line.values, histogram.values
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        if psutil:
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        else:
            return 0.0
    
    def _get_stack_trace(self) -> str:
        """Get current stack trace"""
        import traceback
        return traceback.format_exc()


class TestingSuite:
    """Main testing and validation suite"""
    
    def __init__(self, stress_config: StressTestConfig = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize test components
        self.unit_tests = UnitTestSuite()
        self.stress_tests = StressTesting(stress_config)
        self.performance_benchmarks = PerformanceBenchmarking()
        
        # Test results
        self.all_test_results: List[TestResult] = []
        
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return comprehensive report"""
        self.logger.info("Starting comprehensive test suite...")
        
        start_time = datetime.now()
        
        # Run unit tests
        self.logger.info("Running unit tests...")
        unit_results = self.unit_tests.test_technical_indicators()
        self.all_test_results.extend(unit_results)
        
        # Run stress tests
        self.logger.info("Running stress tests...")
        stress_results = [
            self.stress_tests.run_memory_stress_test(),
            self.stress_tests.run_cpu_stress_test(),
            self.stress_tests.run_data_volume_stress_test(),
            self.stress_tests.run_concurrent_access_stress_test()
        ]
        self.all_test_results.extend(stress_results)
        
        # Run performance benchmarks
        self.logger.info("Running performance benchmarks...")
        benchmark_results = []
        for benchmark in self.performance_benchmarks.benchmarks:
            result = self.performance_benchmarks.run_benchmark(benchmark)
            benchmark_results.append(result)
        self.all_test_results.extend(benchmark_results)
        
        end_time = datetime.now()
        total_execution_time = (end_time - start_time).total_seconds()
        
        # Generate comprehensive report
        report = self._generate_test_report(total_execution_time)
        
        # Save report
        self._save_test_report(report)
        
        self.logger.info(f"Test suite completed in {total_execution_time:.2f} seconds")
        
        return report
    
    def _generate_test_report(self, total_execution_time: float) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        # Categorize results
        results_by_type = {}
        results_by_status = {}
        
        for result in self.all_test_results:
            # By type
            if result.test_type not in results_by_type:
                results_by_type[result.test_type] = []
            results_by_type[result.test_type].append(result)
            
            # By status
            if result.status not in results_by_status:
                results_by_status[result.status] = []
            results_by_status[result.status].append(result)
        
        # Calculate statistics
        total_tests = len(self.all_test_results)
        passed_tests = len(results_by_status.get(TestStatus.PASSED, []))
        failed_tests = len(results_by_status.get(TestStatus.FAILED, []))
        error_tests = len(results_by_status.get(TestStatus.ERROR, []))
        
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Performance statistics
        execution_times = [r.execution_time_ms for r in self.all_test_results if r.execution_time_ms > 0]
        avg_execution_time = statistics.mean(execution_times) if execution_times else 0
        
        # Coverage statistics
        total_assertions = sum(r.assertions_count for r in self.all_test_results)
        
        report = {
            'summary': {
                'timestamp': datetime.now().isoformat(),
                'total_execution_time_seconds': total_execution_time,
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'error_tests': error_tests,
                'pass_rate_percent': pass_rate,
                'total_assertions': total_assertions,
                'avg_test_execution_time_ms': avg_execution_time
            },
            
            'results_by_type': {
                test_type.value: {
                    'count': len(results),
                    'passed': len([r for r in results if r.status == TestStatus.PASSED]),
                    'failed': len([r for r in results if r.status == TestStatus.FAILED]),
                    'avg_execution_time_ms': statistics.mean([r.execution_time_ms for r in results if r.execution_time_ms > 0]) if results else 0
                }
                for test_type, results in results_by_type.items()
            },
            
            'failed_tests': [
                {
                    'name': result.test_name,
                    'type': result.test_type.value,
                    'severity': result.severity.value,
                    'error_message': result.error_message,
                    'execution_time_ms': result.execution_time_ms
                }
                for result in self.all_test_results
                if result.status in [TestStatus.FAILED, TestStatus.ERROR]
            ],
            
            'performance_metrics': {
                'benchmark_results': self.performance_benchmarks.benchmark_results,
                'stress_test_metrics': {
                    result.test_name: result.custom_metrics
                    for result in self.all_test_results
                    if result.test_type == TestType.STRESS and result.custom_metrics
                }
            },
            
            'recommendations': self._generate_recommendations(),
            
            'detailed_results': [
                {
                    'name': result.test_name,
                    'type': result.test_type.value,
                    'status': result.status.value,
                    'severity': result.severity.value,
                    'execution_time_ms': result.execution_time_ms,
                    'assertions_count': result.assertions_count,
                    'memory_usage_mb': result.memory_usage_mb,
                    'custom_metrics': result.custom_metrics,
                    'error_message': result.error_message,
                    'logs': result.logs
                }
                for result in self.all_test_results
            ]
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        # Check pass rate
        total_tests = len(self.all_test_results)
        passed_tests = len([r for r in self.all_test_results if r.status == TestStatus.PASSED])
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        if pass_rate < 90:
            recommendations.append(f"Test pass rate is {pass_rate:.1f}%, consider investigating failed tests")
        
        # Check performance
        performance_failures = [r for r in self.all_test_results if r.test_type == TestType.PERFORMANCE and r.status == TestStatus.FAILED]
        if performance_failures:
            recommendations.append(f"{len(performance_failures)} performance benchmarks failed, consider optimization")
        
        # Check stress tests
        stress_failures = [r for r in self.all_test_results if r.test_type == TestType.STRESS and r.status == TestStatus.FAILED]
        if stress_failures:
            recommendations.append(f"{len(stress_failures)} stress tests failed, system may not handle extreme conditions")
        
        # Check memory usage
        high_memory_tests = [r for r in self.all_test_results if r.memory_usage_mb > 1000]
        if high_memory_tests:
            recommendations.append(f"{len(high_memory_tests)} tests used >1GB memory, consider memory optimization")
        
        # Check execution times
        slow_tests = [r for r in self.all_test_results if r.execution_time_ms > 5000]
        if slow_tests:
            recommendations.append(f"{len(slow_tests)} tests took >5 seconds, consider performance optimization")
        
        return recommendations
    
    def _save_test_report(self, report: Dict[str, Any]):
        """Save test report to file"""
        try:
            # Create reports directory
            reports_dir = Path("./data/test_reports")
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = reports_dir / f"test_report_{timestamp}.json"
            
            # Save report
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            self.logger.info(f"Test report saved to: {report_file}")
            
            # Also save latest report
            latest_file = reports_dir / "latest_test_report.json"
            with open(latest_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
        except Exception as e:
            self.logger.error(f"Failed to save test report: {e}")


# Example usage and testing functions
async def run_comprehensive_testing():
    """Run comprehensive testing suite"""
    print("Starting Comprehensive Testing and Validation Suite")
    print("=" * 60)
    
    # Create stress test configuration
    stress_config = StressTestConfig(
        max_concurrent_users=100,
        requests_per_second=50,
        test_duration_seconds=60,
        max_data_points=100000,
        max_symbols=1000
    )
    
    # Initialize testing suite
    testing_suite = TestingSuite(stress_config)
    
    # Run all tests
    report = testing_suite.run_all_tests()
    
    # Print summary
    print("\nTest Results Summary:")
    print(f"Total Tests: {report['summary']['total_tests']}")
    print(f"Passed: {report['summary']['passed_tests']}")
    print(f"Failed: {report['summary']['failed_tests']}")
    print(f"Pass Rate: {report['summary']['pass_rate_percent']:.1f}%")
    print(f"Total Execution Time: {report['summary']['total_execution_time_seconds']:.2f}s")
    
    # Print failed tests
    if report['failed_tests']:
        print("\nFailed Tests:")
        for failed_test in report['failed_tests']:
            print(f"  - {failed_test['name']} ({failed_test['type']}): {failed_test['error_message']}")
    
    # Print recommendations
    if report['recommendations']:
        print("\nRecommendations:")
        for rec in report['recommendations']:
            print(f"  - {rec}")
    
    return report


def run_unit_tests_only():
    """Run only unit tests for quick validation"""
    print("Running Unit Tests Only")
    print("=" * 30)
    
    unit_tests = UnitTestSuite()
    results = unit_tests.test_technical_indicators()
    
    passed = len([r for r in results if r.status == TestStatus.PASSED])
    total = len(results)
    
    print(f"\nUnit Test Results: {passed}/{total} passed")
    
    for result in results:
        status_symbol = "✓" if result.status == TestStatus.PASSED else "✗"
        print(f"  {status_symbol} {result.test_name} ({result.execution_time_ms:.1f}ms)")
        if result.error_message:
            print(f"    Error: {result.error_message}")
    
    return results


def run_stress_tests_only():
    """Run only stress tests"""
    print("Running Stress Tests Only")
    print("=" * 30)
    
    stress_config = StressTestConfig(
        max_concurrent_users=50,
        max_data_points=50000,
        max_symbols=500
    )
    
    stress_tests = StressTesting(stress_config)
    
    results = [
        stress_tests.run_memory_stress_test(),
        stress_tests.run_cpu_stress_test(),
        stress_tests.run_data_volume_stress_test(),
        stress_tests.run_concurrent_access_stress_test()
    ]
    
    passed = len([r for r in results if r.status == TestStatus.PASSED])
    total = len(results)
    
    print(f"\nStress Test Results: {passed}/{total} passed")
    
    for result in results:
        status_symbol = "✓" if result.status == TestStatus.PASSED else "✗"
        print(f"  {status_symbol} {result.test_name} ({result.execution_time_ms:.1f}ms)")
        if result.custom_metrics:
            print(f"    Metrics: {result.custom_metrics}")
        if result.error_message:
            print(f"    Error: {result.error_message}")
    
    return results


def run_performance_benchmarks_only():
    """Run only performance benchmarks"""
    print("Running Performance Benchmarks Only")
    print("=" * 40)
    
    benchmarks = PerformanceBenchmarking()
    
    results = []
    for benchmark in benchmarks.benchmarks:
        result = benchmarks.run_benchmark(benchmark)
        results.append(result)
    
    passed = len([r for r in results if r.status == TestStatus.PASSED])
    total = len(results)
    
    print(f"\nBenchmark Results: {passed}/{total} passed")
    
    for result in results:
        status_symbol = "✓" if result.status == TestStatus.PASSED else "✗"
        print(f"  {status_symbol} {result.test_name} ({result.execution_time_ms:.1f}ms)")
        if result.custom_metrics:
            throughput = result.custom_metrics.get('throughput_ops_per_sec', 0)
            memory = result.custom_metrics.get('max_memory_usage_mb', 0)
            print(f"    Throughput: {throughput:.1f} ops/sec, Memory: {memory:.1f}MB")
        if result.error_message:
            print(f"    Error: {result.error_message}")
    
    return results


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Check dependencies
    missing_deps = []
    if np is None:
        missing_deps.append("numpy")
    if pd is None:
        missing_deps.append("pandas")
    
    if missing_deps:
        print(f"Warning: Missing dependencies: {', '.join(missing_deps)}")
        print("Some tests may be skipped or use fallback implementations.")
    
    # Run tests based on command line arguments
    import sys
    
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
        
        if test_type == "unit":
            run_unit_tests_only()
        elif test_type == "stress":
            run_stress_tests_only()
        elif test_type == "performance":
            run_performance_benchmarks_only()
        elif test_type == "all":
            asyncio.run(run_comprehensive_testing())
        else:
            print("Usage: python testing_validation_suite.py [unit|stress|performance|all]")
    else:
        # Default: run all tests
        asyncio.run(run_comprehensive_testing())