"""Risk Management System

Comprehensive risk management with position limits, drawdown controls,
exposure monitoring, and real-time risk assessment.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import asyncio
import math
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass
import logging

from pydantic import BaseModel, Field, validator
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.database_manager import DatabaseManager, Order, Position, TradingAccount
from shared.utils.logging_utils import get_logger

logger = get_logger(__name__)

# ===========================================
# ENUMS AND CONSTANTS
# ===========================================

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class RiskCheckResult(str, Enum):
    APPROVED = "APPROVED"
    WARNING = "WARNING"
    REJECTED = "REJECTED"

class RiskMetricType(str, Enum):
    POSITION_SIZE = "POSITION_SIZE"
    PORTFOLIO_EXPOSURE = "PORTFOLIO_EXPOSURE"
    DRAWDOWN = "DRAWDOWN"
    VAR = "VAR"  # Value at Risk
    CONCENTRATION = "CONCENTRATION"
    LEVERAGE = "LEVERAGE"
    CORRELATION = "CORRELATION"

class RiskViolationType(str, Enum):
    POSITION_LIMIT = "POSITION_LIMIT"
    PORTFOLIO_LIMIT = "PORTFOLIO_LIMIT"
    DRAWDOWN_LIMIT = "DRAWDOWN_LIMIT"
    EXPOSURE_LIMIT = "EXPOSURE_LIMIT"
    CONCENTRATION_LIMIT = "CONCENTRATION_LIMIT"
    LEVERAGE_LIMIT = "LEVERAGE_LIMIT"
    LOSS_LIMIT = "LOSS_LIMIT"

# ===========================================
# DATA MODELS
# ===========================================

@dataclass
class RiskLimits:
    """Risk limits configuration"""
    max_position_size: float = 10000  # Maximum position size per symbol
    max_position_value: float = 100000  # Maximum position value per symbol
    max_portfolio_exposure: float = 500000  # Maximum total portfolio exposure
    max_daily_loss: float = 5000  # Maximum daily loss
    max_drawdown_percent: float = 10.0  # Maximum drawdown percentage
    max_concentration_percent: float = 20.0  # Maximum concentration per symbol
    max_leverage: float = 2.0  # Maximum leverage ratio
    max_correlation_exposure: float = 0.7  # Maximum correlated exposure
    var_confidence_level: float = 0.95  # VaR confidence level
    var_time_horizon: int = 1  # VaR time horizon in days

@dataclass
class RiskMetric:
    """Risk metric data"""
    metric_type: RiskMetricType
    current_value: float
    limit_value: float
    utilization_percent: float
    risk_level: RiskLevel
    timestamp: datetime
    metadata: Dict[str, Any] = None

@dataclass
class RiskViolation:
    """Risk violation data"""
    violation_type: RiskViolationType
    severity: RiskLevel
    current_value: float
    limit_value: float
    excess_amount: float
    symbol: Optional[str] = None
    account_id: Optional[str] = None
    message: str = ""
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)

class RiskAssessmentRequest(BaseModel):
    """Risk assessment request"""
    account_id: str
    symbol: str
    side: str  # BUY/SELL
    quantity: float
    price: Optional[float] = None
    order_type: str = "MARKET"
    
class RiskAssessmentResponse(BaseModel):
    """Risk assessment response"""
    result: RiskCheckResult
    risk_level: RiskLevel
    violations: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    metrics: List[Dict[str, Any]] = Field(default_factory=list)
    approved_quantity: Optional[float] = None
    rejection_reason: Optional[str] = None
    
class PortfolioRiskSummary(BaseModel):
    """Portfolio risk summary"""
    account_id: str
    total_exposure: float
    available_buying_power: float
    current_leverage: float
    daily_pnl: float
    total_pnl: float
    max_drawdown: float
    var_95: Optional[float] = None
    risk_level: RiskLevel
    active_violations: List[Dict[str, Any]] = Field(default_factory=list)
    risk_metrics: List[Dict[str, Any]] = Field(default_factory=list)
    last_updated: datetime

# ===========================================
# RISK MANAGEMENT ENGINE
# ===========================================

class RiskManager:
    """Comprehensive risk management system"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.risk_limits: Dict[str, RiskLimits] = {}  # Account-specific limits
        self.default_limits = RiskLimits()
        self.risk_cache: Dict[str, Dict] = {}  # Cache for risk calculations
        self.violation_history: List[RiskViolation] = []
        
    async def initialize(self):
        """Initialize risk manager"""
        await self._load_risk_limits()
        logger.info("Risk Manager initialized successfully")
    
    async def assess_order_risk(
        self, 
        request: RiskAssessmentRequest, 
        user_id: str
    ) -> RiskAssessmentResponse:
        """Comprehensive risk assessment for order placement"""
        try:
            violations = []
            warnings = []
            metrics = []
            
            # Get account limits
            limits = self._get_account_limits(request.account_id)
            
            # Get current portfolio state
            portfolio_state = await self._get_portfolio_state(request.account_id, user_id)
            
            # Calculate order value
            order_value = self._calculate_order_value(request)
            
            # 1. Position Size Check
            position_check = await self._check_position_limits(
                request, portfolio_state, limits, order_value
            )
            if position_check["violations"]:
                violations.extend(position_check["violations"])
            if position_check["warnings"]:
                warnings.extend(position_check["warnings"])
            metrics.append(position_check["metric"])
            
            # 2. Portfolio Exposure Check
            exposure_check = await self._check_exposure_limits(
                request, portfolio_state, limits, order_value
            )
            if exposure_check["violations"]:
                violations.extend(exposure_check["violations"])
            metrics.append(exposure_check["metric"])
            
            # 3. Concentration Check
            concentration_check = await self._check_concentration_limits(
                request, portfolio_state, limits, order_value
            )
            if concentration_check["violations"]:
                violations.extend(concentration_check["violations"])
            metrics.append(concentration_check["metric"])
            
            # 4. Drawdown Check
            drawdown_check = await self._check_drawdown_limits(
                request, portfolio_state, limits
            )
            if drawdown_check["violations"]:
                violations.extend(drawdown_check["violations"])
            metrics.append(drawdown_check["metric"])
            
            # 5. Leverage Check
            leverage_check = await self._check_leverage_limits(
                request, portfolio_state, limits, order_value
            )
            if leverage_check["violations"]:
                violations.extend(leverage_check["violations"])
            metrics.append(leverage_check["metric"])
            
            # Determine overall result
            if violations:
                result = RiskCheckResult.REJECTED
                risk_level = max([v["severity"] for v in violations], key=lambda x: ["LOW", "MEDIUM", "HIGH", "CRITICAL"].index(x))
                rejection_reason = f"Risk violations: {', '.join([v['message'] for v in violations])}"
                approved_quantity = None
            elif warnings:
                result = RiskCheckResult.WARNING
                risk_level = RiskLevel.MEDIUM
                rejection_reason = None
                approved_quantity = request.quantity
            else:
                result = RiskCheckResult.APPROVED
                risk_level = RiskLevel.LOW
                rejection_reason = None
                approved_quantity = request.quantity
            
            # Log risk assessment
            logger.info(
                f"Risk assessment completed for {request.symbol}: {result.value}, "
                f"Risk Level: {risk_level}, Violations: {len(violations)}, Warnings: {len(warnings)}"
            )
            
            return RiskAssessmentResponse(
                result=result,
                risk_level=RiskLevel(risk_level),
                violations=violations,
                warnings=warnings,
                metrics=metrics,
                approved_quantity=approved_quantity,
                rejection_reason=rejection_reason
            )
            
        except Exception as e:
            logger.error(f"Error in risk assessment: {e}")
            return RiskAssessmentResponse(
                result=RiskCheckResult.REJECTED,
                risk_level=RiskLevel.CRITICAL,
                rejection_reason=f"Risk assessment failed: {str(e)}"
            )
    
    async def get_portfolio_risk_summary(
        self, 
        account_id: str, 
        user_id: str
    ) -> PortfolioRiskSummary:
        """Get comprehensive portfolio risk summary"""
        try:
            # Get portfolio state
            portfolio_state = await self._get_portfolio_state(account_id, user_id)
            limits = self._get_account_limits(account_id)
            
            # Calculate risk metrics
            total_exposure = sum(abs(pos["market_value"]) for pos in portfolio_state["positions"])
            current_leverage = total_exposure / max(portfolio_state["account_value"], 1)
            
            # Calculate drawdown
            max_drawdown = await self._calculate_max_drawdown(account_id, user_id)
            
            # Calculate VaR (simplified)
            var_95 = await self._calculate_var(portfolio_state, 0.95)
            
            # Determine overall risk level
            risk_level = self._determine_portfolio_risk_level(
                current_leverage, max_drawdown, total_exposure, limits
            )
            
            # Get active violations
            active_violations = await self._get_active_violations(account_id)
            
            # Build risk metrics
            risk_metrics = [
                {
                    "type": "EXPOSURE",
                    "current": total_exposure,
                    "limit": limits.max_portfolio_exposure,
                    "utilization": (total_exposure / limits.max_portfolio_exposure) * 100
                },
                {
                    "type": "LEVERAGE",
                    "current": current_leverage,
                    "limit": limits.max_leverage,
                    "utilization": (current_leverage / limits.max_leverage) * 100
                },
                {
                    "type": "DRAWDOWN",
                    "current": max_drawdown,
                    "limit": limits.max_drawdown_percent,
                    "utilization": (max_drawdown / limits.max_drawdown_percent) * 100
                }
            ]
            
            return PortfolioRiskSummary(
                account_id=account_id,
                total_exposure=total_exposure,
                available_buying_power=portfolio_state["buying_power"],
                current_leverage=current_leverage,
                daily_pnl=portfolio_state["daily_pnl"],
                total_pnl=portfolio_state["total_pnl"],
                max_drawdown=max_drawdown,
                var_95=var_95,
                risk_level=risk_level,
                active_violations=active_violations,
                risk_metrics=risk_metrics,
                last_updated=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            logger.error(f"Error getting portfolio risk summary: {e}")
            raise Exception(f"Failed to get portfolio risk summary: {str(e)}")
    
    async def monitor_real_time_risk(self, account_id: str, user_id: str) -> List[RiskViolation]:
        """Monitor real-time risk violations"""
        try:
            violations = []
            
            # Get current portfolio state
            portfolio_state = await self._get_portfolio_state(account_id, user_id)
            limits = self._get_account_limits(account_id)
            
            # Check for violations
            total_exposure = sum(abs(pos["market_value"]) for pos in portfolio_state["positions"])
            
            # Portfolio exposure violation
            if total_exposure > limits.max_portfolio_exposure:
                violations.append(RiskViolation(
                    violation_type=RiskViolationType.EXPOSURE_LIMIT,
                    severity=RiskLevel.HIGH,
                    current_value=total_exposure,
                    limit_value=limits.max_portfolio_exposure,
                    excess_amount=total_exposure - limits.max_portfolio_exposure,
                    account_id=account_id,
                    message=f"Portfolio exposure ${total_exposure:,.2f} exceeds limit ${limits.max_portfolio_exposure:,.2f}"
                ))
            
            # Daily loss violation
            if portfolio_state["daily_pnl"] < -limits.max_daily_loss:
                violations.append(RiskViolation(
                    violation_type=RiskViolationType.LOSS_LIMIT,
                    severity=RiskLevel.CRITICAL,
                    current_value=abs(portfolio_state["daily_pnl"]),
                    limit_value=limits.max_daily_loss,
                    excess_amount=abs(portfolio_state["daily_pnl"]) - limits.max_daily_loss,
                    account_id=account_id,
                    message=f"Daily loss ${abs(portfolio_state['daily_pnl']):,.2f} exceeds limit ${limits.max_daily_loss:,.2f}"
                ))
            
            # Drawdown violation
            max_drawdown = await self._calculate_max_drawdown(account_id, user_id)
            if max_drawdown > limits.max_drawdown_percent:
                violations.append(RiskViolation(
                    violation_type=RiskViolationType.DRAWDOWN_LIMIT,
                    severity=RiskLevel.HIGH,
                    current_value=max_drawdown,
                    limit_value=limits.max_drawdown_percent,
                    excess_amount=max_drawdown - limits.max_drawdown_percent,
                    account_id=account_id,
                    message=f"Drawdown {max_drawdown:.2f}% exceeds limit {limits.max_drawdown_percent:.2f}%"
                ))
            
            # Position concentration violations
            for position in portfolio_state["positions"]:
                concentration = (abs(position["market_value"]) / max(portfolio_state["account_value"], 1)) * 100
                if concentration > limits.max_concentration_percent:
                    violations.append(RiskViolation(
                        violation_type=RiskViolationType.CONCENTRATION_LIMIT,
                        severity=RiskLevel.MEDIUM,
                        current_value=concentration,
                        limit_value=limits.max_concentration_percent,
                        excess_amount=concentration - limits.max_concentration_percent,
                        symbol=position["symbol"],
                        account_id=account_id,
                        message=f"Position concentration {concentration:.2f}% in {position['symbol']} exceeds limit {limits.max_concentration_percent:.2f}%"
                    ))
            
            # Store violations for history
            self.violation_history.extend(violations)
            
            return violations
            
        except Exception as e:
            logger.error(f"Error monitoring real-time risk: {e}")
            return []
    
    async def update_risk_limits(self, account_id: str, new_limits: RiskLimits):
        """Update risk limits for an account"""
        try:
            self.risk_limits[account_id] = new_limits
            
            # Store in database (would implement persistent storage)
            logger.info(f"Risk limits updated for account {account_id}")
            
        except Exception as e:
            logger.error(f"Error updating risk limits: {e}")
            raise Exception(f"Failed to update risk limits: {str(e)}")
    
    # ===========================================
    # PRIVATE HELPER METHODS
    # ===========================================
    
    async def _load_risk_limits(self):
        """Load risk limits from database"""
        # This would load account-specific limits from database
        # For now, use default limits for all accounts
        pass
    
    def _get_account_limits(self, account_id: str) -> RiskLimits:
        """Get risk limits for account"""
        return self.risk_limits.get(account_id, self.default_limits)
    
    async def _get_portfolio_state(self, account_id: str, user_id: str) -> Dict[str, Any]:
        """Get current portfolio state"""
        try:
            # Get positions
            async with self.db_manager.get_postgres_session() as session:
                # Get positions
                positions_stmt = select(Position).where(
                    and_(Position.account_id == account_id, Position.user_id == user_id)
                )
                positions_result = await session.execute(positions_stmt)
                positions = positions_result.fetchall()
                
                # Get orders
                orders_stmt = select(Order).where(
                    and_(
                        Order.account_id == account_id,
                        Order.user_id == user_id,
                        Order.status.in_(["PENDING", "SUBMITTED", "PARTIALLY_FILLED"])
                    )
                )
                orders_result = await session.execute(orders_stmt)
                orders = orders_result.fetchall()
            
            # Calculate portfolio metrics
            positions_data = []
            total_value = 0
            daily_pnl = 0
            total_pnl = 0
            
            for pos in positions:
                pos_data = {
                    "symbol": pos.Position.symbol,
                    "quantity": pos.Position.quantity,
                    "avg_cost": pos.Position.avg_cost,
                    "market_value": pos.Position.market_value or 0,
                    "unrealized_pnl": pos.Position.unrealized_pnl or 0,
                    "realized_pnl": pos.Position.realized_pnl or 0
                }
                positions_data.append(pos_data)
                total_value += abs(pos_data["market_value"])
                daily_pnl += pos_data["unrealized_pnl"]
                total_pnl += pos_data["realized_pnl"] + pos_data["unrealized_pnl"]
            
            # Calculate buying power (simplified)
            buying_power = max(100000 - total_value, 0)  # Placeholder calculation
            
            return {
                "account_id": account_id,
                "positions": positions_data,
                "orders": [{
                    "symbol": order.Order.symbol,
                    "side": order.Order.side,
                    "quantity": order.Order.quantity,
                    "price": order.Order.price,
                    "status": order.Order.status
                } for order in orders],
                "account_value": total_value,
                "buying_power": buying_power,
                "daily_pnl": daily_pnl,
                "total_pnl": total_pnl
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio state: {e}")
            return {
                "account_id": account_id,
                "positions": [],
                "orders": [],
                "account_value": 0,
                "buying_power": 0,
                "daily_pnl": 0,
                "total_pnl": 0
            }
    
    def _calculate_order_value(self, request: RiskAssessmentRequest) -> float:
        """Calculate order value"""
        if request.price:
            return request.quantity * request.price
        else:
            # For market orders, estimate using last known price (placeholder)
            return request.quantity * 100  # Placeholder price
    
    async def _check_position_limits(
        self, 
        request: RiskAssessmentRequest, 
        portfolio_state: Dict, 
        limits: RiskLimits, 
        order_value: float
    ) -> Dict[str, Any]:
        """Check position size limits"""
        violations = []
        warnings = []
        
        # Find existing position
        existing_position = None
        for pos in portfolio_state["positions"]:
            if pos["symbol"] == request.symbol:
                existing_position = pos
                break
        
        # Calculate new position size
        current_quantity = existing_position["quantity"] if existing_position else 0
        if request.side == "BUY":
            new_quantity = current_quantity + request.quantity
        else:
            new_quantity = current_quantity - request.quantity
        
        new_position_value = abs(new_quantity * (request.price or 100))
        
        # Check limits
        if abs(new_quantity) > limits.max_position_size:
            violations.append({
                "type": "POSITION_SIZE",
                "severity": "HIGH",
                "message": f"Position size {abs(new_quantity)} exceeds limit {limits.max_position_size}",
                "current": abs(new_quantity),
                "limit": limits.max_position_size
            })
        
        if new_position_value > limits.max_position_value:
            violations.append({
                "type": "POSITION_VALUE",
                "severity": "HIGH",
                "message": f"Position value ${new_position_value:,.2f} exceeds limit ${limits.max_position_value:,.2f}",
                "current": new_position_value,
                "limit": limits.max_position_value
            })
        
        # Warning at 80% of limit
        if abs(new_quantity) > limits.max_position_size * 0.8:
            warnings.append(f"Position size approaching limit: {abs(new_quantity)}/{limits.max_position_size}")
        
        metric = {
            "type": "POSITION_SIZE",
            "symbol": request.symbol,
            "current": abs(new_quantity),
            "limit": limits.max_position_size,
            "utilization": (abs(new_quantity) / limits.max_position_size) * 100
        }
        
        return {
            "violations": violations,
            "warnings": warnings,
            "metric": metric
        }
    
    async def _check_exposure_limits(
        self, 
        request: RiskAssessmentRequest, 
        portfolio_state: Dict, 
        limits: RiskLimits, 
        order_value: float
    ) -> Dict[str, Any]:
        """Check portfolio exposure limits"""
        violations = []
        
        current_exposure = sum(abs(pos["market_value"]) for pos in portfolio_state["positions"])
        new_exposure = current_exposure + order_value
        
        if new_exposure > limits.max_portfolio_exposure:
            violations.append({
                "type": "PORTFOLIO_EXPOSURE",
                "severity": "HIGH",
                "message": f"Portfolio exposure ${new_exposure:,.2f} exceeds limit ${limits.max_portfolio_exposure:,.2f}",
                "current": new_exposure,
                "limit": limits.max_portfolio_exposure
            })
        
        metric = {
            "type": "PORTFOLIO_EXPOSURE",
            "current": new_exposure,
            "limit": limits.max_portfolio_exposure,
            "utilization": (new_exposure / limits.max_portfolio_exposure) * 100
        }
        
        return {
            "violations": violations,
            "warnings": [],
            "metric": metric
        }
    
    async def _check_concentration_limits(
        self, 
        request: RiskAssessmentRequest, 
        portfolio_state: Dict, 
        limits: RiskLimits, 
        order_value: float
    ) -> Dict[str, Any]:
        """Check concentration limits"""
        violations = []
        
        # Find existing position value
        existing_value = 0
        for pos in portfolio_state["positions"]:
            if pos["symbol"] == request.symbol:
                existing_value = abs(pos["market_value"])
                break
        
        new_position_value = existing_value + order_value
        total_portfolio_value = max(portfolio_state["account_value"], 1)
        concentration_percent = (new_position_value / total_portfolio_value) * 100
        
        if concentration_percent > limits.max_concentration_percent:
            violations.append({
                "type": "CONCENTRATION",
                "severity": "MEDIUM",
                "message": f"Concentration {concentration_percent:.2f}% in {request.symbol} exceeds limit {limits.max_concentration_percent:.2f}%",
                "current": concentration_percent,
                "limit": limits.max_concentration_percent
            })
        
        metric = {
            "type": "CONCENTRATION",
            "symbol": request.symbol,
            "current": concentration_percent,
            "limit": limits.max_concentration_percent,
            "utilization": (concentration_percent / limits.max_concentration_percent) * 100
        }
        
        return {
            "violations": violations,
            "warnings": [],
            "metric": metric
        }
    
    async def _check_drawdown_limits(
        self, 
        request: RiskAssessmentRequest, 
        portfolio_state: Dict, 
        limits: RiskLimits
    ) -> Dict[str, Any]:
        """Check drawdown limits"""
        violations = []
        
        # Calculate current drawdown (simplified)
        current_drawdown = max(0, -portfolio_state["total_pnl"] / max(portfolio_state["account_value"], 1) * 100)
        
        if current_drawdown > limits.max_drawdown_percent:
            violations.append({
                "type": "DRAWDOWN",
                "severity": "HIGH",
                "message": f"Drawdown {current_drawdown:.2f}% exceeds limit {limits.max_drawdown_percent:.2f}%",
                "current": current_drawdown,
                "limit": limits.max_drawdown_percent
            })
        
        metric = {
            "type": "DRAWDOWN",
            "current": current_drawdown,
            "limit": limits.max_drawdown_percent,
            "utilization": (current_drawdown / limits.max_drawdown_percent) * 100
        }
        
        return {
            "violations": violations,
            "warnings": [],
            "metric": metric
        }
    
    async def _check_leverage_limits(
        self, 
        request: RiskAssessmentRequest, 
        portfolio_state: Dict, 
        limits: RiskLimits, 
        order_value: float
    ) -> Dict[str, Any]:
        """Check leverage limits"""
        violations = []
        
        current_exposure = sum(abs(pos["market_value"]) for pos in portfolio_state["positions"])
        new_exposure = current_exposure + order_value
        account_value = max(portfolio_state["account_value"], 1)
        new_leverage = new_exposure / account_value
        
        if new_leverage > limits.max_leverage:
            violations.append({
                "type": "LEVERAGE",
                "severity": "HIGH",
                "message": f"Leverage {new_leverage:.2f}x exceeds limit {limits.max_leverage:.2f}x",
                "current": new_leverage,
                "limit": limits.max_leverage
            })
        
        metric = {
            "type": "LEVERAGE",
            "current": new_leverage,
            "limit": limits.max_leverage,
            "utilization": (new_leverage / limits.max_leverage) * 100
        }
        
        return {
            "violations": violations,
            "warnings": [],
            "metric": metric
        }
    
    async def _calculate_max_drawdown(self, account_id: str, user_id: str) -> float:
        """Calculate maximum drawdown (simplified)"""
        # This would calculate historical drawdown from performance data
        # For now, return a placeholder value
        return 5.0  # 5% drawdown
    
    async def _calculate_var(self, portfolio_state: Dict, confidence_level: float) -> Optional[float]:
        """Calculate Value at Risk (simplified)"""
        # This would implement proper VaR calculation using historical data
        # For now, return a placeholder value
        total_value = portfolio_state["account_value"]
        return total_value * 0.02  # 2% of portfolio value
    
    def _determine_portfolio_risk_level(
        self, 
        leverage: float, 
        drawdown: float, 
        exposure: float, 
        limits: RiskLimits
    ) -> RiskLevel:
        """Determine overall portfolio risk level"""
        risk_scores = []
        
        # Leverage risk
        leverage_ratio = leverage / limits.max_leverage
        if leverage_ratio > 1.0:
            risk_scores.append(4)  # Critical
        elif leverage_ratio > 0.8:
            risk_scores.append(3)  # High
        elif leverage_ratio > 0.6:
            risk_scores.append(2)  # Medium
        else:
            risk_scores.append(1)  # Low
        
        # Drawdown risk
        drawdown_ratio = drawdown / limits.max_drawdown_percent
        if drawdown_ratio > 1.0:
            risk_scores.append(4)
        elif drawdown_ratio > 0.8:
            risk_scores.append(3)
        elif drawdown_ratio > 0.6:
            risk_scores.append(2)
        else:
            risk_scores.append(1)
        
        # Exposure risk
        exposure_ratio = exposure / limits.max_portfolio_exposure
        if exposure_ratio > 1.0:
            risk_scores.append(4)
        elif exposure_ratio > 0.8:
            risk_scores.append(3)
        elif exposure_ratio > 0.6:
            risk_scores.append(2)
        else:
            risk_scores.append(1)
        
        # Determine overall risk level
        max_score = max(risk_scores)
        if max_score >= 4:
            return RiskLevel.CRITICAL
        elif max_score >= 3:
            return RiskLevel.HIGH
        elif max_score >= 2:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    async def _get_active_violations(self, account_id: str) -> List[Dict[str, Any]]:
        """Get active risk violations for account"""
        # Filter recent violations for this account
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)
        active_violations = [
            {
                "type": v.violation_type.value,
                "severity": v.severity.value,
                "message": v.message,
                "timestamp": v.timestamp.isoformat()
            }
            for v in self.violation_history
            if v.account_id == account_id and v.timestamp > cutoff_time
        ]
        
        return active_violations

# ===========================================
# FACTORY FUNCTION
# ===========================================

async def create_risk_manager(db_manager: DatabaseManager) -> RiskManager:
    """Factory function to create RiskManager instance"""
    risk_manager = RiskManager(db_manager)
    await risk_manager.initialize()
    return risk_manager