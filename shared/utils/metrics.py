"""Comprehensive metrics and monitoring system.

This module provides advanced metrics collection and monitoring capabilities including:
- Custom metrics with labels and dimensions
- Histogram and gauge metrics
- Counter and timer metrics
- Prometheus integration
- Real-time metrics streaming
- Performance profiling
- Health checks and alerts
- Metrics aggregation and reporting
"""

import asyncio
import time
import logging
import threading
import statistics
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union, Any, Callable, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import json
import weakref
from contextlib import contextmanager, asynccontextmanager

try:
    import prometheus_client
    from prometheus_client import Counter, Histogram, Gauge, Summary, Info
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    prometheus_client = None

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

from config.performance_config import performance_manager

logger = logging.getLogger(__name__)

class MetricType(Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"
    SUMMARY = "summary"

@dataclass
class MetricValue:
    """A metric value with timestamp and labels."""
    value: Union[int, float]
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'labels': self.labels
        }

@dataclass
class HistogramBucket:
    """Histogram bucket."""
    upper_bound: float
    count: int = 0
    
    def __post_init__(self):
        if self.upper_bound == float('inf'):
            self.upper_bound = float('inf')

class Metric(ABC):
    """Abstract base class for metrics."""
    
    def __init__(self, name: str, description: str = "", labels: Optional[List[str]] = None):
        self.name = name
        self.description = description
        self.labels = labels or []
        self.created_at = datetime.utcnow()
        self._lock = threading.Lock()
    
    @abstractmethod
    def record(self, value: Union[int, float], labels: Optional[Dict[str, str]] = None):
        """Record a metric value."""
        pass
    
    @abstractmethod
    def get_value(self, labels: Optional[Dict[str, str]] = None) -> Any:
        """Get current metric value."""
        pass
    
    @abstractmethod
    def reset(self, labels: Optional[Dict[str, str]] = None):
        """Reset metric value."""
        pass
    
    def _validate_labels(self, labels: Optional[Dict[str, str]]) -> Dict[str, str]:
        """Validate and normalize labels."""
        if not labels:
            return {}
        
        # Check if all required labels are present
        for required_label in self.labels:
            if required_label not in labels:
                raise ValueError(f"Missing required label: {required_label}")
        
        return labels
    
    def _get_label_key(self, labels: Dict[str, str]) -> str:
        """Generate key from labels."""
        if not labels:
            return "__default__"
        
        sorted_items = sorted(labels.items())
        return "|".join(f"{k}={v}" for k, v in sorted_items)

class CounterMetric(Metric):
    """Counter metric that only increases."""
    
    def __init__(self, name: str, description: str = "", labels: Optional[List[str]] = None):
        super().__init__(name, description, labels)
        self._values: Dict[str, float] = defaultdict(float)
    
    def record(self, value: Union[int, float] = 1, labels: Optional[Dict[str, str]] = None):
        """Increment counter by value."""
        if value < 0:
            raise ValueError("Counter values must be non-negative")
        
        validated_labels = self._validate_labels(labels)
        label_key = self._get_label_key(validated_labels)
        
        with self._lock:
            self._values[label_key] += value
    
    def get_value(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Get current counter value."""
        validated_labels = self._validate_labels(labels)
        label_key = self._get_label_key(validated_labels)
        
        with self._lock:
            return self._values[label_key]
    
    def reset(self, labels: Optional[Dict[str, str]] = None):
        """Reset counter value."""
        validated_labels = self._validate_labels(labels)
        label_key = self._get_label_key(validated_labels)
        
        with self._lock:
            self._values[label_key] = 0
    
    def get_all_values(self) -> Dict[str, float]:
        """Get all counter values."""
        with self._lock:
            return dict(self._values)

class GaugeMetric(Metric):
    """Gauge metric that can increase or decrease."""
    
    def __init__(self, name: str, description: str = "", labels: Optional[List[str]] = None):
        super().__init__(name, description, labels)
        self._values: Dict[str, float] = defaultdict(float)
        self._history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
    
    def record(self, value: Union[int, float], labels: Optional[Dict[str, str]] = None):
        """Set gauge value."""
        validated_labels = self._validate_labels(labels)
        label_key = self._get_label_key(validated_labels)
        
        with self._lock:
            self._values[label_key] = float(value)
            self._history[label_key].append(MetricValue(
                value=float(value),
                timestamp=datetime.utcnow(),
                labels=validated_labels
            ))
    
    def increment(self, value: Union[int, float] = 1, labels: Optional[Dict[str, str]] = None):
        """Increment gauge value."""
        validated_labels = self._validate_labels(labels)
        label_key = self._get_label_key(validated_labels)
        
        with self._lock:
            self._values[label_key] += value
            self._history[label_key].append(MetricValue(
                value=self._values[label_key],
                timestamp=datetime.utcnow(),
                labels=validated_labels
            ))
    
    def decrement(self, value: Union[int, float] = 1, labels: Optional[Dict[str, str]] = None):
        """Decrement gauge value."""
        self.increment(-value, labels)
    
    def get_value(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Get current gauge value."""
        validated_labels = self._validate_labels(labels)
        label_key = self._get_label_key(validated_labels)
        
        with self._lock:
            return self._values[label_key]
    
    def reset(self, labels: Optional[Dict[str, str]] = None):
        """Reset gauge value."""
        validated_labels = self._validate_labels(labels)
        label_key = self._get_label_key(validated_labels)
        
        with self._lock:
            self._values[label_key] = 0
            self._history[label_key].clear()
    
    def get_history(self, labels: Optional[Dict[str, str]] = None) -> List[MetricValue]:
        """Get gauge value history."""
        validated_labels = self._validate_labels(labels)
        label_key = self._get_label_key(validated_labels)
        
        with self._lock:
            return list(self._history[label_key])

class HistogramMetric(Metric):
    """Histogram metric for measuring distributions."""
    
    def __init__(self, name: str, description: str = "", labels: Optional[List[str]] = None,
                 buckets: Optional[List[float]] = None):
        super().__init__(name, description, labels)
        
        # Default buckets if none provided
        if buckets is None:
            buckets = [0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, float('inf')]
        
        self.buckets = sorted(buckets)
        self._bucket_counts: Dict[str, Dict[float, int]] = defaultdict(lambda: defaultdict(int))
        self._sums: Dict[str, float] = defaultdict(float)
        self._counts: Dict[str, int] = defaultdict(int)
    
    def record(self, value: Union[int, float], labels: Optional[Dict[str, str]] = None):
        """Record a value in the histogram."""
        validated_labels = self._validate_labels(labels)
        label_key = self._get_label_key(validated_labels)
        
        with self._lock:
            # Update sum and count
            self._sums[label_key] += value
            self._counts[label_key] += 1
            
            # Update buckets
            for bucket in self.buckets:
                if value <= bucket:
                    self._bucket_counts[label_key][bucket] += 1
    
    def get_value(self, labels: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Get histogram statistics."""
        validated_labels = self._validate_labels(labels)
        label_key = self._get_label_key(validated_labels)
        
        with self._lock:
            count = self._counts[label_key]
            if count == 0:
                return {
                    'count': 0,
                    'sum': 0,
                    'average': 0,
                    'buckets': {}
                }
            
            return {
                'count': count,
                'sum': self._sums[label_key],
                'average': self._sums[label_key] / count,
                'buckets': dict(self._bucket_counts[label_key])
            }
    
    def reset(self, labels: Optional[Dict[str, str]] = None):
        """Reset histogram."""
        validated_labels = self._validate_labels(labels)
        label_key = self._get_label_key(validated_labels)
        
        with self._lock:
            self._sums[label_key] = 0
            self._counts[label_key] = 0
            self._bucket_counts[label_key].clear()
    
    def get_percentile(self, percentile: float, labels: Optional[Dict[str, str]] = None) -> float:
        """Estimate percentile from histogram buckets."""
        validated_labels = self._validate_labels(labels)
        label_key = self._get_label_key(validated_labels)
        
        with self._lock:
            count = self._counts[label_key]
            if count == 0:
                return 0
            
            target_count = count * (percentile / 100)
            cumulative_count = 0
            
            for bucket in self.buckets:
                cumulative_count += self._bucket_counts[label_key][bucket]
                if cumulative_count >= target_count:
                    return bucket
            
            return self.buckets[-1]

class TimerMetric(HistogramMetric):
    """Timer metric for measuring durations."""
    
    def __init__(self, name: str, description: str = "", labels: Optional[List[str]] = None):
        # Timer-specific buckets (in seconds)
        timer_buckets = [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float('inf')]
        super().__init__(name, description, labels, timer_buckets)
    
    @contextmanager
    def time(self, labels: Optional[Dict[str, str]] = None):
        """Context manager for timing operations."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.record(duration, labels)
    
    @asynccontextmanager
    async def async_time(self, labels: Optional[Dict[str, str]] = None):
        """Async context manager for timing operations."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.record(duration, labels)

class MetricsRegistry:
    """Registry for managing metrics."""
    
    def __init__(self):
        self._metrics: Dict[str, Metric] = {}
        self._lock = threading.Lock()
        self._prometheus_metrics: Dict[str, Any] = {}
        
        # System metrics
        self._system_metrics_task = None
        self._start_system_metrics()
        
        logger.info("Metrics registry initialized")
    
    def counter(self, name: str, description: str = "", labels: Optional[List[str]] = None) -> CounterMetric:
        """Create or get a counter metric."""
        return self._get_or_create_metric(name, CounterMetric, description, labels)
    
    def gauge(self, name: str, description: str = "", labels: Optional[List[str]] = None) -> GaugeMetric:
        """Create or get a gauge metric."""
        return self._get_or_create_metric(name, GaugeMetric, description, labels)
    
    def histogram(self, name: str, description: str = "", labels: Optional[List[str]] = None,
                 buckets: Optional[List[float]] = None) -> HistogramMetric:
        """Create or get a histogram metric."""
        return self._get_or_create_metric(name, HistogramMetric, description, labels, buckets=buckets)
    
    def timer(self, name: str, description: str = "", labels: Optional[List[str]] = None) -> TimerMetric:
        """Create or get a timer metric."""
        return self._get_or_create_metric(name, TimerMetric, description, labels)
    
    def _get_or_create_metric(self, name: str, metric_class: type, description: str = "",
                             labels: Optional[List[str]] = None, **kwargs) -> Metric:
        """Get existing metric or create new one."""
        with self._lock:
            if name in self._metrics:
                metric = self._metrics[name]
                if not isinstance(metric, metric_class):
                    raise ValueError(f"Metric {name} already exists with different type")
                return metric
            
            # Create new metric
            if metric_class == HistogramMetric:
                metric = metric_class(name, description, labels, **kwargs)
            else:
                metric = metric_class(name, description, labels)
            
            self._metrics[name] = metric
            
            # Create Prometheus metric if available
            if PROMETHEUS_AVAILABLE:
                self._create_prometheus_metric(metric, **kwargs)
            
            logger.debug(f"Created {metric_class.__name__}: {name}")
            return metric
    
    def _create_prometheus_metric(self, metric: Metric, **kwargs):
        """Create corresponding Prometheus metric."""
        try:
            if isinstance(metric, CounterMetric):
                prom_metric = Counter(metric.name, metric.description, metric.labels)
            elif isinstance(metric, GaugeMetric):
                prom_metric = Gauge(metric.name, metric.description, metric.labels)
            elif isinstance(metric, (HistogramMetric, TimerMetric)):
                buckets = kwargs.get('buckets')
                if buckets and buckets[-1] != float('inf'):
                    buckets = list(buckets) + [float('inf')]
                prom_metric = Histogram(metric.name, metric.description, metric.labels, buckets=buckets)
            else:
                return
            
            self._prometheus_metrics[metric.name] = prom_metric
            
        except Exception as e:
            logger.warning(f"Failed to create Prometheus metric for {metric.name}: {e}")
    
    def get_metric(self, name: str) -> Optional[Metric]:
        """Get metric by name."""
        with self._lock:
            return self._metrics.get(name)
    
    def get_all_metrics(self) -> Dict[str, Metric]:
        """Get all metrics."""
        with self._lock:
            return dict(self._metrics)
    
    def remove_metric(self, name: str) -> bool:
        """Remove metric by name."""
        with self._lock:
            if name in self._metrics:
                del self._metrics[name]
                if name in self._prometheus_metrics:
                    del self._prometheus_metrics[name]
                return True
            return False
    
    def clear_all(self):
        """Clear all metrics."""
        with self._lock:
            self._metrics.clear()
            self._prometheus_metrics.clear()
    
    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        if not PROMETHEUS_AVAILABLE:
            raise ImportError("Prometheus client not available")
        
        return prometheus_client.generate_latest().decode('utf-8')
    
    def export_json(self) -> Dict[str, Any]:
        """Export metrics in JSON format."""
        result = {
            'timestamp': datetime.utcnow().isoformat(),
            'metrics': {}
        }
        
        with self._lock:
            for name, metric in self._metrics.items():
                if isinstance(metric, CounterMetric):
                    result['metrics'][name] = {
                        'type': 'counter',
                        'description': metric.description,
                        'values': metric.get_all_values()
                    }
                elif isinstance(metric, GaugeMetric):
                    result['metrics'][name] = {
                        'type': 'gauge',
                        'description': metric.description,
                        'value': metric.get_value()
                    }
                elif isinstance(metric, (HistogramMetric, TimerMetric)):
                    result['metrics'][name] = {
                        'type': 'histogram' if isinstance(metric, HistogramMetric) else 'timer',
                        'description': metric.description,
                        'value': metric.get_value()
                    }
        
        return result
    
    def _start_system_metrics(self):
        """Start collecting system metrics."""
        if PSUTIL_AVAILABLE:
            self._system_metrics_task = asyncio.create_task(self._collect_system_metrics())
    
    async def _collect_system_metrics(self):
        """Collect system metrics periodically."""
        # Create system metrics
        cpu_usage = self.gauge('system_cpu_usage_percent', 'CPU usage percentage')
        memory_usage = self.gauge('system_memory_usage_percent', 'Memory usage percentage')
        disk_usage = self.gauge('system_disk_usage_percent', 'Disk usage percentage')
        network_bytes_sent = self.counter('system_network_bytes_sent_total', 'Network bytes sent')
        network_bytes_recv = self.counter('system_network_bytes_recv_total', 'Network bytes received')
        
        last_network_stats = psutil.net_io_counters()
        
        while True:
            try:
                await asyncio.sleep(10)  # Collect every 10 seconds
                
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                cpu_usage.record(cpu_percent)
                
                # Memory usage
                memory = psutil.virtual_memory()
                memory_usage.record(memory.percent)
                
                # Disk usage
                disk = psutil.disk_usage('/')
                disk_usage.record(disk.percent)
                
                # Network I/O
                network_stats = psutil.net_io_counters()
                bytes_sent_delta = network_stats.bytes_sent - last_network_stats.bytes_sent
                bytes_recv_delta = network_stats.bytes_recv - last_network_stats.bytes_recv
                
                if bytes_sent_delta > 0:
                    network_bytes_sent.record(bytes_sent_delta)
                if bytes_recv_delta > 0:
                    network_bytes_recv.record(bytes_recv_delta)
                
                last_network_stats = network_stats
                
            except Exception as e:
                logger.error(f"Error collecting system metrics: {e}")
                await asyncio.sleep(60)  # Wait longer on error

class HealthCheck:
    """Health check system."""
    
    def __init__(self, name: str, check_func: Callable[[], bool], 
                 interval: int = 60, timeout: int = 30):
        self.name = name
        self.check_func = check_func
        self.interval = interval
        self.timeout = timeout
        self.last_check = None
        self.last_result = None
        self.consecutive_failures = 0
        self._task = None
    
    async def start(self):
        """Start health check."""
        self._task = asyncio.create_task(self._check_loop())
    
    async def stop(self):
        """Stop health check."""
        if self._task:
            self._task.cancel()
    
    async def _check_loop(self):
        """Health check loop."""
        while True:
            try:
                await asyncio.sleep(self.interval)
                await self.check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check {self.name}: {e}")
    
    async def check(self) -> bool:
        """Perform health check."""
        try:
            # Run check with timeout
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, self.check_func),
                timeout=self.timeout
            )
            
            self.last_check = datetime.utcnow()
            self.last_result = result
            
            if result:
                self.consecutive_failures = 0
            else:
                self.consecutive_failures += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Health check {self.name} failed: {e}")
            self.last_check = datetime.utcnow()
            self.last_result = False
            self.consecutive_failures += 1
            return False

# Global metrics registry
metrics = MetricsRegistry()

# Convenience functions
def counter(name: str, description: str = "", labels: Optional[List[str]] = None) -> CounterMetric:
    """Create or get a counter metric."""
    return metrics.counter(name, description, labels)

def gauge(name: str, description: str = "", labels: Optional[List[str]] = None) -> GaugeMetric:
    """Create or get a gauge metric."""
    return metrics.gauge(name, description, labels)

def histogram(name: str, description: str = "", labels: Optional[List[str]] = None,
             buckets: Optional[List[float]] = None) -> HistogramMetric:
    """Create or get a histogram metric."""
    return metrics.histogram(name, description, labels, buckets)

def timer(name: str, description: str = "", labels: Optional[List[str]] = None) -> TimerMetric:
    """Create or get a timer metric."""
    return metrics.timer(name, description, labels)

# Export commonly used classes
__all__ = [
    "Metric",
    "CounterMetric",
    "GaugeMetric",
    "HistogramMetric",
    "TimerMetric",
    "MetricsRegistry",
    "HealthCheck",
    "MetricType",
    "MetricValue",
    "metrics",
    "counter",
    "gauge",
    "histogram",
    "timer",
]