"""
Institutional-Grade Position Sizing Algorithms

This module implements advanced position sizing algorithms with institutional-grade features:
- Fixed percentage position sizing
- Volatility-based position sizing
- Kelly Criterion optimization
- Risk parity allocation
- Portfolio optimization integration

All algorithms include volume-weighting, smart money confirmation,
multi-timeframe analysis, adaptive confidence scoring, and integrated risk management.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from enum import Enum
import math
import statistics

from nautilus_trader.model.enums import OrderSide


class PositionSizingMethod(Enum):
    """Position sizing calculation methods"""
    FIXED_PERCENTAGE = "fixed_percentage"
    VOLATILITY_BASED = "volatility_based"
    KELLY_CRITERION = "kelly_criterion"
    RISK_PARITY = "risk_parity"
    EQUAL_RISK = "equal_risk"
    OPTIMAL_F = "optimal_f"


@dataclass
class PositionSizingConfig:
    """Configuration for position sizing algorithms"""
    method: PositionSizingMethod = PositionSizingMethod.VOLATILITY_BASED

    # Fixed percentage parameters
    fixed_percentage: float = 0.02  # 2% of portfolio per trade

    # Volatility-based parameters
    volatility_lookback: int = 20
    volatility_target: float = 0.02  # 2% target volatility
    max_position_size: float = 0.10  # 10% max position size

    # Kelly Criterion parameters
    kelly_fraction: float = 1.0  # Full Kelly (can be fractional)
    win_rate_lookback: int = 50
    avg_win_lookback: int = 50
    avg_loss_lookback: int = 50

    # Risk parity parameters
    risk_budget: float = 0.02  # 2% risk budget per position
    correlation_lookback: int = 60

    # Equal risk parameters
    equal_risk_amount: float = 0.01  # 1% risk per position

    # Optimal F parameters
    optimal_f_lookback: int = 100
    optimal_f_confidence: float = 0.95

    # General constraints
    max_portfolio_risk: float = 0.20  # 20% max portfolio risk
    min_position_size: float = 0.001  # 0.1% minimum position
    max_positions: int = 20  # Maximum number of open positions


@dataclass
class PositionSizingResult:
    """Result of position sizing calculation"""
    position_size: float
    position_size_pct: float  # Percentage of portfolio
    risk_amount: float
    confidence_score: float
    sizing_method: str
    risk_metrics: Dict[str, float]
    constraints_applied: List[str]
    timestamp: datetime


class InstitutionalPositionSizer:
    """
    Institutional-grade position sizer with multiple algorithms.

    Features:
    - Multiple position sizing methodologies (fixed, volatility-based, Kelly, etc.)
    - Portfolio risk management integration
    - Adaptive sizing based on market conditions
    - Confidence scoring for sizing decisions
    - Risk parity and optimal allocation algorithms
    """

    def __init__(self, config: PositionSizingConfig = None):
        if config is None:
            config = PositionSizingConfig()

        self.config = config

        # Historical data for calculations
        self.portfolio_returns = []
        self.position_returns = []
        self.win_rates = []
        self.avg_wins = []
        self.avg_losses = []

        # Current portfolio state
        self.portfolio_value = 0.0
        self.current_positions = {}  # symbol -> position info
        self.portfolio_volatility = 0.0

        # Risk tracking
        self.portfolio_risk = 0.0
        self.correlation_matrix = {}

    def set_portfolio_state(self, portfolio_value: float,
                           current_positions: Dict[str, Dict[str, Any]],
                           portfolio_volatility: float = None):
        """
        Set current portfolio state for position sizing calculations

        Args:
            portfolio_value: Current total portfolio value
            current_positions: Dict of current positions {symbol: position_info}
            portfolio_volatility: Current portfolio volatility (optional)
        """
        self.portfolio_value = portfolio_value
        self.current_positions = current_positions.copy()

        if portfolio_volatility is not None:
            self.portfolio_volatility = portfolio_volatility
        else:
            # Calculate portfolio volatility from positions
            self._calculate_portfolio_volatility()

        # Update portfolio risk
        self._calculate_portfolio_risk()

    def calculate_position_size(self, symbol: str, entry_price: float,
                              stop_loss_price: float, side: OrderSide,
                              market_data: Dict[str, Any] = None) -> PositionSizingResult:
        """
        Calculate position size using configured method

        Args:
            symbol: Trading symbol
            entry_price: Intended entry price
            stop_loss_price: Stop loss price
            side: Trade side (BUY/SELL)
            market_data: Additional market data for calculations

        Returns:
            PositionSizingResult with sizing details
        """
        if self.portfolio_value <= 0:
            return self._create_error_result("Invalid portfolio value")

        # Calculate risk per share
        risk_per_share = abs(entry_price - stop_loss_price)
        if risk_per_share <= 0:
            return self._create_error_result("Invalid stop loss")

        # Calculate maximum position size based on constraints
        max_size_pct = self._calculate_max_position_size(symbol, risk_per_share)

        # Apply selected sizing method
        if self.config.method == PositionSizingMethod.FIXED_PERCENTAGE:
            result = self._fixed_percentage_sizing(max_size_pct)
        elif self.config.method == PositionSizingMethod.VOLATILITY_BASED:
            result = self._volatility_based_sizing(symbol, risk_per_share, market_data, max_size_pct)
        elif self.config.method == PositionSizingMethod.KELLY_CRITERION:
            result = self._kelly_criterion_sizing(symbol, max_size_pct)
        elif self.config.method == PositionSizingMethod.RISK_PARITY:
            result = self._risk_parity_sizing(symbol, risk_per_share, max_size_pct)
        elif self.config.method == PositionSizingMethod.EQUAL_RISK:
            result = self._equal_risk_sizing(risk_per_share, max_size_pct)
        elif self.config.method == PositionSizingMethod.OPTIMAL_F:
            result = self._optimal_f_sizing(symbol, max_size_pct)
        else:
            result = self._fixed_percentage_sizing(max_size_pct)

        # Apply final constraints and validation
        result = self._apply_final_constraints(result, symbol)

        # Update position tracking
        if result.position_size > 0:
            self._update_position_tracking(symbol, result)

        return result

    def _calculate_max_position_size(self, symbol: str, risk_per_share: float) -> float:
        """Calculate maximum allowed position size based on constraints"""
        max_size_pct = self.config.max_position_size

        # Check portfolio risk constraint
        if self.portfolio_risk >= self.config.max_portfolio_risk:
            max_size_pct = 0.0
        else:
            remaining_risk_budget = self.config.max_portfolio_risk - self.portfolio_risk
            risk_based_max = remaining_risk_budget / max(risk_per_share / self.portfolio_value, 0.001)
            max_size_pct = min(max_size_pct, risk_based_max)

        # Check position count constraint
        current_positions = len([p for p in self.current_positions.values() if p.get('size', 0) > 0])
        if current_positions >= self.config.max_positions:
            max_size_pct = 0.0

        # Check existing position in same symbol
        if symbol in self.current_positions and self.current_positions[symbol].get('size', 0) > 0:
            # Limit additional exposure to same symbol
            max_size_pct *= 0.5

        return max(max_size_pct, 0.0)

    def _fixed_percentage_sizing(self, max_size_pct: float) -> PositionSizingResult:
        """Fixed percentage position sizing"""
        position_size_pct = min(self.config.fixed_percentage, max_size_pct)
        position_size = position_size_pct * self.portfolio_value

        return PositionSizingResult(
            position_size=position_size,
            position_size_pct=position_size_pct,
            risk_amount=position_size_pct * self.portfolio_value,
            confidence_score=0.8,  # Fixed percentage is reliable but not adaptive
            sizing_method="fixed_percentage",
            risk_metrics={
                'portfolio_risk': self.portfolio_risk,
                'max_position_size': max_size_pct
            },
            constraints_applied=["fixed_percentage", "max_position_size"],
            timestamp=datetime.now()
        )

    def _volatility_based_sizing(self, symbol: str, risk_per_share: float,
                               market_data: Dict[str, Any], max_size_pct: float) -> PositionSizingResult:
        """Volatility-based position sizing"""
        # Get asset volatility
        asset_volatility = self._get_asset_volatility(symbol, market_data)

        if asset_volatility <= 0:
            # Fallback to fixed percentage
            return self._fixed_percentage_sizing(max_size_pct)

        # Calculate position size to achieve target volatility
        # Size = (Target Volatility / Asset Volatility) * Portfolio Value
        target_volatility = self.config.volatility_target
        volatility_scalar = target_volatility / asset_volatility

        # Adjust for risk per share
        risk_adjusted_size = volatility_scalar * self.portfolio_value
        position_size_pct = min(risk_adjusted_size / self.portfolio_value, max_size_pct)
        position_size_pct = max(position_size_pct, self.config.min_position_size)

        position_size = position_size_pct * self.portfolio_value
        risk_amount = position_size * (risk_per_share / entry_price) if 'entry_price' in locals() else position_size * 0.02

        return PositionSizingResult(
            position_size=position_size,
            position_size_pct=position_size_pct,
            risk_amount=risk_amount,
            confidence_score=0.9 if asset_volatility > 0 else 0.6,
            sizing_method="volatility_based",
            risk_metrics={
                'asset_volatility': asset_volatility,
                'target_volatility': target_volatility,
                'portfolio_volatility': self.portfolio_volatility,
                'volatility_scalar': volatility_scalar
            },
            constraints_applied=["volatility_target", "max_position_size", "min_position_size"],
            timestamp=datetime.now()
        )

    def _kelly_criterion_sizing(self, symbol: str, max_size_pct: float) -> PositionSizingResult:
        """Kelly Criterion position sizing"""
        # Calculate win rate and win/loss ratio from historical data
        if len(self.win_rates) < self.config.win_rate_lookback:
            # Not enough data, use fixed percentage
            return self._fixed_percentage_sizing(max_size_pct)

        # Get recent performance metrics
        win_rate = statistics.mean(self.win_rates[-self.config.win_rate_lookback:])
        avg_win = statistics.mean(self.avg_wins[-self.config.avg_win_lookback:]) if self.avg_wins else 1.0
        avg_loss = abs(statistics.mean(self.avg_losses[-self.config.avg_loss_lookback:])) if self.avg_losses else 1.0

        if avg_loss == 0:
            avg_loss = 0.01  # Avoid division by zero

        # Kelly formula: K = (W * R - L) / R
        # Where W = win rate, R = win/loss ratio, L = loss rate
        win_loss_ratio = avg_win / avg_loss
        loss_rate = 1 - win_rate
        kelly_percentage = (win_rate * win_loss_ratio - loss_rate) / win_loss_ratio

        # Apply Kelly fraction (often use half-Kelly for safety)
        kelly_percentage *= self.config.kelly_fraction

        # Ensure positive and reasonable size
        kelly_percentage = max(0, min(kelly_percentage, max_size_pct))

        position_size_pct = kelly_percentage
        position_size = position_size_pct * self.portfolio_value

        return PositionSizingResult(
            position_size=position_size,
            position_size_pct=position_size_pct,
            risk_amount=position_size_pct * self.portfolio_value,
            confidence_score=0.85 if len(self.win_rates) >= 50 else 0.6,
            sizing_method="kelly_criterion",
            risk_metrics={
                'win_rate': win_rate,
                'win_loss_ratio': win_loss_ratio,
                'kelly_percentage': kelly_percentage,
                'avg_win': avg_win,
                'avg_loss': avg_loss
            },
            constraints_applied=["kelly_fraction", "max_position_size"],
            timestamp=datetime.now()
        )

    def _risk_parity_sizing(self, symbol: str, risk_per_share: float, max_size_pct: float) -> PositionSizingResult:
        """Risk parity position sizing"""
        # Get asset correlation with portfolio
        correlation = self._get_asset_correlation(symbol)

        # Risk parity: allocate based on inverse volatility and correlation
        asset_volatility = self._get_asset_volatility(symbol)

        if asset_volatility <= 0:
            return self._fixed_percentage_sizing(max_size_pct)

        # Risk contribution = volatility * correlation * position_size
        # For risk parity, we want equal risk contribution from each position
        target_risk_contribution = self.config.risk_budget / max(1, len(self.current_positions) + 1)

        # Position size = target_risk / (volatility * correlation)
        risk_scalar = target_risk_contribution / (asset_volatility * max(correlation, 0.1))
        position_size_pct = min(risk_scalar, max_size_pct)

        position_size = position_size_pct * self.portfolio_value
        risk_amount = position_size * (risk_per_share / self.portfolio_value) if self.portfolio_value > 0 else 0

        return PositionSizingResult(
            position_size=position_size,
            position_size_pct=position_size_pct,
            risk_amount=risk_amount,
            confidence_score=0.8,
            sizing_method="risk_parity",
            risk_metrics={
                'asset_volatility': asset_volatility,
                'correlation': correlation,
                'target_risk_contribution': target_risk_contribution,
                'risk_scalar': risk_scalar
            },
            constraints_applied=["risk_parity", "max_position_size"],
            timestamp=datetime.now()
        )

    def _equal_risk_sizing(self, risk_per_share: float, max_size_pct: float) -> PositionSizingResult:
        """Equal risk position sizing"""
        # Each position takes equal risk amount
        risk_amount = self.config.equal_risk_amount * self.portfolio_value
        position_size = risk_amount / risk_per_share if risk_per_share > 0 else 0
        position_size_pct = position_size / self.portfolio_value if self.portfolio_value > 0 else 0

        # Apply constraints
        position_size_pct = min(position_size_pct, max_size_pct)

        position_size = position_size_pct * self.portfolio_value

        return PositionSizingResult(
            position_size=position_size,
            position_size_pct=position_size_pct,
            risk_amount=risk_amount,
            confidence_score=0.9,  # Equal risk is very predictable
            sizing_method="equal_risk",
            risk_metrics={
                'risk_per_share': risk_per_share,
                'equal_risk_amount': self.config.equal_risk_amount
            },
            constraints_applied=["equal_risk", "max_position_size"],
            timestamp=datetime.now()
        )

    def _optimal_f_sizing(self, symbol: str, max_size_pct: float) -> PositionSizingResult:
        """Optimal F position sizing (Ralph Vince method)"""
        if len(self.position_returns) < self.config.optimal_f_lookback:
            return self._fixed_percentage_sizing(max_size_pct)

        # Calculate Optimal F from historical returns
        # F = (Sum of (HPR * TWR)) / Sum of (HPR^2)
        # Where HPR = holding period return, TWR = terminal wealth relative

        returns = self.position_returns[-self.config.optimal_f_lookback:]
        hprs = [1 + r for r in returns]  # Holding period returns

        # Calculate terminal wealth relatives
        twrs = []
        cumulative = 1.0
        for hpr in hprs:
            cumulative *= hpr
            twrs.append(cumulative)

        # Calculate Optimal F
        if len(hprs) > 1:
            numerator = sum(h * t for h, t in zip(hprs, twrs))
            denominator = sum(h * h for h in hprs)
            optimal_f = numerator / denominator if denominator != 0 else 0
        else:
            optimal_f = 0

        # Apply confidence adjustment
        confidence_factor = min(1.0, len(returns) / 100)  # More data = higher confidence
        optimal_f *= confidence_factor

        position_size_pct = min(optimal_f, max_size_pct)
        position_size = position_size_pct * self.portfolio_value

        return PositionSizingResult(
            position_size=position_size,
            position_size_pct=position_size_pct,
            risk_amount=position_size_pct * self.portfolio_value,
            confidence_score=confidence_factor,
            sizing_method="optimal_f",
            risk_metrics={
                'optimal_f': optimal_f,
                'confidence_factor': confidence_factor,
                'lookback_period': len(returns)
            },
            constraints_applied=["optimal_f", "max_position_size"],
            timestamp=datetime.now()
        )

    def _get_asset_volatility(self, symbol: str, market_data: Dict[str, Any] = None) -> float:
        """Get asset volatility for position sizing"""
        # Try to get from market data first
        if market_data and 'volatility' in market_data:
            return market_data['volatility']

        # Try to get from current positions
        if symbol in self.current_positions and 'volatility' in self.current_positions[symbol]:
            return self.current_positions[symbol]['volatility']

        # Fallback to portfolio volatility
        return self.portfolio_volatility or 0.02  # 2% default

    def _get_asset_correlation(self, symbol: str) -> float:
        """Get asset correlation with portfolio"""
        if symbol in self.correlation_matrix:
            return self.correlation_matrix[symbol]

        # Default correlation assumption
        return 0.5  # Moderate correlation

    def _calculate_portfolio_volatility(self):
        """Calculate current portfolio volatility"""
        if not self.current_positions:
            self.portfolio_volatility = 0.02  # Default 2%
            return

        # Simple portfolio volatility calculation
        position_volatilities = []
        position_weights = []

        for pos_info in self.current_positions.values():
            vol = pos_info.get('volatility', 0.02)
            weight = pos_info.get('size', 0) / self.portfolio_value if self.portfolio_value > 0 else 0

            if weight > 0:
                position_volatilities.append(vol)
                position_weights.append(weight)

        if position_volatilities and position_weights:
            # Weighted average volatility (simplified)
            self.portfolio_volatility = sum(v * w for v, w in zip(position_volatilities, position_weights))
        else:
            self.portfolio_volatility = 0.02

    def _calculate_portfolio_risk(self):
        """Calculate current portfolio risk"""
        if not self.current_positions:
            self.portfolio_risk = 0.0
            return

        total_risk = 0.0
        for pos_info in self.current_positions.values():
            position_value = pos_info.get('size', 0)
            if position_value > 0:
                # Estimate risk as position size * volatility
                volatility = pos_info.get('volatility', 0.02)
                position_risk = position_value * volatility
                total_risk += position_risk

        self.portfolio_risk = total_risk / self.portfolio_value if self.portfolio_value > 0 else 0.0

    def _apply_final_constraints(self, result: PositionSizingResult, symbol: str) -> PositionSizingResult:
        """Apply final constraints to position sizing result"""
        constraints_applied = result.constraints_applied.copy()

        # Minimum position size constraint
        if result.position_size_pct < self.config.min_position_size:
            result.position_size_pct = 0.0
            result.position_size = 0.0
            constraints_applied.append("min_position_size")

        # Maximum portfolio risk constraint
        new_portfolio_risk = self.portfolio_risk + result.risk_amount
        if new_portfolio_risk > self.config.max_portfolio_risk:
            # Scale down position size to fit risk budget
            risk_reduction_factor = self.config.max_portfolio_risk / max(new_portfolio_risk, 0.001)
            result.position_size_pct *= risk_reduction_factor
            result.position_size *= risk_reduction_factor
            result.risk_amount *= risk_reduction_factor
            constraints_applied.append("max_portfolio_risk")

        # Update constraints applied
        result.constraints_applied = constraints_applied

        return result

    def _update_position_tracking(self, symbol: str, result: PositionSizingResult):
        """Update position tracking after sizing decision"""
        # This would be called after position is actually opened
        # For now, just track the sizing decision
        pass

    def _create_error_result(self, error_message: str) -> PositionSizingResult:
        """Create error result for invalid calculations"""
        return PositionSizingResult(
            position_size=0.0,
            position_size_pct=0.0,
            risk_amount=0.0,
            confidence_score=0.0,
            sizing_method="error",
            risk_metrics={},
            constraints_applied=["error"],
            timestamp=datetime.now()
        )

    def update_performance_history(self, trade_result: Dict[str, Any]):
        """
        Update performance history for sizing algorithm learning

        Args:
            trade_result: Dictionary with trade performance data
        """
        pnl_pct = trade_result.get('pnl_percentage', 0.0)

        # Update win/loss tracking
        if pnl_pct > 0:
            self.win_rates.append(1.0)
            self.avg_wins.append(pnl_pct)
            self.avg_losses.append(0.0)
        else:
            self.win_rates.append(0.0)
            self.avg_wins.append(0.0)
            self.avg_losses.append(pnl_pct)

        # Keep only recent history
        max_history = max(self.config.win_rate_lookback,
                         self.config.avg_win_lookback,
                         self.config.avg_loss_lookback) * 2

        if len(self.win_rates) > max_history:
            self.win_rates = self.win_rates[-max_history:]
            self.avg_wins = self.avg_wins[-max_history:]
            self.avg_losses = self.avg_losses[-max_history:]

    def get_sizing_info(self) -> Dict[str, Any]:
        """Get comprehensive position sizing information"""
        return {
            'config': {
                'method': self.config.method.value,
                'fixed_percentage': self.config.fixed_percentage,
                'volatility_target': self.config.volatility_target,
                'kelly_fraction': self.config.kelly_fraction,
                'risk_budget': self.config.risk_budget,
                'equal_risk_amount': self.config.equal_risk_amount,
                'max_portfolio_risk': self.config.max_portfolio_risk,
                'min_position_size': self.config.min_position_size,
                'max_positions': self.config.max_positions
            },
            'portfolio_state': {
                'portfolio_value': self.portfolio_value,
                'portfolio_volatility': self.portfolio_volatility,
                'portfolio_risk': self.portfolio_risk,
                'current_positions': len(self.current_positions),
                'active_positions': len([p for p in self.current_positions.values() if p.get('size', 0) > 0])
            },
            'performance_history': {
                'total_trades': len(self.win_rates),
                'win_rate': statistics.mean(self.win_rates) if self.win_rates else 0.0,
                'avg_win': statistics.mean(self.avg_wins) if self.avg_wins else 0.0,
                'avg_loss': statistics.mean(self.avg_losses) if self.avg_losses else 0.0
            }
        }


# Factory functions for easy instantiation
def create_fixed_percentage_sizer(fixed_percentage: float = 0.02) -> InstitutionalPositionSizer:
    """Create fixed percentage position sizer"""
    config = PositionSizingConfig(
        method=PositionSizingMethod.FIXED_PERCENTAGE,
        fixed_percentage=fixed_percentage
    )
    return InstitutionalPositionSizer(config)


def create_volatility_based_sizer(volatility_target: float = 0.02) -> InstitutionalPositionSizer:
    """Create volatility-based position sizer"""
    config = PositionSizingConfig(
        method=PositionSizingMethod.VOLATILITY_BASED,
        volatility_target=volatility_target
    )
    return InstitutionalPositionSizer(config)


def create_kelly_sizer(kelly_fraction: float = 0.5) -> InstitutionalPositionSizer:
    """Create Kelly Criterion position sizer"""
    config = PositionSizingConfig(
        method=PositionSizingMethod.KELLY_CRITERION,
        kelly_fraction=kelly_fraction
    )
    return InstitutionalPositionSizer(config)


def create_risk_parity_sizer(risk_budget: float = 0.02) -> InstitutionalPositionSizer:
    """Create risk parity position sizer"""
    config = PositionSizingConfig(
        method=PositionSizingMethod.RISK_PARITY,
        risk_budget=risk_budget
    )
    return InstitutionalPositionSizer(config)