"""Tests for dashboard configuration and metrics collection."""

import json
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest
from prometheus_client.core import CollectorRegistry

from ..monitoring.dashboard_utils import DashboardConfig, DashboardManager
from ..monitoring.generate_dashboards import DashboardGenerator
from ..monitoring.metrics_collector import MetricsCollector

@pytest.fixture
def dashboard_dir():
    """Create a temporary directory for dashboard files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
def dashboard_config():
    """Create a sample dashboard configuration"""
    return DashboardConfig(
        uid="test-dashboard",
        title="Test Dashboard",
        folder="Test",
        variables=[],
        refresh_interval="5s"
    )

@pytest.fixture
def dashboard_manager(dashboard_dir):
    """Create a dashboard manager instance"""
    return DashboardManager(
        grafana_url="http://localhost:3000",
        api_key="test-key",
        dashboard_dir=dashboard_dir
    )

@pytest.fixture
def metrics_collector():
    """Create a metrics collector instance"""
    registry = CollectorRegistry()
    collector = MetricsCollector(port=9999)
    # Replace the default registry with our test registry
    for metric_name in dir(collector):
        metric = getattr(collector, metric_name)
        if hasattr(metric, "_metrics"):
            metric._metrics = {}
    return collector

def test_dashboard_config_creation():
    """Test creating a dashboard configuration"""
    config = DashboardConfig(
        uid="test",
        title="Test",
        folder="Test",
        variables=[{"name": "test", "type": "query"}]
    )
    
    assert config.uid == "test"
    assert config.title == "Test"
    assert config.folder == "Test"
    assert len(config.variables) == 1
    assert config.refresh_interval == "5s"

def test_dashboard_manager_save_load(dashboard_manager, dashboard_config):
    """Test saving and loading dashboard configurations"""
    test_file = "test_dashboard.json"
    test_panels = [
        {
            "title": "Test Panel",
            "type": "graph",
            "targets": [{"expr": "test_metric"}]
        }
    ]
    
    # Create and save dashboard
    dashboard = dashboard_manager.create_dashboard(dashboard_config, test_panels)
    dashboard_manager.save_dashboard(test_file, dashboard)
    
    # Load and verify dashboard
    loaded = dashboard_manager.load_dashboard(test_file)
    assert loaded["uid"] == dashboard_config.uid
    assert loaded["title"] == dashboard_config.title
    assert len(loaded["panels"]) == len(test_panels)

def test_dashboard_generator(dashboard_dir):
    """Test generating dashboard configurations"""
    generator = DashboardGenerator(
        grafana_url="http://localhost:3000",
        api_key="test-key",
        dashboard_dir=dashboard_dir
    )
    
    # Generate overview dashboard
    overview = generator.generate_overview_dashboard()
    assert overview["uid"] == "dep-overview"
    assert len(overview["panels"]) > 0
    assert "alerts" in overview
    
    # Generate security dashboard
    security = generator.generate_security_dashboard()
    assert security["uid"] == "dep-security"
    assert len(security["panels"]) > 0
    assert "alerts" in security
    
    # Generate performance dashboard
    performance = generator.generate_performance_dashboard()
    assert performance["uid"] == "dep-performance"
    assert len(performance["panels"]) > 0
    assert "alerts" in performance

def test_metrics_collector(metrics_collector):
    """Test metrics collection functionality"""
    tier = "test"
    dependency = "test-dep"
    
    # Test performance metrics
    metrics_collector.update_performance_score(tier, dependency, 85.5)
    metrics = metrics_collector.get_metrics(tier, dependency)
    assert metrics.performance_score._value == {(tier, dependency): 85.5}
    
    # Test resource usage metrics
    metrics_collector.update_resource_usage(tier, dependency, 45.2, 60.8)
    assert metrics.resource_usage_cpu._value == {(tier, dependency): 45.2}
    assert metrics.resource_usage_memory._value == {(tier, dependency): 60.8}
    
    # Test security metrics
    metrics_collector.update_security_metrics(
        tier,
        dependency,
        alerts=2,
        vulnerabilities=1,
        security_score=75.0,
        is_compliant=True
    )
    assert metrics.security_alerts._value == {(tier, dependency): 2}
    assert metrics.vulnerabilities._value == {(tier, dependency): 1}
    assert metrics.security_score._value == {(tier, dependency): 75.0}
    assert metrics.license_compliance._value == {(tier, dependency): 1}
    
    # Test error and request recording
    metrics_collector.record_error(tier, dependency)
    metrics_collector.record_request(tier, dependency, 0.5)
    assert metrics.errors_total._value == {(tier, dependency): 1}
    assert metrics.requests_total._value == {(tier, dependency): 1}

@mock.patch("requests.post")
def test_dashboard_deployment(mock_post, dashboard_manager, dashboard_config):
    """Test deploying dashboards to Grafana"""
    mock_post.return_value.status_code = 200
    
    # Create test dashboard
    dashboard = dashboard_manager.create_dashboard(
        dashboard_config,
        [{"title": "Test Panel"}]
    )
    
    # Test deployment
    result = dashboard_manager.deploy_dashboard(dashboard, "test-folder")
    assert result == True
    
    # Verify API call
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer test-key"
    assert "dashboard" in kwargs["json"]
