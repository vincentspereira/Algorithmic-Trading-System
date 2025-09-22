"""
Stress tests for Nautilus Trader Engine.
Tests system behavior under extreme loads and adverse conditions.
"""

import unittest
import asyncio
import time
import psutil
import gc
import threading
import concurrent.futures
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from queue import Queue
import random
import signal
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from nautilus_trader_engine.tests.testing_framework import TestCase, stress_test, StressTestRunner
from nautilus_trader_engine.core.base.dependency_injection import DependencyContainer
from nautilus_trader_engine.core.base.event_system import EventSystem, Event
from nautilus_trader_engine.core.caching.cache_layer import MultiLevelCache, CacheLevel
from nautilus_trader_engine.core.streaming.streaming_architecture import (
    StreamManager, StreamPipeline, StreamMessage, StreamType,
    MarketDataProcessor, TechnicalIndicatorProcessor
)
from nautilus_trader_engine.core.fault_tolerance.fault_tolerance_system import (
    get_error_handler, get_health_monitor, fault_tolerant
)
from nautilus_trader_engine.engines.parallel_processing_engine import ParallelProcessor


class TestExtremeLoadStress(TestCase):
    """Stress tests for extreme load conditions."""

    def setUp(self):
        super().setUp()
        self.stress_runner = StressTestRunner(duration=30, concurrent_users=50)

    @stress_test()
    def test_extreme_concurrent_operations(self):
        """Test system under extreme concurrent load."""
        results = []
        errors = []
        lock = threading.Lock()

        def high_load_operation(user_id, operation_id):
            try:
                # Simulate complex calculation
                data = np.random.random((1000, 100))
                result = np.linalg.svd(data)

                # Simulate I/O operation
                time.sleep(random.uniform(0.001, 0.01))

                # Simulate memory allocation
                large_list = [i for i in range(10000)]

                with lock:
                    results.append({
                        'user_id': user_id,
                        'operation_id': operation_id,
                        'result_size': len(large_list),
                        'timestamp': datetime.now()
                    })

                return result[0].shape

            except Exception as e:
                with lock:
                    errors.append({
                        'user_id': user_id,
                        'operation_id': operation_id,
                        'error': str(e),
                        'timestamp': datetime.now()
                    })
                return None

        # Run stress test
        stress_results = self.stress_runner.run_stress_test(
            lambda uid, oid: high_load_operation(uid, oid),
            "extreme_concurrent_operations"
        )

        # Analyze results
        success_rate = stress_results['successful_requests'] / max(1, stress_results['total_requests'])

        # Assert system stability under extreme load
        self.assertGreater(success_rate, 0.95, "Should maintain high success rate under extreme load")
        self.assertGreater(stress_results['throughput'], 100, "Should handle significant throughput")
        self.assertLess(stress_results['average_response_time'], 1.0, "Response time should be reasonable")

    @stress_test()
    def test_memory_pressure_stress(self):
        """Test system behavior under memory pressure."""
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024

        def memory_intensive_operation():
            # Allocate large amounts of memory
            large_objects = []
            for i in range(100):
                # Create large data structures
                data = {
                    'array': np.random.random((1000, 1000)),
                    'dataframe': pd.DataFrame(np.random.random((1000, 50))),
                    'list': [j for j in range(10000)],
                    'string': 'x' * 100000  # 100KB string
                }
                large_objects.append(data)

            # Perform calculations
            total_sum = sum(obj['array'].sum() for obj in large_objects)

            # Clean up
            del large_objects
            gc.collect()

            return total_sum

        # Run stress test
        stress_results = self.stress_runner.run_stress_test(
            memory_intensive_operation,
            "memory_pressure_test"
        )

        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_growth = final_memory - initial_memory

        # Assert memory is properly managed
        self.assertLess(memory_growth, 1000, "Memory growth should be reasonable")
        self.assertGreater(stress_results['successful_requests'], 0, "Should complete some operations")

    @stress_test()
    def test_network_failure_simulation(self):
        """Test system resilience under simulated network failures."""
        success_count = 0
        failure_count = 0
        lock = threading.Lock()

        @fault_tolerant(retry_attempts=3)
        def network_operation():
            nonlocal success_count, failure_count

            # Simulate random network failures
            if random.random() < 0.3:  # 30% failure rate
                with lock:
                    failure_count += 1
                raise ConnectionError("Simulated network failure")

            # Simulate network latency
            time.sleep(random.uniform(0.001, 0.1))

            with lock:
                success_count += 1

            return "success"

        # Run stress test
        stress_results = self.stress_runner.run_stress_test(
            network_operation,
            "network_failure_simulation"
        )

        # Assert fault tolerance works
        total_operations = success_count + failure_count
        if total_operations > 0:
            success_rate = success_count / total_operations
            self.assertGreater(success_rate, 0.7, "Should maintain reasonable success rate with failures")

    @stress_test()
    def test_database_connection_storm(self):
        """Test system under database connection storm."""
        connection_pool = []
        lock = threading.Lock()

        def database_operation():
            try:
                # Simulate database connection
                with lock:
                    connection_pool.append(threading.current_thread().ident)

                # Simulate query execution time
                time.sleep(random.uniform(0.01, 0.05))

                # Simulate result processing
                result = np.random.random((100, 10))
                processed_result = result.sum()

                # Clean up connection
                with lock:
                    if threading.current_thread().ident in connection_pool:
                        connection_pool.remove(threading.current_thread().ident)

                return processed_result

            except Exception as e:
                # Clean up on error
                with lock:
                    if threading.current_thread().ident in connection_pool:
                        connection_pool.remove(threading.current_thread().ident)
                raise e

        # Run stress test
        stress_results = self.stress_runner.run_stress_test(
            database_operation,
            "database_connection_storm"
        )

        # Assert connection management works
        self.assertGreater(stress_results['successful_requests'], 0, "Should handle database operations")
        self.assertLess(len(connection_pool), 10, "Should not have excessive connections")


class TestStreamingStress(TestCase):
    """Stress tests for streaming components."""

    def setUp(self):
        super().setUp()
        self.stress_runner = StressTestRunner(duration=60, concurrent_users=20)
        self.stream_manager = StreamManager()

    @stress_test()
    def test_high_frequency_stream_processing(self):
        """Test streaming pipeline under high-frequency data."""
        async def run_streaming_stress_test():
            # Create multiple pipelines
            pipelines = []
            output_queues = []

            for i in range(5):
                pipeline = self.stream_manager.create_pipeline(f"stress_pipeline_{i}")
                market_processor = MarketDataProcessor(f"SYMBOL{i}")
                indicator_processor = TechnicalIndicatorProcessor(['SMA', 'RSI', 'MACD'])

                pipeline.add_processor(market_processor)
                pipeline.add_processor(indicator_processor)

                output_queue = asyncio.Queue()
                pipeline.add_output_queue("output", output_queue)
                output_queues.append(output_queue)
                pipelines.append(pipeline)

            # Start all pipelines
            for pipeline in pipelines:
                await pipeline.start()

            # Generate high-frequency data
            messages_sent = 0
            start_time = time.time()

            try:
                while time.time() - start_time < 30:  # 30 seconds of high-frequency data
                    for i, pipeline in enumerate(pipelines):
                        # Send burst of messages
                        for j in range(10):  # 10 messages per pipeline per iteration
                            message = StreamMessage(
                                stream_type=StreamType.MARKET_DATA,
                                symbol=f"SYMBOL{i}",
                                timestamp=datetime.now(),
                                data={
                                    'open': 100.0 + messages_sent * 0.001,
                                    'high': 101.0 + messages_sent * 0.001,
                                    'low': 99.0 + messages_sent * 0.001,
                                    'close': 100.5 + messages_sent * 0.001,
                                    'volume': 100000 + messages_sent * 10
                                },
                                sequence_number=messages_sent
                            )
                            await pipeline.ingest_message(message)
                            messages_sent += 1

                    # Small delay to prevent overwhelming
                    await asyncio.sleep(0.001)

            except Exception as e:
                print(f"Error during message sending: {e}")

            # Wait for processing
            await asyncio.sleep(5)

            # Collect results
            total_processed = 0
            for queue in output_queues:
                try:
                    while True:
                        result = queue.get_nowait()
                        total_processed += 1
                        queue.task_done()
                except asyncio.QueueEmpty:
                    pass

            # Stop pipelines
            for pipeline in pipelines:
                await pipeline.stop()

            return {
                'messages_sent': messages_sent,
                'messages_processed': total_processed,
                'processing_rate': total_processed / 30 if total_processed > 0 else 0,
                'loss_rate': (messages_sent - total_processed) / max(1, messages_sent)
            }

        # Run async test
        result = asyncio.run(run_streaming_stress_test())

        # Assert streaming performance
        self.assertGreater(result['processing_rate'], 100, "Should process at least 100 messages/second")
        self.assertLess(result['loss_rate'], 0.5, "Message loss should be reasonable")

    @stress_test()
    def test_streaming_backpressure_handling(self):
        """Test streaming system under backpressure."""
        async def run_backpressure_test():
            # Create slow pipeline to induce backpressure
            pipeline = self.stream_manager.create_pipeline("backpressure_pipeline")

            class SlowProcessor(MarketDataProcessor):
                async def process(self, message):
                    # Simulate slow processing
                    await asyncio.sleep(0.1)  # 100ms delay
                    return await super().process(message)

            slow_processor = SlowProcessor("BACKPRESSURE")
            pipeline.add_processor(slow_processor)

            output_queue = asyncio.Queue(maxsize=10)  # Small queue to induce backpressure
            pipeline.add_output_queue("output", output_queue)

            await pipeline.start()

            # Send messages faster than they can be processed
            messages_sent = 0
            start_time = time.time()

            try:
                while time.time() - start_time < 10:  # 10 seconds
                    message = StreamMessage(
                        stream_type=StreamType.MARKET_DATA,
                        symbol="BACKPRESSURE",
                        timestamp=datetime.now(),
                        data={
                            'open': 100.0,
                            'high': 101.0,
                            'low': 99.0,
                            'close': 100.5,
                            'volume': 100000
                        },
                        sequence_number=messages_sent
                    )
                    await pipeline.ingest_message(message)
                    messages_sent += 1

                    # Don't add delay - send as fast as possible

            except Exception as e:
                print(f"Error during backpressure test: {e}")

            # Wait for processing to complete
            await asyncio.sleep(5)

            # Check results
            messages_processed = 0
            try:
                while True:
                    result = output_queue.get_nowait()
                    messages_processed += 1
                    output_queue.task_done()
            except asyncio.QueueEmpty:
                pass

            await pipeline.stop()

            return {
                'messages_sent': messages_sent,
                'messages_processed': messages_processed,
                'queue_size': output_queue.qsize(),
                'backpressure_ratio': messages_processed / max(1, messages_sent)
            }

        # Run async test
        result = asyncio.run(run_backpressure_test())

        # Assert backpressure handling
        self.assertGreater(result['messages_processed'], 0, "Should process some messages under backpressure")
        self.assertLess(result['queue_size'], 20, "Queue should not grow excessively")


class TestResourceExhaustionStress(TestCase):
    """Stress tests for resource exhaustion scenarios."""

    def setUp(self):
        super().setUp()
        self.stress_runner = StressTestRunner(duration=45, concurrent_users=30)

    @stress_test()
    def test_file_descriptor_exhaustion(self):
        """Test system behavior when file descriptors are exhausted."""
        files_opened = []
        errors = []

        def file_operation():
            try:
                # Try to open many files
                for i in range(10):
                    try:
                        # Create temporary file
                        import tempfile
                        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                            f.write(f"Test data {i}")
                            files_opened.append(f.name)
                    except OSError as e:
                        errors.append(str(e))
                        break

                # Clean up
                for file_path in files_opened:
                    try:
                        os.unlink(file_path)
                    except:
                        pass

                return len(files_opened)

            except Exception as e:
                errors.append(str(e))
                return 0

        # Run stress test
        stress_results = self.stress_runner.run_stress_test(
            file_operation,
            "file_descriptor_exhaustion"
        )

        # Assert graceful handling of resource exhaustion
        self.assertGreater(stress_results['successful_requests'], 0, "Should handle some file operations")

    @stress_test()
    def test_thread_pool_exhaustion(self):
        """Test system under thread pool exhaustion."""
        results = []
        errors = []

        def cpu_intensive_task():
            try:
                # CPU-intensive calculation
                result = 0
                for i in range(100000):
                    result += i ** 2

                results.append(result)
                return result

            except Exception as e:
                errors.append(str(e))
                return None

        # Run stress test with high concurrency
        stress_runner = StressTestRunner(duration=20, concurrent_users=100)
        stress_results = stress_runner.run_stress_test(
            cpu_intensive_task,
            "thread_pool_exhaustion"
        )

        # Assert thread pool handles high load
        self.assertGreater(len(results), 0, "Should complete some CPU-intensive tasks")
        self.assertLess(len(errors), len(results) * 0.5, "Error rate should be reasonable")

    @stress_test()
    def test_cache_memory_exhaustion(self):
        """Test caching system under memory exhaustion."""
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create cache with very small memory limit
            cache = MultiLevelCache(
                levels=[CacheLevel.L1_MEMORY],
                memory_size=1,  # Very small cache
                disk_config={"cache_dir": temp_dir, "max_size_mb": 1}
            )

            def cache_stress_operation():
                try:
                    # Try to cache large objects
                    large_data = {
                        'data': 'x' * 100000,  # 100KB string
                        'array': np.random.random((1000, 100))  # Large array
                    }

                    cache.set(f"stress_key_{random.randint(0, 1000)}", large_data)
                    return True

                except Exception as e:
                    return False

            # Run stress test
            stress_results = self.stress_runner.run_stress_test(
                cache_stress_operation,
                "cache_memory_exhaustion"
            )

            # Assert cache handles memory pressure
            self.assertGreater(stress_results['successful_requests'], 0, "Should cache some data")


class TestFailureScenarioStress(TestCase):
    """Stress tests for various failure scenarios."""

    def setUp(self):
        super().setUp()
        self.stress_runner = StressTestRunner(duration=60, concurrent_users=25)

    @stress_test()
    def test_cascading_failure_simulation(self):
        """Test system behavior under cascading failures."""
        service_status = {
            'database': True,
            'cache': True,
            'api': True,
            'message_queue': True
        }

        failures = []
        recoveries = []

        def unreliable_service_operation(service_name):
            try:
                # Simulate service failure
                if random.random() < 0.1:  # 10% chance of failure
                    service_status[service_name] = False
                    failures.append(f"{service_name} failed")

                if not service_status[service_name]:
                    # Try recovery
                    if random.random() < 0.3:  # 30% chance of recovery
                        service_status[service_name] = True
                        recoveries.append(f"{service_name} recovered")
                    else:
                        raise RuntimeError(f"Service {service_name} is down")

                # Simulate service work
                time.sleep(random.uniform(0.001, 0.01))
                return f"{service_name} operation successful"

            except Exception as e:
                return f"{service_name} operation failed: {e}"

        # Run stress test
        stress_results = self.stress_runner.run_stress_test(
            lambda: unreliable_service_operation(random.choice(list(service_status.keys()))),
            "cascading_failure_simulation"
        )

        # Assert system handles cascading failures
        self.assertGreater(stress_results['successful_requests'], 0, "Should complete some operations despite failures")
        self.assertGreater(len(recoveries), 0, "Should have some service recoveries")

    @stress_test()
    def test_data_corruption_stress(self):
        """Test system resilience to data corruption."""
        valid_data_count = 0
        corrupted_data_count = 0
        recovery_attempts = 0

        def data_processing_operation():
            nonlocal valid_data_count, corrupted_data_count, recovery_attempts

            try:
                # Generate data with corruption
                data = np.random.random(1000)

                # Simulate corruption
                if random.random() < 0.2:  # 20% corruption rate
                    corrupted_data_count += 1
                    # Corrupt data
                    data[100:200] = np.nan
                    data[500:600] = np.inf

                # Try to process data
                if np.any(np.isnan(data)) or np.any(np.isinf(data)):
                    recovery_attempts += 1
                    # Attempt recovery
                    data = np.nan_to_num(data, nan=0.0, posinf=999, neginf=-999)

                # Process data
                result = {
                    'mean': np.mean(data),
                    'std': np.std(data),
                    'min': np.min(data),
                    'max': np.max(data)
                }

                valid_data_count += 1
                return result

            except Exception as e:
                return {'error': str(e)}

        # Run stress test
        stress_results = self.stress_runner.run_stress_test(
            data_processing_operation,
            "data_corruption_stress"
        )

        # Assert data corruption handling
        self.assertGreater(valid_data_count, 0, "Should process some valid data")
        self.assertGreater(recovery_attempts, 0, "Should attempt data recovery")

    @stress_test()
    def test_system_restart_simulation(self):
        """Test system behavior during simulated restarts."""
        operation_count = 0
        restart_events = []
        recovery_times = []

        def operation_with_restart_simulation():
            nonlocal operation_count

            operation_count += 1

            # Simulate system restart
            if operation_count % 100 == 0:
                restart_start = time.time()
                restart_events.append(f"Restart at operation {operation_count}")

                # Simulate restart delay
                time.sleep(random.uniform(0.1, 0.5))

                recovery_time = time.time() - restart_start
                recovery_times.append(recovery_time)

            # Simulate normal operation
            time.sleep(random.uniform(0.001, 0.01))
            return f"Operation {operation_count} completed"

        # Run stress test
        stress_results = self.stress_runner.run_stress_test(
            operation_with_restart_simulation,
            "system_restart_simulation"
        )

        # Assert restart handling
        self.assertGreater(stress_results['successful_requests'], 0, "Should complete operations after restarts")
        if recovery_times:
            avg_recovery_time = sum(recovery_times) / len(recovery_times)
            self.assertLess(avg_recovery_time, 1.0, "Recovery time should be reasonable")


if __name__ == "__main__":
    unittest.main()