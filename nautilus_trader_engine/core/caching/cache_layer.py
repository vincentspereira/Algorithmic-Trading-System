"""
Intelligent Caching Layer for Nautilus Trader Engine
Provides multi-level caching with automatic invalidation and performance optimization.
"""

import hashlib
import json
import pickle
import time
from typing import Dict, List, Any, Optional, Callable, Tuple, Union, Type
from dataclasses import dataclass, field
from enum import Enum
import logging
from abc import ABC, abstractmethod
from threading import Lock
from collections import OrderedDict
import redis
import sqlite3
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor
import functools

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """Cache levels from fastest to slowest."""
    L1_MEMORY = "l1_memory"  # Fastest, smallest
    L2_REDIS = "l2_redis"    # Medium speed, larger
    L3_DISK = "l3_disk"      # Slowest, largest


class CacheStrategy(Enum):
    """Cache invalidation strategies."""
    LRU = "lru"                    # Least Recently Used
    LFU = "lfu"                    # Least Frequently Used
    TTL = "ttl"                    # Time To Live
    SIZE_BASED = "size_based"      # Size-based eviction
    ADAPTIVE = "adaptive"          # Adaptive strategy


class CacheEntry:
    """Cache entry with metadata."""

    def __init__(self, key: str, value: Any, ttl: Optional[float] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        self.key = key
        self.value = value
        self.created_at = time.time()
        self.last_accessed = time.time()
        self.access_count = 0
        self.ttl = ttl
        self.metadata = metadata or {}
        self.size_bytes = self._calculate_size()

    def _calculate_size(self) -> int:
        """Calculate approximate size of the entry in bytes."""
        try:
            # Use pickle to estimate size
            return len(pickle.dumps(self.value))
        except:
            # Fallback to string representation
            return len(str(self.value).encode('utf-8'))

    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl

    def access(self) -> None:
        """Mark entry as accessed."""
        self.last_accessed = time.time()
        self.access_count += 1

    def get_age(self) -> float:
        """Get age of entry in seconds."""
        return time.time() - self.created_at

    def get_idle_time(self) -> float:
        """Get idle time since last access in seconds."""
        return time.time() - self.last_accessed


class CacheBackend(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """Set value in cache."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all values from cache."""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        pass


class MemoryCache(CacheBackend):
    """In-memory cache with LRU eviction."""

    def __init__(self, max_size: int = 1000, strategy: CacheStrategy = CacheStrategy.LRU):
        self.max_size = max_size
        self.strategy = strategy
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = Lock()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def get(self, key: str) -> Optional[Any]:
        """Get value from memory cache."""
        with self._lock:
            if key in self.cache:
                entry = self.cache[key]
                if entry.is_expired():
                    del self.cache[key]
                    self.misses += 1
                    return None

                entry.access()
                if self.strategy == CacheStrategy.LRU:
                    self.cache.move_to_end(key)  # Mark as recently used

                self.hits += 1
                return entry.value
            else:
                self.misses += 1
                return None

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """Set value in memory cache."""
        with self._lock:
            entry = CacheEntry(key, value, ttl)

            # Check if we need to evict
            if key not in self.cache and len(self.cache) >= self.max_size:
                self._evict()

            self.cache[key] = entry
            if self.strategy == CacheStrategy.LRU:
                self.cache.move_to_end(key)

            return True

    def delete(self, key: str) -> bool:
        """Delete value from memory cache."""
        with self._lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear memory cache."""
        with self._lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
            self.evictions = 0

    def _evict(self) -> None:
        """Evict entries based on strategy."""
        if self.strategy == CacheStrategy.LRU:
            # Remove least recently used
            self.cache.popitem(last=False)
        elif self.strategy == CacheStrategy.LFU:
            # Remove least frequently used
            lfu_key = min(self.cache.keys(),
                         key=lambda k: self.cache[k].access_count)
            del self.cache[lfu_key]
        elif self.strategy == CacheStrategy.SIZE_BASED:
            # Remove largest entry
            largest_key = max(self.cache.keys(),
                             key=lambda k: self.cache[k].size_bytes)
            del self.cache[largest_key]

        self.evictions += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get memory cache statistics."""
        with self._lock:
            total_size = sum(entry.size_bytes for entry in self.cache.values())
            hit_rate = self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0

            return {
                "level": "L1_MEMORY",
                "entries": len(self.cache),
                "max_size": self.max_size,
                "total_size_bytes": total_size,
                "hit_rate": hit_rate,
                "hits": self.hits,
                "misses": self.misses,
                "evictions": self.evictions,
                "strategy": self.strategy.value
            }


class RedisCache(CacheBackend):
    """Redis-based distributed cache."""

    def __init__(self, host: str = 'localhost', port: int = 6379,
                 db: int = 0, password: Optional[str] = None,
                 max_connections: int = 10):
        try:
            self.redis = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                max_connections=max_connections,
                decode_responses=False  # Keep as bytes for pickle
            )
            self.redis.ping()  # Test connection
            self.available = True
        except redis.ConnectionError:
            logger.warning("Redis not available, falling back to memory cache")
            self.available = False
            self.fallback_cache = MemoryCache()

        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache."""
        if not self.available:
            return self.fallback_cache.get(key)

        try:
            data = self.redis.get(key)
            if data is None:
                self.misses += 1
                return None

            # Deserialize
            entry = pickle.loads(data)
            if entry.is_expired():
                self.redis.delete(key)
                self.misses += 1
                return None

            entry.access()
            # Re-serialize with updated access time
            self.redis.set(key, pickle.dumps(entry), ex=entry.ttl)

            self.hits += 1
            return entry.value

        except Exception as e:
            logger.error(f"Redis get error: {e}")
            self.misses += 1
            return None

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """Set value in Redis cache."""
        if not self.available:
            return self.fallback_cache.set(key, value, ttl)

        try:
            entry = CacheEntry(key, value, ttl)
            data = pickle.dumps(entry)
            return bool(self.redis.set(key, data, ex=ttl))
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete value from Redis cache."""
        if not self.available:
            return self.fallback_cache.delete(key)

        try:
            return bool(self.redis.delete(key))
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False

    def clear(self) -> None:
        """Clear Redis cache."""
        if not self.available:
            self.fallback_cache.clear()
            return

        try:
            self.redis.flushdb()
        except Exception as e:
            logger.error(f"Redis clear error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics."""
        if not self.available:
            return self.fallback_cache.get_stats()

        try:
            info = self.redis.info()
            hit_rate = self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0

            return {
                "level": "L2_REDIS",
                "available": True,
                "keys": self.redis.dbsize(),
                "memory_used": info.get('used_memory', 0),
                "hit_rate": hit_rate,
                "hits": self.hits,
                "misses": self.misses,
                "connections": info.get('connected_clients', 0)
            }
        except Exception as e:
            logger.error(f"Redis stats error: {e}")
            return {"level": "L2_REDIS", "available": False, "error": str(e)}


class DiskCache(CacheBackend):
    """Disk-based persistent cache using SQLite."""

    def __init__(self, cache_dir: str = "./cache", max_size_mb: int = 1000):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.db_path = self.cache_dir / "cache.db"
        self.max_size_bytes = max_size_mb * 1024 * 1024

        self._init_db()
        self._lock = Lock()
        self.hits = 0
        self.misses = 0

    def _init_db(self) -> None:
        """Initialize SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value BLOB,
                    created_at REAL,
                    last_accessed REAL,
                    access_count INTEGER,
                    ttl REAL,
                    size_bytes INTEGER
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_last_accessed ON cache(last_accessed)')
            conn.commit()

    def get(self, key: str) -> Optional[Any]:
        """Get value from disk cache."""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute(
                        'SELECT value, created_at, ttl FROM cache WHERE key = ?',
                        (key,)
                    )
                    row = cursor.fetchone()

                    if row is None:
                        self.misses += 1
                        return None

                    data, created_at, ttl = row

                    # Check expiration
                    if ttl is not None and time.time() - created_at > ttl:
                        conn.execute('DELETE FROM cache WHERE key = ?', (key,))
                        conn.commit()
                        self.misses += 1
                        return None

                    # Update access statistics
                    conn.execute(
                        'UPDATE cache SET last_accessed = ?, access_count = access_count + 1 WHERE key = ?',
                        (time.time(), key)
                    )
                    conn.commit()

                    # Deserialize
                    entry = pickle.loads(data)
                    self.hits += 1
                    return entry

            except Exception as e:
                logger.error(f"Disk cache get error: {e}")
                self.misses += 1
                return None

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """Set value in disk cache."""
        with self._lock:
            try:
                entry = CacheEntry(key, value, ttl)
                data = pickle.dumps(entry)

                with sqlite3.connect(self.db_path) as conn:
                    # Check current size and evict if necessary
                    self._evict_if_needed(conn, len(data))

                    conn.execute(
                        'INSERT OR REPLACE INTO cache (key, value, created_at, last_accessed, access_count, ttl, size_bytes) VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (key, data, entry.created_at, entry.last_accessed, entry.access_count, entry.ttl, entry.size_bytes)
                    )
                    conn.commit()

                return True

            except Exception as e:
                logger.error(f"Disk cache set error: {e}")
                return False

    def delete(self, key: str) -> bool:
        """Delete value from disk cache."""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute('DELETE FROM cache WHERE key = ?', (key,))
                    conn.commit()
                    return cursor.rowcount > 0
            except Exception as e:
                logger.error(f"Disk cache delete error: {e}")
                return False

    def clear(self) -> None:
        """Clear disk cache."""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute('DELETE FROM cache')
                    conn.commit()
                self.hits = 0
                self.misses = 0
            except Exception as e:
                logger.error(f"Disk cache clear error: {e}")

    def _evict_if_needed(self, conn: sqlite3.Connection, new_entry_size: int) -> None:
        """Evict entries if cache size limit would be exceeded."""
        try:
            # Get current total size
            cursor = conn.execute('SELECT SUM(size_bytes) FROM cache')
            result = cursor.fetchone()
            current_size = result[0] if result[0] else 0

            # Evict oldest entries until we have space
            while current_size + new_entry_size > self.max_size_bytes:
                # Delete oldest entry
                conn.execute('DELETE FROM cache WHERE key = (SELECT key FROM cache ORDER BY last_accessed ASC LIMIT 1)')
                # Recalculate size
                cursor = conn.execute('SELECT SUM(size_bytes) FROM cache')
                result = cursor.fetchone()
                current_size = result[0] if result[0] else 0

        except Exception as e:
            logger.error(f"Error during cache eviction: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get disk cache statistics."""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute('SELECT COUNT(*), SUM(size_bytes) FROM cache')
                    count, total_size = cursor.fetchone()
                    count = count or 0
                    total_size = total_size or 0

                    hit_rate = self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0

                    return {
                        "level": "L3_DISK",
                        "entries": count,
                        "total_size_bytes": total_size,
                        "max_size_bytes": self.max_size_bytes,
                        "hit_rate": hit_rate,
                        "hits": self.hits,
                        "misses": self.misses,
                        "utilization": total_size / self.max_size_bytes if self.max_size_bytes > 0 else 0
                    }
            except Exception as e:
                logger.error(f"Disk cache stats error: {e}")
                return {"level": "L3_DISK", "error": str(e)}


class MultiLevelCache:
    """
    Multi-level caching system with automatic tier management.
    """

    def __init__(self, levels: List[CacheLevel] = None,
                 memory_size: int = 1000, redis_config: Dict[str, Any] = None,
                 disk_config: Dict[str, Any] = None):
        if levels is None:
            levels = [CacheLevel.L1_MEMORY, CacheLevel.L3_DISK]

        self.levels = levels
        self.caches: Dict[CacheLevel, CacheBackend] = {}

        # Initialize caches
        if CacheLevel.L1_MEMORY in levels:
            self.caches[CacheLevel.L1_MEMORY] = MemoryCache(max_size=memory_size)

        if CacheLevel.L2_REDIS in levels:
            redis_config = redis_config or {}
            self.caches[CacheLevel.L2_REDIS] = RedisCache(**redis_config)

        if CacheLevel.L3_DISK in levels:
            disk_config = disk_config or {}
            self.caches[CacheLevel.L3_DISK] = DiskCache(**disk_config)

        self._lock = Lock()
        self.cache_hits = {level: 0 for level in levels}
        self.cache_misses = {level: 0 for level in levels}

    def get(self, key: str) -> Optional[Any]:
        """Get value from multi-level cache."""
        # Try caches in order (fastest to slowest)
        for level in self.levels:
            cache = self.caches.get(level)
            if cache:
                value = cache.get(key)
                if value is not None:
                    with self._lock:
                        self.cache_hits[level] += 1
                    # Populate faster caches
                    self._populate_upper_caches(key, value)
                    return value

        with self._lock:
            for level in self.levels:
                if level in self.caches:
                    self.cache_misses[level] += 1

        return None

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """Set value in multi-level cache."""
        success = True

        # Set in all available caches
        for level in self.levels:
            cache = self.caches.get(level)
            if cache:
                if not cache.set(key, value, ttl):
                    success = False

        return success

    def delete(self, key: str) -> bool:
        """Delete value from all cache levels."""
        success = True

        for level in self.levels:
            cache = self.caches.get(level)
            if cache:
                if not cache.delete(key):
                    success = False

        return success

    def clear(self) -> None:
        """Clear all cache levels."""
        for level in self.levels:
            cache = self.caches.get(level)
            if cache:
                cache.clear()

    def _populate_upper_caches(self, key: str, value: Any) -> None:
        """Populate upper cache levels with the retrieved value."""
        # This is a simplified implementation
        # In practice, you might want to populate only certain levels
        pass

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        stats = {
            "overall": {
                "total_hits": sum(self.cache_hits.values()),
                "total_misses": sum(self.cache_misses.values()),
                "overall_hit_rate": 0.0
            },
            "levels": {}
        }

        total_requests = stats["overall"]["total_hits"] + stats["overall"]["total_misses"]
        if total_requests > 0:
            stats["overall"]["overall_hit_rate"] = stats["overall"]["total_hits"] / total_requests

        # Get stats for each level
        for level in self.levels:
            cache = self.caches.get(level)
            if cache:
                level_stats = cache.get_stats()
                level_stats["hits"] = self.cache_hits[level]
                level_stats["misses"] = self.cache_misses[level]
                level_stats["hit_rate"] = (
                    level_stats["hits"] / (level_stats["hits"] + level_stats["misses"])
                    if (level_stats["hits"] + level_stats["misses"]) > 0 else 0
                )
                stats["levels"][level.value] = level_stats

        return stats


class CacheManager:
    """
    Intelligent cache manager with automatic key generation and invalidation.
    """

    def __init__(self, cache: MultiLevelCache):
        self.cache = cache
        self.function_cache: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()

    def cached(self, ttl: Optional[float] = None, key_prefix: str = ""):
        """Decorator for caching function results."""
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                key = self._generate_key(func, args, kwargs, key_prefix)

                # Try to get from cache
                cached_result = self.cache.get(key)
                if cached_result is not None:
                    return cached_result

                # Compute result
                result = func(*args, **kwargs)

                # Cache result
                self.cache.set(key, result, ttl)

                return result

            # Store function metadata
            with self._lock:
                self.function_cache[func.__name__] = {
                    "function": func,
                    "ttl": ttl,
                    "key_prefix": key_prefix
                }

            return wrapper
        return decorator

    def _generate_key(self, func: Callable, args: Tuple, kwargs: Dict[str, Any],
                     key_prefix: str = "") -> str:
        """Generate a unique cache key for the function call."""
        # Create a hash of the function name and arguments
        key_data = {
            "function": func.__name__,
            "args": args,
            "kwargs": kwargs
        }

        key_string = json.dumps(key_data, sort_keys=True, default=str)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()

        if key_prefix:
            return f"{key_prefix}:{key_hash}"
        else:
            return f"{func.__name__}:{key_hash}"

    def invalidate_function_cache(self, function_name: str) -> None:
        """Invalidate all cached results for a specific function."""
        # This is a simplified implementation
        # In practice, you'd need to track which keys belong to which functions
        logger.info(f"Invalidating cache for function: {function_name}")

    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about cached functions."""
        with self._lock:
            return {
                "cached_functions": list(self.function_cache.keys()),
                "cache_stats": self.cache.get_stats()
            }


# Global cache instances
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get the global cache manager."""
    global _cache_manager
    if _cache_manager is None:
        # Initialize with default configuration
        cache = MultiLevelCache(
            levels=[CacheLevel.L1_MEMORY, CacheLevel.L3_DISK],
            memory_size=1000,
            disk_config={"cache_dir": "./cache", "max_size_mb": 500}
        )
        _cache_manager = CacheManager(cache)

    return _cache_manager


def cached(ttl: Optional[float] = None, key_prefix: str = ""):
    """Global caching decorator."""
    return get_cache_manager().cached(ttl=ttl, key_prefix=key_prefix)


# Convenience functions
def cache_get(key: str) -> Optional[Any]:
    """Get value from global cache."""
    return get_cache_manager().cache.get(key)


def cache_set(key: str, value: Any, ttl: Optional[float] = None) -> bool:
    """Set value in global cache."""
    return get_cache_manager().cache.set(key, value, ttl)


def cache_delete(key: str) -> bool:
    """Delete value from global cache."""
    return get_cache_manager().cache.delete(key)


def cache_clear() -> None:
    """Clear global cache."""
    get_cache_manager().cache.clear()


def get_cache_stats() -> Dict[str, Any]:
    """Get global cache statistics."""
    return get_cache_manager().cache.get_stats()


if __name__ == "__main__":
    # Example usage
    cache_manager = get_cache_manager()

    @cached(ttl=300)  # Cache for 5 minutes
    def expensive_computation(x: int, y: int) -> int:
        print(f"Computing {x} + {y}")
        time.sleep(1)  # Simulate expensive computation
        return x + y

    # First call - should compute
    result1 = expensive_computation(5, 3)
    print(f"Result 1: {result1}")

    # Second call - should use cache
    result2 = expensive_computation(5, 3)
    print(f"Result 2: {result2}")

    # Get cache stats
    stats = get_cache_stats()
    print(f"Cache stats: {stats}")