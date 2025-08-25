"""Tests for the Performance Optimization System"""

import unittest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
import numpy as np
from monitoring.performance_optimizer import (
    PerformanceOptimizer,
    PerformanceMetrics,
    OptimizationRecommendation
)

class TestPerformanceOptimizer(unittest.TestCase):
    def setUp(self):
        self.optimizer = PerformanceOptimizer()
        self.test_dependency = "test-dep"
        self.test_tier = "critical"
        
    def _generate_test_metrics(self, value_modifier=1.0):
        """Generate test metrics with optional modifier"""
        return {
            "cpu_usage": 50.0 * value_modifier,
            "memory_usage": 1024.0 * value_modifier,
            "disk_io": {
                "read": 100.0 * value_modifier,
                "write": 50.0 * value_modifier
            },
            "scan_duration": 60.0 * value_modifier
        }
        
    def test_update_metrics(self):
        """Test metrics update functionality"""
        metrics = self._generate_test_metrics()
        
        # Update metrics
        self.optimizer.update_metrics(self.test_dependency, self.test_tier, metrics)
        
        # Verify historical data was updated
        self.assertIn(self.test_dependency, self.optimizer.historical_data)
        self.assertEqual(len(self.optimizer.historical_data[self.test_dependency]), 1)
        
    def test_baseline_calculation(self):
        """Test baseline calculation with sufficient data"""
        # Generate 24 hours of test data
        for i in range(24):
            metrics = self._generate_test_metrics(value_modifier=1.0 + (i * 0.01))
            self.optimizer.update_metrics(self.test_dependency, self.test_tier, metrics)
            
        # Verify baseline was calculated
        self.assertIn(self.test_dependency, self.optimizer.baselines)
        baseline = self.optimizer.baselines[self.test_dependency]
        
        # Check baseline values are reasonable
        self.assertTrue(40 <= baseline.cpu_usage_mean <= 60)
        self.assertTrue(800 <= baseline.memory_usage_mean <= 1200)
        
    def test_optimization_recommendations(self):
        """Test optimization recommendations generation"""
        # Set up baseline
        for i in range(24):
            metrics = self._generate_test_metrics()
            self.optimizer.update_metrics(self.test_dependency, self.test_tier, metrics)
            
        # Test with metrics significantly above baseline
        high_metrics = self._generate_test_metrics(value_modifier=1.5)
        recommendations = self.optimizer.get_optimization_recommendations(
            self.test_dependency,
            high_metrics
        )
        
        # Verify recommendations
        self.assertTrue(len(recommendations) > 0)
        self.assertTrue(any(r.priority == "high" for r in recommendations))
        
    def test_performance_report(self):
        """Test performance report generation"""
        # Set up test data
        for i in range(24):
            metrics = self._generate_test_metrics(value_modifier=1.0 + (i * 0.01))
            self.optimizer.update_metrics(self.test_dependency, self.test_tier, metrics)
            
        report = self.optimizer.get_performance_report(self.test_dependency)
        
        # Verify report structure
        self.assertIsNotNone(report)
        self.assertIn("baseline_metrics", report)
        self.assertIn("current_metrics", report)
        self.assertIn("trends", report)
        
    def test_trend_calculation(self):
        """Test trend calculation functionality"""
        # Test increasing trend
        values = [i * 1.1 for i in range(10)]
        trend = self.optimizer._get_trend(values)
        self.assertEqual(trend, "increasing")
        
        # Test decreasing trend
        values = [(10 - i) * 1.1 for i in range(10)]
        trend = self.optimizer._get_trend(values)
        self.assertEqual(trend, "decreasing")
        
        # Test stable trend
        values = [50.0 + (np.random.random() * 0.1) for _ in range(10)]
        trend = self.optimizer._get_trend(values)
        self.assertEqual(trend, "stable")
        
    def test_window_size_cleanup(self):
        """Test that old data is cleaned up properly"""
        # Add data spanning more than window size
        now = datetime.utcnow()
        old_metrics = self._generate_test_metrics()
        
        with patch('datetime.datetime') as mock_datetime:
            # Add old data (outside window)
            mock_datetime.utcnow.return_value = now - timedelta(days=8)
            self.optimizer.update_metrics(self.test_dependency, self.test_tier, old_metrics)
            
            # Add recent data
            mock_datetime.utcnow.return_value = now
            self.optimizer.update_metrics(self.test_dependency, self.test_tier, old_metrics)
            
        # Verify only recent data is kept
        self.assertEqual(len(self.optimizer.historical_data[self.test_dependency]), 1)
        
if __name__ == '__main__':
    unittest.main()
