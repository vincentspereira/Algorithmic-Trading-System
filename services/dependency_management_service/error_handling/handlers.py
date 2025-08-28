"""
Error handlers for different error categories in dependency management.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
import requests
from .error_manager import ErrorContext, ErrorSeverity, ErrorCategory, error_manager
from prometheus_client import Counter

# Configure logging
logger = logging.getLogger(__name__)

# Prometheus metrics
RECOVERY_ATTEMPTS = Counter(
    'dependency_recovery_attempts_total',
    'Number of recovery attempts by strategy',
    ['strategy', 'success']
)

class NetworkErrorHandler:
    """Handles network-related errors"""
    
    MAX_RETRIES = 3
    BACKOFF_FACTOR = 2
    
    @classmethod
    def handle(cls, context: ErrorContext) -> None:
        """Handle network errors with retries and backoff"""
        if not hasattr(context, 'retry_count'):
            context.retry_count = 0
            
        if context.retry_count < cls.MAX_RETRIES:
            wait_time = (cls.BACKOFF_FACTOR ** context.retry_count)
            logger.info(f"Retrying network operation in {wait_time} seconds...")
            
            import time
            time.sleep(wait_time)
            
            context.retry_count += 1
            RECOVERY_ATTEMPTS.labels(
                strategy='network_retry',
                success='pending'
            ).inc()
        else:
            logger.error("Max retries reached for network operation")
            RECOVERY_ATTEMPTS.labels(
                strategy='network_retry',
                success='failure'
            ).inc()

class SecurityErrorHandler:
    """Handles security-related errors"""
    
    ALERT_ENDPOINTS: List[str] = [
        "http://alert-service/security",
        "http://monitoring-service/alerts"
    ]
    
    @classmethod
    def handle(cls, context: ErrorContext) -> None:
        """Handle security errors with immediate alerts"""
        alert_data = {
            "timestamp": context.timestamp.isoformat(),
            "severity": context.severity.value,
            "message": context.message,
            "component": context.component,
            "correlation_id": context.correlation_id,
            "stack_trace": context.stack_trace
        }
        
        for endpoint in cls.ALERT_ENDPOINTS:
            try:
                response = requests.post(endpoint, json=alert_data)
                if response.status_code == 200:
                    logger.info(f"Security alert sent to {endpoint}")
                    RECOVERY_ATTEMPTS.labels(
                        strategy='security_alert',
                        success='success'
                    ).inc()
                else:
                    logger.error(f"Failed to send security alert to {endpoint}")
                    RECOVERY_ATTEMPTS.labels(
                        strategy='security_alert',
                        success='failure'
                    ).inc()
            except Exception as e:
                logger.error(f"Error sending security alert: {str(e)}")
                RECOVERY_ATTEMPTS.labels(
                    strategy='security_alert',
                    success='failure'
                ).inc()

class PerformanceErrorHandler:
    """Handles performance-related errors"""
    
    @classmethod
    def handle(cls, context: ErrorContext) -> None:
        """Handle performance errors with adaptive measures"""
        if context.additional_data:
            metric = context.additional_data.get('metric')
            threshold = context.additional_data.get('threshold')
            actual = context.additional_data.get('actual')
            
            if all(v is not None for v in [metric, threshold, actual]):
                # Log performance issue
                logger.warning(
                    f"Performance threshold exceeded: {metric} = {actual} "
                    f"(threshold: {threshold})"
                )
                
                # Try to adjust resource allocation
                cls._adjust_resources(metric, actual, threshold)
                
                RECOVERY_ATTEMPTS.labels(
                    strategy='performance_adjustment',
                    success='success'
                ).inc()
    
    @classmethod
    def _adjust_resources(
        cls,
        metric: str,
        actual: float,
        threshold: float
    ) -> None:
        """Adjust resource allocation based on performance metrics"""
        # This would integrate with your resource management system
        logger.info(f"Adjusting resources for {metric}")
        # Implement resource adjustment logic here

class ResourceErrorHandler:
    """Handles resource-related errors"""
    
    RESOURCE_LIMITS: Dict[str, float] = {
        "memory": 0.9,  # 90% of max
        "cpu": 0.8,     # 80% of max
        "disk": 0.95    # 95% of max
    }
    
    @classmethod
    def handle(cls, context: ErrorContext) -> None:
        """Handle resource errors with cleanup and limits"""
        if context.additional_data:
            resource_type = context.additional_data.get('resource_type')
            usage = context.additional_data.get('usage')
            
            if resource_type and usage:
                if resource_type in cls.RESOURCE_LIMITS:
                    limit = cls.RESOURCE_LIMITS[resource_type]
                    
                    if usage > limit:
                        logger.warning(
                            f"Resource usage critical: {resource_type} at {usage*100}%"
                        )
                        cls._cleanup_resources(resource_type)
                        
                        RECOVERY_ATTEMPTS.labels(
                            strategy='resource_cleanup',
                            success='success'
                        ).inc()
    
    @classmethod
    def _cleanup_resources(cls, resource_type: str) -> None:
        """Clean up resources based on type"""
        logger.info(f"Cleaning up {resource_type} resources")
        # Implement resource cleanup logic here

# Register handlers with error manager
error_manager.register_handler(ErrorCategory.NETWORK, NetworkErrorHandler.handle)
error_manager.register_handler(ErrorCategory.SECURITY, SecurityErrorHandler.handle)
error_manager.register_handler(ErrorCategory.PERFORMANCE, PerformanceErrorHandler.handle)
error_manager.register_handler(ErrorCategory.RESOURCE, ResourceErrorHandler.handle)
