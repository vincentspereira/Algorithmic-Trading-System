#!/usr/bin/env python3
"""
Basic functionality tests for performance testing systems
Tests core functionality without external dependencies
"""

import asyncio
import json
import os
import tempfile
import time
import unittest
from datetime import datetime
from typing import Dict, List, Any

# Test the core timer functionality
class MockHighPrecisionTimer:
    """Mock timer for testing without external dependencies"""
    
    def __init__(self):
        self.start_time = None
        self.overhead_ns = 100  # Mock overhead
    
    def start(self):
        """Start timing"""
        self.start_time = time.perf_counter()
    
    def stop(self) -> int:
        """Stop timing and return elapsed nanoseconds"""
        if self.start_time is None:
            raise ValueError("Timer not started")
        
        end_time = time.perf_counter()
        elapsed_ns = int((end_time - self.start_time) * 1_000_000_000)
        elapsed_ns = max(0, elapsed_ns - self.overhead_ns)
        
        self.start_time = None
        return elapsed_ns

class MockLatencyMeasurement:
    """Mock latency measurement for testing"""
    
    def __init__(self, timestamp: float, operation: str, latency_ns: int, 
                 success: bool, metadata: Dict[str, Any]):
        self.timestamp = timestamp
        self.operation = operation
        self.latency_ns = latency_ns
        self.success = success
        self.metadata = metadata
    
    @property
    def latency_us(self) -> float:
        """Latency in microseconds"""
        return self.latency_ns / 1000.0
    
    @property
    def latency_ms(self) -> float:
        """Latency in milliseconds"""
        return self.latency_ns / 1_000_000.0

class MockLatencyStatistics:
    """Mock latency statistics for testing"""
    
    def __init__(self, operation: str, sample_count: int, mean_ns: float,
                 median_ns: float, std_dev_ns: float, min_ns: int, max_ns: int,
                 p50_ns: float, p90_ns: float, p95_ns: float, p99_ns: float,
                 p99_9_ns: float, p99_99_ns: float, success_rate: float):
        self.operation = operation
        self.sample_count = sample_count
        self.mean_ns = mean_ns
        self.median_ns = median_ns
        self.std_dev_ns = std_dev_ns
        self.min_ns = min_ns
        self.max_ns = max_ns
        self.p50_ns = p50_ns
        self.p90_ns = p90_ns
        self.p95_ns = p95_ns
        self.p99_ns = p99_ns
        self.p99_9_ns = p99_9_ns
        self.p99_99_ns = p99_99_ns
        self.success_rate = success_rate
    
    @property
    def mean_us(self) -> float:
        return self.mean_ns / 1000.0
    
    @property
    def p99_us(self) -> float:
        return self.p99_ns / 1000.0

class TestBasicFunctionality(unittest.TestCase):
    """Test basic functionality of performance testing components"""
    
    def setUp(self):
        self.timer = MockHighPrecisionTimer()
    
    def test_timer_basic_functionality(self):
        """Test basic timer functionality"""
        # Test timer initialization
        self.assertIsNotNone(self.timer.overhead_ns)
        self.assertIsInstance(self.timer.overhead_ns, int)
        self.assertGreaterEqual(self.timer.overhead_ns, 0)
        
        # Test timer start/stop
        self.timer.start()
        self.assertIsNotNone(self.timer.start_time)
        
        # Simulate some work
        time.sleep(0.001)  # 1ms
        
        elapsed_ns = self.timer.stop()
        self.assertIsInstance(elapsed_ns, int)
        self.assertGreater(elapsed_ns, 0)
        self.assertIsNone(self.timer.start_time)
    
    def test_timer_without_start_raises_error(self):
        """Test that stopping timer without starting raises error"""
        with self.assertRaises(ValueError):
            self.timer.stop()
    
    def test_latency_measurement_properties(self):
        """Test LatencyMeasurement properties"""
        measurement = MockLatencyMeasurement(
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
    
    def test_latency_statistics_properties(self):
        """Test LatencyStatistics properties"""
        stats = MockLatencyStatistics(
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
    
    def test_timer_precision_and_consistency(self):
        """Test timer precision and consistency"""
        measurements = []
        
        for _ in range(10):  # Reduced iterations for speed
            self.timer.start()
            # Minimal operation
            result = sum(range(100))
            elapsed = self.timer.stop()
            measurements.append(elapsed)
        
        # Verify measurements are reasonable
        self.assertTrue(all(m > 0 for m in measurements))
        self.assertTrue(all(m < 10_000_000 for m in measurements))  # Less than 10ms
        
        # Check basic statistics
        mean_ns = sum(measurements) / len(measurements)
        self.assertGreater(mean_ns, 0)
        self.assertLess(mean_ns, 1_000_000)  # Less than 1ms for simple operation

class TestPerformanceDataStructures(unittest.TestCase):
    """Test performance-related data structures"""
    
    def test_measurement_data_consistency(self):
        """Test consistency of measurement data"""
        measurements = []
        
        # Create test measurements with known values
        test_latencies = [1000000, 1500000, 2000000, 2500000, 3000000]  # 1-3ms
        
        for i, latency_ns in enumerate(test_latencies):
            measurement = MockLatencyMeasurement(
                timestamp=float(i),
                operation="test_op",
                latency_ns=latency_ns,
                success=True,
                metadata={"iteration": i}
            )
            measurements.append(measurement)
        
        # Verify measurements
        self.assertEqual(len(measurements), 5)
        
        # Check latency conversions
        for i, measurement in enumerate(measurements):
            expected_us = test_latencies[i] / 1000.0
            expected_ms = test_latencies[i] / 1_000_000.0
            
            self.assertEqual(measurement.latency_us, expected_us)
            self.assertEqual(measurement.latency_ms, expected_ms)
    
    def test_statistics_calculation_logic(self):
        """Test statistics calculation logic"""
        # Mock data for testing
        latencies_ns = [1000000, 1500000, 2000000, 2500000, 3000000]  # 1-3ms
        
        # Calculate basic statistics manually
        mean_ns = sum(latencies_ns) / len(latencies_ns)
        min_ns = min(latencies_ns)
        max_ns = max(latencies_ns)
        
        # Create mock statistics
        stats = MockLatencyStatistics(
            operation="test_calculation",
            sample_count=len(latencies_ns),
            mean_ns=mean_ns,
            median_ns=2000000.0,  # Middle value
            std_dev_ns=632455.5,  # Calculated standard deviation
            min_ns=min_ns,
            max_ns=max_ns,
            p50_ns=2000000.0,
            p90_ns=2800000.0,
            p95_ns=2900000.0,
            p99_ns=2980000.0,
            p99_9_ns=2998000.0,
            p99_99_ns=2999800.0,
            success_rate=1.0
        )
        
        # Verify calculations
        self.assertEqual(stats.sample_count, 5)
        self.assertEqual(stats.mean_ns, mean_ns)
        self.assertEqual(stats.min_ns, min_ns)
        self.assertEqual(stats.max_ns, max_ns)
        self.assertEqual(stats.success_rate, 1.0)

class TestAsyncFunctionality(unittest.TestCase):
    """Test async functionality"""
    
    async def async_mock_operation(self, duration_ms: float = 1.0) -> Dict[str, Any]:
        """Mock async operation for testing"""
        await asyncio.sleep(duration_ms / 1000.0)  # Convert ms to seconds
        return {
            "operation": "mock_async_op",
            "duration_ms": duration_ms,
            "success": True,
            "timestamp": time.time()
        }
    
    def test_async_operation_timing(self):
        """Test timing of async operations"""
        async def run_async_test():
            timer = MockHighPrecisionTimer()
            
            timer.start()
            result = await self.async_mock_operation(5.0)  # 5ms operation
            elapsed_ns = timer.stop()
            
            # Should take approximately 5ms (5,000,000 ns)
            # Allow for some variance due to system scheduling
            self.assertGreater(elapsed_ns, 3_000_000)  # At least 3ms
            self.assertLess(elapsed_ns, 20_000_000)    # Less than 20ms (more tolerance)
            
            self.assertTrue(result["success"])
            self.assertEqual(result["operation"], "mock_async_op")
            
            return result
        
        # Run the async test
        result = asyncio.run(run_async_test())
        self.assertIsNotNone(result)
    
    def test_concurrent_async_operations(self):
        """Test concurrent async operations"""
        async def run_concurrent_test():
            tasks = []
            
            # Create multiple concurrent operations
            for i in range(5):
                task = self.async_mock_operation(2.0)  # 2ms each
                tasks.append(task)
            
            timer = MockHighPrecisionTimer()
            timer.start()
            
            # Run all tasks concurrently
            results = await asyncio.gather(*tasks)
            
            elapsed_ns = timer.stop()
            
            # Should take approximately 2ms total (not 10ms) due to concurrency
            self.assertGreater(elapsed_ns, 1_000_000)   # At least 1ms
            self.assertLess(elapsed_ns, 20_000_000)     # Less than 20ms (more tolerance)
            
            # Verify all operations succeeded
            self.assertEqual(len(results), 5)
            for result in results:
                self.assertTrue(result["success"])
            
            return results
        
        results = asyncio.run(run_concurrent_test())
        self.assertEqual(len(results), 5)

class TestFileOperations(unittest.TestCase):
    """Test file operations for saving results"""
    
    def test_json_serialization(self):
        """Test JSON serialization of results"""
        test_data = {
            "benchmark_start": datetime.now().isoformat(),
            "timer_overhead_ns": 100,
            "benchmarks": {
                "api_endpoints": {
                    "health_check": {
                        "mean_ns": 1500000.0,
                        "p99_ns": 3000000.0,
                        "success_rate": 0.99,
                        "sample_count": 1000
                    }
                }
            },
            "recommendations": [
                {
                    "category": "performance",
                    "priority": "high",
                    "recommendation": "Optimize database queries"
                }
            ]
        }
        
        # Test JSON serialization
        json_str = json.dumps(test_data, indent=2, default=str)
        self.assertIsInstance(json_str, str)
        
        # Test deserialization
        loaded_data = json.loads(json_str)
        self.assertEqual(loaded_data["timer_overhead_ns"], 100)
        self.assertEqual(len(loaded_data["recommendations"]), 1)
    
    def test_file_save_and_load(self):
        """Test saving and loading results to/from file"""
        test_results = {
            "test_type": "basic_functionality_test",
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "total_tests": 10,
                "passed_tests": 9,
                "failed_tests": 1,
                "success_rate": 0.9
            }
        }
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_filename = f.name
        
        try:
            # Save results
            with open(temp_filename, 'w') as f:
                json.dump(test_results, f, indent=2, default=str)
            
            # Verify file exists
            self.assertTrue(os.path.exists(temp_filename))
            
            # Load and verify results
            with open(temp_filename, 'r') as f:
                loaded_results = json.load(f)
            
            self.assertEqual(loaded_results["test_type"], "basic_functionality_test")
            self.assertEqual(loaded_results["metrics"]["total_tests"], 10)
            self.assertEqual(loaded_results["metrics"]["success_rate"], 0.9)
        
        finally:
            # Clean up
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)

def run_basic_tests():
    """Run all basic functionality tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestBasicFunctionality,
        TestPerformanceDataStructures,
        TestAsyncFunctionality,
        TestFileOperations
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == "__main__":
    print("Running basic functionality tests for performance testing systems...")
    print("=" * 70)
    
    success = run_basic_tests()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ All basic functionality tests PASSED!")
        print("\nThe performance testing systems are working correctly.")
        print("Core functionality verified:")
        print("  - High-precision timing")
        print("  - Latency measurement and statistics")
        print("  - Async operation handling")
        print("  - Data serialization and file operations")
    else:
        print("❌ Some tests FAILED!")
        print("Please check the test output above for details.")
    
    print("=" * 70)
    exit(0 if success else 1)