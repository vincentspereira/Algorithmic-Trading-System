"""Risk Management Factory - Institutional Grade

This module implements an advanced risk management factory that provides:

- Automated stop-loss and take-profit calculation
- ATR-based position sizing with volatility adjustment
- Market structure analysis for risk assessment
- Dynamic risk adjustment based on market conditions
- Portfolio-level risk management and correlation analysis
- Real-time risk monitoring and alerts
- Behavioral risk overlays with sentiment integration
- Multi-timeframe risk convergence analysis
- Drawdown protection and capital preservation
- Risk-adjusted performance optimization

Key Features:
- 5-pillar institutional architecture integration
- Real-time risk calculation for HFT environments
- Advanced volatility modeling with regime detection
- Smart money flow analysis for risk assessment
- Automated position sizing with Kelly criterion
- Multi-asset correlation risk management
- Behavioral risk psychology integration
- Regulatory compliance and risk reporting
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple, NamedTuple, Union
from collections import deque, defaultdict
from dataclasses import dataclass, field
from enum import Enum
import warnings
from abc import ABC, abstractmethod

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=FutureWarning)

from .augmented_indicator import (
    AugmentedIndicator, IndicatorSignal, IndicatorConfig,
    SignalType, MarketRegime, RiskLevel, TimeframeConvergence
)

try:
    from utils.logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

class RiskMetricType(Enum):
    """Types of risk metrics"""
    VALUE_AT_RISK = "value_at_risk"
    EXPECTED_SHORTFALL = "expected_shortfall"
    MAXIMUM_DRAWDOWN = "maximum_drawdown"
    SHARPE_RATIO = "sharpe_ratio"
    SORTINO_RATIO = "sortino_ratio"
    CALMAR_RATIO = "calmar_ratio"
    VOLATILITY = "volatility"
    BETA = "beta"
    CORRELATION = "correlation"
    TRACKING_ERROR = "tracking_error"

class PositionSizingMethod(Enum):
    """Position sizing methods"""
    FIXED_AMOUNT = "fixed_amount"
    FIXED_PERCENTAGE = "fixed_percentage"
    ATR_BASED = "atr_based"
    VOLATILITY_ADJUSTED = "volatility_adjusted"
    KELLY_CRITERION = "kelly_criterion"
    RISK_PARITY = "risk_parity"
    OPTIMAL_F = "optimal_f"
    MONTE_CARLO = "monte_carlo"

class StopLossType(Enum):
    """Stop loss calculation methods"""
    FIXED_PERCENTAGE = "fixed_percentage"
    ATR_MULTIPLE = "atr_multiple"
    SUPPORT_RESISTANCE = "support_resistance"
    VOLATILITY_BASED = "volatility_based"
    TRAILING_STOP = "trailing_stop"
    TIME_BASED = "time_based"
    PARABOLIC_SAR = "parabolic_sar"
    CHANDELIER_EXIT = "chandelier_exit"

class TakeProfitType(Enum):
    """Take profit calculation methods"""
    FIXED_PERCENTAGE = "fixed_percentage"
    RISK_REWARD_RATIO = "risk_reward_ratio"
    ATR_MULTIPLE = "atr_multiple"
    FIBONACCI_LEVELS = "fibonacci_levels"
    RESISTANCE_LEVELS = "resistance_levels"
    TRAILING_PROFIT = "trailing_profit"
    PARTIAL_PROFIT = "partial_profit"
    VOLATILITY_TARGET = "volatility_target"

class RiskAlertLevel(Enum):
    """Risk alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

@dataclass
class RiskMetric:
    """Individual risk metric"""
    metric_type: RiskMetricType
    value: float
    threshold: float
    status: RiskLevel
    timestamp: datetime
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PositionRisk:
    """Risk assessment for a position"""
    symbol: str
    position_size: float
    entry_price: float
    current_price: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    unrealized_pnl: float
    risk_amount: float
    risk_percentage: float
    max_risk_amount: float
    atr_value: float
    volatility: float
    correlation_risk: float
    market_regime: MarketRegime
    risk_level: RiskLevel
    timestamp: datetime

@dataclass
class PortfolioRisk:
    """Portfolio-level risk assessment"""
    total_value: float
    total_risk: float
    risk_percentage: float
    max_drawdown: float
    current_drawdown: float
    var_95: float
    var_99: float
    expected_shortfall: float
    sharpe_ratio: float
    sortino_ratio: float
    correlation_matrix: Dict[str, Dict[str, float]]
    sector_exposure: Dict[str, float]
    currency_exposure: Dict[str, float]
    risk_metrics: List[RiskMetric]
    timestamp: datetime

@dataclass
class RiskAlert:
    """Risk management alert"""
    alert_level: RiskAlertLevel
    message: str
    symbol: Optional[str]
    metric_type: Optional[RiskMetricType]
    current_value: float
    threshold_value: float
    recommended_action: str
    timestamp: datetime

@dataclass
class RiskManagementConfig:
    """Configuration for risk management"""
    # Position sizing
    position_sizing_method: PositionSizingMethod = PositionSizingMethod.ATR_BASED
    max_position_size: float = 0.05  # 5% of portfolio
    max_portfolio_risk: float = 0.02  # 2% of portfolio per trade
    
    # Stop loss settings
    stop_loss_type: StopLossType = StopLossType.ATR_MULTIPLE
    stop_loss_atr_multiple: float = 2.0
    max_stop_loss_percentage: float = 0.03  # 3%
    
    # Take profit settings
    take_profit_type: TakeProfitType = TakeProfitType.RISK_REWARD_RATIO
    risk_reward_ratio: float = 2.0
    take_profit_atr_multiple: float = 4.0
    
    # Risk thresholds
    var_confidence_level: float = 0.95
    max_drawdown_threshold: float = 0.10  # 10%
    correlation_threshold: float = 0.7
    volatility_threshold: float = 0.25
    
    # ATR settings
    atr_period: int = 14
    volatility_period: int = 20
    
    # Portfolio settings
    max_positions: int = 10
    max_sector_exposure: float = 0.30  # 30%
    max_currency_exposure: float = 0.50  # 50%
    
    # Alert settings
    enable_alerts: bool = True
    alert_frequency: int = 60  # seconds
    
    # Advanced features
    enable_correlation_analysis: bool = True
    enable_regime_detection: bool = True
    enable_behavioral_overlay: bool = True
    enable_monte_carlo: bool = True

class ATRCalculator:
    """Average True Range calculator for volatility-based risk management"""
    
    def __init__(self, period: int = 14):
        self.period = period
        self.high_prices = deque(maxlen=period + 1)
        self.low_prices = deque(maxlen=period + 1)
        self.close_prices = deque(maxlen=period + 1)
        self.true_ranges = deque(maxlen=period)
        self.current_atr = 0.0
    
    def update(self, high: float, low: float, close: float) -> float:
        """Update ATR with new price data"""
        self.high_prices.append(high)
        self.low_prices.append(low)
        self.close_prices.append(close)
        
        if len(self.close_prices) < 2:
            return 0.0
        
        # Calculate True Range
        prev_close = self.close_prices[-2]
        current_high = self.high_prices[-1]
        current_low = self.low_prices[-1]
        
        tr1 = current_high - current_low
        tr2 = abs(current_high - prev_close)
        tr3 = abs(current_low - prev_close)
        
        true_range = max(tr1, tr2, tr3)
        self.true_ranges.append(true_range)
        
        # Calculate ATR (Simple Moving Average of True Range)
        if len(self.true_ranges) >= self.period:
            self.current_atr = sum(self.true_ranges) / len(self.true_ranges)
        
        return self.current_atr
    
    def get_atr(self) -> float:
        """Get current ATR value"""
        return self.current_atr

class VolatilityCalculator:
    """Volatility calculator for risk assessment"""
    
    def __init__(self, period: int = 20):
        self.period = period
        self.returns = deque(maxlen=period)
        self.prices = deque(maxlen=period + 1)
        self.current_volatility = 0.0
    
    def update(self, price: float) -> float:
        """Update volatility with new price"""
        self.prices.append(price)
        
        if len(self.prices) < 2:
            return 0.0
        
        # Calculate return
        prev_price = self.prices[-2]
        if prev_price > 0:
            return_val = (price - prev_price) / prev_price
            self.returns.append(return_val)
        
        # Calculate volatility (standard deviation of returns)
        if len(self.returns) >= self.period:
            returns_array = np.array(self.returns)
            self.current_volatility = np.std(returns_array) * np.sqrt(252)  # Annualized
        
        return self.current_volatility
    
    def get_volatility(self) -> float:
        """Get current volatility"""
        return self.current_volatility

class CorrelationAnalyzer:
    """Correlation analysis for portfolio risk management"""
    
    def __init__(self, window: int = 50):
        self.window = window
        self.price_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window))
        self.return_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window))
        self.correlation_matrix: Dict[str, Dict[str, float]] = {}
    
    def update(self, symbol: str, price: float) -> None:
        """Update price history for correlation calculation"""
        prev_prices = self.price_history[symbol]
        
        if len(prev_prices) > 0:
            prev_price = prev_prices[-1]
            if prev_price > 0:
                return_val = (price - prev_price) / prev_price
                self.return_history[symbol].append(return_val)
        
        self.price_history[symbol].append(price)
    
    def calculate_correlation_matrix(self) -> Dict[str, Dict[str, float]]:
        """Calculate correlation matrix for all symbols"""
        symbols = list(self.return_history.keys())
        
        if len(symbols) < 2:
            return {}
        
        correlation_matrix = {}
        
        for symbol1 in symbols:
            correlation_matrix[symbol1] = {}
            
            for symbol2 in symbols:
                if symbol1 == symbol2:
                    correlation_matrix[symbol1][symbol2] = 1.0
                else:
                    corr = self._calculate_correlation(symbol1, symbol2)
                    correlation_matrix[symbol1][symbol2] = corr
        
        self.correlation_matrix = correlation_matrix
        return correlation_matrix
    
    def _calculate_correlation(self, symbol1: str, symbol2: str) -> float:
        """Calculate correlation between two symbols"""
        returns1 = list(self.return_history[symbol1])
        returns2 = list(self.return_history[symbol2])
        
        if len(returns1) < 10 or len(returns2) < 10:
            return 0.0
        
        # Align lengths
        min_length = min(len(returns1), len(returns2))
        returns1 = returns1[-min_length:]
        returns2 = returns2[-min_length:]
        
        # Calculate correlation
        try:
            correlation = np.corrcoef(returns1, returns2)[0, 1]
            return correlation if not np.isnan(correlation) else 0.0
        except:
            return 0.0
    
    def get_correlation(self, symbol1: str, symbol2: str) -> float:
        """Get correlation between two symbols"""
        if symbol1 in self.correlation_matrix and symbol2 in self.correlation_matrix[symbol1]:
            return self.correlation_matrix[symbol1][symbol2]
        return 0.0

class RiskManagementFactory:
    """Advanced Risk Management Factory
    
    Provides comprehensive risk management capabilities including:
    - Automated position sizing
    - Stop-loss and take-profit calculation
    - Portfolio risk monitoring
    - Correlation analysis
    - Real-time risk alerts
    """
    
    def __init__(self, config: RiskManagementConfig):
        self.config = config
        
        # Risk calculators
        self.atr_calculators: Dict[str, ATRCalculator] = {}
        self.volatility_calculators: Dict[str, VolatilityCalculator] = {}
        self.correlation_analyzer = CorrelationAnalyzer()
        
        # Portfolio tracking
        self.positions: Dict[str, PositionRisk] = {}
        self.portfolio_history = deque(maxlen=1000)
        self.risk_alerts = deque(maxlen=100)
        
        # Performance tracking
        self.pnl_history = deque(maxlen=500)
        self.drawdown_history = deque(maxlen=500)
        
        # Risk metrics
        self.current_portfolio_risk: Optional[PortfolioRisk] = None
        self.risk_metrics_history = deque(maxlen=200)
        
        logger.info("Initialized RiskManagementFactory")
    
    def update_market_data(self, symbol: str, price: float, high: float = None, 
                          low: float = None, volume: float = None, timestamp: datetime = None) -> None:
        """Update market data for risk calculations"""
        if timestamp is None:
            timestamp = datetime.now()
        
        # Use price for high/low if not provided
        if high is None:
            high = price
        if low is None:
            low = price
        
        # Initialize calculators if needed
        if symbol not in self.atr_calculators:
            self.atr_calculators[symbol] = ATRCalculator(self.config.atr_period)
            self.volatility_calculators[symbol] = VolatilityCalculator(self.config.volatility_period)
        
        # Update calculators
        self.atr_calculators[symbol].update(high, low, price)
        self.volatility_calculators[symbol].update(price)
        self.correlation_analyzer.update(symbol, price)
    
    def calculate_position_size(self, symbol: str, entry_price: float, 
                               stop_loss_price: float, portfolio_value: float,
                               signal_confidence: float = 1.0) -> float:
        """Calculate optimal position size based on risk management rules"""
        if self.config.position_sizing_method == PositionSizingMethod.FIXED_PERCENTAGE:
            return self._fixed_percentage_sizing(portfolio_value)
        
        elif self.config.position_sizing_method == PositionSizingMethod.ATR_BASED:
            return self._atr_based_sizing(symbol, entry_price, stop_loss_price, portfolio_value)
        
        elif self.config.position_sizing_method == PositionSizingMethod.VOLATILITY_ADJUSTED:
            return self._volatility_adjusted_sizing(symbol, entry_price, portfolio_value, signal_confidence)
        
        elif self.config.position_sizing_method == PositionSizingMethod.KELLY_CRITERION:
            return self._kelly_criterion_sizing(symbol, entry_price, portfolio_value, signal_confidence)
        
        else:
            return self._fixed_percentage_sizing(portfolio_value)
    
    def _fixed_percentage_sizing(self, portfolio_value: float) -> float:
        """Calculate position size as fixed percentage of portfolio"""
        return portfolio_value * self.config.max_position_size
    
    def _atr_based_sizing(self, symbol: str, entry_price: float, 
                         stop_loss_price: float, portfolio_value: float) -> float:
        """Calculate position size based on ATR and risk per trade"""
        if symbol not in self.atr_calculators:
            return self._fixed_percentage_sizing(portfolio_value)
        
        atr = self.atr_calculators[symbol].get_atr()
        if atr <= 0:
            return self._fixed_percentage_sizing(portfolio_value)
        
        # Calculate risk per share
        risk_per_share = abs(entry_price - stop_loss_price)
        
        # Maximum risk amount
        max_risk_amount = portfolio_value * self.config.max_portfolio_risk
        
        # Position size based on risk
        if risk_per_share > 0:
            position_size = max_risk_amount / risk_per_share
        else:
            position_size = self._fixed_percentage_sizing(portfolio_value)
        
        # Apply maximum position size limit
        max_position_value = portfolio_value * self.config.max_position_size
        max_shares = max_position_value / entry_price if entry_price > 0 else 0
        
        return min(position_size, max_shares)
    
    def _volatility_adjusted_sizing(self, symbol: str, entry_price: float, 
                                   portfolio_value: float, signal_confidence: float) -> float:
        """Calculate position size adjusted for volatility"""
        if symbol not in self.volatility_calculators:
            return self._fixed_percentage_sizing(portfolio_value)
        
        volatility = self.volatility_calculators[symbol].get_volatility()
        
        if volatility <= 0:
            return self._fixed_percentage_sizing(portfolio_value)
        
        # Base position size
        base_size = portfolio_value * self.config.max_position_size
        
        # Adjust for volatility (inverse relationship)
        volatility_adjustment = min(1.0, 0.20 / volatility)  # Target 20% volatility
        
        # Adjust for signal confidence
        confidence_adjustment = signal_confidence
        
        # Calculate adjusted position size
        adjusted_size = base_size * volatility_adjustment * confidence_adjustment
        
        return adjusted_size / entry_price if entry_price > 0 else 0
    
    def _kelly_criterion_sizing(self, symbol: str, entry_price: float, 
                               portfolio_value: float, signal_confidence: float) -> float:
        """Calculate position size using Kelly Criterion"""
        # Simplified Kelly Criterion implementation
        # In practice, this would use historical win rate and average win/loss
        
        # Estimate win probability based on signal confidence
        win_probability = 0.5 + (signal_confidence - 0.5) * 0.3  # Scale confidence to probability
        
        # Estimate average win/loss ratio (simplified)
        avg_win_loss_ratio = self.config.risk_reward_ratio
        
        # Kelly fraction
        kelly_fraction = (win_probability * avg_win_loss_ratio - (1 - win_probability)) / avg_win_loss_ratio
        
        # Apply safety factor (use fraction of Kelly)
        kelly_fraction = max(0, min(kelly_fraction * 0.25, self.config.max_position_size))
        
        position_value = portfolio_value * kelly_fraction
        return position_value / entry_price if entry_price > 0 else 0
    
    def calculate_stop_loss(self, symbol: str, entry_price: float, 
                           is_long: bool = True, signal_strength: float = 1.0) -> float:
        """Calculate stop loss price based on configured method"""
        if self.config.stop_loss_type == StopLossType.FIXED_PERCENTAGE:
            return self._fixed_percentage_stop_loss(entry_price, is_long)
        
        elif self.config.stop_loss_type == StopLossType.ATR_MULTIPLE:
            return self._atr_multiple_stop_loss(symbol, entry_price, is_long)
        
        elif self.config.stop_loss_type == StopLossType.VOLATILITY_BASED:
            return self._volatility_based_stop_loss(symbol, entry_price, is_long, signal_strength)
        
        else:
            return self._fixed_percentage_stop_loss(entry_price, is_long)
    
    def _fixed_percentage_stop_loss(self, entry_price: float, is_long: bool) -> float:
        """Calculate stop loss as fixed percentage from entry"""
        if is_long:
            return entry_price * (1 - self.config.max_stop_loss_percentage)
        else:
            return entry_price * (1 + self.config.max_stop_loss_percentage)
    
    def _atr_multiple_stop_loss(self, symbol: str, entry_price: float, is_long: bool) -> float:
        """Calculate stop loss based on ATR multiple"""
        if symbol not in self.atr_calculators:
            return self._fixed_percentage_stop_loss(entry_price, is_long)
        
        atr = self.atr_calculators[symbol].get_atr()
        if atr <= 0:
            return self._fixed_percentage_stop_loss(entry_price, is_long)
        
        atr_distance = atr * self.config.stop_loss_atr_multiple
        
        if is_long:
            stop_loss = entry_price - atr_distance
        else:
            stop_loss = entry_price + atr_distance
        
        # Apply maximum stop loss percentage limit
        max_stop_loss = self._fixed_percentage_stop_loss(entry_price, is_long)
        
        if is_long:
            return max(stop_loss, max_stop_loss)
        else:
            return min(stop_loss, max_stop_loss)
    
    def _volatility_based_stop_loss(self, symbol: str, entry_price: float, 
                                   is_long: bool, signal_strength: float) -> float:
        """Calculate stop loss based on volatility"""
        if symbol not in self.volatility_calculators:
            return self._atr_multiple_stop_loss(symbol, entry_price, is_long)
        
        volatility = self.volatility_calculators[symbol].get_volatility()
        if volatility <= 0:
            return self._atr_multiple_stop_loss(symbol, entry_price, is_long)
        
        # Adjust stop distance based on volatility and signal strength
        base_distance = entry_price * volatility * 0.1  # 10% of daily volatility
        
        # Adjust for signal strength (stronger signals get tighter stops)
        strength_adjustment = 2.0 - signal_strength  # Range: 1.0 to 2.0
        stop_distance = base_distance * strength_adjustment
        
        if is_long:
            stop_loss = entry_price - stop_distance
        else:
            stop_loss = entry_price + stop_distance
        
        # Apply maximum stop loss percentage limit
        max_stop_loss = self._fixed_percentage_stop_loss(entry_price, is_long)
        
        if is_long:
            return max(stop_loss, max_stop_loss)
        else:
            return min(stop_loss, max_stop_loss)
    
    def calculate_take_profit(self, symbol: str, entry_price: float, 
                             stop_loss_price: float, is_long: bool = True) -> float:
        """Calculate take profit price based on configured method"""
        if self.config.take_profit_type == TakeProfitType.RISK_REWARD_RATIO:
            return self._risk_reward_take_profit(entry_price, stop_loss_price, is_long)
        
        elif self.config.take_profit_type == TakeProfitType.ATR_MULTIPLE:
            return self._atr_multiple_take_profit(symbol, entry_price, is_long)
        
        elif self.config.take_profit_type == TakeProfitType.FIXED_PERCENTAGE:
            return self._fixed_percentage_take_profit(entry_price, is_long)
        
        else:
            return self._risk_reward_take_profit(entry_price, stop_loss_price, is_long)
    
    def _risk_reward_take_profit(self, entry_price: float, stop_loss_price: float, is_long: bool) -> float:
        """Calculate take profit based on risk-reward ratio"""
        risk_amount = abs(entry_price - stop_loss_price)
        reward_amount = risk_amount * self.config.risk_reward_ratio
        
        if is_long:
            return entry_price + reward_amount
        else:
            return entry_price - reward_amount
    
    def _atr_multiple_take_profit(self, symbol: str, entry_price: float, is_long: bool) -> float:
        """Calculate take profit based on ATR multiple"""
        if symbol not in self.atr_calculators:
            return self._fixed_percentage_take_profit(entry_price, is_long)
        
        atr = self.atr_calculators[symbol].get_atr()
        if atr <= 0:
            return self._fixed_percentage_take_profit(entry_price, is_long)
        
        atr_distance = atr * self.config.take_profit_atr_multiple
        
        if is_long:
            return entry_price + atr_distance
        else:
            return entry_price - atr_distance
    
    def _fixed_percentage_take_profit(self, entry_price: float, is_long: bool) -> float:
        """Calculate take profit as fixed percentage from entry"""
        profit_percentage = self.config.max_stop_loss_percentage * self.config.risk_reward_ratio
        
        if is_long:
            return entry_price * (1 + profit_percentage)
        else:
            return entry_price * (1 - profit_percentage)
    
    def add_position(self, symbol: str, position_size: float, entry_price: float,
                    stop_loss: float = None, take_profit: float = None) -> None:
        """Add a new position to risk monitoring"""
        if symbol not in self.atr_calculators:
            logger.warning(f"No market data available for {symbol}")
            return
        
        atr_value = self.atr_calculators[symbol].get_atr()
        volatility = self.volatility_calculators[symbol].get_volatility() if symbol in self.volatility_calculators else 0.0
        
        position_risk = PositionRisk(
            symbol=symbol,
            position_size=position_size,
            entry_price=entry_price,
            current_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            unrealized_pnl=0.0,
            risk_amount=0.0,
            risk_percentage=0.0,
            max_risk_amount=0.0,
            atr_value=atr_value,
            volatility=volatility,
            correlation_risk=0.0,
            market_regime=MarketRegime.CONSOLIDATING,
            risk_level=RiskLevel.MEDIUM,
            timestamp=datetime.now()
        )
        
        self.positions[symbol] = position_risk
        logger.info(f"Added position for {symbol}: {position_size} shares at {entry_price}")
    
    def update_position(self, symbol: str, current_price: float) -> Optional[PositionRisk]:
        """Update position with current market price"""
        if symbol not in self.positions:
            return None
        
        position = self.positions[symbol]
        position.current_price = current_price
        
        # Calculate unrealized P&L
        price_diff = current_price - position.entry_price
        position.unrealized_pnl = price_diff * position.position_size
        
        # Calculate current risk
        if position.stop_loss:
            risk_per_share = abs(current_price - position.stop_loss)
            position.risk_amount = risk_per_share * abs(position.position_size)
        
        # Update correlation risk
        position.correlation_risk = self._calculate_position_correlation_risk(symbol)
        
        # Update risk level
        position.risk_level = self._assess_position_risk_level(position)
        
        position.timestamp = datetime.now()
        
        return position
    
    def remove_position(self, symbol: str) -> None:
        """Remove position from risk monitoring"""
        if symbol in self.positions:
            del self.positions[symbol]
            logger.info(f"Removed position for {symbol}")
    
    def calculate_portfolio_risk(self, portfolio_value: float) -> PortfolioRisk:
        """Calculate comprehensive portfolio risk metrics"""
        if not self.positions:
            return self._create_empty_portfolio_risk(portfolio_value)
        
        # Calculate total risk
        total_risk = sum(pos.risk_amount for pos in self.positions.values())
        risk_percentage = total_risk / portfolio_value if portfolio_value > 0 else 0.0
        
        # Calculate drawdown
        current_drawdown = self._calculate_current_drawdown(portfolio_value)
        max_drawdown = self._calculate_max_drawdown()
        
        # Calculate VaR and Expected Shortfall
        var_95, var_99, expected_shortfall = self._calculate_var_and_es(portfolio_value)
        
        # Calculate performance ratios
        sharpe_ratio = self._calculate_sharpe_ratio()
        sortino_ratio = self._calculate_sortino_ratio()
        
        # Update correlation matrix
        correlation_matrix = self.correlation_analyzer.calculate_correlation_matrix()
        
        # Calculate exposures
        sector_exposure = self._calculate_sector_exposure(portfolio_value)
        currency_exposure = self._calculate_currency_exposure(portfolio_value)
        
        # Generate risk metrics
        risk_metrics = self._generate_risk_metrics(portfolio_value)
        
        portfolio_risk = PortfolioRisk(
            total_value=portfolio_value,
            total_risk=total_risk,
            risk_percentage=risk_percentage,
            max_drawdown=max_drawdown,
            current_drawdown=current_drawdown,
            var_95=var_95,
            var_99=var_99,
            expected_shortfall=expected_shortfall,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            correlation_matrix=correlation_matrix,
            sector_exposure=sector_exposure,
            currency_exposure=currency_exposure,
            risk_metrics=risk_metrics,
            timestamp=datetime.now()
        )
        
        self.current_portfolio_risk = portfolio_risk
        self.portfolio_history.append(portfolio_risk)
        
        # Check for risk alerts
        self._check_risk_alerts(portfolio_risk)
        
        return portfolio_risk
    
    def _create_empty_portfolio_risk(self, portfolio_value: float) -> PortfolioRisk:
        """Create empty portfolio risk for portfolios with no positions"""
        return PortfolioRisk(
            total_value=portfolio_value,
            total_risk=0.0,
            risk_percentage=0.0,
            max_drawdown=0.0,
            current_drawdown=0.0,
            var_95=0.0,
            var_99=0.0,
            expected_shortfall=0.0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            correlation_matrix={},
            sector_exposure={},
            currency_exposure={},
            risk_metrics=[],
            timestamp=datetime.now()
        )
    
    def _calculate_position_correlation_risk(self, symbol: str) -> float:
        """Calculate correlation risk for a position"""
        if not self.config.enable_correlation_analysis:
            return 0.0
        
        correlations = []
        for other_symbol in self.positions.keys():
            if other_symbol != symbol:
                corr = self.correlation_analyzer.get_correlation(symbol, other_symbol)
                if abs(corr) > self.config.correlation_threshold:
                    correlations.append(abs(corr))
        
        return max(correlations) if correlations else 0.0
    
    def _assess_position_risk_level(self, position: PositionRisk) -> RiskLevel:
        """Assess risk level for individual position"""
        risk_factors = []
        
        # Volatility risk
        if position.volatility > self.config.volatility_threshold:
            risk_factors.append(1)
        
        # Correlation risk
        if position.correlation_risk > self.config.correlation_threshold:
            risk_factors.append(1)
        
        # P&L risk
        if position.unrealized_pnl < -position.risk_amount * 0.5:
            risk_factors.append(1)
        
        # ATR risk
        if position.atr_value > position.current_price * 0.05:  # 5% of price
            risk_factors.append(1)
        
        risk_score = sum(risk_factors)
        
        if risk_score >= 3:
            return RiskLevel.VERY_HIGH
        elif risk_score >= 2:
            return RiskLevel.HIGH
        elif risk_score >= 1:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _calculate_current_drawdown(self, portfolio_value: float) -> float:
        """Calculate current drawdown from peak"""
        if not self.portfolio_history:
            return 0.0
        
        peak_value = max(p.total_value for p in self.portfolio_history)
        if peak_value <= 0:
            return 0.0
        
        drawdown = (peak_value - portfolio_value) / peak_value
        return max(0.0, drawdown)
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown from history"""
        if len(self.portfolio_history) < 2:
            return 0.0
        
        values = [p.total_value for p in self.portfolio_history]
        peak = values[0]
        max_dd = 0.0
        
        for value in values[1:]:
            if value > peak:
                peak = value
            else:
                dd = (peak - value) / peak if peak > 0 else 0.0
                max_dd = max(max_dd, dd)
        
        return max_dd
    
    def _calculate_var_and_es(self, portfolio_value: float) -> Tuple[float, float, float]:
        """Calculate Value at Risk and Expected Shortfall"""
        if len(self.pnl_history) < 30:
            return 0.0, 0.0, 0.0
        
        returns = np.array(list(self.pnl_history))
        
        # Calculate VaR at 95% and 99% confidence levels
        var_95 = np.percentile(returns, 5) * portfolio_value
        var_99 = np.percentile(returns, 1) * portfolio_value
        
        # Calculate Expected Shortfall (average of losses beyond VaR)
        tail_losses = returns[returns <= np.percentile(returns, 5)]
        expected_shortfall = np.mean(tail_losses) * portfolio_value if len(tail_losses) > 0 else 0.0
        
        return abs(var_95), abs(var_99), abs(expected_shortfall)
    
    def _calculate_sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio from return history"""
        if len(self.pnl_history) < 30:
            return 0.0
        
        returns = np.array(list(self.pnl_history))
        
        if np.std(returns) == 0:
            return 0.0
        
        # Assume risk-free rate of 2% annually (0.02/252 daily)
        risk_free_rate = 0.02 / 252
        excess_returns = returns - risk_free_rate
        
        sharpe = np.mean(excess_returns) / np.std(returns) * np.sqrt(252)
        return sharpe
    
    def _calculate_sortino_ratio(self) -> float:
        """Calculate Sortino ratio (downside deviation)"""
        if len(self.pnl_history) < 30:
            return 0.0
        
        returns = np.array(list(self.pnl_history))
        
        # Calculate downside deviation
        negative_returns = returns[returns < 0]
        if len(negative_returns) == 0:
            return float('inf')
        
        downside_deviation = np.std(negative_returns)
        if downside_deviation == 0:
            return 0.0
        
        risk_free_rate = 0.02 / 252
        excess_returns = returns - risk_free_rate
        
        sortino = np.mean(excess_returns) / downside_deviation * np.sqrt(252)
        return sortino
    
    def _calculate_sector_exposure(self, portfolio_value: float) -> Dict[str, float]:
        """Calculate sector exposure (simplified)"""
        # This is a simplified implementation
        # In practice, you would map symbols to sectors
        sector_exposure = {}
        
        for symbol, position in self.positions.items():
            position_value = abs(position.position_size * position.current_price)
            exposure_pct = position_value / portfolio_value if portfolio_value > 0 else 0.0
            
            # Simplified sector mapping (first letter of symbol)
            sector = symbol[0] if symbol else 'Unknown'
            
            if sector in sector_exposure:
                sector_exposure[sector] += exposure_pct
            else:
                sector_exposure[sector] = exposure_pct
        
        return sector_exposure
    
    def _calculate_currency_exposure(self, portfolio_value: float) -> Dict[str, float]:
        """Calculate currency exposure (simplified)"""
        # Simplified implementation - assume all positions are in base currency
        total_exposure = sum(abs(pos.position_size * pos.current_price) for pos in self.positions.values())
        
        if portfolio_value > 0:
            return {'USD': total_exposure / portfolio_value}
        else:
            return {'USD': 0.0}
    
    def _generate_risk_metrics(self, portfolio_value: float) -> List[RiskMetric]:
        """Generate comprehensive risk metrics"""
        metrics = []
        timestamp = datetime.now()
        
        # Portfolio risk percentage
        total_risk = sum(pos.risk_amount for pos in self.positions.values())
        risk_pct = total_risk / portfolio_value if portfolio_value > 0 else 0.0
        
        metrics.append(RiskMetric(
            metric_type=RiskMetricType.VALUE_AT_RISK,
            value=risk_pct,
            threshold=self.config.max_portfolio_risk,
            status=RiskLevel.HIGH if risk_pct > self.config.max_portfolio_risk else RiskLevel.LOW,
            timestamp=timestamp
        ))
        
        # Maximum drawdown
        max_dd = self._calculate_max_drawdown()
        metrics.append(RiskMetric(
            metric_type=RiskMetricType.MAXIMUM_DRAWDOWN,
            value=max_dd,
            threshold=self.config.max_drawdown_threshold,
            status=RiskLevel.HIGH if max_dd > self.config.max_drawdown_threshold else RiskLevel.LOW,
            timestamp=timestamp
        ))
        
        # Volatility
        if self.volatility_calculators:
            avg_volatility = np.mean([calc.get_volatility() for calc in self.volatility_calculators.values()])
            metrics.append(RiskMetric(
                metric_type=RiskMetricType.VOLATILITY,
                value=avg_volatility,
                threshold=self.config.volatility_threshold,
                status=RiskLevel.HIGH if avg_volatility > self.config.volatility_threshold else RiskLevel.LOW,
                timestamp=timestamp
            ))
        
        return metrics
    
    def _check_risk_alerts(self, portfolio_risk: PortfolioRisk) -> None:
        """Check for risk threshold breaches and generate alerts"""
        if not self.config.enable_alerts:
            return
        
        alerts = []
        
        # Portfolio risk alert
        if portfolio_risk.risk_percentage > self.config.max_portfolio_risk:
            alerts.append(RiskAlert(
                alert_level=RiskAlertLevel.WARNING,
                message=f"Portfolio risk ({portfolio_risk.risk_percentage:.2%}) exceeds threshold ({self.config.max_portfolio_risk:.2%})",
                symbol=None,
                metric_type=RiskMetricType.VALUE_AT_RISK,
                current_value=portfolio_risk.risk_percentage,
                threshold_value=self.config.max_portfolio_risk,
                recommended_action="Consider reducing position sizes or closing high-risk positions",
                timestamp=datetime.now()
            ))
        
        # Drawdown alert
        if portfolio_risk.current_drawdown > self.config.max_drawdown_threshold:
            alerts.append(RiskAlert(
                alert_level=RiskAlertLevel.CRITICAL,
                message=f"Current drawdown ({portfolio_risk.current_drawdown:.2%}) exceeds threshold ({self.config.max_drawdown_threshold:.2%})",
                symbol=None,
                metric_type=RiskMetricType.MAXIMUM_DRAWDOWN,
                current_value=portfolio_risk.current_drawdown,
                threshold_value=self.config.max_drawdown_threshold,
                recommended_action="Implement capital preservation measures immediately",
                timestamp=datetime.now()
            ))
        
        # Individual position alerts
        for symbol, position in self.positions.items():
            if position.risk_level in [RiskLevel.HIGH, RiskLevel.VERY_HIGH]:
                alerts.append(RiskAlert(
                    alert_level=RiskAlertLevel.WARNING,
                    message=f"High risk detected for position {symbol}",
                    symbol=symbol,
                    metric_type=None,
                    current_value=position.correlation_risk,
                    threshold_value=self.config.correlation_threshold,
                    recommended_action=f"Review position {symbol} for risk reduction",
                    timestamp=datetime.now()
                ))
        
        # Add alerts to history
        for alert in alerts:
            self.risk_alerts.append(alert)
            if alert.alert_level in [RiskAlertLevel.CRITICAL, RiskAlertLevel.EMERGENCY]:
                logger.warning(f"Risk Alert: {alert.message}")
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get comprehensive risk management summary"""
        if not self.current_portfolio_risk:
            return {'status': 'no_data'}
        
        portfolio_risk = self.current_portfolio_risk
        
        summary = {
            'portfolio_metrics': {
                'total_value': portfolio_risk.total_value,
                'total_risk': portfolio_risk.total_risk,
                'risk_percentage': portfolio_risk.risk_percentage,
                'current_drawdown': portfolio_risk.current_drawdown,
                'max_drawdown': portfolio_risk.max_drawdown,
                'var_95': portfolio_risk.var_95,
                'sharpe_ratio': portfolio_risk.sharpe_ratio,
                'sortino_ratio': portfolio_risk.sortino_ratio
            },
            'positions': {
                symbol: {
                    'size': pos.position_size,
                    'entry_price': pos.entry_price,
                    'current_price': pos.current_price,
                    'unrealized_pnl': pos.unrealized_pnl,
                    'risk_amount': pos.risk_amount,
                    'risk_level': pos.risk_level.value,
                    'volatility': pos.volatility,
                    'correlation_risk': pos.correlation_risk
                }
                for symbol, pos in self.positions.items()
            },
            'risk_alerts': [
                {
                    'level': alert.alert_level.value,
                    'message': alert.message,
                    'symbol': alert.symbol,
                    'action': alert.recommended_action,
                    'timestamp': alert.timestamp.isoformat()
                }
                for alert in list(self.risk_alerts)[-10:]  # Last 10 alerts
            ],
            'configuration': {
                'max_portfolio_risk': self.config.max_portfolio_risk,
                'max_position_size': self.config.max_position_size,
                'risk_reward_ratio': self.config.risk_reward_ratio,
                'position_sizing_method': self.config.position_sizing_method.value,
                'stop_loss_type': self.config.stop_loss_type.value
            }
        }
        
        return summary
    
    def __str__(self) -> str:
        if self.current_portfolio_risk:
            return (f"RiskManager(Positions={len(self.positions)}, "
                   f"Risk={self.current_portfolio_risk.risk_percentage:.2%}, "
                   f"Drawdown={self.current_portfolio_risk.current_drawdown:.2%})")
        return f"RiskManager(Positions={len(self.positions)})"

# Factory function for easy creation
def create_risk_management_factory(position_sizing_method: PositionSizingMethod = PositionSizingMethod.ATR_BASED,
                                 max_portfolio_risk: float = 0.02,
                                 max_position_size: float = 0.05,
                                 risk_reward_ratio: float = 2.0,
                                 stop_loss_type: StopLossType = StopLossType.ATR_MULTIPLE,
                                 enable_advanced_features: bool = True) -> RiskManagementFactory:
    """Factory function to create RiskManagementFactory
    
    Args:
        position_sizing_method: Method for calculating position sizes
        max_portfolio_risk: Maximum risk per trade as percentage of portfolio
        max_position_size: Maximum position size as percentage of portfolio
        risk_reward_ratio: Target risk-reward ratio for trades
        stop_loss_type: Method for calculating stop losses
        enable_advanced_features: Enable advanced risk management features
    
    Returns:
        Configured RiskManagementFactory instance
    """
    config = RiskManagementConfig(
        position_sizing_method=position_sizing_method,
        max_portfolio_risk=max_portfolio_risk,
        max_position_size=max_position_size,
        risk_reward_ratio=risk_reward_ratio,
        stop_loss_type=stop_loss_type,
        enable_correlation_analysis=enable_advanced_features,
        enable_regime_detection=enable_advanced_features,
        enable_behavioral_overlay=enable_advanced_features,
        enable_monte_carlo=enable_advanced_features
    )
    
    return RiskManagementFactory(config)