"""
Dashboard metrics collector for dependency management system.
Collects and exports metrics for visualization in Grafana.
"""

import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Summary
)

# Dependency Update Metrics
DEPENDENCY_UPDATES = Counter(
    'dependency_updates_total',
    'Total number of dependency updates',
    ['tier', 'dependency', 'update_type']
)

UPDATE_CHECK_DURATION = Histogram(
    'dependency_update_check_duration_seconds',
    'Time spent checking for updates',
    ['tier']
)

# Security Metrics
SECURITY_VULNERABILITIES = Counter(
    'dependency_vulnerabilities_total',
    'Total number of security vulnerabilities found',
    ['tier', 'dependency', 'severity']
)

SECURITY_SCAN_DURATION = Histogram(
    'dependency_security_scan_duration_seconds',
    'Time spent scanning for security vulnerabilities',
    ['tier']
)

# Performance Metrics
PERFORMANCE_SCORE = Gauge(
    'dependency_performance_score',
    'Overall performance score for dependencies',
    ['tier', 'dependency']
)

RESOURCE_USAGE = Gauge(
    'dependency_resource_usage',
    'Resource usage by type',
    ['tier', 'dependency', 'resource_type']
)

OPERATION_LATENCY = Histogram(
    'dependency_operation_latency_seconds',
    'Latency of dependency operations',
    ['tier', 'operation']
)

# Error Metrics
ERROR_COUNT = Counter(
    'dependency_errors_total',
    'Total number of errors by type',
    ['tier', 'error_type', 'severity']
)

ERROR_RECOVERY_TIME = Histogram(
    'dependency_error_recovery_seconds',
    'Time taken to recover from errors',
    ['error_type']
)

# Health Metrics
HEALTH_STATUS = Gauge(
    'dependency_health_status',
    'Health status by component',
    ['component']
)

API_REQUEST_COUNT = Counter(
    'dependency_api_requests_total',
    'Total number of API requests',
    ['endpoint', 'status']
)

API_RESPONSE_TIME = Histogram(
    'dependency_api_response_seconds',
    'API response time in seconds',
    ['endpoint']
)

@dataclass
class DependencyMetrics:
    """Holds metrics for a dependency"""
    name: str
    tier: str
    version: str
    update_available: bool
    vulnerability_count: int
    performance_score: float
    resource_usage: Dict[str, float]
    error_count: int
    last_check: datetime
    last_scan: datetime

class MetricsCollector:
    """Collects and exports metrics for dashboards"""
    
    def __init__(self):
        self.last_collection: Dict[str, datetime] = {}
        
    def record_update_check(
        self,
        tier: str,
        dependency: str,
        has_update: bool,
        duration: float
    ) -> None:
        """Record metrics for an update check"""
        update_type = "available" if has_update else "up_to_date"
        DEPENDENCY_UPDATES.labels(
            tier=tier,
            dependency=dependency,
            update_type=update_type
        ).inc()
        
        UPDATE_CHECK_DURATION.labels(tier=tier).observe(duration)
        
    def record_security_scan(
        self,
        tier: str,
        dependency: str,
        vulnerabilities: List[Dict[str, Any]],
        duration: float
    ) -> None:
        """Record metrics for a security scan"""
        for vuln in vulnerabilities:
            SECURITY_VULNERABILITIES.labels(
                tier=tier,
                dependency=dependency,
                severity=vuln["severity"]
            ).inc()
            
        SECURITY_SCAN_DURATION.labels(tier=tier).observe(duration)
        
    def record_performance_metrics(
        self,
        tier: str,
        dependency: str,
        metrics: Dict[str, Any]
    ) -> None:
        """Record performance metrics"""
        # Calculate performance score (0-100)
        cpu_score = max(0, 100 - metrics["cpu_usage"])
        memory_score = max(0, 100 - (metrics["memory_usage"] / 10))  # Assuming GB
        io_score = max(0, 100 - (sum(metrics["disk_io"].values()) / 100))  # Assuming MB/s
        
        score = (cpu_score + memory_score + io_score) / 3
        PERFORMANCE_SCORE.labels(tier=tier, dependency=dependency).set(score)
        
        # Record resource usage
        for resource_type, value in {
            "cpu": metrics["cpu_usage"],
            "memory": metrics["memory_usage"],
            "disk_read": metrics["disk_io"]["read"],
            "disk_write": metrics["disk_io"]["write"]
        }.items():
            RESOURCE_USAGE.labels(
                tier=tier,
                dependency=dependency,
                resource_type=resource_type
            ).set(value)
            
    def record_operation_latency(
        self,
        tier: str,
        operation: str,
        duration: float
    ) -> None:
        """Record operation latency"""
        OPERATION_LATENCY.labels(
            tier=tier,
            operation=operation
        ).observe(duration)
        
    def record_error(
        self,
        tier: str,
        error_type: str,
        severity: str,
        recovery_time: Optional[float] = None
    ) -> None:
        """Record error metrics"""
        ERROR_COUNT.labels(
            tier=tier,
            error_type=error_type,
            severity=severity
        ).inc()
        
        if recovery_time is not None:
            ERROR_RECOVERY_TIME.labels(error_type=error_type).observe(recovery_time)
            
    def record_health_check(self, component: str, is_healthy: bool) -> None:
        """Record health check status"""
        HEALTH_STATUS.labels(component=component).set(1 if is_healthy else 0)
        
    def record_api_request(
        self,
        endpoint: str,
        status: str,
        duration: float
    ) -> None:
        """Record API request metrics"""
        API_REQUEST_COUNT.labels(endpoint=endpoint, status=status).inc()
        API_RESPONSE_TIME.labels(endpoint=endpoint).observe(duration)
        
    def get_dependency_metrics(
        self,
        dependency: str,
        tier: str
    ) -> DependencyMetrics:
        """Get consolidated metrics for a dependency"""
        # Collect all metrics for the dependency
        return DependencyMetrics(
            name=dependency,
            tier=tier,
            version=self._get_metric_value(
                DEPENDENCY_UPDATES,
                {'dependency': dependency, 'tier': tier}
            ),
            update_available=bool(self._get_metric_value(
                DEPENDENCY_UPDATES,
                {'dependency': dependency, 'tier': tier, 'update_type': 'available'}
            )),
            vulnerability_count=int(self._get_metric_value(
                SECURITY_VULNERABILITIES,
                {'dependency': dependency, 'tier': tier}
            )),
            performance_score=float(self._get_metric_value(
                PERFORMANCE_SCORE,
                {'dependency': dependency, 'tier': tier}
            )),
            resource_usage={
                resource_type: float(self._get_metric_value(
                    RESOURCE_USAGE,
                    {
                        'dependency': dependency,
                        'tier': tier,
                        'resource_type': resource_type
                    }
                ))
                for resource_type in ['cpu', 'memory', 'disk_read', 'disk_write']
            },
            error_count=int(self._get_metric_value(
                ERROR_COUNT,
                {'dependency': dependency, 'tier': tier}
            )),
            last_check=self.last_collection.get(f"{dependency}_check", datetime.min.replace(tzinfo=timezone.utc)),
            last_scan=self.last_collection.get(f"{dependency}_scan", datetime.min.replace(tzinfo=timezone.utc))
        )
        
    def _get_metric_value(
        self,
        metric: Any,
        labels: Dict[str, str]
    ) -> float:
        """Get current value of a metric with given labels"""
        try:
            return metric._value.get()
        except (KeyError, AttributeError):
            return 0.0
