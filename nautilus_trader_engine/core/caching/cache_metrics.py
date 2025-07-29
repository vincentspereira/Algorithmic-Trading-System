"""
Cache Metrics Collection
Performance monitoring and analytics for the caching system
"""

import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import statistics

from .cache_manager import CacheLevel


class MetricType(Enum):
    """Types of cache metrics"""
    HIT_RATE = "hit_rate"
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    SIZE = "size"
    EVICTION_RATE = "eviction_rate"
    ERROR_RATE = "error_rate"


@dataclass
class CacheMetricPoint:
    """Individual metric data point"""
    timestamp: float
    value: float
    level: Optional[CacheLevel] = None
    operation: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()


class CacheMetrics:
    """
    Comprehensive cache metrics collection and analysis
    
    Features:
    - Multi-level cache metrics
    - Real-time performance tracking
    - Historical trend analysis
    - Alerting thresholds
    - Performance optimization insights
    """
    
    def __init__(self, max_history: int = 10000, alert_thresholds: Optional[Dict[str, float]] = None):
        self.max_history = max_history
        self.alert_thresholds = alert_thresholds or self._default_thresholds()
        
        # Per-level metrics
        self._level_metrics: Dict[CacheLevel, Dict[str, Any]] = {
            level: self._init_level_metrics() for level in CacheLevel
        }
        
        # Global metrics
        self._global_metrics = self._init_global_metrics()
        
        # Time series data
        self._time_series: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        
        # Operation metrics
        self._operation_metrics = defaultdict(lambda: {
            'count': 0,
            'total_time': 0.0,
            'min_time': float('inf'),
            'max_time': 0.0,
            'errors': 0
        })
        
        # Alerts
        self._active_alerts: Dict[str, Dict[str, Any]] = {}
        self._alert_history: List[Dict[str, Any]] = []
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Start time for rate calculations
        self._start_time = time.time()
    
    def _default_thresholds(self) -> Dict[str, float]:
        """Default alert thresholds"""
        return {
            'hit_rate_min': 80.0,      # Minimum hit rate percentage
            'latency_max_ms': 10.0,    # Maximum latency in milliseconds
            'error_rate_max': 5.0,     # Maximum error rate percentage
            'eviction_rate_max': 10.0, # Maximum eviction rate per minute
            'memory_usage_max': 90.0   # Maximum memory usage percentage
        }
    
    def _init_level_metrics(self) -> Dict[str, Any]:
        """Initialize metrics for a cache level"""
        return {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'evictions': 0,
            'errors': 0,
            'total_latency_ns': 0,
            'size': 0,
            'memory_usage': 0,
            'last_updated': time.time()
        }
    
    def _init_global_metrics(self) -> Dict[str, Any]:
        """Initialize global metrics"""
        return {
            'total_requests': 0,
            'total_hits': 0,
            'total_misses': 0,
            'total_errors': 0,
            'cache_efficiency': 0.0,
            'average_latency_ms': 0.0,
            'requests_per_second': 0.0
        }
    
    def record_hit(self, level: CacheLevel, latency_ns: int):
        """Record a cache hit"""
        with self._lock:
            level_metrics = self._level_metrics[level]
            level_metrics['hits'] += 1
            level_metrics['total_latency_ns'] += latency_ns
            level_metrics['last_updated'] = time.time()
            
            # Update global metrics
            self._global_metrics['total_requests'] += 1
            self._global_metrics['total_hits'] += 1
            
            # Record time series
            self._record_time_series(f'{level.name.lower()}_hits', 1)
            self._record_time_series(f'{level.name.lower()}_latency_ms', latency_ns / 1_000_000)
            
            # Update operation metrics
            self._update_operation_metrics('get', latency_ns, success=True)
    
    def record_miss(self, latency_ns: int):
        """Record a cache miss"""
        with self._lock:
            # Update global metrics
            self._global_metrics['total_requests'] += 1
            self._global_metrics['total_misses'] += 1
            
            # Record time series
            self._record_time_series('misses', 1)
            self._record_time_series('miss_latency_ms', latency_ns / 1_000_000)
            
            # Update operation metrics
            self._update_operation_metrics('get', latency_ns, success=False)
    
    def record_set(self, latency_ns: int):
        """Record a cache set operation"""
        with self._lock:
            # Update global metrics
            self._global_metrics['total_requests'] += 1
            
            # Record time series
            self._record_time_series('sets', 1)
            self._record_time_series('set_latency_ms', latency_ns / 1_000_000)
            
            # Update operation metrics
            self._update_operation_metrics('set', latency_ns, success=True)
    
    def record_delete(self):
        """Record a cache delete operation"""
        with self._lock:
            # Record time series
            self._record_time_series('deletes', 1)
            
            # Update operation metrics
            self._operation_metrics['delete']['count'] += 1
    
    def record_eviction(self, level: CacheLevel):
        """Record a cache eviction"""
        with self._lock:
            level_metrics = self._level_metrics[level]
            level_metrics['evictions'] += 1
            level_metrics['last_updated'] = time.time()
            
            # Record time series
            self._record_time_series(f'{level.name.lower()}_evictions', 1)
    
    def record_error(self, operation: str, level: Optional[CacheLevel] = None):
        """Record a cache error"""
        with self._lock:
            if level:
                level_metrics = self._level_metrics[level]
                level_metrics['errors'] += 1
                level_metrics['last_updated'] = time.time()
            
            # Update global metrics
            self._global_metrics['total_errors'] += 1
            
            # Record time series
            self._record_time_series('errors', 1)
            
            # Update operation metrics
            self._operation_metrics[operation]['errors'] += 1
    
    def record_clear(self):
        """Record a cache clear operation"""
        with self._lock:
            # Record time series
            self._record_time_series('clears', 1)
    
    def record_invalidation(self, count: int):
        """Record cache invalidation"""
        with self._lock:
            # Record time series
            self._record_time_series('invalidations', count)
    
    def update_level_stats(self, level: CacheLevel, stats: Dict[str, Any]):
        """Update level statistics from cache implementation"""
        with self._lock:
            level_metrics = self._level_metrics[level]
            
            # Update size and memory usage
            if 'size' in stats:
                level_metrics['size'] = stats['size']
                self._record_time_series(f'{level.name.lower()}_size', stats['size'])
            
            if 'memory_usage_bytes' in stats:
                level_metrics['memory_usage'] = stats['memory_usage_bytes']
                self._record_time_series(f'{level.name.lower()}_memory', stats['memory_usage_bytes'])
            
            # Update hit/miss counts if provided
            if 'hits' in stats:
                level_metrics['hits'] = stats['hits']
            if 'misses' in stats:
                level_metrics['misses'] = stats['misses']
            
            level_metrics['last_updated'] = time.time()
    
    def _record_time_series(self, metric_name: str, value: float):
        """Record time series data point"""
        point = CacheMetricPoint(time.time(), value)
        self._time_series[metric_name].append(point)
    
    def _update_operation_metrics(self, operation: str, latency_ns: int, success: bool):
        """Update operation-specific metrics"""
        op_metrics = self._operation_metrics[operation]
        op_metrics['count'] += 1
        
        if success:
            latency_ms = latency_ns / 1_000_000
            op_metrics['total_time'] += latency_ms
            op_metrics['min_time'] = min(op_metrics['min_time'], latency_ms)
            op_metrics['max_time'] = max(op_metrics['max_time'], latency_ms)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        with self._lock:
            current_time = time.time()
            uptime = current_time - self._start_time
            
            # Calculate global rates and averages
            self._calculate_global_metrics(uptime)
            
            # Calculate per-level metrics
            level_summaries = {}
            for level, metrics in self._level_metrics.items():
                level_summaries[level.name.lower()] = self._calculate_level_summary(metrics)
            
            # Calculate operation summaries
            operation_summaries = {}
            for operation, metrics in self._operation_metrics.items():
                operation_summaries[operation] = self._calculate_operation_summary(metrics)
            
            return {
                'timestamp': current_time,
                'uptime_seconds': uptime,
                'global': self._global_metrics.copy(),
                'levels': level_summaries,
                'operations': operation_summaries,
                'alerts': self._get_active_alerts(),
                'trends': self._calculate_trends(),
                'health_score': self._calculate_health_score()
            }
    
    def _calculate_global_metrics(self, uptime: float):
        """Calculate global performance metrics"""
        total_requests = self._global_metrics['total_requests']
        total_hits = self._global_metrics['total_hits']
        
        if total_requests > 0:
            self._global_metrics['cache_efficiency'] = (total_hits / total_requests) * 100
            self._global_metrics['requests_per_second'] = total_requests / uptime if uptime > 0 else 0
        
        # Calculate average latency across all operations
        total_latency = 0
        total_operations = 0
        
        for op_metrics in self._operation_metrics.values():
            if op_metrics['count'] > 0:
                total_latency += op_metrics['total_time']
                total_operations += op_metrics['count']
        
        if total_operations > 0:
            self._global_metrics['average_latency_ms'] = total_latency / total_operations
    
    def _calculate_level_summary(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate summary for a cache level"""
        total_requests = metrics['hits'] + metrics['misses']
        hit_rate = (metrics['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'hits': metrics['hits'],
            'misses': metrics['misses'],
            'hit_rate_pct': hit_rate,
            'sets': metrics['sets'],
            'deletes': metrics['deletes'],
            'evictions': metrics['evictions'],
            'errors': metrics['errors'],
            'size': metrics['size'],
            'memory_usage_bytes': metrics['memory_usage'],
            'avg_latency_ms': (metrics['total_latency_ns'] / metrics['hits'] / 1_000_000) if metrics['hits'] > 0 else 0,
            'last_updated': metrics['last_updated']
        }
    
    def _calculate_operation_summary(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate summary for an operation"""
        count = metrics['count']
        
        return {
            'count': count,
            'avg_latency_ms': (metrics['total_time'] / count) if count > 0 else 0,
            'min_latency_ms': metrics['min_time'] if metrics['min_time'] != float('inf') else 0,
            'max_latency_ms': metrics['max_time'],
            'errors': metrics['errors'],
            'error_rate_pct': (metrics['errors'] / count * 100) if count > 0 else 0
        }
    
    def _calculate_trends(self) -> Dict[str, Dict[str, float]]:
        """Calculate performance trends"""
        trends = {}
        
        # Calculate trends for key metrics
        trend_metrics = ['hits', 'misses', 'sets', 'errors']
        
        for metric in trend_metrics:
            if metric in self._time_series:
                data_points = list(self._time_series[metric])
                if len(data_points) >= 2:
                    # Simple trend calculation (slope of recent data)
                    recent_points = data_points[-min(100, len(data_points)):]  # Last 100 points
                    values = [p.value for p in recent_points]
                    
                    if len(values) > 1:
                        # Calculate simple linear trend
                        x = list(range(len(values)))
                        trend_slope = self._calculate_slope(x, values)
                        
                        trends[metric] = {
                            'slope': trend_slope,
                            'direction': 'increasing' if trend_slope > 0 else 'decreasing' if trend_slope < 0 else 'stable',
                            'recent_avg': statistics.mean(values[-10:]) if len(values) >= 10 else statistics.mean(values)
                        }
        
        return trends
    
    def _calculate_slope(self, x: List[float], y: List[float]) -> float:
        """Calculate linear regression slope"""
        if len(x) != len(y) or len(x) < 2:
            return 0.0
        
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(x[i] * x[i] for i in range(n))
        
        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return 0.0
        
        return (n * sum_xy - sum_x * sum_y) / denominator
    
    def _calculate_health_score(self) -> float:
        """Calculate overall cache health score (0-100)"""
        score = 100.0
        
        # Penalize low hit rates
        total_requests = self._global_metrics['total_requests']
        if total_requests > 0:
            hit_rate = (self._global_metrics['total_hits'] / total_requests) * 100
            if hit_rate < self.alert_thresholds['hit_rate_min']:
                score -= (self.alert_thresholds['hit_rate_min'] - hit_rate)
        
        # Penalize high error rates
        if total_requests > 0:
            error_rate = (self._global_metrics['total_errors'] / total_requests) * 100
            if error_rate > self.alert_thresholds['error_rate_max']:
                score -= (error_rate - self.alert_thresholds['error_rate_max']) * 2
        
        # Penalize high latency
        avg_latency = self._global_metrics['average_latency_ms']
        if avg_latency > self.alert_thresholds['latency_max_ms']:
            score -= (avg_latency - self.alert_thresholds['latency_max_ms'])
        
        return max(0.0, min(100.0, score))
    
    def _get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get currently active alerts"""
        current_time = time.time()
        active_alerts = []
        
        # Check hit rate alerts
        total_requests = self._global_metrics['total_requests']
        if total_requests > 100:  # Only alert after sufficient data
            hit_rate = (self._global_metrics['total_hits'] / total_requests) * 100
            if hit_rate < self.alert_thresholds['hit_rate_min']:
                active_alerts.append({
                    'type': 'hit_rate_low',
                    'message': f'Hit rate ({hit_rate:.1f}%) below threshold ({self.alert_thresholds["hit_rate_min"]:.1f}%)',
                    'severity': 'warning',
                    'timestamp': current_time,
                    'value': hit_rate,
                    'threshold': self.alert_thresholds['hit_rate_min']
                })
        
        # Check latency alerts
        avg_latency = self._global_metrics['average_latency_ms']
        if avg_latency > self.alert_thresholds['latency_max_ms']:
            active_alerts.append({
                'type': 'latency_high',
                'message': f'Average latency ({avg_latency:.2f}ms) above threshold ({self.alert_thresholds["latency_max_ms"]:.2f}ms)',
                'severity': 'warning',
                'timestamp': current_time,
                'value': avg_latency,
                'threshold': self.alert_thresholds['latency_max_ms']
            })
        
        # Check error rate alerts
        if total_requests > 0:
            error_rate = (self._global_metrics['total_errors'] / total_requests) * 100
            if error_rate > self.alert_thresholds['error_rate_max']:
                active_alerts.append({
                    'type': 'error_rate_high',
                    'message': f'Error rate ({error_rate:.1f}%) above threshold ({self.alert_thresholds["error_rate_max"]:.1f}%)',
                    'severity': 'critical',
                    'timestamp': current_time,
                    'value': error_rate,
                    'threshold': self.alert_thresholds['error_rate_max']
                })
        
        return active_alerts
    
    def get_time_series(self, metric_name: str, duration_seconds: int = 3600) -> List[CacheMetricPoint]:
        """Get time series data for a specific metric"""
        with self._lock:
            if metric_name not in self._time_series:
                return []
            
            cutoff_time = time.time() - duration_seconds
            return [point for point in self._time_series[metric_name] if point.timestamp >= cutoff_time]
    
    def reset_metrics(self):
        """Reset all metrics (useful for testing)"""
        with self._lock:
            # Reset level metrics
            for level in CacheLevel:
                self._level_metrics[level] = self._init_level_metrics()
            
            # Reset global metrics
            self._global_metrics = self._init_global_metrics()
            
            # Clear time series
            self._time_series.clear()
            
            # Reset operation metrics
            self._operation_metrics.clear()
            
            # Clear alerts
            self._active_alerts.clear()
            
            # Reset start time
            self._start_time = time.time()
    
    def export_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format"""
        with self._lock:
            lines = []
            current_metrics = self.get_metrics()
            
            # Global metrics
            global_metrics = current_metrics['global']
            lines.append(f"# TYPE cache_requests_total counter")
            lines.append(f"cache_requests_total {global_metrics['total_requests']}")
            
            lines.append(f"# TYPE cache_hits_total counter")
            lines.append(f"cache_hits_total {global_metrics['total_hits']}")
            
            lines.append(f"# TYPE cache_efficiency_percent gauge")
            lines.append(f"cache_efficiency_percent {global_metrics['cache_efficiency']}")
            
            lines.append(f"# TYPE cache_latency_ms gauge")
            lines.append(f"cache_latency_ms {global_metrics['average_latency_ms']}")
            
            # Level-specific metrics
            for level_name, level_metrics in current_metrics['levels'].items():
                lines.append(f"# TYPE cache_level_hits_total counter")
                lines.append(f'cache_level_hits_total{{level="{level_name}"}} {level_metrics["hits"]}')
                
                lines.append(f"# TYPE cache_level_hit_rate_percent gauge")
                lines.append(f'cache_level_hit_rate_percent{{level="{level_name}"}} {level_metrics["hit_rate_pct"]}')
                
                lines.append(f"# TYPE cache_level_size gauge")
                lines.append(f'cache_level_size{{level="{level_name}"}} {level_metrics["size"]}')
            
            return '\n'.join(lines)