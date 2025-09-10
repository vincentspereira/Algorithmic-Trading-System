"""
Test suite for Data Feed Monitoring System
"""

import unittest
import asyncio
import logging
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, List, Any

from nautilus_trader_engine.monitoring.data_feed_monitor import (
    DataFeedMonitor,
    DataFeedHealthStatus,
    DataFeedPerformanceMetrics,
    DataFeedAlertManager
)
from nautilus_trader_engine.core.data_feeds import (
    DataFeedManager,
    DataSource,
    AssetClass,
    DataRequest,
    DataResponse
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestMetricCollector:
    """Simple metric collector for testing"""
    
    def __init__(self):
        self.collected_metrics = []
        self.metric_definitions = {}
    
    def register_metric(self, definition):
        self.metric_definitions[definition.name] = definition
        return True
    
    def collect_metric(self, name: str, value: float, tags: Dict[str, str] = None, metadata: Dict[str, Any] = None) -> bool:
        self.collected_metrics.append({
            "name": name,
            "value": value,
            "tags": tags or {},
            "timestamp": datetime.now()
        })
        return True
    
    def get_collection_stats(self):
        return {
            "total_metrics_collected": len(self.collected_metrics),
            "registered_metrics": len(self.metric_definitions)
        }


class TestDataFeedMonitor(unittest.TestCase):
    """Test cases for DataFeedMonitor"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.data_feed_manager = DataFeedManager()
        self.metric_collector = TestMetricCollector()
        self.monitor = DataFeedMonitor(self.data_feed_manager, self.metric_collector)
    
    def test_initialization(self):
        """Test that monitor initializes correctly"""
        self.assertIsInstance(self.monitor, DataFeedMonitor)
        self.assertEqual(len(self.monitor.health_status), len(DataSource))
        self.assertFalse(self.monitor.is_monitoring)
    
    def test_register_metrics(self):
        """Test that metrics are registered correctly"""
        expected_metrics = [
            "data_feed.success_rate",
            "data_feed.response_time.avg",
            "data_feed.requests.total",
            "data_feed.errors.total",
            "data_feed.availability"
        ]
        
        registered_metrics = list(self.metric_collector.metric_definitions.keys())
        for metric in expected_metrics:
            self.assertIn(metric, registered_metrics)
    
    @patch('nautilus_trader_engine.core.data_feeds.DataFeedManager.get_detailed_health_report')
    def test_perform_health_checks(self, mock_get_health_report):
        """Test health check functionality"""
        # Mock health report
        mock_health_report = {
            'sources': {
                'yahoo_finance': {
                    'status': 'healthy',
                    'success_rate': 0.98,
                    'avg_response_time': 0.5,
                    'total_checks': 100,
                    'successful_checks': 98
                },
                'alpha_vantage': {
                    'status': 'degraded',
                    'success_rate': 0.85,
                    'avg_response_time': 2.1,
                    'total_checks': 100,
                    'successful_checks': 85
                }
            }
        }
        mock_get_health_report.return_value = mock_health_report
        
        # Perform health checks
        health_status = asyncio.run(self.monitor.perform_health_checks())
        
        # Verify results
        self.assertEqual(len(health_status), len(DataSource))
        self.assertEqual(health_status[DataSource.YAHOO_FINANCE].status, 'healthy')
        self.assertEqual(health_status[DataSource.YAHOO_FINANCE].success_rate, 0.98)
        self.assertEqual(health_status[DataSource.ALPHA_VANTAGE].status, 'degraded')
        self.assertEqual(health_status[DataSource.ALPHA_VANTAGE].success_rate, 0.85)
    
    @patch('nautilus_trader_engine.core.data_feeds.DataFeedManager._fetch_from_source')
    def test_test_data_feed_connectivity_success(self, mock_fetch):
        """Test connectivity test with successful response"""
        # Mock successful response
        mock_response = DataResponse(
            data=MagicMock(),
            source=DataSource.YAHOO_FINANCE,
            ticker="AAPL",
            asset_class=AssetClass.STOCK,
            metadata={},
            timestamp=1234567890.0,
            success=True
        )
        mock_fetch.return_value = mock_response
        
        # Test connectivity
        metrics = asyncio.run(
            self.monitor.test_data_feed_connectivity(DataSource.YAHOO_FINANCE)
        )
        
        # Verify results
        self.assertIsInstance(metrics, DataFeedPerformanceMetrics)
        self.assertEqual(metrics.source, DataSource.YAHOO_FINANCE)
        self.assertTrue(metrics.success)
        self.assertGreater(metrics.data_points, 0)
        self.assertGreater(metrics.response_time, 0)
    
    @patch('nautilus_trader_engine.core.data_feeds.DataFeedManager._fetch_from_source')
    def test_test_data_feed_connectivity_failure(self, mock_fetch):
        """Test connectivity test with failed response"""
        # Mock failed response
        mock_response = DataResponse(
            data=MagicMock(),
            source=DataSource.YAHOO_FINANCE,
            ticker="AAPL",
            asset_class=AssetClass.STOCK,
            metadata={},
            timestamp=1234567890.0,
            success=False,
            error_message="API limit exceeded"
        )
        mock_fetch.return_value = mock_response
        
        # Test connectivity
        metrics = asyncio.run(
            self.monitor.test_data_feed_connectivity(DataSource.YAHOO_FINANCE)
        )
        
        # Verify results
        self.assertIsInstance(metrics, DataFeedPerformanceMetrics)
        self.assertEqual(metrics.source, DataSource.YAHOO_FINANCE)
        self.assertFalse(metrics.success)
        self.assertEqual(metrics.error_message, "API limit exceeded")
    
    def test_get_health_status(self):
        """Test getting health status"""
        # Get all health status
        all_status = self.monitor.get_health_status()
        self.assertEqual(len(all_status), len(DataSource))
        
        # Get specific source status
        yahoo_status = self.monitor.get_health_status(DataSource.YAHOO_FINANCE)
        self.assertIn(DataSource.YAHOO_FINANCE, yahoo_status)
    
    def test_get_performance_history(self):
        """Test getting performance history"""
        # Initially should be empty
        history = self.monitor.get_performance_history(DataSource.YAHOO_FINANCE)
        self.assertEqual(len(history), 0)
        
        # Add some mock data
        mock_metrics = DataFeedPerformanceMetrics(
            source=DataSource.YAHOO_FINANCE,
            timestamp=datetime.now(),
            response_time=100.0,
            data_points=50,
            success=True
        )
        self.monitor.performance_history[DataSource.YAHOO_FINANCE].append(mock_metrics)
        
        # Should now have data
        history = self.monitor.get_performance_history(DataSource.YAHOO_FINANCE)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0], mock_metrics)
    
    def test_get_overall_health_score(self):
        """Test overall health score calculation"""
        # Initially should be 0
        score = self.monitor.get_overall_health_score()
        self.assertEqual(score, 0.0)
        
        # Set some mock health statuses
        self.monitor.health_status[DataSource.YAHOO_FINANCE] = DataFeedHealthStatus(
            source=DataSource.YAHOO_FINANCE,
            status="healthy",
            last_check=datetime.now(),
            success_rate=1.0,
            avg_response_time=0.1,
            total_requests=100,
            successful_requests=100,
            failed_requests=0
        )
        
        self.monitor.health_status[DataSource.ALPHA_VANTAGE] = DataFeedHealthStatus(
            source=DataSource.ALPHA_VANTAGE,
            status="degraded",
            last_check=datetime.now(),
            success_rate=0.5,
            avg_response_time=1.0,
            total_requests=100,
            successful_requests=50,
            failed_requests=50
        )
        
        # Should now have a score
        score = self.monitor.get_overall_health_score()
        # Expected: (100.0 + 50.0) / 2 = 75.0
        self.assertEqual(score, 75.0)
    
    def test_generate_health_report(self):
        """Test health report generation"""
        # Set some mock health statuses
        self.monitor.health_status[DataSource.YAHOO_FINANCE] = DataFeedHealthStatus(
            source=DataSource.YAHOO_FINANCE,
            status="healthy",
            last_check=datetime.now(),
            success_rate=1.0,
            avg_response_time=0.1,
            total_requests=100,
            successful_requests=100,
            failed_requests=0
        )
        
        # Generate report
        report = self.monitor.generate_health_report()
        
        # Verify structure
        self.assertIn("timestamp", report)
        self.assertIn("overall_health_score", report)
        self.assertIn("sources", report)
        self.assertIn("summary", report)
        
        # Verify summary counts
        self.assertEqual(report["summary"]["healthy_sources"], 1)
        self.assertEqual(report["summary"]["total_sources"], len(DataSource))


class TestDataFeedAlertManager(unittest.TestCase):
    """Test cases for DataFeedAlertManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.data_feed_manager = DataFeedManager()
        self.metric_collector = TestMetricCollector()
        self.monitor = DataFeedMonitor(self.data_feed_manager, self.metric_collector)
        self.alert_manager = DataFeedAlertManager(self.monitor)
    
    def test_initialization(self):
        """Test that alert manager initializes correctly"""
        self.assertIsInstance(self.alert_manager, DataFeedAlertManager)
        self.assertEqual(len(self.alert_manager.alert_rules), 3)  # success_rate, response_time, availability
    
    def test_evaluate_alerts_healthy(self):
        """Test alert evaluation with healthy status"""
        # Set healthy status
        self.monitor.health_status[DataSource.YAHOO_FINANCE] = DataFeedHealthStatus(
            source=DataSource.YAHOO_FINANCE,
            status="healthy",
            last_check=datetime.now(),
            success_rate=1.0,
            avg_response_time=0.1,
            total_requests=100,
            successful_requests=100,
            failed_requests=0
        )
        
        # Evaluate alerts
        alerts = self.alert_manager.evaluate_alerts()
        
        # Should have no alerts
        self.assertEqual(len(alerts), 0)
        self.assertEqual(len(self.alert_manager.get_active_alerts()), 0)
    
    def test_evaluate_alerts_degraded(self):
        """Test alert evaluation with degraded status"""
        # Set degraded status
        self.monitor.health_status[DataSource.YAHOO_FINANCE] = DataFeedHealthStatus(
            source=DataSource.YAHOO_FINANCE,
            status="degraded",
            last_check=datetime.now(),
            success_rate=0.5,
            avg_response_time=2.0,
            total_requests=100,
            successful_requests=50,
            failed_requests=50
        )
        
        # Evaluate alerts
        alerts = self.alert_manager.evaluate_alerts()
        
        # Should have one alert
        self.assertEqual(len(alerts), 1)
        self.assertEqual(len(self.alert_manager.get_active_alerts()), 1)
        
        # Verify alert properties
        alert = alerts[0]
        self.assertIn("degraded", alert.title)
        self.assertEqual(alert.severity.value, "medium")
        self.assertEqual(alert.category.value, "performance")
    
    def test_evaluate_alerts_unhealthy(self):
        """Test alert evaluation with unhealthy status"""
        # Set unhealthy status
        self.monitor.health_status[DataSource.YAHOO_FINANCE] = DataFeedHealthStatus(
            source=DataSource.YAHOO_FINANCE,
            status="unhealthy",
            last_check=datetime.now(),
            success_rate=0.1,
            avg_response_time=5.0,
            total_requests=100,
            successful_requests=10,
            failed_requests=90
        )
        
        # Evaluate alerts
        alerts = self.alert_manager.evaluate_alerts()
        
        # Should have one alert
        self.assertEqual(len(alerts), 1)
        self.assertEqual(len(self.alert_manager.get_active_alerts()), 1)
        
        # Verify alert properties
        alert = alerts[0]
        self.assertIn("unhealthy", alert.title)
        self.assertEqual(alert.severity.value, "high")
        self.assertEqual(alert.category.value, "performance")
    
    def test_acknowledge_alert(self):
        """Test acknowledging an alert"""
        # Create a mock alert
        from nautilus_trader_engine.monitoring.intelligent_alerting import Alert, AlertSeverity, AlertCategory
        
        alert = Alert(
            alert_id="test_alert_1",
            title="Test Alert",
            description="Test alert description",
            severity=AlertSeverity.HIGH,
            category=AlertCategory.PERFORMANCE,
            source="test"
        )
        
        # Add to active alerts
        self.alert_manager.active_alerts[alert.alert_id] = alert
        
        # Acknowledge the alert
        self.alert_manager.acknowledge_alert("test_alert_1", "test_user")
        
        # Verify it's acknowledged
        updated_alert = self.alert_manager.active_alerts["test_alert_1"]
        self.assertEqual(updated_alert.status, "acknowledged")
        self.assertEqual(updated_alert.acknowledged_by, "test_user")
        self.assertIsNotNone(updated_alert.acknowledged_at)
    
    def test_resolve_alert(self):
        """Test resolving an alert"""
        # Create a mock alert
        from nautilus_trader_engine.monitoring.intelligent_alerting import Alert, AlertSeverity, AlertCategory
        
        alert = Alert(
            alert_id="test_alert_1",
            title="Test Alert",
            description="Test alert description",
            severity=AlertSeverity.HIGH,
            category=AlertCategory.PERFORMANCE,
            source="test"
        )
        
        # Add to active alerts
        self.alert_manager.active_alerts[alert.alert_id] = alert
        
        # Resolve the alert
        self.alert_manager.resolve_alert("test_alert_1")
        
        # Verify it's resolved and moved to history
        self.assertNotIn("test_alert_1", self.alert_manager.active_alerts)
        self.assertEqual(len(self.alert_manager.alert_history), 1)
        
        resolved_alert = self.alert_manager.alert_history[0]
        self.assertEqual(resolved_alert.status, "resolved")
        self.assertIsNotNone(resolved_alert.resolved_at)
    
    def test_get_active_alerts(self):
        """Test getting active alerts"""
        # Initially should be empty
        active_alerts = self.alert_manager.get_active_alerts()
        self.assertEqual(len(active_alerts), 0)
        
        # Add some mock alerts
        from nautilus_trader_engine.monitoring.intelligent_alerting import Alert, AlertSeverity, AlertCategory
        
        alert1 = Alert(
            alert_id="test_alert_1",
            title="Test Alert 1",
            description="Test alert 1 description",
            severity=AlertSeverity.HIGH,
            category=AlertCategory.PERFORMANCE,
            source="test"
        )
        
        alert2 = Alert(
            alert_id="test_alert_2",
            title="Test Alert 2",
            description="Test alert 2 description",
            severity=AlertSeverity.MEDIUM,
            category=AlertCategory.PERFORMANCE,
            source="test"
        )
        
        self.alert_manager.active_alerts[alert1.alert_id] = alert1
        self.alert_manager.active_alerts[alert2.alert_id] = alert2
        
        # Should now have alerts
        active_alerts = self.alert_manager.get_active_alerts()
        self.assertEqual(len(active_alerts), 2)
    
    def test_get_alert_history(self):
        """Test getting alert history"""
        # Initially should be empty
        history = self.alert_manager.get_alert_history()
        self.assertEqual(len(history), 0)
        
        # Add some mock alerts to history
        from nautilus_trader_engine.monitoring.intelligent_alerting import Alert, AlertSeverity, AlertCategory
        
        alert1 = Alert(
            alert_id="test_alert_1",
            title="Test Alert 1",
            description="Test alert 1 description",
            severity=AlertSeverity.HIGH,
            category=AlertCategory.PERFORMANCE,
            source="test"
        )
        
        alert2 = Alert(
            alert_id="test_alert_2",
            title="Test Alert 2",
            description="Test alert 2 description",
            severity=AlertSeverity.MEDIUM,
            category=AlertCategory.PERFORMANCE,
            source="test"
        )
        
        self.alert_manager.alert_history.append(alert1)
        self.alert_manager.alert_history.append(alert2)
        
        # Should now have alerts
        history = self.alert_manager.get_alert_history()
        self.assertEqual(len(history), 2)


def run_tests():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestDataFeedMonitor))
    suite.addTests(loader.loadTestsFromTestCase(TestDataFeedAlertManager))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)