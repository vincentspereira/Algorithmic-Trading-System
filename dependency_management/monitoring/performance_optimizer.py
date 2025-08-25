"""
Performance Optimization System for Dependency Management.
Tracks performance baselines, analyzes resource usage, and provides optimization recommendations.
"""

import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import psutil
import numpy as np
from prometheus_client import Gauge
from monitoring.monitoring_infrastructure import monitoring

# Performance metrics
PERFORMANCE_BASELINE = Gauge(
    'dependency_performance_baseline',
    'Baseline performance metrics for dependencies',
    ['tier', 'dependency', 'metric_type']
)

OPTIMIZATION_SCORE = Gauge(
    'dependency_optimization_score',
    'Optimization potential score for dependencies',
    ['tier', 'dependency']
)

@dataclass
class PerformanceMetrics:
    """Performance metrics for a dependency"""
    cpu_usage_mean: float
    cpu_usage_p95: float
    memory_usage_mean: float
    memory_usage_p95: float
    disk_io_mean: Dict[str, float]
    disk_io_p95: Dict[str, float]
    scan_duration_mean: float
    scan_duration_p95: float
    timestamp: datetime

@dataclass
class OptimizationRecommendation:
    """Optimization recommendation for a dependency"""
    dependency: str
    priority: str  # 'high', 'medium', 'low'
    category: str  # 'cpu', 'memory', 'disk', 'scan'
    current_value: float
    target_value: float
    recommendation: str
    potential_impact: str
    implementation_complexity: str  # 'high', 'medium', 'low'

class PerformanceOptimizer:
    """Manages performance optimization for dependencies"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.baselines: Dict[str, PerformanceMetrics] = {}
        self.historical_data: Dict[str, List[PerformanceMetrics]] = {}
        self.window_size = timedelta(days=7)  # Keep 7 days of history
        
    def update_metrics(self, dependency: str, tier: str, metrics: Dict[str, Any]):
        """Update performance metrics for a dependency"""
        current_metrics = PerformanceMetrics(
            cpu_usage_mean=metrics['cpu_usage'],
            cpu_usage_p95=metrics['cpu_usage'],
            memory_usage_mean=metrics['memory_usage'],
            memory_usage_p95=metrics['memory_usage'],
            disk_io_mean=metrics['disk_io'],
            disk_io_p95=metrics['disk_io'],
            scan_duration_mean=metrics.get('scan_duration', 0),
            scan_duration_p95=metrics.get('scan_duration', 0),
            timestamp=datetime.utcnow()
        )
        
        # Update historical data
        if dependency not in self.historical_data:
            self.historical_data[dependency] = []
        
        self.historical_data[dependency].append(current_metrics)
        
        # Remove old data outside window
        cutoff = datetime.utcnow() - self.window_size
        self.historical_data[dependency] = [
            m for m in self.historical_data[dependency]
            if m.timestamp > cutoff
        ]
        
        # Update baseline if we have enough data
        if len(self.historical_data[dependency]) >= 24:  # At least 24 hours of data
            self._update_baseline(dependency, tier)
            
    def _update_baseline(self, dependency: str, tier: str):
        """Update performance baseline for a dependency"""
        metrics = self.historical_data[dependency]
        
        baseline = PerformanceMetrics(
            cpu_usage_mean=np.mean([m.cpu_usage_mean for m in metrics]),
            cpu_usage_p95=np.percentile([m.cpu_usage_p95 for m in metrics], 95),
            memory_usage_mean=np.mean([m.memory_usage_mean for m in metrics]),
            memory_usage_p95=np.percentile([m.memory_usage_p95 for m in metrics], 95),
            disk_io_mean={
                'read': np.mean([m.disk_io_mean['read'] for m in metrics]),
                'write': np.mean([m.disk_io_mean['write'] for m in metrics])
            },
            disk_io_p95={
                'read': np.percentile([m.disk_io_p95['read'] for m in metrics], 95),
                'write': np.percentile([m.disk_io_p95['write'] for m in metrics], 95)
            },
            scan_duration_mean=np.mean([m.scan_duration_mean for m in metrics]),
            scan_duration_p95=np.percentile([m.scan_duration_p95 for m in metrics], 95),
            timestamp=datetime.utcnow()
        )
        
        self.baselines[dependency] = baseline
        
        # Update Prometheus metrics
        PERFORMANCE_BASELINE.labels(tier=tier, dependency=dependency, metric_type="cpu_mean").set(baseline.cpu_usage_mean)
        PERFORMANCE_BASELINE.labels(tier=tier, dependency=dependency, metric_type="cpu_p95").set(baseline.cpu_usage_p95)
        PERFORMANCE_BASELINE.labels(tier=tier, dependency=dependency, metric_type="memory_mean").set(baseline.memory_usage_mean)
        PERFORMANCE_BASELINE.labels(tier=tier, dependency=dependency, metric_type="memory_p95").set(baseline.memory_usage_p95)
        
    def get_optimization_recommendations(self, dependency: str, current_metrics: Dict[str, Any]) -> List[OptimizationRecommendation]:
        """Generate optimization recommendations based on current metrics vs baseline"""
        if dependency not in self.baselines:
            return []
            
        baseline = self.baselines[dependency]
        recommendations = []
        
        # CPU Optimization
        if current_metrics['cpu_usage'] > baseline.cpu_usage_p95 * 1.2:  # 20% above p95
            recommendations.append(OptimizationRecommendation(
                dependency=dependency,
                priority="high",
                category="cpu",
                current_value=current_metrics['cpu_usage'],
                target_value=baseline.cpu_usage_p95,
                recommendation="CPU usage significantly above baseline. Consider:",
                potential_impact="Reduced scan times and resource costs",
                implementation_complexity="medium"
            ))
            
        # Memory Optimization
        if current_metrics['memory_usage'] > baseline.memory_usage_p95 * 1.2:
            recommendations.append(OptimizationRecommendation(
                dependency=dependency,
                priority="high",
                category="memory",
                current_value=current_metrics['memory_usage'],
                target_value=baseline.memory_usage_p95,
                recommendation="Memory usage significantly above baseline. Consider:",
                potential_impact="Improved stability and reduced costs",
                implementation_complexity="medium"
            ))
            
        # Disk IO Optimization
        current_disk_total = current_metrics['disk_io']['read'] + current_metrics['disk_io']['write']
        baseline_disk_total = baseline.disk_io_p95['read'] + baseline.disk_io_p95['write']
        
        if current_disk_total > baseline_disk_total * 1.2:
            recommendations.append(OptimizationRecommendation(
                dependency=dependency,
                priority="medium",
                category="disk",
                current_value=current_disk_total,
                target_value=baseline_disk_total,
                recommendation="Disk I/O significantly above baseline. Consider:",
                potential_impact="Faster scans and reduced storage costs",
                implementation_complexity="medium"
            ))
            
        # Calculate optimization score (0-100)
        if recommendations:
            score = 100 - (
                len([r for r in recommendations if r.priority == "high"]) * 20 +
                len([r for r in recommendations if r.priority == "medium"]) * 10 +
                len([r for r in recommendations if r.priority == "low"]) * 5
            )
            OPTIMIZATION_SCORE.labels(dependency=dependency).set(max(0, score))
            
        return recommendations
        
    def get_performance_report(self, dependency: str) -> Optional[Dict[str, Any]]:
        """Generate a comprehensive performance report for a dependency"""
        if dependency not in self.baselines or dependency not in self.historical_data:
            return None
            
        baseline = self.baselines[dependency]
        recent_metrics = self.historical_data[dependency][-1]
        
        return {
            "dependency": dependency,
            "last_updated": recent_metrics.timestamp.isoformat(),
            "baseline_metrics": {
                "cpu": {
                    "mean": baseline.cpu_usage_mean,
                    "p95": baseline.cpu_usage_p95
                },
                "memory": {
                    "mean": baseline.memory_usage_mean,
                    "p95": baseline.memory_usage_p95
                },
                "disk_io": {
                    "mean": baseline.disk_io_mean,
                    "p95": baseline.disk_io_p95
                },
                "scan_duration": {
                    "mean": baseline.scan_duration_mean,
                    "p95": baseline.scan_duration_p95
                }
            },
            "current_metrics": {
                "cpu_usage": recent_metrics.cpu_usage_mean,
                "memory_usage": recent_metrics.memory_usage_mean,
                "disk_io": recent_metrics.disk_io_mean,
                "scan_duration": recent_metrics.scan_duration_mean
            },
            "trends": self._calculate_trends(dependency)
        }
        
    def _calculate_trends(self, dependency: str) -> Dict[str, str]:
        """Calculate performance trends over the last 24 hours"""
        metrics = self.historical_data[dependency]
        if len(metrics) < 24:
            return {}
            
        last_24h = metrics[-24:]
        
        return {
            "cpu": self._get_trend([m.cpu_usage_mean for m in last_24h]),
            "memory": self._get_trend([m.memory_usage_mean for m in last_24h]),
            "disk_io": self._get_trend([
                m.disk_io_mean['read'] + m.disk_io_mean['write']
                for m in last_24h
            ])
        }
        
    def _get_trend(self, values: List[float]) -> str:
        """Calculate trend direction from a series of values"""
        if len(values) < 2:
            return "stable"
            
        slope = np.polyfit(range(len(values)), values, 1)[0]
        
        if slope > 0.1:
            return "increasing"
        elif slope < -0.1:
            return "decreasing"
        else:
            return "stable"

# Create global optimizer instance
optimizer = PerformanceOptimizer()
