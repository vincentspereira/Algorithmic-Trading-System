"""
Prometheus Metrics Module for Nautilus Trader Engine

This module defines and manages all Prometheus metrics for monitoring
the trading system's performance, data feeds, backtesting, and system health.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import time
from typing import Dict, Any, Optional
from prometheus_client import Counter, Histogram, Gauge, Info, CollectorRegistry, generate_latest
import logging

logger = logging.getLogger(__name__)


class TradingSystemMetrics:
    """Central metrics collector for the trading system"""
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """Initialize metrics with optional custom registry"""
        self.registry = registry or CollectorRegistry()
        
        # System Health Metrics
        self.system_info = Info(
            'nautilus_trader_system_info',
            'System information',
            registry=self.registry
        )
        
        self.system_uptime = Gauge(
            'nautilus_trader_uptime_seconds',
            'System uptime in seconds',
            registry=self.registry
        )
        
        self.system_health = Gauge(
            'nautilus_trader_health_status',
            'System health status (1=healthy, 0=unhealthy)',
            ['component'],
            registry=self.registry
        )
        
        # Data Feed Metrics
        self.data_fetch_requests_total = Counter(
            'nautilus_trader_data_fetch_requests_total',
            'Total number of data fetch requests',
            ['source', 'symbol', 'status'],
            registry=self.registry
        )
        
        self.data_fetch_duration = Histogram(
            'nautilus_trader_data_fetch_duration_seconds',
            'Time spent fetching data',
            ['source', 'symbol'],
            registry=self.registry
        )
        
        self.data_fetch_rate = Gauge(
            'nautilus_trader_data_fetch_rate_per_minute',
            'Data fetch rate per minute',
            ['source'],
            registry=self.registry
        )
        
        self.data_points_fetched = Counter(
            'nautilus_trader_data_points_total',
            'Total number of data points fetched',
            ['source', 'symbol'],
            registry=self.registry
        )
        
        self.data_source_errors = Counter(
            'nautilus_trader_data_source_errors_total',
            'Total number of data source errors',
            ['source', 'error_type'],
            registry=self.registry
        )
        
        # Backtesting Metrics
        self.backtest_runs_total = Counter(
            'nautilus_trader_backtest_runs_total',
            'Total number of backtest runs',
            ['engine', 'strategy', 'status'],
            registry=self.registry
        )
        
        self.backtest_duration = Histogram(
            'nautilus_trader_backtest_duration_seconds',
            'Time spent running backtests',
            ['engine', 'strategy'],
            registry=self.registry
        )
        
        self.backtest_performance = Gauge(
            'nautilus_trader_backtest_performance',
            'Backtest performance metrics',
            ['engine', 'strategy', 'symbol', 'metric'],
            registry=self.registry
        )
        
        self.backtest_trades = Gauge(
            'nautilus_trader_backtest_trades_total',
            'Total trades in backtest',
            ['engine', 'strategy', 'symbol'],
            registry=self.registry
        )
        
        # API Metrics
        self.api_requests_total = Counter(
            'nautilus_trader_api_requests_total',
            'Total API requests',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )
        
        self.api_request_duration = Histogram(
            'nautilus_trader_api_request_duration_seconds',
            'API request duration',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        self.api_active_connections = Gauge(
            'nautilus_trader_api_active_connections',
            'Number of active API connections',
            registry=self.registry
        )
        
        # Database Connection Metrics
        self.db_connections = Gauge(
            'nautilus_trader_db_connections',
            'Database connection status (1=connected, 0=disconnected)',
            ['database'],
            registry=self.registry
        )
        
        self.db_query_duration = Histogram(
            'nautilus_trader_db_query_duration_seconds',
            'Database query duration',
            ['database', 'operation'],
            registry=self.registry
        )
        
        self.db_errors = Counter(
            'nautilus_trader_db_errors_total',
            'Database errors',
            ['database', 'error_type'],
            registry=self.registry
        )
        
        # Memory and Resource Metrics
        self.memory_usage = Gauge(
            'nautilus_trader_memory_usage_bytes',
            'Memory usage in bytes',
            ['type'],
            registry=self.registry
        )
        
        self.cpu_usage = Gauge(
            'nautilus_trader_cpu_usage_percent',
            'CPU usage percentage',
            registry=self.registry
        )
        
        # Custom Business Metrics
        self.portfolio_value = Gauge(
            'nautilus_trader_portfolio_value',
            'Current portfolio value',
            ['strategy', 'symbol'],
            registry=self.registry
        )
        
        self.active_positions = Gauge(
            'nautilus_trader_active_positions',
            'Number of active positions',
            ['strategy'],
            registry=self.registry
        )
        
        # Initialize system info
        self._initialize_system_info()
        
        logger.info("TradingSystemMetrics initialized with all metric collectors")
    
    def _initialize_system_info(self):
        """Initialize system information metrics"""
        import platform
        import sys
        
        self.system_info.info({
            'version': '1.0.0',
            'python_version': sys.version,
            'platform': platform.platform(),
            'architecture': platform.architecture()[0]
        })
    
    # Data Feed Methods
    def record_data_fetch(self, source: str, symbol: str, duration: float, 
                         status: str = 'success', data_points: int = 0):
        """Record data fetch metrics"""
        self.data_fetch_requests_total.labels(
            source=source, symbol=symbol, status=status
        ).inc()
        
        self.data_fetch_duration.labels(
            source=source, symbol=symbol
        ).observe(duration)
        
        if data_points > 0:
            self.data_points_fetched.labels(
                source=source, symbol=symbol
            ).inc(data_points)
    
    def record_data_error(self, source: str, error_type: str):
        """Record data source error"""
        self.data_source_errors.labels(
            source=source, error_type=error_type
        ).inc()
    
    def update_data_fetch_rate(self, source: str, rate: float):
        """Update data fetch rate"""
        self.data_fetch_rate.labels(source=source).set(rate)
    
    # Backtesting Methods
    def record_backtest_run(self, engine: str, strategy: str, duration: float, 
                           status: str = 'success'):
        """Record backtest run metrics"""
        self.backtest_runs_total.labels(
            engine=engine, strategy=strategy, status=status
        ).inc()
        
        self.backtest_duration.labels(
            engine=engine, strategy=strategy
        ).observe(duration)
    
    def update_backtest_performance(self, engine: str, strategy: str, symbol: str, 
                                  metrics: Dict[str, float]):
        """Update backtest performance metrics"""
        for metric_name, value in metrics.items():
            self.backtest_performance.labels(
                engine=engine, strategy=strategy, symbol=symbol, metric=metric_name
            ).set(value)
    
    def update_backtest_trades(self, engine: str, strategy: str, symbol: str, 
                              trade_count: int):
        """Update backtest trade count"""
        self.backtest_trades.labels(
            engine=engine, strategy=strategy, symbol=symbol
        ).set(trade_count)
    
    # API Methods
    def record_api_request(self, method: str, endpoint: str, duration: float, 
                          status: str):
        """Record API request metrics"""
        self.api_requests_total.labels(
            method=method, endpoint=endpoint, status=status
        ).inc()
        
        self.api_request_duration.labels(
            method=method, endpoint=endpoint
        ).observe(duration)
    
    def update_active_connections(self, count: int):
        """Update active API connections count"""
        self.api_active_connections.set(count)
    
    # Database Methods
    def update_db_connection_status(self, database: str, connected: bool):
        """Update database connection status"""
        self.db_connections.labels(database=database).set(1 if connected else 0)
    
    def record_db_query(self, database: str, operation: str, duration: float):
        """Record database query metrics"""
        self.db_query_duration.labels(
            database=database, operation=operation
        ).observe(duration)
    
    def record_db_error(self, database: str, error_type: str):
        """Record database error"""
        self.db_errors.labels(
            database=database, error_type=error_type
        ).inc()
    
    # System Health Methods
    def update_system_health(self, component: str, healthy: bool):
        """Update system health status"""
        self.system_health.labels(component=component).set(1 if healthy else 0)
    
    def update_uptime(self, uptime_seconds: float):
        """Update system uptime"""
        self.system_uptime.set(uptime_seconds)
    
    def update_resource_usage(self, memory_bytes: int, cpu_percent: float):
        """Update resource usage metrics"""
        self.memory_usage.labels(type='total').set(memory_bytes)
        self.cpu_usage.set(cpu_percent)
    
    # Business Metrics Methods
    def update_portfolio_value(self, strategy: str, symbol: str, value: float):
        """Update portfolio value"""
        self.portfolio_value.labels(strategy=strategy, symbol=symbol).set(value)
    
    def update_active_positions(self, strategy: str, count: int):
        """Update active positions count"""
        self.active_positions.labels(strategy=strategy).set(count)
    
    # Utility Methods
    def get_metrics(self) -> str:
        """Get all metrics in Prometheus format"""
        return generate_latest(self.registry).decode('utf-8')
    
    def reset_metrics(self):
        """Reset all metrics (useful for testing)"""
        # Note: Counters cannot be reset, only Gauges and Histograms
        logger.warning("Metrics reset requested - only Gauges will be reset")


# Global metrics instance
_metrics_instance: Optional[TradingSystemMetrics] = None


def get_metrics() -> TradingSystemMetrics:
    """Get the global metrics instance"""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = TradingSystemMetrics()
    return _metrics_instance


def initialize_metrics(registry: Optional[CollectorRegistry] = None) -> TradingSystemMetrics:
    """Initialize the global metrics instance"""
    global _metrics_instance
    _metrics_instance = TradingSystemMetrics(registry)
    return _metrics_instance


# Context managers for timing operations
class MetricsTimer:
    """Context manager for timing operations and recording metrics"""
    
    def __init__(self, metrics: TradingSystemMetrics, metric_func, *args, **kwargs):
        self.metrics = metrics
        self.metric_func = metric_func
        self.args = args
        self.kwargs = kwargs
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        self.metric_func(duration, *self.args, **self.kwargs)


def time_data_fetch(source: str, symbol: str):
    """Context manager for timing data fetch operations"""
    metrics = get_metrics()
    return MetricsTimer(
        metrics, 
        lambda duration: metrics.record_data_fetch(source, symbol, duration)
    )


def time_backtest(engine: str, strategy: str):
    """Context manager for timing backtest operations"""
    metrics = get_metrics()
    return MetricsTimer(
        metrics,
        lambda duration: metrics.record_backtest_run(engine, strategy, duration)
    )


def time_api_request(method: str, endpoint: str, status: str = 'success'):
    """Context manager for timing API requests"""
    metrics = get_metrics()
    return MetricsTimer(
        metrics,
        lambda duration: metrics.record_api_request(method, endpoint, duration, status)
    )