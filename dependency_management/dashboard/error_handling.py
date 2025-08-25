"""
Retry and error handling utilities.
"""

import asyncio
import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, Type, Union
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

logger = logging.getLogger(__name__)

class RateLimitError(Exception):
    """Rate limit exceeded error"""
    pass

class RetryableError(Exception):
    """Base class for retryable errors"""
    pass

def with_retry(
    retries: int = 3,
    min_wait: float = 1,
    max_wait: float = 10,
    retry_exceptions: tuple = (RetryableError, httpx.NetworkError)
) -> Callable:
    """Retry decorator with exponential backoff"""
    
    def decorator(func: Callable) -> Callable:
        @retry(
            stop=stop_after_attempt(retries),
            wait=wait_exponential(multiplier=min_wait, max=max_wait),
            retry=retry_if_exception_type(retry_exceptions),
            before_sleep=lambda retry_state: logger.warning(
                f"Retrying {func.__name__} after error: "
                f"{retry_state.outcome.exception()}"
            )
        )
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)
            
        return wrapper
        
    return decorator

class RateLimiter:
    """Rate limiter for API calls"""
    
    def __init__(
        self,
        calls: int,
        period: float,
        raise_on_limit: bool = True
    ):
        self.calls = calls
        self.period = period
        self.raise_on_limit = raise_on_limit
        self.calls_made = []
        
    async def __aenter__(self):
        """Check rate limit before making call"""
        now = time.time()
        
        # Remove old calls
        self.calls_made = [
            t for t in self.calls_made
            if now - t < self.period
        ]
        
        if len(self.calls_made) >= self.calls:
            if self.raise_on_limit:
                raise RateLimitError(
                    f"Rate limit exceeded: {self.calls} calls per {self.period}s"
                )
            # Wait until we can make another call
            sleep_time = self.calls_made[0] + self.period - now
            if sleep_time > 0:
                logger.warning(
                    f"Rate limit reached, waiting {sleep_time:.2f}s"
                )
                await asyncio.sleep(sleep_time)
                # Remove expired calls after waiting
                now = time.time()
                self.calls_made = [
                    t for t in self.calls_made
                    if now - t < self.period
                ]
                
        self.calls_made.append(now)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """No cleanup needed"""
        pass

class ErrorTracker:
    """Track and log errors"""
    
    def __init__(self):
        self.errors: Dict[str, Dict] = {}
        
    def record_error(
        self,
        error_type: Union[str, Type[Exception]],
        message: str,
        context: Optional[Dict] = None
    ) -> None:
        """Record an error occurrence"""
        if isinstance(error_type, type):
            error_type = error_type.__name__
            
        if error_type not in self.errors:
            self.errors[error_type] = {
                "count": 0,
                "first_seen": time.time(),
                "last_seen": time.time(),
                "contexts": []
            }
            
        error_info = self.errors[error_type]
        error_info["count"] += 1
        error_info["last_seen"] = time.time()
        
        if context:
            error_info["contexts"].append({
                "time": time.time(),
                "message": message,
                "context": context
            })
            
        # Log the error
        logger.error(
            f"{error_type}: {message}",
            extra={
                "error_type": error_type,
                "context": context
            }
        )
        
    def get_error_summary(self) -> Dict:
        """Get summary of recorded errors"""
        return {
            error_type: {
                "count": info["count"],
                "first_seen": info["first_seen"],
                "last_seen": info["last_seen"],
                "recent_contexts": info["contexts"][-5:]  # Last 5 contexts
            }
            for error_type, info in self.errors.items()
        }

# Global error tracker instance
error_tracker = ErrorTracker()
