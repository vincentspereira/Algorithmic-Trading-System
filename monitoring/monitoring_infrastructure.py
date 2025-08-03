#!/usr/bin/env python3
"""
Comprehensive Monitoring Infrastructure
Provides enterprise-grade monitoring, metrics collection, and observability
for the trading system with real-time dashboards and alerting.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Callable, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import threading
import psutil
import os
import sys
from pathlib import Path

# Monitoring and metrics
from prometheus_client import Counter, Histogram, Gauge, Summary, CollectorRegistry, generate_latest
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "COUNTER"
    GAUGE = "GAUGE"
    HISTOGRAM = "HISTOGRAM"
    SUMMARY = "SUMMARY"

class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class ComponentStatus(Enum):
    """Component health status"""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"

@dataclass
class MetricDefinition:
    """Metric definition"""
    name: str
    metric_type: MetricType
    description: str
    labels: List[str] = field(default_factory=list)
    buckets: Optional[List[float]] = None  # For histograms
    unit: str = ""
    namespace: str = "trading_system"

@dataclass
class Alert:
    """Alert definition"""
    alert_id: str
    name: str
    severity: AlertSeverity
    message: str
    component: str
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class HealthCheck:
    """Health check definition"""
    name: str
    component: str
    status: ComponentStatus
    message: str
    timestamp: datetime
    response_time_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SystemMetrics:
    """System performance metrics"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    network_bytes_sent: int
    network_bytes_recv: int
    load_average: List[float]
    process_count: int
    thread_count: int

class MetricsCollector:
    """Prometheus metrics collector"""
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()
        self.metrics: Dict[str, Any] = {}
        self.metric_definitions: Dict[str, MetricDefinition] = {}
        
        # Initialize core system metrics
        self._initialize_core_metrics()
        
        logger.info("Metrics collector initialized")
    
    def _initialize_core_metrics(self):
        """Initialize core system metrics"""
        core_metrics = [
            MetricDefinition(
                name="system_cpu_percent",
                metric_type=MetricType.GAUGE,
                description="System CPU usage percentage",
                unit="percent"
            ),
            MetricDefinition(
                name="system_memory_percent",
                metric_type=MetricType.GAUGE,
                description="System memory usage percentage",
                unit="percent"
            ),
            MetricDefinition(
                name="system_disk_percent",
                metric_type=MetricType.GAUGE,
                description="System disk usage percentage",
                unit="percent"
            ),
            MetricDefinition(
                name="http_requests_total",
                metric_type=MetricType.COUNTER,
                description="Total HTTP requests",
                labels=["method", "endpoint", "status"]
            ),
            MetricDefinition(
                name="http_request_duration_seconds",
                metric_type=MetricType.HISTOGRAM,
                description="HTTP request duration",
                labels=["method", "endpoint"],
                buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
                unit="seconds"
            ),
            MetricDefinition(
                name="trading_orders_total",
                metric_type=MetricType.COUNTER,
                description="Total trading orders",
                labels=["order_type", "status", "symbol"]
            ),
            MetricDefinition(
                name="security_events_total",
                metric_type=MetricType.COUNTER,
                description="Total security events",
                labels=["event_type", "severity", "component"]
            )
        ]
        
        for metric_def in core_metrics:
            self.register_metric(metric_def)
    
    def register_metric(self, metric_def: MetricDefinition):
        """Register a new metric"""
        self.metric_definitions[metric_def.name] = metric_def
        
        full_name = f"{metric_def.namespace}_{metric_def.name}"
        
        if metric_def.metric_type == MetricType.COUNTER:
            metric = Counter(
                full_name,
                metric_def.description,
                labelnames=metric_def.labels,
                registry=self.registry
            )
        elif metric_def.metric_type == MetricType.GAUGE:
            metric = Gauge(
                full_name,
                metric_def.description,
                labelnames=metric_def.labels,
                registry=self.registry
            )
        elif metric_def.metric_type == MetricType.HISTOGRAM:
            metric = Histogram(
                full_name,
                metric_def.description,
                labelnames=metric_def.labels,
                buckets=metric_def.buckets or [0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0],
                registry=self.registry
            )
        elif metric_def.metric_type == MetricType.SUMMARY:
            metric = Summary(
                full_name,
                metric_def.description,
                labelnames=metric_def.labels,
                registry=self.registry
            )
        else:
            raise ValueError(f"Unknown metric type: {metric_def.metric_type}")
        
        self.metrics[metric_def.name] = metric
        logger.info(f"Registered metric: {metric_def.name}", metric_type=metric_def.metric_type.value)
    
    def increment_counter(self, name: str, labels: Optional[Dict[str, str]] = None, value: float = 1.0):
        """Increment a counter metric"""
        if name not in self.metrics:
            logger.warning(f"Metric not found: {name}")
            return
        
        metric = self.metrics[name]
        if labels:
            metric.labels(**labels).inc(value)
        else:
            metric.inc(value)
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric value"""
        if name not in self.metrics:
            logger.warning(f"Metric not found: {name}")
            return
        
        metric = self.metrics[name]
        if labels:
            metric.labels(**labels).set(value)
        else:
            metric.set(value)
    
    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Observe a histogram metric"""
        if name not in self.metrics:
            logger.warning(f"Metric not found: {name}")
            return
        
        metric = self.metrics[name]
        if labels:
            metric.labels(**labels).observe(value)
        else:
            metric.observe(value)
    
    def get_metrics_text(self) -> str:
        """Get metrics in Prometheus text format"""
        return generate_latest(self.registry).decode('utf-8')

class SystemMonitor:
    """System performance monitor"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.monitoring = False
        self.monitor_thread = None
        self.update_interval = 10  # seconds
        
        logger.info("System monitor initialized")
    
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
            self.monitor_thread.join(timeout=5)
        
        logger.info("System monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                metrics = self.collect_system_metrics()
                self._update_prometheus_metrics(metrics)
                time.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.update_interval)
    
    def collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory metrics
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_gb = memory.used / (1024**3)
        memory_total_gb = memory.total / (1024**3)
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        disk_used_gb = disk.used / (1024**3)
        disk_total_gb = disk.total / (1024**3)
        
        # Network metrics
        network = psutil.net_io_counters()
        network_bytes_sent = network.bytes_sent
        network_bytes_recv = network.bytes_recv
        
        # Load average (Unix-like systems)
        try:
            load_average = list(os.getloadavg())
        except (OSError, AttributeError):
            load_average = [0.0, 0.0, 0.0]
        
        # Process metrics
        process_count = len(psutil.pids())
        try:
            thread_count = sum(p.num_threads() for p in psutil.process_iter(['num_threads']) if p.info['num_threads'])
        except:
            thread_count = 0
        
        return SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used_gb=memory_used_gb,
            memory_total_gb=memory_total_gb,
            disk_percent=disk_percent,
            disk_used_gb=disk_used_gb,
            disk_total_gb=disk_total_gb,
            network_bytes_sent=network_bytes_sent,
            network_bytes_recv=network_bytes_recv,
            load_average=load_average,
            process_count=process_count,
            thread_count=thread_count
        )
    
    def _update_prometheus_metrics(self, metrics: SystemMetrics):
        """Update Prometheus metrics with system data"""
        self.metrics_collector.set_gauge("system_cpu_percent", metrics.cpu_percent)
        self.metrics_collector.set_gauge("system_memory_percent", metrics.memory_percent)
        self.metrics_collector.set_gauge("system_disk_percent", metrics.disk_percent)

class HealthChecker:
    """Component health checker"""
    
    def __init__(self):
        self.health_checks: Dict[str, Callable] = {}
        self.health_status: Dict[str, HealthCheck] = {}
        
        # Register default health checks
        self._register_default_checks()
        
        logger.info("Health checker initialized")
    
    def _register_default_checks(self):
        """Register default health checks"""
        self.register_health_check("system_resources", self._check_system_resources)
        self.register_health_check("disk_space", self._check_disk_space)
        self.register_health_check("memory_usage", self._check_memory_usage)
    
    def register_health_check(self, name: str, check_func: Callable):
        """Register a health check function"""
        self.health_checks[name] = check_func
        logger.info(f"Registered health check: {name}")
    
    async def run_health_checks(self) -> Dict[str, HealthCheck]:
        """Run all health checks"""
        results = {}
        
        for name, check_func in self.health_checks.items():
            try:
                start_time = time.time()
                result = await self._run_check(check_func)
                response_time = (time.time() - start_time) * 1000
                
                health_check = HealthCheck(
                    name=name,
                    component=name,
                    status=result.get('status', ComponentStatus.UNKNOWN),
                    message=result.get('message', 'No message'),
                    timestamp=datetime.now(),
                    response_time_ms=response_time,
                    metadata=result.get('metadata', {})
                )
                
                results[name] = health_check
                self.health_status[name] = health_check
                
            except Exception as e:
                health_check = HealthCheck(
                    name=name,
                    component=name,
                    status=ComponentStatus.UNHEALTHY,
                    message=f"Health check failed: {str(e)}",
                    timestamp=datetime.now(),
                    response_time_ms=0,
                    metadata={'error': str(e)}
                )
                
                results[name] = health_check
                self.health_status[name] = health_check
                
                logger.error(f"Health check failed: {name}", error=str(e))
        
        return results
    
    async def _run_check(self, check_func: Callable) -> Dict[str, Any]:
        """Run a single health check"""
        if asyncio.iscoroutinefunction(check_func):
            return await check_func()
        else:
            return check_func()
    
    def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resource availability"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_percent = psutil.virtual_memory().percent
        
        if cpu_percent > 90 or memory_percent > 90:
            return {
                'status': ComponentStatus.UNHEALTHY,
                'message': f'High resource usage: CPU {cpu_percent}%, Memory {memory_percent}%',
                'metadata': {'cpu_percent': cpu_percent, 'memory_percent': memory_percent}
            }
        elif cpu_percent > 70 or memory_percent > 70:
            return {
                'status': ComponentStatus.DEGRADED,
                'message': f'Moderate resource usage: CPU {cpu_percent}%, Memory {memory_percent}%',
                'metadata': {'cpu_percent': cpu_percent, 'memory_percent': memory_percent}
            }
        else:
            return {
                'status': ComponentStatus.HEALTHY,
                'message': f'Resource usage normal: CPU {cpu_percent}%, Memory {memory_percent}%',
                'metadata': {'cpu_percent': cpu_percent, 'memory_percent': memory_percent}
            }
    
    def _check_disk_space(self) -> Dict[str, Any]:
        """Check disk space availability"""
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        
        if disk_percent > 95:
            return {
                'status': ComponentStatus.UNHEALTHY,
                'message': f'Critical disk usage: {disk_percent:.1f}%',
                'metadata': {'disk_percent': disk_percent}
            }
        elif disk_percent > 85:
            return {
                'status': ComponentStatus.DEGRADED,
                'message': f'High disk usage: {disk_percent:.1f}%',
                'metadata': {'disk_percent': disk_percent}
            }
        else:
            return {
                'status': ComponentStatus.HEALTHY,
                'message': f'Disk usage normal: {disk_percent:.1f}%',
                'metadata': {'disk_percent': disk_percent}
            }
    
    def _check_memory_usage(self) -> Dict[str, Any]:
        """Check memory usage details"""
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        if memory.percent > 95 or swap.percent > 80:
            return {
                'status': ComponentStatus.UNHEALTHY,
                'message': f'Critical memory usage: RAM {memory.percent}%, Swap {swap.percent}%',
                'metadata': {
                    'memory_percent': memory.percent,
                    'swap_percent': swap.percent,
                    'memory_available_gb': memory.available / (1024**3)
                }
            }
        elif memory.percent > 80 or swap.percent > 50:
            return {
                'status': ComponentStatus.DEGRADED,
                'message': f'High memory usage: RAM {memory.percent}%, Swap {swap.percent}%',
                'metadata': {
                    'memory_percent': memory.percent,
                    'swap_percent': swap.percent,
                    'memory_available_gb': memory.available / (1024**3)
                }
            }
        else:
            return {
                'status': ComponentStatus.HEALTHY,
                'message': f'Memory usage normal: RAM {memory.percent}%, Swap {swap.percent}%',
                'metadata': {
                    'memory_percent': memory.percent,
                    'swap_percent': swap.percent,
                    'memory_available_gb': memory.available / (1024**3)
                }
            }

class AlertManager:
    """Alert management system"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.alerts: Dict[str, Alert] = {}
        self.alert_rules: List[Dict[str, Any]] = []
        self.alert_handlers: Dict[str, Callable] = {}
        self.notification_channels: Dict[str, Callable] = {}
        
        # Load alert rules
        self._load_alert_rules()
        
        logger.info("Alert manager initialized")
    
    def _load_alert_rules(self):
        """Load alert rules from configuration"""
        # Default alert rules
        self.alert_rules = [
            {
                'name': 'high_cpu_usage',
                'condition': 'system_cpu_percent > 80',
                'severity': 'WARNING',
                'message': 'High CPU usage detected'
            },
            {
                'name': 'high_memory_usage',
                'condition': 'system_memory_percent > 85',
                'severity': 'WARNING',
                'message': 'High memory usage detected'
            },
            {
                'name': 'disk_space_low',
                'condition': 'system_disk_percent > 90',
                'severity': 'CRITICAL',
                'message': 'Disk space critically low'
            }
        ]
        logger.info("Loaded default alert rules")
    
    def register_alert_handler(self, alert_type: str, handler: Callable):
        """Register an alert handler"""
        self.alert_handlers[alert_type] = handler
        logger.info(f"Registered alert handler: {alert_type}")
    
    def register_notification_channel(self, channel_name: str, handler: Callable):
        """Register a notification channel"""
        self.notification_channels[channel_name] = handler
        logger.info(f"Registered notification channel: {channel_name}")
    
    async def create_alert(self, name: str, severity: AlertSeverity, message: str, 
                          component: str, labels: Optional[Dict[str, str]] = None,
                          metadata: Optional[Dict[str, Any]] = None) -> Alert:
        """Create a new alert"""
        alert_id = str(uuid.uuid4())
        
        alert = Alert(
            alert_id=alert_id,
            name=name,
            severity=severity,
            message=message,
            component=component,
            timestamp=datetime.now(),
            labels=labels or {},
            metadata=metadata or {}
        )
        
        self.alerts[alert_id] = alert
        
        # Update metrics
        self.metrics_collector.increment_counter(
            "security_events_total",
            labels={
                "event_type": "alert_created",
                "severity": severity.value.lower(),
                "component": component
            }
        )
        
        # Send notifications
        await self._send_notifications(alert)
        
        logger.info(f"Alert created: {name}", alert_id=alert_id, severity=severity.value)
        return alert
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        if alert_id not in self.alerts:
            return False
        
        alert = self.alerts[alert_id]
        alert.resolved = True
        alert.resolved_at = datetime.now()
        
        # Update metrics
        self.metrics_collector.increment_counter(
            "security_events_total",
            labels={
                "event_type": "alert_resolved",
                "severity": alert.severity.value.lower(),
                "component": alert.component
            }
        )
        
        logger.info(f"Alert resolved: {alert.name}", alert_id=alert_id)
        return True
    
    async def _send_notifications(self, alert: Alert):
        """Send alert notifications"""
        for channel_name, handler in self.notification_channels.items():
            try:
                await self._call_handler(handler, alert)
            except Exception as e:
                logger.error(f"Failed to send notification via {channel_name}: {e}")
    
    async def _call_handler(self, handler: Callable, alert: Alert):
        """Call a handler function"""
        if asyncio.iscoroutinefunction(handler):
            await handler(alert)
        else:
            handler(alert)
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        return [alert for alert in self.alerts.values() if not alert.resolved]
    
    def get_alert_summary(self) -> Dict[str, int]:
        """Get alert summary by severity"""
        active_alerts = self.get_active_alerts()
        summary = {severity.value: 0 for severity in AlertSeverity}
        
        for alert in active_alerts:
            summary[alert.severity.value] += 1
        
        return summary

class MonitoringInfrastructure:
    """Main monitoring infrastructure orchestrator"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Initialize components
        self.metrics_collector = MetricsCollector()
        self.system_monitor = SystemMonitor(self.metrics_collector)
        self.health_checker = HealthChecker()
        self.alert_manager = AlertManager(self.metrics_collector)
        
        # State
        self.running = False
        self.monitoring_tasks: List[asyncio.Task] = []
        
        # Setup default notification handlers
        self._setup_default_handlers()
        
        logger.info("Monitoring infrastructure initialized")
    
    def _setup_default_handlers(self):
        """Setup default alert handlers"""
        async def log_alert_handler(alert: Alert):
            """Log alert to structured logs"""
            logger.warning(
                f"ALERT: {alert.name}",
                alert_id=alert.alert_id,
                severity=alert.severity.value,
                component=alert.component,
                message=alert.message,
                labels=alert.labels,
                metadata=alert.metadata
            )
        
        self.alert_manager.register_notification_channel("logging", log_alert_handler)
    
    async def start(self):
        """Start monitoring infrastructure"""
        if self.running:
            return
        
        self.running = True
        
        # Start system monitoring
        self.system_monitor.start_monitoring()
        
        # Start periodic tasks
        self.monitoring_tasks = [
            asyncio.create_task(self._health_check_loop()),
            asyncio.create_task(self._alert_evaluation_loop()),
            asyncio.create_task(self._metrics_cleanup_loop())
        ]
        
        logger.info("Monitoring infrastructure started")
    
    async def stop(self):
        """Stop monitoring infrastructure"""
        if not self.running:
            return
        
        self.running = False
        
        # Stop system monitoring
        self.system_monitor.stop_monitoring()
        
        # Cancel monitoring tasks
        for task in self.monitoring_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)
        
        logger.info("Monitoring infrastructure stopped")
    
    async def _health_check_loop(self):
        """Periodic health check loop"""
        while self.running:
            try:
                await self.health_checker.run_health_checks()
                await asyncio.sleep(30)  # Check every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(30)
    
    async def _alert_evaluation_loop(self):
        """Periodic alert evaluation loop"""
        while self.running:
            try:
                await self._evaluate_alert_rules()
                await asyncio.sleep(60)  # Evaluate every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in alert evaluation loop: {e}")
                await asyncio.sleep(60)
    
    async def _metrics_cleanup_loop(self):
        """Periodic metrics cleanup loop"""
        while self.running:
            try:
                await self._cleanup_old_data()
                await asyncio.sleep(3600)  # Cleanup every hour
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics cleanup loop: {e}")
                await asyncio.sleep(3600)
    
    async def _evaluate_alert_rules(self):
        """Evaluate alert rules against current metrics"""
        system_metrics = self.system_monitor.collect_system_metrics()
        
        for rule in self.alert_manager.alert_rules:
            try:
                condition = rule['condition']
                
                # Simple condition evaluation
                if 'system_cpu_percent > 80' in condition and system_metrics.cpu_percent > 80:
                    await self.alert_manager.create_alert(
                        name=rule['name'],
                        severity=AlertSeverity(rule['severity']),
                        message=f"{rule['message']}: {system_metrics.cpu_percent:.1f}%",
                        component="system_monitor",
                        metadata={'cpu_percent': system_metrics.cpu_percent}
                    )
                
                elif 'system_memory_percent > 85' in condition and system_metrics.memory_percent > 85:
                    await self.alert_manager.create_alert(
                        name=rule['name'],
                        severity=AlertSeverity(rule['severity']),
                        message=f"{rule['message']}: {system_metrics.memory_percent:.1f}%",
                        component="system_monitor",
                        metadata={'memory_percent': system_metrics.memory_percent}
                    )
                
                elif 'system_disk_percent > 90' in condition and system_metrics.disk_percent > 90:
                    await self.alert_manager.create_alert(
                        name=rule['name'],
                        severity=AlertSeverity(rule['severity']),
                        message=f"{rule['message']}: {system_metrics.disk_percent:.1f}%",
                        component="system_monitor",
                        metadata={'disk_percent': system_metrics.disk_percent}
                    )
                    
            except Exception as e:
                logger.error(f"Error evaluating alert rule {rule['name']}: {e}")
    
    async def _cleanup_old_data(self):
        """Cleanup old monitoring data"""
        # Remove resolved alerts older than 24 hours
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        alerts_to_remove = []
        for alert_id, alert in self.alert_manager.alerts.items():
            if alert.resolved and alert.resolved_at and alert.resolved_at < cutoff_time:
                alerts_to_remove.append(alert_id)
        
        for alert_id in alerts_to_remove:
            del self.alert_manager.alerts[alert_id]
        
        if alerts_to_remove:
            logger.info(f"Cleaned up {len(alerts_to_remove)} old alerts")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        health_checks = self.health_checker.health_status
        active_alerts = self.alert_manager.get_active_alerts()
        alert_summary = self.alert_manager.get_alert_summary()
        
        # Determine overall status
        overall_status = ComponentStatus.HEALTHY
        if any(check.status == ComponentStatus.UNHEALTHY for check in health_checks.values()):
            overall_status = ComponentStatus.UNHEALTHY
        elif any(check.status == ComponentStatus.DEGRADED for check in health_checks.values()):
            overall_status = ComponentStatus.DEGRADED
        
        return {
            'overall_status': overall_status.value,
            'timestamp': datetime.now().isoformat(),
            'health_checks': {
                name: {
                    'status': check.status.value,
                    'message': check.message,
                    'response_time_ms': check.response_time_ms,
                    'timestamp': check.timestamp.isoformat()
                }
                for name, check in health_checks.items()
            },
            'alerts': {
                'active_count': len(active_alerts),
                'summary': alert_summary,
                'recent_alerts': [
                    {
                        'name': alert.name,
                        'severity': alert.severity.value,
                        'component': alert.component,
                        'message': alert.message,
                        'timestamp': alert.timestamp.isoformat()
                    }
                    for alert in sorted(active_alerts, key=lambda x: x.timestamp, reverse=True)[:5]
                ]
            },
            'metrics': {
                'collection_enabled': True,
                'system_monitoring': self.system_monitor.monitoring
            }
        }
    
    def get_metrics_endpoint(self) -> str:
        """Get Prometheus metrics in text format"""
        return self.metrics_collector.get_metrics_text()

# Global monitoring instance
_monitoring_instance: Optional[MonitoringInfrastructure] = None

def get_monitoring_instance() -> MonitoringInfrastructure:
    """Get global monitoring instance"""
    global _monitoring_instance
    if _monitoring_instance is None:
        _monitoring_instance = MonitoringInfrastructure()
    return _monitoring_instance

async def initialize_monitoring(config: Optional[Dict[str, Any]] = None) -> MonitoringInfrastructure:
    """Initialize and start monitoring infrastructure"""
    global _monitoring_instance
    _monitoring_instance = MonitoringInfrastructure(config)
    await _monitoring_instance.start()
    return _monitoring_instance

async def shutdown_monitoring():
    """Shutdown monitoring infrastructure"""
    global _monitoring_instance
    if _monitoring_instance:
        await _monitoring_instance.stop()
        _monitoring_instance = None

if __name__ == "__main__":
    # Example usage
    async def main():
        infrastructure = MonitoringInfrastructure()
        
        try:
            await infrastructure.start()
            
            # Example metrics
            infrastructure.metrics_collector.increment_counter("http_requests_total", 
                                                             {"method": "GET", "endpoint": "/api/test", "status": "200"})
            
            # Keep running for demonstration
            await asyncio.sleep(30)
            
        finally:
            await infrastructure.stop()
    
    asyncio.run(main())