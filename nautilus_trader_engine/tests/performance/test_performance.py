"""
Performance tests for Nautilus Trader Engine components.
Tests throughput, latency, memory usage, and scalability.
"""

import unittest
import asyncio
import time
import psutil
import gc
import cProfile
import io
import pstats
from unittest.mock import Mock, patch
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from nautilus_trader_engine.tests.testing_framework import TestCase, performance_test, PerformanceTestRunner
from nautilus_trader_engine.core.base.dependency_injection import DependencyContainer
from nautilus_trader_engine.core.base.event_system import EventSystem, Event
from nautilus_trader_engine.core.caching.cache_layer import MultiLevelCache, CacheLevel
from nautilus_trader_engine.core.streaming.streaming_architecture import (
    StreamManager, StreamPipeline, StreamMessage, StreamType,
    MarketDataProcessor, TechnicalIndicatorProcessor
)
from nautilus_trader_engine.engines.parallel_processing_engine import ParallelProcessor
from nautilus_trader_engine.analysis.indicators.adaptive_parameters import AdaptiveParameterManager
from nautilus_trader_engine.analysis.indicators.ensemble_methods import IndicatorEnsemble


class TestCorePerformance(TestCase):
    """Performance tests for core system components."""

    def setUp(self):
        super().setUp()
        self.perf_runner = PerformanceTestRunner()

    @performance_test()
    def test_dependency_injection_performance(self):
        """Test dependency injection container performance."""
        container = DependencyContainer()

        # Register multiple services
        for i in range(100):
            @container.injectable()
            class TestService:
                def __init__(self):
                    self.value = i

            container.register(TestService, name=f"TestService{i}")

        # Test resolution performance
        def resolve_services():
            for i in range(100):
                service = container.resolve(f"TestService{i}")
                assert service.value == i

        metrics = self.perf_runner.run_performance_test(
            resolve_services,
            "dependency_injection_resolution",
            iterations=1000
        )

        # Assert performance requirements
        self.assertLess(metrics.execution_time, 0.1, "DI resolution should be fast")
        self.assertGreater(metrics.throughput, 1000, "Should handle high throughput")

    @performance_test()
    def test_event_system_performance(self):
        """Test event system performance under load."""
        event_system = EventSystem()

        # Register multiple event handlers
        events_received = []
        def event_handler(event: Event):
            events_received.append(event)

        for i in range(10):
            event_system.subscribe("test_event", event_handler)

        # Test event publishing performance
        def publish_events():
            for i in range(100):
                event = Event("test_event", {"data": i})
                event_system.publish(event)

        metrics = self.perf_runner.run_performance_test(
            publish_events,
            "event_system_publishing",
            iterations=100
        )

        # Verify all events were processed
        self.assertEqual(len(events_received), 10000)  # 100 iterations * 100 events * 10 handlers

        # Assert performance requirements
        self.assertLess(metrics.execution_time, 1.0, "Event publishing should be fast")
        self.assertGreater(metrics.throughput, 1000, "Should handle high event throughput")

    @performance_test()
    def test_caching_performance(self):
        """Test caching system performance."""
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = MultiLevelCache(
                levels=[CacheLevel.L1_MEMORY, CacheLevel.L3_DISK],
                memory_size=1000,
                disk_config={"cache_dir": temp_dir, "max_size_mb": 10}
            )

            # Test data
            test_data = {"key": "value", "numbers": list(range(100))}

            # Test cache set performance
            def cache_set_operations():
                for i in range(100):
                    cache.set(f"key_{i}", test_data)

            set_metrics = self.perf_runner.run_performance_test(
                cache_set_operations,
                "cache_set_operations",
                iterations=10
            )

            # Test cache get performance
            def cache_get_operations():
                for i in range(100):
                    result = cache.get(f"key_{i % 100}")  # Cycle through keys
                    assert result is not None

            get_metrics = self.perf_runner.run_performance_test(
                cache_get_operations,
                "cache_get_operations",
                iterations=10
            )

            # Assert performance requirements
            self.assertLess(set_metrics.execution_time, 0.5, "Cache set should be fast")
            self.assertLess(get_metrics.execution_time, 0.3, "Cache get should be fast")
            self.assertGreater(get_metrics.throughput, 1000, "Should handle high cache throughput")


class TestStreamingPerformance(TestCase):
    """Performance tests for streaming components."""

    def setUp(self):
        super().setUp()
        self.perf_runner = PerformanceTestRunner()
        self.stream_manager = StreamManager()

    @performance_test()
    def test_stream_processing_performance(self):
        """Test stream processing pipeline performance."""
        async def run_stream_performance_test():
            # Create pipeline
            pipeline = self.stream_manager.create_pipeline("perf_pipeline")

            # Add processors
            market_processor = MarketDataProcessor("PERF")
            indicator_processor = TechnicalIndicatorProcessor(['SMA'])

            pipeline.add_processor(market_processor)
            pipeline.add_processor(indicator_processor)

            # Create output queue
            output_queue = asyncio.Queue()
            pipeline.add_output_queue("output", output_queue)

            # Start pipeline
            await pipeline.start()

            # Generate test messages
            messages = []
            for i in range(1000):
                message = StreamMessage(
                    stream_type=StreamType.MARKET_DATA,
                    symbol="PERF",
                    timestamp=datetime.now(),
                    data={
                        'open': 100.0 + i * 0.01,
                        'high': 101.0 + i * 0.01,
                        'low': 99.0 + i * 0.01,
                        'close': 100.5 + i * 0.01,
                        'volume': 100000 + i * 100
                    },
                    sequence_number=i
                )
                messages.append(message)

            # Test message ingestion performance
            start_time = time.time()
            for msg in messages:
                await pipeline.ingest_message(msg)

            # Wait for processing
            await asyncio.sleep(2)

            processing_time = time.time() - start_time

            # Count processed messages
            processed_count = 0
            try:
                while True:
                    result = output_queue.get_nowait()
                    processed_count += 1
                    output_queue.task_done()
            except asyncio.QueueEmpty:
                pass

            # Stop pipeline
            await pipeline.stop()

            return {
                'processing_time': processing_time,
                'messages_processed': processed_count,
                'throughput': len(messages) / processing_time if processing_time > 0 else 0
            }

        # Run async test
        result = asyncio.run(run_stream_performance_test())

        # Assert performance requirements
        self.assertGreater(result['throughput'], 100, "Should process at least 100 messages/second")
        self.assertGreater(result['messages_processed'], 500, "Should process most messages")

    @performance_test()
    def test_parallel_indicator_calculation(self):
        """Test parallel indicator calculation performance."""
        async def run_parallel_indicator_test():
            processor = ParallelProcessor()

            # Create large dataset
            dates = pd.date_range('2023-01-01', periods=5000, freq='5min')
            data = pd.DataFrame({
                'open': np.random.uniform(100, 110, 5000),
                'high': np.random.uniform(105, 115, 5000),
                'low': np.random.uniform(95, 105, 5000),
                'close': np.random.uniform(100, 110, 5000),
                'volume': np.random.uniform(1000000, 5000000, 5000)
            }, index=dates)

            # Define multiple indicators
            indicators = [
                {'name': 'SMA', 'parameters': {'period': 20}},
                {'name': 'EMA', 'parameters': {'period': 20}},
                {'name': 'RSI', 'parameters': {'period': 14}},
                {'name': 'MACD', 'parameters': {'fast': 12, 'slow': 26, 'signal': 9}},
                {'name': 'BollingerBands', 'parameters': {'period': 20, 'std_dev': 2}}
            ]

            # Measure parallel calculation performance
            start_time = time.time()
            results = await processor.calculate_indicators_parallel(data, indicators)
            parallel_time = time.time() - start_time

            # Measure sequential calculation performance for comparison
            start_time = time.time()
            sequential_results = {}
            for indicator in indicators:
                # Simplified sequential calculation (would normally use actual indicator functions)
                sequential_results[f"{indicator['name']}_{list(indicator['parameters'].values())[0]}"] = np.random.random(len(data))
            sequential_time = time.time() - start_time

            return {
                'parallel_time': parallel_time,
                'sequential_time': sequential_time,
                'speedup': sequential_time / parallel_time if parallel_time > 0 else 1,
                'indicators_calculated': len(results)
            }

        # Run async test
        result = asyncio.run(run_parallel_indicator_test())

        # Assert performance requirements
        self.assertGreater(result['speedup'], 1.2, "Parallel processing should provide speedup")
        self.assertEqual(result['indicators_calculated'], 5, "All indicators should be calculated")


class TestMemoryPerformance(TestCase):
    """Performance tests focused on memory usage."""

    def setUp(self):
        super().setUp()
        self.perf_runner = PerformanceTestRunner()

    @performance_test()
    def test_memory_usage_caching(self):
        """Test memory usage of caching system."""
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = MultiLevelCache(
                levels=[CacheLevel.L1_MEMORY],
                memory_size=10000  # Large cache for testing
            )

            # Test memory usage with large dataset
            def cache_large_dataset():
                for i in range(1000):
                    large_data = {
                        'prices': np.random.random(1000).tolist(),
                        'volumes': np.random.random(1000).tolist(),
                        'metadata': 'x' * 1000  # 1KB string
                    }
                    cache.set(f"large_key_{i}", large_data)

                # Access all data
                for i in range(1000):
                    result = cache.get(f"large_key_{i}")
                    assert result is not None

            metrics = self.perf_runner.run_performance_test(
                cache_large_dataset,
                "large_dataset_caching",
                iterations=1
            )

            # Assert memory usage is reasonable
            self.assertLess(metrics.memory_usage, 500, "Memory usage should be reasonable (< 500MB)")

    @performance_test()
    def test_memory_leak_detection(self):
        """Test for memory leaks in long-running operations."""
        def long_running_operation():
            # Create objects that should be garbage collected
            data_list = []
            for i in range(10000):
                data_list.append({'data': 'x' * 100, 'numbers': list(range(100))})

            # Process data
            processed = [len(item['data']) + sum(item['numbers']) for item in data_list]

            # Clear references
            del data_list

            # Force garbage collection
            gc.collect()

            return sum(processed)

        # Run multiple iterations to check for memory leaks
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024

        for i in range(10):
            result = long_running_operation()
            assert result > 0

            # Check memory usage doesn't grow significantly
            current_memory = psutil.Process().memory_info().rss / 1024 / 1024
            memory_growth = current_memory - initial_memory

            # Allow some memory growth but not excessive
            self.assertLess(memory_growth, 50, f"Memory leak detected: {memory_growth}MB growth after iteration {i}")


class TestScalabilityPerformance(TestCase):
    """Performance tests for system scalability."""

    def setUp(self):
        super().setUp()
        self.perf_runner = PerformanceTestRunner()

    @performance_test()
    def test_concurrent_operations(self):
        """Test performance under concurrent operations."""
        results = []
        errors = []

        def concurrent_task(task_id):
            try:
                # Simulate some work
                time.sleep(0.01)
                result = task_id * 2
                results.append(result)
                return result
            except Exception as e:
                errors.append(e)
                return None

        # Test with different levels of concurrency
        concurrency_levels = [1, 5, 10, 20]

        for num_threads in concurrency_levels:
            start_time = time.time()

            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = [executor.submit(concurrent_task, i) for i in range(100)]
                for future in as_completed(futures):
                    future.result()

            execution_time = time.time() - start_time

            # Assert reasonable performance
            self.assertLess(execution_time, 5.0, f"Concurrent execution with {num_threads} threads should be fast")
            self.assertEqual(len(results), 100, "All tasks should complete successfully")
            self.assertEqual(len(errors), 0, "No errors should occur")

    @performance_test()
    def test_large_dataset_processing(self):
        """Test performance with large datasets."""
        # Create large dataset
        num_rows = 100000
        data = pd.DataFrame({
            'timestamp': pd.date_range('2023-01-01', periods=num_rows, freq='1min'),
            'price': np.random.uniform(100, 200, num_rows),
            'volume': np.random.uniform(1000, 10000, num_rows)
        })

        def process_large_dataset():
            # Calculate multiple indicators
            data_copy = data.copy()

            # Simple moving averages
            data_copy['SMA_20'] = data_copy['price'].rolling(20).mean()
            data_copy['SMA_50'] = data_copy['price'].rolling(50).mean()

            # Exponential moving averages
            data_copy['EMA_20'] = data_copy['price'].ewm(span=20).mean()
            data_copy['EMA_50'] = data_copy['price'].ewm(span=50).mean()

            # RSI calculation
            delta = data_copy['price'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            data_copy['RSI'] = 100 - (100 / (1 + rs))

            return data_copy

        metrics = self.perf_runner.run_performance_test(
            process_large_dataset,
            "large_dataset_processing",
            iterations=1
        )

        # Assert reasonable processing time for large dataset
        self.assertLess(metrics.execution_time, 30.0, "Large dataset processing should be reasonable")
        self.assertLess(metrics.memory_usage, 1000, "Memory usage should be reasonable")

    @performance_test()
    def test_indicator_ensemble_performance(self):
        """Test performance of indicator ensemble calculations."""
        ensemble = IndicatorEnsemble()

        # Add multiple indicators
        indicators = [
            ("SMA", {"period": 20}),
            ("EMA", {"period": 20}),
            ("RSI", {"period": 14}),
            ("MACD", {"fast": 12, "slow": 26, "signal": 9}),
            ("Stochastic", {"k_period": 14, "d_period": 3}),
            ("WilliamsR", {"period": 14}),
            ("CCI", {"period": 20}),
            ("MFI", {"period": 14})
        ]

        for name, params in indicators:
            ensemble.add_indicator(name, params)

        # Create test data
        dates = pd.date_range('2023-01-01', periods=5000, freq='5min')
        market_data = pd.DataFrame({
            'open': np.random.uniform(100, 110, 5000),
            'high': np.random.uniform(105, 115, 5000),
            'low': np.random.uniform(95, 105, 5000),
            'close': np.random.uniform(100, 110, 5000),
            'volume': np.random.uniform(1000000, 5000000, 5000)
        }, index=dates)

        def calculate_ensemble():
            results = ensemble.calculate_all(market_data)
            return results

        metrics = self.perf_runner.run_performance_test(
            calculate_ensemble,
            "indicator_ensemble_calculation",
            iterations=5
        )

        # Assert performance requirements
        self.assertLess(metrics.execution_time, 10.0, "Ensemble calculation should be fast")
        self.assertGreater(metrics.throughput, 0.5, "Should handle reasonable throughput")


class TestAdaptiveParametersPerformance(TestCase):
    """Performance tests for adaptive parameter system."""

    def setUp(self):
        super().setUp()
        self.perf_runner = PerformanceTestRunner()

    @performance_test()
    def test_adaptive_parameter_optimization(self):
        """Test performance of adaptive parameter optimization."""
        param_manager = AdaptiveParameterManager()

        # Add multiple parameters
        param_manager.add_parameter("rsi_period", 14, min_val=5, max_val=25)
        param_manager.add_parameter("sma_fast", 10, min_val=5, max_val=20)
        param_manager.add_parameter("sma_slow", 20, min_val=10, max_val=40)
        param_manager.add_parameter("macd_fast", 12, min_val=8, max_val=20)
        param_manager.add_parameter("macd_slow", 26, min_val=20, max_val=40)

        # Create test data
        dates = pd.date_range('2023-01-01', periods=1000, freq='1H')
        returns = np.random.normal(0.001, 0.02, 1000)  # Daily returns

        def optimize_parameters():
            # Simulate parameter optimization
            for _ in range(50):  # 50 optimization iterations
                params = param_manager.get_current_parameters()

                # Simulate fitness calculation
                fitness = np.random.random()

                # Update parameters based on fitness
                param_manager.update_parameters(fitness, returns[-100:])

            return param_manager.get_current_parameters()

        metrics = self.perf_runner.run_performance_test(
            optimize_parameters,
            "adaptive_parameter_optimization",
            iterations=3
        )

        # Assert reasonable optimization time
        self.assertLess(metrics.execution_time, 15.0, "Parameter optimization should be reasonable")


if __name__ == "__main__":
    unittest.main()