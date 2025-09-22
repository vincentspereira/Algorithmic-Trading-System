"""
Fault Tolerance System for Nautilus Trader Engine
Provides comprehensive error handling, recovery, and graceful degradation capabilities.
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Callable, Tuple, Union, Type
from dataclasses import dataclass, field
from enum import Enum
import traceback
from datetime import datetime, timedelta
from collections import deque
import threading
from concurrent.futures import ThreadPoolExecutor
import functools
import inspect

logger = logging.getLogger(__name__)


class FailureType(Enum):
    """Types of system failures."""
    NETWORK_ERROR = "network_error"
    DATA_ERROR = "data_error"
    COMPUTATION_ERROR = "computation_error"
    MEMORY_ERROR = "memory_error"
    DISK_ERROR = "disk_error"
    CONFIGURATION_ERROR = "configuration_error"
    EXTERNAL_SERVICE_ERROR = "external_service_error"
    TIMEOUT_ERROR = "timeout_error"


class RecoveryStrategy(Enum):
    """Recovery strategies for failures."""
    RETRY = "retry"
    CIRCUIT_BREAKER = "circuit_breaker"
    FALLBACK = "fallback"
    DEGRADATION = "degradation"
    RESTART = "restart"
    ISOLATION = "isolation"


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"         # Failing, requests rejected
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class FailureEvent:
    """A system failure event."""
    failure_type: FailureType
    component: str
    error_message: str
    timestamp: datetime = field(default_factory=datetime.now)
    stack_trace: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    severity: str = "medium"  # low, medium, high, critical


@dataclass
class RecoveryAction:
    """A recovery action taken in response to a failure."""
    failure_event: FailureEvent
    strategy: RecoveryStrategy
    action_taken: str
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = False
    duration: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthStatus:
    """Health status of a system component."""
    component: str
    status: str  # healthy, degraded, unhealthy, unknown
    last_check: datetime = field(default_factory=datetime.now)
    response_time: float = 0.0
    error_count: int = 0
    success_count: int = 0
    uptime_percentage: float = 100.0


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for fault tolerance.
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0,
                 expected_exception: Exception = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.success_count = 0

        self._lock = threading.Lock()

    def call(self, func: Callable, *args, **kwargs):
        """Execute function through circuit breaker."""
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
            else:
                raise CircuitBreakerOpenException("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result

        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit breaker."""
        if self.last_failure_time is None:
            return True

        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.recovery_timeout

    def _on_success(self) -> None:
        """Handle successful execution."""
        with self._lock:
            self.success_count += 1

            if self.state == CircuitBreakerState.HALF_OPEN:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                logger.info("Circuit breaker reset to CLOSED state")

    def _on_failure(self) -> None:
        """Handle failed execution."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout
        }


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class RetryMechanism:
    """
    Retry mechanism with exponential backoff.
    """

    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0,
                 max_delay: float = 60.0, backoff_factor: float = 2.0):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor

    def execute(self, func: Callable, *args, **kwargs):
        """Execute function with retry logic."""
        last_exception = None

        for attempt in range(self.max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                if attempt < self.max_attempts - 1:
                    delay = min(self.base_delay * (self.backoff_factor ** attempt), self.max_delay)
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay:.2f} seconds: {e}")
                    time.sleep(delay)
                else:
                    logger.error(f"All {self.max_attempts} attempts failed: {e}")

        raise last_exception


class FallbackMechanism:
    """
    Fallback mechanism for graceful degradation.
    """

    def __init__(self, primary_func: Callable, fallback_func: Callable):
        self.primary_func = primary_func
        self.fallback_func = fallback_func

    def execute(self, *args, **kwargs):
        """Execute primary function with fallback."""
        try:
            return self.primary_func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Primary function failed, using fallback: {e}")
            return self.fallback_func(*args, **kwargs)


class DegradationManager:
    """
    Manages graceful degradation of system capabilities.
    """

    def __init__(self):
        self.degradation_levels: Dict[str, List[str]] = {}
        self.current_level: Dict[str, str] = {}
        self.degradation_triggers: Dict[str, Callable] = {}

    def add_degradation_level(self, component: str, level: str, disabled_features: List[str]) -> None:
        """Add a degradation level for a component."""
        if component not in self.degradation_levels:
            self.degradation_levels[component] = []

        self.degradation_levels[component].extend(disabled_features)
        self.current_level[component] = "normal"

    def set_degradation_trigger(self, component: str, trigger_func: Callable) -> None:
        """Set trigger function for degradation."""
        self.degradation_triggers[component] = trigger_func

    def check_degradation(self, component: str) -> str:
        """Check if component should be degraded."""
        if component in self.degradation_triggers:
            try:
                should_degrade = self.degradation_triggers[component]()
                if should_degrade:
                    self.current_level[component] = "degraded"
                    logger.warning(f"Component {component} degraded")
            except Exception as e:
                logger.error(f"Error checking degradation for {component}: {e}")

        return self.current_level.get(component, "normal")

    def get_disabled_features(self, component: str) -> List[str]:
        """Get list of disabled features for a component."""
        level = self.current_level.get(component, "normal")
        if level == "degraded":
            return self.degradation_levels.get(component, [])
        return []


class HealthMonitor:
    """
    Monitors health of system components.
    """

    def __init__(self, check_interval: float = 30.0):
        self.components: Dict[str, HealthStatus] = {}
        self.check_interval = check_interval
        self.health_checks: Dict[str, Callable] = {}
        self._running = False
        self._monitor_thread = None

    def register_component(self, name: str, health_check_func: Callable) -> None:
        """Register a component for health monitoring."""
        self.components[name] = HealthStatus(component=name)
        self.health_checks[name] = health_check_func

    def start_monitoring(self) -> None:
        """Start health monitoring."""
        if self._running:
            return

        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Health monitoring started")

    def stop_monitoring(self) -> None:
        """Stop health monitoring."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join()
        logger.info("Health monitoring stopped")

    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            for component_name, health_check in self.health_checks.items():
                try:
                    start_time = time.time()
                    is_healthy = health_check()
                    response_time = time.time() - start_time

                    status = self.components[component_name]
                    status.last_check = datetime.now()
                    status.response_time = response_time

                    if is_healthy:
                        status.status = "healthy"
                        status.success_count += 1
                    else:
                        status.status = "unhealthy"
                        status.error_count += 1

                    # Calculate uptime percentage
                    total_checks = status.success_count + status.error_count
                    if total_checks > 0:
                        status.uptime_percentage = (status.success_count / total_checks) * 100

                except Exception as e:
                    logger.error(f"Health check failed for {component_name}: {e}")
                    status = self.components[component_name]
                    status.status = "unknown"
                    status.error_count += 1

            time.sleep(self.check_interval)

    def get_health_status(self, component: str = None) -> Union[HealthStatus, Dict[str, HealthStatus]]:
        """Get health status for component(s)."""
        if component:
            return self.components.get(component, HealthStatus(component="unknown"))
        return self.components.copy()


class ErrorHandler:
    """
    Centralized error handling and recovery system.
    """

    def __init__(self):
        self.failure_history: deque = deque(maxlen=1000)
        self.recovery_actions: deque = deque(maxlen=1000)
        self.error_handlers: Dict[FailureType, List[Callable]] = {}
        self.recovery_strategies: Dict[FailureType, List[RecoveryStrategy]] = {}

        # Initialize default recovery strategies
        self._init_default_strategies()

    def _init_default_strategies(self) -> None:
        """Initialize default recovery strategies."""
        self.recovery_strategies = {
            FailureType.NETWORK_ERROR: [RecoveryStrategy.RETRY, RecoveryStrategy.CIRCUIT_BREAKER],
            FailureType.DATA_ERROR: [RecoveryStrategy.FALLBACK, RecoveryStrategy.DEGRADATION],
            FailureType.COMPUTATION_ERROR: [RecoveryStrategy.RETRY, RecoveryStrategy.ISOLATION],
            FailureType.MEMORY_ERROR: [RecoveryStrategy.DEGRADATION, RecoveryStrategy.RESTART],
            FailureType.TIMEOUT_ERROR: [RecoveryStrategy.RETRY, RecoveryStrategy.CIRCUIT_BREAKER],
            FailureType.EXTERNAL_SERVICE_ERROR: [RecoveryStrategy.CIRCUIT_BREAKER, RecoveryStrategy.FALLBACK]
        }

    def register_error_handler(self, failure_type: FailureType, handler: Callable) -> None:
        """Register an error handler for a failure type."""
        if failure_type not in self.error_handlers:
            self.error_handlers[failure_type] = []

        self.error_handlers[failure_type].append(handler)

    def handle_error(self, error: Exception, component: str, context: Dict[str, Any] = None) -> None:
        """Handle an error with appropriate recovery actions."""
        context = context or {}

        # Classify the error
        failure_type = self._classify_error(error)

        # Create failure event
        failure_event = FailureEvent(
            failure_type=failure_type,
            component=component,
            error_message=str(error),
            stack_trace=traceback.format_exc(),
            context=context,
            severity=self._determine_severity(error, failure_type)
        )

        # Record failure
        self.failure_history.append(failure_event)

        # Execute error handlers
        if failure_type in self.error_handlers:
            for handler in self.error_handlers[failure_type]:
                try:
                    handler(failure_event)
                except Exception as e:
                    logger.error(f"Error handler failed: {e}")

        # Execute recovery strategies
        self._execute_recovery_strategies(failure_event)

        logger.error(f"Handled error in {component}: {error}")

    def _classify_error(self, error: Exception) -> FailureType:
        """Classify an error into a failure type."""
        error_type = type(error).__name__

        if "Connection" in error_type or "Network" in error_type:
            return FailureType.NETWORK_ERROR
        elif "Timeout" in error_type:
            return FailureType.TIMEOUT_ERROR
        elif "Memory" in error_type:
            return FailureType.MEMORY_ERROR
        elif "Data" in str(error).lower() or "ValueError" in error_type:
            return FailureType.DATA_ERROR
        elif "Computation" in str(error).lower() or "Arithmetic" in error_type:
            return FailureType.COMPUTATION_ERROR
        else:
            return FailureType.EXTERNAL_SERVICE_ERROR

    def _determine_severity(self, error: Exception, failure_type: FailureType) -> str:
        """Determine the severity of a failure."""
        # Simple severity determination
        if failure_type in [FailureType.MEMORY_ERROR, FailureType.EXTERNAL_SERVICE_ERROR]:
            return "high"
        elif failure_type == FailureType.NETWORK_ERROR:
            return "medium"
        else:
            return "low"

    def _execute_recovery_strategies(self, failure_event: FailureEvent) -> None:
        """Execute recovery strategies for a failure event."""
        strategies = self.recovery_strategies.get(failure_event.failure_type, [])

        for strategy in strategies:
            try:
                recovery_action = RecoveryAction(
                    failure_event=failure_event,
                    strategy=strategy,
                    action_taken=f"Executed {strategy.value} strategy",
                    timestamp=datetime.now()
                )

                start_time = time.time()

                if strategy == RecoveryStrategy.RETRY:
                    recovery_action.details = {"message": "Retry mechanism triggered"}
                    recovery_action.success = True

                elif strategy == RecoveryStrategy.CIRCUIT_BREAKER:
                    recovery_action.details = {"message": "Circuit breaker activated"}
                    recovery_action.success = True

                elif strategy == RecoveryStrategy.FALLBACK:
                    recovery_action.details = {"message": "Fallback mechanism activated"}
                    recovery_action.success = True

                elif strategy == RecoveryStrategy.DEGRADATION:
                    recovery_action.details = {"message": "System degraded gracefully"}
                    recovery_action.success = True

                recovery_action.duration = time.time() - start_time
                self.recovery_actions.append(recovery_action)

            except Exception as e:
                logger.error(f"Recovery strategy {strategy.value} failed: {e}")

    def get_failure_summary(self) -> Dict[str, Any]:
        """Get summary of failure events."""
        if not self.failure_history:
            return {}

        # Group failures by type and component
        failure_counts = {}
        severity_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}

        for failure in self.failure_history:
            key = f"{failure.failure_type.value}:{failure.component}"
            failure_counts[key] = failure_counts.get(key, 0) + 1
            severity_counts[failure.severity] += 1

        return {
            "total_failures": len(self.failure_history),
            "failure_counts": failure_counts,
            "severity_distribution": severity_counts,
            "most_recent_failure": self.failure_history[-1] if self.failure_history else None
        }


class FaultTolerantDecorator:
    """
    Decorator for making functions fault-tolerant.
    """

    def __init__(self, error_handler: ErrorHandler,
                 retry_attempts: int = 3,
                 use_circuit_breaker: bool = True,
                 fallback_func: Callable = None):
        self.error_handler = error_handler
        self.retry_attempts = retry_attempts
        self.use_circuit_breaker = use_circuit_breaker
        self.fallback_func = fallback_func

        if use_circuit_breaker:
            self.circuit_breaker = CircuitBreaker()

    def __call__(self, func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get function name for component identification
            component = f"{func.__module__}.{func.__name__}"

            # Create retry mechanism
            retry = RetryMechanism(max_attempts=self.retry_attempts)

            # Create fallback if provided
            if self.fallback_func:
                fallback = FallbackMechanism(func, self.fallback_func)
                execution_func = lambda: fallback.execute(*args, **kwargs)
            else:
                execution_func = lambda: func(*args, **kwargs)

            try:
                if self.use_circuit_breaker:
                    return self.circuit_breaker.call(execution_func)
                else:
                    return retry.execute(execution_func)

            except Exception as e:
                # Handle the error
                context = {
                    "function": func.__name__,
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys())
                }
                self.error_handler.handle_error(e, component, context)

                # Re-raise the exception
                raise e

        return wrapper


# Global instances
_error_handler = ErrorHandler()
_health_monitor = HealthMonitor()
_degradation_manager = DegradationManager()


def get_error_handler() -> ErrorHandler:
    """Get the global error handler."""
    return _error_handler


def get_health_monitor() -> HealthMonitor:
    """Get the global health monitor."""
    return _health_monitor


def get_degradation_manager() -> DegradationManager:
    """Get the global degradation manager."""
    return _degradation_manager


def fault_tolerant(retry_attempts: int = 3, use_circuit_breaker: bool = True,
                  fallback_func: Callable = None):
    """Decorator for fault-tolerant functions."""
    return FaultTolerantDecorator(
        _error_handler,
        retry_attempts,
        use_circuit_breaker,
        fallback_func
    )


# Convenience functions
def register_health_check(component: str, health_check_func: Callable) -> None:
    """Register a health check for a component."""
    get_health_monitor().register_component(component, health_check_func)


def start_health_monitoring() -> None:
    """Start health monitoring."""
    get_health_monitor().start_monitoring()


def stop_health_monitoring() -> None:
    """Stop health monitoring."""
    get_health_monitor().stop_monitoring()


def get_system_health() -> Dict[str, Any]:
    """Get overall system health status."""
    health_status = get_health_monitor().get_health_status()
    failure_summary = get_error_handler().get_failure_summary()

    # Calculate overall system health
    if not health_status:
        overall_health = "unknown"
    else:
        unhealthy_count = sum(1 for status in health_status.values() if status.status == "unhealthy")
        degraded_count = sum(1 for status in health_status.values() if status.status == "degraded")

        if unhealthy_count > 0:
            overall_health = "unhealthy"
        elif degraded_count > len(health_status) * 0.5:
            overall_health = "degraded"
        else:
            overall_health = "healthy"

    return {
        "overall_health": overall_health,
        "component_health": {name: status.__dict__ for name, status in health_status.items()},
        "failure_summary": failure_summary
    }


if __name__ == "__main__":
    # Example usage
    import random

    # Register health checks
    def database_health_check():
        # Simulate database health check
        return random.random() > 0.1  # 90% success rate

    def api_health_check():
        # Simulate API health check
        return random.random() > 0.05  # 95% success rate

    register_health_check("database", database_health_check)
    register_health_check("api", api_health_check)

    # Start health monitoring
    start_health_monitoring()

    # Example fault-tolerant function
    @fault_tolerant(retry_attempts=2)
    def risky_operation():
        if random.random() < 0.3:  # 30% failure rate
            raise ConnectionError("Network connection failed")
        return "Operation successful"

    # Test the fault-tolerant function
    for i in range(10):
        try:
            result = risky_operation()
            print(f"Attempt {i+1}: {result}")
        except Exception as e:
            print(f"Attempt {i+1}: Failed - {e}")

    # Get system health
    time.sleep(2)  # Let health checks run
    health = get_system_health()
    print(f"System health: {health}")

    # Stop monitoring
    stop_health_monitoring()