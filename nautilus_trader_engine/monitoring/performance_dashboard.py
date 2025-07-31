"""
Performance Analytics Dashboard
Real-time performance visualization, historical performance analysis,
capacity planning and forecasting, and performance optimization recommendations.
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import statistics
import threading
from abc import ABC, abstractmethod

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    stats = None


class MetricType(Enum):
    """Types of performance metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"
    RATE = "rate"


class TimeRange(Enum):
    """Time range options for dashboard views"""
    LAST_5_MINUTES = "5m"
    LAST_15_MINUTES = "15m"
    LAST_HOUR = "1h"
    LAST_6_HOURS = "6h"
    LAST_24_HOURS = "24h"
    LAST_7_DAYS = "7d"
    LAST_30_DAYS = "30d"


class ChartType(Enum):
    """Chart types for visualization"""
    LINE = "line"
    BAR = "bar"
    AREA = "area"
    SCATTER = "scatter"
    HEATMAP = "heatmap"
    PIE = "pie"
    GAUGE = "gauge"


@dataclass
class MetricPoint:
    """Single metric data point"""
    timestamp: datetime
    value: float
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricSeries:
    """Time series of metric data"""
    name: str
    metric_type: MetricType
    points: List[MetricPoint] = field(default_factory=list)
    unit: str = ""
    description: str = ""
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class ChartConfig:
    """Chart configuration"""
    chart_id: str
    title: str
    chart_type: ChartType
    metrics: List[str]
    time_range: TimeRange = TimeRange.LAST_HOUR
    refresh_interval: int = 30  # seconds
    y_axis_label: str = ""
    x_axis_label: str = "Time"
    show_legend: bool = True
    height: int = 400
    width: int = 800
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DashboardWidget:
    """Dashboard widget configuration"""
    widget_id: str
    title: str
    widget_type: str  # "chart", "metric", "alert", "table"
    config: Dict[str, Any] = field(default_factory=dict)
    position: Dict[str, int] = field(default_factory=lambda: {"x": 0, "y": 0, "width": 6, "height": 4})
    refresh_interval: int = 30


@dataclass
class Dashboard:
    """Dashboard configuration"""
    dashboard_id: str
    name: str
    description: str
    widgets: List[DashboardWidget] = field(default_factory=list)
    layout: str = "grid"  # "grid", "flex"
    auto_refresh: bool = True
    refresh_interval: int = 30
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class PerformanceMetrics:
    """Performance metrics summary"""
    timestamp: datetime
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    network_io: float = 0.0
    
    # Application metrics
    request_rate: float = 0.0
    response_time_avg: float = 0.0
    response_time_p95: float = 0.0
    response_time_p99: float = 0.0
    error_rate: float = 0.0
    
    # Trading metrics
    order_rate: float = 0.0
    fill_rate: float = 0.0
    latency_avg: float = 0.0
    latency_p95: float = 0.0
    
    # Custom metrics
    custom_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class CapacityForecast:
    """Capacity planning forecast"""
    metric_name: str
    current_value: float
    predicted_values: List[Tuple[datetime, float]]
    capacity_limit: float
    time_to_limit: Optional[datetime] = None
    confidence_interval: Tuple[float, float] = (0.0, 0.0)
    trend: str = "stable"  # "increasing", "decreasing", "stable"
    recommendation: str = ""


@dataclass
class OptimizationRecommendation:
    """Performance optimization recommendation"""
    recommendation_id: str
    title: str
    description: str
    category: str  # "performance", "capacity", "cost", "reliability"
    priority: str  # "low", "medium", "high", "critical"
    impact: str  # "low", "medium", "high"
    effort: str  # "low", "medium", "high"
    
    # Metrics
    affected_metrics: List[str] = field(default_factory=list)
    expected_improvement: Dict[str, float] = field(default_factory=dict)
    
    # Implementation
    action_items: List[str] = field(default_factory=list)
    estimated_time: str = ""
    
    # Context
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "open"  # "open", "in_progress", "completed", "dismissed"


class MetricCollector:
    """Collects and stores performance metrics"""
    
    def __init__(self, max_points_per_series: int = 10000):
        self.logger = logging.getLogger(__name__)
        self.max_points_per_series = max_points_per_series
        self.metrics: Dict[str, MetricSeries] = {}
        self._lock = threading.Lock()
    
    def add_metric_point(self, metric_name: str, value: float, 
                        timestamp: Optional[datetime] = None,
                        tags: Dict[str, str] = None,
                        metric_type: MetricType = MetricType.GAUGE,
                        unit: str = "",
                        description: str = ""):
        """Add a metric data point"""
        try:
            if timestamp is None:
                timestamp = datetime.now()
            
            point = MetricPoint(
                timestamp=timestamp,
                value=value,
                tags=tags or {},
            )
            
            with self._lock:
                if metric_name not in self.metrics:
                    self.metrics[metric_name] = MetricSeries(
                        name=metric_name,
                        metric_type=metric_type,
                        unit=unit,
                        description=description,
                        tags=tags or {}
                    )
                
                series = self.metrics[metric_name]
                series.points.append(point)
                
                # Maintain size limit
                if len(series.points) > self.max_points_per_series:
                    series.points = series.points[-self.max_points_per_series:]
                    
        except Exception as e:
            self.logger.error(f"Failed to add metric point for {metric_name}: {e}")
    
    def get_metric_series(self, metric_name: str, 
                         time_range: TimeRange = TimeRange.LAST_HOUR,
                         tags_filter: Dict[str, str] = None) -> Optional[MetricSeries]:
        """Get metric series with optional filtering"""
        try:
            with self._lock:
                if metric_name not in self.metrics:
                    return None
                
                series = self.metrics[metric_name]
                
                # Apply time range filter
                cutoff_time = self._get_cutoff_time(time_range)
                filtered_points = [
                    point for point in series.points 
                    if point.timestamp >= cutoff_time
                ]
                
                # Apply tags filter
                if tags_filter:
                    filtered_points = [
                        point for point in filtered_points
                        if all(point.tags.get(k) == v for k, v in tags_filter.items())
                    ]
                
                # Create filtered series
                filtered_series = MetricSeries(
                    name=series.name,
                    metric_type=series.metric_type,
                    points=filtered_points,
                    unit=series.unit,
                    description=series.description,
                    tags=series.tags
                )
                
                return filtered_series
                
        except Exception as e:
            self.logger.error(f"Failed to get metric series for {metric_name}: {e}")
            return None
    
    def get_available_metrics(self) -> List[str]:
        """Get list of available metric names"""
        with self._lock:
            return list(self.metrics.keys())
    
    def get_metric_statistics(self, metric_name: str, 
                            time_range: TimeRange = TimeRange.LAST_HOUR) -> Dict[str, float]:
        """Get statistical summary of a metric"""
        try:
            series = self.get_metric_series(metric_name, time_range)
            if not series or not series.points:
                return {}
            
            values = [point.value for point in series.points]
            
            stats = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "std": statistics.stdev(values) if len(values) > 1 else 0.0
            }
            
            # Add percentiles if we have enough data
            if len(values) >= 10:
                sorted_values = sorted(values)
                stats.update({
                    "p50": sorted_values[int(len(values) * 0.5)],
                    "p90": sorted_values[int(len(values) * 0.9)],
                    "p95": sorted_values[int(len(values) * 0.95)],
                    "p99": sorted_values[int(len(values) * 0.99)]
                })
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get statistics for {metric_name}: {e}")
            return {}
    
    def _get_cutoff_time(self, time_range: TimeRange) -> datetime:
        """Get cutoff time for time range"""
        now = datetime.now()
        
        if time_range == TimeRange.LAST_5_MINUTES:
            return now - timedelta(minutes=5)
        elif time_range == TimeRange.LAST_15_MINUTES:
            return now - timedelta(minutes=15)
        elif time_range == TimeRange.LAST_HOUR:
            return now - timedelta(hours=1)
        elif time_range == TimeRange.LAST_6_HOURS:
            return now - timedelta(hours=6)
        elif time_range == TimeRange.LAST_24_HOURS:
            return now - timedelta(hours=24)
        elif time_range == TimeRange.LAST_7_DAYS:
            return now - timedelta(days=7)
        elif time_range == TimeRange.LAST_30_DAYS:
            return now - timedelta(days=30)
        else:
            return now - timedelta(hours=1)


class CapacityPlanner:
    """Performs capacity planning and forecasting"""
    
    def __init__(self, metric_collector: MetricCollector):
        self.metric_collector = metric_collector
        self.logger = logging.getLogger(__name__)
    
    async def generate_capacity_forecast(self, metric_name: str,
                                       forecast_days: int = 30,
                                       capacity_limit: Optional[float] = None) -> Optional[CapacityForecast]:
        """Generate capacity forecast for a metric"""
        try:
            # Get historical data
            series = self.metric_collector.get_metric_series(
                metric_name, TimeRange.LAST_30_DAYS
            )
            
            if not series or len(series.points) < 10:
                return None
            
            # Extract values and timestamps
            timestamps = [point.timestamp for point in series.points]
            values = [point.value for point in series.points]
            
            # Convert timestamps to numeric values for regression
            base_time = timestamps[0]
            x_values = [(ts - base_time).total_seconds() for ts in timestamps]
            
            # Perform linear regression for trend analysis
            if NUMPY_AVAILABLE:
                slope, intercept = np.polyfit(x_values, values, 1)
                r_squared = np.corrcoef(x_values, values)[0, 1] ** 2
            else:
                # Simple linear regression
                n = len(values)
                sum_x = sum(x_values)
                sum_y = sum(values)
                sum_xy = sum(x_values[i] * values[i] for i in range(n))
                sum_x2 = sum(x ** 2 for x in x_values)
                
                slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
                intercept = (sum_y - slope * sum_x) / n
                r_squared = 0.5  # Rough estimate
            
            # Generate predictions
            current_time = datetime.now()
            current_value = values[-1]
            predicted_values = []
            
            for days in range(1, forecast_days + 1):
                future_time = current_time + timedelta(days=days)
                future_seconds = (future_time - base_time).total_seconds()
                predicted_value = slope * future_seconds + intercept
                predicted_values.append((future_time, max(0, predicted_value)))
            
            # Determine trend - use relative threshold based on data range and time span
            value_range = max(values) - min(values)
            time_span = max(x_values) - min(x_values)
            
            # Calculate relative threshold: if slope would change value by less than 5% of range over time span
            if value_range > 0 and time_span > 0:
                relative_threshold = (value_range * 0.05) / time_span
            else:
                relative_threshold = 0.001
            
            if abs(slope) < relative_threshold:
                trend = "stable"
            elif slope > 0:
                trend = "increasing"
            else:
                trend = "decreasing"
            
            # Calculate time to capacity limit
            time_to_limit = None
            if capacity_limit and slope > 0:
                seconds_to_limit = (capacity_limit - current_value) / slope
                if seconds_to_limit > 0:
                    time_to_limit = current_time + timedelta(seconds=seconds_to_limit)
            
            # Generate recommendation
            recommendation = self._generate_capacity_recommendation(
                metric_name, trend, slope, capacity_limit, time_to_limit
            )
            
            # Calculate confidence interval (simplified)
            std_error = statistics.stdev(values) if len(values) > 1 else 0
            confidence_interval = (
                current_value - 2 * std_error,
                current_value + 2 * std_error
            )
            
            return CapacityForecast(
                metric_name=metric_name,
                current_value=current_value,
                predicted_values=predicted_values,
                capacity_limit=capacity_limit or float('inf'),
                time_to_limit=time_to_limit,
                confidence_interval=confidence_interval,
                trend=trend,
                recommendation=recommendation
            )
            
        except Exception as e:
            self.logger.error(f"Failed to generate capacity forecast for {metric_name}: {e}")
            return None
    
    def _generate_capacity_recommendation(self, metric_name: str, trend: str, 
                                        slope: float, capacity_limit: Optional[float],
                                        time_to_limit: Optional[datetime]) -> str:
        """Generate capacity planning recommendation"""
        if trend == "stable":
            return f"{metric_name} is stable. No immediate capacity concerns."
        
        elif trend == "increasing":
            if time_to_limit and time_to_limit < datetime.now() + timedelta(days=30):
                return f"{metric_name} will reach capacity limit by {time_to_limit.strftime('%Y-%m-%d')}. Immediate action required."
            elif time_to_limit and time_to_limit < datetime.now() + timedelta(days=90):
                return f"{metric_name} will reach capacity limit by {time_to_limit.strftime('%Y-%m-%d')}. Plan capacity expansion."
            else:
                return f"{metric_name} is increasing. Monitor trend and plan for future capacity needs."
        
        else:  # decreasing
            return f"{metric_name} is decreasing. Consider optimizing resource allocation."


class OptimizationEngine:
    """Generates performance optimization recommendations"""
    
    def __init__(self, metric_collector: MetricCollector):
        self.metric_collector = metric_collector
        self.logger = logging.getLogger(__name__)
        self.recommendation_rules = self._load_optimization_rules()
    
    async def generate_recommendations(self, 
                                     time_range: TimeRange = TimeRange.LAST_24_HOURS) -> List[OptimizationRecommendation]:
        """Generate performance optimization recommendations"""
        try:
            recommendations = []
            
            # Get current performance metrics
            metrics = self.metric_collector.get_available_metrics()
            
            for metric_name in metrics:
                stats = self.metric_collector.get_metric_statistics(metric_name, time_range)
                if not stats:
                    continue
                
                # Check for performance issues
                metric_recommendations = await self._analyze_metric_performance(metric_name, stats)
                recommendations.extend(metric_recommendations)
            
            # Cross-metric analysis
            cross_metric_recommendations = await self._analyze_cross_metric_patterns(metrics, time_range)
            recommendations.extend(cross_metric_recommendations)
            
            # Sort by priority and impact
            recommendations.sort(key=lambda r: (
                self._priority_score(r.priority),
                self._impact_score(r.impact)
            ), reverse=True)
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Failed to generate optimization recommendations: {e}")
            return []
    
    async def _analyze_metric_performance(self, metric_name: str, 
                                        stats: Dict[str, float]) -> List[OptimizationRecommendation]:
        """Analyze individual metric performance"""
        recommendations = []
        
        try:
            # High CPU usage
            if "cpu" in metric_name.lower() and stats.get("mean", 0) > 80:
                recommendations.append(OptimizationRecommendation(
                    recommendation_id=f"cpu_high_{int(time.time())}",
                    title="High CPU Usage Detected",
                    description=f"CPU usage averaging {stats['mean']:.1f}% over the selected period",
                    category="performance",
                    priority="high",
                    impact="high",
                    effort="medium",
                    affected_metrics=[metric_name],
                    expected_improvement={"cpu_usage": -20.0, "response_time": -15.0},
                    action_items=[
                        "Profile application for CPU-intensive operations",
                        "Consider horizontal scaling or load balancing",
                        "Optimize algorithms and database queries",
                        "Review garbage collection settings"
                    ],
                    estimated_time="2-4 hours"
                ))
            
            # High memory usage
            elif "memory" in metric_name.lower() and stats.get("mean", 0) > 85:
                recommendations.append(OptimizationRecommendation(
                    recommendation_id=f"memory_high_{int(time.time())}",
                    title="High Memory Usage Detected",
                    description=f"Memory usage averaging {stats['mean']:.1f}% over the selected period",
                    category="performance",
                    priority="high",
                    impact="high",
                    effort="medium",
                    affected_metrics=[metric_name],
                    expected_improvement={"memory_usage": -25.0, "gc_time": -30.0},
                    action_items=[
                        "Investigate memory leaks in application code",
                        "Optimize data structures and caching",
                        "Consider increasing memory allocation",
                        "Review object lifecycle management"
                    ],
                    estimated_time="4-8 hours"
                ))
            
            # High response time
            elif "response_time" in metric_name.lower() or "latency" in metric_name.lower():
                if stats.get("p95", 0) > 1000:  # > 1 second
                    recommendations.append(OptimizationRecommendation(
                        recommendation_id=f"latency_high_{int(time.time())}",
                        title="High Response Time Detected",
                        description=f"95th percentile response time is {stats['p95']:.0f}ms",
                        category="performance",
                        priority="high",
                        impact="high",
                        effort="high",
                        affected_metrics=[metric_name],
                        expected_improvement={"response_time": -40.0, "user_satisfaction": 20.0},
                        action_items=[
                            "Optimize database queries and indexes",
                            "Implement caching strategies",
                            "Review network connectivity and CDN usage",
                            "Profile application bottlenecks"
                        ],
                        estimated_time="1-2 days"
                    ))
            
            # High error rate
            elif "error" in metric_name.lower() and stats.get("mean", 0) > 5:
                recommendations.append(OptimizationRecommendation(
                    recommendation_id=f"error_rate_high_{int(time.time())}",
                    title="High Error Rate Detected",
                    description=f"Error rate averaging {stats['mean']:.1f}% over the selected period",
                    category="reliability",
                    priority="critical",
                    impact="high",
                    effort="high",
                    affected_metrics=[metric_name],
                    expected_improvement={"error_rate": -80.0, "availability": 5.0},
                    action_items=[
                        "Investigate root causes of errors",
                        "Improve error handling and retry logic",
                        "Review input validation and data quality",
                        "Enhance monitoring and alerting"
                    ],
                    estimated_time="1-3 days"
                ))
            
            # High variability (unstable performance)
            if stats.get("std", 0) > stats.get("mean", 0) * 0.5:  # High coefficient of variation
                recommendations.append(OptimizationRecommendation(
                    recommendation_id=f"variability_high_{int(time.time())}",
                    title="High Performance Variability",
                    description=f"High variability in {metric_name} (std: {stats['std']:.2f})",
                    category="performance",
                    priority="medium",
                    impact="medium",
                    effort="medium",
                    affected_metrics=[metric_name],
                    expected_improvement={"stability": 30.0, "predictability": 25.0},
                    action_items=[
                        "Investigate causes of performance spikes",
                        "Implement rate limiting and load balancing",
                        "Review resource allocation and scaling policies",
                        "Optimize for consistent performance"
                    ],
                    estimated_time="4-6 hours"
                ))
            
        except Exception as e:
            self.logger.error(f"Failed to analyze metric {metric_name}: {e}")
        
        return recommendations
    
    async def _analyze_cross_metric_patterns(self, metrics: List[str], 
                                           time_range: TimeRange) -> List[OptimizationRecommendation]:
        """Analyze patterns across multiple metrics"""
        recommendations = []
        
        try:
            # Look for correlated performance issues
            cpu_metrics = [m for m in metrics if "cpu" in m.lower()]
            memory_metrics = [m for m in metrics if "memory" in m.lower()]
            latency_metrics = [m for m in metrics if "latency" in m.lower() or "response_time" in m.lower()]
            
            # Check for resource exhaustion pattern
            high_cpu = any(
                self.metric_collector.get_metric_statistics(m, time_range).get("mean", 0) > 80
                for m in cpu_metrics
            )
            high_memory = any(
                self.metric_collector.get_metric_statistics(m, time_range).get("mean", 0) > 85
                for m in memory_metrics
            )
            high_latency = any(
                self.metric_collector.get_metric_statistics(m, time_range).get("p95", 0) > 1000
                for m in latency_metrics
            )
            
            if high_cpu and high_memory and high_latency:
                recommendations.append(OptimizationRecommendation(
                    recommendation_id=f"resource_exhaustion_{int(time.time())}",
                    title="System Resource Exhaustion Detected",
                    description="Multiple resource constraints detected simultaneously",
                    category="capacity",
                    priority="critical",
                    impact="high",
                    effort="high",
                    affected_metrics=cpu_metrics + memory_metrics + latency_metrics,
                    expected_improvement={
                        "overall_performance": 50.0,
                        "system_stability": 40.0,
                        "user_experience": 35.0
                    },
                    action_items=[
                        "Immediate capacity scaling required",
                        "Review and optimize resource-intensive operations",
                        "Implement load balancing and auto-scaling",
                        "Consider architectural improvements"
                    ],
                    estimated_time="1-2 weeks"
                ))
            
        except Exception as e:
            self.logger.error(f"Failed to analyze cross-metric patterns: {e}")
        
        return recommendations
    
    def _priority_score(self, priority: str) -> int:
        """Convert priority to numeric score"""
        scores = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        return scores.get(priority, 0)
    
    def _impact_score(self, impact: str) -> int:
        """Convert impact to numeric score"""
        scores = {"high": 3, "medium": 2, "low": 1}
        return scores.get(impact, 0)
    
    def _load_optimization_rules(self) -> Dict[str, Any]:
        """Load optimization rules (placeholder for external configuration)"""
        return {
            "cpu_threshold": 80.0,
            "memory_threshold": 85.0,
            "latency_threshold": 1000.0,
            "error_rate_threshold": 5.0
        }


class DashboardRenderer:
    """Renders dashboard data for visualization"""
    
    def __init__(self, metric_collector: MetricCollector):
        self.metric_collector = metric_collector
        self.logger = logging.getLogger(__name__)
    
    async def render_chart_data(self, chart_config: ChartConfig) -> Dict[str, Any]:
        """Render chart data for visualization"""
        try:
            chart_data = {
                "chart_id": chart_config.chart_id,
                "title": chart_config.title,
                "type": chart_config.chart_type.value,
                "data": {},
                "options": chart_config.options,
                "timestamp": datetime.now().isoformat()
            }
            
            # Get data for each metric
            datasets = []
            for metric_name in chart_config.metrics:
                series = self.metric_collector.get_metric_series(
                    metric_name, chart_config.time_range
                )
                
                if series and series.points:
                    dataset = {
                        "label": metric_name,
                        "data": [
                            {
                                "x": point.timestamp.isoformat(),
                                "y": point.value
                            }
                            for point in series.points
                        ],
                        "unit": series.unit
                    }
                    datasets.append(dataset)
            
            chart_data["data"] = {
                "datasets": datasets,
                "labels": [point["x"] for point in datasets[0]["data"]] if datasets else []
            }
            
            return chart_data
            
        except Exception as e:
            self.logger.error(f"Failed to render chart data for {chart_config.chart_id}: {e}")
            return {"error": str(e)}
    
    async def render_metric_widget(self, metric_name: str, 
                                 time_range: TimeRange = TimeRange.LAST_HOUR) -> Dict[str, Any]:
        """Render metric widget data"""
        try:
            stats = self.metric_collector.get_metric_statistics(metric_name, time_range)
            series = self.metric_collector.get_metric_series(metric_name, time_range)
            
            if not stats or not series:
                return {"error": f"No data available for {metric_name}"}
            
            # Calculate trend
            if len(series.points) >= 2:
                recent_avg = statistics.mean([p.value for p in series.points[-10:]])
                older_avg = statistics.mean([p.value for p in series.points[:10]])
                trend = "up" if recent_avg > older_avg else "down" if recent_avg < older_avg else "stable"
                trend_percentage = ((recent_avg - older_avg) / older_avg * 100) if older_avg != 0 else 0
            else:
                trend = "stable"
                trend_percentage = 0
            
            widget_data = {
                "metric_name": metric_name,
                "current_value": series.points[-1].value if series.points else 0,
                "unit": series.unit,
                "statistics": stats,
                "trend": trend,
                "trend_percentage": trend_percentage,
                "timestamp": datetime.now().isoformat()
            }
            
            return widget_data
            
        except Exception as e:
            self.logger.error(f"Failed to render metric widget for {metric_name}: {e}")
            return {"error": str(e)}


class PerformanceAnalyticsDashboard:
    """Main performance analytics dashboard system"""
    
    def __init__(self, max_points_per_series: int = 10000):
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.metric_collector = MetricCollector(max_points_per_series)
        self.capacity_planner = CapacityPlanner(self.metric_collector)
        self.optimization_engine = OptimizationEngine(self.metric_collector)
        self.dashboard_renderer = DashboardRenderer(self.metric_collector)
        
        # Dashboard storage
        self.dashboards: Dict[str, Dashboard] = {}
        self.default_dashboard_id = "main"
        
        # Background tasks
        self._background_tasks = []
        self._running = False
        
        # Initialize default dashboard
        self._create_default_dashboard()
    
    def _create_default_dashboard(self):
        """Create default dashboard with common widgets"""
        try:
            # System performance widgets
            system_widgets = [
                DashboardWidget(
                    widget_id="cpu_usage",
                    title="CPU Usage",
                    widget_type="chart",
                    config={
                        "chart_type": ChartType.LINE.value,
                        "metrics": ["system.cpu.usage"],
                        "time_range": TimeRange.LAST_HOUR.value,
                        "y_axis_label": "Percentage"
                    },
                    position={"x": 0, "y": 0, "width": 6, "height": 4}
                ),
                DashboardWidget(
                    widget_id="memory_usage",
                    title="Memory Usage",
                    widget_type="chart",
                    config={
                        "chart_type": ChartType.LINE.value,
                        "metrics": ["system.memory.usage"],
                        "time_range": TimeRange.LAST_HOUR.value,
                        "y_axis_label": "Percentage"
                    },
                    position={"x": 6, "y": 0, "width": 6, "height": 4}
                ),
                DashboardWidget(
                    widget_id="response_time",
                    title="Response Time",
                    widget_type="chart",
                    config={
                        "chart_type": ChartType.LINE.value,
                        "metrics": ["app.response_time.avg", "app.response_time.p95"],
                        "time_range": TimeRange.LAST_HOUR.value,
                        "y_axis_label": "Milliseconds"
                    },
                    position={"x": 0, "y": 4, "width": 8, "height": 4}
                ),
                DashboardWidget(
                    widget_id="error_rate",
                    title="Error Rate",
                    widget_type="metric",
                    config={
                        "metric_name": "app.error_rate",
                        "time_range": TimeRange.LAST_HOUR.value,
                        "format": "percentage"
                    },
                    position={"x": 8, "y": 4, "width": 4, "height": 4}
                )
            ]
            
            default_dashboard = Dashboard(
                dashboard_id=self.default_dashboard_id,
                name="System Performance",
                description="Main system performance dashboard",
                widgets=system_widgets
            )
            
            self.dashboards[self.default_dashboard_id] = default_dashboard
            
        except Exception as e:
            self.logger.error(f"Failed to create default dashboard: {e}")
    
    async def start(self):
        """Start the dashboard system"""
        try:
            self._running = True
            
            # Start background metric collection
            collection_task = asyncio.create_task(self._collect_system_metrics())
            self._background_tasks.append(collection_task)
            
            self.logger.info("Performance Analytics Dashboard started")
            
        except Exception as e:
            self.logger.error(f"Failed to start dashboard: {e}")
    
    async def stop(self):
        """Stop the dashboard system"""
        try:
            self._running = False
            
            # Cancel background tasks
            for task in self._background_tasks:
                task.cancel()
            
            # Wait for tasks to complete
            if self._background_tasks:
                await asyncio.gather(*self._background_tasks, return_exceptions=True)
            
            self.logger.info("Performance Analytics Dashboard stopped")
            
        except Exception as e:
            self.logger.error(f"Failed to stop dashboard: {e}")
    
    async def _collect_system_metrics(self):
        """Background task to collect system metrics"""
        while self._running:
            try:
                # Simulate system metrics collection
                import psutil
                
                # CPU metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                self.metric_collector.add_metric_point(
                    "system.cpu.usage", cpu_percent,
                    metric_type=MetricType.GAUGE, unit="%"
                )
                
                # Memory metrics
                memory = psutil.virtual_memory()
                self.metric_collector.add_metric_point(
                    "system.memory.usage", memory.percent,
                    metric_type=MetricType.GAUGE, unit="%"
                )
                
                # Disk metrics
                disk = psutil.disk_usage('/')
                disk_percent = (disk.used / disk.total) * 100
                self.metric_collector.add_metric_point(
                    "system.disk.usage", disk_percent,
                    metric_type=MetricType.GAUGE, unit="%"
                )
                
                # Network metrics
                network = psutil.net_io_counters()
                self.metric_collector.add_metric_point(
                    "system.network.bytes_sent", network.bytes_sent,
                    metric_type=MetricType.COUNTER, unit="bytes"
                )
                
                await asyncio.sleep(30)  # Collect every 30 seconds
                
            except ImportError:
                # psutil not available, use mock data
                import random
                
                self.metric_collector.add_metric_point(
                    "system.cpu.usage", random.uniform(20, 80),
                    metric_type=MetricType.GAUGE, unit="%"
                )
                self.metric_collector.add_metric_point(
                    "system.memory.usage", random.uniform(40, 90),
                    metric_type=MetricType.GAUGE, unit="%"
                )
                self.metric_collector.add_metric_point(
                    "app.response_time.avg", random.uniform(50, 200),
                    metric_type=MetricType.GAUGE, unit="ms"
                )
                self.metric_collector.add_metric_point(
                    "app.response_time.p95", random.uniform(100, 500),
                    metric_type=MetricType.GAUGE, unit="ms"
                )
                self.metric_collector.add_metric_point(
                    "app.error_rate", random.uniform(0, 5),
                    metric_type=MetricType.GAUGE, unit="%"
                )
                
                await asyncio.sleep(30)
                
            except Exception as e:
                self.logger.error(f"Failed to collect system metrics: {e}")
                await asyncio.sleep(60)  # Wait longer on error 
   # Dashboard Management Methods
    async def create_dashboard(self, dashboard: Dashboard) -> bool:
        """Create a new dashboard"""
        try:
            self.dashboards[dashboard.dashboard_id] = dashboard
            self.logger.info(f"Created dashboard: {dashboard.name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create dashboard: {e}")
            return False
    
    async def get_dashboard(self, dashboard_id: str) -> Optional[Dashboard]:
        """Get dashboard by ID"""
        return self.dashboards.get(dashboard_id)
    
    async def list_dashboards(self) -> List[Dashboard]:
        """List all dashboards"""
        return list(self.dashboards.values())
    
    async def delete_dashboard(self, dashboard_id: str) -> bool:
        """Delete a dashboard"""
        try:
            if dashboard_id in self.dashboards:
                del self.dashboards[dashboard_id]
                self.logger.info(f"Deleted dashboard: {dashboard_id}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to delete dashboard: {e}")
            return False
    
    # Data Access Methods
    async def get_dashboard_data(self, dashboard_id: str) -> Dict[str, Any]:
        """Get complete dashboard data for rendering"""
        try:
            dashboard = self.dashboards.get(dashboard_id)
            if not dashboard:
                return {"error": f"Dashboard {dashboard_id} not found"}
            
            dashboard_data = {
                "dashboard_id": dashboard.dashboard_id,
                "name": dashboard.name,
                "description": dashboard.description,
                "layout": dashboard.layout,
                "auto_refresh": dashboard.auto_refresh,
                "refresh_interval": dashboard.refresh_interval,
                "widgets": [],
                "timestamp": datetime.now().isoformat()
            }
            
            # Render each widget
            for widget in dashboard.widgets:
                widget_data = await self._render_widget(widget)
                dashboard_data["widgets"].append(widget_data)
            
            return dashboard_data
            
        except Exception as e:
            self.logger.error(f"Failed to get dashboard data: {e}")
            return {"error": str(e)}
    
    async def _render_widget(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Render individual widget data"""
        try:
            widget_data = {
                "widget_id": widget.widget_id,
                "title": widget.title,
                "type": widget.widget_type,
                "position": widget.position,
                "config": widget.config,
                "data": {},
                "timestamp": datetime.now().isoformat()
            }
            
            if widget.widget_type == "chart":
                # Create chart config from widget config
                chart_config = ChartConfig(
                    chart_id=widget.widget_id,
                    title=widget.title,
                    chart_type=ChartType(widget.config.get("chart_type", "line")),
                    metrics=widget.config.get("metrics", []),
                    time_range=TimeRange(widget.config.get("time_range", "1h"))
                )
                widget_data["data"] = await self.dashboard_renderer.render_chart_data(chart_config)
                
            elif widget.widget_type == "metric":
                metric_name = widget.config.get("metric_name")
                time_range = TimeRange(widget.config.get("time_range", "1h"))
                if metric_name:
                    widget_data["data"] = await self.dashboard_renderer.render_metric_widget(
                        metric_name, time_range
                    )
            
            return widget_data
            
        except Exception as e:
            self.logger.error(f"Failed to render widget {widget.widget_id}: {e}")
            return {"error": str(e)}
    
    # Analytics Methods
    async def get_capacity_forecast(self, metric_name: str, 
                                  forecast_days: int = 30) -> Optional[CapacityForecast]:
        """Get capacity forecast for a metric"""
        return await self.capacity_planner.generate_capacity_forecast(
            metric_name, forecast_days
        )
    
    async def get_optimization_recommendations(self, 
                                            time_range: TimeRange = TimeRange.LAST_24_HOURS) -> List[OptimizationRecommendation]:
        """Get performance optimization recommendations"""
        return await self.optimization_engine.generate_recommendations(time_range)
    
    async def get_system_overview(self) -> Dict[str, Any]:
        """Get system performance overview"""
        try:
            overview = {
                "timestamp": datetime.now().isoformat(),
                "metrics_count": len(self.metric_collector.get_available_metrics()),
                "dashboards_count": len(self.dashboards),
                "system_health": "healthy",
                "key_metrics": {}
            }
            
            # Get key system metrics
            key_metrics = [
                "system.cpu.usage",
                "system.memory.usage", 
                "app.response_time.avg",
                "app.error_rate"
            ]
            
            for metric_name in key_metrics:
                stats = self.metric_collector.get_metric_statistics(
                    metric_name, TimeRange.LAST_HOUR
                )
                if stats:
                    overview["key_metrics"][metric_name] = {
                        "current": stats.get("mean", 0),
                        "trend": "stable"  # Simplified
                    }
            
            # Determine overall system health
            cpu_usage = overview["key_metrics"].get("system.cpu.usage", {}).get("current", 0)
            memory_usage = overview["key_metrics"].get("system.memory.usage", {}).get("current", 0)
            error_rate = overview["key_metrics"].get("app.error_rate", {}).get("current", 0)
            
            if cpu_usage > 90 or memory_usage > 95 or error_rate > 10:
                overview["system_health"] = "critical"
            elif cpu_usage > 80 or memory_usage > 85 or error_rate > 5:
                overview["system_health"] = "warning"
            
            return overview
            
        except Exception as e:
            self.logger.error(f"Failed to get system overview: {e}")
            return {"error": str(e)}
    
    # Utility Methods
    def add_metric(self, metric_name: str, value: float, 
                  timestamp: Optional[datetime] = None,
                  tags: Dict[str, str] = None,
                  metric_type: MetricType = MetricType.GAUGE,
                  unit: str = ""):
        """Add a metric data point"""
        self.metric_collector.add_metric_point(
            metric_name, value, timestamp, tags, metric_type, unit
        )
    
    def get_available_metrics(self) -> List[str]:
        """Get list of available metrics"""
        return self.metric_collector.get_available_metrics()
    
    async def export_dashboard_config(self, dashboard_id: str) -> Optional[Dict[str, Any]]:
        """Export dashboard configuration"""
        dashboard = self.dashboards.get(dashboard_id)
        if dashboard:
            return asdict(dashboard)
        return None
    
    async def import_dashboard_config(self, config: Dict[str, Any]) -> bool:
        """Import dashboard configuration"""
        try:
            # Convert widgets
            widgets = []
            for widget_config in config.get("widgets", []):
                widget = DashboardWidget(**widget_config)
                widgets.append(widget)
            
            # Create dashboard
            dashboard = Dashboard(
                dashboard_id=config["dashboard_id"],
                name=config["name"],
                description=config["description"],
                widgets=widgets,
                layout=config.get("layout", "grid"),
                auto_refresh=config.get("auto_refresh", True),
                refresh_interval=config.get("refresh_interval", 30)
            )
            
            return await self.create_dashboard(dashboard)
            
        except Exception as e:
            self.logger.error(f"Failed to import dashboard config: {e}")
            return False


# Example usage and testing
async def example_usage():
    """Example usage of the Performance Analytics Dashboard"""
    
    # Initialize dashboard
    dashboard = PerformanceAnalyticsDashboard()
    
    print("=== Performance Analytics Dashboard Demo ===")
    
    # Start the dashboard
    await dashboard.start()
    
    # Add some custom metrics
    import random
    import time
    
    print("Adding custom metrics...")
    for i in range(50):
        # Trading metrics
        dashboard.add_metric(
            "trading.order_rate", 
            random.uniform(100, 500),
            metric_type=MetricType.GAUGE,
            unit="orders/sec"
        )
        
        dashboard.add_metric(
            "trading.latency",
            random.uniform(10, 100),
            metric_type=MetricType.GAUGE,
            unit="ms"
        )
        
        dashboard.add_metric(
            "trading.fill_rate",
            random.uniform(85, 99),
            metric_type=MetricType.GAUGE,
            unit="%"
        )
        
        # Wait a bit between metrics
        await asyncio.sleep(0.1)
    
    # Wait for some system metrics to be collected
    print("Collecting system metrics...")
    await asyncio.sleep(5)
    
    # Get system overview
    overview = await dashboard.get_system_overview()
    print(f"\n=== System Overview ===")
    print(f"System Health: {overview['system_health']}")
    print(f"Metrics Count: {overview['metrics_count']}")
    print(f"Dashboards Count: {overview['dashboards_count']}")
    
    # Show key metrics
    print(f"\n=== Key Metrics ===")
    for metric_name, data in overview.get("key_metrics", {}).items():
        print(f"{metric_name}: {data['current']:.2f}")
    
    # Get available metrics
    available_metrics = dashboard.get_available_metrics()
    print(f"\n=== Available Metrics ({len(available_metrics)}) ===")
    for metric in available_metrics[:10]:  # Show first 10
        stats = dashboard.metric_collector.get_metric_statistics(metric)
        if stats:
            print(f"- {metric}: avg={stats.get('mean', 0):.2f}, count={stats.get('count', 0)}")
    
    # Get dashboard data
    dashboard_data = await dashboard.get_dashboard_data("main")
    print(f"\n=== Dashboard Data ===")
    print(f"Dashboard: {dashboard_data.get('name', 'Unknown')}")
    print(f"Widgets: {len(dashboard_data.get('widgets', []))}")
    
    # Generate capacity forecast
    print(f"\n=== Capacity Forecast ===")
    forecast = await dashboard.get_capacity_forecast("system.cpu.usage", 30)
    if forecast:
        print(f"Metric: {forecast.metric_name}")
        print(f"Current Value: {forecast.current_value:.2f}")
        print(f"Trend: {forecast.trend}")
        print(f"Recommendation: {forecast.recommendation}")
    
    # Generate optimization recommendations
    print(f"\n=== Optimization Recommendations ===")
    recommendations = await dashboard.get_optimization_recommendations()
    print(f"Found {len(recommendations)} recommendations")
    
    for rec in recommendations[:3]:  # Show top 3
        print(f"\n- {rec.title}")
        print(f"  Priority: {rec.priority}, Impact: {rec.impact}")
        print(f"  Category: {rec.category}")
        print(f"  Actions: {len(rec.action_items)} items")
    
    # Create custom dashboard
    print(f"\n=== Creating Custom Dashboard ===")
    
    trading_widgets = [
        DashboardWidget(
            widget_id="trading_overview",
            title="Trading Overview",
            widget_type="chart",
            config={
                "chart_type": ChartType.LINE.value,
                "metrics": ["trading.order_rate", "trading.fill_rate"],
                "time_range": TimeRange.LAST_HOUR.value
            }
        ),
        DashboardWidget(
            widget_id="trading_latency",
            title="Trading Latency",
            widget_type="metric",
            config={
                "metric_name": "trading.latency",
                "time_range": TimeRange.LAST_HOUR.value
            }
        )
    ]
    
    trading_dashboard = Dashboard(
        dashboard_id="trading",
        name="Trading Performance",
        description="Trading system performance metrics",
        widgets=trading_widgets
    )
    
    await dashboard.create_dashboard(trading_dashboard)
    
    # List all dashboards
    dashboards = await dashboard.list_dashboards()
    print(f"Total dashboards: {len(dashboards)}")
    for db in dashboards:
        print(f"- {db.name} ({db.dashboard_id})")
    
    # Stop the dashboard
    await dashboard.stop()
    print("\nDashboard demo completed!")


if __name__ == "__main__":
    asyncio.run(example_usage())