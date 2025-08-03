#!/usr/bin/env python3
"""
Comprehensive Test Suite for Production Monitoring and Observability
Tests all monitoring components including infrastructure, alerting, and analytics.
"""

import asyncio
import json
import time
import unittest
import requests
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monitoring.monitoring_infrastructure import (
    MetricsCollector, SystemMonitor, HealthChecker, AlertManager,
    MetricType, AlertSeverity, ComponentStatus
)
from monitoring.advanced_alerting_analytics import (
    AdvancedAlertingSystem, AnomalyDetector, PredictiveAnalytics,
    AlertCorrelationEngine, PerformanceAnalyzer
)

class TestMonitoringInfrastructure(unittest.TestCase):
    """Test monitoring infrastructure components"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.metrics_collector = MetricsCollector()
        self.system_monitor = SystemMonitor(self.metrics_collector)
        self.health_checker = HealthChecker()
        self.alert_manager = AlertManager()
    
    def test_metrics_collector_initialization(self):
        """Test metrics collector initialization"""
        self.assertIsNotNone(self.metrics_collector.registry)
        self.assertIsInstance(self.metrics_collector.metrics, dict)
        self.assertIsInstance(self.metrics_collector.metric_definitions, dict)
        
        # Check that core metrics are registered
        core_metrics = [
            'system_cpu_percent',
            'system_memory_percent',
            'system_disk_percent',
            'http_requests_total',
            'http_request_duration_seconds',
            'trading_orders_total',
            'trading_order_processing_time',
            'fraud_detection_score',
            'security_events_total'
        ]
        
        for metric_name in core_metrics:
            self.assertIn(metric_name, self.metrics_collector.metrics)
            self.assertIn(metric_name, self.metrics_collector.metric_definitions)
    
    def test_counter_metric_operations(self):
        """Test counter metric operations"""
        # Test incrementing counter without labels
        self.metrics_collector.increment_counter('http_requests_total')
        
        # Test incrementing counter with labels
        labels = {'method': 'GET', 'endpoint': '/api/orders', 'status': '200'}
        self.metrics_collector.increment_counter('http_requests_total', labels, 5.0)
        
        # Get metrics text and verify counter is present
        metrics_text = self.metrics_collector.get_metrics_text()
        self.assertIn('trading_system_http_requests_total', metrics_text)
    
    def test_gauge_metric_operations(self):
        """Test gauge metric operations"""
        # Test setting gauge without labels
        self.metrics_collector.set_gauge('system_cpu_percent', 45.5)
        
        # Test setting gauge with labels (if supported)
        self.metrics_collector.set_gauge('system_memory_percent', 67.8)
        
        # Get metrics text and verify gauge is present
        metrics_text = self.metrics_collector.get_metrics_text()
        self.assertIn('trading_system_system_cpu_percent', metrics_text)
        self.assertIn('trading_system_system_memory_percent', metrics_text)
    
    def test_histogram_metric_operations(self):
        """Test histogram metric operations"""
        # Test observing histogram without labels
        self.metrics_collector.observe_histogram('http_request_duration_seconds', 0.125)
        
        # Test observing histogram with labels
        labels = {'method': 'POST', 'endpoint': '/api/trades'}
        self.metrics_collector.observe_histogram('http_request_duration_seconds', 0.250, labels)
        
        # Get metrics text and verify histogram is present
        metrics_text = self.metrics_collector.get_metrics_text()
        self.assertIn('trading_system_http_request_duration_seconds', metrics_text)
    
    def test_system_monitor_metrics_collection(self):
        """Test system monitor metrics collection"""
        # Collect system metrics
        metrics = self.system_monitor.collect_system_metrics()
        
        # Verify all required fields are present
        self.assertIsInstance(metrics.timestamp, datetime)
        self.assertIsInstance(metrics.cpu_percent, float)
        self.assertIsInstance(metrics.memory_percent, float)
        self.assertIsInstance(metrics.memory_used_gb, float)
        self.assertIsInstance(metrics.memory_total_gb, float)
        self.assertIsInstance(metrics.disk_percent, float)
        self.assertIsInstance(metrics.disk_used_gb, float)
        self.assertIsInstance(metrics.disk_total_gb, float)
        self.assertIsInstance(metrics.network_bytes_sent, int)
        self.assertIsInstance(metrics.network_bytes_recv, int)
        self.assertIsInstance(metrics.load_average, list)
        self.assertIsInstance(metrics.process_count, int)
        self.assertIsInstance(metrics.thread_count, int)
        
        # Verify reasonable ranges
        self.assertGreaterEqual(metrics.cpu_percent, 0)
        self.assertLessEqual(metrics.cpu_percent, 100)
        self.assertGreaterEqual(metrics.memory_percent, 0)
        self.assertLessEqual(metrics.memory_percent, 100)
        self.assertGreater(metrics.memory_total_gb, 0)
        self.assertGreater(metrics.disk_total_gb, 0)
        self.assertGreaterEqual(metrics.process_count, 1)
        self.assertGreaterEqual(metrics.thread_count, 1)
    
    def test_health_checker_default_checks(self):
        """Test health checker default health checks"""
        # Run health checks
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            health_results = loop.run_until_complete(self.health_checker.run_health_checks())
            
            # Verify default health checks are present
            expected_checks = ['system_resources', 'disk_space', 'memory_usage']
            for check_name in expected_checks:
                self.assertIn(check_name, health_results)
                
                health_check = health_results[check_name]
                self.assertEqual(health_check.name, check_name)
                self.assertIsInstance(health_check.status, ComponentStatus)
                self.assertIsInstance(health_check.message, str)
                self.assertIsInstance(health_check.timestamp, datetime)
                self.assertGreaterEqual(health_check.response_time_ms, 0)
                self.assertIsInstance(health_check.metadata, dict)
        finally:
            loop.close()
    
    def test_alert_manager_alert_creation(self):
        """Test alert manager alert creation and management"""
        # Create test alert
        alert = self.alert_manager.create_alert(
            name="Test Alert",
            severity=AlertSeverity.WARNING,
            message="This is a test alert",
            component="test_component",
            labels={'test': 'true'}
        )
        
        self.assertIsNotNone(alert.alert_id)
        self.assertEqual(alert.name, "Test Alert")
        self.assertEqual(alert.severity, AlertSeverity.WARNING)
        self.assertEqual(alert.message, "This is a test alert")
        self.assertEqual(alert.component, "test_component")
        self.assertFalse(alert.resolved)
        self.assertIsNone(alert.resolved_at)
        
        # Test alert storage
        self.assertIn(alert.alert_id, self.alert_manager.active_alerts)
        
        # Test alert resolution
        self.alert_manager.resolve_alert(alert.alert_id, "Test resolution")
        resolved_alert = self.alert_manager.active_alerts[alert.alert_id]
        self.assertTrue(resolved_alert.resolved)
        self.assertIsNotNone(resolved_alert.resolved_at)

class TestAdvancedAlertingAnalytics(unittest.TestCase):
    """Test advanced alerting and analytics components"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.alerting_system = AdvancedAlertingSystem()
        self.anomaly_detector = AnomalyDetector()
        self.predictive_analytics = PredictiveAnalytics()
        self.correlation_engine = AlertCorrelationEngine()
        self.performance_analyzer = PerformanceAnalyzer()
    
    def test_anomaly_detector_initialization(self):
        """Test anomaly detector initialization"""
        self.assertIsNotNone(self.anomaly_detector.models)
        self.assertIsInstance(self.anomaly_detector.training_data, dict)
        self.assertIsInstance(self.anomaly_detector.detection_thresholds, dict)
    
    def test_anomaly_detection_with_sample_data(self):
        """Test anomaly detection with sample data"""
        # Generate sample normal data
        normal_data = [10.0, 12.0, 11.5, 9.8, 10.2, 11.0, 10.5, 9.9, 10.8, 11.2]
        
        # Train the detector
        self.anomaly_detector.train_model('cpu_usage', normal_data)
        
        # Test normal value detection
        is_anomaly, score = self.anomaly_detector.detect_anomaly('cpu_usage', 10.5)
        self.assertFalse(is_anomaly)
        self.assertIsInstance(score, float)
        
        # Test anomalous value detection
        is_anomaly, score = self.anomaly_detector.detect_anomaly('cpu_usage', 50.0)
        self.assertTrue(is_anomaly)
        self.assertGreater(score, 0.5)  # High anomaly score
    
    def test_predictive_analytics_trend_analysis(self):
        """Test predictive analytics trend analysis"""
        # Generate sample time series data
        timestamps = [datetime.now() - timedelta(minutes=i) for i in range(60, 0, -1)]
        values = [10 + i * 0.1 + (i % 5) * 0.5 for i in range(60)]  # Trending upward with noise
        
        # Analyze trend
        trend_analysis = self.predictive_analytics.analyze_trend('cpu_usage', timestamps, values)
        
        self.assertIn('trend_direction', trend_analysis)
        self.assertIn('trend_strength', trend_analysis)
        self.assertIn('prediction_confidence', trend_analysis)
        self.assertIn('next_values', trend_analysis)
        
        # Verify trend direction is detected
        self.assertIn(trend_analysis['trend_direction'], ['increasing', 'decreasing', 'stable'])
        self.assertIsInstance(trend_analysis['trend_strength'], float)
        self.assertIsInstance(trend_analysis['prediction_confidence'], float)
        self.assertIsInstance(trend_analysis['next_values'], list)\n    \n    def test_alert_correlation_engine(self):\n        \"\"\"Test alert correlation engine\"\"\"\n        # Create sample alerts\n        alert1 = {\n            'alert_id': 'alert_1',\n            'component': 'database',\n            'severity': 'ERROR',\n            'timestamp': datetime.now(),\n            'message': 'High CPU usage'\n        }\n        \n        alert2 = {\n            'alert_id': 'alert_2',\n            'component': 'database',\n            'severity': 'WARNING',\n            'timestamp': datetime.now() + timedelta(seconds=30),\n            'message': 'Slow query performance'\n        }\n        \n        alert3 = {\n            'alert_id': 'alert_3',\n            'component': 'web_server',\n            'severity': 'INFO',\n            'timestamp': datetime.now() + timedelta(minutes=5),\n            'message': 'High request rate'\n        }\n        \n        # Add alerts to correlation engine\n        self.correlation_engine.add_alert(alert1)\n        self.correlation_engine.add_alert(alert2)\n        self.correlation_engine.add_alert(alert3)\n        \n        # Find correlations\n        correlations = self.correlation_engine.find_correlations()\n        \n        self.assertIsInstance(correlations, list)\n        \n        # Check if database alerts are correlated\n        database_correlations = [\n            corr for corr in correlations \n            if any(alert['component'] == 'database' for alert in corr['alerts'])\n        ]\n        \n        self.assertGreater(len(database_correlations), 0)\n    \n    def test_performance_analyzer_metrics_analysis(self):\n        \"\"\"Test performance analyzer metrics analysis\"\"\"\n        # Generate sample performance data\n        performance_data = {\n            'response_times': [0.1, 0.15, 0.12, 0.18, 0.11, 0.16, 0.13, 0.14, 0.17, 0.12],\n            'throughput': [100, 95, 102, 88, 105, 92, 98, 101, 89, 103],\n            'error_rates': [0.01, 0.02, 0.01, 0.03, 0.01, 0.02, 0.01, 0.01, 0.04, 0.01],\n            'resource_usage': [45.2, 48.1, 46.8, 52.3, 44.9, 49.7, 47.2, 46.5, 51.8, 45.8]\n        }\n        \n        # Analyze performance\n        analysis = self.performance_analyzer.analyze_performance_metrics(performance_data)\n        \n        self.assertIn('summary', analysis)\n        self.assertIn('recommendations', analysis)\n        self.assertIn('alerts', analysis)\n        self.assertIn('trends', analysis)\n        \n        # Verify analysis structure\n        summary = analysis['summary']\n        self.assertIn('avg_response_time', summary)\n        self.assertIn('avg_throughput', summary)\n        self.assertIn('avg_error_rate', summary)\n        self.assertIn('avg_resource_usage', summary)\n        \n        self.assertIsInstance(analysis['recommendations'], list)\n        self.assertIsInstance(analysis['alerts'], list)\n        self.assertIsInstance(analysis['trends'], dict)\n\nclass TestMonitoringIntegration(unittest.TestCase):\n    \"\"\"Test monitoring system integration\"\"\"\n    \n    def setUp(self):\n        \"\"\"Set up integration test fixtures\"\"\"\n        self.metrics_collector = MetricsCollector()\n        self.system_monitor = SystemMonitor(self.metrics_collector)\n        self.health_checker = HealthChecker()\n        self.alert_manager = AlertManager()\n        self.alerting_system = AdvancedAlertingSystem()\n    \n    def test_end_to_end_monitoring_workflow(self):\n        \"\"\"Test complete monitoring workflow\"\"\"\n        # 1. Start system monitoring\n        self.system_monitor.start_monitoring()\n        \n        # 2. Wait for some metrics to be collected\n        time.sleep(2)\n        \n        # 3. Collect current system metrics\n        current_metrics = self.system_monitor.collect_system_metrics()\n        self.assertIsNotNone(current_metrics)\n        \n        # 4. Run health checks\n        loop = asyncio.new_event_loop()\n        asyncio.set_event_loop(loop)\n        \n        try:\n            health_results = loop.run_until_complete(self.health_checker.run_health_checks())\n            self.assertGreater(len(health_results), 0)\n            \n            # 5. Create alerts based on health check results\n            for check_name, health_check in health_results.items():\n                if health_check.status in [ComponentStatus.DEGRADED, ComponentStatus.UNHEALTHY]:\n                    alert = self.alert_manager.create_alert(\n                        name=f\"Health Check Alert: {check_name}\",\n                        severity=AlertSeverity.WARNING if health_check.status == ComponentStatus.DEGRADED else AlertSeverity.ERROR,\n                        message=health_check.message,\n                        component=health_check.component\n                    )\n                    self.assertIsNotNone(alert)\n            \n            # 6. Get metrics in Prometheus format\n            metrics_text = self.metrics_collector.get_metrics_text()\n            self.assertIsInstance(metrics_text, str)\n            self.assertIn('trading_system_', metrics_text)\n            \n        finally:\n            loop.close()\n            \n        # 7. Stop monitoring\n        self.system_monitor.stop_monitoring()\n    \n    def test_metrics_export_format(self):\n        \"\"\"Test metrics export in Prometheus format\"\"\"\n        # Generate some sample metrics\n        self.metrics_collector.increment_counter('http_requests_total', {'method': 'GET', 'endpoint': '/api/test', 'status': '200'})\n        self.metrics_collector.set_gauge('system_cpu_percent', 25.5)\n        self.metrics_collector.observe_histogram('http_request_duration_seconds', 0.125, {'method': 'GET', 'endpoint': '/api/test'})\n        \n        # Export metrics\n        metrics_text = self.metrics_collector.get_metrics_text()\n        \n        # Verify Prometheus format\n        self.assertIn('# HELP', metrics_text)\n        self.assertIn('# TYPE', metrics_text)\n        self.assertIn('trading_system_http_requests_total', metrics_text)\n        self.assertIn('trading_system_system_cpu_percent', metrics_text)\n        self.assertIn('trading_system_http_request_duration_seconds', metrics_text)\n        \n        # Verify labels are present\n        self.assertIn('method=\"GET\"', metrics_text)\n        self.assertIn('endpoint=\"/api/test\"', metrics_text)\n        self.assertIn('status=\"200\"', metrics_text)\n\nclass TestDockerizedMonitoring(unittest.TestCase):\n    \"\"\"Test Docker-based monitoring setup\"\"\"\n    \n    def test_docker_compose_configuration(self):\n        \"\"\"Test Docker Compose configuration exists and is valid\"\"\"\n        import yaml\n        \n        # Check if docker-compose.yml exists\n        compose_file = 'monitoring/docker-compose.yml'\n        self.assertTrue(os.path.exists(compose_file), \"Docker Compose file should exist\")\n        \n        # Load and validate docker-compose.yml\n        with open(compose_file, 'r') as f:\n            compose_config = yaml.safe_load(f)\n        \n        self.assertIn('services', compose_config)\n        \n        # Check required services\n        required_services = ['monitoring-infrastructure', 'prometheus', 'grafana', 'redis']\n        for service in required_services:\n            self.assertIn(service, compose_config['services'])\n        \n        # Check monitoring-infrastructure service\n        monitoring_service = compose_config['services']['monitoring-infrastructure']\n        self.assertIn('build', monitoring_service)\n        self.assertIn('ports', monitoring_service)\n        self.assertIn('volumes', monitoring_service)\n        self.assertIn('environment', monitoring_service)\n        \n        # Check Prometheus service\n        prometheus_service = compose_config['services']['prometheus']\n        self.assertIn('image', prometheus_service)\n        self.assertEqual(prometheus_service['image'], 'prom/prometheus:latest')\n        self.assertIn('ports', prometheus_service)\n        self.assertIn('9090:9090', prometheus_service['ports'])\n        \n        # Check Grafana service\n        grafana_service = compose_config['services']['grafana']\n        self.assertIn('image', grafana_service)\n        self.assertEqual(grafana_service['image'], 'grafana/grafana:latest')\n        self.assertIn('ports', grafana_service)\n        self.assertIn('3000:3000', grafana_service['ports'])\n    \n    def test_dockerfile_configuration(self):\n        \"\"\"Test Dockerfile configuration\"\"\"\n        dockerfile_path = 'monitoring/Dockerfile'\n        self.assertTrue(os.path.exists(dockerfile_path), \"Dockerfile should exist\")\n        \n        with open(dockerfile_path, 'r') as f:\n            dockerfile_content = f.read()\n        \n        # Check essential Dockerfile components\n        self.assertIn('FROM python:3.11-slim', dockerfile_content)\n        self.assertIn('WORKDIR /app', dockerfile_content)\n        self.assertIn('COPY requirements.txt', dockerfile_content)\n        self.assertIn('RUN pip install', dockerfile_content)\n        self.assertIn('EXPOSE', dockerfile_content)\n        self.assertIn('HEALTHCHECK', dockerfile_content)\n        self.assertIn('CMD', dockerfile_content)\n    \n    def test_requirements_file(self):\n        \"\"\"Test requirements.txt file\"\"\"\n        requirements_path = 'monitoring/requirements.txt'\n        self.assertTrue(os.path.exists(requirements_path), \"Requirements file should exist\")\n        \n        with open(requirements_path, 'r') as f:\n            requirements_content = f.read()\n        \n        # Check essential dependencies\n        essential_deps = [\n            'prometheus-client',\n            'psutil',\n            'requests',\n            'structlog',\n            'aiohttp',\n            'fastapi',\n            'uvicorn',\n            'pyyaml',\n            'pytest'\n        ]\n        \n        for dep in essential_deps:\n            self.assertIn(dep, requirements_content)\n\ndef run_monitoring_tests():\n    \"\"\"Run all monitoring tests\"\"\"\n    # Create test suite\n    test_suite = unittest.TestSuite()\n    \n    # Add test cases\n    test_classes = [\n        TestMonitoringInfrastructure,\n        TestAdvancedAlertingAnalytics,\n        TestMonitoringIntegration,\n        TestDockerizedMonitoring\n    ]\n    \n    for test_class in test_classes:\n        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)\n        test_suite.addTests(tests)\n    \n    # Run tests\n    runner = unittest.TextTestRunner(verbosity=2)\n    result = runner.run(test_suite)\n    \n    return result.wasSuccessful()\n\nif __name__ == '__main__':\n    print(\"Running Comprehensive Monitoring Tests...\")\n    print(\"=\" * 50)\n    \n    success = run_monitoring_tests()\n    \n    if success:\n        print(\"\\n\" + \"=\" * 50)\n        print(\"✅ All monitoring tests passed successfully!\")\n        print(\"The monitoring infrastructure is ready for production.\")\n    else:\n        print(\"\\n\" + \"=\" * 50)\n        print(\"❌ Some monitoring tests failed.\")\n        print(\"Please review the test output and fix any issues.\")\n    \n    exit(0 if success else 1)"