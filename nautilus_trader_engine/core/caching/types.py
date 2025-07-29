"""
Caching Types and Enums
Common types used across the caching system
"""

from enum import Enum
from typing import Any, Optional
from dataclasses import dataclass


class EvictionPolicy(Enum):
    """Cache eviction policies"""
    LRU = "lru"           # Least Recently Used
    LFU = "lfu"           # Least Frequently Used
    FIFO = "fifo"         # First In, First Out
    RANDOM = "random"     # Random eviction
    TTL = "ttl"           # Time To Live based


class CacheLevel(Enum):
    """Cache hierarchy levels"""
    L1 = "l1"             # In-memory cache
    L2 = "l2"             # Distributed cache (Redis)
    L3 = "l3"             # Persistent cache (Database)


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    ttl: Optional[int] = None
    access_count: int = 0
    created_at: float = 0.0
    last_accessed: float = 0.0
    size_bytes: int = 0
    tags: set = None
    
    def __post_init__(self):
        """Initialize timestamps if not set"""
        import time
        if self.created_at == 0.0:
            self.created_at = time.time()
        if self.last_accessed == 0.0:
            self.last_accessed = self.created_at
        if self.size_bytes == 0:
            self.size_bytes = self._calculate_size()
        if self.tags is None:
            self.tags = set()
    
    def _calculate_size(self) -> int:
        """Calculate approximate size of cached value"""
        try:
            import pickle
            return len(pickle.dumps(self.value))
        except:
            return len(str(self.value).encode('utf-8'))
    
    def is_expired(self) -> bool:
        """Check if entry has expired"""
        if self.ttl is None:
            return False
        import time
        return time.time() - self.created_at > self.ttl
    
    def touch(self):
        """Update access time and count"""
        import time
        self.last_accessed = time.time()
        self.access_count += 1


@dataclass
class CacheStats:
    """Cache statistics"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    max_size: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate hit rate"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    @property
    def utilization(self) -> float:
        """Calculate cache utilization"""
        return self.size / self.max_size if self.max_size > 0 else 0.0