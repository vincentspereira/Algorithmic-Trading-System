"""
Data Feed Monitoring System
Comprehensive monitoring and health checks for all data feed sources
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
import statistics

from nautilus_trader_engine.core.data_feeds import (
    DataFeedManager, 
    DataSource, 
    AssetClass,
    DataRequest,
    DataResponse
)
from nautilus_trader_engine.monitoring.metrics_collection import (
    MetricCollector, 
    MetricDefinition, 
    MetricType, 
    MetricCategory
)
from nautilus_trader_engine.monitoring.intelligent_alerting import (
    Alert, 
    AlertSeverity, 
    AlertCategory, 
    AlertRule,
    AnomalyDetector,
    ThresholdAnomalyDetector
)

logger = logging.getLogger(__name__)


@dataclass
class DataFeedHealthStatus:
    """Current health status of a data feed"""
    source: DataSource
    status: str  # healthy, degraded, unhealthy
    last_check: datetime
    success_rate: float
    avg_response_time: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    last_error: Optional[str] = None
    error_timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataFeedPerformanceMetrics:
    """Performance metrics for a data feed"""
    source: DataSource
    timestamp: datetime
    response_time: float
    data_points: int
    success: bool
    error_message: Optional[str] = None
    latency_percentiles: Dict[str, float] = field(default_factory=dict)


class DataFeedMonitor:
    """Main data feed monitoring system"""
    
    def __init__(self, data_feed_manager: DataFeedManager, 
                 metric_collector: MetricCollector):
        self.data_feed_manager = data_feed_manager
        self.metric_collector = metric_collector
        self.health_status = {}
        self.performance_history = defaultdict(deque)
        self.alert_rules = {}
        self.is_monitoring = False
        self.monitoring_task = None
        
        # Register metrics
        self._register_metrics()
        
        # Initialize health status for all sources
        for source in DataSource:
            self.health_status[source] = DataFeedHealthStatus(
                source=source,
                status="unknown",
                last_check=datetime.now(),
                success_rate=0.0,
                avg_response_time=0.0,
                total_requests=0,
                successful_requests=0,
                failed_requests=0
            )
    
    def _register_metrics(self):
        """Register data feed metrics with the metric collector"""
        metrics = [
            MetricDefinition(
                name="data_feed.success_rate",
                metric_type=MetricType.PERCENTAGE,
                category=MetricCategory.PERFORMANCE,
                description="Data feed success rate percentage",
                unit="percent"
            ),
            MetricDefinition(
                name="data_feed.response_time.avg",
                metric_type=MetricType.TIMER,
                category=MetricCategory.PERFORMANCE,
                description="Average data feed response time",
                unit="milliseconds"
            ),
            MetricDefinition(
                name="data_feed.requests.total",
                metric_type=MetricType.COUNTER,
                category=MetricCategory.PERFORMANCE,
                description="Total data feed requests",
                unit="count"
            ),
            MetricDefinition(
                name="data_feed.errors.total",
                metric_type=MetricType.COUNTER,
                category=MetricCategory.SYSTEM,
                description="Total data feed errors",
                unit="count"
            ),
            MetricDefinition(
                name="data_feed.availability",
                metric_type=MetricType.PERCENTAGE,
                category=MetricCategory.PERFORMANCE,
                description="Data feed availability percentage",
                unit="percent"
            )
        ]
        
        for metric in metrics:
            self.metric_collector.register_metric(metric)
    
    async def start_monitoring(self, interval_seconds: int = 60):
        """Start continuous monitoring of data feeds"""
        if self.is_monitoring:
            logger.warning("Data feed monitoring already running")
            return
        
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(
            self._monitoring_loop(interval_seconds)
        )
        logger.info(f"Started data feed monitoring (interval: {interval_seconds}s)")
    
    async def stop_monitoring(self):
        """Stop continuous monitoring"""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped data feed monitoring")
    
    async def _monitoring_loop(self, interval_seconds: int):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                await self.perform_health_checks()
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(interval_seconds)
    
    async def perform_health_checks(self) -> Dict[str, DataFeedHealthStatus]:
        """Perform health checks on all data feeds"""
        logger.info("Performing data feed health checks...")
        
        # Get detailed health report from data feed manager
        health_report = self.data_feed_manager.get_detailed_health_report()
        
        # Update individual source health status
        for source_name, source_health in health_report.get('sources', {}).items():
            try:
                # Find the corresponding DataSource enum
                source_enum = None
                for source in DataSource:
                    if source.value == source_name:
                        source_enum = source
                        break
                
                if source_enum:
                    # Update health status
                    self.health_status[source_enum] = DataFeedHealthStatus(
                        source=source_enum,
                        status=source_health.get('status', 'unknown'),
                        last_check=datetime.now(),
                        success_rate=source_health.get('success_rate', 0.0),
                        avg_response_time=source_health.get('avg_response_time', 0.0),
                        total_requests=source_health.get('total_checks', 0),
                        successful_requests=source_health.get('successful_checks', 0),
                        failed_requests=source_health.get('total_checks', 0) - source_health.get('successful_checks', 0)
                    )
                    
                    # Collect metrics
                    self._collect_metrics(source_enum, source_health)
                    
            except Exception as e:
                logger.error(f"Error updating health status for {source_name}: {e}")
        
        logger.info("Data feed health checks completed")
        return self.health_status
    
    def _collect_metrics(self, source: DataSource, health_data: Dict[str, Any]):
        """Collect metrics for a data source"""
        try:
            # Success rate
            success_rate = health_data.get('success_rate', 0.0) * 100
            self.metric_collector.collect_metric(
                "data_feed.success_rate",
                success_rate,
                tags={"source": source.value}
            )
            
            # Response time
            avg_response_time = health_data.get('avg_response_time', 0.0) * 1000  # Convert to milliseconds
            self.metric_collector.collect_metric(
                "data_feed.response_time.avg",
                avg_response_time,
                tags={"source": source.value}
            )
            
            # Total requests
            total_checks = health_data.get('total_checks', 0)
            self.metric_collector.collect_metric(
                "data_feed.requests.total",
                total_checks,
                tags={"source": source.value}
            )
            
            # Availability (based on success rate)
            self.metric_collector.collect_metric(
                "data_feed.availability",
                success_rate,  # Using success rate as availability
                tags={"source": source.value}
            )
            
        except Exception as e:
            logger.error(f"Error collecting metrics for {source.value}: {e}")
    
    async def test_data_feed_connectivity(self, source: DataSource, 
                                        test_symbol: str = "AAPL") -> DataFeedPerformanceMetrics:
        """Test connectivity to a specific data feed"""
        logger.info(f"Testing connectivity to {source.value}...")
        
        start_time = time.time()
        try:
            # Create a test request
            request = DataRequest(
                ticker=test_symbol,
                asset_class=AssetClass.STOCK,
                period="1d"
            )
            
            # Try to fetch data
            response = self.data_feed_manager._fetch_from_source(source, request)
            
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Create performance metrics
            metrics = DataFeedPerformanceMetrics(
                source=source,
                timestamp=datetime.now(),
                response_time=response_time,
                data_points=len(response.data) if response and response.data is not None else 0,
                success=response.success if response else False,
                error_message=response.error_message if response else "No response"
            )
            
            # Store in history
            self.performance_history[source].append(metrics)
            
            # Keep only last 1000 entries
            if len(self.performance_history[source]) > 1000:
                self.performance_history[source].popleft()
            
            if response and response.success:
                logger.info(f"✓ {source.value} connectivity test PASSED ({response_time:.2f}ms)")
            else:
                logger.warning(f"✗ {source.value} connectivity test FAILED: {response.error_message if response else 'No response'}")
            
            return metrics
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"✗ {source.value} connectivity test ERROR: {e}")
            
            metrics = DataFeedPerformanceMetrics(
                source=source,
                timestamp=datetime.now(),
                response_time=response_time,
                data_points=0,
                success=False,
                error_message=str(e)
            )
            
            # Store in history
            self.performance_history[source].append(metrics)
            
            # Keep only last 1000 entries
            if len(self.performance_history[source]) > 1000:
                self.performance_history[source].popleft()
            
            return metrics
    
    def get_health_status(self, source: Optional[DataSource] = None) -> Dict[DataSource, DataFeedHealthStatus]:
        """Get health status for data feeds"""
        if source:
            return {source: self.health_status.get(source, None)}
        return self.health_status.copy()
    
    def get_performance_history(self, source: DataSource, 
                              hours: int = 24) -> List[DataFeedPerformanceMetrics]:
        """Get performance history for a data source"""
        if source not in self.performance_history:
            return []
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            metrics for metrics in self.performance_history[source]
            if metrics.timestamp >= cutoff_time
        ]
    
    def get_overall_health_score(self) -> float:
        """Calculate overall health score across all data feeds"""
        if not self.health_status:
            return 0.0
        
        total_score = 0.0
        active_sources = 0
        
        for status in self.health_status.values():
            if status.status != "unknown":
                active_sources += 1
                if status.status == "healthy":
                    total_score += 100.0
                elif status.status == "degraded":
                    total_score += 50.0
                # unhealthy = 0.0
        
        return total_score / active_sources if active_sources > 0 else 0.0
    
    def generate_health_report(self) -> Dict[str, Any]:
        """Generate a comprehensive health report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "overall_health_score": self.get_overall_health_score(),
            "sources": {},
            "summary": {
                "total_sources": len(self.health_status),
                "healthy_sources": 0,
                "degraded_sources": 0,
                "unhealthy_sources": 0,
                "unknown_sources": 0
            }
        }
        
        for source, status in self.health_status.items():
            report["sources"][source.value] = {
                "status": status.status,
                "last_check": status.last_check.isoformat(),
                "success_rate": status.success_rate,
                "avg_response_time": status.avg_response_time,
                "total_requests": status.total_requests,
                "successful_requests": status.successful_requests,
                "failed_requests": status.failed_requests,
                "last_error": status.last_error
            }
            
            # Update summary
            if status.status == "healthy":
                report["summary"]["healthy_sources"] += 1
            elif status.status == "degraded":
                report["summary"]["degraded_sources"] += 1
            elif status.status == "unhealthy":
                report["summary"]["unhealthy_sources"] += 1
            else:
                report["summary"]["unknown_sources"] += 1
        
        return report


class DataFeedAlertManager:
    """Manages alerts for data feed issues"""
    
    def __init__(self, data_feed_monitor: DataFeedMonitor):
        self.data_feed_monitor = data_feed_monitor
        self.active_alerts = {}
        self.alert_history = deque(maxlen=1000)
        self.alert_rules = {}
        self._setup_default_alert_rules()
    
    def _setup_default_alert_rules(self):
        """Setup default alert rules for data feeds"""
        # Success rate alert rule
        success_rate_rule = AlertRule(
            rule_id="data_feed_success_rate",
            name="Data Feed Success Rate",
            description="Alert when data feed success rate drops below threshold",
            metric_name="data_feed.success_rate",
            condition="<",
            threshold_value=90.0,
            warning_threshold=95.0,
            critical_threshold=80.0,
            severity=AlertSeverity.HIGH,
            category=AlertCategory.PERFORMANCE,
            evaluation_window=timedelta(minutes=5),
            cooldown_period=timedelta(minutes=15)
        )
        
        # Response time alert rule
        response_time_rule = AlertRule(
            rule_id="data_feed_response_time",
            name="Data Feed Response Time",
            description="Alert when data feed response time exceeds threshold",
            metric_name="data_feed.response_time.avg",
            condition=">",
            threshold_value=5000.0,  # 5 seconds
            warning_threshold=2000.0,  # 2 seconds
            critical_threshold=10000.0,  # 10 seconds
            severity=AlertSeverity.MEDIUM,
            category=AlertCategory.PERFORMANCE,
            evaluation_window=timedelta(minutes=5),
            cooldown_period=timedelta(minutes=15)
        )
        
        # Availability alert rule
        availability_rule = AlertRule(
            rule_id="data_feed_availability",
            name="Data Feed Availability",
            description="Alert when data feed availability drops below threshold",
            metric_name="data_feed.availability",
            condition="<",
            threshold_value=95.0,
            warning_threshold=98.0,
            critical_threshold=90.0,
            severity=AlertSeverity.HIGH,
            category=AlertCategory.PERFORMANCE,
            evaluation_window=timedelta(minutes=5),
            cooldown_period=timedelta(minutes=15)
        )
        
        self.alert_rules = {
            "success_rate": success_rate_rule,
            "response_time": response_time_rule,
            "availability": availability_rule
        }
    
    def evaluate_alerts(self) -> List[Alert]:
        """Evaluate all alert rules and generate alerts"""
        new_alerts = []
        
        # Get current health status
        health_status = self.data_feed_monitor.get_health_status()
        
        # Check each data source
        for source, status in health_status.items():
            if status.status == "unknown":
                continue
            
            # Check for degraded or unhealthy status
            if status.status in ["degraded", "unhealthy"]:
                severity = AlertSeverity.HIGH if status.status == "unhealthy" else AlertSeverity.MEDIUM
                
                alert = Alert(
                    alert_id=f"data_feed_{source.value}_{datetime.now().timestamp()}",
                    title=f"Data Feed {source.value} is {status.status}",
                    description=f"Data feed {source.value} is reporting {status.status} status. "
                              f"Success rate: {status.success_rate:.2%}, "
                              f"Avg response time: {status.avg_response_time:.2f}s",
                    severity=severity,
                    category=AlertCategory.PERFORMANCE,
                    source="data_feed_monitor",
                    metric_name=f"data_feed.{source.value}.status",
                    metric_value=1.0 if status.status == "healthy" else 0.5 if status.status == "degraded" else 0.0,
                    tags={"source": source.value, "status": status.status},
                    metadata={
                        "success_rate": status.success_rate,
                        "avg_response_time": status.avg_response_time,
                        "total_requests": status.total_requests
                    }
                )
                
                new_alerts.append(alert)
                self.active_alerts[alert.alert_id] = alert
        
        return new_alerts
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str):
        """Acknowledge an alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = "acknowledged"
            alert.acknowledged_by = acknowledged_by
            alert.acknowledged_at = datetime.now()
            alert.updated_at = datetime.now()
    
    def resolve_alert(self, alert_id: str):
        """Resolve an alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = "resolved"
            alert.resolved_at = datetime.now()
            alert.updated_at = datetime.now()
            
            # Move to history
            self.alert_history.append(alert)
            del self.active_alerts[alert_id]
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, hours: int = 24) -> List[Alert]:
        """Get alert history for specified time period"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            alert for alert in self.alert_history
            if alert.created_at >= cutoff_time
        ]


# Example usage and testing
async def example_usage():
    """Example usage of the Data Feed Monitoring System"""
    
    # Initialize components
    data_feed_manager = DataFeedManager()
    
    # Create a simple metric collector for testing
    class SimpleMetricCollector(MetricCollector):
        def __init__(self):
            super().__init__()
            self.collected_metrics = []
        
        def collect_metric(self, name: str, value: float, tags: Dict[str, str] = None, metadata: Dict[str, Any] = None) -> bool:
            self.collected_metrics.append({
                "name": name,
                "value": value,
                "tags": tags or {},
                "timestamp": datetime.now()
            })
            return True
    
    metric_collector = SimpleMetricCollector()
    
    # Initialize monitor
    monitor = DataFeedMonitor(data_feed_manager, metric_collector)
    
    print("Starting data feed monitoring...")
    await monitor.start_monitoring(interval_seconds=30)
    
    # Perform initial health checks
    print("Performing initial health checks...")
    await monitor.perform_health_checks()
    
    # Test connectivity to a few sources
    print("Testing connectivity...")
    await monitor.test_data_feed_connectivity(DataSource.YAHOO_FINANCE)
    await monitor.test_data_feed_connectivity(DataSource.ALPHA_VANTAGE)
    
    # Generate health report
    report = monitor.generate_health_report()
    print(f"\n=== Data Feed Health Report ===")
    print(f"Overall Health Score: {report['overall_health_score']:.2f}%")
    print(f"Total Sources: {report['summary']['total_sources']}")
    print(f"Healthy Sources: {report['summary']['healthy_sources']}")
    print(f"Degraded Sources: {report['summary']['degraded_sources']}")
    print(f"Unhealthy Sources: {report['summary']['unhealthy_sources']}")
    
    # Initialize alert manager
    alert_manager = DataFeedAlertManager(monitor)
    
    # Evaluate alerts
    alerts = alert_manager.evaluate_alerts()
    print(f"\n=== Active Alerts ===")
    print(f"Found {len(alerts)} active alerts")
    
    for alert in alerts:
        print(f"- {alert.title} ({alert.severity.value})")
        print(f"  {alert.description}")
    
    # Stop monitoring
    print("\nStopping monitoring...")
    await monitor.stop_monitoring()


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(example_usage())