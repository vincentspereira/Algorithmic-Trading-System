"""
Shared rate limiting utilities for the Algorithmic Trading System.

This module consolidates all rate limiting implementations that were previously
duplicated across multiple components. Provides consistent rate limiting for
APIs, data feeds, and other system components.
"""

import asyncio
import time
from collections import defaultdict, deque
from typing import Dict, Optional, Union, Tuple, Any
from datetime import datetime, timedelta
from enum import Enum
import redis
import logging


logger = logging.getLogger(__name__)


class RateLimitAlgorithm(Enum):
    """Rate limiting algorithms"""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    LEAKY_BUCKET = "leaky_bucket"


class RateLimitResult(Enum):
    """Rate limit check results"""
    ALLOWED = "allowed"
    DENIED = "denied"
    ERROR = "error"


class RateLimitInfo:
    """Rate limit information"""
    
    def __init__(
        self,
        limit: int,
        remaining: int,
        reset_time: Union[datetime, int],
        retry_after: Optional[int] = None
    ):
        self.limit = limit
        self.remaining = remaining
        self.reset_time = reset_time
        self.retry_after = retry_after
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "limit": self.limit,
            "remaining": self.remaining,
            "reset_time": int(self.reset_time.timestamp()) if isinstance(self.reset_time, datetime) else self.reset_time,
            "retry_after": self.retry_after
        }


class RateLimitRule:
    """Rate limiting rule configuration"""
    
    def __init__(
        self,
        limit: int,
        window_seconds: int,
        algorithm: RateLimitAlgorithm = RateLimitAlgorithm.SLIDING_WINDOW,
        burst_limit: Optional[int] = None
    ):
        self.limit = limit
        self.window_seconds = window_seconds
        self.algorithm = algorithm
        self.burst_limit = burst_limit or limit


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter implementation.
    
    Allows bursts up to bucket capacity while maintaining average rate.
    """
    
    def __init__(
        self,
        capacity: int,
        refill_rate: float,
        initial_tokens: Optional[int] = None
    ):
        self.capacity = capacity
        self.refill_rate = refill_rate  # tokens per second
        self.tokens = initial_tokens if initial_tokens is not None else capacity
        self.last_refill = time.time()
        self._lock = asyncio.Lock() if hasattr(asyncio, 'current_task') else None
    
    async def is_allowed(self, tokens_requested: int = 1) -> Tuple[bool, RateLimitInfo]:
        """
        Check if request is allowed and consume tokens.
        
        Args:
            tokens_requested: Number of tokens to consume
            
        Returns:
            Tuple of (allowed, rate_limit_info)
        """
        if self._lock:
            async with self._lock:
                return self._check_and_consume(tokens_requested)
        else:
            return self._check_and_consume(tokens_requested)
    
    def _check_and_consume(self, tokens_requested: int) -> Tuple[bool, RateLimitInfo]:
        """Internal method to check and consume tokens"""
        now = time.time()
        
        # Refill tokens based on elapsed time
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
        
        # Check if we have enough tokens
        if self.tokens >= tokens_requested:
            self.tokens -= tokens_requested
            
            # Calculate reset time (when bucket will be full)
            time_to_full = (self.capacity - self.tokens) / self.refill_rate
            reset_time = datetime.fromtimestamp(now + time_to_full)
            
            return True, RateLimitInfo(
                limit=self.capacity,
                remaining=int(self.tokens),
                reset_time=reset_time
            )
        else:
            # Calculate retry after time
            tokens_needed = tokens_requested - self.tokens
            retry_after = int(tokens_needed / self.refill_rate) + 1
            
            return False, RateLimitInfo(
                limit=self.capacity,
                remaining=int(self.tokens),
                reset_time=datetime.fromtimestamp(now + retry_after),
                retry_after=retry_after
            )


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter implementation.
    
    Provides precise rate limiting with sliding time windows.
    """
    
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window_seconds = window_seconds
        self.requests: Dict[str, deque] = defaultdict(deque)
        self._lock = asyncio.Lock() if hasattr(asyncio, 'current_task') else None
    
    async def is_allowed(self, key: str) -> Tuple[bool, RateLimitInfo]:
        """
        Check if request is allowed.
        
        Args:
            key: Unique identifier for the rate limit (e.g., user ID, IP)
            
        Returns:
            Tuple of (allowed, rate_limit_info)
        """
        if self._lock:
            async with self._lock:
                return self._check_limit(key)
        else:
            return self._check_limit(key)
    
    def _check_limit(self, key: str) -> Tuple[bool, RateLimitInfo]:
        """Internal method to check rate limit"""
        now = time.time()
        window_start = now - self.window_seconds
        
        # Remove old requests outside the window
        while self.requests[key] and self.requests[key][0] < window_start:
            self.requests[key].popleft()
        
        current_count = len(self.requests[key])
        
        if current_count < self.limit:
            # Request allowed
            self.requests[key].append(now)
            remaining = self.limit - current_count - 1
            
            # Calculate reset time (when oldest request expires)
            if self.requests[key]:
                oldest_request = self.requests[key][0]
                reset_time = datetime.fromtimestamp(oldest_request + self.window_seconds)
            else:
                reset_time = datetime.fromtimestamp(now + self.window_seconds)
            
            return True, RateLimitInfo(
                limit=self.limit,
                remaining=remaining,
                reset_time=reset_time
            )
        else:
            # Request denied
            oldest_request = self.requests[key][0]
            retry_after = int(oldest_request + self.window_seconds - now) + 1
            
            return False, RateLimitInfo(
                limit=self.limit,
                remaining=0,
                reset_time=datetime.fromtimestamp(oldest_request + self.window_seconds),
                retry_after=retry_after
            )


class RedisRateLimiter:
    """
    Redis-backed rate limiter for distributed systems.
    
    Uses Redis for shared rate limiting state across multiple instances.
    """
    
    def __init__(
        self,
        redis_client: redis.Redis,
        limit: int,
        window_seconds: int,
        key_prefix: str = "rate_limit"
    ):
        self.redis_client = redis_client
        self.limit = limit
        self.window_seconds = window_seconds
        self.key_prefix = key_prefix
    
    async def is_allowed(self, key: str) -> Tuple[bool, RateLimitInfo]:
        """
        Check if request is allowed using Redis.
        
        Args:
            key: Unique identifier for the rate limit
            
        Returns:
            Tuple of (allowed, rate_limit_info)
        """
        redis_key = f"{self.key_prefix}:{key}"
        now = time.time()
        window_start = now - self.window_seconds
        
        try:
            # Use Redis pipeline for atomic operations
            pipe = self.redis_client.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(redis_key, 0, window_start)
            
            # Count current entries
            pipe.zcard(redis_key)
            
            # Add current request
            pipe.zadd(redis_key, {str(now): now})
            
            # Set expiry
            pipe.expire(redis_key, self.window_seconds)
            
            # Execute pipeline
            results = pipe.execute()
            current_count = results[1]  # Count from zcard
            
            if current_count < self.limit:
                # Request allowed
                remaining = self.limit - current_count - 1
                reset_time = datetime.fromtimestamp(now + self.window_seconds)
                
                return True, RateLimitInfo(
                    limit=self.limit,
                    remaining=remaining,
                    reset_time=reset_time
                )
            else:
                # Request denied - remove the request we just added
                self.redis_client.zrem(redis_key, str(now))
                
                # Get oldest entry to calculate retry time
                oldest_entries = self.redis_client.zrange(redis_key, 0, 0, withscores=True)
                if oldest_entries:
                    oldest_time = oldest_entries[0][1]
                    retry_after = int(oldest_time + self.window_seconds - now) + 1
                else:
                    retry_after = self.window_seconds
                
                return False, RateLimitInfo(
                    limit=self.limit,
                    remaining=0,
                    reset_time=datetime.fromtimestamp(now + retry_after),
                    retry_after=retry_after
                )
        
        except Exception as e:
            logger.error(f"Redis rate limiting error: {e}")
            # Fallback to allowing request on Redis error
            return True, RateLimitInfo(
                limit=self.limit,
                remaining=self.limit - 1,
                reset_time=datetime.fromtimestamp(now + self.window_seconds)
            )


class FixedWindowRateLimiter:
    """
    Fixed window rate limiter implementation.
    
    Simple rate limiting with fixed time windows.
    """
    
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window_seconds = window_seconds
        self.windows: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
        self._lock = asyncio.Lock() if hasattr(asyncio, 'current_task') else None
    
    async def is_allowed(self, key: str) -> Tuple[bool, RateLimitInfo]:
        """
        Check if request is allowed.
        
        Args:
            key: Unique identifier for the rate limit
            
        Returns:
            Tuple of (allowed, rate_limit_info)
        """
        if self._lock:
            async with self._lock:
                return self._check_limit(key)
        else:
            return self._check_limit(key)
    
    def _check_limit(self, key: str) -> Tuple[bool, RateLimitInfo]:
        """Internal method to check rate limit"""
        now = time.time()
        current_window = int(now // self.window_seconds)
        
        # Clean old windows
        old_windows = [w for w in self.windows[key] if w < current_window]
        for w in old_windows:
            del self.windows[key][w]
        
        current_count = self.windows[key][current_window]
        
        if current_count < self.limit:
            # Request allowed
            self.windows[key][current_window] += 1
            remaining = self.limit - current_count - 1
            
            # Calculate reset time (end of current window)
            reset_time = datetime.fromtimestamp((current_window + 1) * self.window_seconds)
            
            return True, RateLimitInfo(
                limit=self.limit,
                remaining=remaining,
                reset_time=reset_time
            )
        else:
            # Request denied
            retry_after = int((current_window + 1) * self.window_seconds - now)
            
            return False, RateLimitInfo(
                limit=self.limit,
                remaining=0,
                reset_time=datetime.fromtimestamp((current_window + 1) * self.window_seconds),
                retry_after=retry_after
            )


class RateLimiter:
    """
    Unified rate limiter supporting multiple algorithms.
    """
    
    def __init__(
        self,
        rule: RateLimitRule,
        redis_client: Optional[redis.Redis] = None,
        key_prefix: str = "rate_limit"
    ):
        self.rule = rule
        self.redis_client = redis_client
        self.key_prefix = key_prefix
        
        # Initialize appropriate limiter based on algorithm
        if rule.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            self.limiter = TokenBucketRateLimiter(
                capacity=rule.limit,
                refill_rate=rule.limit / rule.window_seconds
            )
        elif rule.algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
            if redis_client:
                self.limiter = RedisRateLimiter(
                    redis_client=redis_client,
                    limit=rule.limit,
                    window_seconds=rule.window_seconds,
                    key_prefix=key_prefix
                )
            else:
                self.limiter = SlidingWindowRateLimiter(
                    limit=rule.limit,
                    window_seconds=rule.window_seconds
                )
        elif rule.algorithm == RateLimitAlgorithm.FIXED_WINDOW:
            self.limiter = FixedWindowRateLimiter(
                limit=rule.limit,
                window_seconds=rule.window_seconds
            )
        else:
            raise ValueError(f"Unsupported algorithm: {rule.algorithm}")
    
    async def check_limit(self, key: str) -> Tuple[RateLimitResult, RateLimitInfo]:
        """
        Check rate limit for given key.
        
        Args:
            key: Unique identifier for the rate limit
            
        Returns:
            Tuple of (result, rate_limit_info)
        """
        try:
            if isinstance(self.limiter, TokenBucketRateLimiter):
                allowed, info = await self.limiter.is_allowed()
            else:
                allowed, info = await self.limiter.is_allowed(key)
            
            return (RateLimitResult.ALLOWED if allowed else RateLimitResult.DENIED), info
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Return error result with default info
            return RateLimitResult.ERROR, RateLimitInfo(
                limit=self.rule.limit,
                remaining=0,
                reset_time=datetime.now() + timedelta(seconds=self.rule.window_seconds)
            )


class AdaptiveRateLimiter:
    """
    Adaptive rate limiter that adjusts limits based on system load.
    """
    
    def __init__(
        self,
        base_limit: int,
        window_seconds: int,
        min_limit: int = 1,
        max_limit: Optional[int] = None,
        adaptation_factor: float = 0.1
    ):
        self.base_limit = base_limit
        self.current_limit = base_limit
        self.window_seconds = window_seconds
        self.min_limit = min_limit
        self.max_limit = max_limit or base_limit * 2
        self.adaptation_factor = adaptation_factor
        
        self.limiter = SlidingWindowRateLimiter(
            limit=self.current_limit,
            window_seconds=window_seconds
        )
        
        self.error_count = 0
        self.success_count = 0
        self.last_adaptation = time.time()
    
    async def is_allowed(self, key: str, system_load: Optional[float] = None) -> Tuple[bool, RateLimitInfo]:
        """
        Check if request is allowed with adaptive limiting.
        
        Args:
            key: Unique identifier for the rate limit
            system_load: Current system load (0.0 to 1.0)
            
        Returns:
            Tuple of (allowed, rate_limit_info)
        """
        # Adapt limit based on system load
        if system_load is not None:
            self._adapt_to_load(system_load)
        
        # Check with current limiter
        allowed, info = await self.limiter.is_allowed(key)
        
        # Track success/error for adaptation
        if allowed:
            self.success_count += 1
        else:
            self.error_count += 1
        
        # Periodic adaptation based on success/error ratio
        self._periodic_adaptation()
        
        return allowed, info
    
    def _adapt_to_load(self, system_load: float):
        """Adapt rate limit based on system load"""
        if system_load > 0.8:  # High load
            target_limit = max(self.min_limit, int(self.base_limit * 0.5))
        elif system_load > 0.6:  # Medium load
            target_limit = int(self.base_limit * 0.75)
        else:  # Low load
            target_limit = min(self.max_limit, int(self.base_limit * 1.25))
        
        if target_limit != self.current_limit:
            self.current_limit = target_limit
            self.limiter = SlidingWindowRateLimiter(
                limit=self.current_limit,
                window_seconds=self.window_seconds
            )
    
    def _periodic_adaptation(self):
        """Periodically adapt based on success/error ratio"""
        now = time.time()
        if now - self.last_adaptation > 60:  # Adapt every minute
            total_requests = self.success_count + self.error_count
            
            if total_requests > 0:
                error_rate = self.error_count / total_requests
                
                if error_rate > 0.1:  # Too many errors, reduce limit
                    new_limit = max(self.min_limit, int(self.current_limit * (1 - self.adaptation_factor)))
                elif error_rate < 0.01:  # Very few errors, increase limit
                    new_limit = min(self.max_limit, int(self.current_limit * (1 + self.adaptation_factor)))
                else:
                    new_limit = self.current_limit
                
                if new_limit != self.current_limit:
                    self.current_limit = new_limit
                    self.limiter = SlidingWindowRateLimiter(
                        limit=self.current_limit,
                        window_seconds=self.window_seconds
                    )
            
            # Reset counters
            self.success_count = 0
            self.error_count = 0
            self.last_adaptation = now


async def rate_limit_decorator(
    rule: RateLimitRule,
    key_func: Optional[callable] = None,
    redis_client: Optional[redis.Redis] = None
):
    """
    Decorator for rate limiting function calls.
    
    Args:
        rule: Rate limiting rule
        key_func: Function to generate rate limit key from arguments
        redis_client: Redis client for distributed rate limiting
        
    Examples:
        @rate_limit_decorator(RateLimitRule(limit=10, window_seconds=60))
        async def api_call(user_id: str):
            # API call implementation
            pass
    """
    def decorator(func):
        limiter = RateLimiter(rule, redis_client)
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate rate limit key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = f"{func.__name__}"
            
            # Check rate limit
            result, info = await limiter.check_limit(key)
            
            if result == RateLimitResult.DENIED:
                from .error_handling import RateLimitError
                raise RateLimitError(
                    f"Rate limit exceeded for {key}",
                    retry_after=info.retry_after
                )
            elif result == RateLimitResult.ERROR:
                logger.warning(f"Rate limit check failed for {key}, allowing request")
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator