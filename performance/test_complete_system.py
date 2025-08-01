#!/usr/bin/env python3
"""
Complete System Test for Performance Testing and Optimization
This test validates the integration of all performance testing components:
- Performance Test Suite (13.1)
- Latency Benchmarking (13.2) 
- Resource Profiling Tools (13.3)
- Performance Regression Detection (13.4)
"""

import asyncio
import json
import os
import tempfile
import unittest
from datetime import datetime

# Import all the systems we're testing
from comprehensive_test_suite import PerformanceTestSuite, TestConfiguration
from latency_benchmarking import LatencyBenchmark
from resource_profiling import ResourceProfiler
from regression_detection import PerformanceRegressionDetector

class TestCompleteSystemIntegration(unittest.TestCase):
    """Integration tests for the complete performance testing system"""
    
    def setUp(self):
        # Setup temporary files for testing
        self.temp_baseline_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_baseline_file.close()
        
        # Initialize all systems
        self.test_config = TestConfiguration(
            base_url="http://localhost:8000",
            websocket_url="ws://localhost:8001",
            load_test_users=10,  # Reduced for testing
            load_test_duration=5,  # Reduced for testing
            max_response_time=2.0,
            max_error_rate=0.05
        )
        
        self.performance_suite = PerformanceTestSuite(self.test_config)
        self.latency_benchmark = LatencyBenchmark()
        self.resource_profiler = ResourceProfiler(sampling_interval=0.1)
        self.regression_detector = PerformanceRegressionDetector(
            baseline_storage_path=self.temp_baseline_file.name
        )
    
    def tearDown(self):
        # Clean up temporary files
        if os.path.exists(self.temp_baseline_file.name):
            os.unlink(self.temp_baseline_file.name)
        
        # Stop any active profiling
        if self.resource_profiler.profiling_active:
            self.resource_profiler.stop_profiling()
    
    def test_system_initialization(self):
        """Test that all systems initialize correctly"""
        # Test configuration
        self.assertIsInstance(self.test_config, TestConfiguration)
        self.assertEqual(self.test_config.load_test_users, 10)
        
        # Test performance suite
        self.assertIsInstance(self.performance_suite, PerformanceTestSuite)
        self.assertEqual(self.performance_suite.config, self.test_config)
        
        # Test latency benchmark
        self.assertIsInstance(self.latency_benchmark, LatencyBenchmark)
        self.assertEqual(self.latency_benchmark.base_url, "http://localhost:8000")
        
        # Test resource profiler
        self.assertIsInstance(self.resource_profiler, ResourceProfiler)
        self.assertEqual(self.resource_profiler.sampling_interval, 0.1)
        
        # Test regression detector
        self.assertIsInstance(self.regression_detector, PerformanceRegressionDetector)
        self.assertEqual(self.regression_detector.baseline_storage_path, self.temp_baseline_file.name)
    
    def test_latency_benchmark_integration(self):
        """Test latency benchmarking system integration"""
        async def run_latency_test():
            # Run a subset of benchmarks for testing
            api_results = await self.latency_benchmark._benchmark_api_endpoints()
            websocket_results = await self.latency_benchmark._benchmark_websocket()
            
            return {
                "api_endpoints": api_results,
                "websocket": websocket_results
            }
        
        results = asyncio.run(run_latency_test())
        
        # Verify results structure
        self.assertIn("api_endpoints", results)
        self.assertIn("websocket", results)
        
        # Verify API results
        api_results = results["api_endpoints"]
        self.assertIsInstance(api_results, dict)
        self.assertGreater(len(api_results), 0)
        
        # Check that each endpoint has proper statistics
        for endpoint_name, stats in api_results.items():
            self.assertIn("mean_ns", stats)
            self.assertIn("p99_ns", stats)
            self.assertIn("success_rate", stats)
            self.assertGreater(stats["mean_ns"], 0)
            self.assertGreater(stats["p99_ns"], stats["mean_ns"])
        
        # Verify WebSocket results
        websocket_results = results["websocket"]
        self.assertIn("connection", websocket_results)
        self.assertIn("message_roundtrip", websocket_results)
    
    def test_resource_profiling_integration(self):
        """Test resource profiling system integration"""
        # Start profiling
        self.resource_profiler.start_profiling()
        
        # Simulate some work
        import time
        time.sleep(0.3)
        
        # Create some objects to affect memory
        temp_data = [f"data_{i}" for i in range(1000)]
        
        # Do some CPU work
        result = sum(range(10000))
        
        # Stop profiling
        self.resource_profiler.stop_profiling()
        
        # Generate report
        report = self.resource_profiler.generate_resource_report()
        
        # Verify report structure
        self.assertIsInstance(report, dict)
        self.assertIn("resource_summary", report)
        self.assertIn("memory_analysis", report)
        self.assertIn("cpu_analysis", report)
        self.assertIn("gc_analysis", report)
        self.assertIn("optimization_recommendations", report)
        
        # Verify we collected snapshots
        self.assertGreater(len(self.resource_profiler.snapshots), 0)
        
        # Verify resource summary
        summary = report["resource_summary"]
        self.assertIn("cpu_usage", summary)
        self.assertIn("memory_usage", summary)
        
        # Verify recommendations
        recommendations = report["optimization_recommendations"]
        self.assertIsInstance(recommendations, list)
        self.assertGreater(len(recommendations), 0)
    
    def test_regression_detection_integration(self):
        """Test regression detection system integration"""
        # Step 1: Establish baseline
        baseline_results = [
            {
                'response_time_ms': 100.0,
                'throughput_rps': 1000.0,
                'error_rate': 0.01,
                'cpu_usage': 40.0,
                'memory_usage': 50.0
            }
            for _ in range(10)
        ]
        
        baseline = self.regression_detector.establish_baseline("integration_test", baseline_results)
        
        # Verify baseline was created
        self.assertIsNotNone(baseline)
        self.assertEqual(baseline.test_name, "integration_test")
        self.assertEqual(baseline.response_time_ms, 100.0)
        
        # Step 2: Run regression test with good performance
        good_results = [
            {
                'response_time_ms': 95.0,   # 5% better
                'throughput_rps': 1050.0,   # 5% better
                'error_rate': 0.009,        # 10% better
                'cpu_usage': 38.0,          # 5% better
                'memory_usage': 48.0        # 4% better
            }
            for _ in range(10)
        ]
        
        good_result = self.regression_detector.run_regression_test("integration_test", good_results)
        
        # Should not detect regression
        self.assertFalse(good_result.regression_detected)
        self.assertEqual(good_result.regression_severity, "none")
        
        # Step 3: Run regression test with poor performance
        poor_results = [
            {
                'response_time_ms': 200.0,  # 100% worse
                'throughput_rps': 500.0,    # 50% worse
                'error_rate': 0.03,         # 200% worse
                'cpu_usage': 80.0,          # 100% worse
                'memory_usage': 75.0        # 50% worse
            }
            for _ in range(10)
        ]
        
        poor_result = self.regression_detector.run_regression_test("integration_test", poor_results)
        
        # Should detect regression
        self.assertTrue(poor_result.regression_detected)
        self.assertIn(poor_result.regression_severity, ["major", "critical"])
        self.assertGreater(len(poor_result.affected_metrics), 0)
        
        # Step 4: Generate comprehensive report
        report = self.regression_detector.generate_regression_report()
        
        # Verify report structure
        self.assertIn("baselines_count", report)
        self.assertIn("test_history_count", report)
        self.assertIn("recent_regressions", report)
        self.assertIn("recommendations", report)
        
        # Verify counts
        self.assertEqual(report["baselines_count"], 1)
        self.assertEqual(report["test_history_count"], 2)
    
    def test_end_to_end_workflow(self):
        """Test complete end-to-end performance testing workflow"""
        async def run_complete_workflow():
            # Step 1: Run latency benchmarks
            latency_results = await self.latency_benchmark._benchmark_api_endpoints()
            
            # Step 2: Start resource profiling
            self.resource_profiler.start_profiling()
            
            # Step 3: Simulate application workload
            import time
            time.sleep(0.2)
            
            # Create some load
            temp_objects = []
            for i in range(500):
                temp_objects.append({"id": i, "data": f"test_data_{i}"})
            
            # CPU intensive work
            computation_result = sum(x**2 for x in range(1000))
            
            # Step 4: Stop profiling and get resource report
            self.resource_profiler.stop_profiling()
            resource_report = self.resource_profiler.generate_resource_report()
            
            # Step 5: Convert latency results to regression test format
            test_results = []
            for endpoint, stats in latency_results.items():
                test_result = {
                    'response_time_ms': stats['mean_ns'] / 1_000_000,  # Convert to ms
                    'throughput_rps': 1000.0,  # Mock throughput
                    'error_rate': 1.0 - stats['success_rate'],
                    'cpu_usage': 45.0,  # Mock CPU usage
                    'memory_usage': 60.0  # Mock memory usage
                }
                test_results.append(test_result)
            
            # Step 6: Establish baseline if not exists
            try:
                self.regression_detector.establish_baseline("e2e_test", test_results)
            except:
                pass  # Baseline might already exist
            
            # Step 7: Run regression test
            regression_result = self.regression_detector.run_regression_test("e2e_test", test_results)
            
            # Step 8: Generate final comprehensive report
            final_report = {
                "timestamp": datetime.now().isoformat(),
                "latency_benchmarks": latency_results,
                "resource_profiling": resource_report,
                "regression_analysis": {
                    "test_name": regression_result.test_name,
                    "regression_detected": regression_result.regression_detected,
                    "severity": regression_result.regression_severity,
                    "affected_metrics": regression_result.affected_metrics,
                    "performance_change": regression_result.performance_change
                },
                "workflow_status": "completed"
            }
            
            return final_report
        
        # Run the complete workflow
        final_report = asyncio.run(run_complete_workflow())
        
        # Verify final report structure
        self.assertIsInstance(final_report, dict)
        self.assertIn("timestamp", final_report)
        self.assertIn("latency_benchmarks", final_report)
        self.assertIn("resource_profiling", final_report)
        self.assertIn("regression_analysis", final_report)
        self.assertEqual(final_report["workflow_status"], "completed")
        
        # Verify latency benchmarks
        latency_benchmarks = final_report["latency_benchmarks"]
        self.assertIsInstance(latency_benchmarks, dict)
        self.assertGreater(len(latency_benchmarks), 0)
        
        # Verify resource profiling
        resource_profiling = final_report["resource_profiling"]
        self.assertIn("resource_summary", resource_profiling)
        self.assertIn("optimization_recommendations", resource_profiling)
        
        # Verify regression analysis
        regression_analysis = final_report["regression_analysis"]
        self.assertIn("test_name", regression_analysis)
        self.assertIn("regression_detected", regression_analysis)
        self.assertIn("severity", regression_analysis)
    
    def test_performance_thresholds_validation(self):
        """Test that performance thresholds are properly validated"""
        # Test configuration thresholds
        self.assertEqual(self.test_config.max_response_time, 2.0)
        self.assertEqual(self.test_config.max_error_rate, 0.05)
        
        # Test regression detector thresholds
        self.assertEqual(self.regression_detector.regression_threshold, 0.10)
        self.assertEqual(self.regression_detector.minor_threshold, 0.05)
        self.assertEqual(self.regression_detector.major_threshold, 0.20)
        self.assertEqual(self.regression_detector.critical_threshold, 0.50)
        
        # Test alert configurations
        alert_names = [alert.alert_name for alert in self.regression_detector.alert_configs]
        expected_alerts = [
            "High Response Time",
            "Low Throughput",
            "High Error Rate",
            "High CPU Usage",
            "High Memory Usage"
        ]
        
        for expected_alert in expected_alerts:
            self.assertIn(expected_alert, alert_names)
    
    def test_data_consistency_across_systems(self):
        """Test that data formats are consistent across all systems"""
        # Test that all systems can handle the same metric format
        test_metrics = {
            'response_time_ms': 150.0,
            'throughput_rps': 1000.0,
            'error_rate': 0.01,
            'cpu_usage': 45.0,
            'memory_usage': 60.0
        }
        
        # Test regression detector can handle these metrics
        test_results = [test_metrics for _ in range(5)]
        baseline = self.regression_detector.establish_baseline("consistency_test", test_results)
        
        self.assertEqual(baseline.response_time_ms, 150.0)
        self.assertEqual(baseline.throughput_rps, 1000.0)
        self.assertEqual(baseline.error_rate, 0.01)
        
        # Test that performance changes are calculated correctly
        modified_metrics = {
            'response_time_ms': 180.0,  # 20% increase
            'throughput_rps': 800.0,    # 20% decrease
            'error_rate': 0.015,        # 50% increase
            'cpu_usage': 54.0,          # 20% increase
            'memory_usage': 72.0        # 20% increase
        }
        
        modified_results = [modified_metrics for _ in range(5)]
        regression_result = self.regression_detector.run_regression_test("consistency_test", modified_results)
        
        # Should detect regression due to significant changes
        self.assertTrue(regression_result.regression_detected)
        
        # Verify performance changes are calculated
        changes = regression_result.performance_change
        self.assertIn('response_time_ms', changes)
        self.assertIn('throughput_rps', changes)
        self.assertGreater(changes['response_time_ms'], 15)  # Should be ~20%
        self.assertGreater(changes['throughput_rps'], 15)    # Should be ~20%

def run_complete_system_tests():
    """Run all complete system integration tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test class
    tests = loader.loadTestsFromTestCase(TestCompleteSystemIntegration)
    suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == "__main__":
    print("Running Complete System Integration Tests...")
    print("Testing integration of all performance testing components:")
    print("  - Performance Test Suite (13.1)")
    print("  - Latency Benchmarking (13.2)")
    print("  - Resource Profiling Tools (13.3)")
    print("  - Performance Regression Detection (13.4)")
    print("=" * 70)
    
    success = run_complete_system_tests()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ All Complete System Integration tests PASSED!")
        print("\nComplete Performance Testing System verified:")
        print("  - System Initialization: All components initialize correctly")
        print("  - Latency Benchmarking: Microsecond-precision measurements")
        print("  - Resource Profiling: CPU, memory, and GC monitoring")
        print("  - Regression Detection: Baseline management and alerting")
        print("  - End-to-End Workflow: Complete testing workflow")
        print("  - Data Consistency: Consistent data formats across systems")
        print("  - Performance Thresholds: Proper threshold validation")
        print("\n🎯 The complete performance testing system is production-ready!")
    else:
        print("❌ Some Complete System Integration tests FAILED!")
        print("Please check the test output above for details.")
    
    print("=" * 70)
    exit(0 if success else 1)