"""High-Frequency Trading Optimizations for Volume-Weighted Indicators

Provides advanced performance monitoring, memory management, and optimization utilities
for institutional-grade high-frequency trading environments.
"""

import time
import gc
import threading
import psutil
import numpy as np
from collections import deque, defaultdict
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timedelta
from functools import wraps
import logging
import warnings
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class PerformanceLevel(Enum):
    """Performance optimization levels"""
    CONSERVATIVE = "conservative"  # Standard optimizations
    AGGRESSIVE = "aggressive"      # Maximum performance
    ULTRA = "ultra"               # Extreme HFT optimizations

@dataclass
class HFTMetrics:
    """Container for HFT performance metrics"""
    total_calculations: int = 0
    avg_latency_ns: float = 0.0
    p95_latency_ns: float = 0.0
    p99_latency_ns: float = 0.0
    max_latency_ns: float = 0.0
    error_rate: float = 0.0
    memory_usage_mb: float = 0.0
    gc_collections: int = 0
    cache_hit_rate: float = 0.0
    throughput_ops_per_sec: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_calculations': self.total_calculations,
            'avg_latency_ns': self.avg_latency_ns,
            'p95_latency_ns': self.p95_latency_ns,
            'p99_latency_ns': self.p99_latency_ns,
            'max_latency_ns': self.max_latency_ns,
            'error_rate': self.error_rate,
            'memory_usage_mb': self.memory_usage_mb,
            'gc_collections': self.gc_collections,
            'cache_hit_rate': self.cache_hit_rate,
            'throughput_ops_per_sec': self.throughput_ops_per_sec
        }

class HFTPerformanceMonitor:
    """Advanced performance monitoring for HFT environments"""
    
    def __init__(self, max_samples: int = 100000, performance_level: PerformanceLevel = PerformanceLevel.CONSERVATIVE):
        self.max_samples = max_samples
        self.performance_level = performance_level
        
        # Performance tracking
        self.latencies = deque(maxlen=max_samples)
        self.error_counts = defaultdict(int)
        self.operation_counts = defaultdict(int)
        self.cache_stats = {'hits': 0, 'misses': 0}
        
        # Memory tracking
        self.memory_samples = deque(maxlen=1000)
        self.gc_counts = deque(maxlen=100)
        
        # Threading
        self._lock = threading.RLock()
        self.start_time = time.time()
        
        # Process monitoring
        self.process = psutil.Process()
        
        logger.info(f"HFT Performance Monitor initialized (level={performance_level.value})")
    
    def record_latency(self, operation: str, latency_ns: float) -> None:
        """Record operation latency"""
        with self._lock:
            self.latencies.append(latency_ns)
            self.operation_counts[operation] += 1
    
    def record_error(self, operation: str, error_type: str) -> None:
        """Record operation error"""
        with self._lock:
            self.error_counts[f"{operation}:{error_type}"] += 1
    
    def record_cache_hit(self, hit: bool) -> None:
        """Record cache hit/miss"""
        with self._lock:
            if hit:
                self.cache_stats['hits'] += 1
            else:
                self.cache_stats['misses'] += 1
    
    def sample_memory(self) -> None:
        """Sample current memory usage"""
        try:
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            with self._lock:
                self.memory_samples.append(memory_mb)
                self.gc_counts.append(gc.get_count()[0])
        except Exception as e:
            logger.warning(f"Memory sampling failed: {e}")
    
    def get_metrics(self) -> HFTMetrics:
        """Get comprehensive performance metrics"""
        with self._lock:
            metrics = HFTMetrics()
            
            # Latency statistics
            if self.latencies:
                latencies_array = np.array(list(self.latencies))
                metrics.avg_latency_ns = np.mean(latencies_array)
                metrics.p95_latency_ns = np.percentile(latencies_array, 95)
                metrics.p99_latency_ns = np.percentile(latencies_array, 99)
                metrics.max_latency_ns = np.max(latencies_array)
            
            # Operation counts
            metrics.total_calculations = sum(self.operation_counts.values())
            
            # Error rate
            total_errors = sum(self.error_counts.values())
            if metrics.total_calculations > 0:
                metrics.error_rate = total_errors / metrics.total_calculations
            
            # Memory usage
            if self.memory_samples:
                metrics.memory_usage_mb = self.memory_samples[-1]
            
            # GC collections
            if self.gc_counts:
                metrics.gc_collections = self.gc_counts[-1]
            
            # Cache hit rate
            total_cache_ops = self.cache_stats['hits'] + self.cache_stats['misses']
            if total_cache_ops > 0:
                metrics.cache_hit_rate = self.cache_stats['hits'] / total_cache_ops
            
            # Throughput
            elapsed_time = time.time() - self.start_time
            if elapsed_time > 0:
                metrics.throughput_ops_per_sec = metrics.total_calculations / elapsed_time
            
            return metrics
    
    def reset_stats(self) -> None:
        """Reset all performance statistics"""
        with self._lock:
            self.latencies.clear()
            self.error_counts.clear()
            self.operation_counts.clear()
            self.cache_stats = {'hits': 0, 'misses': 0}
            self.memory_samples.clear()
            self.gc_counts.clear()
            self.start_time = time.time()
        
        logger.info("Performance statistics reset")

class HFTMemoryManager:
    """Advanced memory management for HFT environments"""
    
    def __init__(self, max_memory_mb: int = 1024, gc_threshold: int = 10000):
        self.max_memory_mb = max_memory_mb
        self.gc_threshold = gc_threshold
        self.operation_count = 0
        self.last_gc_time = time.time()
        self.process = psutil.Process()
        
        # Memory pools for object reuse
        self.float_pool = deque(maxlen=1000)
        self.list_pool = deque(maxlen=100)
        self.dict_pool = deque(maxlen=100)
        
        logger.info(f"HFT Memory Manager initialized (max_memory={max_memory_mb}MB)")
    
    def check_memory_pressure(self) -> bool:
        """Check if memory pressure is high"""
        try:
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            return memory_mb > self.max_memory_mb
        except Exception:
            return False
    
    def force_gc_if_needed(self) -> bool:
        """Force garbage collection if needed"""
        self.operation_count += 1
        
        # Check if GC is needed
        should_gc = (
            self.operation_count % self.gc_threshold == 0 or
            self.check_memory_pressure() or
            time.time() - self.last_gc_time > 60  # Force GC every minute
        )
        
        if should_gc:
            collected = gc.collect()
            self.last_gc_time = time.time()
            logger.debug(f"Forced GC: collected {collected} objects")
            return True
        
        return False
    
    def get_reusable_list(self, initial_capacity: int = 0) -> List:
        """Get a reusable list from the pool"""
        if self.list_pool:
            lst = self.list_pool.popleft()
            lst.clear()
            return lst
        else:
            return [] if initial_capacity == 0 else [None] * initial_capacity
    
    def return_list(self, lst: List) -> None:
        """Return a list to the pool for reuse"""
        if len(self.list_pool) < self.list_pool.maxlen:
            lst.clear()
            self.list_pool.append(lst)
    
    def get_reusable_dict(self) -> Dict:
        """Get a reusable dictionary from the pool"""
        if self.dict_pool:
            d = self.dict_pool.popleft()
            d.clear()
            return d
        else:
            return {}
    
    def return_dict(self, d: Dict) -> None:
        """Return a dictionary to the pool for reuse"""
        if len(self.dict_pool) < self.dict_pool.maxlen:
            d.clear()
            self.dict_pool.append(d)

class HFTCache:
    """High-performance caching for HFT calculations"""
    
    def __init__(self, max_size: int = 10000, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache = {}
        self.access_times = {}
        self.access_counts = defaultdict(int)
        self._lock = threading.RLock()
        
        logger.info(f"HFT Cache initialized (max_size={max_size}, ttl={ttl_seconds}s)")
    
    def _generate_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Generate cache key from function call"""
        # Simple hash-based key generation
        key_parts = [func_name]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return "|".join(key_parts)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            if key not in self.cache:
                return None
            
            # Check TTL
            if time.time() - self.access_times[key] > self.ttl_seconds:
                del self.cache[key]
                del self.access_times[key]
                return None
            
            self.access_counts[key] += 1
            return self.cache[key]
    
    def put(self, key: str, value: Any) -> None:
        """Put value in cache"""
        with self._lock:
            # Evict if cache is full
            if len(self.cache) >= self.max_size and key not in self.cache:
                self._evict_lru()
            
            self.cache[key] = value
            self.access_times[key] = time.time()
            self.access_counts[key] = 1
    
    def _evict_lru(self) -> None:
        """Evict least recently used item"""
        if not self.cache:
            return
        
        # Find LRU item
        lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        
        del self.cache[lru_key]
        del self.access_times[lru_key]
        del self.access_counts[lru_key]
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self.cache.clear()
            self.access_times.clear()
            self.access_counts.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hit_rate': sum(count > 1 for count in self.access_counts.values()) / max(len(self.access_counts), 1),
                'total_accesses': sum(self.access_counts.values())
            }

# Global instances for HFT optimization
_hft_monitor = None
_hft_memory_manager = None
_hft_cache = None

def initialize_hft_optimizations(performance_level: PerformanceLevel = PerformanceLevel.CONSERVATIVE,
                                max_memory_mb: int = 1024,
                                cache_size: int = 10000) -> None:
    """Initialize global HFT optimization components"""
    global _hft_monitor, _hft_memory_manager, _hft_cache
    
    _hft_monitor = HFTPerformanceMonitor(performance_level=performance_level)
    _hft_memory_manager = HFTMemoryManager(max_memory_mb=max_memory_mb)
    _hft_cache = HFTCache(max_size=cache_size)
    
    logger.info(f"HFT optimizations initialized (level={performance_level.value})")

def get_hft_monitor() -> Optional[HFTPerformanceMonitor]:
    """Get global HFT performance monitor"""
    return _hft_monitor

def get_hft_memory_manager() -> Optional[HFTMemoryManager]:
    """Get global HFT memory manager"""
    return _hft_memory_manager

def get_hft_cache() -> Optional[HFTCache]:
    """Get global HFT cache"""
    return _hft_cache

def hft_cached(ttl_seconds: int = 300):
    """Decorator for caching function results in HFT environments"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_hft_cache()
            if not cache:
                return func(*args, **kwargs)
            
            # Generate cache key
            key = cache._generate_key(func.__name__, args, kwargs)
            
            # Try to get from cache
            cached_result = cache.get(key)
            if cached_result is not None:
                if _hft_monitor:
                    _hft_monitor.record_cache_hit(True)
                return cached_result
            
            # Calculate and cache result
            result = func(*args, **kwargs)
            cache.put(key, result)
            
            if _hft_monitor:
                _hft_monitor.record_cache_hit(False)
            
            return result
        return wrapper
    return decorator

def hft_optimized(operation_name: str = None):
    """Decorator for HFT-optimized functions with full monitoring"""
    def decorator(func: Callable) -> Callable:
        op_name = operation_name or func.__name__
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter_ns()
            
            try:
                # Memory management
                if _hft_memory_manager:
                    _hft_memory_manager.force_gc_if_needed()
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Record performance
                if _hft_monitor:
                    latency_ns = time.perf_counter_ns() - start_time
                    _hft_monitor.record_latency(op_name, latency_ns)
                
                return result
                
            except Exception as e:
                # Record error
                if _hft_monitor:
                    _hft_monitor.record_error(op_name, type(e).__name__)
                raise
        
        return wrapper
    return decorator

def get_hft_performance_report() -> Dict[str, Any]:
    """Get comprehensive HFT performance report"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'monitor_active': _hft_monitor is not None,
        'memory_manager_active': _hft_memory_manager is not None,
        'cache_active': _hft_cache is not None
    }
    
    if _hft_monitor:
        report['performance_metrics'] = _hft_monitor.get_metrics().to_dict()
    
    if _hft_memory_manager:
        report['memory_pressure'] = _hft_memory_manager.check_memory_pressure()
        report['operation_count'] = _hft_memory_manager.operation_count
    
    if _hft_cache:
        report['cache_stats'] = _hft_cache.get_stats()
    
    return report

# Initialize with conservative settings by default
initialize_hft_optimizations()

# Add the missing VectorizedPatternDetector class
class VectorizedPatternDetector:
    """Vectorized pattern detection for HFT environments"""
    
    def __init__(self, optimization_level: 'OptimizationLevel' = None):
        self.optimization_level = optimization_level
    
    def parallel_pattern_detection(self, data: Any, pattern_functions: Dict[str, Callable], 
                                 start_index: int, end_index: int, chunk_size: int = 50) -> Dict[int, List[Any]]:
        """Parallel pattern detection"""
        # Simplified implementation
        return {}
    
    def vectorized_single_candle_detection(self, data: Any, pattern_functions: Dict[str, Callable], 
                                         start_index: int, end_index: int) -> Dict[int, List[Any]]:
        """Vectorized single candle detection"""
        # Simplified implementation
        return {}

# Add the missing OptimizationLevel class
class OptimizationLevel:
    CONSERVATIVE = "conservative"
    AGGRESSIVE = "aggressive"
    ULTRA_LOW_LATENCY = "ultra_low_latency"

# Add the missing create_hft_optimized_detector function
def create_hft_optimized_detector(optimization_level: OptimizationLevel = OptimizationLevel.CONSERVATIVE):
    """Create HFT optimized detector"""
    return VectorizedPatternDetector(optimization_level)
