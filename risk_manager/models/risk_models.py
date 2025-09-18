"""Risk Management Data Models

Comprehensive data models for risk management including limits,
metrics, violations, and assessment structures.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import asyncio
import math
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
from dataclasses import dataclass, field
import logging

from pydantic import BaseModel, Field, validator
import numpy as np

# ===========================================
# ENUMS AND CONSTANTS
# ===========================================

class RiskLevel(str, Enum):
    """Risk severity levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class RiskCheckResult(str, Enum):
    """Risk assessment results"""
    APPROVED = "APPROVED"
    WARNING = "WARNING"
    REJECTED = "REJECTED"

class RiskMetricType(str, Enum):
    """Types of risk metrics"""
    POSITION_SIZE = "POSITION_SIZE"
    PORTFOLIO_EXPOSURE = "PORTFOLIO_EXPOSURE"
    DRAWDOWN = "DRAWDOWN"
    VAR = "VAR"  # Value at Risk
    CVAR = "CVAR"  # Conditional Value at Risk
    CONCENTRATION = "CONCENTRATION"
    LEVERAGE = "LEVERAGE"
    CORRELATION = "CORRELATION"
    VOLATILITY = "VOLATILITY"
    BETA = "BETA"
    SHARPE_RATIO = "SHARPE_RATIO"
    MAX_DRAWDOWN = "MAX_DRAWDOWN"
    CALMAR_RATIO = "CALMAR_RATIO"

class RiskViolationType(str, Enum):
    """Types of risk violations"""
    POSITION_LIMIT = "POSITION_LIMIT"
    PORTFOLIO_LIMIT = "PORTFOLIO_LIMIT"
    DRAWDOWN_LIMIT = "DRAWDOWN_LIMIT"
    EXPOSURE_LIMIT = "EXPOSURE_LIMIT"
    CONCENTRATION_LIMIT = "CONCENTRATION_LIMIT"
    LEVERAGE_LIMIT = "LEVERAGE_LIMIT"
    LOSS_LIMIT = "LOSS_LIMIT"
    VAR_LIMIT = "VAR_LIMIT"
    CORRELATION_LIMIT = "CORRELATION_LIMIT"
    VOLATILITY_LIMIT = "VOLATILITY_LIMIT"

class PositionSizingMethod(str, Enum):
    """Position sizing methods"""
    FIXED_AMOUNT = "FIXED_AMOUNT"
    FIXED_PERCENTAGE = "FIXED_PERCENTAGE"
    KELLY_CRITERION = "KELLY_CRITERION"
    VOLATILITY_ADJUSTED = "VOLATILITY_ADJUSTED"
    RISK_PARITY = "RISK_PARITY"
    ATR_BASED = "ATR_BASED"
    VAR_BASED = "VAR_BASED"

class VaRMethod(str, Enum):
    """Value at Risk calculation methods"""
    HISTORICAL = "HISTORICAL"
    PARAMETRIC = "PARAMETRIC"
    MONTE_CARLO = "MONTE_CARLO"
    CORNISH_FISHER = "CORNISH_FISHER"

# ===========================================
# DATA MODELS
# ===========================================

@dataclass
class RiskLimits:
    """Comprehensive risk limits configuration"""
    # Position Limits
    max_position_size: float = 10000  # Maximum position size per symbol
    max_position_value: float = 100000  # Maximum position value per symbol
    max_position_percentage: float = 5.0  # Maximum position as % of portfolio
    
    # Portfolio Limits
    max_portfolio_exposure: float = 500000  # Maximum total portfolio exposure
    max_gross_exposure: float = 1000000  # Maximum gross exposure
    max_net_exposure: float = 500000  # Maximum net exposure
    max_leverage: float = 2.0  # Maximum leverage ratio
    
    # Risk Limits
    max_daily_loss: float = 5000  # Maximum daily loss
    max_daily_loss_percentage: float = 2.0  # Maximum daily loss as % of portfolio
    max_drawdown_percent: float = 10.0  # Maximum drawdown percentage
    max_concentration_percent: float = 20.0  # Maximum concentration per symbol
    max_sector_concentration: float = 30.0  # Maximum sector concentration
    max_correlation_exposure: float = 0.7  # Maximum correlated exposure
    
    # VaR Limits
    var_confidence_level: float = 0.95  # VaR confidence level
    var_time_horizon: int = 1  # VaR time horizon in days
    max_var_percentage: float = 3.0  # Maximum VaR as % of portfolio
    max_cvar_percentage: float = 5.0  # Maximum CVaR as % of portfolio
    
    # Volatility Limits
    max_portfolio_volatility: float = 0.25  # Maximum portfolio volatility (25%)
    max_position_volatility: float = 0.50  # Maximum position volatility (50%)
    
    # Performance Limits
    min_sharpe_ratio: float = 0.5  # Minimum acceptable Sharpe ratio
    max_beta: float = 1.5  # Maximum portfolio beta
    
    # Operational Limits
    max_orders_per_minute: int = 100  # Maximum orders per minute
    max_order_value: float = 50000  # Maximum single order value
    
    # Time-based Limits
    trading_start_time: str = "09:30"  # Trading start time
    trading_end_time: str = "16:00"  # Trading end time
    max_holding_period_days: int = 365  # Maximum holding period
    
    def __post_init__(self):
        """Validate risk limits"""
        if self.max_position_percentage > 100:
            raise ValueError("Max position percentage cannot exceed 100%")
        if self.max_leverage < 1.0:
            raise ValueError("Max leverage cannot be less than 1.0")
        if self.var_confidence_level <= 0 or self.var_confidence_level >= 1:
            raise ValueError("VaR confidence level must be between 0 and 1")

@dataclass
class RiskMetric:
    """Risk metric data structure"""
    metric_type: RiskMetricType
    current_value: float
    limit_value: float
    utilization_percent: float
    risk_level: RiskLevel
    timestamp: datetime
    symbol: Optional[str] = None
    account_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Calculate utilization percentage"""
        if self.limit_value > 0:
            self.utilization_percent = (self.current_value / self.limit_value) * 100
        else:
            self.utilization_percent = 0.0
            
        # Determine risk level based on utilization
        if self.utilization_percent >= 95:
            self.risk_level = RiskLevel.CRITICAL
        elif self.utilization_percent >= 80:
            self.risk_level = RiskLevel.HIGH
        elif self.utilization_percent >= 60:
            self.risk_level = RiskLevel.MEDIUM
        else:
            self.risk_level = RiskLevel.LOW

@dataclass
class RiskViolation:
    """Risk violation data structure"""
    violation_type: RiskViolationType
    severity: RiskLevel
    current_value: float
    limit_value: float
    excess_amount: float
    symbol: Optional[str] = None
    account_id: Optional[str] = None
    message: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = False
    resolution_timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Calculate excess amount and generate message"""
        self.excess_amount = self.current_value - self.limit_value
        if not self.message:
            self.message = f"{self.violation_type.value}: {self.current_value:.2f} exceeds limit of {self.limit_value:.2f}"

class RiskAssessmentRequest(BaseModel):
    """Risk assessment request model"""
    account_id: str
    symbol: str
    side: str  # BUY/SELL
    quantity: float
    price: Optional[float] = None
    order_type: str = "MARKET"
    strategy_id: Optional[str] = None
    portfolio_id: Optional[str] = None
    
    @validator('side')
    def validate_side(cls, v):
        if v.upper() not in ['BUY', 'SELL']:
            raise ValueError('Side must be BUY or SELL')
        return v.upper()
    
    @validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be positive')
        return v

class RiskAssessmentResponse(BaseModel):
    """Risk assessment response model"""
    result: RiskCheckResult
    risk_level: RiskLevel
    violations: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    metrics: List[Dict[str, Any]] = Field(default_factory=list)
    approved_quantity: Optional[float] = None
    suggested_quantity: Optional[float] = None
    rejection_reason: Optional[str] = None
    risk_score: float = 0.0
    confidence_score: float = 0.0
    assessment_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
class PortfolioRiskSummary(BaseModel):
    """Portfolio risk summary model"""
    account_id: str
    portfolio_id: Optional[str] = None
    
    # Exposure Metrics
    total_exposure: float
    gross_exposure: float
    net_exposure: float
    long_exposure: float
    short_exposure: float
    available_buying_power: float
    
    # Leverage and Concentration
    current_leverage: float
    max_position_concentration: float
    sector_concentrations: Dict[str, float] = Field(default_factory=dict)
    
    # Performance Metrics
    daily_pnl: float
    total_pnl: float
    unrealized_pnl: float
    realized_pnl: float
    
    # Risk Metrics
    current_drawdown: float
    max_drawdown: float
    portfolio_volatility: float
    portfolio_beta: float
    sharpe_ratio: Optional[float] = None
    
    # VaR Metrics
    var_1_day: Optional[float] = None
    var_1_week: Optional[float] = None
    var_1_month: Optional[float] = None
    cvar_1_day: Optional[float] = None
    
    # Risk Assessment
    overall_risk_level: RiskLevel
    risk_score: float
    active_violations: List[Dict[str, Any]] = Field(default_factory=list)
    risk_metrics: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Timestamps
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    calculation_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class PositionSizingResult:
    """Position sizing calculation result"""
    method: PositionSizingMethod
    recommended_quantity: float
    recommended_value: float
    risk_amount: float
    risk_percentage: float
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    confidence_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    calculation_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class VaRResult:
    """Value at Risk calculation result"""
    method: VaRMethod
    confidence_level: float
    time_horizon: int
    var_amount: float
    var_percentage: float
    cvar_amount: Optional[float] = None
    cvar_percentage: Optional[float] = None
    expected_shortfall: Optional[float] = None
    volatility: Optional[float] = None
    correlation_matrix: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    calculation_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class StressTestScenario:
    """Stress test scenario definition"""
    name: str
    description: str
    market_shock_percentage: float
    volatility_multiplier: float = 1.0
    correlation_adjustment: float = 0.0
    sector_shocks: Dict[str, float] = field(default_factory=dict)
    duration_days: int = 1
    probability: float = 0.01  # 1% probability
    
@dataclass
class StressTestResult:
    """Stress test result"""
    scenario: StressTestScenario
    portfolio_loss: float
    portfolio_loss_percentage: float
    position_losses: Dict[str, float] = field(default_factory=dict)
    max_drawdown: float = 0.0
    recovery_time_days: Optional[int] = None
    risk_metrics: Dict[str, float] = field(default_factory=dict)
    passed: bool = True
    calculation_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

# ===========================================
# UTILITY FUNCTIONS
# ===========================================

def calculate_risk_score(metrics: List[RiskMetric]) -> float:
    """Calculate overall risk score from individual metrics"""
    if not metrics:
        return 0.0
    
    weights = {
        RiskMetricType.VAR: 0.25,
        RiskMetricType.LEVERAGE: 0.20,
        RiskMetricType.CONCENTRATION: 0.15,
        RiskMetricType.DRAWDOWN: 0.15,
        RiskMetricType.VOLATILITY: 0.10,
        RiskMetricType.CORRELATION: 0.10,
        RiskMetricType.PORTFOLIO_EXPOSURE: 0.05
    }
    
    total_score = 0.0
    total_weight = 0.0
    
    for metric in metrics:
        weight = weights.get(metric.metric_type, 0.05)
        # Convert utilization to risk score (100 - utilization)
        risk_contribution = (100 - metric.utilization_percent) * weight
        total_score += risk_contribution
        total_weight += weight
    
    return total_score / total_weight if total_weight > 0 else 0.0

def determine_risk_level(risk_score: float) -> RiskLevel:
    """Determine risk level from risk score"""
    if risk_score >= 80:
        return RiskLevel.LOW
    elif risk_score >= 60:
        return RiskLevel.MEDIUM
    elif risk_score >= 40:
        return RiskLevel.HIGH
    else:
        return RiskLevel.CRITICAL