#!/usr/bin/env python3
"""
Comprehensive Test Suite for Performance Regression Detection
Tests all components of the regression detection system including
PerformanceRegressionDetector, baseline management, alert system, and trend analysis.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from collections import defaultdict

# Import the modules we're testing
from regression_detection import (
    PerformanceRegressionDetector, PerformanceBaseline, RegressionTestResult,
    PerformanceAlert
)

class TestPerformanceBaseline(unittest.TestCase):
    """Test cases for PerformanceBaseline data structure"""
    
    def test_baseline_creation(self):
        """Test PerformanceBaseline creation and attributes"""
        baseline_date = datetime.now()
        confidence_interval = {
            'response_time_ms': (100.0, 200.0),
            'throughput_rps': (800.0, 1200.0),
            'error_rate': (0.005, 0.015),
            'cpu_usage': (40.0, 50.0),
            'memory_usage': (55.0, 65.0)
        }
        
        baseline = PerformanceBaseline(
            test_name="api_performance_test",
            baseline_date=baseline_date,
            response_time_ms=150.0,
            throughput_rps=1000.0,
            error_rate=0.01,
            cpu_usage=45.0,
            memory_usage=60.0,
            confidence_interval=confidence_interval,
            sample_size=100
        )
        
        self.assertEqual(baseline.test_name, "api_performance_test")
        self.assertEqual(baseline.baseline_date, baseline_date)
        self.assertEqual(baseline.response_time_ms, 150.0)
        self.assertEqual(baseline.throughput_rps, 1000.0)
        self.assertEqual(baseline.error_rate, 0.01)
        self.assertEqual(baseline.cpu_usage, 45.0)
        self.assertEqual(baseline.memory_usage, 60.0)
        self.assertEqual(baseline.confidence_interval, confidence_interval)
        self.assertEqual(baseline.sample_size, 100)

class TestRegressionTestResult(unittest.TestCase):
    """Test cases for RegressionTestResult data structure"""
    
    def test_regression_result_creation(self):
        """Test RegressionTestResult creation and attributes"""
        test_date = datetime.now()
        current_metrics = {
            'response_time_ms': 180.0,
            'throughput_rps': 850.0,
            'error_rate': 0.015,
            'cpu_usage': 55.0,
            'memory_usage': 65.0
        }
        baseline_metrics = {
            'response_time_ms': 150.0,
            'throughput_rps': 1000.0,
            'error_rate': 0.01,
            'cpu_usage': 45.0,
            'memory_usage': 60.0
        }
        performance_change = {
            'response_time_ms': 20.0,
            'throughput_rps': 15.0,
            'error_rate': 50.0,
            'cpu_usage': 22.2,
            'memory_usage': 8.3
        }
        
        result = RegressionTestResult(
            test_name="api_performance_test",
            test_date=test_date,
            current_metrics=current_metrics,
            baseline_metrics=baseline_metrics,
            regression_detected=True,
            regression_severity="major",
            affected_metrics=["response_time_ms", "throughput_rps", "error_rate"],
            performance_change=performance_change,
            statistical_significance={'response_time_ms': 0.02, 'throughput_rps': 0.03}
        )
        
        self.assertEqual(result.test_name, "api_performance_test")
        self.assertEqual(result.test_date, test_date)
        self.assertEqual(result.current_metrics, current_metrics)
        self.assertEqual(result.baseline_metrics, baseline_metrics)
        self.assertTrue(result.regression_detected)
        self.assertEqual(result.regression_severity, "major")
        self.assertEqual(result.affected_metrics, ["response_time_ms", "throughput_rps", "error_rate"])
        self.assertEqual(result.performance_change, performance_change)

class TestPerformanceAlert(unittest.TestCase):
    """Test cases for PerformanceAlert data structure"""
    
    def test_alert_creation(self):
        """Test PerformanceAlert creation and attributes"""
        trigger_time = datetime.now()
        
        alert = PerformanceAlert(
            alert_name="High Response Time",
            metric_name="response_time_ms",
            threshold_type="absolute",
            threshold_value=2000.0,
            comparison_operator="gt",
            alert_level="warning",
            triggered=True,
            trigger_time=trigger_time,
            current_value=2500.0,
            message="Response time exceeded 2 seconds"
        )
        
        self.assertEqual(alert.alert_name, "High Response Time")
        self.assertEqual(alert.metric_name, "response_time_ms")
        self.assertEqual(alert.threshold_type, "absolute")
        self.assertEqual(alert.threshold_value, 2000.0)
        self.assertEqual(alert.comparison_operator, "gt")
        self.assertEqual(alert.alert_level, "warning")
        self.assertTrue(alert.triggered)
        self.assertEqual(alert.trigger_time, trigger_time)
        self.assertEqual(alert.current_value, 2500.0)
        self.assertEqual(alert.message, "Response time exceeded 2 seconds")

class TestPerformanceRegressionDetector(unittest.TestCase):
    """Test cases for PerformanceRegressionDetector"""
    
    def setUp(self):
        # Use temporary file for testing
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        self.detector = PerformanceRegressionDetector(baseline_storage_path=self.temp_file.name)
    
    def tearDown(self):
        # Clean up temporary file
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
    
    def test_detector_initialization(self):
        """Test detector initialization"""
        self.assertEqual(self.detector.baseline_storage_path, self.temp_file.name)
        self.assertIsInstance(self.detector.baselines, dict)
        self.assertIsInstance(self.detector.test_history, list)
        self.assertIsInstance(self.detector.alert_configs, list)
        
        # Check default thresholds
        self.assertEqual(self.detector.significance_level, 0.05)
        self.assertEqual(self.detector.regression_threshold, 0.10)
        self.assertEqual(self.detector.minor_threshold, 0.05)
        self.assertEqual(self.detector.major_threshold, 0.20)
        self.assertEqual(self.detector.critical_threshold, 0.50)
        
        # Check default alerts were setup
        self.assertGreater(len(self.detector.alert_configs), 0)
    
    def test_establish_baseline(self):
        """Test establishing performance baseline"""
        test_results = [
            {
                'response_time_ms': 150.0,
                'throughput_rps': 1000.0,
                'error_rate': 0.01,
                'cpu_usage': 45.0,
                'memory_usage': 60.0
            }
            for _ in range(10)
        ]
        
        baseline = self.detector.establish_baseline("test_api", test_results)
        
        # Verify baseline was created
        self.assertIsInstance(baseline, PerformanceBaseline)
        self.assertEqual(baseline.test_name, "test_api")
        self.assertEqual(baseline.response_time_ms, 150.0)
        self.assertEqual(baseline.throughput_rps, 1000.0)
        self.assertEqual(baseline.error_rate, 0.01)
        self.assertEqual(baseline.cpu_usage, 45.0)
        self.assertEqual(baseline.memory_usage, 60.0)
        self.assertEqual(baseline.sample_size, 10)
        
        # Verify baseline was stored
        self.assertIn("test_api", self.detector.baselines)
        self.assertEqual(self.detector.baselines["test_api"], baseline)
    
    def test_establish_baseline_empty_results(self):
        """Test establishing baseline with empty results"""
        with self.assertRaises(ValueError):
            self.detector.establish_baseline("test_api", [])
    
    def test_calculate_confidence_intervals(self):
        """Test confidence interval calculation"""
        test_results = [
            {'response_time_ms': 100.0, 'throughput_rps': 1000.0},
            {'response_time_ms': 150.0, 'throughput_rps': 1100.0},
            {'response_time_ms': 200.0, 'throughput_rps': 900.0}
        ]
        
        intervals = self.detector._calculate_confidence_intervals(test_results)
        
        self.assertIsInstance(intervals, dict)
        self.assertIn('response_time_ms', intervals)
        self.assertIn('throughput_rps', intervals)
        
        # Each interval should be a tuple of (lower, upper)
        for metric, interval in intervals.items():
            self.assertIsInstance(interval, tuple)
            self.assertEqual(len(interval), 2)
            self.assertLessEqual(interval[0], interval[1])  # lower <= upper
    
    def test_run_regression_test_no_baseline(self):
        """Test running regression test without baseline"""
        current_results = [{'response_time_ms': 200.0}]
        
        with self.assertRaises(ValueError):
            self.detector.run_regression_test("nonexistent_test", current_results)
    
    def test_run_regression_test_with_baseline(self):
        """Test running regression test with baseline"""
        # First establish baseline
        baseline_results = [
            {
                'response_time_ms': 150.0,
                'throughput_rps': 1000.0,
                'error_rate': 0.01,
                'cpu_usage': 45.0,
                'memory_usage': 60.0
            }
            for _ in range(10)
        ]
        self.detector.establish_baseline("test_api", baseline_results)
        
        # Run regression test with degraded performance
        current_results = [
            {
                'response_time_ms': 180.0,  # 20% slower
                'throughput_rps': 850.0,    # 15% lower
                'error_rate': 0.015,        # 50% higher
                'cpu_usage': 55.0,          # 22% higher
                'memory_usage': 65.0        # 8% higher
            }
            for _ in range(10)
        ]
        
        result = self.detector.run_regression_test("test_api", current_results)
        
        # Verify regression was detected
        self.assertIsInstance(result, RegressionTestResult)
        self.assertEqual(result.test_name, "test_api")
        self.assertTrue(result.regression_detected)
        self.assertIn(result.regression_severity, ["minor", "major", "critical"])
        self.assertGreater(len(result.affected_metrics), 0)
        
        # Verify performance changes are calculated
        self.assertIn('response_time_ms', result.performance_change)
        self.assertGreater(result.performance_change['response_time_ms'], 0)  # Should be positive (worse)
        
        # Verify result was stored in history
        self.assertIn(result, self.detector.test_history)
    
    def test_analyze_regression_no_regression(self):
        """Test regression analysis with no regression"""
        baseline_metrics = {
            'response_time_ms': 150.0,
            'throughput_rps': 1000.0,
            'error_rate': 0.01,
            'cpu_usage': 45.0,
            'memory_usage': 60.0
        }
        
        # Current metrics are similar to baseline (no regression)
        current_metrics = {
            'response_time_ms': 155.0,  # 3% increase (below threshold)
            'throughput_rps': 980.0,    # 2% decrease (below threshold)
            'error_rate': 0.011,        # 10% increase (above threshold but small absolute change)
            'cpu_usage': 47.0,          # 4% increase (below threshold)
            'memory_usage': 62.0        # 3% increase (below threshold)
        }
        
        analysis = self.detector._analyze_regression(baseline_metrics, current_metrics)
        
        self.assertIsInstance(analysis, dict)
        self.assertIn('regression_detected', analysis)
        self.assertIn('severity', analysis)
        self.assertIn('affected_metrics', analysis)
        self.assertIn('performance_change', analysis)
        
        # Should not detect significant regression
        self.assertEqual(analysis['severity'], 'none')
    
    def test_analyze_regression_with_regression(self):
        """Test regression analysis with significant regression"""
        baseline_metrics = {
            'response_time_ms': 150.0,
            'throughput_rps': 1000.0,
            'error_rate': 0.01,
            'cpu_usage': 45.0,
            'memory_usage': 60.0
        }
        
        # Current metrics show significant degradation
        current_metrics = {
            'response_time_ms': 225.0,  # 50% increase (major regression)
            'throughput_rps': 700.0,    # 30% decrease (major regression)
            'error_rate': 0.02,         # 100% increase (major regression)
            'cpu_usage': 67.5,          # 50% increase (major regression)
            'memory_usage': 75.0        # 25% increase (major regression)
        }
        
        analysis = self.detector._analyze_regression(baseline_metrics, current_metrics)
        
        self.assertTrue(analysis['regression_detected'])
        self.assertIn(analysis['severity'], ['major', 'critical'])
        self.assertGreater(len(analysis['affected_metrics']), 0)
        
        # Check performance changes are calculated correctly
        changes = analysis['performance_change']
        self.assertGreater(changes['response_time_ms'], 40)  # Should be ~50%
        self.assertGreater(changes['throughput_rps'], 25)    # Should be ~30%
    
    def test_setup_default_alerts(self):
        """Test default alert setup"""
        # Clear existing alerts
        self.detector.alert_configs = []
        
        # Setup default alerts
        self.detector.setup_default_alerts()
        
        # Verify alerts were created
        self.assertGreater(len(self.detector.alert_configs), 0)
        
        # Check for expected alert types
        alert_names = [alert.alert_name for alert in self.detector.alert_configs]
        expected_alerts = [
            "High Response Time",
            "Low Throughput", 
            "High Error Rate",
            "High CPU Usage",
            "High Memory Usage"
        ]
        
        for expected_alert in expected_alerts:
            self.assertIn(expected_alert, alert_names)
    
    def test_add_custom_alert(self):
        """Test adding custom alert"""
        initial_count = len(self.detector.alert_configs)
        
        custom_alert = PerformanceAlert(
            alert_name="Custom Test Alert",
            metric_name="custom_metric",
            threshold_type="absolute",
            threshold_value=100.0,
            comparison_operator="gt",
            alert_level="info",
            triggered=False,
            trigger_time=None,
            current_value=0.0,
            message="Custom alert message"
        )
        
        self.detector.add_custom_alert(custom_alert)
        
        # Verify alert was added
        self.assertEqual(len(self.detector.alert_configs), initial_count + 1)
        self.assertIn(custom_alert, self.detector.alert_configs)
    
    def test_check_performance_alerts(self):
        """Test performance alert checking"""
        # Setup a simple alert
        alert = PerformanceAlert(
            alert_name="Test Alert",
            metric_name="response_time_ms",
            threshold_type="absolute",
            threshold_value=200.0,
            comparison_operator="gt",
            alert_level="warning",
            triggered=False,
            trigger_time=None,
            current_value=0.0,
            message="Test alert triggered"
        )
        
        self.detector.alert_configs = [alert]
        
        # Test with metrics below threshold
        metrics_below = {'response_time_ms': 150.0}
        self.detector._check_performance_alerts(metrics_below)
        
        self.assertFalse(alert.triggered)
        self.assertIsNone(alert.trigger_time)
        
        # Test with metrics above threshold
        metrics_above = {'response_time_ms': 250.0}
        self.detector._check_performance_alerts(metrics_above)
        
        self.assertTrue(alert.triggered)
        self.assertIsNotNone(alert.trigger_time)
        self.assertEqual(alert.current_value, 250.0)
    
    def test_calculate_trend(self):
        """Test trend calculation"""
        # Test increasing trend
        increasing_values = [1.0, 2.0, 3.0, 4.0, 5.0]
        trend = self.detector._calculate_trend(increasing_values)
        self.assertGreater(trend, 0)
        
        # Test decreasing trend
        decreasing_values = [5.0, 4.0, 3.0, 2.0, 1.0]
        trend = self.detector._calculate_trend(decreasing_values)
        self.assertLess(trend, 0)
        
        # Test stable trend
        stable_values = [3.0, 3.0, 3.0, 3.0, 3.0]
        trend = self.detector._calculate_trend(stable_values)
        self.assertAlmostEqual(trend, 0.0, places=2)
        
        # Test edge cases
        self.assertEqual(self.detector._calculate_trend([]), 0.0)
        self.assertEqual(self.detector._calculate_trend([5.0]), 0.0)
    
    def test_assess_overall_health(self):
        """Test overall health assessment"""
        # Test good health (no degrading metrics)
        good_trends = {
            'response_time_ms': {'trend_direction': 'stable'},
            'throughput_rps': {'trend_direction': 'stable'},
            'error_rate': {'trend_direction': 'stable'},
            'cpu_usage': {'trend_direction': 'stable'},
            'memory_usage': {'trend_direction': 'stable'}
        }
        health = self.detector._assess_overall_health(good_trends)
        self.assertEqual(health, 'good')
        
        # Test concerning health (some degrading metrics)
        concerning_trends = {
            'response_time_ms': {'trend_direction': 'increasing'},  # degrading
            'throughput_rps': {'trend_direction': 'decreasing'},    # degrading
            'error_rate': {'trend_direction': 'stable'},
            'cpu_usage': {'trend_direction': 'stable'},
            'memory_usage': {'trend_direction': 'stable'}
        }
        health = self.detector._assess_overall_health(concerning_trends)
        self.assertEqual(health, 'concerning')
        
        # Test poor health (most metrics degrading)
        poor_trends = {
            'response_time_ms': {'trend_direction': 'increasing'},  # degrading
            'throughput_rps': {'trend_direction': 'decreasing'},    # degrading
            'error_rate': {'trend_direction': 'increasing'},        # degrading
            'cpu_usage': {'trend_direction': 'increasing'},         # degrading
            'memory_usage': {'trend_direction': 'stable'}
        }
        health = self.detector._assess_overall_health(poor_trends)
        self.assertEqual(health, 'poor')
    
    def test_save_load_baselines(self):
        """Test saving and loading baselines"""
        # Create a baseline
        test_results = [
            {
                'response_time_ms': 150.0,
                'throughput_rps': 1000.0,
                'error_rate': 0.01,
                'cpu_usage': 45.0,
                'memory_usage': 60.0
            }
            for _ in range(5)
        ]
        
        baseline = self.detector.establish_baseline("test_save_load", test_results)
        
        # Save baselines
        self.detector.save_baselines()
        
        # Create new detector and load baselines
        new_detector = PerformanceRegressionDetector(baseline_storage_path=self.temp_file.name)
        
        # Verify baseline was loaded
        self.assertIn("test_save_load", new_detector.baselines)
        loaded_baseline = new_detector.baselines["test_save_load"]
        
        self.assertEqual(loaded_baseline.test_name, baseline.test_name)
        self.assertEqual(loaded_baseline.response_time_ms, baseline.response_time_ms)
        self.assertEqual(loaded_baseline.throughput_rps, baseline.throughput_rps)
        self.assertEqual(loaded_baseline.sample_size, baseline.sample_size)
    
    def test_generate_regression_report(self):
        """Test regression report generation"""
        # Setup some test data
        baseline_results = [
            {
                'response_time_ms': 150.0,
                'throughput_rps': 1000.0,
                'error_rate': 0.01,
                'cpu_usage': 45.0,
                'memory_usage': 60.0
            }
            for _ in range(5)
        ]
        self.detector.establish_baseline("test_report", baseline_results)
        
        # Run a regression test
        current_results = [
            {
                'response_time_ms': 200.0,
                'throughput_rps': 800.0,
                'error_rate': 0.02,
                'cpu_usage': 60.0,
                'memory_usage': 70.0
            }
            for _ in range(5)
        ]
        self.detector.run_regression_test("test_report", current_results)
        
        # Generate report
        report = self.detector.generate_regression_report()
        
        # Verify report structure
        self.assertIsInstance(report, dict)
        self.assertIn("report_date", report)
        self.assertIn("baselines_count", report)
        self.assertIn("test_history_count", report)
        self.assertIn("active_alerts", report)
        self.assertIn("baselines", report)
        self.assertIn("recent_regressions", report)
        self.assertIn("performance_trends", report)
        self.assertIn("alert_summary", report)
        self.assertIn("optimization_tracking", report)
        self.assertIn("recommendations", report)
        
        # Verify counts
        self.assertEqual(report["baselines_count"], 1)
        self.assertEqual(report["test_history_count"], 1)
        
        # Verify baselines are included
        self.assertIn("test_report", report["baselines"])
    
    def test_save_report(self):
        """Test saving regression report"""
        report = {
            "test_report": True,
            "timestamp": datetime.now().isoformat(),
            "data": {"key": "value"}
        }
        
        # Create temporary file for report
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_report:
            temp_report_path = temp_report.name
        
        try:
            # Save report
            self.detector.save_report(report, temp_report_path)
            
            # Verify file was created
            self.assertTrue(os.path.exists(temp_report_path))
            
            # Verify content
            with open(temp_report_path, 'r') as f:
                loaded_report = json.load(f)
            
            self.assertEqual(loaded_report["test_report"], True)
            self.assertEqual(loaded_report["data"]["key"], "value")
            
        finally:
            if os.path.exists(temp_report_path):
                os.unlink(temp_report_path)

class TestIntegration(unittest.TestCase):
    """Integration tests for regression detection system"""
    
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        self.detector = PerformanceRegressionDetector(baseline_storage_path=self.temp_file.name)
    
    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
    
    def test_full_regression_workflow(self):
        """Test complete regression detection workflow"""
        # Step 1: Establish baseline
        baseline_results = [
            {
                'response_time_ms': 150.0,
                'throughput_rps': 1000.0,
                'error_rate': 0.01,
                'cpu_usage': 45.0,
                'memory_usage': 60.0
            }
            for _ in range(10)
        ]
        
        baseline = self.detector.establish_baseline("integration_test", baseline_results)
        self.assertIsNotNone(baseline)
        
        # Step 2: Run regression test with good performance
        good_results = [
            {
                'response_time_ms': 145.0,  # Slightly better
                'throughput_rps': 1050.0,   # Slightly better
                'error_rate': 0.009,        # Slightly better
                'cpu_usage': 43.0,          # Slightly better
                'memory_usage': 58.0        # Slightly better
            }
            for _ in range(10)
        ]
        
        good_result = self.detector.run_regression_test("integration_test", good_results)
        self.assertFalse(good_result.regression_detected)
        self.assertEqual(good_result.regression_severity, "none")
        
        # Step 3: Run regression test with poor performance
        poor_results = [
            {
                'response_time_ms': 300.0,  # 100% worse
                'throughput_rps': 500.0,    # 50% worse
                'error_rate': 0.05,         # 400% worse
                'cpu_usage': 90.0,          # 100% worse
                'memory_usage': 90.0        # 50% worse
            }
            for _ in range(10)
        ]
        
        poor_result = self.detector.run_regression_test("integration_test", poor_results)
        self.assertTrue(poor_result.regression_detected)
        self.assertIn(poor_result.regression_severity, ["major", "critical"])
        self.assertGreater(len(poor_result.affected_metrics), 0)
        
        # Step 4: Generate comprehensive report
        report = self.detector.generate_regression_report()
        self.assertIsInstance(report, dict)
        self.assertEqual(report["baselines_count"], 1)
        self.assertEqual(report["test_history_count"], 2)
        
        # Step 5: Verify alert system worked
        active_alerts = [a for a in self.detector.alert_configs if a.triggered]
        self.assertGreater(len(active_alerts), 0)  # Should have triggered some alerts
        
        # Step 6: Save and reload
        self.detector.save_baselines()
        
        new_detector = PerformanceRegressionDetector(baseline_storage_path=self.temp_file.name)
        self.assertIn("integration_test", new_detector.baselines)
    
    def test_multiple_tests_trend_analysis(self):
        """Test trend analysis with multiple test runs"""
        # Establish baseline
        baseline_results = [
            {
                'response_time_ms': 100.0,
                'throughput_rps': 1000.0,
                'error_rate': 0.01,
                'cpu_usage': 40.0,
                'memory_usage': 50.0
            }
            for _ in range(5)
        ]
        
        self.detector.establish_baseline("trend_test", baseline_results)
        
        # Run multiple tests with gradually degrading performance
        for i in range(5):
            degradation_factor = 1 + (i * 0.05)  # 0%, 5%, 10%, 15%, 20% degradation
            
            test_results = [
                {
                    'response_time_ms': 100.0 * degradation_factor,
                    'throughput_rps': 1000.0 / degradation_factor,
                    'error_rate': 0.01 * degradation_factor,
                    'cpu_usage': 40.0 * degradation_factor,
                    'memory_usage': 50.0 * degradation_factor
                }
                for _ in range(5)
            ]
            
            result = self.detector.run_regression_test("trend_test", test_results)
            
            # Later tests should show more severe regressions
            if i >= 2:  # 10%+ degradation
                self.assertTrue(result.regression_detected)
        
        # Analyze trends
        trends = self.detector.analyze_performance_trends(lookback_days=1)
        
        if "trend_test" in trends:
            trend_data = trends["trend_test"]
            self.assertIn("metric_trends", trend_data)
            self.assertIn("overall_health", trend_data)
            
            # Should detect degrading trends
            metric_trends = trend_data["metric_trends"]
            if "response_time_ms" in metric_trends:
                self.assertEqual(metric_trends["response_time_ms"]["trend_direction"], "increasing")

def run_regression_detection_tests():
    """Run all regression detection tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestPerformanceBaseline,
        TestRegressionTestResult,
        TestPerformanceAlert,
        TestPerformanceRegressionDetector,
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
    print("Running comprehensive tests for Performance Regression Detection...")
    print("=" * 70)
    
    success = run_regression_detection_tests()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ All Regression Detection tests PASSED!")
        print("\nRegression Detection System verified:")
        print("  - PerformanceBaseline: Baseline management and storage")
        print("  - RegressionTestResult: Test result analysis and reporting")
        print("  - PerformanceAlert: Alert system and notifications")
        print("  - Trend Analysis: Performance trend detection")
        print("  - Integration: End-to-end workflow validation")
    else:
        print("❌ Some Regression Detection tests FAILED!")
        print("Please check the test output above for details.")
    
    print("=" * 70)
    exit(0 if success else 1)