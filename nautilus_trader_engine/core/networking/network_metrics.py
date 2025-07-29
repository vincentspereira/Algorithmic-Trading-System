"""
Network Metrics
Performance monitoring for networking components
"""

import asyncio
import psutil
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import logging


class NetworkProtocol(Enum):
    """Network protocols for metrics"""
    TCP = "tcp"
    UDP = "udp"
    KERNEL_BYPASS = "kernel_bypass"


@dataclass
class NetworkMetricPoint:
    """Network metric data point"""
    timestamp: float
    value: float
    protocol: Optional[NetworkProtocol] = None
    operation: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()


class NetworkMetrics:
    """
    Comprehensive network performance metrics
    
    Features:
    - Connection lifecycle tracking
    - Latency and throughput monitoring
    - Protocol-specific metrics
    - System-level network statistics
    - Real-time performance analysis
    """
    
    def __init__(self, max_history: int = 10000):
        self.max_history = max_history
        
        # Metrics storage
        self._connection_metrics = defaultdict(lambda: {
            'created': 0,
            'closed': 0,
            'errors': 0,
            'active': 0
        })
        
        self._message_metrics = defaultdict(lambda: {
            'sent': 0,
            'received': 0,
            'bytes_sent': 0,
            'bytes_received': 0,
            'send_errors': 0,
            'receive_errors': 0
        })
        
        self._latency_metrics = defaultdict(lambda: deque(maxlen=max_history))
        self._throughput_metrics = defaultdict(lambda: deque(maxlen=max_history))
        
        # System metrics
        self._system_metrics = {
            'network_io': deque(maxlen=max_history),
            'tcp_connections': deque(maxlen=max_history),
            'udp_sockets': deque(maxlen=max_history),
            'network_errors': deque(maxlen=max_history)
        }
        
        # Background tasks
        self._collection_task: Optional[asyncio.Task] = None
        self._running = False
        
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Start metrics collection"""
        if self._running:
            return
        
        self._running = True
        
        # Start background collection
        self._collection_task = asyncio.create_task(self._collection_worker())
        
        self.logger.info("Network metrics collection started")
    
    async def stop(self):
        """Stop metrics collection"""
        self._running = False
        
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Network metrics collection stopped")
    
    def record_connection_created(self, protocol: NetworkProtocol, latency_ns: int):
        """Record connection creation"""
        self._connection_metrics[protocol]['created'] += 1
        self._connection_metrics[protocol]['active'] += 1
        
        # Record latency
        latency_ms = latency_ns / 1_000_000
        self._latency_metrics[f"{protocol.value}_connect"].append(
            NetworkMetricPoint(time.time(), latency_ms, protocol, "connect")
        )
    
    def record_connection_closed(self, protocol: NetworkProtocol):
        """Record connection closure"""
        self._connection_metrics[protocol]['closed'] += 1
        self._connection_metrics[protocol]['active'] = max(0, 
            self._connection_metrics[protocol]['active'] - 1)
    
    def record_connection_error(self, protocol: NetworkProtocol, error: str):
        """Record connection error"""
        self._connection_metrics[protocol]['errors'] += 1
        self.logger.debug(f"Connection error for {protocol.value}: {error}")
    
    def record_message_sent(self, bytes_sent: int, latency_ns: int):
        """Record message sent"""
        protocol = NetworkProtocol.TCP  # Default, could be parameterized
        
        self._message_metrics[protocol]['sent'] += 1
        self._message_metrics[protocol]['bytes_sent'] += bytes_sent
        
        # Record latency
        latency_ms = latency_ns / 1_000_000
        self._latency_metrics[f"{protocol.value}_send"].append(
            NetworkMetricPoint(time.time(), latency_ms, protocol, "send")
        )
        
        # Record throughput
        self._throughput_metrics[f"{protocol.value}_send"].append(
            NetworkMetricPoint(time.time(), bytes_sent, protocol, "send")
        )
    
    def record_message_received(self, bytes_received: int, latency_ns: int):
        """Record message received"""
        protocol = NetworkProtocol.TCP  # Default, could be parameterized
        
        self._message_metrics[protocol]['received'] += 1
        self._message_metrics[protocol]['bytes_received'] += bytes_received
        
        # Record latency
        latency_ms = latency_ns / 1_000_000
        self._latency_metrics[f"{protocol.value}_receive"].append(
            NetworkMetricPoint(time.time(), latency_ms, protocol, "receive")
        )
        
        # Record throughput
        self._throughput_metrics[f"{protocol.value}_receive"].append(
            NetworkMetricPoint(time.time(), bytes_received, protocol, "receive")
        )
    
    def record_send_error(self, error: str):
        """Record send error"""
        protocol = NetworkProtocol.TCP  # Default
        self._message_metrics[protocol]['send_errors'] += 1
        self.logger.debug(f"Send error: {error}")
    
    def record_receive_error(self, error: str):
        """Record receive error"""
        protocol = NetworkProtocol.TCP  # Default
        self._message_metrics[protocol]['receive_errors'] += 1
        self.logger.debug(f"Receive error: {error}")
    
    async def collect_system_metrics(self):
        """Collect system-level network metrics"""
        try:
            current_time = time.time()
            
            # Network I/O statistics
            net_io = psutil.net_io_counters()
            if net_io:
                self._system_metrics['network_io'].append(
                    NetworkMetricPoint(current_time, {
                        'bytes_sent': net_io.bytes_sent,
                        'bytes_recv': net_io.bytes_recv,
                        'packets_sent': net_io.packets_sent,
                        'packets_recv': net_io.packets_recv,
                        'errin': net_io.errin,
                        'errout': net_io.errout,
                        'dropin': net_io.dropin,
                        'dropout': net_io.dropout
                    })
                )
            
            # Connection statistics
            connections = psutil.net_connections()
            tcp_count = sum(1 for conn in connections if conn.type == socket.SOCK_STREAM)
            udp_count = sum(1 for conn in connections if conn.type == socket.SOCK_DGRAM)
            
            self._system_metrics['tcp_connections'].append(
                NetworkMetricPoint(current_time, tcp_count)
            )
            self._system_metrics['udp_sockets'].append(
                NetworkMetricPoint(current_time, udp_count)
            )
            
            # Network interface statistics
            net_if_stats = psutil.net_if_stats()
            total_errors = 0
            for interface, stats in net_if_stats.items():
                if stats.isup:
                    # This would need to be expanded to track per-interface errors
                    pass
            
            self._system_metrics['network_errors'].append(
                NetworkMetricPoint(current_time, total_errors)
            )
            
        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")
    
    async def _collection_worker(self):
        """Background worker for metrics collection"""
        while self._running:
            try:
                await self.collect_system_metrics()
                await asyncio.sleep(1)  # Collect every second
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Metrics collection worker error: {e}")
                await asyncio.sleep(5)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive network statistics"""
        current_time = time.time()
        
        # Calculate connection statistics
        connection_stats = {}
        for protocol, metrics in self._connection_metrics.items():
            connection_stats[protocol.value] = {
                'total_created': metrics['created'],
                'total_closed': metrics['closed'],
                'currently_active': metrics['active'],
                'total_errors': metrics['errors'],
                'success_rate': (metrics['created'] - metrics['errors']) / max(1, metrics['created']) * 100
            }
        
        # Calculate message statistics
        message_stats = {}
        for protocol, metrics in self._message_metrics.items():
            total_messages = metrics['sent'] + metrics['received']
            total_errors = metrics['send_errors'] + metrics['receive_errors']
            
            message_stats[protocol.value] = {
                'messages_sent': metrics['sent'],
                'messages_received': metrics['received'],
                'bytes_sent': metrics['bytes_sent'],
                'bytes_received': metrics['bytes_received'],
                'send_errors': metrics['send_errors'],
                'receive_errors': metrics['receive_errors'],
                'error_rate': (total_errors / max(1, total_messages)) * 100,
                'avg_message_size_sent': metrics['bytes_sent'] / max(1, metrics['sent']),
                'avg_message_size_received': metrics['bytes_received'] / max(1, metrics['received'])
            }
        
        # Calculate latency statistics
        latency_stats = {}
        for metric_name, points in self._latency_metrics.items():
            if points:
                recent_points = [p.value for p in points if current_time - p.timestamp < 60]  # Last minute
                if recent_points:
                    latency_stats[metric_name] = {
                        'avg_ms': sum(recent_points) / len(recent_points),
                        'min_ms': min(recent_points),
                        'max_ms': max(recent_points),
                        'p50_ms': self._percentile(recent_points, 50),
                        'p95_ms': self._percentile(recent_points, 95),
                        'p99_ms': self._percentile(recent_points, 99),
                        'sample_count': len(recent_points)
                    }
        
        # Calculate throughput statistics
        throughput_stats = {}
        for metric_name, points in self._throughput_metrics.items():
            if points:
                recent_points = [p.value for p in points if current_time - p.timestamp < 60]  # Last minute
                if recent_points:
                    total_bytes = sum(recent_points)
                    throughput_stats[metric_name] = {
                        'bytes_per_second': total_bytes / 60,  # Average over last minute
                        'messages_per_second': len(recent_points) / 60,
                        'total_bytes': total_bytes,
                        'sample_count': len(recent_points)
                    }
        
        # Get system statistics
        system_stats = {}
        for metric_name, points in self._system_metrics.items():
            if points:
                latest_point = points[-1]
                system_stats[metric_name] = {
                    'current_value': latest_point.value,
                    'timestamp': latest_point.timestamp
                }
        
        return {
            'timestamp': current_time,
            'connections': connection_stats,
            'messages': message_stats,
            'latency': latency_stats,
            'throughput': throughput_stats,
            'system': system_stats,
            'health_score': self._calculate_health_score()
        }
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of data"""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower_index = int(index)
            upper_index = lower_index + 1
            weight = index - lower_index
            
            if upper_index < len(sorted_data):
                return sorted_data[lower_index] * (1 - weight) + sorted_data[upper_index] * weight
            else:
                return sorted_data[lower_index]
    
    def _calculate_health_score(self) -> float:
        """Calculate overall network health score (0-100)"""
        score = 100.0
        current_time = time.time()
        
        # Penalize high error rates
        total_errors = 0
        total_operations = 0
        
        for protocol, metrics in self._connection_metrics.items():
            total_errors += metrics['errors']
            total_operations += metrics['created']
        
        for protocol, metrics in self._message_metrics.items():
            total_errors += metrics['send_errors'] + metrics['receive_errors']
            total_operations += metrics['sent'] + metrics['received']
        
        if total_operations > 0:
            error_rate = (total_errors / total_operations) * 100
            if error_rate > 5:  # More than 5% error rate
                score -= min(50, error_rate * 2)  # Penalize up to 50 points
        
        # Penalize high latency
        for metric_name, points in self._latency_metrics.items():
            if points:
                recent_points = [p.value for p in points if current_time - p.timestamp < 60]
                if recent_points:
                    avg_latency = sum(recent_points) / len(recent_points)
                    if avg_latency > 10:  # More than 10ms average latency
                        score -= min(30, (avg_latency - 10) * 2)  # Penalize up to 30 points
        
        return max(0.0, min(100.0, score))
    
    def get_time_series(self, metric_name: str, duration_seconds: int = 3600) -> List[NetworkMetricPoint]:
        """Get time series data for a specific metric"""
        cutoff_time = time.time() - duration_seconds
        
        # Check latency metrics
        if metric_name in self._latency_metrics:
            return [point for point in self._latency_metrics[metric_name] 
                   if point.timestamp >= cutoff_time]
        
        # Check throughput metrics
        if metric_name in self._throughput_metrics:
            return [point for point in self._throughput_metrics[metric_name] 
                   if point.timestamp >= cutoff_time]
        
        # Check system metrics
        if metric_name in self._system_metrics:
            return [point for point in self._system_metrics[metric_name] 
                   if point.timestamp >= cutoff_time]
        
        return []
    
    def reset_metrics(self):
        """Reset all metrics (useful for testing)"""
        self._connection_metrics.clear()
        self._message_metrics.clear()
        self._latency_metrics.clear()
        self._throughput_metrics.clear()
        
        for metric_list in self._system_metrics.values():
            metric_list.clear()
    
    def export_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format"""
        lines = []
        current_stats = self.get_stats()
        
        # Connection metrics
        for protocol, stats in current_stats['connections'].items():
            lines.append(f"# TYPE network_connections_created_total counter")
            lines.append(f'network_connections_created_total{{protocol="{protocol}"}} {stats["total_created"]}')
            
            lines.append(f"# TYPE network_connections_active gauge")
            lines.append(f'network_connections_active{{protocol="{protocol}"}} {stats["currently_active"]}')
            
            lines.append(f"# TYPE network_connection_success_rate_percent gauge")
            lines.append(f'network_connection_success_rate_percent{{protocol="{protocol}"}} {stats["success_rate"]}')
        
        # Message metrics
        for protocol, stats in current_stats['messages'].items():
            lines.append(f"# TYPE network_messages_sent_total counter")
            lines.append(f'network_messages_sent_total{{protocol="{protocol}"}} {stats["messages_sent"]}')
            
            lines.append(f"# TYPE network_bytes_sent_total counter")
            lines.append(f'network_bytes_sent_total{{protocol="{protocol}"}} {stats["bytes_sent"]}')
            
            lines.append(f"# TYPE network_message_error_rate_percent gauge")
            lines.append(f'network_message_error_rate_percent{{protocol="{protocol}"}} {stats["error_rate"]}')
        
        # Latency metrics
        for metric_name, stats in current_stats['latency'].items():
            lines.append(f"# TYPE network_latency_ms gauge")
            lines.append(f'network_latency_ms{{metric="{metric_name}",percentile="avg"}} {stats["avg_ms"]}')
            lines.append(f'network_latency_ms{{metric="{metric_name}",percentile="p95"}} {stats["p95_ms"]}')
            lines.append(f'network_latency_ms{{metric="{metric_name}",percentile="p99"}} {stats["p99_ms"]}')
        
        # Health score
        lines.append(f"# TYPE network_health_score gauge")
        lines.append(f"network_health_score {current_stats['health_score']}")
        
        return '\n'.join(lines)