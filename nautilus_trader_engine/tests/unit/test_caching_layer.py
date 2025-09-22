"""
Unit tests for caching layer components.
"""

import unittest
import time
import tempfile
import os
import shutil
from unittest.mock import Mock, patch, MagicMock
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from nautilus_trader_engine.tests.testing_framework import TestCase, unit_test
from nautilus_trader_engine.core.caching.cache_layer import (
    CacheLevel, CacheStrategy, CacheEntry, CacheBackend,
    MemoryCache, RedisCache, DiskCache, MultiLevelCache,
    CacheManager, get_cache_manager, cached
)


class TestCacheEntry(TestCase):
    """Test cases for CacheEntry."""

    @unit_test()
    def test_cache_entry_creation(self):
        """Test CacheEntry creation and basic properties."""
        entry = CacheEntry("test_key", "test_value", ttl=60)

        self.assertEqual(entry.key, "test_key")
        self.assertEqual(entry.value, "test_value")
        self.assertEqual(entry.ttl, 60)
        self.assertFalse(entry.is_expired())
        self.assertGreater(entry.created_at, 0)
        self.assertEqual(entry.access_count, 0)

    @unit_test()
    def test_cache_entry_expiration(self):
        """Test CacheEntry expiration."""
        # Test entry without TTL
        entry_no_ttl = CacheEntry("key1", "value1")
        self.assertFalse(entry_no_ttl.is_expired())

        # Test entry with TTL
        entry_with_ttl = CacheEntry("key2", "value2", ttl=0.1)  # 100ms TTL
        self.assertFalse(entry_with_ttl.is_expired())

        # Wait for expiration
        time.sleep(0.2)
        self.assertTrue(entry_with_ttl.is_expired())

    @unit_test()
    def test_cache_entry_access(self):
        """Test CacheEntry access tracking."""
        entry = CacheEntry("key", "value")

        self.assertEqual(entry.access_count, 0)
        initial_access_time = entry.last_accessed

        time.sleep(0.01)  # Small delay
        entry.access()

        self.assertEqual(entry.access_count, 1)
        self.assertGreater(entry.last_accessed, initial_access_time)


class TestMemoryCache(TestCase):
    """Test cases for MemoryCache."""

    def setUp(self):
        super().setUp()
        self.cache = MemoryCache(max_size=10, strategy=CacheStrategy.LRU)

    @unit_test()
    def test_memory_cache_basic_operations(self):
        """Test basic memory cache operations."""
        # Test set and get
        self.assertTrue(self.cache.set("key1", "value1"))
        self.assertEqual(self.cache.get("key1"), "value1")

        # Test get non-existent key
        self.assertIsNone(self.cache.get("nonexistent"))

        # Test delete
        self.assertTrue(self.cache.delete("key1"))
        self.assertIsNone(self.cache.get("key1"))

        # Test delete non-existent key
        self.assertFalse(self.cache.delete("nonexistent"))

    @unit_test()
    def test_memory_cache_ttl(self):
        """Test memory cache TTL functionality."""
        # Set entry with TTL
        self.cache.set("ttl_key", "ttl_value", ttl=0.1)

        # Should be available immediately
        self.assertEqual(self.cache.get("ttl_key"), "ttl_value")

        # Wait for expiration
        time.sleep(0.2)

        # Should be expired and removed
        self.assertIsNone(self.cache.get("ttl_key"))

    @unit_test()
    def test_memory_cache_lru_eviction(self):
        """Test LRU eviction strategy."""
        # Fill cache to max size
        for i in range(10):
            self.cache.set(f"key{i}", f"value{i}")

        # All entries should be present
        for i in range(10):
            self.assertEqual(self.cache.get(f"key{i}"), f"value{i}")

        # Add one more entry to trigger eviction
        self.cache.set("key10", "value10")

        # Cache should still have 10 entries (one evicted)
        self.assertEqual(len(self.cache.cache), 10)
        self.assertIsNone(self.cache.get("key0"))  # First entry should be evicted

    @unit_test()
    def test_memory_cache_lfu_eviction(self):
        """Test LFU eviction strategy."""
        cache = MemoryCache(max_size=3, strategy=CacheStrategy.LFU)

        # Add entries
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Access key1 multiple times
        cache.get("key1")
        cache.get("key1")
        cache.get("key1")

        # Access key2 once
        cache.get("key2")

        # Don't access key3

        # Add new entry to trigger eviction
        cache.set("key4", "value4")

        # key3 should be evicted (least frequently used)
        self.assertIsNone(cache.get("key3"))
        self.assertEqual(cache.get("key1"), "value1")
        self.assertEqual(cache.get("key2"), "value2")
        self.assertEqual(cache.get("key4"), "value4")

    @unit_test()
    def test_memory_cache_clear(self):
        """Test memory cache clear operation."""
        # Add some entries
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")

        # Verify entries exist
        self.assertEqual(self.cache.get("key1"), "value1")
        self.assertEqual(self.cache.get("key2"), "value2")

        # Clear cache
        self.cache.clear()

        # Verify cache is empty
        self.assertIsNone(self.cache.get("key1"))
        self.assertIsNone(self.cache.get("key2"))
        self.assertEqual(len(self.cache.cache), 0)

    @unit_test()
    def test_memory_cache_stats(self):
        """Test memory cache statistics."""
        # Add some entries
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")

        # Get one entry (hit)
        self.cache.get("key1")

        # Try to get non-existent entry (miss)
        self.cache.get("nonexistent")

        stats = self.cache.get_stats()

        self.assertEqual(stats["level"], "L1_MEMORY")
        self.assertEqual(stats["entries"], 2)
        self.assertEqual(stats["max_size"], 10)
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)
        self.assertGreater(stats["hit_rate"], 0)


class TestDiskCache(TestCase):
    """Test cases for DiskCache."""

    def setUp(self):
        super().setUp()
        self.temp_dir = tempfile.mkdtemp()
        self.cache = DiskCache(cache_dir=self.temp_dir, max_size_mb=1)

    def tearDown(self):
        super().tearDown()
        # Clean up temp directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @unit_test()
    def test_disk_cache_basic_operations(self):
        """Test basic disk cache operations."""
        # Test set and get
        self.assertTrue(self.cache.set("key1", "value1"))
        self.assertEqual(self.cache.get("key1"), "value1")

        # Test get non-existent key
        self.assertIsNone(self.cache.get("nonexistent"))

        # Test delete
        self.assertTrue(self.cache.delete("key1"))
        self.assertIsNone(self.cache.get("key1"))

    @unit_test()
    def test_disk_cache_complex_objects(self):
        """Test disk cache with complex objects."""
        test_data = {
            "numbers": [1, 2, 3, 4, 5],
            "nested": {
                "key": "value",
                "list": [1, 2, {"deep": "nested"}]
            },
            "string": "test string"
        }

        self.cache.set("complex_key", test_data)
        retrieved_data = self.cache.get("complex_key")

        self.assertEqual(retrieved_data, test_data)

    @unit_test()
    def test_disk_cache_eviction(self):
        """Test disk cache size-based eviction."""
        # Create a small cache for testing
        small_cache = DiskCache(cache_dir=self.temp_dir, max_size_mb=0.001)  # 1KB

        # Add a large entry
        large_data = "x" * 1000  # 1KB string
        small_cache.set("large_key", large_data)

        # Add another large entry (should trigger eviction)
        small_cache.set("another_key", large_data)

        # First entry should be evicted
        self.assertIsNone(small_cache.get("large_key"))
        self.assertEqual(small_cache.get("another_key"), large_data)


class TestMultiLevelCache(TestCase):
    """Test cases for MultiLevelCache."""

    def setUp(self):
        super().setUp()
        self.temp_dir = tempfile.mkdtemp()
        self.cache = MultiLevelCache(
            levels=[CacheLevel.L1_MEMORY, CacheLevel.L3_DISK],
            memory_size=5,
            disk_config={"cache_dir": self.temp_dir, "max_size_mb": 1}
        )

    def tearDown(self):
        super().tearDown()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @unit_test()
    def test_multilevel_cache_hierarchy(self):
        """Test multi-level cache hierarchy."""
        # Set value
        self.cache.set("test_key", "test_value")

        # Should be retrievable
        self.assertEqual(self.cache.get("test_key"), "test_value")

        # Check that it's in memory cache
        memory_cache = self.cache.caches[CacheLevel.L1_MEMORY]
        self.assertEqual(memory_cache.get("test_key"), "test_value")

    @unit_test()
    def test_multilevel_cache_deletion(self):
        """Test deletion across all levels."""
        # Set value in all levels
        self.cache.set("test_key", "test_value")

        # Delete from all levels
        self.assertTrue(self.cache.delete("test_key"))

        # Should not be retrievable
        self.assertIsNone(self.cache.get("test_key"))

    @unit_test()
    def test_multilevel_cache_clear(self):
        """Test clearing all cache levels."""
        # Set values
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")

        # Clear all levels
        self.cache.clear()

        # Should not be retrievable
        self.assertIsNone(self.cache.get("key1"))
        self.assertIsNone(self.cache.get("key2"))

    @unit_test()
    def test_multilevel_cache_stats(self):
        """Test multi-level cache statistics."""
        # Set and get some values
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")

        self.cache.get("key1")  # Hit
        self.cache.get("key2")  # Hit
        self.cache.get("nonexistent")  # Miss

        stats = self.cache.get_stats()

        self.assertIn("overall", stats)
        self.assertIn("levels", stats)
        self.assertEqual(stats["overall"]["total_hits"], 2)
        self.assertEqual(stats["overall"]["total_misses"], 1)


class TestCacheManager(TestCase):
    """Test cases for CacheManager."""

    def setUp(self):
        super().setUp()
        self.temp_dir = tempfile.mkdtemp()
        cache = MultiLevelCache(
            levels=[CacheLevel.L1_MEMORY],
            memory_size=10
        )
        self.cache_manager = CacheManager(cache)

    def tearDown(self):
        super().tearDown()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @unit_test()
    def test_cache_manager_decorator(self):
        """Test cache manager decorator."""
        call_count = 0

        @self.cache_manager.cached(ttl=60)
        def expensive_function(x, y):
            nonlocal call_count
            call_count += 1
            return x + y

        # First call
        result1 = expensive_function(5, 3)
        self.assertEqual(result1, 8)
        self.assertEqual(call_count, 1)

        # Second call (should use cache)
        result2 = expensive_function(5, 3)
        self.assertEqual(result2, 8)
        self.assertEqual(call_count, 1)  # Function should not be called again

    @unit_test()
    def test_cache_manager_key_generation(self):
        """Test cache key generation."""
        @self.cache_manager.cached()
        def test_function(a, b, c=None):
            return a + b + (c or 0)

        # Generate key
        key1 = self.cache_manager._generate_key(test_function, (1, 2), {"c": 3})
        key2 = self.cache_manager._generate_key(test_function, (1, 2), {"c": 3})

        # Keys should be identical for same inputs
        self.assertEqual(key1, key2)

        # Keys should be different for different inputs
        key3 = self.cache_manager._generate_key(test_function, (1, 2), {"c": 4})
        self.assertNotEqual(key1, key3)

    @unit_test()
    def test_cache_manager_function_invalidation(self):
        """Test function cache invalidation."""
        call_count = 0

        @self.cache_manager.cached()
        def test_function():
            nonlocal call_count
            call_count += 1
            return "result"

        # Call function twice (second should use cache)
        test_function()
        test_function()
        self.assertEqual(call_count, 1)

        # Invalidate cache
        self.cache_manager.invalidate_function_cache("test_function")

        # Next call should execute function again
        test_function()
        self.assertEqual(call_count, 2)

    @unit_test()
    def test_cache_manager_info(self):
        """Test cache manager information retrieval."""
        @self.cache_manager.cached(ttl=300)
        def test_function():
            return "test"

        # Call function to register it
        test_function()

        info = self.cache_manager.get_cache_info()

        self.assertIn("cached_functions", info)
        self.assertIn("cache_stats", info)
        self.assertIn("test_function", info["cached_functions"])


class TestRedisCache(TestCase):
    """Test cases for RedisCache."""

    def setUp(self):
        super().setUp()
        # Mock Redis for testing
        with patch('redis.Redis') as mock_redis:
            mock_instance = MagicMock()
            mock_instance.ping.return_value = True
            mock_redis.return_value = mock_instance

            self.cache = RedisCache()
            self.mock_redis = mock_instance

    @unit_test()
    def test_redis_cache_fallback(self):
        """Test Redis cache fallback to memory cache."""
        # Simulate Redis connection failure
        self.mock_redis.ping.side_effect = Exception("Connection failed")

        # Create cache (should fallback)
        cache = RedisCache()
        self.assertFalse(cache.available)

        # Should work with fallback cache
        cache.set("key", "value")
        self.assertEqual(cache.get("key"), "value")

    @unit_test()
    def test_redis_cache_operations(self):
        """Test Redis cache operations when available."""
        # Test set
        self.mock_redis.set.return_value = True
        self.assertTrue(self.cache.set("key", "value"))

        # Test get
        import pickle
        mock_entry = CacheEntry("key", "value")
        self.mock_redis.get.return_value = pickle.dumps(mock_entry)
        self.assertEqual(self.cache.get("key"), "value")

        # Test delete
        self.mock_redis.delete.return_value = 1
        self.assertTrue(self.cache.delete("key"))

    @unit_test()
    def test_redis_cache_stats(self):
        """Test Redis cache statistics."""
        # Mock Redis info
        self.mock_redis.info.return_value = {
            'used_memory': 1024,
            'connected_clients': 5
        }

        # Mock hits and misses
        self.cache.hits = 10
        self.cache.misses = 5

        stats = self.cache.get_stats()

        self.assertEqual(stats["level"], "L2_REDIS")
        self.assertTrue(stats["available"])
        self.assertEqual(stats["hits"], 10)
        self.assertEqual(stats["misses"], 5)


if __name__ == "__main__":
    unittest.main()