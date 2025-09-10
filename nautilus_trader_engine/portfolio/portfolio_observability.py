"""
Portfolio Observability System
Comprehensive monitoring, metrics collection, and observability for portfolio operations.
"""

import asyncio
import logging
import time
import threading
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
import statistics

# Import monitoring components
try:
    from nautilus_trader_engine.monitoring.metrics_collection import (
        MetricsCollectionSystem, 
        MetricDefinition, 
        MetricType, 
        MetricCategory
    )
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False
    logging.warning("Monitoring system not available, using basic logging")
    # Define placeholder classes for when monitoring is not available
    class MetricsCollectionSystem:
        pass
    
    class MetricDefinition:
        def __init__(self, *args, **kwargs):
            pass
    
    class MetricType:
        GAUGE = "gauge"
        COUNTER = "counter"
        HISTOGRAM = "histogram"
    
    class MetricCategory:
        BUSINESS = "business"
        RISK = "risk"
        PERFORMANCE = "performance"

from nautilus_trader.common.component import Logger
from nautilus_trader.portfolio.portfolio import Portfolio
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.objects import Money


@dataclass
class PortfolioMetrics:
    """Key portfolio performance metrics"""
    total_value: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    total_pnl: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    var_95: float = 0.0
    var_99: float = 0.0
    turnover: float = 0.0
    effective_assets: float = 0.0
    diversification_ratio: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class RiskMetrics:
    """Portfolio risk metrics"""
    value_at_risk: float = 0.0
    conditional_var: float = 0.0
    max_drawdown: float = 0.0
    beta: float = 0.0
    alpha: float = 0.0
    tracking_error: float = 0.0
    information_ratio: float = 0.0
    risk_contribution: Dict[str, float] = field(default_factory=dict)
    concentration_risk: float = 0.0
    liquidity_risk: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PerformanceAttribution:
    """Performance attribution metrics"""
    asset_contributions: Dict[str, float] = field(default_factory=dict)
    sector_contributions: Dict[str, float] = field(default_factory=dict)
    factor_contributions: Dict[str, float] = field(default_factory=dict)
    timing_contributions: Dict[str, float] = field(default_factory=dict)
    selection_contributions: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class PortfolioObservability:
    """Comprehensive portfolio observability system"""
    
    def __init__(self, portfolio: Portfolio, metrics_system: MetricsCollectionSystem = None):
        self.portfolio = portfolio
        self.metrics_system = metrics_system
        self.logger = Logger(name=type(self).__name__)
        self._is_running = False
        self._collection_tasks = []
        self._historical_metrics = defaultdict(deque)
        self._risk_metrics = defaultdict(deque)
        self._alerts = []
        self._lock = threading.RLock()
        
        # Initialize metrics if monitoring system is available
        if self.metrics_system:
            self._register_portfolio_metrics()
            
    def _register_portfolio_metrics(self):
        """Register portfolio-specific metrics"""
        portfolio_metrics = [
            MetricDefinition(
                name="portfolio.value.total",
                metric_type=MetricType.GAUGE,
                category=MetricCategory.BUSINESS,
                description="Total portfolio value",
                unit="USD"
            ),
            MetricDefinition(
                name="portfolio.pnl.realized",
                metric_type=MetricType.GAUGE,
                category=MetricCategory.BUSINESS,
                description="Realized profit and loss",
                unit="USD"
            ),
            MetricDefinition(
                name="portfolio.pnl.unrealized",
                metric_type=MetricType.GAUGE,
                category=MetricCategory.BUSINESS,
                description="Unrealized profit and loss",
                unit="USD"
            ),
            MetricDefinition(
                name="portfolio.risk.var_95",
                metric_type=MetricType.GAUGE,
                category=MetricCategory.RISK,
                description="Value at Risk at 95% confidence",
                unit="USD"
            ),
            MetricDefinition(
                name="portfolio.risk.max_drawdown",
                metric_type=MetricType.GAUGE,
                category=MetricCategory.RISK,
                description="Maximum drawdown",
                unit="percent"
            ),
            MetricDefinition(
                name="portfolio.diversification.effective_assets",
                metric_type=MetricType.GAUGE,
                category=MetricCategory.BUSINESS,
                description="Effective number of assets",
                unit="count"
            ),
            MetricDefinition(
                name="portfolio.turnover.daily",
                metric_type=MetricType.GAUGE,
                category=MetricCategory.PERFORMANCE,
                description="Daily portfolio turnover",
                unit="percent"
            )
        ]
        
        for metric in portfolio_metrics:
            self.metrics_system.collector.register_metric(metric)
            
    async def start(self):
        """Start the portfolio observability system"""
        if self._is_running:
            self.logger.warning("Portfolio observability system already running")
            return
            
        self._is_running = True
        
        # Start periodic metrics collection
        collection_task = asyncio.create_task(self._metrics_collection_loop())
        self._collection_tasks.append(collection_task)
        
        self.logger.info("Portfolio observability system started")
        
    async def stop(self):
        """Stop the portfolio observability system"""
        if not self._is_running:
            return
            
        self._is_running = False
        
        # Cancel collection tasks
        for task in self._collection_tasks:
            task.cancel()
            
        self.logger.info("Portfolio observability system stopped")
        
    async def _metrics_collection_loop(self):
        """Periodic metrics collection loop"""
        while self._is_running:
            try:
                await self.collect_portfolio_metrics()
                await asyncio.sleep(60)  # Collect every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Metrics collection error: {e}")
                await asyncio.sleep(60)
                
    async def collect_portfolio_metrics(self):
        """Collect current portfolio metrics"""
        try:
            # Get portfolio metrics
            metrics = self._calculate_portfolio_metrics()
            
            # Store historical metrics
            with self._lock:
                self._historical_metrics['portfolio_value'].append(
                    (datetime.now(), metrics.total_value)
                )
                self._historical_metrics['portfolio_pnl'].append(
                    (datetime.now(), metrics.total_pnl)
                )
                self._historical_metrics['portfolio_risk'].append(
                    (datetime.now(), metrics.volatility)
                )
                
                # Keep only last 24 hours of data
                cutoff_time = datetime.now() - timedelta(hours=24)
                for key in self._historical_metrics:
                    while (self._historical_metrics[key] and 
                           self._historical_metrics[key][0][0] < cutoff_time):
                        self._historical_metrics[key].popleft()
                        
            # Update monitoring system if available
            if self.metrics_system:
                self.metrics_system.collect_metric("portfolio.value.total", metrics.total_value)
                self.metrics_system.collect_metric("portfolio.pnl.realized", metrics.realized_pnl)
                self.metrics_system.collect_metric("portfolio.pnl.unrealized", metrics.unrealized_pnl)
                self.metrics_system.collect_metric("portfolio.risk.var_95", metrics.var_95)
                self.metrics_system.collect_metric("portfolio.risk.max_drawdown", metrics.max_drawdown * 100)
                self.metrics_system.collect_metric("portfolio.diversification.effective_assets", metrics.effective_assets)
                self.metrics_system.collect_metric("portfolio.turnover.daily", metrics.turnover * 100)
                
            self.logger.debug(f"Collected portfolio metrics: Total Value=${metrics.total_value:,.2f}")
            
        except Exception as e:
            self.logger.error(f"Failed to collect portfolio metrics: {e}")
            
    def _calculate_portfolio_metrics(self) -> PortfolioMetrics:
        """Calculate comprehensive portfolio metrics"""
        metrics = PortfolioMetrics()
        
        try:
            # Get portfolio data (this would need to be adapted to actual Nautilus API)
            # For now, we'll simulate with placeholder values
            metrics.total_value = 1000000.0  # $1M portfolio
            metrics.realized_pnl = 25000.0
            metrics.unrealized_pnl = -5000.0
            metrics.total_pnl = metrics.realized_pnl + metrics.unrealized_pnl
            metrics.volatility = 0.15  # 15% annualized
            metrics.sharpe_ratio = 1.2
            metrics.max_drawdown = 0.08  # 8%
            metrics.var_95 = 30000.0  # $30K VaR at 95%
            metrics.var_99 = 50000.0  # $50K VaR at 99%
            metrics.turnover = 0.02  # 2% daily turnover
            metrics.effective_assets = 15.5
            metrics.diversification_ratio = 1.3
            
        except Exception as e:
            self.logger.error(f"Error calculating portfolio metrics: {e}")
            
        return metrics
        
    def get_portfolio_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Get portfolio metrics for the specified time period"""
        with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            # Filter metrics by time
            filtered_metrics = {}
            for key, values in self._historical_metrics.items():
                filtered_values = [(t, v) for t, v in values if t >= cutoff_time]
                filtered_metrics[key] = filtered_values
                
            return {
                "current": self._calculate_portfolio_metrics(),
                "historical": filtered_metrics,
                "timestamp": datetime.now()
            }
            
    def calculate_performance_attribution(self, 
                                        benchmark_returns: List[float] = None,
                                        factor_returns: Dict[str, List[float]] = None) -> PerformanceAttribution:
        """
        Calculate performance attribution metrics.
        
        Parameters
        ----------
        benchmark_returns : List[float], optional
            Benchmark returns for comparison
        factor_returns : Dict[str, List[float]], optional
            Factor returns for factor-based attribution
            
        Returns
        -------
        PerformanceAttribution
            Performance attribution analysis
        """
        attribution = PerformanceAttribution()
        
        try:
            # Placeholder for actual attribution calculation
            # This would need to be implemented with proper return data
            attribution.asset_contributions = {
                "AAPL": 0.002,
                "GOOGL": 0.0015,
                "MSFT": 0.001,
                "AMZN": -0.0005,
                "TSLA": 0.003
            }
            
            attribution.sector_contributions = {
                "Technology": 0.005,
                "Financials": 0.001,
                "Healthcare": 0.0005
            }
            
            if factor_returns:
                attribution.factor_contributions = {
                    factor: 0.001 for factor in factor_returns.keys()
                }
                
        except Exception as e:
            self.logger.error(f"Error calculating performance attribution: {e}")
            
        return attribution
        
    def calculate_risk_metrics(self, 
                             returns: List[float] = None,
                             benchmark_returns: List[float] = None,
                             confidence_level: float = 0.95) -> RiskMetrics:
        """
        Calculate comprehensive risk metrics.
        
        Parameters
        ----------
        returns : List[float], optional
            Portfolio returns for risk calculation
        benchmark_returns : List[float], optional
            Benchmark returns for relative risk metrics
        confidence_level : float
            Confidence level for VaR calculation
            
        Returns
        -------
        RiskMetrics
            Comprehensive risk metrics
        """
        risk_metrics = RiskMetrics()
        
        try:
            if returns:
                # Calculate VaR
                sorted_returns = sorted(returns)
                var_index_95 = int(len(sorted_returns) * (1 - 0.95))
                var_index_99 = int(len(sorted_returns) * (1 - 0.99))
                
                risk_metrics.value_at_risk = abs(sorted_returns[var_index_95]) if var_index_95 < len(sorted_returns) else 0
                risk_metrics.conditional_var = abs(statistics.mean(sorted_returns[:var_index_99])) if var_index_99 > 0 else 0
                
                # Calculate volatility
                if len(returns) > 1:
                    risk_metrics.beta = 1.0  # Placeholder
                    risk_metrics.alpha = 0.0  # Placeholder
                    
                # Calculate max drawdown
                cumulative = [1.0]
                for r in returns:
                    cumulative.append(cumulative[-1] * (1 + r))
                    
                peak = cumulative[0]
                max_dd = 0.0
                for value in cumulative:
                    if value > peak:
                        peak = value
                    dd = (peak - value) / peak
                    max_dd = max(max_dd, dd)
                    
                risk_metrics.max_drawdown = max_dd
                
            if benchmark_returns and returns and len(returns) == len(benchmark_returns):
                # Calculate tracking error and information ratio
                diffs = [r - br for r, br in zip(returns, benchmark_returns)]
                risk_metrics.tracking_error = statistics.stdev(diffs) if len(diffs) > 1 else 0
                avg_diff = statistics.mean(diffs)
                risk_metrics.information_ratio = avg_diff / risk_metrics.tracking_error if risk_metrics.tracking_error > 0 else 0
                
        except Exception as e:
            self.logger.error(f"Error calculating risk metrics: {e}")
            
        return risk_metrics
        
    def add_alert(self, alert_type: str, message: str, severity: str = "info"):
        """Add an alert to the alert system"""
        alert = {
            "timestamp": datetime.now(),
            "type": alert_type,
            "message": message,
            "severity": severity
        }
        
        with self._lock:
            self._alerts.append(alert)
            
            # Keep only last 100 alerts
            if len(self._alerts) > 100:
                self._alerts = self._alerts[-100:]
                
        self.logger.info(f"Portfolio Alert [{severity.upper()}]: {message}")
        
    def get_alerts(self, hours: int = 24, severity: str = None) -> List[Dict]:
        """Get recent alerts"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            filtered_alerts = [
                alert for alert in self._alerts 
                if alert["timestamp"] >= cutoff_time
            ]
            
            if severity:
                filtered_alerts = [
                    alert for alert in filtered_alerts
                    if alert["severity"] == severity
                ]
                
            return sorted(filtered_alerts, key=lambda x: x["timestamp"], reverse=True)
            
    def generate_portfolio_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive portfolio report.
        
        Returns
        -------
        Dict[str, Any]
            Comprehensive portfolio report
        """
        try:
            current_metrics = self._calculate_portfolio_metrics()
            risk_metrics = self.calculate_risk_metrics()
            attribution = self.calculate_performance_attribution()
            
            report = {
                "timestamp": datetime.now().isoformat(),
                "portfolio_summary": {
                    "total_value": current_metrics.total_value,
                    "total_pnl": current_metrics.total_pnl,
                    "total_pnl_percentage": (current_metrics.total_pnl / (current_metrics.total_value - current_metrics.total_pnl)) * 100,
                    "unrealized_pnl": current_metrics.unrealized_pnl,
                    "realized_pnl": current_metrics.realized_pnl
                },
                "performance_metrics": {
                    "volatility": current_metrics.volatility,
                    "sharpe_ratio": current_metrics.sharpe_ratio,
                    "max_drawdown": current_metrics.max_drawdown,
                    "turnover": current_metrics.turnover,
                    "effective_assets": current_metrics.effective_assets,
                    "diversification_ratio": current_metrics.diversification_ratio
                },
                "risk_metrics": {
                    "value_at_risk_95": risk_metrics.value_at_risk,
                    "conditional_var_99": risk_metrics.conditional_var,
                    "max_drawdown": risk_metrics.max_drawdown,
                    "beta": risk_metrics.beta,
                    "tracking_error": risk_metrics.tracking_error,
                    "information_ratio": risk_metrics.information_ratio
                },
                "performance_attribution": {
                    "asset_contributions": attribution.asset_contributions,
                    "sector_contributions": attribution.sector_contributions
                },
                "recent_alerts": self.get_alerts(hours=24)
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating portfolio report: {e}")
            return {"error": str(e)}


class PortfolioAlertManager:
    """Manage portfolio alerts and notifications"""
    
    def __init__(self, observability: PortfolioObservability):
        self.observability = observability
        self.logger = Logger(name=type(self).__name__)
        self._alert_rules = []
        self._is_monitoring = False
        self._monitoring_task = None
        
    def add_alert_rule(self, name: str, condition: Callable, message: str, severity: str = "warning"):
        """Add an alert rule"""
        rule = {
            "name": name,
            "condition": condition,
            "message": message,
            "severity": severity
        }
        self._alert_rules.append(rule)
        self.logger.info(f"Added alert rule: {name}")
        
    async def start_monitoring(self):
        """Start monitoring for alert conditions"""
        if self._is_monitoring:
            return
            
        self._is_monitoring = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Portfolio alert monitoring started")
        
    async def stop_monitoring(self):
        """Stop monitoring for alert conditions"""
        if not self._is_monitoring:
            return
            
        self._is_monitoring = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
        self.logger.info("Portfolio alert monitoring stopped")
        
    async def _monitoring_loop(self):
        """Monitoring loop to check alert conditions"""
        while self._is_monitoring:
            try:
                # Check all alert rules
                current_metrics = self.observability._calculate_portfolio_metrics()
                
                for rule in self._alert_rules:
                    try:
                        if rule["condition"](current_metrics):
                            self.observability.add_alert(
                                alert_type="rule_triggered",
                                message=f"{rule['name']}: {rule['message']}",
                                severity=rule["severity"]
                            )
                    except Exception as e:
                        self.logger.error(f"Error evaluating alert rule {rule['name']}: {e}")
                        
                await asyncio.sleep(300)  # Check every 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(300)


# Example usage and testing
async def example_usage():
    """Example usage of the portfolio observability system"""
    
    # This would normally use a real Nautilus Trader portfolio
    # For this example, we'll create a mock portfolio
    class MockPortfolio:
        pass
        
    portfolio = MockPortfolio()
    
    # Create observability system
    if MONITORING_AVAILABLE:
        metrics_system = MetricsCollectionSystem()
        await metrics_system.start()
    else:
        metrics_system = None
        
    observability = PortfolioObservability(portfolio, metrics_system)
    
    print("Starting portfolio observability system...")
    await observability.start()
    
    # Collect some metrics
    print("Collecting portfolio metrics...")
    await observability.collect_portfolio_metrics()
    
    # Get metrics
    metrics = observability.get_portfolio_metrics()
    print(f"Current portfolio value: ${metrics['current'].total_value:,.2f}")
    print(f"Portfolio Sharpe ratio: {metrics['current'].sharpe_ratio:.2f}")
    
    # Calculate risk metrics
    sample_returns = [0.01, -0.005, 0.02, -0.01, 0.008, 0.015, -0.002, 0.011]
    risk_metrics = observability.calculate_risk_metrics(sample_returns)
    print(f"Value at Risk (95%): ${risk_metrics.value_at_risk:.2f}")
    print(f"Max Drawdown: {risk_metrics.max_drawdown:.2%}")
    
    # Generate report
    report = observability.generate_portfolio_report()
    print(f"\nPortfolio Report Generated at: {report['timestamp']}")
    print(f"Total Value: ${report['portfolio_summary']['total_value']:,.2f}")
    print(f"Sharpe Ratio: {report['performance_metrics']['sharpe_ratio']:.2f}")
    
    # Add some alerts
    observability.add_alert("high_volatility", "Portfolio volatility exceeded 20%", "warning")
    observability.add_alert("drawdown_alert", "Portfolio drawdown exceeded 5%", "critical")
    
    # Get alerts
    alerts = observability.get_alerts()
    print(f"\nRecent Alerts ({len(alerts)}):")
    for alert in alerts[:3]:  # Show first 3 alerts
        print(f"  {alert['timestamp'].strftime('%Y-%m-%d %H:%M')} [{alert['severity'].upper()}] {alert['message']}")
    
    # Stop the system
    print("\nStopping portfolio observability system...")
    await observability.stop()
    
    if metrics_system:
        await metrics_system.stop()


if __name__ == "__main__":
    asyncio.run(example_usage())