"""
Logging utilities for the Algorithmic Trading System.

This module provides consolidated logging configuration and utilities that were
previously duplicated across multiple components. Provides consistent logging
setup, structured logging, and performance monitoring.
"""

import os
import sys
import json
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union
from contextvars import ContextVar
import functools
import time

# Context variables for structured logging
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)


class StructuredFormatter(logging.Formatter):
    """Structured JSON formatter for logs"""
    
    def __init__(self, include_extra: bool = True):
        """
        Initialize structured formatter
        
        Args:
            include_extra: Whether to include extra fields in log records
        """
        super().__init__()
        self.include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as structured JSON
        
        Args:
            record: Log record to format
            
        Returns:
            JSON formatted log string
        """
        # Base log data
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add context variables
        request_id = request_id_var.get()
        if request_id:
            log_data["request_id"] = request_id
        
        user_id = user_id_var.get()
        if user_id:
            log_data["user_id"] = user_id
        
        # Add exception information if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add extra fields if enabled
        if self.include_extra and hasattr(record, '__dict__'):
            extra_fields = {}
            excluded_fields = {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                'thread', 'threadName', 'processName', 'process', 'message'
            }
            
            for key, value in record.__dict__.items():
                if key not in excluded_fields and not key.startswith('_'):
                    try:
                        # Ensure value is JSON serializable
                        json.dumps(value)
                        extra_fields[key] = value
                    except (TypeError, ValueError):
                        extra_fields[key] = str(value)
            
            if extra_fields:
                log_data["extra"] = extra_fields
        
        return json.dumps(log_data, ensure_ascii=False)


class PerformanceLogger:
    """Performance logging utility for timing operations"""
    
    def __init__(self, logger: logging.Logger, level: int = logging.INFO):
        """
        Initialize performance logger
        
        Args:
            logger: Logger instance to use
            level: Log level for performance messages
        """
        self.logger = logger
        self.level = level
    
    def __call__(self, operation_name: str):
        """
        Decorator for logging operation performance
        
        Args:
            operation_name: Name of the operation being timed
            
        Returns:
            Decorator function
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    self.logger.log(
                        self.level,
                        f"Operation completed",
                        extra={
                            "operation": operation_name,
                            "execution_time_ms": round(execution_time * 1000, 2),
                            "status": "success"
                        }
                    )
                    return result
                except Exception as e:
                    execution_time = time.time() - start_time
                    self.logger.error(
                        f"Operation failed",
                        extra={
                            "operation": operation_name,
                            "execution_time_ms": round(execution_time * 1000, 2),
                            "status": "error",
                            "error": str(e)
                        }
                    )
                    raise
            return wrapper
        return decorator


def setup_logging(
    name: str = None,
    level: Union[str, int] = logging.INFO,
    log_file: Optional[str] = None,
    use_structured: bool = True,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    console_output: bool = True
) -> logging.Logger:
    """
    Set up consistent logging configuration
    
    Args:
        name: Logger name (uses calling module if None)
        level: Logging level
        log_file: Optional log file path
        use_structured: Whether to use structured JSON logging
        max_file_size: Maximum log file size before rotation
        backup_count: Number of backup files to keep
        console_output: Whether to output to console
        
    Returns:
        Configured logger instance
        
    Examples:
        >>> logger = setup_logging("my_service", logging.INFO, "logs/service.log")
        >>> logger.info("Service started")
    """
    # Get logger
    if name is None:
        # Get calling module name
        frame = sys._getframe(1)
        name = frame.f_globals.get('__name__', 'unknown')
    
    logger = logging.getLogger(name)
    
    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Set level
    if isinstance(level, str):
        level = getattr(logging, level.upper())
    logger.setLevel(level)
    
    # Choose formatter
    if use_structured:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_file:
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Set secure file permissions (owner read/write only)
        try:
            if log_path.exists():
                os.chmod(log_path, 0o600)
        except (OSError, PermissionError) as e:
            logger.warning(f"Could not set log file permissions: {e}")
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """
    Get logger with default configuration
    
    Args:
        name: Logger name (uses calling module if None)
        
    Returns:
        Logger instance
    """
    if name is None:
        # Get calling module name
        frame = sys._getframe(1)
        name = frame.f_globals.get('__name__', 'unknown')
    
    return logging.getLogger(name)


def set_request_context(request_id: str, user_id: Optional[str] = None):
    """
    Set request context for structured logging
    
    Args:
        request_id: Unique request identifier
        user_id: Optional user identifier
    """
    request_id_var.set(request_id)
    if user_id:
        user_id_var.set(user_id)


def clear_request_context():
    """Clear request context"""
    request_id_var.set(None)
    user_id_var.set(None)


def configure_trading_logger(
    service_name: str,
    environment: str = "development",
    log_dir: str = "logs"
) -> logging.Logger:
    """
    Configure logger for trading services with standard settings
    
    Args:
        service_name: Name of the trading service
        environment: Deployment environment
        log_dir: Directory for log files
        
    Returns:
        Configured logger for trading services
    """
    # Determine log level based on environment
    log_level = logging.DEBUG if environment == "development" else logging.INFO
    
    # Create log file path
    log_file = os.path.join(log_dir, f"{service_name}.log")
    
    # Set up logger
    logger = setup_logging(
        name=f"trading.{service_name}",
        level=log_level,
        log_file=log_file,
        use_structured=True
    )
    
    # Log configuration
    logger.info(
        "Logger configured",
        extra={
            "service": service_name,
            "environment": environment,
            "log_level": logging.getLevelName(log_level),
            "log_file": log_file
        }
    )
    
    return logger


def log_api_request(logger: logging.Logger):
    """
    Decorator for logging API requests and responses
    
    Args:
        logger: Logger instance to use
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(
                    "API request completed",
                    extra={
                        "function": func.__name__,
                        "execution_time_ms": round(execution_time * 1000, 2),
                        "status": "success"
                    }
                )
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    "API request failed",
                    extra={
                        "function": func.__name__,
                        "execution_time_ms": round(execution_time * 1000, 2),
                        "status": "error",
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                )
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(
                    "API request completed",
                    extra={
                        "function": func.__name__,
                        "execution_time_ms": round(execution_time * 1000, 2),
                        "status": "success"
                    }
                )
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    "API request failed",
                    extra={
                        "function": func.__name__,
                        "execution_time_ms": round(execution_time * 1000, 2),
                        "status": "error",
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                )
                raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Performance logger instance for reuse
performance_logger = None

def get_performance_logger(logger_name: str = "performance") -> PerformanceLogger:
    """
    Get performance logger instance
    
    Args:
        logger_name: Name for the performance logger
        
    Returns:
        PerformanceLogger instance
    """
    global performance_logger
    if performance_logger is None:
        logger = get_logger(logger_name)
        performance_logger = PerformanceLogger(logger)
    return performance_logger