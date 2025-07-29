"""
Advanced Cache Manager
Multi-level caching system with L1/L2/L3 hierarchy for trading system performance
"""

import asyncio
import time
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional, Dict, List, Union, Callable
from enum import Enum
import logging
import hashlib
import pickle

from .types import EvictionPolicy, CacheLevel, CacheEntry, CacheStats
from .cache_coherency import CacheCoherencyManager
from .cache_metrics import CacheMetrics


@dataclass
class CacheConfig:
    """Configuration for cache manager"""
    # L1 Cache (In-Memory)
    l1_enabled: bool = True
    l1_max_size: int = 10000
    l1_ttl_seconds: int = 300  # 5 minutes
    l1_eviction_policy: EvictionPolicy = EvictionPolicy.LRU
    
    # L2 Cache (Distributed)
    l2_enabled: bool = True
    l2_redis_url: str = "redis://localhost:6379"
    l2_max_size: int = 100000
    l2_ttl_seconds: int = 3600  # 1 hour
    
    # L3 Cache (Persistent)
    l3_enabled: bool = True
    l3_database_url: str = "sqlite:///cache.db"
    l3_max_size: int = 1000000
    l3_ttl_seconds: int = 86400  # 24 hours
    
    # Coherency
    enable_coherency: bool = True
    coherency_check_interval: int = 60  # seconds
    
    # Performance
    enable_metrics: bool = True
    enable_compression: bool = True
    compression_threshold: int = 1024  # bytes
    
    # Prefetching
    enable_prefetching: bool = True
    prefetch_batch_size: int = 100


# Import cache implementations after config to avoid circular imports
from .l1_cache import L1Cache
from .l2_cache import L2Cache  
from .l3_cache import L3Cache


class CacheManager:
    """
    Advanced multi-level cache manager
    
    Provides a unified interface to a three-level cache hierarchy:
    - L1: In-memory cache (fastest, smallest)
    - L2: Distributed cache (fast, medium)
    - L3: Persistent cache (slower, largest)
    
    Features:
    - Automatic cache level promotion/demotion
    - Cache coherency management
    - Performance metrics
    - Prefetching and batch operations
    - Compression for large values
    """
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize cache levels
        self.l1_cache = L1Cache(
            max_size=config.l1_max_size,
            ttl=config.l1_ttl_seconds,
            eviction_policy=config.l1_eviction_policy
        ) if config.l1_enabled else None
        
        self.l2_cache = L2Cache(
            redis_url=config.l2_redis_url,
            max_size=config.l2_max_size,
            ttl=config.l2_ttl_seconds
        ) if config.l2_enabled else None
        
        self.l3_cache = L3Cache(
            database_url=config.l3_database_url,
            max_size=config.l3_max_size,
            ttl=config.l3_ttl_seconds
        ) if config.l3_enabled else None
        
        # Cache coherency manager
        self.coherency_manager = CacheCoherencyManager(
            [self.l1_cache, self.l2_cache, self.l3_cache]
        ) if config.enable_coherency else None
        
        # Metrics collection
        self.metrics = CacheMetrics() if config.enable_metrics else None
        
        # Threading
        self._lock = threading.RLock()
        self._background_tasks = []
        self._running = False
        
        # Prefetching
        self._prefetch_queue = asyncio.Queue() if config.enable_prefetching else None
        
        # Compression
        self._compressor = self._get_compressor() if config.enable_compression else None
    
    async def start(self):
        """Start the cache manager and background tasks"""
        if self._running:
            return
        
        self._running = True
        
        # Start cache levels
        if self.l2_cache:
            await self.l2_cache.start()
        if self.l3_cache:
            await self.l3_cache.start()
        
        # Start coherency manager
        if self.coherency_manager:
            await self.coherency_manager.start()
        
        # Start background tasks
        if self.config.enable_prefetching:
            task = asyncio.create_task(self._prefetch_worker())
            self._background_tasks.append(task)
        
        # Start metrics collection
        if self.metrics:
            task = asyncio.create_task(self._metrics_collector())
            self._background_tasks.append(task)
        
        self.logger.info("CacheManager started")
    
    async def stop(self):
        """Stop the cache manager and cleanup resources"""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        
        # Stop cache levels
        if self.l2_cache:
            await self.l2_cache.stop()
        if self.l3_cache:
            await self.l3_cache.stop()
        
        # Stop coherency manager
        if self.coherency_manager:
            await self.coherency_manager.stop()
        
        self.logger.info("CacheManager stopped")
    
    async def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from cache, checking all levels
        
        Args:
            key: Cache key
            default: Default value if not found
            
        Returns:
            Cached value or default
        """
        start_time = time.time_ns()
        
        try:
            # Try L1 cache first (fastest)
            if self.l1_cache:
                value = await self.l1_cache.get(key)
                if value is not None:
                    if self.metrics:
                        self.metrics.record_hit(CacheLevel.L1, time.time_ns() - start_time)
                    return self._decompress_if_needed(value)
            
            # Try L2 cache
            if self.l2_cache:
                value = await self.l2_cache.get(key)
                if value is not None:
                    # Promote to L1
                    if self.l1_cache:
                        await self.l1_cache.set(key, value, ttl=self.config.l1_ttl_seconds)
                    
                    if self.metrics:
                        self.metrics.record_hit(CacheLevel.L2, time.time_ns() - start_time)
                    return self._decompress_if_needed(value)
            
            # Try L3 cache
            if self.l3_cache:
                value = await self.l3_cache.get(key)
                if value is not None:
                    # Promote to L2 and L1
                    if self.l2_cache:
                        await self.l2_cache.set(key, value, ttl=self.config.l2_ttl_seconds)
                    if self.l1_cache:
                        await self.l1_cache.set(key, value, ttl=self.config.l1_ttl_seconds)
                    
                    if self.metrics:
                        self.metrics.record_hit(CacheLevel.L3, time.time_ns() - start_time)
                    return self._decompress_if_needed(value)
            
            # Cache miss
            if self.metrics:
                self.metrics.record_miss(time.time_ns() - start_time)
            
            return default
        
        except Exception as e:
            self.logger.error(f"Cache get error for key {key}: {e}")
            if self.metrics:
                self.metrics.record_error("get")
            return default
    
    async def set(self, 
                  key: str, 
                  value: Any, 
                  ttl: Optional[int] = None,
                  tags: Optional[List[str]] = None,
                  level: Optional[CacheLevel] = None) -> bool:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            tags: Tags for cache invalidation
            level: Specific cache level to use
            
        Returns:
            True if successful
        """
        start_time = time.time_ns()
        
        try:
            # Compress if needed
            compressed_value = self._compress_if_needed(value)
            
            success = True
            
            # Set in specified level or all levels
            if level == CacheLevel.L1 or level is None:
                if self.l1_cache:
                    success &= await self.l1_cache.set(
                        key, compressed_value, 
                        ttl or self.config.l1_ttl_seconds, 
                        tags
                    )
            
            if level == CacheLevel.L2 or level is None:
                if self.l2_cache:
                    success &= await self.l2_cache.set(
                        key, compressed_value, 
                        ttl or self.config.l2_ttl_seconds, 
                        tags
                    )
            
            if level == CacheLevel.L3 or level is None:
                if self.l3_cache:
                    success &= await self.l3_cache.set(
                        key, compressed_value, 
                        ttl or self.config.l3_ttl_seconds, 
                        tags
                    )
            
            if self.metrics:
                if success:
                    self.metrics.record_set(time.time_ns() - start_time)
                else:
                    self.metrics.record_error("set")
            
            return success
        
        except Exception as e:
            self.logger.error(f"Cache set error for key {key}: {e}")
            if self.metrics:
                self.metrics.record_error("set")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from all cache levels"""
        success = True
        
        try:
            if self.l1_cache:
                success &= await self.l1_cache.delete(key)
            if self.l2_cache:
                success &= await self.l2_cache.delete(key)
            if self.l3_cache:
                success &= await self.l3_cache.delete(key)
            
            if self.metrics:
                self.metrics.record_delete()
            
            return success
        
        except Exception as e:
            self.logger.error(f"Cache delete error for key {key}: {e}")
            if self.metrics:
                self.metrics.record_error("delete")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in any cache level"""
        try:
            if self.l1_cache and await self.l1_cache.exists(key):
                return True
            if self.l2_cache and await self.l2_cache.exists(key):
                return True
            if self.l3_cache and await self.l3_cache.exists(key):
                return True
            return False
        except Exception as e:
            self.logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    async def clear(self, level: Optional[CacheLevel] = None):
        """Clear cache level(s)"""
        try:
            if level == CacheLevel.L1 or level is None:
                if self.l1_cache:
                    await self.l1_cache.clear()
            
            if level == CacheLevel.L2 or level is None:
                if self.l2_cache:
                    await self.l2_cache.clear()
            
            if level == CacheLevel.L3 or level is None:
                if self.l3_cache:
                    await self.l3_cache.clear()
            
            if self.metrics:
                self.metrics.record_clear()
        
        except Exception as e:
            self.logger.error(f"Cache clear error: {e}")
    
    async def invalidate_by_tags(self, tags: List[str]):
        """Invalidate cache entries by tags"""
        try:
            if self.l1_cache:
                await self.l1_cache.invalidate_by_tags(tags)
            if self.l2_cache:
                await self.l2_cache.invalidate_by_tags(tags)
            if self.l3_cache:
                await self.l3_cache.invalidate_by_tags(tags)
            
            if self.metrics:
                self.metrics.record_invalidation(len(tags))
        
        except Exception as e:
            self.logger.error(f"Cache invalidation error: {e}")
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple keys efficiently"""
        results = {}
        
        # Try to get all keys from L1 first
        if self.l1_cache:
            l1_results = await self.l1_cache.get_many(keys)
            results.update(l1_results)
        
        # Get missing keys from L2
        missing_keys = [k for k in keys if k not in results]
        if missing_keys and self.l2_cache:
            l2_results = await self.l2_cache.get_many(missing_keys)
            results.update(l2_results)
            
            # Promote L2 hits to L1
            if self.l1_cache and l2_results:
                await self.l1_cache.set_many(l2_results, ttl=self.config.l1_ttl_seconds)
        
        # Get remaining missing keys from L3
        missing_keys = [k for k in keys if k not in results]
        if missing_keys and self.l3_cache:
            l3_results = await self.l3_cache.get_many(missing_keys)
            results.update(l3_results)
            
            # Promote L3 hits to L2 and L1
            if l3_results:
                if self.l2_cache:
                    await self.l2_cache.set_many(l3_results, ttl=self.config.l2_ttl_seconds)
                if self.l1_cache:
                    await self.l1_cache.set_many(l3_results, ttl=self.config.l1_ttl_seconds)
        
        # Decompress results
        for key, value in results.items():
            results[key] = self._decompress_if_needed(value)
        
        return results
    
    async def set_many(self, items: Dict[str, Any], ttl: Optional[int] = None):
        """Set multiple keys efficiently"""
        # Compress values
        compressed_items = {}
        for key, value in items.items():
            compressed_items[key] = self._compress_if_needed(value)
        
        # Set in all levels
        if self.l1_cache:
            await self.l1_cache.set_many(compressed_items, ttl or self.config.l1_ttl_seconds)
        if self.l2_cache:
            await self.l2_cache.set_many(compressed_items, ttl or self.config.l2_ttl_seconds)
        if self.l3_cache:
            await self.l3_cache.set_many(compressed_items, ttl or self.config.l3_ttl_seconds)
    
    def _compress_if_needed(self, value: Any) -> Any:
        """Compress value if it exceeds threshold"""
        if not self._compressor:
            return value
        
        try:
            serialized = pickle.dumps(value)
            if len(serialized) > self.config.compression_threshold:
                return self._compressor.compress(serialized)
            return value
        except:
            return value
    
    def _decompress_if_needed(self, value: Any) -> Any:
        """Decompress value if needed"""
        if not self._compressor:
            return value
        
        try:
            if isinstance(value, bytes) and value.startswith(b'compressed:'):
                decompressed = self._compressor.decompress(value[11:])  # Remove 'compressed:' prefix
                return pickle.loads(decompressed)
            return value
        except:
            return value
    
    def _get_compressor(self):
        """Get compression handler"""
        try:
            import zlib
            
            class ZlibCompressor:
                def compress(self, data: bytes) -> bytes:
                    return b'compressed:' + zlib.compress(data)
                
                def decompress(self, data: bytes) -> bytes:
                    return zlib.decompress(data)
            
            return ZlibCompressor()
        except ImportError:
            return None
    
    async def _prefetch_worker(self):
        """Background worker for prefetching"""
        while self._running:
            try:
                # This would implement intelligent prefetching logic
                # based on access patterns and predictions
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Prefetch worker error: {e}")
    
    async def _metrics_collector(self):
        """Background metrics collection"""
        while self._running:
            try:
                if self.metrics:
                    # Collect cache level statistics
                    if self.l1_cache:
                        stats = await self.l1_cache.get_stats()
                        self.metrics.update_level_stats(CacheLevel.L1, stats)
                    
                    if self.l2_cache:
                        stats = await self.l2_cache.get_stats()
                        self.metrics.update_level_stats(CacheLevel.L2, stats)
                    
                    if self.l3_cache:
                        stats = await self.l3_cache.get_stats()
                        self.metrics.update_level_stats(CacheLevel.L3, stats)
                
                await asyncio.sleep(10)  # Collect every 10 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Metrics collector error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        stats = {
            'config': {
                'l1_enabled': self.config.l1_enabled,
                'l2_enabled': self.config.l2_enabled,
                'l3_enabled': self.config.l3_enabled,
                'coherency_enabled': self.config.enable_coherency,
                'metrics_enabled': self.config.enable_metrics
            }
        }
        
        if self.metrics:
            stats['metrics'] = self.metrics.get_metrics()
        
        return stats