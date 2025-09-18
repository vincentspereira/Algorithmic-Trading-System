"""
Error Management System for Dependency Management.
Provides centralized error handling, logging, and recovery mechanisms.
"""

import functools
import logging
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
from prometheus_client import Counter, Histogram

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dependency_errors.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Prometheus metrics
ERROR_COUNTER = Counter(
    'dependency_errors_total',
    'Total number of errors by type and severity',
    ['error_type', 'severity']
)

ERROR_HANDLING_TIME = Histogram(
    'dependency_error_handling_seconds',
    'Time spent handling errors',
    ['error_type']
)

class ErrorSeverity(Enum):
    """Error severity levels"""
    CRITICAL = "critical"  # System cannot continue, immediate attention required
    HIGH = "high"         # System can continue but degraded, urgent attention needed
    MEDIUM = "medium"     # System working but with reduced functionality
    LOW = "low"          # Minor issue, can be addressed in regular maintenance

class ErrorCategory(Enum):
    """Categories of errors"""
    NETWORK = "network"
    DATABASE = "database"
    API = "api"
    SECURITY = "security"
    VALIDATION = "validation"
    PERFORMANCE = "performance"
    CONFIGURATION = "configuration"
    DEPENDENCY = "dependency"
    RESOURCE = "resource"
    UNKNOWN = "unknown"

@dataclass
class ErrorContext:
    """Context information for an error"""
    timestamp: datetime
    error_type: str
    message: str
    severity: ErrorSeverity
    category: ErrorCategory
    stack_trace: str
    component: str
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None

class ErrorRecoveryStrategy(Enum):
    """Strategies for error recovery"""
    RETRY = "retry"           # Retry the operation
    FALLBACK = "fallback"     # Use fallback/cached data
    IGNORE = "ignore"         # Continue without the operation
    TERMINATE = "terminate"   # Stop the process
    NOTIFY = "notify"         # Notify administrators only

class DependencyError(Exception):
    """Base exception class for dependency management errors"""
    def __init__(
        self,
        message: str,
        severity: ErrorSeverity,
        category: ErrorCategory,
        recovery_strategy: ErrorRecoveryStrategy,
        correlation_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message)
        self.severity = severity
        self.category = category
        self.recovery_strategy = recovery_strategy
        self.correlation_id = correlation_id
        self.timestamp = datetime.now(timezone.utc)
        self.additional_data = kwargs

T = TypeVar('T')

class ErrorManager:
    """Manages error handling, logging, and recovery"""
    
    def __init__(self):
        self.error_handlers: Dict[ErrorCategory, List[Callable]] = {
            category: [] for category in ErrorCategory
        }
        
    def handle_error(self, error: Union[DependencyError, Exception]) -> None:
        """Handle an error with appropriate logging and recovery"""
        start_time = datetime.now(timezone.utc)
        
        try:
            if isinstance(error, DependencyError):
                context = ErrorContext(
                    timestamp=error.timestamp,
                    error_type=error.__class__.__name__,
                    message=str(error),
                    severity=error.severity,
                    category=error.category,
                    stack_trace=traceback.format_exc(),
                    component="dependency_management",
                    correlation_id=error.correlation_id,
                    additional_data=error.additional_data
                )
            else:
                context = ErrorContext(
                    timestamp=datetime.now(timezone.utc),
                    error_type=error.__class__.__name__,
                    message=str(error),
                    severity=ErrorSeverity.HIGH,
                    category=ErrorCategory.UNKNOWN,
                    stack_trace=traceback.format_exc(),
                    component="dependency_management"
                )
            
            # Update metrics
            ERROR_COUNTER.labels(
                error_type=context.error_type,
                severity=context.severity.value
            ).inc()
            
            # Log error
            self._log_error(context)
            
            # Execute error handlers
            self._execute_handlers(context)
            
        finally:
            # Record handling time
            handling_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            ERROR_HANDLING_TIME.labels(
                error_type=context.error_type
            ).observe(handling_time)
    
    def register_handler(
        self,
        category: ErrorCategory,
        handler: Callable[[ErrorContext], None]
    ) -> None:
        """Register an error handler for a specific category"""
        self.error_handlers[category].append(handler)
    
    def _log_error(self, context: ErrorContext) -> None:
        """Log error with appropriate severity"""
        log_message = (
            f"Error: {context.error_type}\n"
            f"Message: {context.message}\n"
            f"Severity: {context.severity.value}\n"
            f"Category: {context.category.value}\n"
            f"Component: {context.component}\n"
            f"Correlation ID: {context.correlation_id}\n"
            f"Timestamp: {context.timestamp}\n"
            f"Stack Trace:\n{context.stack_trace}\n"
            f"Additional Data: {context.additional_data}"
        )
        
        if context.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message)
        elif context.severity == ErrorSeverity.HIGH:
            logger.error(log_message)
        elif context.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    def _execute_handlers(self, context: ErrorContext) -> None:
        """Execute all registered handlers for the error category"""
        for handler in self.error_handlers[context.category]:
            try:
                handler(context)
            except Exception as e:
                logger.error(f"Error in error handler: {str(e)}")

def with_error_handling(
    severity: ErrorSeverity,
    category: ErrorCategory,
    recovery_strategy: ErrorRecoveryStrategy
):
    """Decorator for automatic error handling"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error = DependencyError(
                    message=str(e),
                    severity=severity,
                    category=category,
                    recovery_strategy=recovery_strategy,
                    original_error=e
                )
                ErrorManager().handle_error(error)
                
                if recovery_strategy == ErrorRecoveryStrategy.RETRY:
                    # Implement retry logic
                    return func(*args, **kwargs)
                elif recovery_strategy == ErrorRecoveryStrategy.TERMINATE:
                    raise error
                elif recovery_strategy == ErrorRecoveryStrategy.FALLBACK:
                    # Return a safe default value based on return type annotation
                    return None
                else:
                    return None
        return wrapper
    return decorator

# Create global error manager instance
error_manager = ErrorManager()
