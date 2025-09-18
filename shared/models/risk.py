"""Risk management models for the algorithmic trading system.

This module provides data structures for risk management, risk metrics,
and risk monitoring.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
import uuid
import math

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk level enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskType(Enum):
    """Risk type enumeration."""
    MARKET_RISK = "market_risk"
    CREDIT_RISK = "credit_risk"
    LIQUIDITY_RISK = "liquidity_risk"
    OPERATIONAL_RISK = "operational_risk"
    CONCENTRATION_RISK = "concentration_risk"
    VOLATILITY_RISK = "volatility_risk"
    CORRELATION_RISK = "correlation_risk"
    LEVERAGE_RISK = "leverage_risk"


class RiskLimitType(Enum):
    """Risk limit type enumeration."""
    POSITION_SIZE = "position_size"
    PORTFOLIO_VALUE = "portfolio_value"
    DAILY_LOSS = "daily_loss"
    DRAWDOWN = "drawdown"
    VAR = "var"  # Value at Risk
    LEVERAGE = "leverage"
    CONCENTRATION = "concentration"
    VOLATILITY = "volatility"
    CORRELATION = "correlation"


class RiskStatus(Enum):
    """Risk status enumeration."""
    NORMAL = "normal"
    WARNING = "warning"
    BREACH = "breach"
    CRITICAL = "critical"


@dataclass
class RiskLimit:
    """Represents a risk limit or constraint."""
    limit_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    limit_type: RiskLimitType = RiskLimitType.POSITION_SIZE
    value: Decimal = Decimal('0')
    threshold_warning: Optional[Decimal] = None  # Warning threshold (e.g., 80% of limit)
    threshold_critical: Optional[Decimal] = None  # Critical threshold (e.g., 95% of limit)
    
    # Scope
    applies_to: str = "portfolio"  # "portfolio", "strategy", "symbol", "account"
    scope_id: Optional[str] = None  # ID of the scope (strategy_id, symbol, etc.)
    
    # Status
    is_active: bool = True
    current_value: Decimal = Decimal('0')
    utilization_pct: Decimal = Decimal('0')
    status: RiskStatus = RiskStatus.NORMAL
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_breach_at: Optional[datetime] = None
    
    # Metadata
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization processing."""
        if self.threshold_warning is None:
            self.threshold_warning = self.value * Decimal('0.8')
        if self.threshold_critical is None:
            self.threshold_critical = self.value * Decimal('0.95')
    
    def update_current_value(self, new_value: Decimal, timestamp: Optional[datetime] = None) -> None:
        """Update current value and check status."""
        self.current_value = new_value
        self.updated_at = timestamp or datetime.utcnow()
        
        # Calculate utilization percentage
        if self.value > 0:
            self.utilization_pct = (abs(self.current_value) / self.value) * 100
        else:
            self.utilization_pct = Decimal('0')
        
        # Update status
        old_status = self.status
        
        if abs(self.current_value) >= self.value:
            self.status = RiskStatus.BREACH
            if old_status != RiskStatus.BREACH:
                self.last_breach_at = self.updated_at
        elif self.threshold_critical and abs(self.current_value) >= self.threshold_critical:
            self.status = RiskStatus.CRITICAL
        elif self.threshold_warning and abs(self.current_value) >= self.threshold_warning:
            self.status = RiskStatus.WARNING
        else:
            self.status = RiskStatus.NORMAL
        
        if old_status != self.status:
            logger.info(f"Risk limit {self.limit_id} status changed: {old_status.value} -> {self.status.value}")
    
    @property
    def is_breached(self) -> bool:
        """Check if limit is breached."""
        return self.status == RiskStatus.BREACH
    
    @property
    def is_warning(self) -> bool:
        """Check if limit is in warning state."""
        return self.status in [RiskStatus.WARNING, RiskStatus.CRITICAL, RiskStatus.BREACH]
    
    @property
    def remaining_capacity(self) -> Decimal:
        """Calculate remaining capacity before limit breach."""
        return max(Decimal('0'), self.value - abs(self.current_value))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "limit_id": self.limit_id,
            "name": self.name,
            "limit_type": self.limit_type.value,
            "value": float(self.value),
            "threshold_warning": float(self.threshold_warning) if self.threshold_warning else None,
            "threshold_critical": float(self.threshold_critical) if self.threshold_critical else None,
            "applies_to": self.applies_to,
            "scope_id": self.scope_id,
            "is_active": self.is_active,
            "current_value": float(self.current_value),
            "utilization_pct": float(self.utilization_pct),
            "status": self.status.value,
            "remaining_capacity": float(self.remaining_capacity),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_breach_at": self.last_breach_at.isoformat() if self.last_breach_at else None,
            "description": self.description,
            "tags": self.tags,
            "metadata": self.metadata
        }


@dataclass
class RiskMetrics:
    """Comprehensive risk metrics for a portfolio or position."""
    entity_id: str  # portfolio_id, strategy_id, etc.
    entity_type: str  # "portfolio", "strategy", "position"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Value at Risk (VaR)
    var_1d_95: Optional[Decimal] = None  # 1-day VaR at 95% confidence
    var_1d_99: Optional[Decimal] = None  # 1-day VaR at 99% confidence
    var_10d_95: Optional[Decimal] = None  # 10-day VaR at 95% confidence
    var_10d_99: Optional[Decimal] = None  # 10-day VaR at 99% confidence
    
    # Expected Shortfall (Conditional VaR)
    es_1d_95: Optional[Decimal] = None  # 1-day Expected Shortfall at 95%
    es_1d_99: Optional[Decimal] = None  # 1-day Expected Shortfall at 99%
    
    # Volatility metrics
    volatility_1d: Optional[Decimal] = None  # 1-day volatility
    volatility_annualized: Optional[Decimal] = None  # Annualized volatility
    
    # Drawdown metrics
    current_drawdown: Decimal = Decimal('0')
    max_drawdown: Decimal = Decimal('0')
    max_drawdown_duration: Optional[int] = None  # in days
    
    # Exposure metrics
    gross_exposure: Decimal = Decimal('0')
    net_exposure: Decimal = Decimal('0')
    long_exposure: Decimal = Decimal('0')
    short_exposure: Decimal = Decimal('0')
    
    # Leverage metrics
    leverage_ratio: Decimal = Decimal('1')
    effective_leverage: Decimal = Decimal('1')
    
    # Concentration metrics
    concentration_hhi: Optional[Decimal] = None  # Herfindahl-Hirschman Index
    largest_position_pct: Decimal = Decimal('0')
    top_5_positions_pct: Decimal = Decimal('0')
    
    # Correlation metrics
    portfolio_beta: Optional[Decimal] = None
    correlation_to_market: Optional[Decimal] = None
    
    # Liquidity metrics
    liquidity_score: Optional[Decimal] = None
    days_to_liquidate: Optional[int] = None
    
    # Performance-based risk metrics
    sharpe_ratio: Optional[Decimal] = None
    sortino_ratio: Optional[Decimal] = None
    calmar_ratio: Optional[Decimal] = None
    
    # Stress test results
    stress_test_results: Dict[str, Decimal] = field(default_factory=dict)
    
    def calculate_risk_score(self) -> Decimal:
        """Calculate overall risk score (0-100, higher = riskier)."""
        score = Decimal('0')
        factors = 0
        
        # VaR contribution (0-30 points)
        if self.var_1d_95:
            var_score = min(30, abs(self.var_1d_95) * 100)  # Assuming VaR as % of portfolio
            score += var_score
            factors += 1
        
        # Volatility contribution (0-25 points)
        if self.volatility_annualized:
            vol_score = min(25, self.volatility_annualized * 100)  # Assuming vol as decimal
            score += vol_score
            factors += 1
        
        # Drawdown contribution (0-20 points)
        drawdown_score = min(20, abs(self.current_drawdown))
        score += drawdown_score
        factors += 1
        
        # Leverage contribution (0-15 points)
        leverage_score = min(15, max(0, (self.leverage_ratio - 1) * 10))
        score += leverage_score
        factors += 1
        
        # Concentration contribution (0-10 points)
        concentration_score = min(10, self.largest_position_pct)
        score += concentration_score
        factors += 1
        
        # Average the score if we have factors
        if factors > 0:
            return score / factors
        return Decimal('0')
    
    @property
    def risk_level(self) -> RiskLevel:
        """Determine risk level based on risk score."""
        score = self.calculate_risk_score()
        
        if score >= 75:
            return RiskLevel.CRITICAL
        elif score >= 50:
            return RiskLevel.HIGH
        elif score >= 25:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "timestamp": self.timestamp.isoformat(),
            "var_1d_95": float(self.var_1d_95) if self.var_1d_95 else None,
            "var_1d_99": float(self.var_1d_99) if self.var_1d_99 else None,
            "var_10d_95": float(self.var_10d_95) if self.var_10d_95 else None,
            "var_10d_99": float(self.var_10d_99) if self.var_10d_99 else None,
            "es_1d_95": float(self.es_1d_95) if self.es_1d_95 else None,
            "es_1d_99": float(self.es_1d_99) if self.es_1d_99 else None,
            "volatility_1d": float(self.volatility_1d) if self.volatility_1d else None,
            "volatility_annualized": float(self.volatility_annualized) if self.volatility_annualized else None,
            "current_drawdown": float(self.current_drawdown),
            "max_drawdown": float(self.max_drawdown),
            "max_drawdown_duration": self.max_drawdown_duration,
            "gross_exposure": float(self.gross_exposure),
            "net_exposure": float(self.net_exposure),
            "long_exposure": float(self.long_exposure),
            "short_exposure": float(self.short_exposure),
            "leverage_ratio": float(self.leverage_ratio),
            "effective_leverage": float(self.effective_leverage),
            "concentration_hhi": float(self.concentration_hhi) if self.concentration_hhi else None,
            "largest_position_pct": float(self.largest_position_pct),
            "top_5_positions_pct": float(self.top_5_positions_pct),
            "portfolio_beta": float(self.portfolio_beta) if self.portfolio_beta else None,
            "correlation_to_market": float(self.correlation_to_market) if self.correlation_to_market else None,
            "liquidity_score": float(self.liquidity_score) if self.liquidity_score else None,
            "days_to_liquidate": self.days_to_liquidate,
            "sharpe_ratio": float(self.sharpe_ratio) if self.sharpe_ratio else None,
            "sortino_ratio": float(self.sortino_ratio) if self.sortino_ratio else None,
            "calmar_ratio": float(self.calmar_ratio) if self.calmar_ratio else None,
            "stress_test_results": {k: float(v) for k, v in self.stress_test_results.items()},
            "risk_score": float(self.calculate_risk_score()),
            "risk_level": self.risk_level.value
        }


@dataclass
class RiskAlert:
    """Represents a risk alert or notification."""
    alert_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    risk_type: RiskType = RiskType.MARKET_RISK
    severity: RiskLevel = RiskLevel.MEDIUM
    title: str = ""
    message: str = ""
    
    # Context
    entity_id: Optional[str] = None  # portfolio_id, strategy_id, etc.
    entity_type: Optional[str] = None  # "portfolio", "strategy", "position"
    limit_id: Optional[str] = None  # Associated risk limit
    
    # Alert details
    current_value: Optional[Decimal] = None
    threshold_value: Optional[Decimal] = None
    breach_percentage: Optional[Decimal] = None
    
    # Status
    is_active: bool = True
    is_acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    
    # Actions
    recommended_actions: List[str] = field(default_factory=list)
    actions_taken: List[str] = field(default_factory=list)
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def acknowledge(self, user_id: str, notes: Optional[str] = None) -> None:
        """Acknowledge the alert."""
        self.is_acknowledged = True
        self.acknowledged_by = user_id
        self.acknowledged_at = datetime.utcnow()
        
        if notes:
            self.metadata["acknowledgment_notes"] = notes
        
        logger.info(f"Risk alert {self.alert_id} acknowledged by {user_id}")
    
    def resolve(self, notes: Optional[str] = None) -> None:
        """Resolve the alert."""
        self.is_active = False
        self.resolved_at = datetime.utcnow()
        
        if notes:
            self.metadata["resolution_notes"] = notes
        
        logger.info(f"Risk alert {self.alert_id} resolved")
    
    def add_action_taken(self, action: str) -> None:
        """Add an action that was taken in response to the alert."""
        self.actions_taken.append(action)
        self.metadata["last_action_at"] = datetime.utcnow().isoformat()
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Calculate alert duration."""
        end_time = self.resolved_at or datetime.utcnow()
        return end_time - self.created_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "alert_id": self.alert_id,
            "risk_type": self.risk_type.value,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "limit_id": self.limit_id,
            "current_value": float(self.current_value) if self.current_value else None,
            "threshold_value": float(self.threshold_value) if self.threshold_value else None,
            "breach_percentage": float(self.breach_percentage) if self.breach_percentage else None,
            "is_active": self.is_active,
            "is_acknowledged": self.is_acknowledged,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "duration_seconds": self.duration.total_seconds() if self.duration else None,
            "recommended_actions": self.recommended_actions,
            "actions_taken": self.actions_taken,
            "tags": self.tags,
            "metadata": self.metadata
        }


class RiskManager:
    """Comprehensive risk management system."""
    
    def __init__(self):
        self.limits: Dict[str, RiskLimit] = {}
        self.metrics: Dict[str, RiskMetrics] = {}  # entity_id -> latest metrics
        self.alerts: Dict[str, RiskAlert] = {}
        self.metrics_history: Dict[str, List[RiskMetrics]] = {}  # entity_id -> historical metrics
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def add_limit(self, limit: RiskLimit) -> None:
        """Add a risk limit."""
        self.limits[limit.limit_id] = limit
        self.logger.info(f"Risk limit added: {limit.limit_id} ({limit.name})")
    
    def get_limit(self, limit_id: str) -> Optional[RiskLimit]:
        """Get risk limit by ID."""
        return self.limits.get(limit_id)
    
    def get_limits_by_scope(self, applies_to: str, scope_id: Optional[str] = None) -> List[RiskLimit]:
        """Get limits by scope."""
        return [
            limit for limit in self.limits.values()
            if limit.applies_to == applies_to and 
            (scope_id is None or limit.scope_id == scope_id)
        ]
    
    def update_limit_value(self, limit_id: str, new_value: Decimal) -> None:
        """Update a risk limit's current value."""
        limit = self.get_limit(limit_id)
        if not limit:
            raise ValueError(f"Risk limit not found: {limit_id}")
        
        limit.update_current_value(new_value)
        
        # Check for breaches and create alerts
        if limit.is_breached and limit.is_active:
            self._create_limit_breach_alert(limit)
    
    def _create_limit_breach_alert(self, limit: RiskLimit) -> None:
        """Create an alert for a limit breach."""
        alert = RiskAlert(
            risk_type=RiskType.MARKET_RISK,  # Default, could be mapped from limit type
            severity=RiskLevel.HIGH if limit.status == RiskStatus.BREACH else RiskLevel.MEDIUM,
            title=f"Risk Limit Breach: {limit.name}",
            message=f"Risk limit '{limit.name}' has been breached. Current: {limit.current_value}, Limit: {limit.value}",
            entity_id=limit.scope_id,
            entity_type=limit.applies_to,
            limit_id=limit.limit_id,
            current_value=limit.current_value,
            threshold_value=limit.value,
            breach_percentage=limit.utilization_pct
        )
        
        # Add recommended actions based on limit type
        if limit.limit_type == RiskLimitType.POSITION_SIZE:
            alert.recommended_actions = ["Reduce position size", "Close positions", "Review position limits"]
        elif limit.limit_type == RiskLimitType.DAILY_LOSS:
            alert.recommended_actions = ["Stop trading", "Review strategies", "Implement stop-loss"]
        elif limit.limit_type == RiskLimitType.DRAWDOWN:
            alert.recommended_actions = ["Reduce risk", "Review portfolio allocation", "Consider hedging"]
        
        self.add_alert(alert)
    
    def update_metrics(self, metrics: RiskMetrics) -> None:
        """Update risk metrics for an entity."""
        entity_id = metrics.entity_id
        
        # Store current metrics
        self.metrics[entity_id] = metrics
        
        # Store in history
        if entity_id not in self.metrics_history:
            self.metrics_history[entity_id] = []
        self.metrics_history[entity_id].append(metrics)
        
        # Keep only last 1000 entries per entity
        if len(self.metrics_history[entity_id]) > 1000:
            self.metrics_history[entity_id] = self.metrics_history[entity_id][-1000:]
        
        # Check for risk threshold breaches
        self._check_metrics_thresholds(metrics)
        
        self.logger.debug(f"Risk metrics updated for {entity_id}")
    
    def _check_metrics_thresholds(self, metrics: RiskMetrics) -> None:
        """Check metrics against predefined thresholds and create alerts."""
        entity_id = metrics.entity_id
        
        # Check VaR thresholds
        if metrics.var_1d_95 and abs(metrics.var_1d_95) > Decimal('0.05'):  # 5% VaR threshold
            self._create_metrics_alert(
                metrics, RiskType.MARKET_RISK, RiskLevel.HIGH,
                "High VaR Detected", f"1-day VaR at 95% confidence exceeds 5%: {metrics.var_1d_95}"
            )
        
        # Check drawdown thresholds
        if abs(metrics.current_drawdown) > Decimal('10'):  # 10% drawdown threshold
            self._create_metrics_alert(
                metrics, RiskType.MARKET_RISK, RiskLevel.HIGH,
                "High Drawdown Alert", f"Current drawdown exceeds 10%: {metrics.current_drawdown}%"
            )
        
        # Check leverage thresholds
        if metrics.leverage_ratio > Decimal('3'):  # 3x leverage threshold
            self._create_metrics_alert(
                metrics, RiskType.LEVERAGE_RISK, RiskLevel.MEDIUM,
                "High Leverage Alert", f"Leverage ratio exceeds 3x: {metrics.leverage_ratio}"
            )
        
        # Check concentration thresholds
        if metrics.largest_position_pct > Decimal('25'):  # 25% concentration threshold
            self._create_metrics_alert(
                metrics, RiskType.CONCENTRATION_RISK, RiskLevel.MEDIUM,
                "High Concentration Alert", f"Largest position exceeds 25%: {metrics.largest_position_pct}%"
            )
    
    def _create_metrics_alert(self, metrics: RiskMetrics, risk_type: RiskType, 
                            severity: RiskLevel, title: str, message: str) -> None:
        """Create an alert based on metrics thresholds."""
        alert = RiskAlert(
            risk_type=risk_type,
            severity=severity,
            title=title,
            message=message,
            entity_id=metrics.entity_id,
            entity_type=metrics.entity_type
        )
        
        self.add_alert(alert)
    
    def add_alert(self, alert: RiskAlert) -> None:
        """Add a risk alert."""
        self.alerts[alert.alert_id] = alert
        self.logger.warning(f"Risk alert created: {alert.title} ({alert.severity.value})")
    
    def get_alert(self, alert_id: str) -> Optional[RiskAlert]:
        """Get alert by ID."""
        return self.alerts.get(alert_id)
    
    def get_active_alerts(self, entity_id: Optional[str] = None) -> List[RiskAlert]:
        """Get active alerts, optionally filtered by entity."""
        alerts = [alert for alert in self.alerts.values() if alert.is_active]
        
        if entity_id:
            alerts = [alert for alert in alerts if alert.entity_id == entity_id]
        
        return sorted(alerts, key=lambda x: x.created_at, reverse=True)
    
    def get_alerts_by_severity(self, severity: RiskLevel) -> List[RiskAlert]:
        """Get alerts by severity level."""
        return [alert for alert in self.alerts.values() if alert.severity == severity]
    
    def acknowledge_alert(self, alert_id: str, user_id: str, notes: Optional[str] = None) -> None:
        """Acknowledge an alert."""
        alert = self.get_alert(alert_id)
        if not alert:
            raise ValueError(f"Alert not found: {alert_id}")
        
        alert.acknowledge(user_id, notes)
    
    def resolve_alert(self, alert_id: str, notes: Optional[str] = None) -> None:
        """Resolve an alert."""
        alert = self.get_alert(alert_id)
        if not alert:
            raise ValueError(f"Alert not found: {alert_id}")
        
        alert.resolve(notes)
    
    def get_risk_summary(self, entity_id: Optional[str] = None) -> Dict[str, Any]:
        """Get comprehensive risk summary."""
        # Get metrics
        if entity_id:
            metrics = self.metrics.get(entity_id)
            metrics_list = [metrics] if metrics else []
        else:
            metrics_list = list(self.metrics.values())
        
        # Get limits
        if entity_id:
            limits = self.get_limits_by_scope("portfolio", entity_id)  # Assuming portfolio scope
        else:
            limits = list(self.limits.values())
        
        # Get alerts
        alerts = self.get_active_alerts(entity_id)
        
        # Calculate summary statistics
        breached_limits = [limit for limit in limits if limit.is_breached]
        warning_limits = [limit for limit in limits if limit.is_warning]
        
        critical_alerts = [alert for alert in alerts if alert.severity == RiskLevel.CRITICAL]
        high_alerts = [alert for alert in alerts if alert.severity == RiskLevel.HIGH]
        
        # Overall risk level
        overall_risk = RiskLevel.LOW
        if critical_alerts or breached_limits:
            overall_risk = RiskLevel.CRITICAL
        elif high_alerts or len(warning_limits) > 2:
            overall_risk = RiskLevel.HIGH
        elif alerts or warning_limits:
            overall_risk = RiskLevel.MEDIUM
        
        return {
            "entity_id": entity_id,
            "overall_risk_level": overall_risk.value,
            "total_limits": len(limits),
            "breached_limits": len(breached_limits),
            "warning_limits": len(warning_limits),
            "active_alerts": len(alerts),
            "critical_alerts": len(critical_alerts),
            "high_alerts": len(high_alerts),
            "latest_metrics": metrics_list[0].to_dict() if metrics_list else None,
            "recent_alerts": [alert.to_dict() for alert in alerts[:5]],  # Last 5 alerts
            "limit_utilization": {
                limit.name: float(limit.utilization_pct) 
                for limit in limits if limit.is_active
            }
        }
    
    def run_stress_test(self, entity_id: str, scenarios: Dict[str, Decimal]) -> Dict[str, Decimal]:
        """Run stress test scenarios."""
        results = {}
        
        # Get current metrics
        current_metrics = self.metrics.get(entity_id)
        if not current_metrics:
            return results
        
        # Run each scenario
        for scenario_name, shock_factor in scenarios.items():
            # Simple stress test: apply shock to current portfolio value
            if current_metrics.net_exposure:
                stressed_value = current_metrics.net_exposure * (1 + shock_factor)
                stress_pnl = stressed_value - current_metrics.net_exposure
                results[scenario_name] = stress_pnl
        
        # Update metrics with stress test results
        if current_metrics:
            current_metrics.stress_test_results = results
        
        return results
    
    def get_manager_summary(self) -> Dict[str, Any]:
        """Get risk manager summary."""
        all_limits = list(self.limits.values())
        all_alerts = list(self.alerts.values())
        active_alerts = [alert for alert in all_alerts if alert.is_active]
        
        return {
            "total_limits": len(all_limits),
            "active_limits": len([limit for limit in all_limits if limit.is_active]),
            "breached_limits": len([limit for limit in all_limits if limit.is_breached]),
            "total_alerts": len(all_alerts),
            "active_alerts": len(active_alerts),
            "critical_alerts": len([alert for alert in active_alerts if alert.severity == RiskLevel.CRITICAL]),
            "entities_monitored": len(self.metrics),
            "metrics_history_size": sum(len(history) for history in self.metrics_history.values())
        }