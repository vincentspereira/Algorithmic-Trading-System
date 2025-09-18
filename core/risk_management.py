"""Risk management module for the algorithmic trading system.

This module provides risk management functionality including position sizing,
risk limits, and portfolio risk monitoring.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import numpy as np

from .data_types import Position, Order, Trade, OrderSide
from .events import Event, EventType

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk level enumeration."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskLimitType(Enum):
    """Risk limit type enumeration."""
    POSITION_SIZE = "POSITION_SIZE"
    PORTFOLIO_VALUE = "PORTFOLIO_VALUE"
    DAILY_LOSS = "DAILY_LOSS"
    DRAWDOWN = "DRAWDOWN"
    LEVERAGE = "LEVERAGE"
    CONCENTRATION = "CONCENTRATION"
    VAR = "VAR"  # Value at Risk


@dataclass
class RiskLimit:
    """Risk limit configuration."""
    limit_type: RiskLimitType
    threshold: float
    warning_threshold: Optional[float] = None
    enabled: bool = True
    description: str = ""
    
    def __post_init__(self):
        if self.warning_threshold is None:
            self.warning_threshold = self.threshold * 0.8


@dataclass
class RiskMetrics:
    """Risk metrics container."""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    portfolio_value: float = 0.0
    total_exposure: float = 0.0
    leverage: float = 0.0
    daily_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    var_1d: Optional[float] = None
    var_5d: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    concentration_risk: Dict[str, float] = field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.LOW
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "portfolio_value": self.portfolio_value,
            "total_exposure": self.total_exposure,
            "leverage": self.leverage,
            "daily_pnl": self.daily_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "realized_pnl": self.realized_pnl,
            "max_drawdown": self.max_drawdown,
            "current_drawdown": self.current_drawdown,
            "var_1d": self.var_1d,
            "var_5d": self.var_5d,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "concentration_risk": self.concentration_risk,
            "risk_level": self.risk_level.value
        }


class RiskManager:
    """Risk management system.
    
    Monitors portfolio risk, enforces risk limits, and provides
    risk metrics and alerts.
    """
    
    def __init__(self, initial_capital: float = 1000000.0):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions: Dict[str, Position] = {}
        self.risk_limits: Dict[RiskLimitType, RiskLimit] = {}
        self.risk_history: List[RiskMetrics] = []
        self.daily_pnl_history: List[Tuple[datetime, float]] = []
        self.high_water_mark = initial_capital
        self.max_drawdown = 0.0
        
        # Set default risk limits
        self._set_default_limits()
        
        logger.info(f"RiskManager initialized with capital: ${initial_capital:,.2f}")
    
    def _set_default_limits(self):
        """Set default risk limits."""
        self.risk_limits = {
            RiskLimitType.POSITION_SIZE: RiskLimit(
                RiskLimitType.POSITION_SIZE,
                threshold=0.1,  # 10% of portfolio per position
                description="Maximum position size as % of portfolio"
            ),
            RiskLimitType.DAILY_LOSS: RiskLimit(
                RiskLimitType.DAILY_LOSS,
                threshold=0.02,  # 2% daily loss limit
                description="Maximum daily loss as % of portfolio"
            ),
            RiskLimitType.DRAWDOWN: RiskLimit(
                RiskLimitType.DRAWDOWN,
                threshold=0.15,  # 15% maximum drawdown
                description="Maximum drawdown from high water mark"
            ),
            RiskLimitType.LEVERAGE: RiskLimit(
                RiskLimitType.LEVERAGE,
                threshold=2.0,  # 2x leverage limit
                description="Maximum leverage ratio"
            ),
            RiskLimitType.CONCENTRATION: RiskLimit(
                RiskLimitType.CONCENTRATION,
                threshold=0.25,  # 25% concentration limit
                description="Maximum concentration in single asset"
            )
        }
    
    def set_risk_limit(self, limit_type: RiskLimitType, threshold: float, 
                      warning_threshold: Optional[float] = None, 
                      description: str = ""):
        """Set or update a risk limit."""
        self.risk_limits[limit_type] = RiskLimit(
            limit_type=limit_type,
            threshold=threshold,
            warning_threshold=warning_threshold,
            description=description
        )
        logger.info(f"Risk limit updated: {limit_type.value} = {threshold}")
    
    def update_position(self, position: Position):
        """Update position in risk manager."""
        self.positions[position.symbol] = position
    
    def remove_position(self, symbol: str):
        """Remove position from risk manager."""
        if symbol in self.positions:
            del self.positions[symbol]
    
    def validate_order(self, order: Order) -> Tuple[bool, str]:
        """Validate order against risk limits.
        
        Returns:
            Tuple of (is_valid, reason)
        """
        try:
            # Check position size limit
            if not self._check_position_size_limit(order):
                return False, f"Order exceeds position size limit for {order.symbol}"
            
            # Check leverage limit
            if not self._check_leverage_limit(order):
                return False, "Order would exceed leverage limit"
            
            # Check concentration limit
            if not self._check_concentration_limit(order):
                return False, f"Order would exceed concentration limit for {order.symbol}"
            
            # Check if we have sufficient capital
            if not self._check_capital_requirement(order):
                return False, "Insufficient capital for order"
            
            return True, "Order validated successfully"
            
        except Exception as e:
            logger.error(f"Error validating order: {e}")
            return False, f"Validation error: {str(e)}"
    
    def _check_position_size_limit(self, order: Order) -> bool:
        """Check if order respects position size limits."""
        limit = self.risk_limits.get(RiskLimitType.POSITION_SIZE)
        if not limit or not limit.enabled:
            return True
        
        # Calculate new position size after order
        current_position = self.positions.get(order.symbol)
        current_quantity = current_position.quantity if current_position else 0.0
        
        if order.is_buy:
            new_quantity = current_quantity + order.quantity
        else:
            new_quantity = current_quantity - order.quantity
        
        # Estimate position value
        estimated_price = order.price or 100.0  # Use order price or default
        position_value = abs(new_quantity) * estimated_price
        position_percentage = position_value / self.current_capital
        
        return position_percentage <= limit.threshold
    
    def _check_leverage_limit(self, order: Order) -> bool:
        """Check if order respects leverage limits."""
        limit = self.risk_limits.get(RiskLimitType.LEVERAGE)
        if not limit or not limit.enabled:
            return True
        
        # Calculate total exposure after order
        current_exposure = sum(abs(pos.market_value) for pos in self.positions.values())
        
        estimated_price = order.price or 100.0
        order_value = order.quantity * estimated_price
        new_exposure = current_exposure + order_value
        
        leverage = new_exposure / self.current_capital
        return leverage <= limit.threshold
    
    def _check_concentration_limit(self, order: Order) -> bool:
        """Check if order respects concentration limits."""
        limit = self.risk_limits.get(RiskLimitType.CONCENTRATION)
        if not limit or not limit.enabled:
            return True
        
        # Calculate concentration after order
        current_position = self.positions.get(order.symbol)
        current_value = current_position.market_value if current_position else 0.0
        
        estimated_price = order.price or 100.0
        order_value = order.quantity * estimated_price
        new_value = current_value + order_value
        
        concentration = new_value / self.current_capital
        return concentration <= limit.threshold
    
    def _check_capital_requirement(self, order: Order) -> bool:
        """Check if we have sufficient capital for the order."""
        if order.order_type.value in ['MARKET', 'LIMIT']:
            estimated_price = order.price or 100.0
            required_capital = order.quantity * estimated_price
            
            # For buy orders, check if we have enough cash
            if order.is_buy:
                available_cash = self._calculate_available_cash()
                return available_cash >= required_capital
            
            # For sell orders, check if we have enough position
            else:
                current_position = self.positions.get(order.symbol)
                if current_position and current_position.is_long:
                    return current_position.quantity >= order.quantity
                elif current_position and current_position.is_short:
                    return True  # Can always add to short position (in theory)
                else:
                    return True  # Can open short position (in theory)
        
        return True
    
    def _calculate_available_cash(self) -> float:
        """Calculate available cash for new positions."""
        total_position_value = sum(pos.market_value for pos in self.positions.values())
        return self.current_capital - total_position_value
    
    def calculate_risk_metrics(self) -> RiskMetrics:
        """Calculate current risk metrics."""
        # Calculate portfolio metrics
        portfolio_value = self.current_capital
        total_exposure = sum(abs(pos.market_value) for pos in self.positions.values())
        leverage = total_exposure / portfolio_value if portfolio_value > 0 else 0.0
        
        # Calculate PnL
        unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        realized_pnl = sum(pos.realized_pnl for pos in self.positions.values())
        total_pnl = unrealized_pnl + realized_pnl
        
        # Calculate drawdown
        current_value = self.initial_capital + total_pnl
        if current_value > self.high_water_mark:
            self.high_water_mark = current_value
        
        current_drawdown = (self.high_water_mark - current_value) / self.high_water_mark
        if current_drawdown > self.max_drawdown:
            self.max_drawdown = current_drawdown
        
        # Calculate concentration risk
        concentration_risk = {}
        if portfolio_value > 0:
            for symbol, position in self.positions.items():
                concentration_risk[symbol] = abs(position.market_value) / portfolio_value
        
        # Determine risk level
        risk_level = self._assess_risk_level(leverage, current_drawdown, concentration_risk)
        
        # Calculate daily PnL
        daily_pnl = 0.0
        if self.daily_pnl_history:
            today = datetime.now().date()
            today_pnl = [pnl for date, pnl in self.daily_pnl_history if date.date() == today]
            daily_pnl = sum(today_pnl)
        
        metrics = RiskMetrics(
            portfolio_value=portfolio_value,
            total_exposure=total_exposure,
            leverage=leverage,
            daily_pnl=daily_pnl,
            unrealized_pnl=unrealized_pnl,
            realized_pnl=realized_pnl,
            max_drawdown=self.max_drawdown,
            current_drawdown=current_drawdown,
            concentration_risk=concentration_risk,
            risk_level=risk_level
        )
        
        # Store metrics history
        self.risk_history.append(metrics)
        
        # Keep only last 1000 entries
        if len(self.risk_history) > 1000:
            self.risk_history = self.risk_history[-1000:]
        
        return metrics
    
    def _assess_risk_level(self, leverage: float, drawdown: float, 
                          concentration: Dict[str, float]) -> RiskLevel:
        """Assess overall risk level based on metrics."""
        risk_score = 0
        
        # Leverage risk
        if leverage > 3.0:
            risk_score += 3
        elif leverage > 2.0:
            risk_score += 2
        elif leverage > 1.5:
            risk_score += 1
        
        # Drawdown risk
        if drawdown > 0.20:
            risk_score += 3
        elif drawdown > 0.15:
            risk_score += 2
        elif drawdown > 0.10:
            risk_score += 1
        
        # Concentration risk
        max_concentration = max(concentration.values()) if concentration else 0
        if max_concentration > 0.50:
            risk_score += 3
        elif max_concentration > 0.30:
            risk_score += 2
        elif max_concentration > 0.20:
            risk_score += 1
        
        # Determine risk level
        if risk_score >= 7:
            return RiskLevel.CRITICAL
        elif risk_score >= 5:
            return RiskLevel.HIGH
        elif risk_score >= 3:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def check_risk_limits(self) -> List[Event]:
        """Check all risk limits and generate alerts."""
        alerts = []
        metrics = self.calculate_risk_metrics()
        
        # Check each risk limit
        for limit_type, limit in self.risk_limits.items():
            if not limit.enabled:
                continue
            
            current_value = self._get_metric_value(metrics, limit_type)
            if current_value is None:
                continue
            
            # Check if limit is breached
            if current_value > limit.threshold:
                alert = Event(
                    event_type=EventType.RISK_LIMIT_EXCEEDED,
                    data={
                        "limit_type": limit_type.value,
                        "current_value": current_value,
                        "threshold": limit.threshold,
                        "description": limit.description,
                        "severity": "CRITICAL"
                    }
                )
                alerts.append(alert)
            
            # Check warning threshold
            elif limit.warning_threshold and current_value > limit.warning_threshold:
                alert = Event(
                    event_type=EventType.WARNING,
                    data={
                        "limit_type": limit_type.value,
                        "current_value": current_value,
                        "warning_threshold": limit.warning_threshold,
                        "threshold": limit.threshold,
                        "description": limit.description,
                        "severity": "WARNING"
                    }
                )
                alerts.append(alert)
        
        return alerts
    
    def _get_metric_value(self, metrics: RiskMetrics, limit_type: RiskLimitType) -> Optional[float]:
        """Get metric value for a specific limit type."""
        if limit_type == RiskLimitType.LEVERAGE:
            return metrics.leverage
        elif limit_type == RiskLimitType.DRAWDOWN:
            return metrics.current_drawdown
        elif limit_type == RiskLimitType.DAILY_LOSS:
            return abs(metrics.daily_pnl) / metrics.portfolio_value if metrics.portfolio_value > 0 else 0
        elif limit_type == RiskLimitType.CONCENTRATION:
            return max(metrics.concentration_risk.values()) if metrics.concentration_risk else 0
        else:
            return None
    
    def add_trade(self, trade: Trade):
        """Add trade and update risk metrics."""
        # Update daily PnL history
        self.daily_pnl_history.append((trade.timestamp, trade.net_value))
        
        # Keep only last 30 days
        cutoff_date = datetime.now() - timedelta(days=30)
        self.daily_pnl_history = [
            (date, pnl) for date, pnl in self.daily_pnl_history 
            if date > cutoff_date
        ]
        
        logger.info(f"Trade added to risk manager: {trade.symbol} {trade.side.value} {trade.quantity}@{trade.price}")
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get comprehensive risk summary."""
        metrics = self.calculate_risk_metrics()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "risk_level": metrics.risk_level.value,
            "portfolio_value": metrics.portfolio_value,
            "total_positions": len(self.positions),
            "leverage": metrics.leverage,
            "current_drawdown": metrics.current_drawdown,
            "max_drawdown": metrics.max_drawdown,
            "daily_pnl": metrics.daily_pnl,
            "unrealized_pnl": metrics.unrealized_pnl,
            "realized_pnl": metrics.realized_pnl,
            "risk_limits": {
                limit_type.value: {
                    "threshold": limit.threshold,
                    "warning_threshold": limit.warning_threshold,
                    "enabled": limit.enabled,
                    "description": limit.description
                }
                for limit_type, limit in self.risk_limits.items()
            },
            "positions": {
                symbol: position.to_dict() 
                for symbol, position in self.positions.items()
            }
        }