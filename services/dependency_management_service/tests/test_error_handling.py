"""Tests for the error handling system"""

import unittest
from unittest.mock import Mock, patch
from datetime import datetime
from dependency_management.error_handling.error_manager import (
    ErrorManager,
    ErrorContext,
    ErrorSeverity,
    ErrorCategory,
    ErrorRecoveryStrategy,
    DependencyError
)
from dependency_management.error_handling.error_types import (
    DependencyVersionError,
    DependencyNetworkError,
    DependencySecurityError,
    DependencyValidationError,
    DependencyPerformanceError,
    DependencyResourceError
)
from dependency_management.error_handling.handlers import (
    NetworkErrorHandler,
    SecurityErrorHandler,
    PerformanceErrorHandler,
    ResourceErrorHandler
)

class TestErrorManager(unittest.TestCase):
    def setUp(self):
        self.error_manager = ErrorManager()
        self.mock_handler = Mock()
        
    def test_error_registration_and_handling(self):
        """Test error handler registration and execution"""
        # Register mock handler
        self.error_manager.register_handler(
            ErrorCategory.NETWORK,
            self.mock_handler
        )
        
        # Create and handle error
        error = DependencyNetworkError(
            url="http://test.com",
            message="Connection failed"
        )
        
        self.error_manager.handle_error(error)
        
        # Verify handler was called
        self.mock_handler.assert_called_once()
        
    def test_error_context_creation(self):
        """Test error context creation from different error types"""
        # Test with DependencyError
        error = DependencyVersionError(
            dependency="test-package",
            message="Version conflict"
        )
        
        with patch('logging.Logger.error') as mock_log:
            self.error_manager.handle_error(error)
            mock_log.assert_called_once()
            
        # Test with standard Exception
        error = ValueError("Invalid value")
        
        with patch('logging.Logger.error') as mock_log:
            self.error_manager.handle_error(error)
            mock_log.assert_called_once()
            
class TestErrorHandlers(unittest.TestCase):
    def setUp(self):
        self.network_handler = NetworkErrorHandler()
        self.security_handler = SecurityErrorHandler()
        self.performance_handler = PerformanceErrorHandler()
        self.resource_handler = ResourceErrorHandler()
        
    @patch('time.sleep')  # Prevent actual sleeping in tests
    def test_network_error_handler(self, mock_sleep):
        """Test network error handling with retries"""
        context = ErrorContext(
            timestamp=datetime.utcnow(),
            error_type="NetworkError",
            message="Connection failed",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.NETWORK,
            stack_trace="",
            component="test"
        )
        
        # Test retry mechanism
        for i in range(NetworkErrorHandler.MAX_RETRIES + 1):
            self.network_handler.handle(context)
            
        self.assertEqual(context.retry_count, NetworkErrorHandler.MAX_RETRIES)
        
    @patch('requests.post')
    def test_security_error_handler(self, mock_post):
        """Test security error handling with alerts"""
        mock_post.return_value.status_code = 200
        
        context = ErrorContext(
            timestamp=datetime.utcnow(),
            error_type="SecurityError",
            message="Security violation",
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.SECURITY,
            stack_trace="",
            component="test"
        )
        
        self.security_handler.handle(context)
        
        # Verify alerts were sent
        self.assertEqual(
            mock_post.call_count,
            len(SecurityErrorHandler.ALERT_ENDPOINTS)
        )
        
    def test_performance_error_handler(self):
        """Test performance error handling"""
        context = ErrorContext(
            timestamp=datetime.utcnow(),
            error_type="PerformanceError",
            message="Performance degraded",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.PERFORMANCE,
            stack_trace="",
            component="test",
            additional_data={
                "metric": "cpu",
                "threshold": 80.0,
                "actual": 90.0
            }
        )
        
        with patch.object(PerformanceErrorHandler, '_adjust_resources') as mock_adjust:
            self.performance_handler.handle(context)
            mock_adjust.assert_called_once()
            
    def test_resource_error_handler(self):
        """Test resource error handling"""
        context = ErrorContext(
            timestamp=datetime.utcnow(),
            error_type="ResourceError",
            message="Resource limit exceeded",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.RESOURCE,
            stack_trace="",
            component="test",
            additional_data={
                "resource_type": "memory",
                "usage": 0.95
            }
        )
        
        with patch.object(ResourceErrorHandler, '_cleanup_resources') as mock_cleanup:
            self.resource_handler.handle(context)
            mock_cleanup.assert_called_once()
            
class TestErrorTypes(unittest.TestCase):
    def test_dependency_version_error(self):
        """Test DependencyVersionError creation"""
        error = DependencyVersionError(
            dependency="test-package",
            message="Version conflict"
        )
        
        self.assertEqual(error.severity, ErrorSeverity.HIGH)
        self.assertEqual(error.category, ErrorCategory.DEPENDENCY)
        self.assertEqual(
            error.recovery_strategy,
            ErrorRecoveryStrategy.FALLBACK
        )
        
    def test_dependency_security_error(self):
        """Test DependencySecurityError creation"""
        error = DependencySecurityError(
            dependency="test-package",
            vulnerability="CVE-2025-1234",
            message="Security vulnerability found"
        )
        
        self.assertEqual(error.severity, ErrorSeverity.CRITICAL)
        self.assertEqual(error.category, ErrorCategory.SECURITY)
        self.assertEqual(
            error.recovery_strategy,
            ErrorRecoveryStrategy.NOTIFY
        )
        
    def test_dependency_performance_error(self):
        """Test DependencyPerformanceError creation"""
        error = DependencyPerformanceError(
            dependency="test-package",
            metric="cpu_usage",
            threshold=80.0,
            actual=90.0,
            message="Performance threshold exceeded"
        )
        
        self.assertEqual(error.severity, ErrorSeverity.MEDIUM)
        self.assertEqual(error.category, ErrorCategory.PERFORMANCE)
        self.assertEqual(
            error.recovery_strategy,
            ErrorRecoveryStrategy.NOTIFY
        )
        
if __name__ == '__main__':
    unittest.main()
