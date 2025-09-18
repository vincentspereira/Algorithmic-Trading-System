import asyncio
import logging
import traceback
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable, Union, Type
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import json

# Configure logging
logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ErrorCategory(Enum):
    """Error categories for classification."""
    CONNECTION = "CONNECTION"
    AUTHENTICATION = "AUTHENTICATION"
    AUTHORIZATION = "AUTHORIZATION"
    TRADING = "TRADING"
    DATA = "DATA"
    SYSTEM = "SYSTEM"
    NETWORK = "NETWORK"
    VALIDATION = "VALIDATION"
    RATE_LIMIT = "RATE_LIMIT"
    MARKET = "MARKET"

class RecoveryAction(Enum):
    """Recovery actions for error handling."""
    RETRY = "RETRY"
    RECONNECT = "RECONNECT"
    FALLBACK = "FALLBACK"
    ABORT = "ABORT"
    IGNORE = "IGNORE"
    ESCALATE = "ESCALATE"
    CIRCUIT_BREAK = "CIRCUIT_BREAK"

@dataclass
class ErrorContext:
    """Context information for error handling."""
    operation: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    additional_info: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ErrorRecord:
    """Comprehensive error record for tracking and analysis."""
    error_id: str
    error_type: str
    error_message: str
    severity: ErrorSeverity
    category: ErrorCategory
    context: ErrorContext
    timestamp: datetime
    stack_trace: Optional[str] = None
    recovery_action: Optional[RecoveryAction] = None
    recovery_attempts: int = 0
    resolved: bool = False
    resolution_time: Optional[datetime] = None
    impact_assessment: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error record to dictionary."""
        return {
            'error_id': self.error_id,
            'error_type': self.error_type,
            'error_message': self.error_message,
            'severity': self.severity.value,
            'category': self.category.value,
            'timestamp': self.timestamp.isoformat(),
            'context': {
                'operation': self.context.operation,
                'parameters': self.context.parameters,
                'user_id': self.context.user_id,
                'session_id': self.context.session_id,
                'request_id': self.context.request_id,
                'timestamp': self.context.timestamp.isoformat(),
                'additional_info': self.context.additional_info
            },
            'stack_trace': self.stack_trace,
            'recovery_action': self.recovery_action.value if self.recovery_action else None,
            'recovery_attempts': self.recovery_attempts,
            'resolved': self.resolved,
            'resolution_time': self.resolution_time.isoformat() if self.resolution_time else None,
            'impact_assessment': self.impact_assessment
        }

@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_backoff: bool = True
    jitter: bool = True
    retry_on_exceptions: List[Type[Exception]] = field(default_factory=list)
    stop_on_exceptions: List[Type[Exception]] = field(default_factory=list)

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker pattern."""
    failure_threshold: int = 5
    recovery_timeout: int = 60
    expected_exception: Type[Exception] = Exception
    name: str = "default"

class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreaker:
    """Circuit breaker implementation for fault tolerance."""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitBreakerState.CLOSED
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        async with self._lock:
            if self.state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitBreakerState.HALF_OPEN
                    logger.info(f"Circuit breaker {self.config.name} transitioning to HALF_OPEN")
                else:
                    raise Exception(f"Circuit breaker {self.config.name} is OPEN")
        
        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            await self._on_success()
            return result
        except self.config.expected_exception as e:
            await self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset."""
        if self.last_failure_time is None:
            return True
        
        time_since_failure = datetime.now(timezone.utc) - self.last_failure_time
        return time_since_failure.total_seconds() >= self.config.recovery_timeout
    
    async def _on_success(self) -> None:
        """Handle successful operation."""
        async with self._lock:
            self.failure_count = 0
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.state = CircuitBreakerState.CLOSED
                logger.info(f"Circuit breaker {self.config.name} reset to CLOSED")
    
    async def _on_failure(self) -> None:
        """Handle failed operation."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now(timezone.utc)
            
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                logger.warning(f"Circuit breaker {self.config.name} opened after {self.failure_count} failures")

class IBErrorHandler:
    """
    Comprehensive error handling system for Interactive Brokers integration.
    
    This class provides:
    - Centralized error classification and logging
    - Intelligent retry mechanisms with exponential backoff
    - Circuit breaker pattern for fault tolerance
    - Error recovery strategies
    - Comprehensive error analytics and reporting
    - Real-time error monitoring and alerting
    """
    
    def __init__(
        self,
        max_error_history: int = 10000,
        alert_callback: Optional[Callable] = None,
        metrics_callback: Optional[Callable] = None
    ):
        """
        Initialize the error handler.
        
        Parameters
        ----------
        max_error_history : int
            Maximum number of error records to keep in memory
        alert_callback : Callable, optional
            Callback function for error alerts
        metrics_callback : Callable, optional
            Callback function for error metrics
        """
        self._max_error_history = max_error_history
        self._alert_callback = alert_callback
        self._metrics_callback = metrics_callback
        
        # Error tracking
        self._error_history: deque = deque(maxlen=max_error_history)
        self._error_counts: Dict[str, int] = defaultdict(int)
        self._error_patterns: Dict[str, List[datetime]] = defaultdict(list)
        
        # Circuit breakers
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # Error classification rules
        self._error_rules = self._initialize_error_rules()
        
        # Recovery strategies
        self._recovery_strategies = self._initialize_recovery_strategies()
        
        logger.info("IB Error Handler initialized")
    
    def _initialize_error_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize error classification rules."""
        return {
            # Connection errors
            'ConnectionError': {
                'category': ErrorCategory.CONNECTION,
                'severity': ErrorSeverity.HIGH,
                'recovery_action': RecoveryAction.RECONNECT
            },
            'TimeoutError': {
                'category': ErrorCategory.NETWORK,
                'severity': ErrorSeverity.MEDIUM,
                'recovery_action': RecoveryAction.RETRY
            },
            'socket.error': {
                'category': ErrorCategory.NETWORK,
                'severity': ErrorSeverity.HIGH,
                'recovery_action': RecoveryAction.RECONNECT
            },
            
            # IB specific errors
            'IBError_502': {
                'category': ErrorCategory.CONNECTION,
                'severity': ErrorSeverity.CRITICAL,
                'recovery_action': RecoveryAction.RECONNECT,
                'description': 'Couldn\'t connect to TWS'
            },
            'IBError_503': {
                'category': ErrorCategory.CONNECTION,
                'severity': ErrorSeverity.HIGH,
                'recovery_action': RecoveryAction.RECONNECT,
                'description': 'The TWS is out of date'
            },
            'IBError_504': {
                'category': ErrorCategory.CONNECTION,
                'severity': ErrorSeverity.HIGH,
                'recovery_action': RecoveryAction.RECONNECT,
                'description': 'Not connected'
            },
            'IBError_200': {
                'category': ErrorCategory.TRADING,
                'severity': ErrorSeverity.MEDIUM,
                'recovery_action': RecoveryAction.ABORT,
                'description': 'No security definition found'
            },
            'IBError_201': {
                'category': ErrorCategory.TRADING,
                'severity': ErrorSeverity.MEDIUM,
                'recovery_action': RecoveryAction.ABORT,
                'description': 'Order rejected'
            },
            'IBError_202': {
                'category': ErrorCategory.TRADING,
                'severity': ErrorSeverity.MEDIUM,
                'recovery_action': RecoveryAction.ABORT,
                'description': 'Order cancelled'
            },
            'IBError_399': {
                'category': ErrorCategory.TRADING,
                'severity': ErrorSeverity.HIGH,
                'recovery_action': RecoveryAction.ABORT,
                'description': 'Order message error'
            },
            
            # Authentication errors
            'IBAuthenticationError': {
                'category': ErrorCategory.AUTHENTICATION,
                'severity': ErrorSeverity.HIGH,
                'recovery_action': RecoveryAction.ABORT
            },
            'IBAuthorizationError': {
                'category': ErrorCategory.AUTHORIZATION,
                'severity': ErrorSeverity.HIGH,
                'recovery_action': RecoveryAction.ABORT
            },
            
            # Data errors
            'IBDataError': {
                'category': ErrorCategory.DATA,
                'severity': ErrorSeverity.MEDIUM,
                'recovery_action': RecoveryAction.RETRY
            },
            
            # Rate limiting
            'RateLimitError': {
                'category': ErrorCategory.RATE_LIMIT,
                'severity': ErrorSeverity.MEDIUM,
                'recovery_action': RecoveryAction.RETRY
            },
            
            # Market errors
            'MarketClosedError': {
                'category': ErrorCategory.MARKET,
                'severity': ErrorSeverity.LOW,
                'recovery_action': RecoveryAction.IGNORE
            },
            
            # System errors
            'MemoryError': {
                'category': ErrorCategory.SYSTEM,
                'severity': ErrorSeverity.CRITICAL,
                'recovery_action': RecoveryAction.ESCALATE
            },
            'SystemError': {
                'category': ErrorCategory.SYSTEM,
                'severity': ErrorSeverity.HIGH,
                'recovery_action': RecoveryAction.ESCALATE
            }
        }
    
    def _initialize_recovery_strategies(self) -> Dict[RecoveryAction, Callable]:
        """Initialize recovery strategies."""
        return {
            RecoveryAction.RETRY: self._retry_strategy,
            RecoveryAction.RECONNECT: self._reconnect_strategy,
            RecoveryAction.FALLBACK: self._fallback_strategy,
            RecoveryAction.ABORT: self._abort_strategy,
            RecoveryAction.IGNORE: self._ignore_strategy,
            RecoveryAction.ESCALATE: self._escalate_strategy,
            RecoveryAction.CIRCUIT_BREAK: self._circuit_break_strategy
        }
    
    def _generate_error_id(self) -> str:
        """Generate unique error ID."""
        import uuid
        return str(uuid.uuid4())
    
    def _classify_error(self, error: Exception) -> Dict[str, Any]:
        """Classify error based on type and message."""
        error_type = type(error).__name__
        error_message = str(error)
        
        # Check for specific IB error codes
        if 'IBError' in error_message or 'Error' in error_message:
            for pattern, rule in self._error_rules.items():
                if pattern in error_message or pattern in error_type:
                    return rule
        
        # Check for general error types
        if error_type in self._error_rules:
            return self._error_rules[error_type]
        
        # Default classification
        return {
            'category': ErrorCategory.SYSTEM,
            'severity': ErrorSeverity.MEDIUM,
            'recovery_action': RecoveryAction.RETRY
        }
    
    async def handle_error(
        self,
        error: Exception,
        context: ErrorContext,
        auto_recover: bool = True
    ) -> ErrorRecord:
        """
        Handle error with comprehensive logging and recovery.
        
        Parameters
        ----------
        error : Exception
            The error to handle
        context : ErrorContext
            Context information for the error
        auto_recover : bool
            Whether to attempt automatic recovery
        
        Returns
        -------
        ErrorRecord
            The error record created
        """
        try:
            # Generate error ID
            error_id = self._generate_error_id()
            
            # Classify error
            classification = self._classify_error(error)
            
            # Create error record
            error_record = ErrorRecord(
                error_id=error_id,
                error_type=type(error).__name__,
                error_message=str(error),
                severity=classification['severity'],
                category=classification['category'],
                context=context,
                timestamp=datetime.now(timezone.utc),
                stack_trace=traceback.format_exc(),
                recovery_action=classification['recovery_action']
            )
            
            # Add to error history
            self._error_history.append(error_record)
            
            # Update error counts and patterns
            self._update_error_statistics(error_record)
            
            # Log error
            self._log_error(error_record)
            
            # Send alert if necessary
            await self._send_alert_if_needed(error_record)
            
            # Update metrics
            await self._update_metrics(error_record)
            
            # Attempt recovery if enabled
            if auto_recover and error_record.recovery_action:
                await self._attempt_recovery(error_record)
            
            return error_record
            
        except Exception as handler_error:
            logger.error(f"Error in error handler: {str(handler_error)}")
            # Create minimal error record
            return ErrorRecord(
                error_id=self._generate_error_id(),
                error_type=type(error).__name__,
                error_message=str(error),
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.SYSTEM,
                context=context,
                timestamp=datetime.now(timezone.utc)
            )
    
    def _update_error_statistics(self, error_record: ErrorRecord) -> None:
        """Update error statistics for pattern analysis."""
        error_key = f"{error_record.category.value}_{error_record.error_type}"
        self._error_counts[error_key] += 1
        
        # Track error patterns (time-based)
        pattern_key = f"{error_record.context.operation}_{error_record.error_type}"
        self._error_patterns[pattern_key].append(error_record.timestamp)
        
        # Keep only recent patterns (last 24 hours)
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
        self._error_patterns[pattern_key] = [
            timestamp for timestamp in self._error_patterns[pattern_key]
            if timestamp > cutoff_time
        ]
    
    def _log_error(self, error_record: ErrorRecord) -> None:
        """Log error with appropriate level based on severity."""
        log_message = (
            f"Error {error_record.error_id}: {error_record.error_message} "
            f"[{error_record.category.value}/{error_record.severity.value}] "
            f"in operation '{error_record.context.operation}'"
        )
        
        if error_record.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message)
        elif error_record.severity == ErrorSeverity.HIGH:
            logger.error(log_message)
        elif error_record.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    async def _send_alert_if_needed(self, error_record: ErrorRecord) -> None:
        """Send alert for critical errors or error patterns."""
        try:
            should_alert = False
            alert_reason = ""
            
            # Alert on critical errors
            if error_record.severity == ErrorSeverity.CRITICAL:
                should_alert = True
                alert_reason = "Critical error occurred"
            
            # Alert on error patterns (multiple errors in short time)
            pattern_key = f"{error_record.context.operation}_{error_record.error_type}"
            recent_errors = self._error_patterns.get(pattern_key, [])
            
            if len(recent_errors) >= 5:  # 5 errors in pattern
                recent_window = datetime.now(timezone.utc) - timedelta(minutes=10)
                recent_count = sum(1 for ts in recent_errors if ts > recent_window)
                
                if recent_count >= 3:  # 3 errors in 10 minutes
                    should_alert = True
                    alert_reason = f"Error pattern detected: {recent_count} errors in 10 minutes"
            
            if should_alert and self._alert_callback:
                await self._alert_callback(error_record, alert_reason)
                
        except Exception as e:
            logger.error(f"Error sending alert: {str(e)}")
    
    async def _update_metrics(self, error_record: ErrorRecord) -> None:
        """Update error metrics."""
        try:
            if self._metrics_callback:
                metrics_data = {
                    'error_count': 1,
                    'error_type': error_record.error_type,
                    'error_category': error_record.category.value,
                    'error_severity': error_record.severity.value,
                    'operation': error_record.context.operation,
                    'timestamp': error_record.timestamp.isoformat()
                }
                await self._metrics_callback(metrics_data)
                
        except Exception as e:
            logger.error(f"Error updating metrics: {str(e)}")
    
    async def _attempt_recovery(self, error_record: ErrorRecord) -> None:
        """Attempt error recovery based on recovery action."""
        try:
            if error_record.recovery_action in self._recovery_strategies:
                recovery_func = self._recovery_strategies[error_record.recovery_action]
                await recovery_func(error_record)
                
        except Exception as e:
            logger.error(f"Error during recovery attempt: {str(e)}")
            error_record.recovery_attempts += 1
    
    # Recovery strategy implementations
    async def _retry_strategy(self, error_record: ErrorRecord) -> None:
        """Implement retry strategy."""
        logger.info(f"Retry strategy triggered for error {error_record.error_id}")
        # This would typically involve re-queuing the failed operation
        # Implementation depends on the specific operation context
    
    async def _reconnect_strategy(self, error_record: ErrorRecord) -> None:
        """Implement reconnection strategy."""
        logger.info(f"Reconnect strategy triggered for error {error_record.error_id}")
        # This would typically involve reconnecting to IB
        # Implementation depends on the connection manager
    
    async def _fallback_strategy(self, error_record: ErrorRecord) -> None:
        """Implement fallback strategy."""
        logger.info(f"Fallback strategy triggered for error {error_record.error_id}")
        # This would typically involve using alternative data sources or methods
    
    async def _abort_strategy(self, error_record: ErrorRecord) -> None:
        """Implement abort strategy."""
        logger.info(f"Abort strategy triggered for error {error_record.error_id}")
        # This would typically involve cancelling the operation
    
    async def _ignore_strategy(self, error_record: ErrorRecord) -> None:
        """Implement ignore strategy."""
        logger.info(f"Ignore strategy triggered for error {error_record.error_id}")
        # This would typically involve logging and continuing
    
    async def _escalate_strategy(self, error_record: ErrorRecord) -> None:
        """Implement escalation strategy."""
        logger.info(f"Escalate strategy triggered for error {error_record.error_id}")
        # This would typically involve notifying administrators
    
    async def _circuit_break_strategy(self, error_record: ErrorRecord) -> None:
        """Implement circuit breaker strategy."""
        logger.info(f"Circuit break strategy triggered for error {error_record.error_id}")
        # This would typically involve opening a circuit breaker
    
    def create_circuit_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception
    ) -> CircuitBreaker:
        """Create and register a circuit breaker."""
        config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
            name=name
        )
        
        circuit_breaker = CircuitBreaker(config)
        self._circuit_breakers[name] = circuit_breaker
        
        logger.info(f"Circuit breaker '{name}' created")
        return circuit_breaker
    
    def get_circuit_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self._circuit_breakers.get(name)
    
    async def retry_with_backoff(
        self,
        func: Callable,
        retry_config: RetryConfig,
        context: ErrorContext,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with retry logic and exponential backoff.
        
        Parameters
        ----------
        func : Callable
            Function to execute
        retry_config : RetryConfig
            Retry configuration
        context : ErrorContext
            Error context for logging
        *args, **kwargs
            Function arguments
        
        Returns
        -------
        Any
            Function result if successful
        """
        last_exception = None
        
        for attempt in range(retry_config.max_attempts):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
                    
            except Exception as e:
                last_exception = e
                
                # Check if we should stop retrying
                if any(isinstance(e, exc_type) for exc_type in retry_config.stop_on_exceptions):
                    logger.info(f"Stopping retry due to stop exception: {type(e).__name__}")
                    break
                
                # Check if we should retry
                if retry_config.retry_on_exceptions and not any(
                    isinstance(e, exc_type) for exc_type in retry_config.retry_on_exceptions
                ):
                    logger.info(f"Not retrying due to exception type: {type(e).__name__}")
                    break
                
                # Calculate delay
                if attempt < retry_config.max_attempts - 1:
                    delay = retry_config.base_delay
                    
                    if retry_config.exponential_backoff:
                        delay *= (2 ** attempt)
                    
                    delay = min(delay, retry_config.max_delay)
                    
                    if retry_config.jitter:
                        import random
                        delay *= (0.5 + random.random() * 0.5)
                    
                    logger.info(
                        f"Retry attempt {attempt + 1}/{retry_config.max_attempts} "
                        f"failed: {str(e)}. Retrying in {delay:.2f} seconds..."
                    )
                    
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"All {retry_config.max_attempts} retry attempts failed. "
                        f"Last error: {str(e)}"
                    )
        
        # Handle final failure
        if last_exception:
            await self.handle_error(last_exception, context)
            raise last_exception
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics."""
        total_errors = len(self._error_history)
        
        if total_errors == 0:
            return {'total_errors': 0}
        
        # Calculate statistics
        severity_counts = defaultdict(int)
        category_counts = defaultdict(int)
        recent_errors = 0
        
        recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        
        for error_record in self._error_history:
            severity_counts[error_record.severity.value] += 1
            category_counts[error_record.category.value] += 1
            
            if error_record.timestamp > recent_cutoff:
                recent_errors += 1
        
        return {
            'total_errors': total_errors,
            'recent_errors_1h': recent_errors,
            'severity_breakdown': dict(severity_counts),
            'category_breakdown': dict(category_counts),
            'error_counts': dict(self._error_counts),
            'active_patterns': len(self._error_patterns),
            'circuit_breakers': {
                name: {
                    'state': cb.state.value,
                    'failure_count': cb.failure_count,
                    'last_failure': cb.last_failure_time.isoformat() if cb.last_failure_time else None
                }
                for name, cb in self._circuit_breakers.items()
            }
        }
    
    def get_recent_errors(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent error records."""
        recent_errors = list(self._error_history)[-limit:]
        return [error.to_dict() for error in recent_errors]
    
    def clear_error_history(self) -> None:
        """Clear error history (use with caution)."""
        self._error_history.clear()
        self._error_counts.clear()
        self._error_patterns.clear()
        logger.info("Error history cleared")

# Factory function for easy instantiation
def create_error_handler(
    max_error_history: int = 10000,
    alert_callback: Optional[Callable] = None,
    metrics_callback: Optional[Callable] = None
) -> IBErrorHandler:
    """
    Factory function to create an error handler.
    
    Parameters
    ----------
    max_error_history : int
        Maximum number of error records to keep
    alert_callback : Callable, optional
        Callback for error alerts
    metrics_callback : Callable, optional
        Callback for error metrics
    
    Returns
    -------
    IBErrorHandler
        Configured error handler
    """
    return IBErrorHandler(
        max_error_history=max_error_history,
        alert_callback=alert_callback,
        metrics_callback=metrics_callback
    )