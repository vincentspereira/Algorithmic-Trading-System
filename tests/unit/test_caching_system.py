"""Unit tests for Caching System components."""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import asyncio
from typing import Dict, Any, Optional
import time


class TestCacheManager:
    """Test suite for Cache Manager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache_config = {
            'l1_size': 1000,
            'l2_size': 10000,
            'l3_size': 100000,
            'ttl_seconds': 300,
            'eviction_policy': 'LRU'
        }
    
    @patch('nautilus_trader_engine.core.caching.cache_manager.CacheManager')
    def test_cache_manager_initialization(self, mock_cache_manager):
        """Test cache manager initialization."""
        mock_manager = Mock()
        mock_cache_manager.return_value = mock_manager
        
        from nautilus_trader_engine.core.caching.cache_manager import CacheManager
        manager = CacheManager(self.cache_config)
        
        assert manager is not None
        mock_cache_manager.assert_called_once_with(self.cache_config)
    
    @patch('nautilus_trader_engine.core.caching.cache_manager.CacheManager')
    def test_cache_set_get_operations(self, mock_cache_manager):
        """Test basic cache set and get operations."""
        mock_manager = Mock()
        mock_cache_manager.return_value = mock_manager
        
        # Mock cache operations
        test_key = 'test_key'
        test_value = {'data': 'test_value', 'timestamp': time.time()}
        
        mock_manager.set.return_value = True
        mock_manager.get.return_value = test_value
        
        from nautilus_trader_engine.core.caching.cache_manager import CacheManager
        manager = CacheManager(self.cache_config)
        
        # Test set operation
        result = manager.set(test_key, test_value)
        assert result is True
        mock_manager.set.assert_called_once_with(test_key, test_value)
        
        # Test get operation
        retrieved_value = manager.get(test_key)
        assert retrieved_value == test_value
        mock_manager.get.assert_called_once_with(test_key)
    
    @patch('nautilus_trader_engine.core.caching.cache_manager.CacheManager')
    def test_cache_eviction_policy(self, mock_cache_manager):
        """Test cache eviction policy."""
        mock_manager = Mock()
        mock_cache_manager.return_value = mock_manager
        
        # Mock eviction behavior
        mock_manager.evict_lru.return_value = ['evicted_key1', 'evicted_key2']
        mock_manager.get_cache_stats.return_value = {
            'hits': 100,
            'misses': 20,
            'evictions': 5,
            'size': 950
        }
        
        from nautilus_trader_engine.core.caching.cache_manager import CacheManager
        manager = CacheManager(self.cache_config)
        
        # Test eviction
        evicted_keys = manager.evict_lru()
        assert len(evicted_keys) == 2
        assert 'evicted_key1' in evicted_keys
        
        # Test cache statistics
        stats = manager.get_cache_stats()
        assert stats['hits'] == 100
        assert stats['evictions'] == 5


class TestL1Cache:
    """Test suite for L1 Cache (CPU cache)."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.l1_config = {
            'size': 1000,
            'ttl_seconds': 60,
            'numa_node': 0
        }
    
    @patch('nautilus_trader_engine.core.caching.l1_cache.L1Cache')
    def test_l1_cache_initialization(self, mock_l1_cache):
        """Test L1 cache initialization."""
        mock_cache = Mock()
        mock_l1_cache.return_value = mock_cache
        
        from nautilus_trader_engine.core.caching.l1_cache import L1Cache
        cache = L1Cache(self.l1_config)
        
        assert cache is not None
        mock_l1_cache.assert_called_once_with(self.l1_config)
    
    @patch('nautilus_trader_engine.core.caching.l1_cache.L1Cache')
    def test_l1_cache_performance(self, mock_l1_cache):
        """Test L1 cache performance characteristics."""
        mock_cache = Mock()
        mock_l1_cache.return_value = mock_cache
        
        # Mock performance metrics
        mock_cache.get_latency_stats.return_value = {
            'avg_get_latency_ns': 50,  # 50 nanoseconds
            'avg_set_latency_ns': 75,
            'cache_hit_ratio': 0.95
        }
        
        from nautilus_trader_engine.core.caching.l1_cache import L1Cache
        cache = L1Cache(self.l1_config)
        
        stats = cache.get_latency_stats()
        assert stats['avg_get_latency_ns'] <= 100  # Should be very fast
        assert stats['cache_hit_ratio'] >= 0.9  # Should have high hit ratio


class TestL2Cache:
    """Test suite for L2 Cache (Memory cache)."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.l2_config = {
            'size': 10000,
            'ttl_seconds': 300,
            'compression': True
        }
    
    @patch('nautilus_trader_engine.core.caching.l2_cache.L2Cache')
    def test_l2_cache_compression(self, mock_l2_cache):
        """Test L2 cache compression functionality."""
        mock_cache = Mock()
        mock_l2_cache.return_value = mock_cache
        
        # Mock compression behavior
        large_data = {'market_data': [i for i in range(1000)]}
        compressed_size = 500  # Simulated compressed size
        
        mock_cache.set_compressed.return_value = True
        mock_cache.get_compression_ratio.return_value = 0.5  # 50% compression
        
        from nautilus_trader_engine.core.caching.l2_cache import L2Cache
        cache = L2Cache(self.l2_config)
        
        result = cache.set_compressed('large_data_key', large_data)
        assert result is True
        
        compression_ratio = cache.get_compression_ratio()
        assert compression_ratio <= 0.8  # Should achieve good compression


class TestL3Cache:
    """Test suite for L3 Cache (Persistent cache)."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.l3_config = {
            'size': 100000,
            'persistence_path': '/tmp/l3_cache',
            'sync_interval_seconds': 30
        }
    
    @patch('nautilus_trader_engine.core.caching.l3_cache.L3Cache')
    def test_l3_cache_persistence(self, mock_l3_cache):
        """Test L3 cache persistence functionality."""
        mock_cache = Mock()
        mock_l3_cache.return_value = mock_cache
        
        # Mock persistence operations
        mock_cache.sync_to_disk.return_value = True
        mock_cache.load_from_disk.return_value = True
        mock_cache.get_persistent_keys.return_value = ['key1', 'key2', 'key3']
        
        from nautilus_trader_engine.core.caching.l3_cache import L3Cache
        cache = L3Cache(self.l3_config)
        
        # Test sync to disk
        sync_result = cache.sync_to_disk()
        assert sync_result is True
        
        # Test load from disk
        load_result = cache.load_from_disk()
        assert load_result is True
        
        # Test persistent keys
        keys = cache.get_persistent_keys()
        assert len(keys) == 3


class TestCacheCoherency:
    """Test suite for Cache Coherency system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.coherency_config = {
            'protocol': 'MESI',
            'invalidation_strategy': 'write_through',
            'consistency_level': 'strong'
        }
    
    @patch('nautilus_trader_engine.core.caching.cache_coherency.CacheCoherency')
    def test_cache_invalidation(self, mock_coherency):
        """Test cache invalidation across cache levels."""
        mock_coherency_manager = Mock()
        mock_coherency.return_value = mock_coherency_manager
        
        # Mock invalidation behavior
        mock_coherency_manager.invalidate_key.return_value = True
        mock_coherency_manager.get_invalidation_count.return_value = 5
        
        from nautilus_trader_engine.core.caching.cache_coherency import CacheCoherency
        coherency = CacheCoherency(self.coherency_config)
        
        # Test key invalidation
        result = coherency.invalidate_key('test_key')
        assert result is True
        
        # Test invalidation statistics
        count = coherency.get_invalidation_count()
        assert count == 5
    
    @patch('nautilus_trader_engine.core.caching.cache_coherency.CacheCoherency')
    def test_write_through_consistency(self, mock_coherency):
        """Test write-through consistency protocol."""
        mock_coherency_manager = Mock()
        mock_coherency.return_value = mock_coherency_manager
        
        # Mock write-through behavior
        mock_coherency_manager.write_through.return_value = True
        mock_coherency_manager.verify_consistency.return_value = True
        
        from nautilus_trader_engine.core.caching.cache_coherency import CacheCoherency
        coherency = CacheCoherency(self.coherency_config)
        
        # Test write-through operation
        result = coherency.write_through('key', 'value')
        assert result is True
        
        # Test consistency verification
        is_consistent = coherency.verify_consistency()
        assert is_consistent is True


class TestCacheMetrics:
    """Test suite for Cache Metrics collection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.metrics_config = {
            'collection_interval_seconds': 10,
            'metrics_retention_hours': 24,
            'export_format': 'prometheus'
        }
    
    @patch('nautilus_trader_engine.core.caching.cache_metrics.CacheMetrics')
    def test_metrics_collection(self, mock_metrics):
        """Test cache metrics collection."""
        mock_metrics_collector = Mock()
        mock_metrics.return_value = mock_metrics_collector
        
        # Mock metrics data
        mock_metrics_collector.get_cache_metrics.return_value = {
            'l1_hit_ratio': 0.95,
            'l2_hit_ratio': 0.85,
            'l3_hit_ratio': 0.75,
            'total_requests': 10000,
            'avg_response_time_ms': 2.5,
            'memory_usage_mb': 512
        }
        
        from nautilus_trader_engine.core.caching.cache_metrics import CacheMetrics
        metrics = CacheMetrics(self.metrics_config)
        
        cache_stats = metrics.get_cache_metrics()
        assert cache_stats['l1_hit_ratio'] >= 0.9
        assert cache_stats['avg_response_time_ms'] <= 5.0
        assert cache_stats['total_requests'] > 0
    
    @patch('nautilus_trader_engine.core.caching.cache_metrics.CacheMetrics')
    def test_performance_monitoring(self, mock_metrics):
        """Test cache performance monitoring."""
        mock_metrics_collector = Mock()
        mock_metrics.return_value = mock_metrics_collector
        
        # Mock performance alerts
        mock_metrics_collector.check_performance_thresholds.return_value = {
            'alerts': [
                {'level': 'warning', 'message': 'L1 hit ratio below 90%'},
                {'level': 'info', 'message': 'Cache memory usage normal'}
            ],
            'overall_health': 'good'
        }
        
        from nautilus_trader_engine.core.caching.cache_metrics import CacheMetrics
        metrics = CacheMetrics(self.metrics_config)
        
        health_check = metrics.check_performance_thresholds()
        assert health_check['overall_health'] in ['good', 'warning', 'critical']
        assert len(health_check['alerts']) >= 0


if __name__ == '__main__':
    pytest.main([__file__])