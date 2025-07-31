"""
Metrics Collection System
Comprehensive metrics collection for business-level KPIs, system performance metrics,
custom metric definitions, and metrics aggregation and storage.
"""

import asyncio
import logging
import time
import threading
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import json
import statistics
import warnings

# Suppress warnings
warnings.filterwarnings('ignore', category=RuntimeWarning)

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None


class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"
    RATE = "rate"
    PERCENTAGE = "percentage"


class MetricCategory(Enum):
    """Categories of metrics"""
    BUSINESS = "business"
    SYSTEM = "system"
    PERFORMANCE = "performance"
    TRADING = "trading"
    RISK = "risk"
    CUSTOM = "custom"


@dataclass
class MetricDefinition:
    """Definition of a metric"""
    name: str
    metric_type: MetricType
    category: MetricCategory
    description: str
    unit: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    aggregation_window: int = 60  # seconds
    retention_period: int = 86400  # 24 hours in seconds
    alert_thresholds: Dict[str, float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class MetricValue:
    """A metric value with timestamp"""
    value: Union[float, int]
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AggregatedMetric:
    """Aggregated metric data"""
    name: str
    start_time: datetime
    end_time: datetime
    count: int
    sum_value: float
    min_value: float
    max_value: float
    avg_value: float
    percentiles: Dict[str, float] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)


class MetricCollector:
    """Core metric collection engine"""
    
    def __init__(self, max_buffer_size: int = 10000):
        self.logger = logging.getLogger(__name__)
        self.metrics_buffer = defaultdict(deque)
        self.metric_definitions = {}
        self.max_buffer_size = max_buffer_size
        self.aggregated_metrics = defaultdict(list)
        self.lock = threading.RLock()
        
        # Performance tracking
        self.collection_stats = {
            "total_metrics_collected": 0,
            "collection_errors": 0,
            "last_collection_time": None,
            "buffer_utilization": 0.0
        }
        
    def register_metric(self, definition: MetricDefinition) -> bool:
        """Register a new metric definition"""
        try:
            with self.lock:
                self.metric_definitions[definition.name] = definition
                self.logger.info(f"Registered metric: {definition.name} ({definition.metric_type.value})")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to register metric {definition.name}: {e}")
            return False
    
    def collect_metric(self, name: str, value: Union[float, int], 
                      tags: Dict[str, str] = None, metadata: Dict[str, Any] = None) -> bool:
        """Collect a metric value"""
        try:
            if name not in self.metric_definitions:
                self.logger.warning(f"Metric {name} not registered, skipping collection")
                return False
            
            with self.lock:
                metric_value = MetricValue(
                    value=value,
                    timestamp=datetime.now(),
                    tags=tags or {},
                    metadata=metadata or {}
                )
                
                # Add to buffer
                buffer = self.metrics_buffer[name]
                buffer.append(metric_value)
                
                # Maintain buffer size
                if len(buffer) > self.max_buffer_size:
                    buffer.popleft()
                
                # Update collection stats
                self.collection_stats["total_metrics_collected"] += 1
                self.collection_stats["last_collection_time"] = datetime.now()
                self.collection_stats["buffer_utilization"] = len(buffer) / self.max_buffer_size
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to collect metric {name}: {e}")
            self.collection_stats["collection_errors"] += 1
            return False
    
    def get_metric_values(self, name: str, start_time: datetime = None, 
                         end_time: datetime = None) -> List[MetricValue]:
        """Get metric values within time range"""
        try:
            with self.lock:
                if name not in self.metrics_buffer:
                    return []
                
                values = list(self.metrics_buffer[name])
                
                # Filter by time range if specified
                if start_time or end_time:
                    filtered_values = []
                    for value in values:
                        if start_time and value.timestamp < start_time:
                            continue
                        if end_time and value.timestamp > end_time:
                            continue
                        filtered_values.append(value)
                    return filtered_values
                
                return values
                
        except Exception as e:
            self.logger.error(f"Failed to get metric values for {name}: {e}")
            return []
    
    def aggregate_metrics(self, name: str, window_seconds: int = 60) -> Optional[AggregatedMetric]:
        """Aggregate metrics over a time window"""
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(seconds=window_seconds)
            
            values = self.get_metric_values(name, start_time, end_time)
            
            if not values:
                return None
            
            numeric_values = [v.value for v in values]
            
            # Calculate aggregations
            aggregated = AggregatedMetric(
                name=name,
                start_time=start_time,
                end_time=end_time,
                count=len(numeric_values),
                sum_value=sum(numeric_values),
                min_value=min(numeric_values),
                max_value=max(numeric_values),
                avg_value=statistics.mean(numeric_values)
            )
            
            # Calculate percentiles if numpy is available
            if NUMPY_AVAILABLE and len(numeric_values) > 1:
                np_values = np.array(numeric_values)
                aggregated.percentiles = {
                    "p50": float(np.percentile(np_values, 50)),
                    "p90": float(np.percentile(np_values, 90)),
                    "p95": float(np.percentile(np_values, 95)),
                    "p99": float(np.percentile(np_values, 99))
                }
            
            # Store aggregated metric
            with self.lock:
                self.aggregated_metrics[name].append(aggregated)
                
                # Maintain aggregated metrics history
                definition = self.metric_definitions.get(name)
                if definition:
                    retention_limit = datetime.now() - timedelta(seconds=definition.retention_period)
                    self.aggregated_metrics[name] = [
                        agg for agg in self.aggregated_metrics[name]
                        if agg.end_time > retention_limit
                    ]
            
            return aggregated
            
        except Exception as e:
            self.logger.error(f"Failed to aggregate metrics for {name}: {e}")
            return None
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        with self.lock:
            stats = self.collection_stats.copy()
            stats["registered_metrics"] = len(self.metric_definitions)
            stats["buffer_sizes"] = {name: len(buffer) for name, buffer in self.metrics_buffer.items()}
            return stats


class BusinessMetricsCollector:
    """Collects business-level KPI metrics"""
    
    def __init__(self, collector: MetricCollector):
        self.collector = collector
        self.logger = logging.getLogger(__name__)
        self._register_business_metrics()
    
    def _register_business_metrics(self):
        """Register standard business metrics"""
        business_metrics = [
            MetricDefinition(
                name="trading.orders.total",
                metric_type=MetricType.COUNTER,
                category=MetricCategory.BUSINESS,
                description="Total number of orders placed",
                unit="count"
            ),
            MetricDefinition(
                name="trading.orders.filled",
                metric_type=MetricType.COUNTER,
                category=MetricCategory.BUSINESS,
                description="Number of filled orders",
                unit="count"
            ),
            MetricDefinition(
                name="trading.volume.daily",
                metric_type=MetricType.GAUGE,
                category=MetricCategory.BUSINESS,
                description="Daily trading volume",
                unit="USD"
            ),
            MetricDefinition(
                name="trading.pnl.realized",
                metric_type=MetricType.GAUGE,
                category=MetricCategory.BUSINESS,
                description="Realized profit and loss",
                unit="USD"
            ),
            MetricDefinition(
                name="trading.pnl.unrealized",
                metric_type=MetricType.GAUGE,
                category=MetricCategory.BUSINESS,
                description="Unrealized profit and loss",
                unit="USD"
            ),
            MetricDefinition(
                name="portfolio.value.total",
                metric_type=MetricType.GAUGE,
                category=MetricCategory.BUSINESS,
                description="Total portfolio value",
                unit="USD"
            ),
            MetricDefinition(
                name="risk.var.daily",
                metric_type=MetricType.GAUGE,
                category=MetricCategory.RISK,
                description="Daily Value at Risk",
                unit="USD"
            ),
            MetricDefinition(
                name="risk.exposure.total",
                metric_type=MetricType.GAUGE,
                category=MetricCategory.RISK,
                description="Total risk exposure",
                unit="USD"
            )
        ]
        
        for metric in business_metrics:
            self.collector.register_metric(metric)
    
    async def collect_trading_metrics(self, orders_data: Dict[str, Any]):
        """Collect trading-related metrics"""
        try:
            # Order metrics
            total_orders = orders_data.get("total_orders", 0)
            filled_orders = orders_data.get("filled_orders", 0)
            daily_volume = orders_data.get("daily_volume", 0.0)
            
            self.collector.collect_metric("trading.orders.total", total_orders)
            self.collector.collect_metric("trading.orders.filled", filled_orders)
            self.collector.collect_metric("trading.volume.daily", daily_volume)
            
            # Calculate fill rate
            fill_rate = (filled_orders / total_orders * 100) if total_orders > 0 else 0
            self.collector.collect_metric("trading.fill_rate", fill_rate, 
                                        metadata={"calculation": "filled/total*100"})
            
        except Exception as e:
            self.logger.error(f"Failed to collect trading metrics: {e}")
    
    async def collect_portfolio_metrics(self, portfolio_data: Dict[str, Any]):
        """Collect portfolio-related metrics"""
        try:
            total_value = portfolio_data.get("total_value", 0.0)
            realized_pnl = portfolio_data.get("realized_pnl", 0.0)
            unrealized_pnl = portfolio_data.get("unrealized_pnl", 0.0)
            
            self.collector.collect_metric("portfolio.value.total", total_value)
            self.collector.collect_metric("trading.pnl.realized", realized_pnl)
            self.collector.collect_metric("trading.pnl.unrealized", unrealized_pnl)
            
            # Calculate total P&L
            total_pnl = realized_pnl + unrealized_pnl
            self.collector.collect_metric("trading.pnl.total", total_pnl)
            
        except Exception as e:
            self.logger.error(f"Failed to collect portfolio metrics: {e}")
    
    async def collect_risk_metrics(self, risk_data: Dict[str, Any]):
        """Collect risk-related metrics"""
        try:
            daily_var = risk_data.get("daily_var", 0.0)
            total_exposure = risk_data.get("total_exposure", 0.0)
            
            self.collector.collect_metric("risk.var.daily", daily_var)
            self.collector.collect_metric("risk.exposure.total", total_exposure)
            
        except Exception as e:
            self.logger.error(f"Failed to collect risk metrics: {e}")


class SystemMetricsCollector:
    """Collects system performance metrics"""
    
    def __init__(self, collector: MetricCollector):
        self.collector = collector
        self.logger = logging.getLogger(__name__)
        self._register_system_metrics()
    
    def _register_system_metrics(self):
        """Register standard system metrics"""
        system_metrics = [
            MetricDefinition(
                name="system.cpu.usage",
                metric_type=MetricType.GAUGE,
                category=MetricCategory.SYSTEM,
                description="CPU usage percentage",
                unit="percent"
            ),
            MetricDefinition(
                name="system.memory.usage",
                metric_type=MetricType.GAUGE,
                category=MetricCategory.SYSTEM,
                description="Memory usage percentage",
                unit="percent"
            ),
            MetricDefinition(
                name="system.latency.api",
                metric_type=MetricType.TIMER,
                category=MetricCategory.PERFORMANCE,
                description="API response latency",
                unit="milliseconds"
            ),
            MetricDefinition(
                name="system.throughput.requests",
                metric_type=MetricType.RATE,
                category=MetricCategory.PERFORMANCE,
                description="Request throughput",
                unit="requests/second"
            ),
            MetricDefinition(
                name="system.errors.total",
                metric_type=MetricType.COUNTER,
                category=MetricCategory.SYSTEM,
                description="Total system errors",
                unit="count"
            ),
            MetricDefinition(
                name="system.uptime",
                metric_type=MetricType.GAUGE,
                category=MetricCategory.SYSTEM,
                description="System uptime",
                unit="seconds"
            )
        ]
        
        for metric in system_metrics:
            self.collector.register_metric(metric)
    
    async def collect_system_resources(self):
        """Collect system resource metrics"""
        try:
            # Simulate system resource collection
            # In production, this would use psutil or similar
            import random
            
            cpu_usage = random.uniform(10, 80)
            memory_usage = random.uniform(20, 90)
            
            self.collector.collect_metric("system.cpu.usage", cpu_usage)
            self.collector.collect_metric("system.memory.usage", memory_usage)
            
        except Exception as e:
            self.logger.error(f"Failed to collect system resources: {e}")
    
    async def collect_performance_metrics(self, latency_ms: float, request_count: int):
        """Collect performance metrics"""
        try:
            self.collector.collect_metric("system.latency.api", latency_ms)
            self.collector.collect_metric("system.throughput.requests", request_count)
            
        except Exception as e:
            self.logger.error(f"Failed to collect performance metrics: {e}")
    
    async def collect_error_metrics(self, error_count: int, error_type: str = "general"):
        """Collect error metrics"""
        try:
            self.collector.collect_metric("system.errors.total", error_count, 
                                        tags={"error_type": error_type})
            
        except Exception as e:
            self.logger.error(f"Failed to collect error metrics: {e}")


class CustomMetricsRegistry:
    """Registry for custom metric definitions"""
    
    def __init__(self, collector: MetricCollector):
        self.collector = collector
        self.logger = logging.getLogger(__name__)
        self.custom_metrics = {}
        self.metric_calculators = {}
    
    def register_custom_metric(self, definition: MetricDefinition, 
                             calculator: Callable = None) -> bool:
        """Register a custom metric with optional calculator function"""
        try:
            # Register with main collector
            if not self.collector.register_metric(definition):
                return False
            
            self.custom_metrics[definition.name] = definition
            
            if calculator:
                self.metric_calculators[definition.name] = calculator
            
            self.logger.info(f"Registered custom metric: {definition.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register custom metric {definition.name}: {e}")
            return False
    
    def collect_custom_metric(self, name: str, *args, **kwargs) -> bool:
        """Collect a custom metric using its calculator"""
        try:
            if name not in self.custom_metrics:
                self.logger.warning(f"Custom metric {name} not registered")
                return False
            
            if name in self.metric_calculators:
                # Use custom calculator
                calculator = self.metric_calculators[name]
                value = calculator(*args, **kwargs)
                return self.collector.collect_metric(name, value)
            else:
                # Direct value collection
                value = kwargs.get('value') or (args[0] if args else 0)
                return self.collector.collect_metric(name, value)
                
        except Exception as e:
            self.logger.error(f"Failed to collect custom metric {name}: {e}")
            return False
    
    def get_custom_metrics(self) -> Dict[str, MetricDefinition]:
        """Get all registered custom metrics"""
        return self.custom_metrics.copy()


class MetricsAggregator:
    """Aggregates and stores metrics data"""
    
    def __init__(self, collector: MetricCollector):
        self.collector = collector
        self.logger = logging.getLogger(__name__)
        self.aggregation_tasks = {}
        self.storage_backend = None
        
    def start_aggregation_task(self, metric_name: str, interval_seconds: int = 60):
        """Start periodic aggregation for a metric"""
        try:
            if metric_name in self.aggregation_tasks:
                self.logger.warning(f"Aggregation task for {metric_name} already running")
                return
            
            async def aggregation_loop():
                while True:
                    try:
                        aggregated = self.collector.aggregate_metrics(metric_name, interval_seconds)
                        if aggregated:
                            await self._store_aggregated_metric(aggregated)
                        await asyncio.sleep(interval_seconds)
                    except Exception as e:
                        self.logger.error(f"Aggregation error for {metric_name}: {e}")
                        await asyncio.sleep(interval_seconds)
            
            task = asyncio.create_task(aggregation_loop())
            self.aggregation_tasks[metric_name] = task
            
            self.logger.info(f"Started aggregation task for {metric_name} (interval: {interval_seconds}s)")
            
        except Exception as e:
            self.logger.error(f"Failed to start aggregation task for {metric_name}: {e}")
    
    def stop_aggregation_task(self, metric_name: str):
        """Stop aggregation task for a metric"""
        try:
            if metric_name in self.aggregation_tasks:
                task = self.aggregation_tasks[metric_name]
                task.cancel()
                del self.aggregation_tasks[metric_name]
                self.logger.info(f"Stopped aggregation task for {metric_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to stop aggregation task for {metric_name}: {e}")
    
    async def _store_aggregated_metric(self, aggregated: AggregatedMetric):
        """Store aggregated metric (placeholder for storage backend)"""
        try:
            # In production, this would store to database, time-series DB, etc.
            self.logger.debug(f"Storing aggregated metric: {aggregated.name} "
                            f"(avg: {aggregated.avg_value:.2f}, count: {aggregated.count})")
            
        except Exception as e:
            self.logger.error(f"Failed to store aggregated metric: {e}")
    
    def get_aggregated_metrics(self, metric_name: str, 
                             start_time: datetime = None, 
                             end_time: datetime = None) -> List[AggregatedMetric]:
        """Get aggregated metrics for a time range"""
        try:
            with self.collector.lock:
                aggregated_list = self.collector.aggregated_metrics.get(metric_name, [])
                
                if not start_time and not end_time:
                    return aggregated_list.copy()
                
                filtered_list = []
                for agg in aggregated_list:
                    if start_time and agg.end_time < start_time:
                        continue
                    if end_time and agg.start_time > end_time:
                        continue
                    filtered_list.append(agg)
                
                return filtered_list
                
        except Exception as e:
            self.logger.error(f"Failed to get aggregated metrics for {metric_name}: {e}")
            return []


class MetricsCollectionSystem:
    """Main metrics collection system orchestrator"""
    
    def __init__(self, max_buffer_size: int = 10000):
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.collector = MetricCollector(max_buffer_size)
        self.business_collector = BusinessMetricsCollector(self.collector)
        self.system_collector = SystemMetricsCollector(self.collector)
        self.custom_registry = CustomMetricsRegistry(self.collector)
        self.aggregator = MetricsAggregator(self.collector)
        
        # System state
        self.is_running = False
        self.collection_tasks = []
        
    async def start(self):
        """Start the metrics collection system"""
        try:
            if self.is_running:
                self.logger.warning("Metrics collection system already running")
                return
            
            self.is_running = True
            
            # Start system metrics collection
            system_task = asyncio.create_task(self._system_metrics_loop())
            self.collection_tasks.append(system_task)
            
            # Start aggregation for key metrics
            key_metrics = [
                "trading.orders.total",
                "trading.volume.daily",
                "portfolio.value.total",
                "system.cpu.usage",
                "system.memory.usage",
                "system.latency.api"
            ]
            
            for metric_name in key_metrics:
                self.aggregator.start_aggregation_task(metric_name, 60)
            
            self.logger.info("Metrics collection system started")
            
        except Exception as e:
            self.logger.error(f"Failed to start metrics collection system: {e}")
            self.is_running = False
    
    async def stop(self):
        """Stop the metrics collection system"""
        try:
            if not self.is_running:
                return
            
            self.is_running = False
            
            # Cancel collection tasks
            for task in self.collection_tasks:
                task.cancel()
            
            # Stop aggregation tasks
            for metric_name in list(self.aggregator.aggregation_tasks.keys()):
                self.aggregator.stop_aggregation_task(metric_name)
            
            self.logger.info("Metrics collection system stopped")
            
        except Exception as e:
            self.logger.error(f"Failed to stop metrics collection system: {e}")
    
    async def _system_metrics_loop(self):
        """Periodic system metrics collection"""
        while self.is_running:
            try:
                await self.system_collector.collect_system_resources()
                await asyncio.sleep(30)  # Collect every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"System metrics collection error: {e}")
                await asyncio.sleep(30)
    
    async def collect_business_metrics(self, metric_data: Dict[str, Any]):
        """Collect business metrics from external data"""
        try:
            if "trading" in metric_data:
                await self.business_collector.collect_trading_metrics(metric_data["trading"])
            
            if "portfolio" in metric_data:
                await self.business_collector.collect_portfolio_metrics(metric_data["portfolio"])
            
            if "risk" in metric_data:
                await self.business_collector.collect_risk_metrics(metric_data["risk"])
                
        except Exception as e:
            self.logger.error(f"Failed to collect business metrics: {e}")
    
    def register_custom_metric(self, name: str, metric_type: MetricType, 
                             description: str, unit: str = "", 
                             calculator: Callable = None) -> bool:
        """Register a custom metric"""
        definition = MetricDefinition(
            name=name,
            metric_type=metric_type,
            category=MetricCategory.CUSTOM,
            description=description,
            unit=unit
        )
        
        return self.custom_registry.register_custom_metric(definition, calculator)
    
    def collect_metric(self, name: str, value: Union[float, int], 
                      tags: Dict[str, str] = None) -> bool:
        """Collect a metric value"""
        return self.collector.collect_metric(name, value, tags)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        try:
            summary = {
                "collection_stats": self.collector.get_collection_stats(),
                "registered_metrics": len(self.collector.metric_definitions),
                "custom_metrics": len(self.custom_registry.custom_metrics),
                "active_aggregations": len(self.aggregator.aggregation_tasks),
                "system_status": "running" if self.is_running else "stopped",
                "timestamp": datetime.now()
            }
            
            # Add recent metric values for key metrics
            key_metrics = ["trading.orders.total", "portfolio.value.total", "system.cpu.usage"]
            recent_values = {}
            
            for metric_name in key_metrics:
                values = self.collector.get_metric_values(metric_name)
                if values:
                    recent_values[metric_name] = {
                        "latest_value": values[-1].value,
                        "latest_timestamp": values[-1].timestamp,
                        "count_last_hour": len([v for v in values 
                                              if v.timestamp > datetime.now() - timedelta(hours=1)])
                    }
            
            summary["recent_values"] = recent_values
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get metrics summary: {e}")
            return {"error": str(e)}


# Example usage and testing
async def example_usage():
    """Example usage of the Metrics Collection System"""
    
    # Initialize the metrics system
    metrics_system = MetricsCollectionSystem()
    
    print("Starting metrics collection system...")
    await metrics_system.start()
    
    # Register custom metrics
    metrics_system.register_custom_metric(
        name="strategy.sharpe_ratio",
        metric_type=MetricType.GAUGE,
        description="Strategy Sharpe ratio",
        unit="ratio",
        calculator=lambda returns, risk_free_rate=0.02: (statistics.mean(returns) - risk_free_rate) / statistics.stdev(returns) if len(returns) > 1 else 0
    )
    
    # Simulate collecting business metrics
    print("Collecting business metrics...")
    business_data = {
        "trading": {
            "total_orders": 150,
            "filled_orders": 142,
            "daily_volume": 1250000.0
        },
        "portfolio": {
            "total_value": 5000000.0,
            "realized_pnl": 25000.0,
            "unrealized_pnl": -5000.0
        },
        "risk": {
            "daily_var": 50000.0,
            "total_exposure": 4800000.0
        }
    }
    
    await metrics_system.collect_business_metrics(business_data)
    
    # Collect custom metrics
    sample_returns = [0.01, 0.02, -0.005, 0.015, 0.008]
    metrics_system.custom_registry.collect_custom_metric("strategy.sharpe_ratio", sample_returns)
    
    # Wait for some aggregation
    await asyncio.sleep(2)
    
    # Get metrics summary
    summary = metrics_system.get_metrics_summary()
    
    print(f"\n=== Metrics Collection Summary ===")
    print(f"System Status: {summary['system_status']}")
    print(f"Total Metrics Collected: {summary['collection_stats']['total_metrics_collected']}")
    print(f"Registered Metrics: {summary['registered_metrics']}")
    print(f"Custom Metrics: {summary['custom_metrics']}")
    print(f"Active Aggregations: {summary['active_aggregations']}")
    
    if summary.get("recent_values"):
        print(f"\n=== Recent Metric Values ===")
        for metric_name, data in summary["recent_values"].items():
            print(f"{metric_name}: {data['latest_value']} (at {data['latest_timestamp']})")
    
    # Demonstrate aggregation
    print(f"\n=== Metric Aggregation Example ===")
    aggregated = metrics_system.collector.aggregate_metrics("trading.orders.total", 60)
    if aggregated:
        print(f"Orders Total - Count: {aggregated.count}, Avg: {aggregated.avg_value:.2f}")
    
    # Stop the system
    print("\nStopping metrics collection system...")
    await metrics_system.stop()


if __name__ == "__main__":
    asyncio.run(example_usage())