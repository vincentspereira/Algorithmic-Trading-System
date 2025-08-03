#!/usr/bin/env python3
"""
Comprehensive Test Suite for Monitoring Infrastructure
Tests all components of the monitoring system including metrics collection,
health checks, alerting, and system monitoring.
"""

import asyncio
import json
import time
import unittest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import tempfile
import os
import sys
from pathlib import Path

# Add the parent directory to the path to import monitoring modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from monitoring.monitoring_infrastructure import (
    MonitoringInfrastructure,
    MetricsCollector,
    SystemMonitor,
    HealthChecker,
    AlertManager,
    MetricDefinition,
    MetricType,
    AlertSeverity,
    ComponentStatus,
    Alert,
    HealthCheck,
    SystemMetrics,
    initialize_monitoring,
    shutdown_monitoring
)

from monitoring.monitoring_server import MonitoringServer

import structlog

# Configure test logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

class TestMetricsCollector(unittest.TestCase):
    """Test the MetricsCollector component"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.collector = MetricsCollector()
    
    def test_initialization(self):
        """Test metrics collector initialization"""
        self.assertIsNotNone(self.collector.registry)
        self.assertIsInstance(self.collector.metrics, dict)
        self.assertIsInstance(self.collector.metric_definitions, dict)
        
        # Check that core metrics are initialized
        core_metrics = [
            "system_cpu_percent",
            "system_memory_percent", 
            "system_disk_percent",
            "http_requests_total",
            "http_request_duration_seconds",
            "trading_orders_total",
            "security_events_total"
        ]
        
        for metric_name in core_metrics:
            self.assertIn(metric_name, self.collector.metrics)
            self.assertIn(metric_name, self.collector.metric_definitions)
    
    def test_register_metric(self):
        """Test metric registration"""
        metric_def = MetricDefinition(
            name="test_counter",
            metric_type=MetricType.COUNTER,
            description="Test counter metric",
            labels=["label1", "label2"]
        )
        
        self.collector.register_metric(metric_def)
        
        self.assertIn("test_counter", self.collector.metrics)
        self.assertIn("test_counter", self.collector.metric_definitions)
        self.assertEqual(self.collector.metric_definitions["test_counter"], metric_def)
    
    def test_increment_counter(self):
        """Test counter increment"""
        # Test without labels
        self.collector.increment_counter("http_requests_total")
        
        # Test with labels
        labels = {"method": "GET", "endpoint": "/api/test", "status": "200"}
        self.collector.increment_counter("http_requests_total", labels, 5.0)
        
        # Test non-existent metric (should not raise exception)
        self.collector.increment_counter("non_existent_metric")
    
    def test_set_gauge(self):
        """Test gauge setting"""
        # Test without labels
        self.collector.set_gauge("system_cpu_percent", 75.5)
        
        # Test with labels (system metrics don't have labels, but test the functionality)
        self.collector.set_gauge("system_memory_percent", 60.0)
        
        # Test non-existent metric
        self.collector.set_gauge("non_existent_gauge", 100.0)
    
    def test_observe_histogram(self):
        """Test histogram observation"""
        labels = {"method": "POST", "endpoint": "/api/orders"}
        self.collector.observe_histogram("http_request_duration_seconds", 0.125, labels)
        
        # Test non-existent metric
        self.collector.observe_histogram("non_existent_histogram", 1.0)
    
    def test_get_metrics_text(self):
        """Test Prometheus metrics text generation"""
        # Add some test data
        self.collector.increment_counter("http_requests_total", 
                                       {"method": "GET", "endpoint": "/test", "status": "200"})
        self.collector.set_gauge("system_cpu_percent", 45.0)
        
        metrics_text = self.collector.get_metrics_text()
        
        self.assertIsInstance(metrics_text, str)
        self.assertIn("trading_system_http_requests_total", metrics_text)
        self.assertIn("trading_system_system_cpu_percent", metrics_text)

class TestSystemMonitor(unittest.TestCase):
    """Test the SystemMonitor component"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.collector = MetricsCollector()
        self.monitor = SystemMonitor(self.collector)
    
    def test_initialization(self):
        """Test system monitor initialization"""
        self.assertEqual(self.monitor.metrics_collector, self.collector)
        self.assertFalse(self.monitor.monitoring)
        self.assertIsNone(self.monitor.monitor_thread)
        self.assertEqual(self.monitor.update_interval, 10)
    
    def test_collect_system_metrics(self):
        """Test system metrics collection"""
        metrics = self.monitor.collect_system_metrics()
        
        self.assertIsInstance(metrics, SystemMetrics)
        self.assertIsInstance(metrics.timestamp, datetime)
        self.assertGreaterEqual(metrics.cpu_percent, 0)
        self.assertLessEqual(metrics.cpu_percent, 100)
        self.assertGreaterEqual(metrics.memory_percent, 0)
        self.assertLessEqual(metrics.memory_percent, 100)
        self.assertGreaterEqual(metrics.disk_percent, 0)
        self.assertLessEqual(metrics.disk_percent, 100)
        self.assertIsInstance(metrics.load_average, list)
        self.assertEqual(len(metrics.load_average), 3)
        self.assertGreater(metrics.process_count, 0)
        self.assertGreaterEqual(metrics.thread_count, 0)
    
    def test_start_stop_monitoring(self):
        """Test starting and stopping monitoring"""
        # Start monitoring
        self.monitor.start_monitoring()
        self.assertTrue(self.monitor.monitoring)
        self.assertIsNotNone(self.monitor.monitor_thread)
        
        # Wait a bit for the thread to start
        time.sleep(0.1)
        self.assertTrue(self.monitor.monitor_thread.is_alive())
        
        # Stop monitoring
        self.monitor.stop_monitoring()
        self.assertFalse(self.monitor.monitoring)
        
        # Wait for thread to finish
        time.sleep(0.1)
        if self.monitor.monitor_thread:
            self.assertFalse(self.monitor.monitor_thread.is_alive())

class TestHealthChecker(unittest.TestCase):
    """Test the HealthChecker component"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.health_checker = HealthChecker()
    
    def test_initialization(self):
        """Test health checker initialization"""
        self.assertIsInstance(self.health_checker.health_checks, dict)
        self.assertIsInstance(self.health_checker.health_status, dict)
        
        # Check default health checks are registered
        default_checks = ["system_resources", "disk_space", "memory_usage"]
        for check_name in default_checks:
            self.assertIn(check_name, self.health_checker.health_checks)
    
    def test_register_health_check(self):
        """Test health check registration"""
        def test_check():
            return {
                'status': ComponentStatus.HEALTHY,
                'message': 'Test check passed'
            }
        
        self.health_checker.register_health_check("test_check", test_check)
        self.assertIn("test_check", self.health_checker.health_checks)
    
    async def test_run_health_checks(self):
        """Test running health checks"""
        results = await self.health_checker.run_health_checks()
        
        self.assertIsInstance(results, dict)
        self.assertGreater(len(results), 0)
        
        for name, check in results.items():
            self.assertIsInstance(check, HealthCheck)
            self.assertIn(check.status, [ComponentStatus.HEALTHY, ComponentStatus.DEGRADED, ComponentStatus.UNHEALTHY])
            self.assertIsInstance(check.message, str)
            self.assertIsInstance(check.response_time_ms, float)
            self.assertGreaterEqual(check.response_time_ms, 0)
    
    async def test_custom_health_check(self):
        """Test custom health check"""
        async def async_test_check():
            return {
                'status': ComponentStatus.HEALTHY,
                'message': 'Async test check passed',
                'metadata': {'test': True}
            }
        
        self.health_checker.register_health_check("async_test", async_test_check)
        results = await self.health_checker.run_health_checks()
        
        self.assertIn("async_test", results)
        check = results["async_test"]
        self.assertEqual(check.status, ComponentStatus.HEALTHY)
        self.assertEqual(check.message, 'Async test check passed')
        self.assertEqual(check.metadata['test'], True)

class TestAlertManager(unittest.TestCase):
    """Test the AlertManager component"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.collector = MetricsCollector()
        self.alert_manager = AlertManager(self.collector)
    
    def test_initialization(self):
        """Test alert manager initialization"""
        self.assertEqual(self.alert_manager.metrics_collector, self.collector)
        self.assertIsInstance(self.alert_manager.alerts, dict)
        self.assertIsInstance(self.alert_manager.alert_rules, list)
        self.assertIsInstance(self.alert_manager.alert_handlers, dict)
        self.assertIsInstance(self.alert_manager.notification_channels, dict)
        
        # Check default alert rules are loaded
        self.assertGreater(len(self.alert_manager.alert_rules), 0)
    
    def test_register_handlers(self):
        """Test handler registration"""
        def test_handler(alert):
            pass
        
        async def async_handler(alert):
            pass
        
        self.alert_manager.register_alert_handler("test_alert", test_handler)
        self.alert_manager.register_notification_channel("test_channel", async_handler)
        
        self.assertIn("test_alert", self.alert_manager.alert_handlers)
        self.assertIn("test_channel", self.alert_manager.notification_channels)
    
    async def test_create_alert(self):
        """Test alert creation"""
        alert = await self.alert_manager.create_alert(
            name="test_alert",
            severity=AlertSeverity.WARNING,
            message="Test alert message",
            component="test_component",
            labels={"test": "value"},
            metadata={"additional": "info"}
        )
        
        self.assertIsInstance(alert, Alert)
        self.assertEqual(alert.name, "test_alert")
        self.assertEqual(alert.severity, AlertSeverity.WARNING)
        self.assertEqual(alert.message, "Test alert message")
        self.assertEqual(alert.component, "test_component")
        self.assertEqual(alert.labels["test"], "value")
        self.assertEqual(alert.metadata["additional"], "info")
        self.assertFalse(alert.resolved)
        self.assertIsNone(alert.resolved_at)
        
        # Check alert is stored
        self.assertIn(alert.alert_id, self.alert_manager.alerts)
    
    async def test_resolve_alert(self):
        """Test alert resolution"""
        # Create an alert first
        alert = await self.alert_manager.create_alert(
            name="test_resolve",
            severity=AlertSeverity.INFO,
            message="Test resolve message",
            component="test"
        )
        
        # Resolve the alert
        success = await self.alert_manager.resolve_alert(alert.alert_id)
        self.assertTrue(success)
        
        # Check alert is resolved
        resolved_alert = self.alert_manager.alerts[alert.alert_id]
        self.assertTrue(resolved_alert.resolved)
        self.assertIsNotNone(resolved_alert.resolved_at)
        
        # Test resolving non-existent alert
        success = await self.alert_manager.resolve_alert("non_existent_id")
        self.assertFalse(success)
    
    def test_get_active_alerts(self):
        """Test getting active alerts"""
        # Initially should be empty
        active_alerts = self.alert_manager.get_active_alerts()
        initial_count = len(active_alerts)
        
        # Create test alerts
        asyncio.run(self._create_test_alerts())
        
        active_alerts = self.alert_manager.get_active_alerts()
        self.assertGreater(len(active_alerts), initial_count)
        
        # All returned alerts should be unresolved
        for alert in active_alerts:
            self.assertFalse(alert.resolved)
    
    async def _create_test_alerts(self):
        """Helper method to create test alerts"""
        await self.alert_manager.create_alert(
            name="active_alert_1",
            severity=AlertSeverity.WARNING,
            message="Active alert 1",
            component="test"
        )
        
        alert2 = await self.alert_manager.create_alert(
            name="resolved_alert",
            severity=AlertSeverity.INFO,
            message="Resolved alert",
            component="test"
        )
        
        # Resolve one alert
        await self.alert_manager.resolve_alert(alert2.alert_id)
    
    def test_get_alert_summary(self):
        """Test alert summary generation"""
        summary = self.alert_manager.get_alert_summary()
        
        self.assertIsInstance(summary, dict)
        for severity in AlertSeverity:
            self.assertIn(severity.value, summary)
            self.assertIsInstance(summary[severity.value], int)
            self.assertGreaterEqual(summary[severity.value], 0)

class TestMonitoringInfrastructure(unittest.TestCase):
    """Test the main MonitoringInfrastructure orchestrator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.infrastructure = MonitoringInfrastructure()
    
    def test_initialization(self):
        """Test monitoring infrastructure initialization"""
        self.assertIsNotNone(self.infrastructure.metrics_collector)
        self.assertIsNotNone(self.infrastructure.system_monitor)
        self.assertIsNotNone(self.infrastructure.health_checker)
        self.assertIsNotNone(self.infrastructure.alert_manager)
        self.assertFalse(self.infrastructure.running)
        self.assertEqual(len(self.infrastructure.monitoring_tasks), 0)
    
    async def test_start_stop(self):
        """Test starting and stopping infrastructure"""
        # Start infrastructure
        await self.infrastructure.start()
        self.assertTrue(self.infrastructure.running)
        self.assertTrue(self.infrastructure.system_monitor.monitoring)
        self.assertGreater(len(self.infrastructure.monitoring_tasks), 0)
        
        # Wait a bit for tasks to start
        await asyncio.sleep(0.1)
        
        # Stop infrastructure
        await self.infrastructure.stop()
        self.assertFalse(self.infrastructure.running)
        self.assertFalse(self.infrastructure.system_monitor.monitoring)
    
    def test_get_system_status(self):
        """Test system status retrieval"""
        status = self.infrastructure.get_system_status()
        
        self.assertIsInstance(status, dict)
        self.assertIn('overall_status', status)
        self.assertIn('timestamp', status)
        self.assertIn('health_checks', status)
        self.assertIn('alerts', status)
        self.assertIn('metrics', status)
        
        # Check alert summary structure
        alerts = status['alerts']
        self.assertIn('active_count', alerts)
        self.assertIn('summary', alerts)
        self.assertIn('recent_alerts', alerts)
    
    def test_get_metrics_endpoint(self):
        """Test metrics endpoint"""
        metrics_text = self.infrastructure.get_metrics_endpoint()
        self.assertIsInstance(metrics_text, str)
        self.assertIn("trading_system_", metrics_text)

class TestMonitoringServer(unittest.TestCase):
    """Test the MonitoringServer HTTP interface"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.server = MonitoringServer(host="127.0.0.1", port=8091)
    
    def test_initialization(self):
        """Test server initialization"""
        self.assertEqual(self.server.host, "127.0.0.1")
        self.assertEqual(self.server.port, 8091)
        self.assertIsNotNone(self.server.app)
        self.assertIsNone(self.server.monitoring_infrastructure)
        self.assertEqual(len(self.server.websocket_connections), 0)
    
    def test_routes_setup(self):
        """Test that routes are properly set up"""
        routes = [str(route.resource) for route in self.server.app.router.routes()]
        
        expected_routes = [
            '/health',
            '/status', 
            '/metrics',
            '/api/v1/alerts',
            '/api/v1/health-checks',
            '/api/v1/system-metrics',
            '/',
            '/dashboard',
            '/dashboard/alerts',
            '/dashboard/metrics',
            '/ws'
        ]
        
        for expected_route in expected_routes:
            # Check if any route matches (some routes have parameters)
            route_found = any(expected_route in route for route in routes)
            self.assertTrue(route_found, f"Route {expected_route} not found in {routes}")

class TestIntegration(unittest.TestCase):
    """Integration tests for the complete monitoring system"""
    
    async def test_full_monitoring_lifecycle(self):
        """Test complete monitoring lifecycle"""
        # Initialize monitoring
        infrastructure = await initialize_monitoring()
        
        try:
            # Verify infrastructure is running
            self.assertTrue(infrastructure.running)
            
            # Wait for monitoring to collect some data
            await asyncio.sleep(2)
            
            # Test metrics collection
            metrics_text = infrastructure.get_metrics_endpoint()
            self.assertIn("trading_system_", metrics_text)
            
            # Test health checks
            health_results = await infrastructure.health_checker.run_health_checks()
            self.assertGreater(len(health_results), 0)
            
            # Test alert creation
            alert = await infrastructure.alert_manager.create_alert(
                name="integration_test_alert",
                severity=AlertSeverity.INFO,
                message="Integration test alert",
                component="test"
            )
            self.assertIsNotNone(alert)
            
            # Test system status
            status = infrastructure.get_system_status()
            self.assertIn('overall_status', status)
            
            # Test alert resolution
            success = await infrastructure.alert_manager.resolve_alert(alert.alert_id)
            self.assertTrue(success)
            
        finally:
            # Cleanup
            await shutdown_monitoring()
    
    async def test_monitoring_server_integration(self):
        """Test monitoring server integration"""
        server = MonitoringServer(host="127.0.0.1", port=8092)
        
        try:
            # Start server (this also initializes monitoring infrastructure)
            await server.start()
            
            # Verify monitoring infrastructure is initialized
            self.assertIsNotNone(server.monitoring_infrastructure)
            self.assertTrue(server.monitoring_infrastructure.running)
            
            # Wait for monitoring to start
            await asyncio.sleep(1)
            
            # Test that we can get system status
            status = server.monitoring_infrastructure.get_system_status()
            self.assertIsInstance(status, dict)
            
        finally:
            # Cleanup
            await server.stop()

class TestDockerIntegration(unittest.TestCase):
    """Test Docker-based monitoring setup"""
    
    def test_docker_compose_file_exists(self):
        """Test that Docker Compose file exists and is valid"""
        compose_file = Path(__file__).parent / "docker-compose.yml"
        self.assertTrue(compose_file.exists(), "Docker Compose file not found")
        
        # Basic validation that it's a valid YAML file
        import yaml
        with open(compose_file, 'r') as f:
            compose_config = yaml.safe_load(f)
        
        self.assertIn('services', compose_config)
        self.assertIn('monitoring-infrastructure', compose_config['services'])
        self.assertIn('prometheus', compose_config['services'])
        self.assertIn('grafana', compose_config['services'])
        self.assertIn('redis', compose_config['services'])
    
    def test_prometheus_config_exists(self):
        """Test that Prometheus configuration exists"""
        prometheus_config = Path(__file__).parent / "config" / "prometheus.yml"
        self.assertTrue(prometheus_config.exists(), "Prometheus config not found")
        
        import yaml
        with open(prometheus_config, 'r') as f:
            config = yaml.safe_load(f)
        
        self.assertIn('scrape_configs', config)
        self.assertIn('global', config)
    
    def test_alert_rules_exist(self):
        """Test that alert rules configuration exists"""
        alert_rules = Path(__file__).parent / "config" / "alert_rules.yml"
        self.assertTrue(alert_rules.exists(), "Alert rules config not found")
        
        import yaml
        with open(alert_rules, 'r') as f:
            config = yaml.safe_load(f)
        
        self.assertIn('groups', config)
        self.assertGreater(len(config['groups']), 0)

def run_async_test(test_func):
    """Helper function to run async tests"""
    return asyncio.run(test_func())

class AsyncTestRunner:
    """Custom test runner for async tests"""
    
    @staticmethod
    def run_test_suite():
        """Run the complete test suite"""
        # Create test suite
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Add test classes
        test_classes = [
            TestMetricsCollector,
            TestSystemMonitor,
            TestHealthChecker,
            TestAlertManager,
            TestMonitoringInfrastructure,
            TestMonitoringServer,
            TestDockerIntegration
        ]
        
        for test_class in test_classes:
            tests = loader.loadTestsFromTestCase(test_class)
            suite.addTests(tests)
        
        # Run synchronous tests
        runner = unittest.TextTestRunner(verbosity=2)
        sync_result = runner.run(suite)
        
        # Run async integration tests
        print("\\n" + "="*70)
        print("Running Async Integration Tests")
        print("="*70)
        
        async_tests = [
            TestHealthChecker().test_run_health_checks,
            TestHealthChecker().test_custom_health_check,
            TestAlertManager().test_create_alert,
            TestAlertManager().test_resolve_alert,
            TestMonitoringInfrastructure().test_start_stop,
            TestIntegration().test_full_monitoring_lifecycle,
            TestIntegration().test_monitoring_server_integration
        ]
        
        async_results = []
        for test in async_tests:
            try:
                print(f"Running {test.__name__}...")
                asyncio.run(test())
                print(f"✓ {test.__name__} passed")
                async_results.append(True)
            except Exception as e:
                print(f"✗ {test.__name__} failed: {e}")
                async_results.append(False)
        
        # Summary
        print("\\n" + "="*70)
        print("Test Results Summary")
        print("="*70)
        print(f"Synchronous tests: {sync_result.testsRun} run, {len(sync_result.failures)} failures, {len(sync_result.errors)} errors")
        print(f"Asynchronous tests: {len(async_tests)} run, {async_results.count(False)} failures")
        
        total_tests = sync_result.testsRun + len(async_tests)
        total_failures = len(sync_result.failures) + len(sync_result.errors) + async_results.count(False)
        
        print(f"\\nOverall: {total_tests} tests, {total_failures} failures")
        
        if total_failures == 0:
            print("\\n🎉 All tests passed!")
            return True
        else:
            print(f"\\n❌ {total_failures} tests failed")
            return False

def main():
    """Main test execution function"""
    print("="*70)
    print("Trading System Monitoring Infrastructure Test Suite")
    print("="*70)
    
    # Set up test environment
    os.environ['MONITORING_TEST_MODE'] = 'true'
    
    # Run tests
    runner = AsyncTestRunner()
    success = runner.run_test_suite()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()