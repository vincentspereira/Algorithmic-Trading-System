"""
Message Bus Metrics Collection
Performance monitoring and metrics for the messaging system
"""

import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import statistics

from .serialization import MessageType


class MetricType(Enum):
    """Types of metrics collected"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class MetricValue:
    """Individual metric value with timestamp"""
    value: float
    timestamp: int = field(default_factory=time.time_ns)
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class HistogramBucket:
    """Histogram bucket for latency measurements"""
    upper_bound: float
    count: int = 0


class MessageMetrics:
    """
    High-performance metrics collection for message bus
    
    Collects detailed performance metrics with minimal overhead
    to enable monitoring and optimization of the trading system.
    """
    
    def __init__(self, max_history: int = 10000):
        self.max_history = max_history
        
        # Counters
        self._counters: Dict[str, int] = defaultdict(int)
        
        # Gauges
        self._gauges: Dict[str, float] = {}
        
        # Histograms (for latency measurements)
        self._histograms: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        
        # Message-specific metrics
        self._messages_published = defaultdict(int)
        self._messages_processed = defaultdict(int)
        self._messages_dropped = defaultdict(int)
        self._messages_unrouted = defaultdict(int)
        
        # Latency tracking
        self._processing_times = defaultdict(lambda: deque(maxlen=1000))
        self._serialization_times = defaultdict(lambda: deque(maxlen=1000))
        
        # Topic-specific metrics
        self._topic_metrics = defaultdict(lambda: {
            'published': 0,
            'processed': 0,
            'dropped': 0,
            'avg_latency': 0.0,
            'last_activity': 0
        })
        
        # Priority-specific metrics
        self._priority_metrics = defaultdict(lambda: {
            'published': 0,
            'processed': 0,
            'dropped': 0,
            'queue_depth': 0
        })
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Performance tracking
        self._start_time = time.time_ns()
        self._last_reset = time.time_ns()
    
    def record_message_published(self, topic: str, priority: Any):
        """Record a message being published"""
        with self._lock:
            self._counters['messages_published_total'] += 1
            self._messages_published[topic] += 1
            
            # Update topic metrics
            self._topic_metrics[topic]['published'] += 1
            self._topic_metrics[topic]['last_activity'] = time.time_ns()
            
            # Update priority metrics
            priority_name = priority.name if hasattr(priority, 'name') else str(priority)
            self._priority_metrics[priority_name]['published'] += 1
    
    def record_message_processed(self, topic: str, priority: Any, processing_time_ns: int):
        """Record a message being processed"""
        with self._lock:
            self._counters['messages_processed_total'] += 1
            self._messages_processed[topic] += 1
            
            # Record processing time
            processing_time_ms = processing_time_ns / 1_000_000  # Convert to milliseconds
            self._processing_times[topic].append(processing_time_ms)
            self._histograms['processing_time_ms'].append(processing_time_ms)
            
            # Update topic metrics
            topic_data = self._topic_metrics[topic]
            topic_data['processed'] += 1
            topic_data['last_activity'] = time.time_ns()
            
            # Update average latency (exponential moving average)
            if topic_data['avg_latency'] == 0:
                topic_data['avg_latency'] = processing_time_ms
            else:
                alpha = 0.1  # Smoothing factor
                topic_data['avg_latency'] = (alpha * processing_time_ms + 
                                           (1 - alpha) * topic_data['avg_latency'])
            
            # Update priority metrics
            priority_name = priority.name if hasattr(priority, 'name') else str(priority)
            self._priority_metrics[priority_name]['processed'] += 1
    
    def record_message_dropped(self, topic: str, priority: Any):
        """Record a message being dropped due to backpressure"""
        with self._lock:
            self._counters['messages_dropped_total'] += 1
            self._messages_dropped[topic] += 1
            
            # Update topic metrics
            self._topic_metrics[topic]['dropped'] += 1
            self._topic_metrics[topic]['last_activity'] = time.time_ns()
            
            # Update priority metrics
            priority_name = priority.name if hasattr(priority, 'name') else str(priority)
            self._priority_metrics[priority_name]['dropped'] += 1
    
    def record_message_unrouted(self, topic: str):
        """Record a message that couldn't be routed"""
        with self._lock:
            self._counters['messages_unrouted_total'] += 1
            self._messages_unrouted[topic] += 1
    
    def record_serialization_time(self, message_type: MessageType, time_ns: int):
        """Record serialization time"""
        with self._lock:
            time_ms = time_ns / 1_000_000
            self._serialization_times[message_type.name].append(time_ms)
            self._histograms['serialization_time_ms'].append(time_ms)
    
    def update_queue_depth(self, priority: Any, depth: int):
        """Update queue depth for a priority level"""
        with self._lock:
            priority_name = priority.name if hasattr(priority, 'name') else str(priority)
            self._priority_metrics[priority_name]['queue_depth'] = depth
            self._gauges[f'queue_depth_{priority_name}'] = depth
    
    def increment_counter(self, name: str, value: int = 1, labels: Optional[Dict[str, str]] = None):
        """Increment a custom counter"""
        with self._lock:
            self._counters[name] += value
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge value"""
        with self._lock:
            self._gauges[name] = value
    
    def record_histogram(self, name: str, value: float):
        """Record a histogram value"""
        with self._lock:
            self._histograms[name].append(value)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all current metrics"""
        with self._lock:
            current_time = time.time_ns()
            uptime_seconds = (current_time - self._start_time) / 1_000_000_000
            
            # Calculate rates
            time_since_reset = (current_time - self._last_reset) / 1_000_000_000
            if time_since_reset > 0:
                publish_rate = self._counters['messages_published_total'] / time_since_reset
                process_rate = self._counters['messages_processed_total'] / time_since_reset
            else:
                publish_rate = process_rate = 0
            
            return {
                'timestamp': current_time,
                'uptime_seconds': uptime_seconds,
                
                # Basic counters
                'counters': dict(self._counters),
                'gauges': dict(self._gauges),
                
                # Rates
                'rates': {
                    'messages_published_per_sec': publish_rate,
                    'messages_processed_per_sec': process_rate,
                },
                
                # Topic metrics
                'topics': dict(self._topic_metrics),
                
                # Priority metrics
                'priorities': dict(self._priority_metrics),
                
                # Latency statistics
                'latency_stats': self._calculate_latency_stats(),
                
                # Histogram summaries
                'histograms': self._get_histogram_summaries(),
                
                # System health
                'health': self._calculate_health_metrics()
            }
    
    def _calculate_latency_stats(self) -> Dict[str, Dict[str, float]]:
        """Calculate latency statistics for all topics"""
        stats = {}
        
        for topic, times in self._processing_times.items():
            if times:
                times_list = list(times)
                stats[topic] = {
                    'count': len(times_list),
                    'min_ms': min(times_list),
                    'max_ms': max(times_list),
                    'mean_ms': statistics.mean(times_list),
                    'median_ms': statistics.median(times_list),
                    'p95_ms': self._percentile(times_list, 0.95),
                    'p99_ms': self._percentile(times_list, 0.99)
                }
        
        return stats
    
    def _get_histogram_summaries(self) -> Dict[str, Dict[str, float]]:
        """Get histogram summaries"""
        summaries = {}
        
        for name, values in self._histograms.items():
            if values:
                values_list = list(values)
                summaries[name] = {
                    'count': len(values_list),
                    'min': min(values_list),
                    'max': max(values_list),
                    'mean': statistics.mean(values_list),
                    'p50': self._percentile(values_list, 0.5),
                    'p95': self._percentile(values_list, 0.95),
                    'p99': self._percentile(values_list, 0.99)
                }
        
        return summaries
    
    def _calculate_health_metrics(self) -> Dict[str, Any]:
        """Calculate system health metrics"""
        total_published = self._counters['messages_published_total']
        total_processed = self._counters['messages_processed_total']
        total_dropped = self._counters['messages_dropped_total']
        
        if total_published > 0:
            success_rate = (total_processed / total_published) * 100
            drop_rate = (total_dropped / total_published) * 100
        else:
            success_rate = drop_rate = 0
        
        # Calculate average processing time across all topics
        all_processing_times = []
        for times in self._processing_times.values():
            all_processing_times.extend(times)
        
        avg_processing_time = statistics.mean(all_processing_times) if all_processing_times else 0
        
        return {
            'success_rate_pct': success_rate,
            'drop_rate_pct': drop_rate,
            'avg_processing_time_ms': avg_processing_time,
            'active_topics': len([t for t, m in self._topic_metrics.items() if m['last_activity'] > 0]),
            'health_score': min(100, success_rate - drop_rate)  # Simple health score
        }
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of data"""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = int(percentile * len(sorted_data))
        if index >= len(sorted_data):
            index = len(sorted_data) - 1
        
        return sorted_data[index]
    
    def reset_metrics(self):
        """Reset all metrics (useful for testing or periodic resets)"""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._messages_published.clear()
            self._messages_processed.clear()
            self._messages_dropped.clear()
            self._messages_unrouted.clear()
            self._processing_times.clear()
            self._serialization_times.clear()
            self._topic_metrics.clear()
            self._priority_metrics.clear()
            self._last_reset = time.time_ns()
    
    def get_top_topics(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top topics by activity"""
        with self._lock:
            topics = []
            for topic, metrics in self._topic_metrics.items():
                total_activity = metrics['published'] + metrics['processed']
                if total_activity > 0:
                    topics.append({
                        'topic': topic,
                        'published': metrics['published'],
                        'processed': metrics['processed'],
                        'dropped': metrics['dropped'],
                        'avg_latency_ms': metrics['avg_latency'],
                        'total_activity': total_activity
                    })
            
            # Sort by total activity
            topics.sort(key=lambda x: x['total_activity'], reverse=True)
            return topics[:limit]
    
    def export_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format"""
        metrics = self.get_metrics()
        lines = []
        
        # Counters
        for name, value in metrics['counters'].items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")
        
        # Gauges
        for name, value in metrics['gauges'].items():
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")
        
        # Rates
        for name, value in metrics['rates'].items():
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")
        
        return '\n'.join(lines)


class MessagingMetrics:
    """Backward-compatible facade used in tests.
    Wraps MessageMetrics and exposes higher-level convenience methods.
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._metrics = MessageMetrics(max_history=self.config.get('max_history', 10000))
        # Defaults for alert thresholds
        self._thresholds = {
            'min_messages_per_second': self.config.get('min_messages_per_second', 10000),
            'max_avg_latency_ms': self.config.get('max_avg_latency_ms', 5.0),
            'max_p99_latency_ms': self.config.get('max_p99_latency_ms', 20.0),
            'max_error_rate': self.config.get('max_error_rate', 0.01),
            'max_queue_depth': self.config.get('max_queue_depth', 10000),
        }

    # Passthrough helpers when needed by other parts of the system
    def get_metrics(self) -> Dict[str, Any]:
        return self._metrics.get_metrics()

    def reset_metrics(self):
        self._metrics.reset_metrics()

    # High-level summary used by tests
    def get_messaging_stats(self) -> Dict[str, Any]:
        m = self._metrics.get_metrics()
        messages_per_second = float(m['rates'].get('messages_processed_per_sec', 0.0))
        # Avg and p99 latency across topics
        latency_stats = m.get('latency_stats', {})
        all_means = [s.get('mean_ms', 0.0) for s in latency_stats.values() if s]
        all_p99s = [s.get('p99_ms', 0.0) for s in latency_stats.values() if s]
        avg_latency_ms = (sum(all_means) / len(all_means)) if all_means else 0.0
        p99_latency_ms = max(all_p99s) if all_p99s else 0.0
        # Queue depth: take max across priorities
        priorities = m.get('priorities', {})
        queue_depth = 0
        for p in priorities.values():
            try:
                queue_depth = max(queue_depth, int(p.get('queue_depth', 0)))
            except Exception:
                continue
        # Error rate
        counters = m.get('counters', {})
        published = int(counters.get('messages_published_total', 0))
        dropped = int(counters.get('messages_dropped_total', 0))
        error_rate = (dropped / published) if published > 0 else 0.0
        # Throughput (mbps): without payload sizes we conservatively return 0.0
        throughput_mbps = 0.0
        return {
            'messages_per_second': messages_per_second,
            'avg_latency_ms': avg_latency_ms,
            'p99_latency_ms': p99_latency_ms,
            'queue_depth': queue_depth,
            'error_rate': error_rate,
            'throughput_mbps': throughput_mbps,
        }

    def check_alert_conditions(self) -> Dict[str, Any]:
        stats = self.get_messaging_stats()
        alerts: List[Dict[str, Any]] = []
        # Check thresholds and add alerts
        if stats['messages_per_second'] < self._thresholds['min_messages_per_second']:
            alerts.append({'level': 'warning', 'metric': 'messages_per_second',
                           'value': stats['messages_per_second'],
                           'threshold': self._thresholds['min_messages_per_second']})
        if stats['avg_latency_ms'] > self._thresholds['max_avg_latency_ms']:
            alerts.append({'level': 'warning', 'metric': 'latency',
                           'value': stats['avg_latency_ms'],
                           'threshold': self._thresholds['max_avg_latency_ms']})
        if stats['p99_latency_ms'] > self._thresholds['max_p99_latency_ms']:
            alerts.append({'level': 'warning', 'metric': 'p99_latency',
                           'value': stats['p99_latency_ms'],
                           'threshold': self._thresholds['max_p99_latency_ms']})
        if stats['error_rate'] > self._thresholds['max_error_rate']:
            alerts.append({'level': 'warning', 'metric': 'error_rate',
                           'value': stats['error_rate'],
                           'threshold': self._thresholds['max_error_rate']})
        if stats['queue_depth'] > self._thresholds['max_queue_depth']:
            alerts.append({'level': 'info', 'metric': 'queue_depth',
                           'value': stats['queue_depth'],
                           'threshold': self._thresholds['max_queue_depth']})
        # Overall health
        if any(a['level'] == 'warning' for a in alerts):
            overall = 'warning'
        elif any(a['level'] == 'critical' for a in alerts):
            overall = 'critical'
        else:
            overall = 'good'
        return {'alerts': alerts, 'overall_health': overall}