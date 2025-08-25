"""
Specific error types and recovery strategies for dependency management.
"""

from typing import Any, Dict, Optional
from .error_manager import (
    DependencyError,
    ErrorSeverity,
    ErrorCategory,
    ErrorRecoveryStrategy
)

class DependencyVersionError(DependencyError):
    """Error when version resolution fails"""
    def __init__(
        self,
        dependency: str,
        message: str,
        correlation_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.DEPENDENCY,
            recovery_strategy=ErrorRecoveryStrategy.FALLBACK,
            correlation_id=correlation_id,
            dependency=dependency,
            **kwargs
        )

class DependencyNetworkError(DependencyError):
    """Error when network operations fail"""
    def __init__(
        self,
        url: str,
        message: str,
        correlation_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.NETWORK,
            recovery_strategy=ErrorRecoveryStrategy.RETRY,
            correlation_id=correlation_id,
            url=url,
            **kwargs
        )

class DependencySecurityError(DependencyError):
    """Error when security checks fail"""
    def __init__(
        self,
        dependency: str,
        vulnerability: str,
        message: str,
        correlation_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.SECURITY,
            recovery_strategy=ErrorRecoveryStrategy.NOTIFY,
            correlation_id=correlation_id,
            dependency=dependency,
            vulnerability=vulnerability,
            **kwargs
        )

class DependencyValidationError(DependencyError):
    """Error when dependency validation fails"""
    def __init__(
        self,
        dependency: str,
        validation_type: str,
        message: str,
        correlation_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.VALIDATION,
            recovery_strategy=ErrorRecoveryStrategy.TERMINATE,
            correlation_id=correlation_id,
            dependency=dependency,
            validation_type=validation_type,
            **kwargs
        )

class DependencyPerformanceError(DependencyError):
    """Error when performance thresholds are exceeded"""
    def __init__(
        self,
        dependency: str,
        metric: str,
        threshold: float,
        actual: float,
        message: str,
        correlation_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.PERFORMANCE,
            recovery_strategy=ErrorRecoveryStrategy.NOTIFY,
            correlation_id=correlation_id,
            dependency=dependency,
            metric=metric,
            threshold=threshold,
            actual=actual,
            **kwargs
        )

class DependencyResourceError(DependencyError):
    """Error when resource limits are reached"""
    def __init__(
        self,
        resource_type: str,
        limit: float,
        usage: float,
        message: str,
        correlation_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.RESOURCE,
            recovery_strategy=ErrorRecoveryStrategy.FALLBACK,
            correlation_id=correlation_id,
            resource_type=resource_type,
            limit=limit,
            usage=usage,
            **kwargs
        )
