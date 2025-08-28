"""Integration tests for the dependency management performance optimization system"""

import unittest
import tempfile
import json
import os
from unittest.mock import patch, Mock
from dependency_management.scripts.dependency_manager import DependencyManager, DependencyTier

class TestDependencyManagerPerformance(unittest.TestCase):
    def setUp(self):
        # Create a temporary config file
        self.config = {
            "tiers": {
                "tier1": {
                    "dependencies": [
                        {
                            "name": "test-dep",
                            "repository": "github.com/test/test-dep",
                            "version": "1.0.0"
                        }
                    ]
                },
                "tier2": {"dependencies": []},
                "tier3": {"dependencies": []},
                "tier4": {"dependencies": []}
            }
        }
        
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "test_config.json")
        
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f)
            
        self.manager = DependencyManager(self.config_path)
        
    def tearDown(self):
        # Clean up temp files
        os.unlink(self.config_path)
        os.rmdir(self.temp_dir)
        
    @patch('psutil.Process')
    def test_collect_performance_metrics(self, mock_process):
        """Test performance metrics collection"""
        # Mock process metrics
        mock_process.return_value.cpu_percent.return_value = 50.0
        mock_process.return_value.memory_info.return_value = Mock(rss=1024*1024*100)  # 100MB
        mock_process.return_value.io_counters.return_value = Mock(
            read_bytes=1024*1024*50,  # 50MB
            write_bytes=1024*1024*25   # 25MB
        )
        
        metrics = self.manager.collect_performance_metrics("test-dep")
        
        # Verify metrics structure
        self.assertIn("cpu_usage", metrics)
        self.assertIn("memory_usage", metrics)
        self.assertIn("disk_io", metrics)
        self.assertIn("read", metrics["disk_io"])
        self.assertIn("write", metrics["disk_io"])
        
        # Verify values
        self.assertEqual(metrics["cpu_usage"], 50.0)
        self.assertEqual(metrics["memory_usage"], 100.0)  # 100MB
        self.assertEqual(metrics["disk_io"]["read"], 50.0)  # 50MB
        self.assertEqual(metrics["disk_io"]["write"], 25.0)  # 25MB
        
    def test_get_performance_recommendations(self):
        """Test performance recommendations generation"""
        # First collect some metrics to establish baseline
        with patch('psutil.Process') as mock_process:
            mock_process.return_value.cpu_percent.return_value = 50.0
            mock_process.return_value.memory_info.return_value = Mock(rss=1024*1024*100)
            mock_process.return_value.io_counters.return_value = Mock(
                read_bytes=1024*1024*50,
                write_bytes=1024*1024*25
            )
            
            # Collect metrics for 24 data points
            for _ in range(24):
                self.manager.collect_performance_metrics("test-dep")
                
            # Now simulate high resource usage
            mock_process.return_value.cpu_percent.return_value = 90.0
            mock_process.return_value.memory_info.return_value = Mock(rss=1024*1024*200)
            
            recommendations = self.manager.get_performance_recommendations("test-dep")
            
            # Verify recommendations structure
            self.assertTrue(len(recommendations) > 0)
            for rec in recommendations:
                self.assertIn("dependency", rec)
                self.assertIn("priority", rec)
                self.assertIn("category", rec)
                self.assertIn("current_value", rec)
                self.assertIn("target_value", rec)
                self.assertIn("recommendation", rec)
                
    def test_get_performance_report(self):
        """Test performance report generation"""
        # Collect sample metrics
        with patch('psutil.Process') as mock_process:
            mock_process.return_value.cpu_percent.return_value = 50.0
            mock_process.return_value.memory_info.return_value = Mock(rss=1024*1024*100)
            mock_process.return_value.io_counters.return_value = Mock(
                read_bytes=1024*1024*50,
                write_bytes=1024*1024*25
            )
            
            # Collect metrics for 24 data points
            for _ in range(24):
                self.manager.collect_performance_metrics("test-dep")
                
            report = self.manager.get_performance_report("test-dep")
            
            # Verify report structure
            self.assertIsNotNone(report)
            self.assertIn("baseline_metrics", report)
            self.assertIn("current_metrics", report)
            self.assertIn("trends", report)
            
            # Verify baseline metrics
            self.assertIn("cpu", report["baseline_metrics"])
            self.assertIn("memory", report["baseline_metrics"])
            self.assertIn("disk_io", report["baseline_metrics"])
            
            # Verify current metrics
            self.assertIn("cpu_usage", report["current_metrics"])
            self.assertIn("memory_usage", report["current_metrics"])
            self.assertIn("disk_io", report["current_metrics"])
            
    def test_get_dependency_tier(self):
        """Test dependency tier lookup"""
        # Test existing dependency
        tier = self.manager._get_dependency_tier("test-dep")
        self.assertEqual(tier, DependencyTier.TIER1)
        
        # Test non-existent dependency
        tier = self.manager._get_dependency_tier("non-existent")
        self.assertIsNone(tier)
        
if __name__ == '__main__':
    unittest.main()
