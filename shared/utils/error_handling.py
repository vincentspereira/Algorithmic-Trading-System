"""
Shared error handling utilities for the Algorithmic Trading System.

This module consolidates all error handling and retry mechanisms that were
previously duplicated across multiple components. Provides consistent error
handling, retry decorators, and exception management.
"""

import asyncio
import functools
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Type, Union, Tuple
from enum import Enum
import random
import sys
import traceback
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification"""
    NETWORK = "network"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RATE_LIMIT = "rate_limit"
    DATA = "data"
    CONFIGURATION = "configuration"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_API = "external_api"
    DATABASE = "database"
    SYSTEM = "system"


class RetryStrategy(Enum):
    """Retry strategies"""
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    RANDOM = "random"


class TradingSystemError(Exception):
    """Base exception for trading system errors"""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.category = category
        self.context = context or {}
        self.timestamp = datetime.utcnow()


class NetworkError(TradingSystemError):
    """Network-related errors"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, 
            category=ErrorCategory.NETWORK,
            **kwargs
        )


class ValidationError(TradingSystemError):
    """Validation errors"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, 
            category=ErrorCategory.VALIDATION,
            **kwargs
        )


class RateLimitError(TradingSystemError):
    """Rate limiting errors"""
    
    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(
            message, 
            category=ErrorCategory.RATE_LIMIT,
            **kwargs
        )
        self.retry_after = retry_after


class AuthenticationError(TradingSystemError):
    """Authentication errors"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, 
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class AuthorizationError(TradingSystemError):
    """Authorization errors"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, 
            category=ErrorCategory.AUTHORIZATION,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class DataError(TradingSystemError):
    """Data-related errors"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, 
            category=ErrorCategory.DATA,
            **kwargs
        )


class ConfigurationError(TradingSystemError):
    """Configuration errors"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, 
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class DatabaseError(TradingSystemError):
    """Database-related errors"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, 
            category=ErrorCategory.DATABASE,
            **kwargs
        )


def calculate_backoff_delay(
    attempt: int,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True
) -> float:
    """
    Calculate backoff delay for retry attempts.
    
    Args:
        attempt: Current attempt number (1-based)
        strategy: Retry strategy to use
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        jitter: Whether to add random jitter
        
    Returns:
        Delay in seconds
        
    Examples:
        >>> calculate_backoff_delay(1, RetryStrategy.EXPONENTIAL)
        1.0
        >>> calculate_backoff_delay(3, RetryStrategy.EXPONENTIAL)
        4.0
    """
    if strategy == RetryStrategy.FIXED:
        delay = base_delay
    elif strategy == RetryStrategy.EXPONENTIAL:
        delay = base_delay * (2 ** (attempt - 1))
    elif strategy == RetryStrategy.LINEAR:
        delay = base_delay * attempt
    elif strategy == RetryStrategy.RANDOM:
        delay = random.uniform(base_delay, max_delay)
    else:
        delay = base_delay
    
    # Apply maximum delay
    delay = min(delay, max_delay)
    
    # Add jitter to prevent thundering herd
    if jitter and strategy != RetryStrategy.RANDOM:
        jitter_amount = delay * 0.1  # 10% jitter
        delay += random.uniform(-jitter_amount, jitter_amount)
    
    return max(0, delay)


def retry(
    max_attempts: int = 3,
    backoff_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retry_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    stop_exceptions: Tuple[Type[Exception], ...] = (),
    on_retry: Optional[Callable[[Exception, int], None]] = None
) -> Callable:
    """
    Retry decorator with configurable backoff strategies.
    
    Args:
        max_attempts: Maximum number of retry attempts
        backoff_strategy: Strategy for calculating delays
        base_delay: Base delay between retries
        max_delay: Maximum delay between retries
        retry_exceptions: Exceptions that should trigger retries
        stop_exceptions: Exceptions that should stop retries immediately
        on_retry: Callback function called on each retry
        
    Returns:
        Decorated function
        
    Examples:
        @retry(max_attempts=3, backoff_strategy=RetryStrategy.EXPONENTIAL)
        def risky_operation():
            # Operation that might fail
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except stop_exceptions as e:
                    logger.error(f"Stopping retries due to: {e}")
                    raise
                except retry_exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(f"Max attempts ({max_attempts}) reached for {func.__name__}")
                        break
                    
                    delay = calculate_backoff_delay(
                        attempt, 
                        backoff_strategy, 
                        base_delay, 
                        max_delay
                    )
                    
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f}s"
                    )
                    
                    if on_retry:
                        on_retry(e, attempt)
                    
                    await asyncio.sleep(delay)
            
            raise last_exception
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except stop_exceptions as e:
                    logger.error(f"Stopping retries due to: {e}")
                    raise
                except retry_exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(f"Max attempts ({max_attempts}) reached for {func.__name__}")
                        break
                    
                    delay = calculate_backoff_delay(
                        attempt, 
                        backoff_strategy, 
                        base_delay, 
                        max_delay
                    )
                    
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f}s"
                    )
                    
                    if on_retry:
                        on_retry(e, attempt)
                    
                    time.sleep(delay)
            
            raise last_exception
        
        # Return appropriate wrapper based on function type
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for fault tolerance.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                else:
                    raise TradingSystemError("Circuit breaker is OPEN")
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise
        
        return wrapper
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        return (
            self.last_failure_time and
            time.time() - self.last_failure_time >= self.timeout
        )
    
    def _on_success(self):
        """Handle successful operation"""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        """Handle failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


class ErrorContext:
    """Context information for error handling"""
    
    def __init__(
        self,
        operation: str,
        component: str,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        self.operation = operation
        self.component = component
        self.user_id = user_id
        self.request_id = request_id
        self.additional_data = additional_data or {}
        self.timestamp = datetime.utcnow()


def handle_error(
    error: Exception,
    context: Optional[ErrorContext] = None,
    notify: bool = False,
    log_level: str = "ERROR"
) -> None:
    """
    Centralized error handling function.
    
    Args:
        error: Exception to handle
        context: Error context information
        notify: Whether to send notifications
        log_level: Logging level to use
        
    Examples:
        >>> try:
        ...     risky_operation()
        ... except Exception as e:
        ...     handle_error(e, ErrorContext("trading", "order_service"))
    """
    # Extract error information
    error_info = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Add context information
    if context:
        error_info.update({
            "operation": context.operation,
            "component": context.component,
            "user_id": context.user_id,
            "request_id": context.request_id,
            "additional_data": context.additional_data
        })
    
    # Add stack trace for debugging
    error_info["stack_trace"] = traceback.format_exc()
    
    # Log the error
    log_func = getattr(logger, log_level.lower(), logger.error)
    log_func(f"Error in {context.component if context else 'unknown'}: {error}", extra=error_info)
    
    # Handle specific error types
    if isinstance(error, TradingSystemError):
        _handle_trading_system_error(error, context)
    
    # Send notifications if required
    if notify:
        _send_error_notification(error, error_info)


def _handle_trading_system_error(error: TradingSystemError, context: Optional[ErrorContext]) -> None:
    """Handle trading system specific errors"""
    if error.severity == ErrorSeverity.CRITICAL:
        logger.critical(f"CRITICAL ERROR: {error.message}", extra={"error_context": error.context})
        # TODO: Implement critical error alerting
    
    if error.category == ErrorCategory.AUTHENTICATION:
        # TODO: Implement authentication error handling
        pass
    elif error.category == ErrorCategory.RATE_LIMIT:
        # TODO: Implement rate limit handling
        pass


def _send_error_notification(error: Exception, error_info: Dict[str, Any]) -> None:
    """Send error notifications to appropriate channels"""
    # TODO: Implement notification sending (email, Slack, etc.)
    logger.info("Error notification would be sent", extra=error_info)


def safe_execute(
    func: Callable,
    default_return: Any = None,
    log_errors: bool = True,
    context: Optional[ErrorContext] = None
) -> Any:
    """
    Safely execute a function and return default value on error.
    
    Args:
        func: Function to execute
        default_return: Default value to return on error
        log_errors: Whether to log errors
        context: Error context
        
    Returns:
        Function result or default value
        
    Examples:
        >>> result = safe_execute(lambda: 1/0, default_return=0)
        >>> result
        0
    """
    try:
        return func()
    except Exception as e:
        if log_errors:
            handle_error(e, context)
        return default_return


def create_error_response(
    error: Exception,
    request_id: Optional[str] = None,
    include_details: bool = False
) -> Dict[str, Any]:
    """
    Create standardized error response.
    
    Args:
        error: Exception to create response for
        request_id: Request ID for tracking
        include_details: Whether to include error details
        
    Returns:
        Error response dictionary
        
    Examples:
        >>> response = create_error_response(ValidationError("Invalid input"))
        >>> "error" in response
        True
    """
    response = {
        "error": {
            "type": type(error).__name__,
            "message": str(error),
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    
    if request_id:
        response["request_id"] = request_id
    
    if isinstance(error, TradingSystemError):
        response["error"]["code"] = error.error_code
        response["error"]["severity"] = error.severity.value
        response["error"]["category"] = error.category.value
        
        if include_details:
            response["error"]["context"] = error.context
    
    if isinstance(error, RateLimitError) and error.retry_after:
        response["error"]["retry_after"] = error.retry_after
    
    return response


class ErrorCollector:
    """Collect and aggregate errors for batch processing"""
    
    def __init__(self, max_errors: int = 100):
        self.max_errors = max_errors
        self.errors: List[Dict[str, Any]] = []
        self.error_counts: Dict[str, int] = {}
    
    def add_error(self, error: Exception, context: Optional[ErrorContext] = None) -> None:
        """Add error to collection"""
        error_type = type(error).__name__
        
        # Track error frequency
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Add to collection if under limit
        if len(self.errors) < self.max_errors:
            error_data = {
                "type": error_type,
                "message": str(error),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if context:
                error_data["context"] = {
                    "operation": context.operation,
                    "component": context.component,
                    "user_id": context.user_id,
                    "request_id": context.request_id
                }
            
            self.errors.append(error_data)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get error summary"""
        return {
            "total_errors": len(self.errors),
            "error_counts": self.error_counts,
            "most_common": max(self.error_counts.items(), key=lambda x: x[1]) if self.error_counts else None
        }
    
    def clear(self) -> None:
        """Clear collected errors"""
        self.errors.clear()
        self.error_counts.clear()