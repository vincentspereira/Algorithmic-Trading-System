"""
Monitoring Infrastructure for Dependency Management System.
Provides centralized logging, metrics collection, and monitoring functionality.
"""

import logging
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import psutil
import prometheus_client
from prometheus_client import Counter, Gauge, Histogram, Summary
import structlog
from opentelemetry import trace, metrics
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider

# Prometheus metrics
DEPENDENCY_UPDATES = Counter(
    'dependency_updates_total',
    'Number of dependency updates detected',
    ['tier', 'dependency', 'update_type']
)

SECURITY_ISSUES = Counter(
    'security_issues_total',
    'Number of security issues found',
    ['tier', 'dependency', 'severity']
)

DEPENDENCY_HEALTH = Gauge(
    'dependency_health_score',
    'Health score for dependencies',
    ['tier', 'dependency']
)

SCAN_DURATION = Histogram(
    'dependency_scan_duration_seconds',
    'Time spent scanning dependencies',
    ['tier', 'dependency', 'scan_type']
)

RESOURCE_USAGE = Gauge(
    'dependency_resource_usage',
    'Resource usage by dependency',
    ['tier', 'dependency', 'resource_type']
)

@dataclass
class DependencyMetrics:
    """Metrics for a single dependency"""
    cpu_usage: float
    memory_usage: float
    disk_io: Dict[str, float]
    network_io: Dict[str, float]
    scan_times: Dict[str, float]
    error_count: int
    last_update: datetime
    health_score: float

class MonitoringSystem:
    """Central monitoring system for dependency management"""
    
    def __init__(self):
        # Set up structured logging
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer()
            ],
            wrapper_class=structlog.BoundLogger,
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
        )
        
        self.logger = structlog.get_logger()
        
        # Set up OpenTelemetry
        trace.set_tracer_provider(TracerProvider())
        self.tracer = trace.get_tracer(__name__)
        
        metrics.set_meter_provider(MeterProvider())
        self.meter = metrics.get_meter(__name__)
        
        # Initialize metrics storage
        self.metrics: Dict[str, DependencyMetrics] = {}
    
    def record_dependency_update(self, tier: str, dependency: str, update_type: str):
        """Record a dependency update event"""
        DEPENDENCY_UPDATES.labels(tier=tier, dependency=dependency, update_type=update_type).inc()
        self.logger.info(
            "dependency_update",
            tier=tier,
            dependency=dependency,
            update_type=update_type
        )
    
    def record_security_issue(self, tier: str, dependency: str, severity: str):
        """Record a security issue"""
        SECURITY_ISSUES.labels(tier=tier, dependency=dependency, severity=severity).inc()
        self.logger.warning(
            "security_issue",
            tier=tier,
            dependency=dependency,
            severity=severity
        )
    
    def update_health_score(self, tier: str, dependency: str, score: float):
        """Update dependency health score"""
        DEPENDENCY_HEALTH.labels(tier=tier, dependency=dependency).set(score)
    
    def record_scan_duration(self, tier: str, dependency: str, scan_type: str, duration: float):
        """Record the duration of a scan"""
        SCAN_DURATION.labels(tier=tier, dependency=dependency, scan_type=scan_type).observe(duration)
    
    def update_resource_metrics(self, tier: str, dependency: str):
        """Update resource usage metrics for a dependency"""
        process = psutil.Process()
        
        # CPU
        cpu_percent = process.cpu_percent()
        RESOURCE_USAGE.labels(tier=tier, dependency=dependency, resource_type="cpu").set(cpu_percent)
        
        # Memory
        memory_info = process.memory_info()
        RESOURCE_USAGE.labels(tier=tier, dependency=dependency, resource_type="memory").set(memory_info.rss)
        
        # Disk IO
        disk_io = process.io_counters()
        RESOURCE_USAGE.labels(tier=tier, dependency=dependency, resource_type="disk_read").set(disk_io.read_bytes)
        RESOURCE_USAGE.labels(tier=tier, dependency=dependency, resource_type="disk_write").set(disk_io.write_bytes)
        
        # Store metrics
        self.metrics[dependency] = DependencyMetrics(
            cpu_usage=cpu_percent,
            memory_usage=memory_info.rss,
            disk_io={"read": disk_io.read_bytes, "write": disk_io.write_bytes},
            network_io={"sent": 0, "recv": 0},  # Will be updated separately
            scan_times={},  # Will be updated during scans
            error_count=0,  # Will be updated when errors occur
            last_update=datetime.now(timezone.utc),
            health_score=self._calculate_health_score(dependency)
        )
    
    def _calculate_health_score(self, dependency: str) -> float:
        """Calculate health score based on metrics"""
        if dependency not in self.metrics:
            return 0.0
            
        metrics = self.metrics[dependency]
        
        # Start with perfect score
        score = 100.0
        
        # Penalize for high CPU usage
        if metrics.cpu_usage > 80:
            score -= 20
        elif metrics.cpu_usage > 60:
            score -= 10
            
        # Penalize for high memory usage (assuming 8GB max)
        memory_gb = metrics.memory_usage / (1024 * 1024 * 1024)
        if memory_gb > 6:
            score -= 20
        elif memory_gb > 4:
            score -= 10
            
        # Penalize for errors
        score -= min(metrics.error_count * 5, 30)  # Max 30 point penalty
        
        return max(0.0, score)  # Don't go below 0
    
    def get_dependency_metrics(self, dependency: str) -> Optional[DependencyMetrics]:
        """Get current metrics for a dependency"""
        return self.metrics.get(dependency)
    
    def log_error(self, tier: str, dependency: str, error: Exception):
        """Log an error with full context"""
        with self.tracer.start_as_current_span("dependency_error") as span:
            span.set_attribute("tier", tier)
            span.set_attribute("dependency", dependency)
            span.set_attribute("error", str(error))
            
            self.logger.error(
                "dependency_error",
                tier=tier,
                dependency=dependency,
                error=str(error),
                exc_info=True
            )
            
            if dependency in self.metrics:
                self.metrics[dependency].error_count += 1
    
    def export_metrics(self) -> Dict[str, Any]:
        """Export all metrics in a serializable format"""
        return {
            name: {
                "cpu_usage": metrics.cpu_usage,
                "memory_usage": metrics.memory_usage,
                "disk_io": metrics.disk_io,
                "network_io": metrics.network_io,
                "scan_times": metrics.scan_times,
                "error_count": metrics.error_count,
                "last_update": metrics.last_update.isoformat(),
                "health_score": metrics.health_score
            }
            for name, metrics in self.metrics.items()
        }

# Create global monitoring instance
monitoring = MonitoringSystem()
