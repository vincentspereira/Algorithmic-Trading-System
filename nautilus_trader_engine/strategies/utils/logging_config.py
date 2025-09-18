"""Comprehensive Logging and Monitoring Configuration for Trading Strategies

This module provides centralized logging configuration, performance monitoring,
and alerting capabilities for all trading strategy modules.

Author: AI Assistant
Date: 2024-12-15
"""

import logging
import logging.handlers
import sys
import os
import json
import time
import threading
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import traceback
from collections import defaultdict, deque
import psutil
from functools import wraps


class LogLevel(Enum):
    """Log levels for trading system"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    TRADE = "TRADE"  # Special level for trade-related logs
    PERFORMANCE = "PERFORMANCE"  # Special level for performance metrics


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PerformanceMetric:
    """Performance monitoring metric"""
    name: str
    value: float
    timestamp: datetime
    unit: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None


@dataclass
class Alert:
    """System alert"""
    message: str
    severity: AlertSeverity
    timestamp: datetime
    source: str
    tags: Dict[str, str] = field(default_factory=dict)
    resolved: bool = False
    resolution_time: Optional[datetime] = None


class TradingFormatter(logging.Formatter):
    """Custom formatter for trading system logs"""
    
    def __init__(self, include_performance: bool = True):
        super().__init__()
        self.include_performance = include_performance
        
        # Color codes for console output
        self.colors = {
            'DEBUG': '\033[36m',      # Cyan
            'INFO': '\033[32m',       # Green
            'WARNING': '\033[33m',    # Yellow
            'ERROR': '\033[31m',      # Red
            'CRITICAL': '\033[35m',   # Magenta
            'TRADE': '\033[94m',      # Blue
            'PERFORMANCE': '\033[96m', # Light Cyan
            'RESET': '\033[0m'        # Reset
        }
    
    def format(self, record):
        # Add timestamp
        record.timestamp = datetime.now().isoformat()
        
        # Add thread info
        record.thread_name = threading.current_thread().name
        
        # Add process info if available
        try:
            process = psutil.Process()
            record.cpu_percent = process.cpu_percent()
            record.memory_mb = process.memory_info().rss / 1024 / 1024
        except:
            record.cpu_percent = 0.0
            record.memory_mb = 0.0
        
        # Format based on log level
        if record.levelname == 'TRADE':
            return self._format_trade_log(record)
        elif record.levelname == 'PERFORMANCE':
            return self._format_performance_log(record)
        else:
            return self._format_standard_log(record)
    
    def _format_trade_log(self, record):
        """Format trade-specific logs"""
        base_format = (
            f"{record.timestamp} | TRADE | {record.thread_name} | "
            f"{record.name} | {record.getMessage()}"
        )
        
        # Add trade-specific fields if available
        trade_fields = []
        for attr in ['symbol', 'side', 'quantity', 'price', 'order_id']:
            if hasattr(record, attr):
                trade_fields.append(f"{attr}={getattr(record, attr)}")
        
        if trade_fields:
            base_format += f" | {' | '.join(trade_fields)}"
        
        return base_format
    
    def _format_performance_log(self, record):
        """Format performance monitoring logs"""
        return (
            f"{record.timestamp} | PERF | {record.thread_name} | "
            f"{record.name} | {record.getMessage()} | "
            f"CPU: {record.cpu_percent:.1f}% | MEM: {record.memory_mb:.1f}MB"
        )
    
    def _format_standard_log(self, record):
        """Format standard logs"""
        color = self.colors.get(record.levelname, '')
        reset = self.colors.get('RESET', '')
        
        base_format = (
            f"{record.timestamp} | {color}{record.levelname:8}{reset} | "
            f"{record.thread_name} | {record.name} | {record.getMessage()}"
        )
        
        # Add exception info if present
        if record.exc_info:
            base_format += f"\n{self.formatException(record.exc_info)}"
        
        return base_format


class PerformanceMonitor:
    """Monitor system and strategy performance"""
    
    def __init__(self, max_metrics: int = 10000):
        self.metrics: deque = deque(maxlen=max_metrics)
        self.alerts: List[Alert] = []
        self.thresholds: Dict[str, Dict[str, float]] = {}
        self.callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self.lock = threading.Lock()
        
        # Start monitoring thread
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def add_metric(self, metric: PerformanceMetric) -> None:
        """
        Add a performance metric.
        
        Args:
            metric: PerformanceMetric to add
        """
        with self.lock:
            self.metrics.append(metric)
            
            # Check thresholds
            self._check_thresholds(metric)
            
            # Trigger callbacks
            for callback in self.callbacks.get(metric.name, []):
                try:
                    callback(metric)
                except Exception as e:
                    logging.error(f"Error in performance callback: {e}")
    
    def set_threshold(self, metric_name: str, warning: float, critical: float) -> None:
        """
        Set alert thresholds for a metric.
        
        Args:
            metric_name: Name of the metric
            warning: Warning threshold
            critical: Critical threshold
        """
        self.thresholds[metric_name] = {
            'warning': warning,
            'critical': critical
        }
    
    def add_callback(self, metric_name: str, callback: Callable[[PerformanceMetric], None]) -> None:
        """
        Add callback for metric updates.
        
        Args:
            metric_name: Name of the metric to monitor
            callback: Callback function
        """
        self.callbacks[metric_name].append(callback)
    
    def get_metrics(
        self,
        metric_name: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[PerformanceMetric]:
        """
        Get performance metrics.
        
        Args:
            metric_name: Filter by metric name
            since: Filter by timestamp
            limit: Limit number of results
            
        Returns:
            List of PerformanceMetric
        """
        with self.lock:
            filtered_metrics = list(self.metrics)
            
            if metric_name:
                filtered_metrics = [m for m in filtered_metrics if m.name == metric_name]
            
            if since:
                filtered_metrics = [m for m in filtered_metrics if m.timestamp >= since]
            
            if limit:
                filtered_metrics = filtered_metrics[-limit:]
            
            return filtered_metrics
    
    def get_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        unresolved_only: bool = False
    ) -> List[Alert]:
        """
        Get system alerts.
        
        Args:
            severity: Filter by severity
            unresolved_only: Only return unresolved alerts
            
        Returns:
            List of Alert
        """
        filtered_alerts = self.alerts.copy()
        
        if severity:
            filtered_alerts = [a for a in filtered_alerts if a.severity == severity]
        
        if unresolved_only:
            filtered_alerts = [a for a in filtered_alerts if not a.resolved]
        
        return filtered_alerts
    
    def resolve_alert(self, alert: Alert) -> None:
        """
        Mark an alert as resolved.
        
        Args:
            alert: Alert to resolve
        """
        alert.resolved = True
        alert.resolution_time = datetime.now()
    
    def _check_thresholds(self, metric: PerformanceMetric) -> None:
        """Check if metric exceeds thresholds"""
        thresholds = self.thresholds.get(metric.name)
        if not thresholds:
            return
        
        warning_threshold = thresholds.get('warning')
        critical_threshold = thresholds.get('critical')
        
        if critical_threshold and metric.value >= critical_threshold:
            alert = Alert(
                message=f"Critical threshold exceeded for {metric.name}: {metric.value} >= {critical_threshold}",
                severity=AlertSeverity.CRITICAL,
                timestamp=datetime.now(),
                source="performance_monitor",
                tags=metric.tags.copy()
            )
            self.alerts.append(alert)
            
        elif warning_threshold and metric.value >= warning_threshold:
            alert = Alert(
                message=f"Warning threshold exceeded for {metric.name}: {metric.value} >= {warning_threshold}",
                severity=AlertSeverity.MEDIUM,
                timestamp=datetime.now(),
                source="performance_monitor",
                tags=metric.tags.copy()
            )
            self.alerts.append(alert)
    
    def _monitor_loop(self) -> None:
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                # Collect system metrics
                self._collect_system_metrics()
                time.sleep(30)  # Monitor every 30 seconds
            except Exception as e:
                logging.error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait longer on error
    
    def _collect_system_metrics(self) -> None:
        """Collect system performance metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.add_metric(PerformanceMetric(
                name="system_cpu_percent",
                value=cpu_percent,
                timestamp=datetime.now(),
                unit="%"
            ))
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.add_metric(PerformanceMetric(
                name="system_memory_percent",
                value=memory.percent,
                timestamp=datetime.now(),
                unit="%"
            ))
            
            # Disk usage
            disk = psutil.disk_usage('/')
            self.add_metric(PerformanceMetric(
                name="system_disk_percent",
                value=(disk.used / disk.total) * 100,
                timestamp=datetime.now(),
                unit="%"
            ))
            
        except Exception as e:
            logging.error(f"Error collecting system metrics: {e}")
    
    def stop(self) -> None:
        """Stop the performance monitor"""
        self.monitoring_active = False
        if self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)


class TradingLogger:
    """Centralized logging configuration for trading system"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.loggers: Dict[str, logging.Logger] = {}
        self.performance_monitor = PerformanceMonitor()
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        # Add custom log levels
        logging.addLevelName(25, 'TRADE')
        logging.addLevelName(24, 'PERFORMANCE')
        
        # Configure root logger
        self._configure_root_logger()
    
    def get_logger(self, name: str, level: LogLevel = LogLevel.INFO) -> logging.Logger:
        """
        Get or create a logger with the specified configuration.
        
        Args:
            name: Logger name
            level: Log level
            
        Returns:
            Configured logger
        """
        if name in self.loggers:
            return self.loggers[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level.value))
        
        # Add handlers if not already present
        if not logger.handlers:
            # Console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(TradingFormatter())
            logger.addHandler(console_handler)
            
            # File handler
            file_handler = logging.handlers.RotatingFileHandler(
                self.log_dir / f"{name}.log",
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            file_handler.setFormatter(TradingFormatter())
            logger.addHandler(file_handler)
            
            # Trade-specific handler
            if 'strategy' in name.lower() or 'trade' in name.lower():
                trade_handler = logging.handlers.RotatingFileHandler(
                    self.log_dir / "trades.log",
                    maxBytes=50*1024*1024,  # 50MB
                    backupCount=10
                )
                trade_handler.setLevel(25)  # TRADE level
                trade_handler.setFormatter(TradingFormatter())
                logger.addHandler(trade_handler)
        
        self.loggers[name] = logger
        return logger
    
    def log_trade(self, logger_name: str, message: str, **kwargs) -> None:
        """
        Log a trade-related event.
        
        Args:
            logger_name: Name of the logger
            message: Log message
            **kwargs: Additional trade fields
        """
        logger = self.get_logger(logger_name)
        
        # Add trade fields to log record
        extra = {k: v for k, v in kwargs.items()}
        logger.log(25, message, extra=extra)  # TRADE level
    
    def log_performance(self, logger_name: str, metric_name: str, value: float, **kwargs) -> None:
        """
        Log a performance metric.
        
        Args:
            logger_name: Name of the logger
            metric_name: Name of the metric
            value: Metric value
            **kwargs: Additional metric fields
        """
        logger = self.get_logger(logger_name)
        
        # Log to file
        logger.log(24, f"METRIC: {metric_name} = {value}")  # PERFORMANCE level
        
        # Add to performance monitor
        metric = PerformanceMetric(
            name=metric_name,
            value=value,
            timestamp=datetime.now(),
            tags=kwargs
        )
        self.performance_monitor.add_metric(metric)
    
    def _configure_root_logger(self) -> None:
        """Configure the root logger"""
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Add console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(TradingFormatter())
        root_logger.addHandler(console_handler)
        
        # Add main log file handler
        main_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "trading_system.log",
            maxBytes=20*1024*1024,  # 20MB
            backupCount=10
        )
        main_handler.setFormatter(TradingFormatter())
        root_logger.addHandler(main_handler)
        
        # Add error log handler
        error_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "errors.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(TradingFormatter())
        root_logger.addHandler(error_handler)


def performance_monitor(metric_name: str, unit: str = ""):
    """
    Decorator to monitor function performance.
    
    Args:
        metric_name: Name of the performance metric
        unit: Unit of measurement
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            logger = TradingLogger().get_logger(func.__module__)
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Log performance metric
                TradingLogger().log_performance(
                    func.__module__,
                    f"{metric_name}_execution_time",
                    execution_time * 1000,  # Convert to milliseconds
                    function=func.__name__,
                    unit="ms"
                )
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
                
                # Log error metric
                TradingLogger().log_performance(
                    func.__module__,
                    f"{metric_name}_error_count",
                    1,
                    function=func.__name__,
                    error_type=type(e).__name__
                )
                
                raise
        
        return wrapper
    return decorator


def log_trade_event(symbol: str, side: str, quantity: float, price: float, order_id: str = ""):
    """
    Decorator to log trade events.
    
    Args:
        symbol: Trading symbol
        side: Trade side (buy/sell)
        quantity: Trade quantity
        price: Trade price
        order_id: Order ID
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = TradingLogger().get_logger(func.__module__)
            
            try:
                result = func(*args, **kwargs)
                
                # Log successful trade
                TradingLogger().log_trade(
                    func.__module__,
                    f"Trade executed: {side} {quantity} {symbol} @ {price}",
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    price=price,
                    order_id=order_id,
                    function=func.__name__
                )
                
                return result
                
            except Exception as e:
                logger.error(f"Trade execution failed: {e}", exc_info=True)
                raise
        
        return wrapper
    return decorator


# Global logger instance
_trading_logger = TradingLogger()


def get_logger(name: str, level: LogLevel = LogLevel.INFO) -> logging.Logger:
    """Get a configured logger instance"""
    return _trading_logger.get_logger(name, level)


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance"""
    return _trading_logger.performance_monitor


# Export main classes and functions
__all__ = [
    'TradingLogger',
    'PerformanceMonitor',
    'TradingFormatter',
    'PerformanceMetric',
    'Alert',
    'LogLevel',
    'AlertSeverity',
    'get_logger',
    'get_performance_monitor',
    'performance_monitor',
    'log_trade_event'
]