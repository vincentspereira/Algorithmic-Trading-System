"""Advanced caching manager with multiple strategies and backends.

This module provides comprehensive caching capabilities including:
- Redis caching with clustering and sentinel support
- In-memory caching with LRU eviction
- Hybrid caching (L1 memory + L2 Redis)
- Distributed caching across multiple nodes
- Cache warming and preloading
- Cache analytics and monitoring
"""

import asyncio
import json
import pickle
import logging
import time
import hashlib
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Callable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import OrderedDict
from functools import wraps
import threading

try:
    import redis
    import redis.sentinel
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

try:
    import aioredis
    AIOREDIS_AVAILABLE = True
except ImportError:
    AIOREDIS_AVAILABLE = False
    aioredis = None

from config.performance_config import performance_manager, CacheStrategy

logger = logging.getLogger(__name__)

@dataclass
class CacheStats:
    """Cache statistics and metrics."""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    errors: int = 0
    total_size: int = 0
    memory_usage: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate."""
        return 1.0 - self.hit_rate

@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime]
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    size: int = 0
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def touch(self):
        """Update access metadata."""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()

class CacheBackend(ABC):
    """Abstract base class for cache backends."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cache entries."""
        pass
    
    @abstractmethod
    async def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        pass

class MemoryCacheBackend(CacheBackend):
    """In-memory cache backend with LRU eviction."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = CacheStats()
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_expired())
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from memory cache."""
        with self._lock:
            if key not in self._cache:
                self._stats.misses += 1
                return None
            
            entry = self._cache[key]
            
            # Check expiration
            if entry.is_expired():
                del self._cache[key]
                self._stats.misses += 1
                self._stats.evictions += 1
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.touch()
            
            self._stats.hits += 1
            return entry.value
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in memory cache."""
        try:
            with self._lock:
                ttl = ttl or self.default_ttl
                expires_at = datetime.utcnow() + timedelta(seconds=ttl) if ttl > 0 else None
                
                # Calculate size (approximate)
                size = len(pickle.dumps(value))
                
                entry = CacheEntry(
                    key=key,
                    value=value,
                    created_at=datetime.utcnow(),
                    expires_at=expires_at,
                    size=size
                )
                
                # Remove existing entry if present
                if key in self._cache:
                    del self._cache[key]
                
                # Add new entry
                self._cache[key] = entry
                
                # Evict if necessary
                while len(self._cache) > self.max_size:
                    oldest_key = next(iter(self._cache))
                    del self._cache[oldest_key]
                    self._stats.evictions += 1
                
                self._stats.sets += 1
                self._stats.total_size = len(self._cache)
                return True
                
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
            self._stats.errors += 1
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from memory cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats.deletes += 1
                self._stats.total_size = len(self._cache)
                return True
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in memory cache."""
        with self._lock:
            if key not in self._cache:
                return False
            
            entry = self._cache[key]
            if entry.is_expired():
                del self._cache[key]
                return False
            
            return True
    
    async def clear(self) -> bool:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._stats.total_size = 0
            return True
    
    async def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            self._stats.total_size = len(self._cache)
            self._stats.memory_usage = sum(entry.size for entry in self._cache.values())
            return self._stats
    
    async def _cleanup_expired(self):
        """Periodically clean up expired entries."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                with self._lock:
                    expired_keys = [
                        key for key, entry in self._cache.items()
                        if entry.is_expired()
                    ]
                    
                    for key in expired_keys:
                        del self._cache[key]
                        self._stats.evictions += 1
                    
                    if expired_keys:
                        logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
                        
            except Exception as e:
                logger.error(f"Error during cache cleanup: {e}")

class RedisCacheBackend(CacheBackend):
    """Redis cache backend with clustering and sentinel support."""
    
    def __init__(self, config: Dict[str, Any]):
        if not REDIS_AVAILABLE:
            raise ImportError("Redis not available. Install redis-py: pip install redis")
        
        self.config = config
        self._stats = CacheStats()
        self._client = None
        self._async_client = None
        
        # Initialize Redis client
        self._init_redis_client()
    
    def _init_redis_client(self):
        """Initialize Redis client based on configuration."""
        try:
            if self.config.get('sentinel', False):
                # Redis Sentinel setup
                sentinel_hosts = self.config.get('sentinel_hosts', [('localhost', 26379)])
                sentinel = redis.sentinel.Sentinel(sentinel_hosts)
                self._client = sentinel.master_for(
                    self.config.get('service_name', 'mymaster'),
                    password=self.config.get('password')
                )
            elif self.config.get('cluster', False):
                # Redis Cluster setup
                from redis.cluster import RedisCluster
                startup_nodes = self.config.get('cluster_nodes', [{'host': 'localhost', 'port': 7000}])
                self._client = RedisCluster(
                    startup_nodes=startup_nodes,
                    password=self.config.get('password'),
                    decode_responses=False
                )
            else:
                # Standard Redis setup
                self._client = redis.Redis(
                    host=self.config.get('host', 'localhost'),
                    port=self.config.get('port', 6379),
                    db=self.config.get('db', 0),
                    password=self.config.get('password'),
                    ssl=self.config.get('ssl', False),
                    decode_responses=False
                )
            
            # Test connection
            self._client.ping()
            logger.info("Redis cache backend initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            raise
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache."""
        try:
            data = self._client.get(key)
            if data is None:
                self._stats.misses += 1
                return None
            
            # Deserialize data
            value = pickle.loads(data)
            self._stats.hits += 1
            return value
            
        except Exception as e:
            logger.error(f"Error getting cache key {key}: {e}")
            self._stats.errors += 1
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis cache."""
        try:
            # Serialize data
            data = pickle.dumps(value)
            
            # Set with TTL
            if ttl:
                result = self._client.setex(key, ttl, data)
            else:
                result = self._client.set(key, data)
            
            if result:
                self._stats.sets += 1
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
            self._stats.errors += 1
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from Redis cache."""
        try:
            result = self._client.delete(key)
            if result > 0:
                self._stats.deletes += 1
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {e}")
            self._stats.errors += 1
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis cache."""
        try:
            return bool(self._client.exists(key))
        except Exception as e:
            logger.error(f"Error checking cache key {key}: {e}")
            return False
    
    async def clear(self) -> bool:
        """Clear all cache entries."""
        try:
            self._client.flushdb()
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False
    
    async def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        try:
            info = self._client.info()
            self._stats.memory_usage = info.get('used_memory', 0)
            return self._stats
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return self._stats

class HybridCacheBackend(CacheBackend):
    """Hybrid cache backend (L1 memory + L2 Redis)."""
    
    def __init__(self, l1_config: Dict[str, Any], l2_config: Dict[str, Any]):
        self.l1_cache = MemoryCacheBackend(**l1_config)
        self.l2_cache = RedisCacheBackend(l2_config)
        self._stats = CacheStats()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from hybrid cache (L1 first, then L2)."""
        # Try L1 cache first
        value = await self.l1_cache.get(key)
        if value is not None:
            self._stats.hits += 1
            return value
        
        # Try L2 cache
        value = await self.l2_cache.get(key)
        if value is not None:
            # Populate L1 cache
            await self.l1_cache.set(key, value)
            self._stats.hits += 1
            return value
        
        self._stats.misses += 1
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in both L1 and L2 caches."""
        l1_result = await self.l1_cache.set(key, value, ttl)
        l2_result = await self.l2_cache.set(key, value, ttl)
        
        if l1_result or l2_result:
            self._stats.sets += 1
            return True
        return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from both caches."""
        l1_result = await self.l1_cache.delete(key)
        l2_result = await self.l2_cache.delete(key)
        
        if l1_result or l2_result:
            self._stats.deletes += 1
            return True
        return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in either cache."""
        return await self.l1_cache.exists(key) or await self.l2_cache.exists(key)
    
    async def clear(self) -> bool:
        """Clear both caches."""
        l1_result = await self.l1_cache.clear()
        l2_result = await self.l2_cache.clear()
        return l1_result and l2_result
    
    async def get_stats(self) -> CacheStats:
        """Get combined cache statistics."""
        l1_stats = await self.l1_cache.get_stats()
        l2_stats = await self.l2_cache.get_stats()
        
        return CacheStats(
            hits=l1_stats.hits + l2_stats.hits + self._stats.hits,
            misses=l1_stats.misses + l2_stats.misses + self._stats.misses,
            sets=l1_stats.sets + l2_stats.sets + self._stats.sets,
            deletes=l1_stats.deletes + l2_stats.deletes + self._stats.deletes,
            evictions=l1_stats.evictions + l2_stats.evictions,
            errors=l1_stats.errors + l2_stats.errors,
            total_size=l1_stats.total_size + l2_stats.total_size,
            memory_usage=l1_stats.memory_usage + l2_stats.memory_usage,
        )

class CacheManager:
    """Advanced cache manager with multiple backends and strategies."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or performance_manager.get_cache_config()
        self.strategy = CacheStrategy(self.config.get('strategy', 'redis'))
        self._backend = None
        self._init_backend()
        
        # Cache warming and preloading
        self._warm_cache_functions: List[Callable] = []
        
        logger.info(f"Cache manager initialized with strategy: {self.strategy}")
    
    def _init_backend(self):
        """Initialize cache backend based on strategy."""
        if self.strategy == CacheStrategy.MEMORY:
            self._backend = MemoryCacheBackend(
                max_size=self.config.get('max_size', 1000),
                default_ttl=self.config.get('ttl', 3600)
            )
        elif self.strategy == CacheStrategy.REDIS:
            if not REDIS_AVAILABLE:
                logger.warning("Redis not available, falling back to memory cache")
                self._backend = MemoryCacheBackend()
            else:
                self._backend = RedisCacheBackend(self.config)
        elif self.strategy == CacheStrategy.HYBRID:
            l1_config = {'max_size': 1000, 'default_ttl': 300}
            l2_config = self.config.copy()
            self._backend = HybridCacheBackend(l1_config, l2_config)
        else:
            # Default to memory cache
            self._backend = MemoryCacheBackend()
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache."""
        value = await self._backend.get(key)
        return value if value is not None else default
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        return await self._backend.set(key, value, ttl)
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        return await self._backend.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        return await self._backend.exists(key)
    
    async def clear(self) -> bool:
        """Clear all cache entries."""
        return await self._backend.clear()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = await self._backend.get_stats()
        return asdict(stats)
    
    def cache_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = f"{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def cached(self, ttl: Optional[int] = None, key_func: Optional[Callable] = None):
        """Decorator for caching function results."""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = f"{func.__name__}:{self.cache_key(*args, **kwargs)}"
                
                # Try to get from cache
                cached_result = await self.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # Execute function and cache result
                result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                await self.set(cache_key, result, ttl)
                return result
            
            return wrapper
        return decorator
    
    def add_warm_cache_function(self, func: Callable):
        """Add function to warm cache on startup."""
        self._warm_cache_functions.append(func)
    
    async def warm_cache(self):
        """Warm cache by executing registered functions."""
        logger.info("Starting cache warming...")
        
        for func in self._warm_cache_functions:
            try:
                if asyncio.iscoroutinefunction(func):
                    await func()
                else:
                    func()
                logger.debug(f"Cache warmed by {func.__name__}")
            except Exception as e:
                logger.error(f"Error warming cache with {func.__name__}: {e}")
        
        logger.info("Cache warming completed")
    
    async def get_cache_info(self) -> Dict[str, Any]:
        """Get comprehensive cache information."""
        stats = await self.get_stats()
        
        return {
            "strategy": self.strategy.value,
            "backend": type(self._backend).__name__,
            "config": self.config,
            "stats": stats,
            "performance": {
                "hit_rate": stats.get('hits', 0) / max(stats.get('hits', 0) + stats.get('misses', 0), 1),
                "memory_efficiency": stats.get('memory_usage', 0) / max(stats.get('total_size', 1), 1),
            }
        }

# Global cache manager instance
cache_manager = CacheManager()

# Export commonly used functions
__all__ = [
    "CacheManager",
    "CacheBackend",
    "MemoryCacheBackend",
    "RedisCacheBackend",
    "HybridCacheBackend",
    "CacheStats",
    "CacheEntry",
    "cache_manager",
]