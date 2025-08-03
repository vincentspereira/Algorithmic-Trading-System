#!/usr/bin/env python3
"""
Basic Functionality Test for Monitoring Infrastructure
Tests core monitoring components without Docker dependencies.
"""

import sys
import os
import unittest
import time
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from monitoring_infrastructure import (
        MetricsCollector, SystemMonitor, HealthChecker,
        MetricType, AlertSeverity, ComponentStatus
    )
    print("✅ Successfully imported monitoring infrastructure components")
except ImportError as e:
    print(f"❌ Failed to import monitoring infrastructure: {e}")
    sys.exit(1)

class TestBasicMonitoring(unittest.TestCase):
    """Test basic monitoring functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.metrics_collector = MetricsCollector()
        self.system_monitor = SystemMonitor(self.metrics_collector)
        self.health_checker = HealthChecker()
    
    def test_metrics_collector_basic(self):
        """Test basic metrics collector functionality"""
        print("Testing metrics collector...")
        
        # Test counter increment
        self.metrics_collector.increment_counter('http_requests_total', {'method': 'GET', 'endpoint': '/test', 'status': '200'})
        
        # Test gauge setting
        self.metrics_collector.set_gauge('system_cpu_percent', 45.5)
        
        # Test histogram observation
        self.metrics_collector.observe_histogram('http_request_duration_seconds', 0.125, {'method': 'GET', 'endpoint': '/test'})
        
        # Get metrics text
        metrics_text = self.metrics_collector.get_metrics_text()
        self.assertIsInstance(metrics_text, str)
        self.assertIn('trading_system_', metrics_text)
        
        print("✅ Metrics collector basic functionality works")
    
    def test_system_monitor_basic(self):
        """Test basic system monitor functionality"""
        print("Testing system monitor...")
        
        # Collect system metrics
        metrics = self.system_monitor.collect_system_metrics()
        
        # Verify basic fields
        self.assertIsInstance(metrics.timestamp, datetime)
        self.assertIsInstance(metrics.cpu_percent, float)
        self.assertIsInstance(metrics.memory_percent, float)
        self.assertGreaterEqual(metrics.cpu_percent, 0)
        self.assertLessEqual(metrics.cpu_percent, 100)
        self.assertGreaterEqual(metrics.memory_percent, 0)
        self.assertLessEqual(metrics.memory_percent, 100)
        
        print(f"✅ System monitor works - CPU: {metrics.cpu_percent}%, Memory: {metrics.memory_percent}%")
    
    def test_health_checker_basic(self):
        """Test basic health checker functionality"""
        print("Testing health checker...")
        
        import asyncio
        
        # Run health checks
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            health_results = loop.run_until_complete(self.health_checker.run_health_checks())
            
            # Verify we have health check results
            self.assertIsInstance(health_results, dict)
            self.assertGreater(len(health_results), 0)
            
            # Check each health check result
            for check_name, health_check in health_results.items():
                self.assertIsInstance(health_check.status, ComponentStatus)
                self.assertIsInstance(health_check.message, str)
                self.assertIsInstance(health_check.response_time_ms, float)
                self.assertGreaterEqual(health_check.response_time_ms, 0)
                
                print(f"  - {check_name}: {health_check.status.value} ({health_check.response_time_ms:.1f}ms)")
            
            print("✅ Health checker basic functionality works")
            
        finally:
            loop.close()

def run_basic_tests():
    """Run basic functionality tests"""
    print("Running Basic Monitoring Infrastructure Tests")
    print("=" * 50)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    test_suite.addTest(TestBasicMonitoring('test_metrics_collector_basic'))
    test_suite.addTest(TestBasicMonitoring('test_system_monitor_basic'))
    test_suite.addTest(TestBasicMonitoring('test_health_checker_basic'))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
    result = runner.run(test_suite)
    
    return result.wasSuccessful()

if __name__ == '__main__':
    print("Testing Monitoring Infrastructure Basic Functionality...")
    print("=" * 60)
    
    success = run_basic_tests()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ All basic monitoring tests passed!")
        print("The monitoring infrastructure core functionality is working.")
        print("\nNext steps:")
        print("1. Start Docker Desktop to test full containerized setup")
        print("2. Run: docker-compose up -d")
        print("3. Access monitoring dashboard at http://localhost:8090")
        print("4. Access Grafana at http://localhost:3000 (admin/admin123)")
        print("5. Access Prometheus at http://localhost:9090")
    else:
        print("\n" + "=" * 60)
        print("❌ Some basic monitoring tests failed.")
        print("Please review the errors above and fix any issues.")
    
    exit(0 if success else 1)