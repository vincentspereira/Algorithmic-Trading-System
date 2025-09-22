"""
Unit tests for fault tolerance system components.
"""

import unittest
import time
import asyncio
from unittest.mock import Mock, patch, MagicMock, call
import sys
import threading

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from nautilus_trader_engine.tests.testing_framework import TestCase, unit_test
from nautilus_trader_engine.core.fault_tolerance.fault_tolerance_system import (
    FailureType, RecoveryStrategy, CircuitBreakerState, FailureEvent,
    RecoveryAction, HealthStatus, CircuitBreaker, RetryMechanism,
    FallbackMechanism, DegradationManager, HealthMonitor, ErrorHandler,
    FaultTolerantDecorator, get_error_handler, get_health_monitor,
    get_degradation_manager, fault_tolerant
)


class TestCircuitBreaker(TestCase):
    """Test cases for CircuitBreaker."""

    def setUp(self):
        super().setUp()
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)

    @unit_test()
    def test_circuit_breaker_initial_state(self):
        """Test circuit breaker initial state."""
        self.assertEqual(self.circuit_breaker.state, CircuitBreakerState.CLOSED)
        self.assertEqual(self.circuit_breaker.failure_count, 0)
        self.assertIsNone(self.circuit_breaker.last_failure_time)

    @unit_test()
    def test_circuit_breaker_success(self):
        """Test circuit breaker success handling."""
        def successful_operation():
            return "success"

        # Successful call
        result = self.circuit_breaker.call(successful_operation)
        self.assertEqual(result, "success")
        self.assertEqual(self.circuit_breaker.state, CircuitBreakerState.CLOSED)
        self.assertEqual(self.circuit_breaker.success_count, 1)

    @unit_test()
    def test_circuit_breaker_failure_and_recovery(self):
        """Test circuit breaker failure and recovery."""
        call_count = 0

        def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ValueError("Operation failed")
            return "success"

        # First failure
        with self.assertRaises(ValueError):
            self.circuit_breaker.call(failing_operation)

        self.assertEqual(self.circuit_breaker.failure_count, 1)
        self.assertEqual(self.circuit_breaker.state, CircuitBreakerState.CLOSED)

        # Second failure
        with self.assertRaises(ValueError):
            self.circuit_breaker.call(failing_operation)

        self.assertEqual(self.circuit_breaker.failure_count, 2)
        self.assertEqual(self.circuit_breaker.state, CircuitBreakerState.CLOSED)

        # Third failure - should open circuit
        with self.assertRaises(ValueError):
            self.circuit_breaker.call(failing_operation)

        self.assertEqual(self.circuit_breaker.failure_count, 3)
        self.assertEqual(self.circuit_breaker.state, CircuitBreakerState.OPEN)

        # Call while open should raise CircuitBreakerOpenException
        from nautilus_trader_engine.core.fault_tolerance.fault_tolerance_system import CircuitBreakerOpenException
        with self.assertRaises(CircuitBreakerOpenException):
            self.circuit_breaker.call(failing_operation)

        # Wait for recovery timeout
        time.sleep(1.1)

        # Next call should be in half-open state
        result = self.circuit_breaker.call(failing_operation)
        self.assertEqual(result, "success")
        self.assertEqual(self.circuit_breaker.state, CircuitBreakerState.CLOSED)
        self.assertEqual(self.circuit_breaker.failure_count, 0)

    @unit_test()
    def test_circuit_breaker_stats(self):
        """Test circuit breaker statistics."""
        def successful_operation():
            return "success"

        def failing_operation():
            raise ValueError("Failed")

        # Mix of success and failure
        self.circuit_breaker.call(successful_operation)
        self.circuit_breaker.call(successful_operation)

        try:
            self.circuit_breaker.call(failing_operation)
        except ValueError:
            pass

        stats = self.circuit_breaker.get_status()

        self.assertEqual(stats["state"], "closed")
        self.assertEqual(stats["failure_count"], 1)
        self.assertEqual(stats["success_count"], 2)
        self.assertEqual(stats["failure_threshold"], 3)
        self.assertEqual(stats["recovery_timeout"], 1.0)


class TestRetryMechanism(TestCase):
    """Test cases for RetryMechanism."""

    @unit_test()
    def test_retry_mechanism_success(self):
        """Test retry mechanism with eventual success."""
        call_count = 0

        def eventually_successful_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        retry = RetryMechanism(max_attempts=5, base_delay=0.01)

        result = retry.execute(eventually_successful_operation)
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 3)

    @unit_test()
    def test_retry_mechanism_failure(self):
        """Test retry mechanism with persistent failure."""
        call_count = 0

        def always_failing_operation():
            nonlocal call_count
            call_count += 1
            raise ValueError("Persistent failure")

        retry = RetryMechanism(max_attempts=3, base_delay=0.01)

        with self.assertRaises(ValueError):
            retry.execute(always_failing_operation)

        self.assertEqual(call_count, 3)

    @unit_test()
    def test_retry_mechanism_exponential_backoff(self):
        """Test retry mechanism exponential backoff."""
        import time
        call_times = []

        def failing_operation():
            call_times.append(time.time())
            raise ValueError("Failure")

        retry = RetryMechanism(max_attempts=4, base_delay=0.1, backoff_factor=2)

        start_time = time.time()
        try:
            retry.execute(failing_operation)
        except ValueError:
            pass

        # Check that delays are increasing exponentially
        self.assertEqual(len(call_times), 4)
        delays = [call_times[i] - call_times[i-1] for i in range(1, len(call_times))]
        self.assertGreater(delays[1], delays[0])  # Second delay > first delay
        self.assertGreater(delays[2], delays[1])  # Third delay > second delay


class TestFallbackMechanism(TestCase):
    """Test cases for FallbackMechanism."""

    @unit_test()
    def test_fallback_mechanism_primary_success(self):
        """Test fallback mechanism when primary succeeds."""
        def primary():
            return "primary_result"

        def fallback():
            return "fallback_result"

        mechanism = FallbackMechanism(primary, fallback)
        result = mechanism.execute()

        self.assertEqual(result, "primary_result")

    @unit_test()
    def test_fallback_mechanism_primary_failure(self):
        """Test fallback mechanism when primary fails."""
        def primary():
            raise ValueError("Primary failed")

        def fallback():
            return "fallback_result"

        mechanism = FallbackMechanism(primary, fallback)
        result = mechanism.execute()

        self.assertEqual(result, "fallback_result")

    @unit_test()
    def test_fallback_mechanism_both_fail(self):
        """Test fallback mechanism when both primary and fallback fail."""
        def primary():
            raise ValueError("Primary failed")

        def fallback():
            raise RuntimeError("Fallback failed")

        mechanism = FallbackMechanism(primary, fallback)

        with self.assertRaises(RuntimeError):
            mechanism.execute()


class TestDegradationManager(TestCase):
    """Test cases for DegradationManager."""

    def setUp(self):
        super().setUp()
        self.manager = DegradationManager()

    @unit_test()
    def test_degradation_level_management(self):
        """Test degradation level management."""
        # Add degradation level
        self.manager.add_degradation_level("database", "degraded", ["cache", "analytics"])

        # Initially normal
        self.assertEqual(self.manager.check_degradation("database"), "normal")
        self.assertEqual(self.manager.get_disabled_features("database"), [])

        # Set to degraded
        self.manager.current_level["database"] = "degraded"

        # Check degraded state
        self.assertEqual(self.manager.check_degradation("database"), "degraded")
        self.assertEqual(self.manager.get_disabled_features("database"), ["cache", "analytics"])

    @unit_test()
    def test_degradation_trigger(self):
        """Test degradation trigger functionality."""
        trigger_called = False

        def degradation_trigger():
            nonlocal trigger_called
            trigger_called = True
            return True  # Trigger degradation

        self.manager.add_degradation_level("api", "degraded", ["advanced_features"])
        self.manager.set_degradation_trigger("api", degradation_trigger)

        # Check degradation
        result = self.manager.check_degradation("api")

        self.assertTrue(trigger_called)
        self.assertEqual(result, "degraded")
        self.assertEqual(self.manager.get_disabled_features("api"), ["advanced_features"])


class TestHealthMonitor(TestCase):
    """Test cases for HealthMonitor."""

    def setUp(self):
        super().setUp()
        self.monitor = HealthMonitor(check_interval=0.1)  # Fast checks for testing

    def tearDown(self):
        super().tearDown()
        self.monitor.stop_monitoring()

    @unit_test()
    def test_health_monitor_registration(self):
        """Test component registration."""
        def health_check():
            return True

        self.monitor.register_component("test_component", health_check)

        self.assertIn("test_component", self.monitor.components)
        self.assertIn("test_component", self.monitor.health_checks)

    @unit_test()
    def test_health_monitor_checking(self):
        """Test health checking functionality."""
        call_count = 0

        def health_check():
            nonlocal call_count
            call_count += 1
            return call_count <= 2  # Fail after 2 calls

        self.monitor.register_component("test_component", health_check)
        self.monitor.start_monitoring()

        # Wait for a few checks
        time.sleep(0.5)

        self.monitor.stop_monitoring()

        # Get health status
        status = self.monitor.get_health_status("test_component")

        self.assertIsNotNone(status)
        self.assertGreater(call_count, 0)

    @unit_test()
    def test_health_monitor_multiple_components(self):
        """Test monitoring multiple components."""
        def healthy_check():
            return True

        def unhealthy_check():
            return False

        self.monitor.register_component("healthy", healthy_check)
        self.monitor.register_component("unhealthy", unhealthy_check)

        # Get all statuses
        statuses = self.monitor.get_health_status()

        self.assertIn("healthy", statuses)
        self.assertIn("unhealthy", statuses)
        self.assertEqual(len(statuses), 2)


class TestErrorHandler(TestCase):
    """Test cases for ErrorHandler."""

    def setUp(self):
        super().setUp()
        self.handler = ErrorHandler()

    @unit_test()
    def test_error_classification(self):
        """Test error classification."""
        # Network error
        network_error = ConnectionError("Network failed")
        self.assertEqual(self.handler._classify_error(network_error), FailureType.NETWORK_ERROR)

        # Timeout error
        timeout_error = TimeoutError("Operation timed out")
        self.assertEqual(self.handler._classify_error(timeout_error), FailureType.TIMEOUT_ERROR)

        # Data error
        data_error = ValueError("Invalid data")
        self.assertEqual(self.handler._classify_error(data_error), FailureType.DATA_ERROR)

        # Memory error
        memory_error = MemoryError("Out of memory")
        self.assertEqual(self.handler._classify_error(memory_error), FailureType.MEMORY_ERROR)

        # Unknown error
        unknown_error = RuntimeError("Unknown error")
        self.assertEqual(self.handler._classify_error(unknown_error), FailureType.EXTERNAL_SERVICE_ERROR)

    @unit_test()
    def test_error_handling(self):
        """Test error handling and event recording."""
        test_error = ValueError("Test error")

        # Handle error
        self.handler.handle_error(test_error, "test_component", {"context": "test"})

        # Check failure history
        self.assertEqual(len(self.handler.failure_history), 1)

        failure = self.handler.failure_history[0]
        self.assertEqual(failure.failure_type, FailureType.DATA_ERROR)
        self.assertEqual(failure.component, "test_component")
        self.assertEqual(failure.error_message, "Test error")
        self.assertEqual(failure.context["context"], "test")

    @unit_test()
    def test_error_handler_with_callbacks(self):
        """Test error handler with registered callbacks."""
        callback_called = False
        callback_failure = None

        def test_callback(failure_event):
            nonlocal callback_called, callback_failure
            callback_called = True
            callback_failure = failure_event

        # Register callback
        self.handler.register_error_handler(FailureType.DATA_ERROR, test_callback)

        # Handle error
        test_error = ValueError("Test error")
        self.handler.handle_error(test_error, "test_component")

        # Check callback was called
        self.assertTrue(callback_called)
        self.assertIsNotNone(callback_failure)
        self.assertEqual(callback_failure.failure_type, FailureType.DATA_ERROR)

    @unit_test()
    def test_recovery_strategies(self):
        """Test recovery strategy execution."""
        test_error = ConnectionError("Network failed")
        failure_event = FailureEvent(
            failure_type=FailureType.NETWORK_ERROR,
            component="network_component",
            error_message="Network failed"
        )

        # Execute recovery strategies
        self.handler._execute_recovery_strategies(failure_event)

        # Check recovery actions were recorded
        self.assertGreater(len(self.handler.recovery_actions), 0)

        action = self.handler.recovery_actions[0]
        self.assertEqual(action.failure_event, failure_event)
        self.assertIn(action.strategy, [RecoveryStrategy.RETRY, RecoveryStrategy.CIRCUIT_BREAKER])

    @unit_test()
    def test_failure_summary(self):
        """Test failure summary generation."""
        # Add some failures
        self.handler.handle_error(ValueError("Data error 1"), "comp1")
        self.handler.handle_error(ConnectionError("Network error"), "comp2")
        self.handler.handle_error(ValueError("Data error 2"), "comp1")

        summary = self.handler.get_failure_summary()

        self.assertEqual(summary["total_failures"], 3)
        self.assertIn("DATA_ERROR:comp1", summary["failure_counts"])
        self.assertIn("NETWORK_ERROR:comp2", summary["failure_counts"])
        self.assertEqual(summary["failure_counts"]["DATA_ERROR:comp1"], 2)
        self.assertEqual(summary["failure_counts"]["NETWORK_ERROR:comp2"], 1)


class TestFaultTolerantDecorator(TestCase):
    """Test cases for FaultTolerantDecorator."""

    @unit_test()
    def test_decorator_success(self):
        """Test decorator with successful function."""
        call_count = 0

        @FaultTolerantDecorator(ErrorHandler())
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_function()

        self.assertEqual(result, "success")
        self.assertEqual(call_count, 1)

    @unit_test()
    def test_decorator_with_retry(self):
        """Test decorator with retry mechanism."""
        call_count = 0

        @FaultTolerantDecorator(ErrorHandler(), retry_attempts=2)
        def eventually_successful_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary failure")
            return "success"

        result = eventually_successful_function()

        self.assertEqual(result, "success")
        self.assertEqual(call_count, 2)  # Should be called twice

    @unit_test()
    def test_decorator_with_fallback(self):
        """Test decorator with fallback mechanism."""
        primary_called = False
        fallback_called = False

        def primary():
            nonlocal primary_called
            primary_called = True
            raise ValueError("Primary failed")

        def fallback():
            nonlocal fallback_called
            fallback_called = True
            return "fallback_result"

        decorator = FaultTolerantDecorator(ErrorHandler(), fallback_func=fallback)
        decorated_function = decorator(primary)

        result = decorated_function()

        self.assertEqual(result, "fallback_result")
        self.assertTrue(primary_called)
        self.assertTrue(fallback_called)

    @unit_test()
    def test_decorator_with_circuit_breaker(self):
        """Test decorator with circuit breaker."""
        call_count = 0

        @FaultTolerantDecorator(ErrorHandler(), use_circuit_breaker=True)
        def failing_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        # First few calls should raise the original exception
        for i in range(3):
            with self.assertRaises(ValueError):
                failing_function()

        # Circuit should be open now
        from nautilus_trader_engine.core.fault_tolerance.fault_tolerance_system import CircuitBreakerOpenException
        with self.assertRaises(CircuitBreakerOpenException):
            failing_function()


class TestGlobalInstances(TestCase):
    """Test cases for global instances."""

    @unit_test()
    def test_global_error_handler(self):
        """Test global error handler instance."""
        handler1 = get_error_handler()
        handler2 = get_error_handler()

        self.assertIs(handler1, handler2)
        self.assertIsInstance(handler1, ErrorHandler)

    @unit_test()
    def test_global_health_monitor(self):
        """Test global health monitor instance."""
        monitor1 = get_health_monitor()
        monitor2 = get_health_monitor()

        self.assertIs(monitor1, monitor2)
        self.assertIsInstance(monitor1, HealthMonitor)

    @unit_test()
    def test_global_degradation_manager(self):
        """Test global degradation manager instance."""
        manager1 = get_degradation_manager()
        manager2 = get_degradation_manager()

        self.assertIs(manager1, manager2)
        self.assertIsInstance(manager1, DegradationManager)

    @unit_test()
    def test_fault_tolerant_decorator_functionality(self):
        """Test the fault_tolerant decorator."""
        call_count = 0

        @fault_tolerant(retry_attempts=2)
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Retry me")
            return "success"

        result = test_function()

        self.assertEqual(result, "success")
        self.assertEqual(call_count, 2)


if __name__ == "__main__":
    unittest.main()