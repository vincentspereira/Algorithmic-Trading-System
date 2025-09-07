#!/usr/bin/env python3
"""
Performance Monitoring Integration Tests
Tests system performance monitoring, metrics collection, and alerting.
"""

import pytest
import asyncio
import time
import psutil
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import logging
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict, deque
import statistics
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Performance metric types"""
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    DISK_IO = "disk_io"
    NETWORK_IO = "network_io"
    ERROR_RATE = "error_rate"
    RESPONSE_TIME = "response_time"
    QUEUE_DEPTH = "queue_depth"
    CONNECTION_COUNT = "connection_count"


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class MetricData:
    """Performance metric data point"""
    metric_name: str
    metric_type: MetricType
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    unit: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "metric_name": self.metric_name,
            "metric_type": self.metric_type.value,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
            "unit": self.unit
        }


@dataclass
class AlertRule:
    """Performance alert rule"""
    rule_id: str
    metric_name: str
    condition: str  # e.g., ">", "<", "=="
    threshold: float
    severity: AlertSeverity
    duration: int = 60  # seconds
    enabled: bool = True
    
    def evaluate(self, value: float) -> bool:
        """Evaluate if alert should trigger"""
        if not self.enabled:
            return False
            
        if self.condition == ">":
            return value > self.threshold
        elif self.condition == "<":
            return value < self.threshold
        elif self.condition == ">=":
            return value >= self.threshold
        elif self.condition == "<=":
            return value <= self.threshold
        elif self.condition == "==":
            return value == self.threshold
        else:
            return False


@dataclass
class Alert:
    """Performance alert"""
    alert_id: str
    rule_id: str
    metric_name: str
    current_value: float
    threshold: float
    severity: AlertSeverity
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    message: str = ""
    
    @property
    def is_active(self) -> bool:
        """Check if alert is still active"""
        return self.resolved_at is None
        
    def resolve(self):
        """Resolve the alert"""
        self.resolved_at = datetime.now()


class MockSystemMonitor:
    """Mock system performance monitor"""
    
    def __init__(self):
        self.monitoring = False
        self.metrics_history = defaultdict(deque)
        self.current_metrics = {}
        self.collection_interval = 1.0  # seconds
        self.monitor_thread = None
        
    def start_monitoring(self):
        """Start system monitoring"""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("System monitoring started")
        
    def stop_monitoring(self):
        """Stop system monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        logger.info("System monitoring stopped")
        
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                # Collect system metrics
                metrics = self._collect_system_metrics()
                
                # Store metrics
                timestamp = datetime.now()
                for metric_name, value in metrics.items():
                    metric_data = MetricData(
                        metric_name=metric_name,
                        metric_type=self._get_metric_type(metric_name),
                        value=value,
                        timestamp=timestamp
                    )
                    
                    self.current_metrics[metric_name] = metric_data
                    self.metrics_history[metric_name].append(metric_data)
                    
                    # Keep only last 1000 data points
                    if len(self.metrics_history[metric_name]) > 1000:
                        self.metrics_history[metric_name].popleft()
                        
                time.sleep(self.collection_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.collection_interval)
                
    def _collect_system_metrics(self) -> Dict[str, float]:
        """Collect system performance metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_gb = memory.used / (1024**3)
            memory_available_gb = memory.available / (1024**3)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Network metrics (mock values for testing)
            network_bytes_sent = 1024 * 1024 * 10  # 10 MB
            network_bytes_recv = 1024 * 1024 * 15  # 15 MB
            
            return {
                "cpu_usage_percent": cpu_percent,
                "cpu_count": cpu_count,
                "memory_usage_percent": memory_percent,
                "memory_used_gb": memory_used_gb,
                "memory_available_gb": memory_available_gb,
                "disk_usage_percent": disk_percent,
                "network_bytes_sent": network_bytes_sent,
                "network_bytes_recv": network_bytes_recv
            }
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return {}
            
    def _get_metric_type(self, metric_name: str) -> MetricType:
        """Get metric type based on metric name"""
        if "cpu" in metric_name.lower():
            return MetricType.CPU_USAGE
        elif "memory" in metric_name.lower():
            return MetricType.MEMORY_USAGE
        elif "disk" in metric_name.lower():
            return MetricType.DISK_IO
        elif "network" in metric_name.lower():
            return MetricType.NETWORK_IO
        else:
            return MetricType.THROUGHPUT
            
    def get_current_metrics(self) -> Dict[str, MetricData]:
        """Get current metric values"""
        return self.current_metrics.copy()
        
    def get_metric_history(self, metric_name: str, duration_minutes: int = 60) -> List[MetricData]:
        """Get metric history for specified duration"""
        if metric_name not in self.metrics_history:
            return []
            
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        return [
            metric for metric in self.metrics_history[metric_name]
            if metric.timestamp >= cutoff_time
        ]
        
    def get_metric_statistics(self, metric_name: str, duration_minutes: int = 60) -> Dict[str, float]:
        """Get statistical summary of metric"""
        history = self.get_metric_history(metric_name, duration_minutes)
        
        if not history:
            return {}
            
        values = [m.value for m in history]
        
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0.0,
            "p95": self._percentile(values, 95),
            "p99": self._percentile(values, 99)
        }
        
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile"""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int((percentile / 100.0) * len(sorted_values))
        return sorted_values[min(index, len(sorted_values) - 1)]


class MockApplicationMonitor:
    """Mock application performance monitor"""
    
    def __init__(self):
        self.metrics = defaultdict(deque)
        self.request_times = deque()
        self.error_count = 0
        self.total_requests = 0
        
    def record_request(self, endpoint: str, response_time: float, status_code: int):
        """Record API request metrics"""
        timestamp = datetime.now()
        
        # Record response time
        metric_data = MetricData(
            metric_name=f"response_time_{endpoint}",
            metric_type=MetricType.RESPONSE_TIME,
            value=response_time,
            timestamp=timestamp,
            tags={"endpoint": endpoint, "status_code": str(status_code)},
            unit="ms"
        )
        
        self.metrics[f"response_time_{endpoint}"].append(metric_data)
        self.request_times.append((timestamp, response_time))
        
        # Track errors
        if status_code >= 400:
            self.error_count += 1
            
        self.total_requests += 1
        
        # Keep only last 1000 requests
        if len(self.request_times) > 1000:
            self.request_times.popleft()
            
    def record_throughput(self, component: str, operations_per_second: float):
        """Record throughput metrics"""
        metric_data = MetricData(
            metric_name=f"throughput_{component}",
            metric_type=MetricType.THROUGHPUT,
            value=operations_per_second,
            timestamp=datetime.now(),
            tags={"component": component},
            unit="ops/sec"
        )
        
        self.metrics[f"throughput_{component}"].append(metric_data)
        
    def record_queue_depth(self, queue_name: str, depth: int):
        """Record queue depth metrics"""
        metric_data = MetricData(
            metric_name=f"queue_depth_{queue_name}",
            metric_type=MetricType.QUEUE_DEPTH,
            value=depth,
            timestamp=datetime.now(),
            tags={"queue": queue_name},
            unit="items"
        )
        
        self.metrics[f"queue_depth_{queue_name}"].append(metric_data)
        
    def get_error_rate(self, duration_minutes: int = 5) -> float:
        """Calculate error rate over specified duration"""
        if self.total_requests == 0:
            return 0.0
            
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        recent_requests = [
            (timestamp, response_time) for timestamp, response_time in self.request_times
            if timestamp >= cutoff_time
        ]
        
        if not recent_requests:
            return 0.0
            
        # For simplicity, assume error rate is proportional to total errors
        return (self.error_count / self.total_requests) * 100
        
    def get_average_response_time(self, duration_minutes: int = 5) -> float:
        """Get average response time over specified duration"""
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        recent_times = [
            response_time for timestamp, response_time in self.request_times
            if timestamp >= cutoff_time
        ]
        
        if not recent_times:
            return 0.0
            
        return statistics.mean(recent_times)


class MockAlertManager:
    """Mock alert management system"""
    
    def __init__(self):
        self.rules = {}
        self.active_alerts = {}
        self.alert_history = []
        self.notification_callbacks = []
        
    def add_rule(self, rule: AlertRule):
        """Add alert rule"""
        self.rules[rule.rule_id] = rule
        logger.info(f"Added alert rule: {rule.rule_id}")
        
    def remove_rule(self, rule_id: str):
        """Remove alert rule"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"Removed alert rule: {rule_id}")
            
    def evaluate_metrics(self, metrics: Dict[str, MetricData]):
        """Evaluate metrics against alert rules"""
        for rule in self.rules.values():
            if rule.metric_name in metrics:
                metric = metrics[rule.metric_name]
                
                if rule.evaluate(metric.value):
                    self._trigger_alert(rule, metric)
                else:
                    self._resolve_alert(rule.rule_id)
                    
    def _trigger_alert(self, rule: AlertRule, metric: MetricData):
        """Trigger an alert"""
        alert_id = f"{rule.rule_id}_{int(time.time())}"
        
        # Check if alert is already active
        if rule.rule_id in self.active_alerts:
            return  # Don't create duplicate alerts
            
        alert = Alert(
            alert_id=alert_id,
            rule_id=rule.rule_id,
            metric_name=rule.metric_name,
            current_value=metric.value,
            threshold=rule.threshold,
            severity=rule.severity,
            triggered_at=datetime.now(),
            message=f"{rule.metric_name} is {metric.value} (threshold: {rule.threshold})"
        )
        
        self.active_alerts[rule.rule_id] = alert
        self.alert_history.append(alert)
        
        # Send notifications
        self._send_notifications(alert)
        
        logger.warning(f"Alert triggered: {alert.message}")
        
    def _resolve_alert(self, rule_id: str):
        """Resolve an active alert"""
        if rule_id in self.active_alerts:
            alert = self.active_alerts[rule_id]
            alert.resolve()
            del self.active_alerts[rule_id]
            
            logger.info(f"Alert resolved: {alert.alert_id}")
            
    def _send_notifications(self, alert: Alert):
        """Send alert notifications"""
        for callback in self.notification_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Error sending notification: {e}")
                
    def add_notification_callback(self, callback: Callable[[Alert], None]):
        """Add notification callback"""
        self.notification_callbacks.append(callback)
        
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        return list(self.active_alerts.values())
        
    def get_alert_history(self, hours: int = 24) -> List[Alert]:
        """Get alert history for specified hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            alert for alert in self.alert_history
            if alert.triggered_at >= cutoff_time
        ]


class TestPerformanceMonitoring:
    """Test suite for performance monitoring integration"""
    
    def setup_method(self):
        """Setup test environment"""
        self.system_monitor = MockSystemMonitor()
        self.app_monitor = MockApplicationMonitor()
        self.alert_manager = MockAlertManager()
        
        # Setup alert rules
        self.cpu_alert_rule = AlertRule(
            rule_id="high_cpu_usage",
            metric_name="cpu_usage_percent",
            condition=">",
            threshold=80.0,
            severity=AlertSeverity.WARNING
        )
        
        self.memory_alert_rule = AlertRule(
            rule_id="high_memory_usage",
            metric_name="memory_usage_percent",
            condition=">",
            threshold=90.0,
            severity=AlertSeverity.CRITICAL
        )
        
        self.response_time_rule = AlertRule(
            rule_id="slow_response_time",
            metric_name="response_time_api",
            condition=">",
            threshold=1000.0,  # 1 second
            severity=AlertSeverity.WARNING
        )
        
        # Add rules to alert manager
        self.alert_manager.add_rule(self.cpu_alert_rule)
        self.alert_manager.add_rule(self.memory_alert_rule)
        self.alert_manager.add_rule(self.response_time_rule)
        
        # Setup notification tracking
        self.notifications_received = []
        
        def notification_callback(alert: Alert):
            self.notifications_received.append(alert)
            
        self.alert_manager.add_notification_callback(notification_callback)
        
        logger.info("Performance monitoring test setup completed")
        
    async def teardown_method(self):
        """Cleanup test environment"""
        if hasattr(self, 'system_monitor'):
            self.system_monitor.stop_monitoring()
        logger.info("Performance monitoring test cleanup completed")
        
    @pytest.mark.asyncio
    async def test_system_monitoring_startup(self):
        """Test system monitoring startup and shutdown"""
        self.setup_method()  # Ensure setup is called
        # Start monitoring
        self.system_monitor.start_monitoring()
        assert self.system_monitor.monitoring is True
        
        # Wait for some metrics to be collected
        await asyncio.sleep(2.0)
        
        # Check that metrics are being collected
        current_metrics = self.system_monitor.get_current_metrics()
        assert len(current_metrics) > 0
        assert "cpu_usage_percent" in current_metrics
        assert "memory_usage_percent" in current_metrics
        
        # Stop monitoring
        self.system_monitor.stop_monitoring()
        assert self.system_monitor.monitoring is False
        
    @pytest.mark.asyncio
    async def test_metric_collection_and_storage(self):
        """Test metric collection and storage"""
        self.setup_method()  # Ensure setup is called
        # Start monitoring
        self.system_monitor.start_monitoring()
        
        # Wait for metrics collection
        await asyncio.sleep(3.0)
        
        # Check metric history
        cpu_history = self.system_monitor.get_metric_history("cpu_usage_percent", 5)
        assert len(cpu_history) > 0
        
        # Verify metric data structure
        for metric in cpu_history:
            assert isinstance(metric, MetricData)
            assert metric.metric_name == "cpu_usage_percent"
            assert metric.metric_type == MetricType.CPU_USAGE
            assert isinstance(metric.value, (int, float))
            assert isinstance(metric.timestamp, datetime)
            
    @pytest.mark.asyncio
    async def test_metric_statistics_calculation(self):
        """Test metric statistics calculation"""
        self.setup_method()  # Ensure setup is called
        # Start monitoring
        self.system_monitor.start_monitoring()
        
        # Wait for metrics collection
        await asyncio.sleep(3.0)
        
        # Get statistics
        stats = self.system_monitor.get_metric_statistics("cpu_usage_percent", 5)
        
        assert "count" in stats
        assert "min" in stats
        assert "max" in stats
        assert "mean" in stats
        assert "median" in stats
        assert "std_dev" in stats
        assert "p95" in stats
        assert "p99" in stats
        
        assert stats["count"] > 0
        assert stats["min"] <= stats["max"]
        assert stats["p95"] >= stats["median"]
        assert stats["p99"] >= stats["p95"]
        
    @pytest.mark.asyncio
    async def test_application_metrics_recording(self):
        """Test application metrics recording"""
        self.setup_method()  # Ensure setup is called
        # Record some API requests
        endpoints = ["/api/orders", "/api/portfolio", "/api/market-data"]
        
        for i, endpoint in enumerate(endpoints):
            response_time = 100 + i * 50  # Varying response times
            status_code = 200 if i < 2 else 500  # One error
            
            self.app_monitor.record_request(endpoint, response_time, status_code)
            
        # Record throughput metrics
        self.app_monitor.record_throughput("order_processor", 150.0)
        self.app_monitor.record_throughput("market_data_processor", 1000.0)
        
        # Record queue depths
        self.app_monitor.record_queue_depth("order_queue", 25)
        self.app_monitor.record_queue_depth("market_data_queue", 100)
        
        # Verify metrics were recorded
        assert self.app_monitor.total_requests == 3
        assert self.app_monitor.error_count == 1
        
        # Check error rate
        error_rate = self.app_monitor.get_error_rate()
        assert abs(error_rate - 33.33) < 0.1  # 1 error out of 3 requests
        
        # Check average response time
        avg_response_time = self.app_monitor.get_average_response_time()
        assert abs(avg_response_time - 150.0) < 0.1  # (100 + 150 + 200) / 3
        
    @pytest.mark.asyncio
    async def test_alert_rule_evaluation(self):
        """Test alert rule evaluation"""
        self.setup_method()  # Ensure setup is called
        # Create metrics that should trigger alerts
        high_cpu_metric = MetricData(
            metric_name="cpu_usage_percent",
            metric_type=MetricType.CPU_USAGE,
            value=85.0,  # Above 80% threshold
            timestamp=datetime.now()
        )
        
        high_memory_metric = MetricData(
            metric_name="memory_usage_percent",
            metric_type=MetricType.MEMORY_USAGE,
            value=95.0,  # Above 90% threshold
            timestamp=datetime.now()
        )
        
        normal_response_time = MetricData(
            metric_name="response_time_api",
            metric_type=MetricType.RESPONSE_TIME,
            value=500.0,  # Below 1000ms threshold
            timestamp=datetime.now()
        )
        
        # Evaluate metrics
        metrics = {
            "cpu_usage_percent": high_cpu_metric,
            "memory_usage_percent": high_memory_metric,
            "response_time_api": normal_response_time
        }
        
        self.alert_manager.evaluate_metrics(metrics)
        
        # Check active alerts
        active_alerts = self.alert_manager.get_active_alerts()
        assert len(active_alerts) == 2  # CPU and memory alerts
        
        # Verify alert details
        alert_rule_ids = [alert.rule_id for alert in active_alerts]
        assert "high_cpu_usage" in alert_rule_ids
        assert "high_memory_usage" in alert_rule_ids
        
        # Check notifications were sent
        assert len(self.notifications_received) == 2
        
    @pytest.mark.asyncio
    async def test_alert_resolution(self):
        """Test alert resolution"""
        self.setup_method()  # Ensure setup is called
        # First, trigger an alert
        high_cpu_metric = MetricData(
            metric_name="cpu_usage_percent",
            metric_type=MetricType.CPU_USAGE,
            value=85.0,
            timestamp=datetime.now()
        )
        
        self.alert_manager.evaluate_metrics({"cpu_usage_percent": high_cpu_metric})
        
        # Verify alert is active
        active_alerts = self.alert_manager.get_active_alerts()
        assert len(active_alerts) == 1
        assert active_alerts[0].rule_id == "high_cpu_usage"
        
        # Now send normal CPU metric
        normal_cpu_metric = MetricData(
            metric_name="cpu_usage_percent",
            metric_type=MetricType.CPU_USAGE,
            value=50.0,  # Below threshold
            timestamp=datetime.now()
        )
        
        self.alert_manager.evaluate_metrics({"cpu_usage_percent": normal_cpu_metric})
        
        # Verify alert is resolved
        active_alerts = self.alert_manager.get_active_alerts()
        assert len(active_alerts) == 0
        
    @pytest.mark.asyncio
    async def test_performance_threshold_monitoring(self):
        """Test performance threshold monitoring"""
        self.setup_method()  # Ensure setup is called
        # Start system monitoring
        self.system_monitor.start_monitoring()
        
        # Wait for initial metrics
        await asyncio.sleep(2.0)
        
        # Simulate high load scenario
        # Record high response times
        for i in range(10):
            self.app_monitor.record_request("/api/orders", 1500.0, 200)  # Slow responses
            
        # Create slow response time metric
        slow_response_metric = MetricData(
            metric_name="response_time_api",
            metric_type=MetricType.RESPONSE_TIME,
            value=1500.0,  # Above 1000ms threshold
            timestamp=datetime.now()
        )
        
        # Get current system metrics
        current_metrics = self.system_monitor.get_current_metrics()
        current_metrics["response_time_api"] = slow_response_metric
        
        # Evaluate all metrics
        self.alert_manager.evaluate_metrics(current_metrics)
        
        # Check if performance alerts were triggered
        active_alerts = self.alert_manager.get_active_alerts()
        response_time_alerts = [
            alert for alert in active_alerts 
            if alert.rule_id == "slow_response_time"
        ]
        
        assert len(response_time_alerts) > 0
        
    @pytest.mark.asyncio
    async def test_concurrent_monitoring(self):
        """Test concurrent monitoring operations"""
        self.setup_method()  # Ensure setup is called
        # Start system monitoring
        self.system_monitor.start_monitoring()
        
        # Create concurrent tasks
        async def simulate_api_load():
            """Simulate API load"""
            for i in range(50):
                endpoint = f"/api/endpoint_{i % 5}"
                response_time = 100 + (i % 10) * 50
                status_code = 200 if i % 10 != 9 else 500
                
                self.app_monitor.record_request(endpoint, response_time, status_code)
                await asyncio.sleep(0.01)
                
        async def simulate_throughput_monitoring():
            """Simulate throughput monitoring"""
            components = ["processor_1", "processor_2", "processor_3"]
            for i in range(20):
                component = components[i % len(components)]
                throughput = 100 + (i % 5) * 20
                
                self.app_monitor.record_throughput(component, throughput)
                await asyncio.sleep(0.05)
                
        async def simulate_queue_monitoring():
            """Simulate queue monitoring"""
            queues = ["order_queue", "market_data_queue", "notification_queue"]
            for i in range(30):
                queue = queues[i % len(queues)]
                depth = 10 + (i % 8) * 5
                
                self.app_monitor.record_queue_depth(queue, depth)
                await asyncio.sleep(0.03)
                
        # Run concurrent monitoring tasks
        await asyncio.gather(
            simulate_api_load(),
            simulate_throughput_monitoring(),
            simulate_queue_monitoring()
        )
        
        # Wait for system metrics collection
        await asyncio.sleep(2.0)
        
        # Verify all monitoring worked correctly
        assert self.app_monitor.total_requests == 50
        assert self.app_monitor.error_count == 5  # Every 10th request was an error
        
        # Check system metrics are still being collected
        current_metrics = self.system_monitor.get_current_metrics()
        assert len(current_metrics) > 0
        
    @pytest.mark.asyncio
    async def test_alert_history_tracking(self):
        """Test alert history tracking"""
        self.setup_method()  # Ensure setup is called
        # Trigger multiple alerts over time
        alerts_to_trigger = [
            ("cpu_usage_percent", 85.0),
            ("memory_usage_percent", 95.0),
            ("response_time_api", 1500.0)
        ]
        
        for metric_name, value in alerts_to_trigger:
            metric = MetricData(
                metric_name=metric_name,
                metric_type=MetricType.CPU_USAGE,  # Simplified for test
                value=value,
                timestamp=datetime.now()
            )
            
            self.alert_manager.evaluate_metrics({metric_name: metric})
            await asyncio.sleep(0.1)  # Small delay between alerts
            
        # Check alert history
        alert_history = self.alert_manager.get_alert_history(24)
        assert len(alert_history) == 3
        
        # Verify alert details
        rule_ids = [alert.rule_id for alert in alert_history]
        assert "high_cpu_usage" in rule_ids
        assert "high_memory_usage" in rule_ids
        assert "slow_response_time" in rule_ids
        
    @pytest.mark.asyncio
    async def test_performance_degradation_detection(self):
        """Test performance degradation detection"""
        self.setup_method()  # Ensure setup is called
        # Start monitoring
        self.system_monitor.start_monitoring()
        
        # Record baseline performance
        baseline_requests = 20
        for i in range(baseline_requests):
            self.app_monitor.record_request("/api/orders", 200.0, 200)  # Good performance
            
        baseline_avg = self.app_monitor.get_average_response_time()
        assert baseline_avg == 200.0
        
        # Simulate performance degradation
        degraded_requests = 10
        for i in range(degraded_requests):
            self.app_monitor.record_request("/api/orders", 800.0, 200)  # Degraded performance
            
        # Check if performance has degraded
        current_avg = self.app_monitor.get_average_response_time()
        assert current_avg > baseline_avg
        
        # The average should be between baseline and degraded values
        expected_avg = (baseline_avg * baseline_requests + 800.0 * degraded_requests) / (baseline_requests + degraded_requests)
        assert abs(current_avg - expected_avg) < 1.0
        
    @pytest.mark.asyncio
    async def test_resource_usage_monitoring(self):
        """Test resource usage monitoring"""
        self.setup_method()  # Ensure setup is called
        # Start system monitoring
        self.system_monitor.start_monitoring()
        
        # Wait for metrics collection
        await asyncio.sleep(3.0)
        
        # Get resource usage statistics
        cpu_stats = self.system_monitor.get_metric_statistics("cpu_usage_percent", 5)
        memory_stats = self.system_monitor.get_metric_statistics("memory_usage_percent", 5)
        
        # Verify resource monitoring
        assert cpu_stats["count"] > 0
        assert memory_stats["count"] > 0
        
        # Check that values are within reasonable ranges
        assert 0 <= cpu_stats["min"] <= 100
        assert 0 <= cpu_stats["max"] <= 100
        assert 0 <= memory_stats["min"] <= 100
        assert 0 <= memory_stats["max"] <= 100
        
        # Verify statistics consistency
        assert cpu_stats["min"] <= cpu_stats["mean"] <= cpu_stats["max"]
        assert memory_stats["min"] <= memory_stats["mean"] <= memory_stats["max"]


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])