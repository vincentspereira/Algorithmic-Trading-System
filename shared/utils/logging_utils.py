"""Comprehensive logging utilities for the Algorithmic Trading System.

This module provides consolidated logging configuration and utilities that were
previously duplicated across multiple components. Provides consistent logging
setup, structured logging, correlation ID support, YAML configuration loading,
and performance monitoring with trading-specific enhancements.
"""

import os
import sys
import json
import logging
import logging.handlers
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Union, List
from contextvars import ContextVar
import functools
import time

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

try:
    from pythonjsonlogger import jsonlogger
    JSON_LOGGER_AVAILABLE = True
except ImportError:
    JSON_LOGGER_AVAILABLE = False

# Context variables for structured logging
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


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
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
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
        
        correlation_id = correlation_id_var.get()
        if correlation_id:
            log_data["correlation_id"] = correlation_id
        elif hasattr(record, 'correlation_id'):
            log_data["correlation_id"] = record.correlation_id
        
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


class CorrelationIDFilter(logging.Filter):
    """Filter to add correlation ID to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation ID to the log record."""
        if not hasattr(record, 'correlation_id'):
            record.correlation_id = correlation_id_var.get() or self._generate_correlation_id()
        return True
    
    @staticmethod
    def _generate_correlation_id() -> str:
        """Generate a new correlation ID."""
        return str(uuid.uuid4())


class TradingSystemFormatter(logging.Formatter):
    """Enhanced JSON formatter for the trading system with correlation ID support."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hostname = os.getenv('HOSTNAME', 'localhost')
        self.service_name = os.getenv('SERVICE_NAME', 'trading-system')
        self.environment = os.getenv('ENVIRONMENT', 'development')
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with trading system specific fields."""
        log_data = {
            'timestamp': datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            'hostname': self.hostname,
            'service': self.service_name,
            'environment': self.environment,
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': record.thread,
            'process': record.process
        }
        
        # Add correlation ID if available
        if hasattr(record, 'correlation_id'):
            log_data['correlation_id'] = record.correlation_id
        
        # Add context variables
        request_id = request_id_var.get()
        if request_id:
            log_data['request_id'] = request_id
        
        user_id = user_id_var.get()
        if user_id:
            log_data['user_id'] = user_id
        
        # Add exception information if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }
        
        # Add custom fields from extra
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data, ensure_ascii=False)


class CorrelationContext:
    """Context manager for correlation ID."""
    
    def __init__(self, correlation_id_value: Optional[str] = None):
        self.correlation_id_value = correlation_id_value or str(uuid.uuid4())
        self.token = None
    
    def __enter__(self) -> str:
        self.token = correlation_id_var.set(self.correlation_id_value)
        return self.correlation_id_value
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.token:
            correlation_id_var.reset(self.token)


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


class TradingSystemLogger:
    """Enhanced logger with trading system specific methods."""
    
    def __init__(self, logger: logging.Logger, service: Optional[str] = None):
        self.logger = logger
        self.service = service
    
    def _log_with_extra(self, level: int, msg: str, extra_fields: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Log with extra fields."""
        if extra_fields:
            # Create a new record with extra fields
            record = self.logger.makeRecord(
                self.logger.name, level, '', 0, msg, (), None
            )
            record.extra_fields = extra_fields
            self.logger.handle(record)
        else:
            self.logger.log(level, msg, **kwargs)
    
    def debug(self, msg: str, extra_fields: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Log debug message."""
        self._log_with_extra(logging.DEBUG, msg, extra_fields, **kwargs)
    
    def info(self, msg: str, extra_fields: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Log info message."""
        self._log_with_extra(logging.INFO, msg, extra_fields, **kwargs)
    
    def warning(self, msg: str, extra_fields: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Log warning message."""
        self._log_with_extra(logging.WARNING, msg, extra_fields, **kwargs)
    
    def error(self, msg: str, extra_fields: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Log error message."""
        self._log_with_extra(logging.ERROR, msg, extra_fields, **kwargs)
    
    def critical(self, msg: str, extra_fields: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Log critical message."""
        self._log_with_extra(logging.CRITICAL, msg, extra_fields, **kwargs)
    
    # Trading-specific logging methods
    def log_order_created(self, order_id: str, symbol: str, side: str, quantity: float, 
                         order_type: str, price: Optional[float] = None, 
                         strategy_id: Optional[str] = None) -> None:
        """Log order creation."""
        extra_fields = {
            'event_type': 'order_created',
            'order_id': order_id,
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'order_type': order_type,
            'price': price,
            'strategy_id': strategy_id
        }
        self.info("Order created", extra_fields=extra_fields)
    
    def log_order_executed(self, order_id: str, execution_id: str, symbol: str, 
                          executed_quantity: float, execution_price: float, 
                          commission: float, slippage_bps: Optional[float] = None,
                          execution_venue: Optional[str] = None) -> None:
        """Log order execution."""
        extra_fields = {
            'event_type': 'order_executed',
            'order_id': order_id,
            'execution_id': execution_id,
            'symbol': symbol,
            'executed_quantity': executed_quantity,
            'execution_price': execution_price,
            'commission': commission,
            'slippage_bps': slippage_bps,
            'execution_venue': execution_venue
        }
        self.info("Order executed", extra_fields=extra_fields)
    
    def log_risk_limit_breach(self, limit_type: str, current_value: float, 
                             limit_value: float, portfolio_id: Optional[str] = None) -> None:
        """Log risk limit breach."""
        breach_percentage = ((current_value - limit_value) / limit_value) * 100
        extra_fields = {
            'event_type': 'risk_limit_breach',
            'limit_type': limit_type,
            'current_value': current_value,
            'limit_value': limit_value,
            'breach_percentage': breach_percentage,
            'portfolio_id': portfolio_id
        }
        self.warning("Risk limit breached", extra_fields=extra_fields)
    
    def log_market_data_received(self, symbol: str, data_type: str, source: str, 
                                latency_ms: Optional[float] = None,
                                sequence_number: Optional[int] = None) -> None:
        """Log market data reception."""
        extra_fields = {
            'event_type': 'market_data_received',
            'symbol': symbol,
            'data_type': data_type,
            'source': source,
            'latency_ms': latency_ms,
            'sequence_number': sequence_number
        }
        self.debug("Market data received", extra_fields=extra_fields)
    
    def log_ai_request_processed(self, request_id: str, user_id: str, request_type: str,
                                model_used: str, processing_time_ms: float,
                                confidence_score: Optional[float] = None) -> None:
        """Log AI request processing."""
        extra_fields = {
            'event_type': 'ai_request_processed',
            'request_id': request_id,
            'user_id': user_id,
            'request_type': request_type,
            'model_used': model_used,
            'processing_time_ms': processing_time_ms,
            'confidence_score': confidence_score
        }
        self.info("AI request processed", extra_fields=extra_fields)


def load_logging_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load logging configuration from YAML file."""
    if not YAML_AVAILABLE:
        return {}
    
    if config_path is None:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'config', 'logging', 'logging-config.yml'
        )
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Apply environment-specific overrides
        environment = os.getenv('ENVIRONMENT', 'development')
        if environment in config.get('environments', {}):
            env_config = config['environments'][environment]
            _merge_config(config, env_config)
        
        return config
    except Exception as e:
        print(f"Failed to load logging config from {config_path}: {e}")
        return {}


def _merge_config(base_config: Dict[str, Any], override_config: Dict[str, Any]) -> None:
    """Merge override configuration into base configuration."""
    for key, value in override_config.items():
        if isinstance(value, dict) and key in base_config:
            _merge_config(base_config[key], value)
        else:
            base_config[key] = value


def set_correlation_id(correlation_id_value: str) -> None:
    """Set correlation ID for current context."""
    correlation_id_var.set(correlation_id_value)


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID."""
    return correlation_id_var.get()


def with_correlation_id(func):
    """Decorator to automatically handle correlation ID for functions."""
    def wrapper(*args, **kwargs):
        # Check if correlation ID is already set
        if correlation_id_var.get() is None:
            with CorrelationContext():
                return func(*args, **kwargs)
        else:
            return func(*args, **kwargs)
    return wrapper


def get_trading_logger(name: str, service: Optional[str] = None) -> TradingSystemLogger:
    """Get a trading system logger instance."""
    logger = logging.getLogger(name)
    
    # Add correlation ID filter if not already present
    correlation_filter = CorrelationIDFilter()
    if not any(isinstance(f, CorrelationIDFilter) for f in logger.filters):
        logger.addFilter(correlation_filter)
    
    return TradingSystemLogger(logger, service)