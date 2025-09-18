"""Advanced rate limiting system for API requests and system protection.

This module provides comprehensive rate limiting capabilities including:
- Token bucket algorithm
- Sliding window rate limiting
- Fixed window rate limiting
- Distributed rate limiting with Redis
- Per-user and per-endpoint rate limiting
- Adaptive rate limiting based on system load
- Rate limiting middleware for web frameworks
"""

import asyncio
import time
import logging
import hashlib
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union, Tuple, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import threading
import json

try:
    import aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    aioredis = None

from config.performance_config import performance_manager

logger = logging.getLogger(__name__)

class RateLimitStrategy(Enum):
    """Rate limiting strategies."""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    ADAPTIVE = "adaptive"

@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    requests_per_second: float = 10.0
    requests_per_minute: float = 600.0
    requests_per_hour: float = 36000.0
    burst_size: int = 20
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET
    key_prefix: str = "rate_limit"
    distributed: bool = False
    redis_config: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate configuration."""
        if self.distributed and not REDIS_AVAILABLE:
            raise ImportError("Redis not available for distributed rate limiting")

@dataclass
class RateLimitResult:
    """Result of rate limit check."""
    allowed: bool
    remaining: int
    reset_time: datetime
    retry_after: Optional[int] = None
    current_usage: int = 0
    
    def to_headers(self) -> Dict[str, str]:
        """Convert to HTTP headers."""
        headers = {
            'X-RateLimit-Remaining': str(self.remaining),
            'X-RateLimit-Reset': str(int(self.reset_time.timestamp())),
        }
        
        if self.retry_after:
            headers['Retry-After'] = str(self.retry_after)
        
        return headers

class RateLimiter(ABC):
    """Abstract base class for rate limiters."""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._stats = defaultdict(int)
        self._lock = threading.Lock()
    
    @abstractmethod
    async def is_allowed(self, key: str, tokens: int = 1) -> RateLimitResult:
        """Check if request is allowed."""
        pass
    
    @abstractmethod
    async def reset(self, key: str):
        """Reset rate limit for key."""
        pass
    
    def get_stats(self) -> Dict[str, int]:
        """Get rate limiter statistics."""
        with self._lock:
            return dict(self._stats)
    
    def _increment_stat(self, stat_name: str, value: int = 1):
        """Increment statistics counter."""
        with self._lock:
            self._stats[stat_name] += value

class TokenBucketLimiter(RateLimiter):
    """Token bucket rate limiter."""
    
    def __init__(self, config: RateLimitConfig):
        super().__init__(config)
        self._buckets: Dict[str, Dict[str, Any]] = {}
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def is_allowed(self, key: str, tokens: int = 1) -> RateLimitResult:
        """Check if request is allowed using token bucket algorithm."""
        now = time.time()
        
        # Get or create bucket
        if key not in self._buckets:
            self._buckets[key] = {
                'tokens': self.config.burst_size,
                'last_refill': now,
                'created_at': now
            }
        
        bucket = self._buckets[key]
        
        # Calculate tokens to add
        time_passed = now - bucket['last_refill']
        tokens_to_add = time_passed * self.config.requests_per_second
        
        # Refill bucket
        bucket['tokens'] = min(
            self.config.burst_size,
            bucket['tokens'] + tokens_to_add
        )
        bucket['last_refill'] = now
        
        # Check if enough tokens
        if bucket['tokens'] >= tokens:
            bucket['tokens'] -= tokens
            self._increment_stat('requests_allowed')
            
            return RateLimitResult(
                allowed=True,
                remaining=int(bucket['tokens']),
                reset_time=datetime.fromtimestamp(
                    now + (self.config.burst_size - bucket['tokens']) / self.config.requests_per_second
                )
            )
        else:
            self._increment_stat('requests_denied')
            retry_after = int((tokens - bucket['tokens']) / self.config.requests_per_second) + 1
            
            return RateLimitResult(
                allowed=False,
                remaining=int(bucket['tokens']),
                reset_time=datetime.fromtimestamp(now + retry_after),
                retry_after=retry_after
            )
    
    async def reset(self, key: str):
        """Reset token bucket for key."""
        if key in self._buckets:
            self._buckets[key]['tokens'] = self.config.burst_size
            self._buckets[key]['last_refill'] = time.time()
    
    async def _cleanup_loop(self):
        """Clean up old buckets."""
        while True:
            try:
                await asyncio.sleep(300)  # Clean up every 5 minutes
                now = time.time()
                
                # Remove buckets older than 1 hour
                old_keys = [
                    key for key, bucket in self._buckets.items()
                    if now - bucket['created_at'] > 3600
                ]
                
                for key in old_keys:
                    del self._buckets[key]
                
                if old_keys:
                    logger.debug(f"Cleaned up {len(old_keys)} old rate limit buckets")
                    
            except Exception as e:
                logger.error(f"Error in rate limiter cleanup: {e}")

class SlidingWindowLimiter(RateLimiter):
    """Sliding window rate limiter."""
    
    def __init__(self, config: RateLimitConfig):
        super().__init__(config)
        self._windows: Dict[str, deque] = defaultdict(deque)
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def is_allowed(self, key: str, tokens: int = 1) -> RateLimitResult:
        """Check if request is allowed using sliding window."""
        now = time.time()
        window = self._windows[key]
        
        # Remove old entries
        cutoff_time = now - 60  # 1 minute window
        while window and window[0] < cutoff_time:
            window.popleft()
        
        # Check if under limit
        current_count = len(window)
        if current_count + tokens <= self.config.requests_per_minute:
            # Add new requests
            for _ in range(tokens):
                window.append(now)
            
            self._increment_stat('requests_allowed')
            
            return RateLimitResult(
                allowed=True,
                remaining=int(self.config.requests_per_minute - current_count - tokens),
                reset_time=datetime.fromtimestamp(window[0] + 60) if window else datetime.fromtimestamp(now + 60),
                current_usage=current_count + tokens
            )
        else:
            self._increment_stat('requests_denied')
            
            # Calculate retry after
            if window:
                retry_after = int(window[0] + 60 - now) + 1
            else:
                retry_after = 60
            
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=datetime.fromtimestamp(window[0] + 60) if window else datetime.fromtimestamp(now + 60),
                retry_after=retry_after,
                current_usage=current_count
            )
    
    async def reset(self, key: str):
        """Reset sliding window for key."""
        if key in self._windows:
            self._windows[key].clear()
    
    async def _cleanup_loop(self):
        """Clean up old windows."""
        while True:
            try:
                await asyncio.sleep(300)  # Clean up every 5 minutes
                now = time.time()
                cutoff_time = now - 3600  # Keep windows for 1 hour
                
                keys_to_remove = []
                for key, window in self._windows.items():
                    # Remove old entries from window
                    while window and window[0] < cutoff_time:
                        window.popleft()
                    
                    # Remove empty windows
                    if not window:
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del self._windows[key]
                
                if keys_to_remove:
                    logger.debug(f"Cleaned up {len(keys_to_remove)} empty rate limit windows")
                    
            except Exception as e:
                logger.error(f"Error in sliding window cleanup: {e}")

class FixedWindowLimiter(RateLimiter):
    """Fixed window rate limiter."""
    
    def __init__(self, config: RateLimitConfig):
        super().__init__(config)
        self._windows: Dict[str, Dict[str, Any]] = {}
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def is_allowed(self, key: str, tokens: int = 1) -> RateLimitResult:
        """Check if request is allowed using fixed window."""
        now = time.time()
        window_start = int(now // 60) * 60  # 1-minute windows
        
        # Get or create window
        if key not in self._windows or self._windows[key]['window_start'] != window_start:
            self._windows[key] = {
                'count': 0,
                'window_start': window_start,
                'created_at': now
            }
        
        window = self._windows[key]
        
        # Check if under limit
        if window['count'] + tokens <= self.config.requests_per_minute:
            window['count'] += tokens
            self._increment_stat('requests_allowed')
            
            return RateLimitResult(
                allowed=True,
                remaining=int(self.config.requests_per_minute - window['count']),
                reset_time=datetime.fromtimestamp(window_start + 60),
                current_usage=window['count']
            )
        else:
            self._increment_stat('requests_denied')
            
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=datetime.fromtimestamp(window_start + 60),
                retry_after=int(window_start + 60 - now) + 1,
                current_usage=window['count']
            )
    
    async def reset(self, key: str):
        """Reset fixed window for key."""
        if key in self._windows:
            self._windows[key]['count'] = 0
    
    async def _cleanup_loop(self):
        """Clean up old windows."""
        while True:
            try:
                await asyncio.sleep(300)  # Clean up every 5 minutes
                now = time.time()
                
                # Remove windows older than 1 hour
                old_keys = [
                    key for key, window in self._windows.items()
                    if now - window['created_at'] > 3600
                ]
                
                for key in old_keys:
                    del self._windows[key]
                
                if old_keys:
                    logger.debug(f"Cleaned up {len(old_keys)} old rate limit windows")
                    
            except Exception as e:
                logger.error(f"Error in fixed window cleanup: {e}")

class DistributedRateLimiter(RateLimiter):
    """Distributed rate limiter using Redis."""
    
    def __init__(self, config: RateLimitConfig):
        if not REDIS_AVAILABLE:
            raise ImportError("Redis not available for distributed rate limiting")
        
        super().__init__(config)
        self._redis = None
        self._connect_task = asyncio.create_task(self._connect_redis())
    
    async def _connect_redis(self):
        """Connect to Redis."""
        try:
            redis_config = self.config.redis_config or {}
            self._redis = await aioredis.create_redis_pool(
                f"redis://{redis_config.get('host', 'localhost')}:{redis_config.get('port', 6379)}",
                db=redis_config.get('db', 0),
                password=redis_config.get('password'),
                minsize=redis_config.get('minsize', 1),
                maxsize=redis_config.get('maxsize', 10)
            )
            logger.info("Connected to Redis for distributed rate limiting")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def is_allowed(self, key: str, tokens: int = 1) -> RateLimitResult:
        """Check if request is allowed using Redis-based sliding window."""
        if not self._redis:
            await self._connect_task
        
        now = time.time()
        redis_key = f"{self.config.key_prefix}:{key}"
        
        # Use Redis pipeline for atomic operations
        pipe = self._redis.pipeline()
        
        # Remove old entries
        cutoff_time = now - 60  # 1 minute window
        pipe.zremrangebyscore(redis_key, 0, cutoff_time)
        
        # Count current entries
        pipe.zcard(redis_key)
        
        # Execute pipeline
        results = await pipe.execute()
        current_count = results[1]
        
        if current_count + tokens <= self.config.requests_per_minute:
            # Add new requests
            pipe = self._redis.pipeline()
            for i in range(tokens):
                pipe.zadd(redis_key, now + i * 0.001, f"{now}_{i}")
            pipe.expire(redis_key, 120)  # Expire after 2 minutes
            await pipe.execute()
            
            self._increment_stat('requests_allowed')
            
            return RateLimitResult(
                allowed=True,
                remaining=int(self.config.requests_per_minute - current_count - tokens),
                reset_time=datetime.fromtimestamp(now + 60),
                current_usage=current_count + tokens
            )
        else:
            self._increment_stat('requests_denied')
            
            # Get oldest entry for retry calculation
            oldest_entries = await self._redis.zrange(redis_key, 0, 0, withscores=True)
            if oldest_entries:
                oldest_time = oldest_entries[0][1]
                retry_after = int(oldest_time + 60 - now) + 1
            else:
                retry_after = 60
            
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=datetime.fromtimestamp(now + retry_after),
                retry_after=retry_after,
                current_usage=current_count
            )
    
    async def reset(self, key: str):
        """Reset rate limit for key."""
        if not self._redis:
            await self._connect_task
        
        redis_key = f"{self.config.key_prefix}:{key}"
        await self._redis.delete(redis_key)
    
    async def close(self):
        """Close Redis connection."""
        if self._redis:
            self._redis.close()
            await self._redis.wait_closed()

class AdaptiveRateLimiter(RateLimiter):
    """Adaptive rate limiter that adjusts limits based on system load."""
    
    def __init__(self, config: RateLimitConfig, load_monitor: Optional[Callable[[], float]] = None):
        super().__init__(config)
        self._base_limiter = TokenBucketLimiter(config)
        self._load_monitor = load_monitor or self._default_load_monitor
        self._current_multiplier = 1.0
        self._adjustment_task = asyncio.create_task(self._adjustment_loop())
    
    def _default_load_monitor(self) -> float:
        """Default system load monitor."""
        try:
            import psutil
            return psutil.cpu_percent(interval=1) / 100.0
        except ImportError:
            return 0.5  # Default moderate load
    
    async def is_allowed(self, key: str, tokens: int = 1) -> RateLimitResult:
        """Check if request is allowed with adaptive limits."""
        # Adjust the base limiter's rate based on current load
        adjusted_config = RateLimitConfig(
            requests_per_second=self.config.requests_per_second * self._current_multiplier,
            requests_per_minute=self.config.requests_per_minute * self._current_multiplier,
            burst_size=int(self.config.burst_size * self._current_multiplier),
            strategy=self.config.strategy
        )
        
        # Temporarily update base limiter config
        original_config = self._base_limiter.config
        self._base_limiter.config = adjusted_config
        
        try:
            result = await self._base_limiter.is_allowed(key, tokens)
            return result
        finally:
            self._base_limiter.config = original_config
    
    async def reset(self, key: str):
        """Reset adaptive rate limit for key."""
        await self._base_limiter.reset(key)
    
    async def _adjustment_loop(self):
        """Periodically adjust rate limits based on system load."""
        while True:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds
                
                current_load = self._load_monitor()
                
                # Adjust multiplier based on load
                if current_load > 0.8:  # High load
                    self._current_multiplier = max(0.1, self._current_multiplier * 0.8)
                elif current_load > 0.6:  # Medium load
                    self._current_multiplier = max(0.3, self._current_multiplier * 0.9)
                elif current_load < 0.3:  # Low load
                    self._current_multiplier = min(2.0, self._current_multiplier * 1.1)
                elif current_load < 0.5:  # Medium-low load
                    self._current_multiplier = min(1.5, self._current_multiplier * 1.05)
                
                logger.debug(f"Adaptive rate limiter: load={current_load:.2f}, multiplier={self._current_multiplier:.2f}")
                
            except Exception as e:
                logger.error(f"Error in adaptive rate limiter adjustment: {e}")

class RateLimitManager:
    """Manages multiple rate limiters for different keys and endpoints."""
    
    def __init__(self, default_config: Optional[RateLimitConfig] = None):
        self.default_config = default_config or RateLimitConfig()
        self._limiters: Dict[str, RateLimiter] = {}
        self._configs: Dict[str, RateLimitConfig] = {}
        self._lock = threading.Lock()
        
        logger.info("Rate limit manager initialized")
    
    def create_limiter(self, name: str, config: Optional[RateLimitConfig] = None) -> RateLimiter:
        """Create a new rate limiter."""
        with self._lock:
            if name in self._limiters:
                return self._limiters[name]
            
            limiter_config = config or self.default_config
            self._configs[name] = limiter_config
            
            # Create appropriate limiter based on strategy
            if limiter_config.distributed:
                limiter = DistributedRateLimiter(limiter_config)
            elif limiter_config.strategy == RateLimitStrategy.TOKEN_BUCKET:
                limiter = TokenBucketLimiter(limiter_config)
            elif limiter_config.strategy == RateLimitStrategy.SLIDING_WINDOW:
                limiter = SlidingWindowLimiter(limiter_config)
            elif limiter_config.strategy == RateLimitStrategy.FIXED_WINDOW:
                limiter = FixedWindowLimiter(limiter_config)
            elif limiter_config.strategy == RateLimitStrategy.ADAPTIVE:
                limiter = AdaptiveRateLimiter(limiter_config)
            else:
                limiter = TokenBucketLimiter(limiter_config)
            
            self._limiters[name] = limiter
            logger.info(f"Created {limiter_config.strategy.value} rate limiter: {name}")
            return limiter
    
    def get_limiter(self, name: str) -> Optional[RateLimiter]:
        """Get rate limiter by name."""
        return self._limiters.get(name)
    
    async def is_allowed(self, limiter_name: str, key: str, tokens: int = 1) -> RateLimitResult:
        """Check if request is allowed for named limiter."""
        limiter = self.get_limiter(limiter_name)
        if not limiter:
            # Create default limiter if not exists
            limiter = self.create_limiter(limiter_name)
        
        return await limiter.is_allowed(key, tokens)
    
    async def reset(self, limiter_name: str, key: str):
        """Reset rate limit for key in named limiter."""
        limiter = self.get_limiter(limiter_name)
        if limiter:
            await limiter.reset(key)
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all rate limiters."""
        stats = {}
        for name, limiter in self._limiters.items():
            stats[name] = {
                'type': type(limiter).__name__,
                'config': self._configs[name].__dict__,
                'stats': limiter.get_stats(),
            }
        return stats
    
    async def close_all(self):
        """Close all rate limiters."""
        for name, limiter in self._limiters.items():
            try:
                if hasattr(limiter, 'close'):
                    await limiter.close()
                logger.info(f"Closed rate limiter: {name}")
            except Exception as e:
                logger.error(f"Error closing rate limiter {name}: {e}")
        
        self._limiters.clear()
        self._configs.clear()
        logger.info("All rate limiters closed")

def rate_limit_key(user_id: Optional[str] = None, endpoint: Optional[str] = None, 
                  ip_address: Optional[str] = None) -> str:
    """Generate rate limit key from user, endpoint, and IP."""
    parts = []
    
    if user_id:
        parts.append(f"user:{user_id}")
    if endpoint:
        parts.append(f"endpoint:{endpoint}")
    if ip_address:
        parts.append(f"ip:{ip_address}")
    
    if not parts:
        parts.append("global")
    
    return ":".join(parts)

def rate_limit_decorator(limiter_name: str, tokens: int = 1, 
                        key_func: Optional[Callable[..., str]] = None):
    """Decorator for rate limiting functions."""
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            # Generate key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = f"func:{func.__name__}"
            
            # Check rate limit
            result = await rate_limit_manager.is_allowed(limiter_name, key, tokens)
            
            if not result.allowed:
                raise Exception(f"Rate limit exceeded. Retry after {result.retry_after} seconds")
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

# Global rate limit manager
rate_limit_manager = RateLimitManager()

# Export commonly used classes
__all__ = [
    "RateLimiter",
    "TokenBucketLimiter",
    "SlidingWindowLimiter",
    "FixedWindowLimiter",
    "DistributedRateLimiter",
    "AdaptiveRateLimiter",
    "RateLimitManager",
    "RateLimitConfig",
    "RateLimitResult",
    "RateLimitStrategy",
    "rate_limit_manager",
    "rate_limit_key",
    "rate_limit_decorator",
]