"""Robust Error Handling and Recovery System for Volume-Weighted Indicators

Provides comprehensive error handling, recovery mechanisms, and fault tolerance
for institutional-grade trading systems operating in high-frequency environments.
"""

import logging
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union, Type
from collections import deque, defaultdict
from functools import wraps
from enum import Enum
from dataclasses import dataclass, field
import threading
import numpy as np

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"           # Minor calculation errors, use fallback
    MEDIUM = "medium"     # Significant errors, may affect accuracy
    HIGH = "high"         # Critical errors, may halt indicator
    CRITICAL = "critical" # System-level errors, requires intervention

class RecoveryStrategy(Enum):
    """Error recovery strategies"""
    IGNORE = "ignore"                 # Ignore error and continue
    FALLBACK = "fallback"             # Use fallback value
    RETRY = "retry"                   # Retry operation
    RESET = "reset"                   # Reset indicator state
    CIRCUIT_BREAKER = "circuit_breaker" # Stop processing temporarily
    ESCALATE = "escalate"             # Escalate to higher level

@dataclass
class ErrorContext:
    """Context information for error handling"""
    timestamp: datetime
    indicator_name: str
    operation: str
    error_type: str
    error_message: str
    severity: ErrorSeverity
    recovery_strategy: RecoveryStrategy
    input_data: Dict[str, Any] = field(default_factory=dict)
    stack_trace: str = ""
    retry_count: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'indicator_name': self.indicator_name,
            'operation': self.operation,
            'error_type': self.error_type,
            'error_message': self.error_message,
            'severity': self.severity.value,
            'recovery_strategy': self.recovery_strategy.value,
            'input_data': self.input_data,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries
        }

class CircuitBreaker:
    """Circuit breaker pattern for error handling"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60, half_open_max_calls: int = 3):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open
        self.half_open_calls = 0
        self._lock = threading.Lock()
        
        logger.info(f"Circuit breaker initialized (threshold={failure_threshold}, timeout={recovery_timeout}s)")
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        with self._lock:
            if self.state == "open":
                if self._should_attempt_reset():
                    self.state = "half_open"
                    self.half_open_calls = 0
                    logger.info("Circuit breaker transitioning to half-open")
                else:
                    raise Exception("Circuit breaker is open - operation blocked")
            
            if self.state == "half_open":
                if self.half_open_calls >= self.half_open_max_calls:
                    raise Exception("Circuit breaker half-open limit exceeded")
                self.half_open_calls += 1
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset"""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    def _on_success(self) -> None:
        """Handle successful operation"""
        with self._lock:
            if self.state == "half_open":
                self.state = "closed"
                self.failure_count = 0
                logger.info("Circuit breaker reset to closed state")
    
    def _on_failure(self) -> None:
        """Handle failed operation"""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state"""
        with self._lock:
            return {
                'state': self.state,
                'failure_count': self.failure_count,
                'last_failure_time': self.last_failure_time,
                'half_open_calls': self.half_open_calls
            }

class ErrorRecoveryManager:
    """Comprehensive error recovery management system"""
    
    def __init__(self, max_error_history: int = 1000):
        self.max_error_history = max_error_history
        self.error_history = deque(maxlen=max_error_history)
        self.error_counts = defaultdict(int)
        self.recovery_strategies = {}
        self.circuit_breakers = {}
        self.fallback_values = {}
        self._lock = threading.RLock()
        
        # Default recovery strategies
        self._setup_default_strategies()
        
        logger.info(f"Error Recovery Manager initialized (max_history={max_error_history})")
    
    def _setup_default_strategies(self) -> None:
        """Setup default error recovery strategies"""
        self.recovery_strategies.update({
            'ValueError': RecoveryStrategy.FALLBACK,
            'ZeroDivisionError': RecoveryStrategy.FALLBACK,
            'IndexError': RecoveryStrategy.FALLBACK,
            'TypeError': RecoveryStrategy.FALLBACK,
            'OverflowError': RecoveryStrategy.RESET,
            'MemoryError': RecoveryStrategy.CIRCUIT_BREAKER,
            'RuntimeError': RecoveryStrategy.RETRY,
            'Exception': RecoveryStrategy.ESCALATE
        })
    
    def register_fallback_value(self, indicator_name: str, operation: str, value: Any) -> None:
        """Register fallback value for specific indicator operation"""
        key = f"{indicator_name}:{operation}"
        self.fallback_values[key] = value
        logger.debug(f"Registered fallback value for {key}: {value}")
    
    def register_circuit_breaker(self, indicator_name: str, circuit_breaker: CircuitBreaker) -> None:
        """Register circuit breaker for specific indicator"""
        self.circuit_breakers[indicator_name] = circuit_breaker
        logger.debug(f"Registered circuit breaker for {indicator_name}")
    
    def handle_error(self, error_context: ErrorContext) -> Any:
        """Handle error based on context and recovery strategy"""
        with self._lock:
            # Record error
            self.error_history.append(error_context)
            self.error_counts[error_context.error_type] += 1
            
            # Determine recovery strategy
            strategy = self._determine_recovery_strategy(error_context)
            error_context.recovery_strategy = strategy
            
            # Execute recovery strategy
            return self._execute_recovery_strategy(error_context)
    
    def _determine_recovery_strategy(self, error_context: ErrorContext) -> RecoveryStrategy:
        """Determine appropriate recovery strategy"""
        # Check for custom strategy
        custom_key = f"{error_context.indicator_name}:{error_context.error_type}"
        if custom_key in self.recovery_strategies:
            return self.recovery_strategies[custom_key]
        
        # Check for error type strategy
        if error_context.error_type in self.recovery_strategies:
            return self.recovery_strategies[error_context.error_type]
        
        # Check error frequency for escalation
        recent_errors = sum(1 for ctx in list(self.error_history)[-100:] 
                          if ctx.error_type == error_context.error_type)
        
        if recent_errors > 10:
            return RecoveryStrategy.CIRCUIT_BREAKER
        elif recent_errors > 5:
            return RecoveryStrategy.RESET
        
        # Default strategy based on severity
        if error_context.severity == ErrorSeverity.CRITICAL:
            return RecoveryStrategy.CIRCUIT_BREAKER
        elif error_context.severity == ErrorSeverity.HIGH:
            return RecoveryStrategy.RESET
        elif error_context.severity == ErrorSeverity.MEDIUM:
            return RecoveryStrategy.RETRY
        else:
            return RecoveryStrategy.FALLBACK
    
    def _execute_recovery_strategy(self, error_context: ErrorContext) -> Any:
        """Execute the determined recovery strategy"""
        strategy = error_context.recovery_strategy
        
        if strategy == RecoveryStrategy.IGNORE:
            logger.debug(f"Ignoring error in {error_context.indicator_name}: {error_context.error_message}")
            return None
        
        elif strategy == RecoveryStrategy.FALLBACK:
            return self._get_fallback_value(error_context)
        
        elif strategy == RecoveryStrategy.RETRY:
            return self._retry_operation(error_context)
        
        elif strategy == RecoveryStrategy.RESET:
            logger.warning(f"Resetting indicator {error_context.indicator_name} due to error: {error_context.error_message}")
            return None  # Indicator should handle reset
        
        elif strategy == RecoveryStrategy.CIRCUIT_BREAKER:
            self._activate_circuit_breaker(error_context)
            return None
        
        elif strategy == RecoveryStrategy.ESCALATE:
            self._escalate_error(error_context)
            return None
        
        else:
            logger.error(f"Unknown recovery strategy: {strategy}")
            return None
    
    def _get_fallback_value(self, error_context: ErrorContext) -> Any:
        """Get fallback value for the operation"""
        key = f"{error_context.indicator_name}:{error_context.operation}"
        
        if key in self.fallback_values:
            fallback = self.fallback_values[key]
            logger.debug(f"Using fallback value for {key}: {fallback}")
            return fallback
        
        # Default fallback values
        default_fallbacks = {
            'calculate': 0.0,
            'calculate_values': {},
            'generate_signal': None,
            'normalize': 0.0,
            'detect_outliers': [],
            'volume_weighted_average': 0.0
        }
        
        fallback = default_fallbacks.get(error_context.operation, None)
        logger.debug(f"Using default fallback value for {error_context.operation}: {fallback}")
        return fallback
    
    def _retry_operation(self, error_context: ErrorContext) -> Any:
        """Retry the failed operation"""
        if error_context.retry_count >= error_context.max_retries:
            logger.warning(f"Max retries exceeded for {error_context.indicator_name}:{error_context.operation}")
            return self._get_fallback_value(error_context)
        
        error_context.retry_count += 1
        logger.debug(f"Retrying operation {error_context.operation} (attempt {error_context.retry_count})")
        
        # Return None to indicate retry needed - calling code should handle
        return None
    
    def _activate_circuit_breaker(self, error_context: ErrorContext) -> None:
        """Activate circuit breaker for the indicator"""
        indicator_name = error_context.indicator_name
        
        if indicator_name not in self.circuit_breakers:
            self.circuit_breakers[indicator_name] = CircuitBreaker()
        
        circuit_breaker = self.circuit_breakers[indicator_name]
        circuit_breaker._on_failure()
        
        logger.warning(f"Circuit breaker activated for {indicator_name}")
    
    def _escalate_error(self, error_context: ErrorContext) -> None:
        """Escalate error to higher level handling"""
        logger.error(f"ESCALATED ERROR in {error_context.indicator_name}: {error_context.error_message}")
        logger.error(f"Stack trace: {error_context.stack_trace}")
        
        # Could integrate with external monitoring systems here
        # For now, just log at critical level
        logger.critical(f"Critical error requires attention: {error_context.to_dict()}")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics"""
        with self._lock:
            total_errors = len(self.error_history)
            
            if total_errors == 0:
                return {'total_errors': 0}
            
            # Error type distribution
            error_types = defaultdict(int)
            severity_counts = defaultdict(int)
            recovery_strategy_counts = defaultdict(int)
            
            for error_ctx in self.error_history:
                error_types[error_ctx.error_type] += 1
                severity_counts[error_ctx.severity.value] += 1
                recovery_strategy_counts[error_ctx.recovery_strategy.value] += 1
            
            # Recent error rate (last hour)
            recent_time = datetime.now() - timedelta(hours=1)
            recent_errors = sum(1 for ctx in self.error_history if ctx.timestamp > recent_time)
            
            return {
                'total_errors': total_errors,
                'recent_errors_1h': recent_errors,
                'error_rate_per_hour': recent_errors,
                'error_types': dict(error_types),
                'severity_distribution': dict(severity_counts),
                'recovery_strategy_distribution': dict(recovery_strategy_counts),
                'circuit_breaker_states': {name: cb.get_state() for name, cb in self.circuit_breakers.items()}
            }
    
    def reset_error_history(self) -> None:
        """Reset error history and statistics"""
        with self._lock:
            self.error_history.clear()
            self.error_counts.clear()
            logger.info("Error history reset")

# Global error recovery manager
_global_error_manager = None

def get_error_manager() -> ErrorRecoveryManager:
    """Get global error recovery manager"""
    global _global_error_manager
    if _global_error_manager is None:
        _global_error_manager = ErrorRecoveryManager()
    return _global_error_manager

def robust_indicator_operation(operation_name: str, indicator_name: str = None, 
                             severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                             max_retries: int = 3):
    """Decorator for robust indicator operations with comprehensive error handling"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            error_manager = get_error_manager()
            func_indicator_name = indicator_name or getattr(self, 'name', self.__class__.__name__)
            
            # Check circuit breaker
            if func_indicator_name in error_manager.circuit_breakers:
                circuit_breaker = error_manager.circuit_breakers[func_indicator_name]
                if circuit_breaker.state == "open":
                    logger.warning(f"Circuit breaker open for {func_indicator_name} - operation blocked")
                    return error_manager._get_fallback_value(ErrorContext(
                        timestamp=datetime.now(),
                        indicator_name=func_indicator_name,
                        operation=operation_name,
                        error_type="CircuitBreakerOpen",
                        error_message="Circuit breaker is open",
                        severity=severity
                    ))
            
            retry_count = 0
            while retry_count <= max_retries:
                try:
                    return func(self, *args, **kwargs)
                
                except Exception as e:
                    error_context = ErrorContext(
                        timestamp=datetime.now(),
                        indicator_name=func_indicator_name,
                        operation=operation_name,
                        error_type=type(e).__name__,
                        error_message=str(e),
                        severity=severity,
                        recovery_strategy=RecoveryStrategy.RETRY,
                        input_data={'args': str(args), 'kwargs': str(kwargs)},
                        stack_trace=traceback.format_exc(),
                        retry_count=retry_count,
                        max_retries=max_retries
                    )
                    
                    # Handle error
                    recovery_result = error_manager.handle_error(error_context)
                    
                    # Check if we should retry
                    if (error_context.recovery_strategy == RecoveryStrategy.RETRY and 
                        retry_count < max_retries):
                        retry_count += 1
                        time.sleep(0.001 * retry_count)  # Exponential backoff
                        continue
                    
                    # Return recovery result or re-raise
                    if recovery_result is not None:
                        return recovery_result
                    elif error_context.recovery_strategy == RecoveryStrategy.ESCALATE:
                        raise
                    else:
                        return None
            
            # Max retries exceeded
            logger.error(f"Max retries exceeded for {func_indicator_name}.{operation_name}")
            return None
        
        return wrapper
    return decorator

def validate_input_data(price: float = None, volume: float = None, 
                       timestamp: datetime = None, strict: bool = False) -> bool:
    """Validate input data for indicator calculations"""
    errors = []
    
    if price is not None:
        if not isinstance(price, (int, float)):
            errors.append(f"Price must be numeric, got {type(price)}")
        elif price <= 0:
            errors.append(f"Price must be positive, got {price}")
        elif np.isnan(price) or np.isinf(price):
            errors.append(f"Price must be finite, got {price}")
    
    if volume is not None:
        if not isinstance(volume, (int, float)):
            errors.append(f"Volume must be numeric, got {type(volume)}")
        elif volume < 0:
            errors.append(f"Volume must be non-negative, got {volume}")
        elif np.isnan(volume) or np.isinf(volume):
            errors.append(f"Volume must be finite, got {volume}")
    
    if timestamp is not None:
        if not isinstance(timestamp, datetime):
            errors.append(f"Timestamp must be datetime, got {type(timestamp)}")
    
    if errors:
        error_msg = "; ".join(errors)
        if strict:
            raise ValueError(f"Input validation failed: {error_msg}")
        else:
            logger.warning(f"Input validation warnings: {error_msg}")
            return False
    
    return True

def sanitize_numeric_value(value: Any, default: float = 0.0, 
                          min_value: float = None, max_value: float = None) -> float:
    """Sanitize numeric value for safe calculation"""
    try:
        if value is None:
            return default
        
        if isinstance(value, (int, float)):
            if np.isnan(value) or np.isinf(value):
                return default
            
            # Apply bounds if specified
            if min_value is not None and value < min_value:
                return min_value
            if max_value is not None and value > max_value:
                return max_value
            
            return float(value)
        
        # Try to convert to float
        numeric_value = float(value)
        if np.isnan(numeric_value) or np.isinf(numeric_value):
            return default
        
        return numeric_value
        
    except (ValueError, TypeError, OverflowError):
        logger.warning(f"Could not sanitize value {value}, using default {default}")
        return default

# Initialize global error manager
get_error_manager()