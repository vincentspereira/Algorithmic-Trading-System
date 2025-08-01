#!/usr/bin/env python3
"""
Nautilus Trader - Performance Regression Detection
This module provides automated performance regression testing, trend analysis,
performance alert thresholds, and performance optimization tracking.
"""

import asyncio
import json
import logging
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class PerformanceBaseline:
    """Performance baseline for regression detection"""
    test_name: str
    baseline_date: datetime
    response_time_ms: float
    throughput_rps: float
    error_rate: float
    cpu_usage: float
    memory_usage: float
    confidence_interval: Dict[str, Tuple[float, float]]
    sample_size: int

@dataclass
class RegressionTestResult:
    """Result of a regression test"""
    test_name: str
    test_date: datetime
    current_metrics: Dict[str, float]
    baseline_metrics: Dict[str, float]
    regression_detected: bool
    regression_severity: str  # "none", "minor", "major", "critical"
    affected_metrics: List[str]
    performance_change: Dict[str, float]  # Percentage change
    statistical_significance: Dict[str, float]  # p-values

@dataclass
class PerformanceAlert:
    """Performance alert configuration and result"""
    alert_name: str
    metric_name: str
    threshold_type: str  # "absolute", "percentage", "statistical"
    threshold_value: float
    comparison_operator: str  # "gt", "lt", "eq"
    alert_level: str  # "info", "warning", "critical"
    triggered: bool
    trigger_time: Optional[datetime]
    current_value: float
    message: str

class PerformanceRegressionDetector:
    """Automated performance regression detection system"""
    
    def __init__(self, baseline_storage_path: str = "performance_baselines.json"):
        self.baseline_storage_path = baseline_storage_path
        self.baselines: Dict[str, PerformanceBaseline] = {}
        self.test_history: List[RegressionTestResult] = []
        self.alert_configs: List[PerformanceAlert] = []
        
        # Statistical thresholds
        self.significance_level = 0.05  # 5% significance level
        self.regression_threshold = 0.10  # 10% performance degradation threshold
        self.minor_threshold = 0.05  # 5% minor degradation
        self.major_threshold = 0.20  # 20% major degradation
        self.critical_threshold = 0.50  # 50% critical degradation
        
        # Load existing baselines
        self.load_baselines()
        
        # Setup default alerts
        self.setup_default_alerts()
    
    def load_baselines(self):
        """Load performance baselines from storage"""
        try:
            with open(self.baseline_storage_path, 'r') as f:
                data = json.load(f)
                
            for test_name, baseline_data in data.items():
                baseline_data['baseline_date'] = datetime.fromisoformat(baseline_data['baseline_date'])
                self.baselines[test_name] = PerformanceBaseline(**baseline_data)
                
            logger.info(f"Loaded {len(self.baselines)} performance baselines")
            
        except FileNotFoundError:
            logger.info("No existing baselines found, starting fresh")
        except Exception as e:
            logger.error(f"Error loading baselines: {e}")
    
    def save_baselines(self):
        """Save performance baselines to storage"""
        try:
            data = {}
            for test_name, baseline in self.baselines.items():
                baseline_dict = asdict(baseline)
                baseline_dict['baseline_date'] = baseline.baseline_date.isoformat()
                data[test_name] = baseline_dict
            
            with open(self.baseline_storage_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
                
            logger.info(f"Saved {len(self.baselines)} performance baselines")
            
        except Exception as e:
            logger.error(f"Error saving baselines: {e}")
    
    def establish_baseline(self, test_name: str, test_results: List[Dict[str, float]]) -> PerformanceBaseline:
        """Establish performance baseline from test results"""
        if not test_results:
            raise ValueError("No test results provided for baseline")
        
        # Extract metrics
        response_times = [r.get('response_time_ms', 0) for r in test_results]
        throughputs = [r.get('throughput_rps', 0) for r in test_results]
        error_rates = [r.get('error_rate', 0) for r in test_results]
        cpu_usages = [r.get('cpu_usage', 0) for r in test_results]
        memory_usages = [r.get('memory_usage', 0) for r in test_results]
        
        # Calculate statistics
        baseline = PerformanceBaseline(
            test_name=test_name,
            baseline_date=datetime.now(),
            response_time_ms=statistics.mean(response_times),
            throughput_rps=statistics.mean(throughputs),
            error_rate=statistics.mean(error_rates),
            cpu_usage=statistics.mean(cpu_usages),
            memory_usage=statistics.mean(memory_usages),
            confidence_interval=self._calculate_confidence_intervals(test_results),
            sample_size=len(test_results)
        )
        
        # Store baseline
        self.baselines[test_name] = baseline
        self.save_baselines()
        
        logger.info(f"Established baseline for {test_name}")
        return baseline
    
    def _calculate_confidence_intervals(self, test_results: List[Dict[str, float]]) -> Dict[str, Tuple[float, float]]:
        """Calculate 95% confidence intervals for metrics"""
        intervals = {}
        
        metrics = ['response_time_ms', 'throughput_rps', 'error_rate', 'cpu_usage', 'memory_usage']
        
        for metric in metrics:
            values = [r.get(metric, 0) for r in test_results]
            if values:
                mean = statistics.mean(values)
                if len(values) > 1:
                    stdev = statistics.stdev(values)
                    # 95% confidence interval (assuming normal distribution)
                    margin = 1.96 * stdev / (len(values) ** 0.5)
                    intervals[metric] = (mean - margin, mean + margin)
                else:
                    intervals[metric] = (mean, mean)
        
        return intervals
    
    def run_regression_test(self, test_name: str, current_results: List[Dict[str, float]]) -> RegressionTestResult:
        """Run regression test against baseline"""
        if test_name not in self.baselines:
            raise ValueError(f"No baseline found for test {test_name}")
        
        baseline = self.baselines[test_name]
        
        # Calculate current metrics
        current_metrics = self._calculate_current_metrics(current_results)
        baseline_metrics = {
            'response_time_ms': baseline.response_time_ms,
            'throughput_rps': baseline.throughput_rps,
            'error_rate': baseline.error_rate,
            'cpu_usage': baseline.cpu_usage,
            'memory_usage': baseline.memory_usage
        }
        
        # Detect regressions
        regression_analysis = self._analyze_regression(baseline_metrics, current_metrics)
        
        # Create test result
        result = RegressionTestResult(
            test_name=test_name,
            test_date=datetime.now(),
            current_metrics=current_metrics,
            baseline_metrics=baseline_metrics,
            regression_detected=regression_analysis['regression_detected'],
            regression_severity=regression_analysis['severity'],
            affected_metrics=regression_analysis['affected_metrics'],
            performance_change=regression_analysis['performance_change'],
            statistical_significance=regression_analysis['statistical_significance']
        )
        
        # Store result
        self.test_history.append(result)
        
        # Check alerts
        self._check_performance_alerts(current_metrics)
        
        logger.info(f"Regression test completed for {test_name}: {result.regression_severity}")
        return result
    
    def _calculate_current_metrics(self, test_results: List[Dict[str, float]]) -> Dict[str, float]:
        """Calculate current performance metrics"""
        if not test_results:
            return {}
        
        metrics = {}
        
        # Calculate means for each metric
        for metric in ['response_time_ms', 'throughput_rps', 'error_rate', 'cpu_usage', 'memory_usage']:
            values = [r.get(metric, 0) for r in test_results]
            if values:
                metrics[metric] = statistics.mean(values)
        
        return metrics
    
    def _analyze_regression(self, baseline_metrics: Dict[str, float], 
                          current_metrics: Dict[str, float]) -> Dict[str, Any]:
        """Analyze performance regression"""
        analysis = {
            'regression_detected': False,
            'severity': 'none',
            'affected_metrics': [],
            'performance_change': {},
            'statistical_significance': {}
        }
        
        regression_detected = False
        max_degradation = 0.0
        
        for metric, baseline_value in baseline_metrics.items():
            if metric not in current_metrics:
                continue
            
            current_value = current_metrics[metric]
            
            # Calculate percentage change
            if baseline_value != 0:
                if metric in ['response_time_ms', 'error_rate', 'cpu_usage', 'memory_usage']:
                    # For these metrics, higher is worse
                    change = (current_value - baseline_value) / baseline_value
                else:
                    # For throughput, higher is better
                    change = (baseline_value - current_value) / baseline_value
            else:
                change = 0.0
            
            analysis['performance_change'][metric] = change * 100  # Convert to percentage
            
            # Check for regression
            if change > self.regression_threshold:
                regression_detected = True
                analysis['affected_metrics'].append(metric)
                max_degradation = max(max_degradation, change)
            
            # Mock statistical significance (would use proper statistical tests in real implementation)
            analysis['statistical_significance'][metric] = 0.03 if change > 0.05 else 0.15
        
        analysis['regression_detected'] = regression_detected
        
        # Determine severity
        if max_degradation >= self.critical_threshold:
            analysis['severity'] = 'critical'
        elif max_degradation >= self.major_threshold:
            analysis['severity'] = 'major'
        elif max_degradation >= self.minor_threshold:
            analysis['severity'] = 'minor'
        else:
            analysis['severity'] = 'none'
        
        return analysis
    
    def setup_default_alerts(self):
        """Setup default performance alert configurations"""
        default_alerts = [
            PerformanceAlert(
                alert_name="High Response Time",
                metric_name="response_time_ms",
                threshold_type="absolute",
                threshold_value=2000.0,  # 2 seconds
                comparison_operator="gt",
                alert_level="warning",
                triggered=False,
                trigger_time=None,
                current_value=0.0,
                message="Response time exceeded 2 seconds"
            ),
            PerformanceAlert(
                alert_name="Low Throughput",
                metric_name="throughput_rps",
                threshold_type="absolute",
                threshold_value=100.0,  # 100 RPS
                comparison_operator="lt",
                alert_level="warning",
                triggered=False,
                trigger_time=None,
                current_value=0.0,
                message="Throughput dropped below 100 RPS"
            ),
            PerformanceAlert(
                alert_name="High Error Rate",
                metric_name="error_rate",
                threshold_type="percentage",
                threshold_value=5.0,  # 5%
                comparison_operator="gt",
                alert_level="critical",
                triggered=False,
                trigger_time=None,
                current_value=0.0,
                message="Error rate exceeded 5%"
            ),
            PerformanceAlert(
                alert_name="High CPU Usage",
                metric_name="cpu_usage",
                threshold_type="percentage",
                threshold_value=80.0,  # 80%
                comparison_operator="gt",
                alert_level="warning",
                triggered=False,
                trigger_time=None,
                current_value=0.0,
                message="CPU usage exceeded 80%"
            ),
            PerformanceAlert(
                alert_name="High Memory Usage",
                metric_name="memory_usage",
                threshold_type="percentage",
                threshold_value=85.0,  # 85%
                comparison_operator="gt",
                alert_level="critical",
                triggered=False,
                trigger_time=None,
                current_value=0.0,
                message="Memory usage exceeded 85%"
            )
        ]
        
        self.alert_configs = default_alerts
        logger.info(f"Setup {len(default_alerts)} default performance alerts")
    
    def add_custom_alert(self, alert: PerformanceAlert):
        """Add custom performance alert"""
        self.alert_configs.append(alert)
        logger.info(f"Added custom alert: {alert.alert_name}")
    
    def _check_performance_alerts(self, current_metrics: Dict[str, float]):
        """Check performance alerts against current metrics"""
        for alert in self.alert_configs:
            if alert.metric_name not in current_metrics:
                continue
            
            current_value = current_metrics[alert.metric_name]
            alert.current_value = current_value
            
            # Check threshold
            threshold_exceeded = False
            
            if alert.comparison_operator == "gt":
                threshold_exceeded = current_value > alert.threshold_value
            elif alert.comparison_operator == "lt":
                threshold_exceeded = current_value < alert.threshold_value
            elif alert.comparison_operator == "eq":
                threshold_exceeded = abs(current_value - alert.threshold_value) < 0.001
            
            # Update alert status
            if threshold_exceeded and not alert.triggered:
                alert.triggered = True
                alert.trigger_time = datetime.now()
                self._send_alert(alert)
            elif not threshold_exceeded and alert.triggered:
                alert.triggered = False
                alert.trigger_time = None
    
    def _send_alert(self, alert: PerformanceAlert):
        """Send performance alert notification"""
        logger.warning(f"PERFORMANCE ALERT: {alert.alert_name}")
        logger.warning(f"  Level: {alert.alert_level.upper()}")
        logger.warning(f"  Message: {alert.message}")
        logger.warning(f"  Current Value: {alert.current_value}")
        logger.warning(f"  Threshold: {alert.threshold_value}")
        
        # In a real implementation, this would send notifications via:
        # - Email
        # - Slack
        # - PagerDuty
        # - SMS
        # etc.
    
    def analyze_performance_trends(self, lookback_days: int = 30) -> Dict[str, Any]:
        """Analyze performance trends over time"""
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        recent_tests = [t for t in self.test_history if t.test_date >= cutoff_date]
        
        if not recent_tests:
            return {"error": "No recent test data available"}
        
        # Group by test name
        test_groups = defaultdict(list)
        for test in recent_tests:
            test_groups[test.test_name].append(test)
        
        trends = {}
        
        for test_name, tests in test_groups.items():
            if len(tests) < 3:  # Need at least 3 data points for trend analysis
                continue
            
            # Sort by date
            tests.sort(key=lambda x: x.test_date)
            
            # Calculate trends for each metric
            metric_trends = {}
            
            for metric in ['response_time_ms', 'throughput_rps', 'error_rate', 'cpu_usage', 'memory_usage']:
                values = [t.current_metrics.get(metric, 0) for t in tests]
                trend = self._calculate_trend(values)
                
                metric_trends[metric] = {
                    'trend_slope': trend,
                    'trend_direction': 'increasing' if trend > 0.01 else 'decreasing' if trend < -0.01 else 'stable',
                    'latest_value': values[-1] if values else 0,
                    'change_from_first': ((values[-1] - values[0]) / values[0] * 100) if values and values[0] != 0 else 0
                }
            
            trends[test_name] = {
                'test_count': len(tests),
                'date_range': {
                    'start': tests[0].test_date.isoformat(),
                    'end': tests[-1].test_date.isoformat()
                },
                'metric_trends': metric_trends,
                'overall_health': self._assess_overall_health(metric_trends)
            }
        
        return trends
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend using simple linear regression"""
        if len(values) < 2:
            return 0.0
        
        n = len(values)
        x_values = list(range(n))
        
        # Calculate slope using least squares
        x_mean = sum(x_values) / n
        y_mean = sum(values) / n
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def _assess_overall_health(self, metric_trends: Dict[str, Dict[str, Any]]) -> str:
        """Assess overall performance health based on metric trends"""
        degrading_metrics = 0
        total_metrics = len(metric_trends)
        
        for metric, trend_data in metric_trends.items():
            direction = trend_data['trend_direction']
            
            # Check if metric is degrading
            if metric in ['response_time_ms', 'error_rate', 'cpu_usage', 'memory_usage']:
                if direction == 'increasing':
                    degrading_metrics += 1
            else:  # throughput_rps
                if direction == 'decreasing':
                    degrading_metrics += 1
        
        degradation_ratio = degrading_metrics / total_metrics if total_metrics > 0 else 0
        
        if degradation_ratio >= 0.6:
            return 'poor'
        elif degradation_ratio >= 0.3:
            return 'concerning'
        else:
            return 'good'
    
    def generate_regression_report(self) -> Dict[str, Any]:
        """Generate comprehensive regression analysis report"""
        report = {
            "report_date": datetime.now().isoformat(),
            "baselines_count": len(self.baselines),
            "test_history_count": len(self.test_history),
            "active_alerts": len([a for a in self.alert_configs if a.triggered]),
            "baselines": {name: asdict(baseline) for name, baseline in self.baselines.items()},
            "recent_regressions": self._get_recent_regressions(),
            "performance_trends": self.analyze_performance_trends(),
            "alert_summary": self._get_alert_summary(),
            "optimization_tracking": self._track_optimization_progress(),
            "recommendations": self._generate_regression_recommendations()
        }
        
        # Convert datetime objects to strings for JSON serialization
        for baseline_name, baseline_data in report["baselines"].items():
            baseline_data["baseline_date"] = baseline_data["baseline_date"].isoformat()
        
        return report
    
    def _get_recent_regressions(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get recent regression test results"""
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_regressions = [
            {
                "test_name": t.test_name,
                "test_date": t.test_date.isoformat(),
                "severity": t.regression_severity,
                "affected_metrics": t.affected_metrics,
                "performance_change": t.performance_change
            }
            for t in self.test_history 
            if t.test_date >= cutoff_date and t.regression_detected
        ]
        
        return recent_regressions
    
    def _get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of performance alerts"""
        return {
            "total_alerts": len(self.alert_configs),
            "triggered_alerts": len([a for a in self.alert_configs if a.triggered]),
            "alert_levels": {
                "critical": len([a for a in self.alert_configs if a.alert_level == "critical" and a.triggered]),
                "warning": len([a for a in self.alert_configs if a.alert_level == "warning" and a.triggered]),
                "info": len([a for a in self.alert_configs if a.alert_level == "info" and a.triggered])
            },
            "active_alerts": [
                {
                    "name": a.alert_name,
                    "level": a.alert_level,
                    "message": a.message,
                    "trigger_time": a.trigger_time.isoformat() if a.trigger_time else None,
                    "current_value": a.current_value,
                    "threshold": a.threshold_value
                }
                for a in self.alert_configs if a.triggered
            ]
        }
    
    def _track_optimization_progress(self) -> Dict[str, Any]:
        """Track performance optimization progress over time"""
        if len(self.test_history) < 2:
            return {"error": "Insufficient data for optimization tracking"}
        
        # Compare recent performance with older performance
        recent_tests = self.test_history[-10:]  # Last 10 tests
        older_tests = self.test_history[-20:-10] if len(self.test_history) >= 20 else []
        
        if not older_tests:
            return {"error": "Insufficient historical data"}
        
        # Calculate average metrics for both periods
        recent_avg = self._calculate_average_metrics(recent_tests)
        older_avg = self._calculate_average_metrics(older_tests)
        
        optimization_progress = {}
        
        for metric in recent_avg:
            if metric in older_avg and older_avg[metric] != 0:
                if metric in ['response_time_ms', 'error_rate', 'cpu_usage', 'memory_usage']:
                    # Lower is better for these metrics
                    improvement = (older_avg[metric] - recent_avg[metric]) / older_avg[metric] * 100
                else:
                    # Higher is better for throughput
                    improvement = (recent_avg[metric] - older_avg[metric]) / older_avg[metric] * 100
                
                optimization_progress[metric] = {
                    'improvement_percentage': improvement,
                    'recent_average': recent_avg[metric],
                    'older_average': older_avg[metric],
                    'status': 'improved' if improvement > 5 else 'degraded' if improvement < -5 else 'stable'
                }
        
        return optimization_progress
    
    def _calculate_average_metrics(self, tests: List[RegressionTestResult]) -> Dict[str, float]:
        """Calculate average metrics from test results"""
        if not tests:
            return {}
        
        metric_sums = defaultdict(float)
        metric_counts = defaultdict(int)
        
        for test in tests:
            for metric, value in test.current_metrics.items():
                metric_sums[metric] += value
                metric_counts[metric] += 1
        
        return {
            metric: metric_sums[metric] / metric_counts[metric]
            for metric in metric_sums
            if metric_counts[metric] > 0
        }
    
    def _generate_regression_recommendations(self) -> List[Dict[str, str]]:
        """Generate recommendations based on regression analysis"""
        recommendations = []
        
        # Check for recent regressions
        recent_regressions = self._get_recent_regressions()
        
        if recent_regressions:
            recommendations.append({
                "category": "regression",
                "priority": "high",
                "recommendation": f"Address {len(recent_regressions)} recent performance regressions",
                "details": "Investigate and fix performance degradations in affected components"
            })
        
        # Check for triggered alerts
        triggered_alerts = [a for a in self.alert_configs if a.triggered]
        
        if triggered_alerts:
            critical_alerts = [a for a in triggered_alerts if a.alert_level == "critical"]
            if critical_alerts:
                recommendations.append({
                    "category": "alerts",
                    "priority": "critical",
                    "recommendation": f"Resolve {len(critical_alerts)} critical performance alerts",
                    "details": "Address critical performance issues immediately"
                })
        
        # General recommendations
        recommendations.extend([
            {
                "category": "monitoring",
                "priority": "medium",
                "recommendation": "Implement continuous performance monitoring",
                "details": "Set up automated performance testing in CI/CD pipeline"
            },
            {
                "category": "baselines",
                "priority": "low",
                "recommendation": "Update performance baselines regularly",
                "details": "Refresh baselines after major optimizations or infrastructure changes"
            },
            {
                "category": "alerting",
                "priority": "medium",
                "recommendation": "Fine-tune alert thresholds based on historical data",
                "details": "Adjust alert thresholds to reduce false positives while maintaining sensitivity"
            }
        ])
        
        return recommendations
    
    def save_report(self, report: Dict[str, Any], filename: str = None):
        """Save regression report to file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"regression_report_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Regression report saved to {filename}")

async def main():
    """Main function to demonstrate regression detection"""
    logger.info("Starting performance regression detection demonstration")
    
    # Create detector
    detector = PerformanceRegressionDetector()
    
    # Simulate establishing a baseline
    logger.info("Establishing performance baseline...")
    baseline_results = [
        {
            'response_time_ms': 150.0,
            'throughput_rps': 1000.0,
            'error_rate': 0.01,
            'cpu_usage': 45.0,
            'memory_usage': 60.0
        }
        for _ in range(10)  # 10 baseline measurements
    ]
    
    baseline = detector.establish_baseline("api_performance_test", baseline_results)
    
    # Simulate current test results (with some regression)
    logger.info("Running regression test...")
    current_results = [
        {
            'response_time_ms': 180.0,  # 20% slower
            'throughput_rps': 850.0,    # 15% lower throughput
            'error_rate': 0.015,        # 50% higher error rate
            'cpu_usage': 55.0,          # 22% higher CPU
            'memory_usage': 65.0        # 8% higher memory
        }
        for _ in range(10)  # 10 current measurements
    ]
    
    regression_result = detector.run_regression_test("api_performance_test", current_results)
    
    # Analyze trends
    logger.info("Analyzing performance trends...")
    trends = detector.analyze_performance_trends()
    
    # Generate comprehensive report
    report = detector.generate_regression_report()
    
    # Save report
    detector.save_report(report)
    
    # Print summary
    print("\n" + "="*60)
    print("PERFORMANCE REGRESSION DETECTION SUMMARY")
    print("="*60)
    
    print(f"Regression Detected: {regression_result.regression_detected}")
    print(f"Severity: {regression_result.regression_severity}")
    
    if regression_result.affected_metrics:
        print(f"Affected Metrics: {', '.join(regression_result.affected_metrics)}")
    
    print("\nPerformance Changes:")
    for metric, change in regression_result.performance_change.items():
        print(f"  {metric}: {change:+.1f}%")
    
    # Show active alerts
    active_alerts = [a for a in detector.alert_configs if a.triggered]
    if active_alerts:
        print(f"\nActive Alerts ({len(active_alerts)}):")
        for alert in active_alerts:
            print(f"  - {alert.alert_name} ({alert.alert_level}): {alert.message}")
    
    # Show recommendations
    if "recommendations" in report:
        recommendations = report["recommendations"]
        print(f"\nRecommendations ({len(recommendations)}):")
        for rec in recommendations[:3]:  # Show top 3
            print(f"  - [{rec['priority'].upper()}] {rec['recommendation']}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    asyncio.run(main())