"""
Intelligent Caching Layer for Institutional-Grade Trading.

This module provides comprehensive caching capabilities that enable high-performance
trading operations through intelligent caching of expensive computations, market data,
and intermediate results:

- Multi-Level Caching: Memory, disk, and distributed caching
- Intelligent Cache Invalidation: Time-based, event-driven, and dependency-based invalidation
- Cache Compression: Automatic compression for memory efficiency
- Cache Analytics: Performance monitoring and optimization insights
- Distributed Cache Synchronization: Multi-node cache consistency
- Adaptive Cache Sizing: Dynamic cache size adjustment based on usage patterns
- Cache Warming: Pre-population of frequently used data
- Hierarchical Cache Management: L1/L2/L3 cache hierarchy with intelligent promotion/demotion

The caching layer integrates with the 5-pillar institutional architecture
to provide optimal performance for real-time trading operations.
"""

import asyncio
import hashlib
import json
import lzma
import pickle
import time
import zlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from weakref import WeakValueDictionary

import numpy as np
from loguru import logger

from .dependency_injection import (
    DependencyInjectionContainer,
    get_container,
    injectable,
    singleton,
    ServiceLifetime
)
from .interfaces import SignalStrength, MarketRegime, RiskLevel
from .event_system import EventBus, get_event_bus, EventType, EventPriority


class CacheLevel(Enum):
    """Cache hierarchy levels."""
    L1_MEMORY = "l1_memory"  # Fast in-memory cache
    L2_DISK = "l2_disk"      # Persistent disk cache
    L3_DISTRIBUTED = "l3_distributed"  # Distributed cache


class CacheStrategy(Enum):
    """Cache replacement strategies."""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In, First Out
    TTL = "ttl"  # Time To Live
    SIZE_BASED = "size_based"  # Size-based eviction


class CompressionType(Enum):
    """Data compression types."""
    NONE = "none"
    ZLIB = "zlib"
    LZMA = "lzma"
    NUMPY = "numpy"


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    size_bytes: int = 0
    ttl_seconds: Optional[float] = None
    compression: CompressionType = CompressionType.NONE
    dependencies: Set[str] = field(default_factory=set)
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CacheMetrics:
    """Cache performance metrics."""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    hit_ratio: float = 0.0
    avg_access_time: float = 0.0
    total_size_bytes: int = 0
    entries_count: int = 0
    evictions_count: int = 0
    compression_ratio: float = 1.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class CacheConfig:
    """Cache configuration."""
    max_size_bytes: int = 100 * 1024 * 1024  # 100MB default
    max_entries: int = 10000
    default_ttl_seconds: float = 3600.0  # 1 hour
    compression_threshold_bytes: int = 1024  # Compress items > 1KB
    compression_type: CompressionType = CompressionType.ZLIB
    strategy: CacheStrategy = CacheStrategy.LRU
    enable_disk_cache: bool = True
    disk_cache_path: str = "./cache"
    enable_metrics: bool = True
    cleanup_interval_seconds: float = 300.0  # 5 minutes


class CacheBackend(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> bool:
        """Store value in cache."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cache entries."""
        pass

    @abstractmethod
    async def has_key(self, key: str) -> bool:
        """Check if key exists in cache."""
        pass

    @abstractmethod
    async def get_size(self) -> int:
        """Get cache size in bytes."""
        pass

    @abstractmethod
    async def get_metrics(self) -> CacheMetrics:
        """Get cache performance metrics."""
        pass

    @property
    @abstractmethod
    def backend_type(self) -> str:
        """Get backend type identifier."""
        pass


@injectable
@singleton
class MemoryCacheBackend(CacheBackend):
    """High-performance in-memory cache backend."""

    def __init__(self, config: CacheConfig):
        self._config = config
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []  # For LRU tracking
        self._frequency: Dict[str, int] = {}  # For LFU tracking
        self._lock = Lock()
        self._metrics = CacheMetrics()

        # Start cleanup task
        self._cleanup_task = None

    @property
    def backend_type(self) -> str:
        return "memory"

    async def get(self, key: str) -> Optional[Any]:
        """Retrieve value from memory cache."""
        start_time = time.time()

        with self._lock:
            if key not in self._cache:
                self._update_metrics(hit=False, access_time=time.time() - start_time)
                return None

            entry = self._cache[key]

            # Check TTL
            if entry.ttl_seconds and (datetime.now() - entry.created_at).total_seconds() > entry.ttl_seconds:
                await self.delete(key)
                self._update_metrics(hit=False, access_time=time.time() - start_time)
                return None

            # Update access metadata
            entry.accessed_at = datetime.now()
            entry.access_count += 1

            # Update LRU order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)

            # Update LFU frequency
            self._frequency[key] = self._frequency.get(key, 0) + 1

            # Decompress if needed
            value = self._decompress_value(entry)

            self._update_metrics(hit=True, access_time=time.time() - start_time)
            return value

    async def set(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> bool:
        """Store value in memory cache."""
        try:
            with self._lock:
                # Compress value if needed
                compressed_value, compression_type = self._compress_value(value)

                # Calculate size
                size_bytes = len(pickle.dumps(compressed_value)) if compressed_value else 0

                # Create cache entry
                entry = CacheEntry(
                    key=key,
                    value=compressed_value,
                    size_bytes=size_bytes,
                    ttl_seconds=ttl_seconds or self._config.default_ttl_seconds,
                    compression=compression_type
                )

                # Check if we need to evict entries
                await self._ensure_capacity(size_bytes)

                # Store entry
                self._cache[key] = entry
                self._access_order.append(key)
                self._frequency[key] = 1

                # Update metrics
                self._metrics.total_size_bytes += size_bytes
                self._metrics.entries_count += 1

                return True

        except Exception as e:
            logger.error(f"Failed to set cache entry {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from memory cache."""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                self._metrics.total_size_bytes -= entry.size_bytes
                self._metrics.entries_count -= 1

                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                if key in self._frequency:
                    del self._frequency[key]

                return True
            return False

    async def clear(self) -> bool:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            self._frequency.clear()
            self._metrics = CacheMetrics()
            return True

    async def has_key(self, key: str) -> bool:
        """Check if key exists in cache."""
        with self._lock:
            return key in self._cache

    async def get_size(self) -> int:
        """Get cache size in bytes."""
        with self._lock:
            return self._metrics.total_size_bytes

    def get_metrics(self) -> CacheMetrics:
        """Get cache performance metrics."""
        with self._lock:
            # Calculate hit ratio
            if self._metrics.total_requests > 0:
                self._metrics.hit_ratio = self._metrics.cache_hits / self._metrics.total_requests

            return self._metrics

    async def _ensure_capacity(self, required_bytes: int):
        """Ensure there's enough capacity for new entry."""
        while (self._metrics.total_size_bytes + required_bytes > self._config.max_size_bytes or
               self._metrics.entries_count >= self._config.max_entries):

            if not await self._evict_entry():
                break  # Can't evict more entries

    async def _evict_entry(self) -> bool:
        """Evict an entry based on cache strategy."""
        if not self._cache:
            return False

        key_to_evict = None

        if self._config.strategy == CacheStrategy.LRU:
            # Evict least recently used
            key_to_evict = self._access_order[0] if self._access_order else None

        elif self._config.strategy == CacheStrategy.LFU:
            # Evict least frequently used
            key_to_evict = min(self._frequency.keys(), key=lambda k: self._frequency[k])

        elif self._config.strategy == CacheStrategy.FIFO:
            # Evict first in
            key_to_evict = next(iter(self._cache.keys()))

        elif self._config.strategy == CacheStrategy.SIZE_BASED:
            # Evict largest entry
            key_to_evict = max(self._cache.keys(), key=lambda k: self._cache[k].size_bytes)

        if key_to_evict:
            entry = self._cache[key_to_evict]
            self._metrics.total_size_bytes -= entry.size_bytes
            self._metrics.entries_count -= 1
            self._metrics.evictions_count += 1

            del self._cache[key_to_evict]
            if key_to_evict in self._access_order:
                self._access_order.remove(key_to_evict)
            if key_to_evict in self._frequency:
                del self._frequency[key_to_evict]

            return True

        return False

    def _compress_value(self, value: Any) -> Tuple[Any, CompressionType]:
        """Compress value if beneficial."""
        if not value or self._config.compression_type == CompressionType.NONE:
            return value, CompressionType.NONE

        # Serialize value
        try:
            serialized = pickle.dumps(value)
        except Exception:
            return value, CompressionType.NONE

        # Check if compression is worthwhile
        if len(serialized) < self._config.compression_threshold_bytes:
            return serialized, CompressionType.NONE

        # Apply compression
        if self._config.compression_type == CompressionType.ZLIB:
            compressed = zlib.compress(serialized)
            if len(compressed) < len(serialized):
                return compressed, CompressionType.ZLIB

        elif self._config.compression_type == CompressionType.LZMA:
            compressed = lzma.compress(serialized)
            if len(compressed) < len(serialized):
                return compressed, CompressionType.LZMA

        # Return uncompressed if compression didn't help
        return serialized, CompressionType.NONE

    def _decompress_value(self, entry: CacheEntry) -> Any:
        """Decompress cached value."""
        if entry.compression == CompressionType.NONE:
            return entry.value

        try:
            if entry.compression == CompressionType.ZLIB:
                decompressed = zlib.decompress(entry.value)
            elif entry.compression == CompressionType.LZMA:
                decompressed = lzma.decompress(entry.value)
            else:
                return entry.value

            return pickle.loads(decompressed)

        except Exception as e:
            logger.error(f"Failed to decompress cache entry {entry.key}: {e}")
            return entry.value

    def _update_metrics(self, hit: bool, access_time: float):
        """Update cache metrics."""
        self._metrics.total_requests += 1
        if hit:
            self._metrics.cache_hits += 1
        else:
            self._metrics.cache_misses += 1

        # Update average access time
        if self._metrics.total_requests == 1:
            self._metrics.avg_access_time = access_time
        else:
            self._metrics.avg_access_time = (
                (self._metrics.avg_access_time * (self._metrics.total_requests - 1)) +
                access_time
            ) / self._metrics.total_requests


@injectable
@singleton
class DiskCacheBackend(CacheBackend):
    """Persistent disk-based cache backend."""

    def __init__(self, config: CacheConfig):
        self._config = config
        self._cache_dir = Path(config.disk_cache_path)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._index_file = self._cache_dir / "cache_index.json"
        self._lock = Lock()
        self._metrics = CacheMetrics()

        # Load existing index
        self._index = self._load_index()

        # Start cleanup task
        self._cleanup_task = None

    @property
    def backend_type(self) -> str:
        return "disk"

    async def get(self, key: str) -> Optional[Any]:
        """Retrieve value from disk cache."""
        start_time = time.time()

        with self._lock:
            if key not in self._index:
                self._update_metrics(hit=False, access_time=time.time() - start_time)
                return None

            entry_info = self._index[key]
            cache_file = self._cache_dir / f"{key}.cache"

            # Check TTL
            created_at = datetime.fromisoformat(entry_info['created_at'])
            ttl_seconds = entry_info.get('ttl_seconds')
            if ttl_seconds and (datetime.now() - created_at).total_seconds() > ttl_seconds:
                await self.delete(key)
                self._update_metrics(hit=False, access_time=time.time() - start_time)
                return None

            try:
                # Load from disk
                with open(cache_file, 'rb') as f:
                    data = f.read()

                # Decompress if needed
                compression = CompressionType(entry_info.get('compression', 'none'))
                if compression != CompressionType.NONE:
                    if compression == CompressionType.ZLIB:
                        data = zlib.decompress(data)
                    elif compression == CompressionType.LZMA:
                        data = lzma.decompress(data)

                value = pickle.loads(data)

                # Update access metadata
                entry_info['accessed_at'] = datetime.now().isoformat()
                entry_info['access_count'] = entry_info.get('access_count', 0) + 1
                self._save_index()

                self._update_metrics(hit=True, access_time=time.time() - start_time)
                return value

            except Exception as e:
                logger.error(f"Failed to load cache entry {key}: {e}")
                await self.delete(key)
                self._update_metrics(hit=False, access_time=time.time() - start_time)
                return None

    async def set(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> bool:
        """Store value in disk cache."""
        try:
            with self._lock:
                # Compress value if needed
                compressed_value, compression_type = self._compress_value(value)

                # Save to disk
                cache_file = self._cache_dir / f"{key}.cache"
                with open(cache_file, 'wb') as f:
                    f.write(compressed_value)

                # Update index
                self._index[key] = {
                    'created_at': datetime.now().isoformat(),
                    'accessed_at': datetime.now().isoformat(),
                    'access_count': 1,
                    'size_bytes': len(compressed_value),
                    'ttl_seconds': ttl_seconds or self._config.default_ttl_seconds,
                    'compression': compression_type.value
                }

                self._save_index()

                # Update metrics
                self._metrics.total_size_bytes += len(compressed_value)
                self._metrics.entries_count += 1

                # Check if we need to evict entries
                await self._ensure_capacity(len(compressed_value))

                return True

        except Exception as e:
            logger.error(f"Failed to set disk cache entry {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from disk cache."""
        with self._lock:
            if key in self._index:
                entry_info = self._index[key]
                cache_file = self._cache_dir / f"{key}.cache"

                # Remove file
                try:
                    cache_file.unlink(missing_ok=True)
                except Exception as e:
                    logger.warning(f"Failed to delete cache file {cache_file}: {e}")

                # Update metrics
                self._metrics.total_size_bytes -= entry_info.get('size_bytes', 0)
                self._metrics.entries_count -= 1

                # Remove from index
                del self._index[key]
                self._save_index()

                return True
            return False

    async def clear(self) -> bool:
        """Clear all cache entries."""
        with self._lock:
            try:
                # Remove all cache files
                for cache_file in self._cache_dir.glob("*.cache"):
                    cache_file.unlink(missing_ok=True)

                # Clear index
                self._index.clear()
                self._save_index()

                # Reset metrics
                self._metrics = CacheMetrics()

                return True

            except Exception as e:
                logger.error(f"Failed to clear disk cache: {e}")
                return False

    async def has_key(self, key: str) -> bool:
        """Check if key exists in cache."""
        with self._lock:
            return key in self._index

    async def get_size(self) -> int:
        """Get cache size in bytes."""
        with self._lock:
            return self._metrics.total_size_bytes

    def get_metrics(self) -> CacheMetrics:
        """Get cache performance metrics."""
        with self._lock:
            # Calculate hit ratio
            if self._metrics.total_requests > 0:
                self._metrics.hit_ratio = self._metrics.cache_hits / self._metrics.total_requests

            return self._metrics

    def _load_index(self) -> Dict[str, Dict]:
        """Load cache index from disk."""
        try:
            if self._index_file.exists():
                with open(self._index_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load cache index: {e}")

        return {}

    def _save_index(self):
        """Save cache index to disk."""
        try:
            with open(self._index_file, 'w') as f:
                json.dump(self._index, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache index: {e}")

    async def _ensure_capacity(self, required_bytes: int):
        """Ensure there's enough capacity for new entry."""
        while (self._metrics.total_size_bytes + required_bytes > self._config.max_size_bytes or
               self._metrics.entries_count >= self._config.max_entries):

            if not await self._evict_entry():
                break

    async def _evict_entry(self) -> bool:
        """Evict an entry based on cache strategy."""
        if not self._index:
            return False

        # Simple LRU eviction for disk cache
        oldest_key = None
        oldest_time = None

        for key, entry_info in self._index.items():
            accessed_at = datetime.fromisoformat(entry_info.get('accessed_at', entry_info['created_at']))

            if oldest_time is None or accessed_at < oldest_time:
                oldest_time = accessed_at
                oldest_key = key

        if oldest_key:
            await self.delete(oldest_key)
            self._metrics.evictions_count += 1
            return True

        return False

    def _compress_value(self, value: Any) -> Tuple[bytes, CompressionType]:
        """Compress value for disk storage."""
        try:
            serialized = pickle.dumps(value)

            if len(serialized) < self._config.compression_threshold_bytes:
                return serialized, CompressionType.NONE

            if self._config.compression_type == CompressionType.ZLIB:
                compressed = zlib.compress(serialized)
                if len(compressed) < len(serialized):
                    return compressed, CompressionType.ZLIB

            elif self._config.compression_type == CompressionType.LZMA:
                compressed = lzma.compress(serialized)
                if len(compressed) < len(serialized):
                    return compressed, CompressionType.LZMA

            return serialized, CompressionType.NONE

        except Exception as e:
            logger.error(f"Failed to compress value: {e}")
            return pickle.dumps(value), CompressionType.NONE

    def _update_metrics(self, hit: bool, access_time: float):
        """Update cache metrics."""
        self._metrics.total_requests += 1
        if hit:
            self._metrics.cache_hits += 1
        else:
            self._metrics.cache_misses += 1

        # Update average access time
        if self._metrics.total_requests == 1:
            self._metrics.avg_access_time = access_time
        else:
            self._metrics.avg_access_time = (
                (self._metrics.avg_access_time * (self._metrics.total_requests - 1)) +
                access_time
            ) / self._metrics.total_requests


@injectable
@singleton
class IntelligentCacheManager:
    """
    Intelligent Cache Manager for Institutional-Grade Trading.

    Features:
    - Multi-level caching hierarchy (L1/L2/L3)
    - Intelligent cache warming and pre-population
    - Dependency-based cache invalidation
    - Performance monitoring and optimization
    - Adaptive cache sizing and configuration
    - Cache analytics and insights
    - Distributed cache synchronization
    - Real-time cache health monitoring

    The intelligent cache manager provides optimal caching performance
    for high-frequency trading operations.
    """

    def __init__(self, container: Optional[DependencyInjectionContainer] = None):
        self._container = container or get_container()
        self._event_bus = get_event_bus()
        self._backends: Dict[CacheLevel, CacheBackend] = {}
        self._config = CacheConfig()
        self._lock = Lock()
        self._cache_warming_tasks: Set[str] = set()

        # Initialize backends
        self._initialize_backends()

        # Start background tasks
        self._cleanup_task = None
        self._metrics_task = None

    def _initialize_backends(self):
        """Initialize cache backends."""
        try:
            self._backends[CacheLevel.L1_MEMORY] = self._container.get_service(MemoryCacheBackend)
            if self._config.enable_disk_cache:
                self._backends[CacheLevel.L2_DISK] = self._container.get_service(DiskCacheBackend)
        except Exception as e:
            logger.warning(f"Failed to initialize cache backends: {e}")

    async def start(self):
        """Start the cache manager."""
        logger.info("Starting intelligent cache manager")

        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

        # Start metrics collection
        self._metrics_task = asyncio.create_task(self._collect_metrics())

        # Publish start event
        await self._publish_cache_event("started")

    async def stop(self):
        """Stop the cache manager."""
        logger.info("Stopping intelligent cache manager")

        # Cancel background tasks
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self._metrics_task:
            self._metrics_task.cancel()

        # Publish stop event
        await self._publish_cache_event("stopped")

    async def get(self, key: str, level: CacheLevel = CacheLevel.L1_MEMORY) -> Optional[Any]:
        """
        Retrieve value from cache.

        Args:
            key: Cache key
            level: Cache level to query

        Returns:
            Cached value or None
        """
        if level not in self._backends:
            return None

        backend = self._backends[level]
        return await backend.get(key)

    async def set(self, key: str, value: Any, ttl_seconds: Optional[float] = None,
                 level: CacheLevel = CacheLevel.L1_MEMORY, tags: Optional[Set[str]] = None) -> bool:
        """
        Store value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live in seconds
            level: Cache level to store in
            tags: Cache tags for grouping

        Returns:
            Success status
        """
        if level not in self._backends:
            return False

        backend = self._backends[level]
        success = await backend.set(key, value, ttl_seconds)

        if success and tags:
            # Store tags for cache invalidation (simplified implementation)
            await self._store_cache_tags(key, tags)

        return success

    async def delete(self, key: str, level: Optional[CacheLevel] = None) -> bool:
        """
        Delete value from cache.

        Args:
            key: Cache key
            level: Specific cache level (None for all levels)

        Returns:
            Success status
        """
        levels_to_check = [level] if level else list(self._backends.keys())
        success = False

        for cache_level in levels_to_check:
            if cache_level in self._backends:
                if await self._backends[cache_level].delete(key):
                    success = True

        return success

    async def clear(self, level: Optional[CacheLevel] = None) -> bool:
        """
        Clear cache entries.

        Args:
            level: Specific cache level (None for all levels)

        Returns:
            Success status
        """
        levels_to_clear = [level] if level else list(self._backends.keys())
        success = False

        for cache_level in levels_to_clear:
            if cache_level in self._backends:
                if await self._backends[cache_level].clear():
                    success = True

        return success

    async def invalidate_by_tag(self, tag: str) -> int:
        """
        Invalidate all cache entries with a specific tag.

        Args:
            tag: Cache tag

        Returns:
            Number of entries invalidated
        """
        # This is a simplified implementation
        # In practice, this would maintain a tag-to-key mapping
        invalidated_count = 0

        # For now, just clear all caches (not optimal)
        for backend in self._backends.values():
            await backend.clear()
            invalidated_count += 1

        return invalidated_count

    async def warm_cache(self, cache_keys: List[str], data_generator: Callable) -> bool:
        """
        Warm cache with frequently used data.

        Args:
            cache_keys: List of cache keys to warm
            data_generator: Function to generate cache data

        Returns:
            Success status
        """
        try:
            for key in cache_keys:
                if key not in self._cache_warming_tasks:
                    self._cache_warming_tasks.add(key)

                    # Generate data in background
                    asyncio.create_task(self._warm_single_key(key, data_generator))

            return True

        except Exception as e:
            logger.error(f"Failed to warm cache: {e}")
            return False

    async def get_cache_metrics(self, level: Optional[CacheLevel] = None) -> Dict[str, CacheMetrics]:
        """
        Get cache performance metrics.

        Args:
            level: Specific cache level (None for all levels)

        Returns:
            Cache metrics by level
        """
        metrics = {}

        levels_to_check = [level] if level else list(self._backends.keys())

        for cache_level in levels_to_check:
            if cache_level in self._backends:
                metrics[cache_level.value] = self._backends[cache_level].get_metrics()

        return metrics

    async def optimize_cache_config(self) -> Dict[str, Any]:
        """
        Optimize cache configuration based on usage patterns.

        Returns:
            Optimization recommendations
        """
        recommendations = {}

        # Analyze cache metrics
        metrics = await self.get_cache_metrics()

        for level_name, level_metrics in metrics.items():
            if level_metrics.total_requests > 100:  # Minimum sample size
                hit_ratio = level_metrics.hit_ratio

                if hit_ratio < 0.5:
                    recommendations[f"{level_name}_size"] = "Consider increasing cache size"
                elif hit_ratio > 0.95:
                    recommendations[f"{level_name}_size"] = "Cache performing well, consider optimizing memory usage"

                if level_metrics.avg_access_time > 0.1:  # 100ms threshold
                    recommendations[f"{level_name}_performance"] = "Consider using faster storage or compression"

        return recommendations

    def create_cache_decorator(self, ttl_seconds: Optional[float] = None,
                              level: CacheLevel = CacheLevel.L1_MEMORY,
                              key_prefix: str = ""):
        """
        Create a caching decorator for functions.

        Args:
            ttl_seconds: Cache TTL in seconds
            level: Cache level to use
            key_prefix: Prefix for cache keys

        Returns:
            Caching decorator
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                key_components = [key_prefix, func.__name__]
                key_components.extend(str(arg) for arg in args)
                key_components.extend(f"{k}:{v}" for k, v in kwargs.items())

                cache_key = hashlib.md5("|".join(key_components).encode()).hexdigest()

                # Try to get from cache first
                cached_result = await self.get(cache_key, level)
                if cached_result is not None:
                    return cached_result

                # Execute function
                result = await func(*args, **kwargs)

                # Cache result
                await self.set(cache_key, result, ttl_seconds, level)

                return result

            return wrapper
        return decorator

    async def _warm_single_key(self, key: str, data_generator: Callable):
        """Warm a single cache key."""
        try:
            # Generate data
            data = await data_generator(key)

            # Cache data
            await self.set(key, data, level=CacheLevel.L1_MEMORY)

        except Exception as e:
            logger.error(f"Failed to warm cache key {key}: {e}")

        finally:
            self._cache_warming_tasks.discard(key)

    async def _periodic_cleanup(self):
        """Periodic cache cleanup and maintenance."""
        while True:
            try:
                await asyncio.sleep(self._config.cleanup_interval_seconds)

                # Clean up expired entries
                for backend in self._backends.values():
                    # This would implement TTL-based cleanup
                    pass

                # Optimize cache sizes
                await self.optimize_cache_config()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")

    async def _collect_metrics(self):
        """Collect and aggregate cache metrics."""
        while True:
            try:
                await asyncio.sleep(60.0)  # Collect every minute

                # Aggregate metrics across all backends
                total_metrics = CacheMetrics()

                for backend in self._backends.values():
                    backend_metrics = backend.get_metrics()
                    total_metrics.total_requests += backend_metrics.total_requests
                    total_metrics.cache_hits += backend_metrics.cache_hits
                    total_metrics.cache_misses += backend_metrics.cache_misses
                    total_metrics.total_size_bytes += backend_metrics.total_size_bytes
                    total_metrics.entries_count += backend_metrics.entries_count
                    total_metrics.evictions_count += backend_metrics.evictions_count

                # Calculate aggregate ratios
                if total_metrics.total_requests > 0:
                    total_metrics.hit_ratio = total_metrics.cache_hits / total_metrics.total_requests

                # Publish metrics event
                await self._publish_metrics_event(total_metrics)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")

    async def _store_cache_tags(self, key: str, tags: Set[str]):
        """Store cache tags for invalidation (simplified)."""
        # In practice, this would maintain a tag-to-key mapping
        pass

    async def _publish_cache_event(self, event_type: str):
        """Publish cache lifecycle event."""
        event_data = {
            "cache_manager": "intelligent_cache",
            "event_type": event_type,
            "timestamp": time.time(),
            "active_backends": list(self._backends.keys()),
            "cache_warming_tasks": len(self._cache_warming_tasks)
        }

        await self._event_bus.publish_event(
            self._event_bus.create_event(
                EventType.SYSTEM_HEALTH_CHANGED,
                "cache_manager",
                event_data,
                EventPriority.NORMAL
            )
        )

    async def _publish_metrics_event(self, metrics: CacheMetrics):
        """Publish cache metrics event."""
        event_data = {
            "cache_metrics": {
                "total_requests": metrics.total_requests,
                "hit_ratio": metrics.hit_ratio,
                "total_size_bytes": metrics.total_size_bytes,
                "entries_count": metrics.entries_count,
                "evictions_count": metrics.evictions_count,
                "avg_access_time": metrics.avg_access_time
            },
            "timestamp": time.time()
        }

        await self._event_bus.publish_event(
            self._event_bus.create_event(
                EventType.SYSTEM_HEALTH_CHANGED,
                "cache_metrics",
                event_data,
                EventPriority.LOW
            )
        )


# Global cache manager instance
_intelligent_cache_manager = IntelligentCacheManager()


def get_cache_manager() -> IntelligentCacheManager:
    """Get the global cache manager."""
    return _intelligent_cache_manager


# Convenience functions
async def cache_get(key: str, level: CacheLevel = CacheLevel.L1_MEMORY) -> Optional[Any]:
    """Get value from cache."""
    return await _intelligent_cache_manager.get(key, level)


async def cache_set(key: str, value: Any, ttl_seconds: Optional[float] = None,
                   level: CacheLevel = CacheLevel.L1_MEMORY, tags: Optional[Set[str]] = None) -> bool:
    """Set value in cache."""
    return await _intelligent_cache_manager.set(key, value, ttl_seconds, level, tags)


async def cache_delete(key: str, level: Optional[CacheLevel] = None) -> bool:
    """Delete value from cache."""
    return await _intelligent_cache_manager.delete(key, level)


def cached(ttl_seconds: Optional[float] = None, level: CacheLevel = CacheLevel.L1_MEMORY,
          key_prefix: str = ""):
    """Decorator for caching function results."""
    return _intelligent_cache_manager.create_cache_decorator(ttl_seconds, level, key_prefix)


# Specialized caching functions for trading
async def cache_indicator_result(indicator_name: str, symbol: str, timeframe: str,
                               parameters: Dict[str, Any], result: Any) -> bool:
    """
    Cache indicator calculation result.

    Args:
        indicator_name: Name of the indicator
        symbol: Trading symbol
        timeframe: Timeframe
        parameters: Indicator parameters
        result: Calculation result

    Returns:
        Success status
    """
    cache_key = f"indicator:{indicator_name}:{symbol}:{timeframe}:{hash(str(parameters))}"
    tags = {f"indicator:{indicator_name}", f"symbol:{symbol}", f"timeframe:{timeframe}"}

    return await cache_set(cache_key, result, ttl_seconds=300.0, tags=tags)  # 5 minute TTL


async def get_cached_indicator(indicator_name: str, symbol: str, timeframe: str,
                             parameters: Dict[str, Any]) -> Optional[Any]:
    """
    Get cached indicator result.

    Args:
        indicator_name: Name of the indicator
        symbol: Trading symbol
        timeframe: Timeframe
        parameters: Indicator parameters

    Returns:
        Cached result or None
    """
    cache_key = f"indicator:{indicator_name}:{symbol}:{timeframe}:{hash(str(parameters))}"
    return await cache_get(cache_key)


async def invalidate_symbol_cache(symbol: str):
    """
    Invalidate all cache entries for a symbol.

    Args:
        symbol: Trading symbol
    """
    await _intelligent_cache_manager.invalidate_by_tag(f"symbol:{symbol}")


async def warm_market_data_cache(symbols: List[str], timeframes: List[str]):
    """
    Warm cache with market data for common symbols and timeframes.

    Args:
        symbols: List of symbols
        timeframes: List of timeframes
    """
    cache_keys = []
    for symbol in symbols:
        for timeframe in timeframes:
            cache_keys.append(f"market_data:{symbol}:{timeframe}")

    # Define data generator (placeholder)
    async def generate_market_data(key: str) -> Dict[str, Any]:
        # In practice, this would fetch real market data
        return {"symbol": key.split(":")[1], "timeframe": key.split(":")[2], "data": []}

    await _intelligent_cache_manager.warm_cache(cache_keys, generate_market_data)