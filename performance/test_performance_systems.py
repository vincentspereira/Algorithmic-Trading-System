#!/usr/bin/env python3
"""
Test Suite for Performance Testing and Latency Benchmarking Systems
This module provides comprehensive tests for the performance testing infrastructure.
"""

import asyncio
import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch, AsyncMock
import numpy as np
import pytest

# Import the modules we're testing
from comprehensive_test_suite import (
    PerformanceTestSuite, TestConfiguration, PerformanceMetrics,
    NautilusTraderUser
)
from latency_benchmarking import (
    LatencyBenchmark, LatencyMeasurement, LatencyStatistics,
    HighPrecisionTimer
)

class TestHighPrecisionTimer(unittest.TestCase):
    """Test cases for HighPrecisionTimer"""
    
    def setUp(self):
        self.timer = HighPrecisionTimer()
    
    def test_timer_initialization(self):
        """Test timer initialization"""
        self.assertIsNotNone(self.timer.overhead_ns)
        self.assertIsInstance(self.timer.overhead_ns, int)
        self.assertGreaterEqual(self.timer.overhead_ns, 0)
    
    def test_timer_start_stop(self):
        """Test timer start/stop functionality"""
        self.timer.start()
        self.assertIsNotNone(self.timer.start_time)
        
        # Simulate some work
        import time
        time.sleep(0.001)  # 1ms
        
        elapsed_ns = self.timer.stop()
        self.assertIsInstance(elapsed_ns, int)
        self.assertGreater(elapsed_ns, 0)
        self.assertIsNone(self.timer.start_time)
    
    def test_timer_without_start(self):
        """Test timer stop without start raises error"""
        with self.assertRaises(ValueError):
            self.timer.stop()
    
    def test_timer_precision(self):
        """Test timer precision and consistency"""
        measurements = []
        for _ in range(100):
            self.timer.start()
            # Minimal operation
            x = 1 + 1
            elapsed = self.timer.stop()
            measurements.append(elapsed)
        
        # Check that measurements are reasonable
        mean_ns = np.mean(measurements)
        std_ns = np.std(measurements)
        
        # Should be very fast (less than 1 microsecond on average)
        self.assertLess(mean_ns, 1000)  # Less than 1 microsecond
        
        # Should have low variance for consistent operations
        cv = std_ns / mean_ns if mean_ns > 0 else 0
        self.assertLess(cv, 2.0)  # Coefficient of variation < 2

class TestLatencyMeasurement(unittest.TestCase):
    """Test cases for LatencyMeasurement"""
    
    def test_latency_measurement_creation(self):
        """Test LatencyMeasurement creation and properties"""
        measurement = LatencyMeasurement(
            timestamp=1234567890.0,
            operation="test_op",
            latency_ns=1500000,  # 1.5ms
            success=True,
            metadata={"test": "data"}
        )
        
        self.assertEqual(measurement.timestamp, 1234567890.0)
        self.assertEqual(measurement.operation, "test_op")
        self.assertEqual(measurement.latency_ns, 1500000)
        self.assertTrue(measurement.success)
        self.assertEqual(measurement.metadata, {"test": "data"})
        
        # Test property conversions
        self.assertEqual(measurement.latency_us, 1500.0)
        self.assertEqual(measurement.latency_ms, 1.5)

class TestLatencyStatistics(unittest.TestCase):
    """Test cases for LatencyStatistics"""
    
    def test_latency_statistics_properties(self):
        """Test LatencyStatistics property conversions"""
        stats = LatencyStatistics(
            operation="test_op",
            sample_count=1000,
            mean_ns=2500000.0,  # 2.5ms
            median_ns=2000000.0,  # 2ms
            std_dev_ns=500000.0,  # 0.5ms
            min_ns=1000000,  # 1ms
            max_ns=5000000,  # 5ms
            p50_ns=2000000.0,
            p90_ns=3500000.0,
            p95_ns=4000000.0,
            p99_ns=4800000.0,  # 4.8ms
            p99_9_ns=4950000.0,
            p99_99_ns=4995000.0,
            success_rate=0.99
        )
        
        # Test microsecond conversions
        self.assertEqual(stats.mean_us, 2500.0)
        self.assertEqual(stats.p99_us, 4800.0)

class TestLatencyBenchmark(unittest.TestCase):
    """Test cases for LatencyBenchmark"""
    
    def setUp(self):
        self.benchmark = LatencyBenchmark()
    
    def test_benchmark_initialization(self):
        """Test benchmark initialization"""
        self.assertEqual(self.benchmark.base_url, "http://localhost:8000")
        self.assertEqual(self.benchmark.websocket_url, "ws://localhost:8001")
        self.assertIsInstance(self.benchmark.measurements, list)
        self.assertIsInstance(self.benchmark.timer, HighPrecisionTimer)
    
    @pytest.mark.asyncio
    async def test_benchmark_api_endpoints(self):
        """Test API endpoint benchmarking"""
        results = await self.benchmark._benchmark_api_endpoints()
        
        self.assertIsInstance(results, dict)
        self.assertIn("health_check", results)
        self.assertIn("portfolio_get", results)
        
        # Check structure of results
        for endpoint_name, stats in results.items():
            self.assertIn("mean_ns", stats)
            self.assertIn("p99_ns", stats)
            self.assertIn("success_rate", stats)
            self.assertIn("sample_count", stats)
    
    @pytest.mark.asyncio
    async def test_benchmark_websocket(self):
        """Test WebSocket benchmarking"""
        results = await self.benchmark._benchmark_websocket()
        
        self.assertIsInstance(results, dict)
        self.assertIn("connection", results)
        self.assertIn("message_roundtrip", results)
        
        # Check structure
        for test_type, stats in results.items():
            self.assertIn("mean_ns", stats)
            self.assertIn("p99_ns", stats)
    
    @pytest.mark.asyncio
    async def test_benchmark_database_operations(self):
        """Test database operation benchmarking"""
        results = await self.benchmark._benchmark_database_operations()
        
        self.assertIsInstance(results, dict)
        self.assertIn("simple_select", results)
        self.assertIn("portfolio_select", results)
        
        # Verify realistic latencies (should be in reasonable range)
        for operation, stats in results.items():
            mean_us = stats["mean_ns"] / 1000.0
            self.assertGreater(mean_us, 0.1)  # At least 0.1 microseconds
            self.assertLess(mean_us, 100000)  # Less than 100ms
    
    @pytest.mark.asyncio
    async def test_benchmark_cache_operations(self):
        """Test cache operation benchmarking"""
        results = await self.benchmark._benchmark_cache_operations()
        
        self.assertIsInstance(results, dict)
        self.assertIn("get", results)
        self.assertIn("set", results)
        
        # Cache operations should be faster than database operations
        for operation, stats in results.items():
            mean_us = stats["mean_ns"] / 1000.0
            self.assertLess(mean_us, 10000)  # Less than 10ms
    
    def test_calculate_latency_statistics(self):
        """Test latency statistics calculation"""
        # Create test measurements
        measurements = []
        latencies_ns = [1000000, 1500000, 2000000, 2500000, 3000000]  # 1-3ms range
        
        for i, latency_ns in enumerate(latencies_ns):
            measurement = LatencyMeasurement(
                timestamp=float(i),
                operation="test_op",
                latency_ns=latency_ns,
                success=True,
                metadata={}
            )
            measurements.append(measurement)
        
        stats = self.benchmark._calculate_latency_statistics("test_op", measurements)
        
        self.assertEqual(stats.operation, "test_op")
        self.assertEqual(stats.sample_count, 5)
        self.assertEqual(stats.success_rate, 1.0)
        self.assertEqual(stats.min_ns, 1000000)
        self.assertEqual(stats.max_ns, 3000000)
        
        # Check mean calculation
        expected_mean = sum(latencies_ns) / len(latencies_ns)
        self.assertAlmostEqual(stats.mean_ns, expected_mean, places=0)
    
    def test_calculate_latency_statistics_empty(self):
        """Test latency statistics with empty measurements"""
        stats = self.benchmark._calculate_latency_statistics("empty_op", [])
        
        self.assertEqual(stats.operation, "empty_op")
        self.assertEqual(stats.sample_count, 0)
        self.assertEqual(stats.success_rate, 0)
        self.assertEqual(stats.mean_ns, 0)
    
    def test_calculate_percentile_distribution(self):
        """Test percentile distribution calculation"""
        latencies_ns = list(range(1000000, 10000000, 100000))  # 1-10ms range
        
        distribution = self.benchmark._calculate_percentile_distribution(latencies_ns)
        
        self.assertIsInstance(distribution, dict)
        self.assertIn("p50", distribution)
        self.assertIn("p99", distribution)
        self.assertIn("p99.9", distribution)
        
        # Check that percentiles are in ascending order
        self.assertLessEqual(distribution["p50"], distribution["p90"])
        self.assertLessEqual(distribution["p90"], distribution["p99"])
    
    def test_system_info_collection(self):
        """Test system information collection"""
        system_info = self.benchmark._get_system_info()
        
        self.assertIsInstance(system_info, dict)
        self.assertIn("cpu_count", system_info)
        self.assertIn("memory_total", system_info)
        self.assertIn("timer_resolution", system_info)
        self.assertIn("timer_overhead_ns", system_info)
    
    def test_save_results(self):
        """Test results saving functionality"""
        test_results = {
            "test": "data",
            "timestamp": "2024-01-01T00:00:00",
            "benchmarks": {"test_op": {"mean_ns": 1000000}}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_filename = f.name
        
        try:
            self.benchmark.save_results(test_results, temp_filename)
            
            # Verify file was created and contains correct data
            self.assertTrue(os.path.exists(temp_filename))
            
            with open(temp_filename, 'r') as f:
                loaded_data = json.load(f)
            
            self.assertEqual(loaded_data["test"], "data")
            self.assertEqual(loaded_data["benchmarks"]["test_op"]["mean_ns"], 1000000)
        
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)

class TestPerformanceTestSuite(unittest.TestCase):
    """Test cases for PerformanceTestSuite"""
    
    def setUp(self):
        self.config = TestConfiguration()
        self.test_suite = PerformanceTestSuite(self.config)
    
    def test_test_suite_initialization(self):
        """Test performance test suite initialization"""
        self.assertEqual(self.test_suite.config, self.config)
        self.assertIsInstance(self.test_suite.results, list)
        self.assertIsNone(self.test_suite.baseline_metrics)
    
    def test_configuration_defaults(self):
        """Test default configuration values"""
        config = TestConfiguration()
        
        self.assertEqual(config.base_url, "http://localhost:8000")
        self.assertEqual(config.websocket_url, "ws://localhost:8001")
        self.assertEqual(config.load_test_users, 100)
        self.assertEqual(config.load_test_duration, 300)
        self.assertEqual(config.max_response_time, 2.0)
        self.assertEqual(config.max_error_rate, 0.01)
    
    def test_performance_metrics_creation(self):
        """Test PerformanceMetrics creation"""
        from datetime import datetime
        
        metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            test_type="load_test",
            duration=300.0,
            total_requests=10000,
            successful_requests=9950,
            failed_requests=50,
            average_response_time=0.5,
            median_response_time=0.4,
            p95_response_time=1.2,
            p99_response_time=2.1,
            min_response_time=0.1,
            max_response_time=5.0,
            requests_per_second=33.3,
            error_rate=0.005,
            cpu_usage=45.2,
            memory_usage=62.8,
            network_io={"bytes_sent": 1000000, "bytes_recv": 2000000},
            disk_io={"read_bytes": 500000, "write_bytes": 300000}
        )
        
        self.assertEqual(metrics.test_type, "load_test")
        self.assertEqual(metrics.total_requests, 10000)
        self.assertEqual(metrics.error_rate, 0.005)
        self.assertIsInstance(metrics.network_io, dict)
    
    def test_calculate_performance_degradation(self):
        """Test performance degradation calculation"""
        from datetime import datetime
        
        baseline = PerformanceMetrics(
            timestamp=datetime.now(),
            test_type="baseline",
            duration=60.0,
            total_requests=1000,
            successful_requests=1000,
            failed_requests=0,
            average_response_time=0.5,
            median_response_time=0.4,
            p95_response_time=1.0,
            p99_response_time=1.5,
            min_response_time=0.1,
            max_response_time=2.0,
            requests_per_second=16.7,
            error_rate=0.0,
            cpu_usage=30.0,
            memory_usage=50.0,
            network_io={},
            disk_io={}
        )
        
        current = PerformanceMetrics(
            timestamp=datetime.now(),
            test_type="load_test",
            duration=300.0,
            total_requests=5000,
            successful_requests=4950,
            failed_requests=50,
            average_response_time=0.75,  # 50% increase
            median_response_time=0.6,
            p95_response_time=1.5,
            p99_response_time=2.2,
            min_response_time=0.1,
            max_response_time=3.0,
            requests_per_second=15.0,  # ~10% decrease
            error_rate=0.01,
            cpu_usage=45.0,  # 15% increase
            memory_usage=65.0,  # 15% increase
            network_io={},
            disk_io={}
        )
        
        degradation = self.test_suite.calculate_performance_degradation(baseline, current)
        
        self.assertAlmostEqual(degradation["response_time_increase"], 50.0, places=1)
        self.assertAlmostEqual(degradation["throughput_decrease"], 10.18, places=1)
        self.assertEqual(degradation["error_rate_increase"], 1.0)  # 1% increase
        self.assertEqual(degradation["cpu_usage_increase"], 15.0)
    
    def test_detect_breaking_point(self):
        """Test breaking point detection"""
        from datetime import datetime
        
        # Normal metrics - should not trigger breaking point
        normal_metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            test_type="normal",
            duration=300.0,
            total_requests=10000,
            successful_requests=9990,
            failed_requests=10,
            average_response_time=0.5,  # Below threshold
            median_response_time=0.4,
            p95_response_time=1.0,
            p99_response_time=1.5,
            min_response_time=0.1,
            max_response_time=2.0,
            requests_per_second=2000,  # Above threshold
            error_rate=0.001,  # Below threshold
            cpu_usage=50.0,
            memory_usage=60.0,
            network_io={},
            disk_io={}
        )
        
        self.assertFalse(self.test_suite.detect_breaking_point(normal_metrics))
        
        # Breaking point metrics - should trigger
        breaking_metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            test_type="breaking",
            duration=300.0,
            total_requests=10000,
            successful_requests=9800,
            failed_requests=200,
            average_response_time=3.0,  # Above threshold
            median_response_time=2.5,
            p95_response_time=5.0,
            p99_response_time=8.0,
            min_response_time=0.5,
            max_response_time=10.0,
            requests_per_second=500,  # Below threshold
            error_rate=0.02,  # Above threshold
            cpu_usage=90.0,
            memory_usage=95.0,
            network_io={},
            disk_io={}
        )
        
        self.assertTrue(self.test_suite.detect_breaking_point(breaking_metrics))

class TestIntegration(unittest.TestCase):
    """Integration tests for performance testing systems"""
    
    @pytest.mark.asyncio
    async def test_full_latency_benchmark_flow(self):
        """Test complete latency benchmark flow"""
        benchmark = LatencyBenchmark()
        
        # Run a minimal benchmark
        results = await benchmark.run_comprehensive_benchmark()
        
        # Verify structure
        self.assertIn("benchmark_start", results)
        self.assertIn("benchmark_end", results)
        self.assertIn("benchmarks", results)
        self.assertIn("analysis", results)
        self.assertIn("recommendations", results)
        
        # Verify benchmark categories
        benchmarks = results["benchmarks"]
        expected_categories = ["api_endpoints", "websocket", "database", "cache", "network", "trading"]
        
        for category in expected_categories:
            self.assertIn(category, benchmarks)
        
        # Verify recommendations structure
        recommendations = results["recommendations"]
        self.assertIsInstance(recommendations, list)
        
        for rec in recommendations:
            self.assertIn("category", rec)
            self.assertIn("priority", rec)
            self.assertIn("recommendation", rec)
    
    def test_performance_test_configuration_validation(self):
        """Test performance test configuration validation"""
        # Test valid configuration
        valid_config = TestConfiguration(
            base_url="http://localhost:8000",
            load_test_users=50,
            load_test_duration=60,
            max_response_time=1.0,
            max_error_rate=0.005
        )
        
        test_suite = PerformanceTestSuite(valid_config)
        self.assertEqual(test_suite.config.load_test_users, 50)
        self.assertEqual(test_suite.config.max_response_time, 1.0)
    
    def test_measurement_data_consistency(self):
        """Test consistency of measurement data across systems"""
        # Create measurements using both systems
        timer = HighPrecisionTimer()
        
        # Test timer consistency
        measurements = []
        for _ in range(100):
            timer.start()
            # Simulate minimal work
            result = sum(range(10))
            elapsed = timer.stop()
            measurements.append(elapsed)
        
        # Verify measurements are reasonable and consistent
        mean_ns = np.mean(measurements)
        std_ns = np.std(measurements)
        
        self.assertGreater(mean_ns, 0)
        self.assertLess(mean_ns, 1000000)  # Less than 1ms for simple operation
        
        # Coefficient of variation should be reasonable
        cv = std_ns / mean_ns if mean_ns > 0 else 0
        self.assertLess(cv, 5.0)  # Less than 500% variation

def run_performance_tests():
    """Run all performance tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestHighPrecisionTimer,
        TestLatencyMeasurement,
        TestLatencyStatistics,
        TestLatencyBenchmark,
        TestPerformanceTestSuite,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_performance_tests()
    exit(0 if success else 1)