"""
L1 Cache Implementation
In-memory cache with LRU eviction for ultra-low latency access
"""

import time
import threading
from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import Any, Optional, Dict, List, Set
from dataclasses import dataclass
from enum import Enum
import logging

from .types import EvictionPolicy, CacheEntry as BaseCacheEntry


class L1Cache:
    """
    High-performance in-memory cache (L1)
    
    Features:
    - Multiple eviction policies (LRU, LFU, FIFO, TTL)
    - Thread-safe operations
    - Tag-based invalidation
    - Memory usage tracking
    - Performance metrics
    """
    
    def __init__(self, 
                 max_size: int = 10000,
                 ttl: Optional[int] = None,
                 eviction_policy: EvictionPolicy = EvictionPolicy.LRU):
        
        self.max_size = max_size
        self.default_ttl = ttl
        self.eviction_policy = eviction_policy
        
        # Storage
        self._cache: Dict[str, BaseCacheEntry] = {}
        self._access_order = OrderedDict()  # For LRU
        self._frequency_counter: Dict[str, int] = {}  # For LFU
        self._insertion_order = []  # For FIFO
        
        # Tag tracking
        self._tags_to_keys: Dict[str, Set[str]] = {}
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._memory_usage = 0
        
        self.logger = logging.getLogger(__name__)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._misses += 1
                return None
            
            # Check expiration
            if entry.is_expired():
                self._remove_entry(key)
                self._misses += 1
                return None
            
            # Update access metadata
            entry.touch()
            self._update_access_tracking(key)
            
            self._hits += 1
            return entry.value
    
    async def set(self, 
                  key: str, 
                  value: Any, 
                  ttl: Optional[int] = None,
                  tags: Optional[List[str]] = None) -> bool:
        """Set value in cache"""
        with self._lock:
            # Remove existing entry if present
            if key in self._cache:
                self._remove_entry(key)
            
            # Check if we need to evict
            if len(self._cache) >= self.max_size:
                self._evict_entries(1)
            
            # Create new entry
            entry = BaseCacheEntry(key, value, ttl or self.default_ttl)
            self._cache[key] = entry
            self._memory_usage += entry.size_bytes
            
            # Update tracking structures
            self._update_insertion_tracking(key)
            self._update_tag_tracking(key, entry.tags)
            
            return True
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        with self._lock:
            if key in self._cache:
                self._remove_entry(key)
                return True
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists and is not expired"""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False
            
            if entry.is_expired():
                self._remove_entry(key)
                return False
            
            return True
    
    async def clear(self):
        """Clear all entries"""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            self._frequency_counter.clear()
            self._insertion_order.clear()
            self._tags_to_keys.clear()
            self._memory_usage = 0
    
    async def invalidate_by_tags(self, tags: List[str]):
        """Invalidate entries by tags"""
        with self._lock:
            keys_to_remove = set()
            
            for tag in tags:
                if tag in self._tags_to_keys:
                    keys_to_remove.update(self._tags_to_keys[tag])
            
            for key in keys_to_remove:
                self._remove_entry(key)
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple keys efficiently"""
        results = {}
        
        with self._lock:
            for key in keys:
                value = await self.get(key)
                if value is not None:
                    results[key] = value
        
        return results
    
    async def set_many(self, items: Dict[str, Any], ttl: Optional[int] = None):
        """Set multiple keys efficiently"""
        with self._lock:
            for key, value in items.items():
                await self.set(key, value, ttl)
    
    def _remove_entry(self, key: str):
        """Remove entry and update tracking structures"""
        entry = self._cache.get(key)
        if entry is None:
            return
        
        # Remove from cache
        del self._cache[key]
        self._memory_usage -= entry.size_bytes
        
        # Update tracking structures
        self._access_order.pop(key, None)
        self._frequency_counter.pop(key, None)
        
        if key in self._insertion_order:
            self._insertion_order.remove(key)
        
        # Update tag tracking
        for tag in entry.tags:
            if tag in self._tags_to_keys:
                self._tags_to_keys[tag].discard(key)
                if not self._tags_to_keys[tag]:
                    del self._tags_to_keys[tag]
    
    def _evict_entries(self, count: int):
        """Evict entries based on eviction policy"""
        evicted = 0
        
        while evicted < count and self._cache:
            key_to_evict = self._select_eviction_candidate()
            if key_to_evict:
                self._remove_entry(key_to_evict)
                self._evictions += 1
                evicted += 1
            else:
                break
    
    def _select_eviction_candidate(self) -> Optional[str]:
        """Select key for eviction based on policy"""
        if not self._cache:
            return None
        
        if self.eviction_policy == EvictionPolicy.LRU:
            return self._select_lru_candidate()
        elif self.eviction_policy == EvictionPolicy.LFU:
            return self._select_lfu_candidate()
        elif self.eviction_policy == EvictionPolicy.FIFO:
            return self._select_fifo_candidate()
        elif self.eviction_policy == EvictionPolicy.TTL:
            return self._select_ttl_candidate()
        else:  # RANDOM
            return next(iter(self._cache.keys()))
    
    def _select_lru_candidate(self) -> Optional[str]:
        """Select least recently used key"""
        if self._access_order:
            return next(iter(self._access_order))
        
        # Fallback: find oldest accessed
        oldest_key = None
        oldest_time = float('inf')
        
        for key, entry in self._cache.items():
            if entry.accessed_at < oldest_time:
                oldest_time = entry.accessed_at
                oldest_key = key
        
        return oldest_key
    
    def _select_lfu_candidate(self) -> Optional[str]:
        """Select least frequently used key"""
        if not self._frequency_counter:
            return next(iter(self._cache.keys()))
        
        min_frequency = min(self._frequency_counter.values())
        
        for key, frequency in self._frequency_counter.items():
            if frequency == min_frequency:
                return key
        
        return None
    
    def _select_fifo_candidate(self) -> Optional[str]:
        """Select first inserted key"""
        if self._insertion_order:
            return self._insertion_order[0]
        
        # Fallback: find oldest created
        oldest_key = None
        oldest_time = float('inf')
        
        for key, entry in self._cache.items():
            if entry.created_at < oldest_time:
                oldest_time = entry.created_at
                oldest_key = key
        
        return oldest_key
    
    def _select_ttl_candidate(self) -> Optional[str]:
        """Select expired or soonest to expire key"""
        current_time = time.time()
        soonest_key = None
        soonest_expiry = float('inf')
        
        for key, entry in self._cache.items():
            if entry.ttl is None:
                continue
            
            expiry_time = entry.created_at + entry.ttl
            
            # Return expired entries immediately
            if expiry_time <= current_time:
                return key
            
            # Track soonest to expire
            if expiry_time < soonest_expiry:
                soonest_expiry = expiry_time
                soonest_key = key
        
        return soonest_key
    
    def _update_access_tracking(self, key: str):
        """Update access tracking for eviction policies"""
        # Update LRU tracking
        self._access_order.pop(key, None)
        self._access_order[key] = True
        
        # Update LFU tracking
        self._frequency_counter[key] = self._frequency_counter.get(key, 0) + 1
    
    def _update_insertion_tracking(self, key: str):
        """Update insertion tracking for FIFO"""
        if key not in self._insertion_order:
            self._insertion_order.append(key)
    
    def _update_tag_tracking(self, key: str, tags: Set[str]):
        """Update tag to key mapping"""
        for tag in tags:
            if tag not in self._tags_to_keys:
                self._tags_to_keys[tag] = set()
            self._tags_to_keys[tag].add(key)
    
    def _cleanup_expired(self):
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = []
        
        for key, entry in self._cache.items():
            if entry.is_expired():
                expired_keys.append(key)
        
        for key in expired_keys:
            self._remove_entry(key)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            # Clean up expired entries for accurate stats
            self._cleanup_expired()
            
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'utilization_pct': (len(self._cache) / self.max_size) * 100,
                'memory_usage_bytes': self._memory_usage,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate_pct': hit_rate,
                'evictions': self._evictions,
                'eviction_policy': self.eviction_policy.value,
                'tags_count': len(self._tags_to_keys)
            }
    
    def get_size(self) -> int:
        """Get current cache size"""
        with self._lock:
            return len(self._cache)
    
    def get_memory_usage(self) -> int:
        """Get estimated memory usage in bytes"""
        with self._lock:
            return self._memory_usage


class LRUCache(L1Cache):
    """Specialized LRU cache implementation"""
    
    def __init__(self, max_size: int = 10000, ttl: Optional[int] = None):
        super().__init__(max_size, ttl, EvictionPolicy.LRU)