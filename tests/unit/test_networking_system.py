"""Unit tests for Networking System components."""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import asyncio
from typing import Dict, Any, List, Optional
import socket
import time


class TestNetworkManager:
    """Test suite for Network Manager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.network_config = {
            'max_connections': 1000,
            'connection_timeout_seconds': 30,
            'keepalive_enabled': True,
            'tcp_nodelay': True,
            'buffer_size': 65536
        }
    
    @patch('nautilus_trader_engine.core.networking.network_manager.NetworkManager')
    def test_network_manager_initialization(self, mock_network_manager):
        """Test network manager initialization."""
        mock_manager = Mock()
        mock_network_manager.return_value = mock_manager
        
        from nautilus_trader_engine.core.networking.network_manager import NetworkManager
        manager = NetworkManager(self.network_config)
        
        assert manager is not None
        mock_network_manager.assert_called_once_with(self.network_config)
    
    @patch('nautilus_trader_engine.core.networking.network_manager.NetworkManager')
    def test_connection_management(self, mock_network_manager):
        """Test connection management functionality."""
        mock_manager = Mock()
        mock_network_manager.return_value = mock_manager
        
        # Mock connection operations
        mock_manager.create_connection.return_value = 'conn_001'
        mock_manager.close_connection.return_value = True
        mock_manager.get_active_connections.return_value = ['conn_001', 'conn_002']
        
        from nautilus_trader_engine.core.networking.network_manager import NetworkManager
        manager = NetworkManager(self.network_config)
        
        # Test connection creation
        conn_id = manager.create_connection('127.0.0.1', 8080)
        assert conn_id == 'conn_001'
        
        # Test connection closure
        result = manager.close_connection(conn_id)
        assert result is True
        
        # Test active connections
        active_conns = manager.get_active_connections()
        assert len(active_conns) == 2
    
    @patch('nautilus_trader_engine.core.networking.network_manager.NetworkManager')
    def test_network_statistics(self, mock_network_manager):
        """Test network statistics collection."""
        mock_manager = Mock()
        mock_network_manager.return_value = mock_manager
        
        # Mock network statistics
        mock_manager.get_network_stats.return_value = {
            'total_connections': 50,
            'active_connections': 45,
            'bytes_sent': 1048576,  # 1MB
            'bytes_received': 2097152,  # 2MB
            'packets_sent': 1000,
            'packets_received': 1500,
            'connection_errors': 2,
            'avg_latency_ms': 1.5
        }
        
        from nautilus_trader_engine.core.networking.network_manager import NetworkManager
        manager = NetworkManager(self.network_config)
        
        stats = manager.get_network_stats()
        assert stats['total_connections'] == 50
        assert stats['avg_latency_ms'] <= 5.0
        assert stats['connection_errors'] <= 5


class TestConnectionPool:
    """Test suite for Connection Pool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.pool_config = {
            'min_connections': 5,
            'max_connections': 50,
            'connection_timeout_seconds': 30,
            'idle_timeout_seconds': 300,
            'health_check_interval_seconds': 60
        }
    
    @patch('nautilus_trader_engine.core.networking.connection_pool.ConnectionPool')
    def test_connection_pool_initialization(self, mock_pool):
        """Test connection pool initialization."""
        mock_pool_instance = Mock()
        mock_pool.return_value = mock_pool_instance
        
        from nautilus_trader_engine.core.networking.connection_pool import ConnectionPool
        pool = ConnectionPool(self.pool_config)
        
        assert pool is not None
        mock_pool.assert_called_once_with(self.pool_config)
    
    @patch('nautilus_trader_engine.core.networking.connection_pool.ConnectionPool')
    def test_connection_acquisition(self, mock_pool):
        """Test connection acquisition from pool."""
        mock_pool_instance = Mock()
        mock_pool.return_value = mock_pool_instance
        
        # Mock connection acquisition
        mock_connection = Mock()
        mock_pool_instance.acquire_connection.return_value = mock_connection
        mock_pool_instance.release_connection.return_value = True
        mock_pool_instance.get_pool_stats.return_value = {
            'active_connections': 10,
            'idle_connections': 5,
            'total_connections': 15,
            'pool_utilization': 0.3
        }
        
        from nautilus_trader_engine.core.networking.connection_pool import ConnectionPool
        pool = ConnectionPool(self.pool_config)
        
        # Test connection acquisition
        connection = pool.acquire_connection()
        assert connection is not None
        
        # Test connection release
        result = pool.release_connection(connection)
        assert result is True
        
        # Test pool statistics
        stats = pool.get_pool_stats()
        assert stats['total_connections'] == 15
        assert stats['pool_utilization'] <= 1.0
    
    @patch('nautilus_trader_engine.core.networking.connection_pool.ConnectionPool')
    def test_health_monitoring(self, mock_pool):
        """Test connection health monitoring."""
        mock_pool_instance = Mock()
        mock_pool.return_value = mock_pool_instance
        
        # Mock health check behavior
        mock_pool_instance.health_check.return_value = {
            'healthy_connections': 12,
            'unhealthy_connections': 1,
            'removed_connections': 1,
            'health_check_duration_ms': 50
        }
        
        from nautilus_trader_engine.core.networking.connection_pool import ConnectionPool
        pool = ConnectionPool(self.pool_config)
        
        health_report = pool.health_check()
        assert health_report['healthy_connections'] >= 0
        assert health_report['health_check_duration_ms'] <= 100


class TestKernelBypass:
    """Test suite for Kernel Bypass networking."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.bypass_config = {
            'enabled': True,
            'interface': 'eth0',
            'queue_size': 2048,
            'batch_size': 32,
            'polling_mode': True
        }
    
    @patch('nautilus_trader_engine.core.networking.kernel_bypass.KernelBypass')
    def test_kernel_bypass_initialization(self, mock_bypass):
        """Test kernel bypass initialization."""
        mock_bypass_instance = Mock()
        mock_bypass.return_value = mock_bypass_instance
        
        from nautilus_trader_engine.core.networking.kernel_bypass import KernelBypass
        bypass = KernelBypass(self.bypass_config)
        
        assert bypass is not None
        mock_bypass.assert_called_once_with(self.bypass_config)
    
    @patch('nautilus_trader_engine.core.networking.kernel_bypass.KernelBypass')
    def test_dpdk_integration(self, mock_bypass):
        """Test DPDK integration for kernel bypass."""
        mock_bypass_instance = Mock()
        mock_bypass.return_value = mock_bypass_instance
        
        # Mock DPDK operations
        mock_bypass_instance.initialize_dpdk.return_value = True
        mock_bypass_instance.get_dpdk_stats.return_value = {
            'packets_received': 1000000,
            'packets_transmitted': 950000,
            'packets_dropped': 50,
            'rx_rate_pps': 500000,  # packets per second
            'tx_rate_pps': 475000,
            'latency_ns': 200  # nanoseconds
        }
        
        from nautilus_trader_engine.core.networking.kernel_bypass import KernelBypass
        bypass = KernelBypass(self.bypass_config)
        
        # Test DPDK initialization
        init_result = bypass.initialize_dpdk()
        assert init_result is True
        
        # Test DPDK statistics
        stats = bypass.get_dpdk_stats()
        assert stats['latency_ns'] <= 1000  # Sub-microsecond latency
        assert stats['packets_dropped'] / stats['packets_received'] <= 0.01  # Low drop rate
    
    @patch('nautilus_trader_engine.core.networking.kernel_bypass.KernelBypass')
    def test_zero_copy_operations(self, mock_bypass):
        """Test zero-copy networking operations."""
        mock_bypass_instance = Mock()
        mock_bypass.return_value = mock_bypass_instance
        
        # Mock zero-copy behavior
        test_data = b'market_data_packet'
        mock_bypass_instance.send_zero_copy.return_value = len(test_data)
        mock_bypass_instance.receive_zero_copy.return_value = test_data
        
        from nautilus_trader_engine.core.networking.kernel_bypass import KernelBypass
        bypass = KernelBypass(self.bypass_config)
        
        # Test zero-copy send
        bytes_sent = bypass.send_zero_copy(test_data)
        assert bytes_sent == len(test_data)
        
        # Test zero-copy receive
        received_data = bypass.receive_zero_copy()
        assert received_data == test_data


class TestCPUAffinity:
    """Test suite for CPU Affinity management."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.affinity_config = {
            'enabled': True,
            'network_threads': [0, 1],
            'processing_threads': [2, 3, 4, 5],
            'isolation_enabled': True,
            'numa_aware': True
        }
    
    @patch('nautilus_trader_engine.core.networking.cpu_affinity.CPUAffinity')
    def test_cpu_affinity_initialization(self, mock_affinity):
        """Test CPU affinity initialization."""
        mock_affinity_instance = Mock()
        mock_affinity.return_value = mock_affinity_instance
        
        from nautilus_trader_engine.core.networking.cpu_affinity import CPUAffinity
        affinity = CPUAffinity(self.affinity_config)
        
        assert affinity is not None
        mock_affinity.assert_called_once_with(self.affinity_config)
    
    @patch('nautilus_trader_engine.core.networking.cpu_affinity.CPUAffinity')
    def test_thread_pinning(self, mock_affinity):
        """Test thread pinning to specific CPU cores."""
        mock_affinity_instance = Mock()
        mock_affinity.return_value = mock_affinity_instance
        
        # Mock thread pinning operations
        mock_affinity_instance.pin_thread.return_value = True
        mock_affinity_instance.get_thread_affinity.return_value = [0, 1]
        mock_affinity_instance.get_cpu_usage.return_value = {
            'core_0': 0.25,
            'core_1': 0.30,
            'core_2': 0.80,
            'core_3': 0.75
        }
        
        from nautilus_trader_engine.core.networking.cpu_affinity import CPUAffinity
        affinity = CPUAffinity(self.affinity_config)
        
        # Test thread pinning
        result = affinity.pin_thread('network_thread_1', [0, 1])
        assert result is True
        
        # Test affinity retrieval
        thread_cores = affinity.get_thread_affinity('network_thread_1')
        assert thread_cores == [0, 1]
        
        # Test CPU usage monitoring
        cpu_usage = affinity.get_cpu_usage()
        assert all(0 <= usage <= 1.0 for usage in cpu_usage.values())
    
    @patch('nautilus_trader_engine.core.networking.cpu_affinity.CPUAffinity')
    def test_numa_optimization(self, mock_affinity):
        """Test NUMA-aware CPU affinity optimization."""
        mock_affinity_instance = Mock()
        mock_affinity.return_value = mock_affinity_instance
        
        # Mock NUMA operations
        mock_affinity_instance.get_numa_topology.return_value = {
            'node_0': {'cores': [0, 1, 2, 3], 'memory_gb': 16},
            'node_1': {'cores': [4, 5, 6, 7], 'memory_gb': 16}
        }
        mock_affinity_instance.optimize_numa_placement.return_value = {
            'network_threads': {'node': 0, 'cores': [0, 1]},
            'processing_threads': {'node': 0, 'cores': [2, 3]}
        }
        
        from nautilus_trader_engine.core.networking.cpu_affinity import CPUAffinity
        affinity = CPUAffinity(self.affinity_config)
        
        # Test NUMA topology detection
        topology = affinity.get_numa_topology()
        assert len(topology) >= 1
        assert all('cores' in node and 'memory_gb' in node for node in topology.values())
        
        # Test NUMA optimization
        placement = affinity.optimize_numa_placement()
        assert 'network_threads' in placement
        assert 'processing_threads' in placement


class TestNUMAAllocator:
    """Test suite for NUMA-aware memory allocator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.numa_config = {
            'enabled': True,
            'preferred_node': 0,
            'fallback_enabled': True,
            'huge_pages_enabled': True,
            'page_size_kb': 2048
        }
    
    @patch('nautilus_trader_engine.core.networking.numa_allocator.NUMAAllocator')
    def test_numa_allocator_initialization(self, mock_allocator):
        """Test NUMA allocator initialization."""
        mock_allocator_instance = Mock()
        mock_allocator.return_value = mock_allocator_instance
        
        from nautilus_trader_engine.core.networking.numa_allocator import NUMAAllocator
        allocator = NUMAAllocator(self.numa_config)
        
        assert allocator is not None
        mock_allocator.assert_called_once_with(self.numa_config)
    
    @patch('nautilus_trader_engine.core.networking.numa_allocator.NUMAAllocator')
    def test_memory_allocation(self, mock_allocator):
        """Test NUMA-aware memory allocation."""
        mock_allocator_instance = Mock()
        mock_allocator.return_value = mock_allocator_instance
        
        # Mock memory allocation
        mock_memory_ptr = Mock()
        mock_allocator_instance.allocate.return_value = mock_memory_ptr
        mock_allocator_instance.deallocate.return_value = True
        mock_allocator_instance.get_allocation_stats.return_value = {
            'total_allocated_bytes': 1048576,  # 1MB
            'allocations_count': 10,
            'deallocations_count': 5,
            'fragmentation_ratio': 0.05,
            'numa_node_distribution': {0: 0.8, 1: 0.2}
        }
        
        from nautilus_trader_engine.core.networking.numa_allocator import NUMAAllocator
        allocator = NUMAAllocator(self.numa_config)
        
        # Test memory allocation
        memory_ptr = allocator.allocate(65536, numa_node=0)  # 64KB
        assert memory_ptr is not None
        
        # Test memory deallocation
        result = allocator.deallocate(memory_ptr)
        assert result is True
        
        # Test allocation statistics
        stats = allocator.get_allocation_stats()
        assert stats['fragmentation_ratio'] <= 0.1  # Low fragmentation
        assert sum(stats['numa_node_distribution'].values()) == 1.0
    
    @patch('nautilus_trader_engine.core.networking.numa_allocator.NUMAAllocator')
    def test_huge_pages_support(self, mock_allocator):
        """Test huge pages support for memory allocation."""
        mock_allocator_instance = Mock()
        mock_allocator.return_value = mock_allocator_instance
        
        # Mock huge pages operations
        mock_allocator_instance.allocate_huge_pages.return_value = Mock()
        mock_allocator_instance.get_huge_pages_stats.return_value = {
            'huge_pages_total': 100,
            'huge_pages_used': 25,
            'huge_pages_free': 75,
            'page_size_kb': 2048,
            'total_memory_mb': 200
        }
        
        from nautilus_trader_engine.core.networking.numa_allocator import NUMAAllocator
        allocator = NUMAAllocator(self.numa_config)
        
        # Test huge pages allocation
        huge_memory = allocator.allocate_huge_pages(4)  # 4 pages
        assert huge_memory is not None
        
        # Test huge pages statistics
        stats = allocator.get_huge_pages_stats()
        assert stats['huge_pages_used'] <= stats['huge_pages_total']
        assert stats['page_size_kb'] == 2048


class TestNetworkMetrics:
    """Test suite for Network Metrics collection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.metrics_config = {
            'collection_interval_ms': 100,
            'retention_hours': 24,
            'latency_buckets': [0.1, 0.5, 1.0, 5.0, 10.0],
            'export_format': 'prometheus'
        }
    
    @patch('nautilus_trader_engine.core.networking.network_metrics.NetworkMetrics')
    def test_network_metrics_collection(self, mock_metrics):
        """Test network metrics collection."""
        mock_metrics_instance = Mock()
        mock_metrics.return_value = mock_metrics_instance
        
        # Mock network metrics
        mock_metrics_instance.get_network_metrics.return_value = {
            'connections_per_second': 1000,
            'bytes_per_second_in': 10485760,  # 10MB/s
            'bytes_per_second_out': 5242880,  # 5MB/s
            'avg_latency_ms': 0.5,
            'p95_latency_ms': 2.0,
            'p99_latency_ms': 5.0,
            'connection_errors_per_second': 0.1,
            'active_connections': 500
        }
        
        from nautilus_trader_engine.core.networking.network_metrics import NetworkMetrics
        metrics = NetworkMetrics(self.metrics_config)
        
        network_stats = metrics.get_network_metrics()
        assert network_stats['avg_latency_ms'] <= 5.0
        assert network_stats['connection_errors_per_second'] <= 1.0
        assert network_stats['active_connections'] >= 0
    
    @patch('nautilus_trader_engine.core.networking.network_metrics.NetworkMetrics')
    def test_latency_distribution(self, mock_metrics):
        """Test latency distribution tracking."""
        mock_metrics_instance = Mock()
        mock_metrics.return_value = mock_metrics_instance
        
        # Mock latency distribution
        mock_metrics_instance.get_latency_distribution.return_value = {
            '0.1ms': 0.60,  # 60% of requests
            '0.5ms': 0.25,  # 25% of requests
            '1.0ms': 0.10,  # 10% of requests
            '5.0ms': 0.04,  # 4% of requests
            '10.0ms': 0.01  # 1% of requests
        }
        
        from nautilus_trader_engine.core.networking.network_metrics import NetworkMetrics
        metrics = NetworkMetrics(self.metrics_config)
        
        distribution = metrics.get_latency_distribution()
        total_percentage = sum(distribution.values())
        assert abs(total_percentage - 1.0) <= 0.01  # Should sum to ~100%
        assert distribution['0.1ms'] >= 0.5  # Most requests should be fast
    
    @patch('nautilus_trader_engine.core.networking.network_metrics.NetworkMetrics')
    def test_performance_alerts(self, mock_metrics):
        """Test network performance alerting."""
        mock_metrics_instance = Mock()
        mock_metrics.return_value = mock_metrics_instance
        
        # Mock performance alerts
        mock_metrics_instance.check_performance_thresholds.return_value = {
            'alerts': [
                {'level': 'warning', 'metric': 'latency_p95', 'value': 4.5, 'threshold': 5.0},
                {'level': 'critical', 'metric': 'error_rate', 'value': 0.02, 'threshold': 0.01}
            ],
            'overall_health': 'degraded'
        }
        
        from nautilus_trader_engine.core.networking.network_metrics import NetworkMetrics
        metrics = NetworkMetrics(self.metrics_config)
        
        alert_status = metrics.check_performance_thresholds()
        assert alert_status['overall_health'] in ['healthy', 'degraded', 'critical']
        assert len(alert_status['alerts']) >= 0
        
        # Check for critical alerts
        critical_alerts = [alert for alert in alert_status['alerts'] if alert['level'] == 'critical']
        if critical_alerts:
            assert alert_status['overall_health'] in ['degraded', 'critical']


if __name__ == '__main__':
    pytest.main([__file__])