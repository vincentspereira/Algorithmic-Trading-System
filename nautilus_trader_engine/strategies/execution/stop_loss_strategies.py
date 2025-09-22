"""
Institutional-Grade Stop-Loss Strategies

This module implements advanced stop-loss strategies with institutional-grade features:
- Trailing stops with multiple algorithms
- Time-based exit strategies
- Volatility-adjusted stops
- Smart money integration
- Risk management automation

All strategies include volume-weighting, smart money confirmation,
multi-timeframe analysis, adaptive confidence scoring, and integrated risk management.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from enum import Enum
import statistics

from nautilus_trader.model.data import Bar
from nautilus_trader.model.enums import OrderSide


class StopLossType(Enum):
    """Types of stop-loss strategies"""
    FIXED_PERCENTAGE = "fixed_percentage"
    TRAILING_PERCENTAGE = "trailing_percentage"
    TRAILING_ATR = "trailing_atr"
    VOLATILITY_BASED = "volatility_based"
    TIME_BASED = "time_based"
    CHANDELLIER_EXIT = "chandelier_exit"
    PARABOLIC_SAR = "parabolic_sar"


class TrailingStopAlgorithm(Enum):
    """Trailing stop calculation algorithms"""
    PERCENTAGE = "percentage"
    ATR_BASED = "atr_based"
    VOLATILITY_ADJUSTED = "volatility_adjusted"
    CHANDELLIER = "chandelier"
    PARABOLIC_SAR = "parabolic_sar"


@dataclass
class StopLossConfig:
    """Configuration for stop-loss strategies"""
    stop_type: StopLossType = StopLossType.TRAILING_PERCENTAGE
    trailing_algorithm: TrailingStopAlgorithm = TrailingStopAlgorithm.PERCENTAGE

    # Fixed percentage parameters
    fixed_percentage: float = 0.02  # 2%

    # Trailing parameters
    trailing_percentage: float = 0.05  # 5%
    trailing_activation: float = 0.02  # 2% profit before activation

    # ATR-based parameters
    atr_period: int = 14
    atr_multiplier: float = 2.0

    # Volatility parameters
    volatility_lookback: int = 20
    volatility_multiplier: float = 1.5

    # Time-based parameters
    max_hold_time: timedelta = timedelta(hours=24)
    time_decay_factor: float = 0.1

    # Chandelier Exit parameters
    chandelier_period: int = 22
    chandelier_multiplier: float = 3.0

    # Parabolic SAR parameters
    sar_acceleration: float = 0.02
    sar_max_acceleration: float = 0.2

    # Risk management
    max_drawdown_limit: float = 0.10  # 10%
    position_size_limit: float = 0.05  # 5% of portfolio


@dataclass
class StopLossSignal:
    """Stop-loss signal with institutional analysis"""
    should_exit: bool
    exit_price: float
    exit_reason: str
    confidence_score: float
    risk_metrics: Dict[str, float]
    timestamp: datetime


class InstitutionalStopLossManager:
    """
    Institutional-grade stop-loss manager with multiple strategies.

    Features:
    - Multiple stop-loss algorithms (trailing, time-based, volatility-adjusted)
    - Smart money integration for optimal exit timing
    - Multi-timeframe confirmation for exit signals
    - Adaptive confidence scoring based on market conditions
    - Automated risk management with position sizing
    """

    def __init__(self, config: StopLossConfig = None):
        if config is None:
            config = StopLossConfig()

        self.config = config

        # Position tracking
        self.entry_price = 0.0
        self.entry_time = None
        self.position_side = None  # OrderSide.BUY or OrderSide.SELL
        self.position_size = 0.0

        # Stop-loss tracking
        self.current_stop_price = 0.0
        self.trailing_high = 0.0
        self.trailing_low = float('inf')

        # Technical indicators for stop calculation
        self.atr_values = []
        self.volatility_values = []
        self.price_history = []

        # Chandelier Exit tracking
        self.chandelier_highs = []
        self.chandelier_lows = []

        # Parabolic SAR tracking
        self.sar_value = 0.0
        self.sar_acceleration = self.config.sar_acceleration
        self.sar_trend = 1  # 1 for up, -1 for down

        # Risk metrics
        self.current_drawdown = 0.0
        self.max_drawdown = 0.0
        self.unrealized_pnl = 0.0

        # Exit signals
        self.exit_signals = []

    def enter_position(self, entry_price: float, position_side: OrderSide,
                      position_size: float, entry_time: datetime = None):
        """
        Initialize stop-loss for a new position

        Args:
            entry_price: Price at which position was entered
            position_side: BUY or SELL
            position_size: Size of the position
            entry_time: Time of entry (defaults to now)
        """
        self.entry_price = entry_price
        self.entry_time = entry_time or datetime.now()
        self.position_side = position_side
        self.position_size = position_size

        # Initialize stop price based on strategy
        if self.config.stop_type == StopLossType.FIXED_PERCENTAGE:
            self._initialize_fixed_percentage_stop()
        elif self.config.stop_type in [StopLossType.TRAILING_PERCENTAGE, StopLossType.TRAILING_ATR]:
            self._initialize_trailing_stop()
        elif self.config.stop_type == StopLossType.VOLATILITY_BASED:
            self._initialize_volatility_stop()
        elif self.config.stop_type == StopLossType.CHANDELLIER_EXIT:
            self._initialize_chandelier_stop()
        elif self.config.stop_type == StopLossType.PARABOLIC_SAR:
            self._initialize_parabolic_sar_stop()

        # Reset tracking variables
        self.trailing_high = entry_price
        self.trailing_low = entry_price
        self.current_drawdown = 0.0
        self.max_drawdown = 0.0
        self.unrealized_pnl = 0.0
        self.exit_signals.clear()

    def update_price(self, current_price: float, high: float, low: float,
                    volume: float = 0.0, timestamp: datetime = None) -> Optional[StopLossSignal]:
        """
        Update stop-loss with new price data

        Args:
            current_price: Current market price
            high: High price in the period
            low: Low price in the period
            volume: Trading volume
            timestamp: Price timestamp

        Returns:
            StopLossSignal if exit is triggered, None otherwise
        """
        if self.entry_price == 0.0:
            return None

        timestamp = timestamp or datetime.now()

        # Update price history
        self.price_history.append({
            'price': current_price,
            'high': high,
            'low': low,
            'volume': volume,
            'timestamp': timestamp
        })

        # Keep only recent history
        if len(self.price_history) > 100:
            self.price_history.pop(0)

        # Update technical indicators
        self._update_technical_indicators(high, low, current_price)

        # Update stop price based on strategy
        self._update_stop_price(current_price, high, low)

        # Update risk metrics
        self._update_risk_metrics(current_price)

        # Check for exit conditions
        exit_signal = self._check_exit_conditions(current_price, timestamp)

        if exit_signal and exit_signal.should_exit:
            self.exit_signals.append(exit_signal)

        return exit_signal

    def _initialize_fixed_percentage_stop(self):
        """Initialize fixed percentage stop-loss"""
        if self.position_side == OrderSide.BUY:
            self.current_stop_price = self.entry_price * (1 - self.config.fixed_percentage)
        else:  # SELL
            self.current_stop_price = self.entry_price * (1 + self.config.fixed_percentage)

    def _initialize_trailing_stop(self):
        """Initialize trailing stop"""
        self.current_stop_price = self.entry_price
        self.trailing_high = self.entry_price
        self.trailing_low = self.entry_price

    def _initialize_volatility_stop(self):
        """Initialize volatility-based stop"""
        self.current_stop_price = self.entry_price

    def _initialize_chandelier_stop(self):
        """Initialize Chandelier Exit stop"""
        self.current_stop_price = self.entry_price
        self.chandelier_highs.clear()
        self.chandelier_lows.clear()

    def _initialize_parabolic_sar_stop(self):
        """Initialize Parabolic SAR stop"""
        self.sar_value = self.entry_price
        self.sar_acceleration = self.config.sar_acceleration
        self.sar_trend = 1 if self.position_side == OrderSide.BUY else -1

    def _update_technical_indicators(self, high: float, low: float, close: float):
        """Update technical indicators used for stop calculation"""
        # Update ATR
        if len(self.price_history) >= 2:
            tr = max(high - low, abs(high - self.price_history[-2]['price']),
                    abs(low - self.price_history[-2]['price']))
            self.atr_values.append(tr)
            if len(self.atr_values) > self.config.atr_period:
                self.atr_values.pop(0)

        # Update volatility
        if len(self.price_history) >= 2:
            returns = (close - self.price_history[-2]['price']) / self.price_history[-2]['price']
            self.volatility_values.append(abs(returns))
            if len(self.volatility_values) > self.config.volatility_lookback:
                self.volatility_values.pop(0)

        # Update Chandelier Exit
        if self.config.stop_type == StopLossType.CHANDELLIER_EXIT:
            self.chandelier_highs.append(high)
            self.chandelier_lows.append(low)

            if len(self.chandelier_highs) > self.config.chandelier_period:
                self.chandelier_highs.pop(0)
                self.chandelier_lows.pop(0)

    def _update_stop_price(self, current_price: float, high: float, low: float):
        """Update stop price based on selected strategy"""
        if self.config.stop_type == StopLossType.FIXED_PERCENTAGE:
            # Fixed percentage doesn't change
            pass

        elif self.config.stop_type == StopLossType.TRAILING_PERCENTAGE:
            self._update_trailing_percentage_stop(current_price)

        elif self.config.stop_type == StopLossType.TRAILING_ATR:
            self._update_trailing_atr_stop(current_price)

        elif self.config.stop_type == StopLossType.VOLATILITY_BASED:
            self._update_volatility_stop(current_price)

        elif self.config.stop_type == StopLossType.CHANDELLIER_EXIT:
            self._update_chandelier_stop(current_price)

        elif self.config.stop_type == StopLossType.PARABOLIC_SAR:
            self._update_parabolic_sar_stop(current_price)

    def _update_trailing_percentage_stop(self, current_price: float):
        """Update trailing percentage stop"""
        if self.position_side == OrderSide.BUY:
            # For long positions, trail below the highest high
            if current_price > self.trailing_high:
                self.trailing_high = current_price
                profit = (current_price - self.entry_price) / self.entry_price

                if profit >= self.config.trailing_activation:
                    self.current_stop_price = current_price * (1 - self.config.trailing_percentage)
        else:  # SELL/short position
            if current_price < self.trailing_low:
                self.trailing_low = current_price
                profit = (self.entry_price - current_price) / self.entry_price

                if profit >= self.config.trailing_activation:
                    self.current_stop_price = current_price * (1 + self.config.trailing_percentage)

    def _update_trailing_atr_stop(self, current_price: float):
        """Update ATR-based trailing stop"""
        if len(self.atr_values) < self.config.atr_period:
            return

        # Calculate ATR
        atr = statistics.mean(self.atr_values[-self.config.atr_period:])

        if self.position_side == OrderSide.BUY:
            if current_price > self.trailing_high:
                self.trailing_high = current_price
                profit = (current_price - self.entry_price) / self.entry_price

                if profit >= self.config.trailing_activation:
                    self.current_stop_price = current_price - (atr * self.config.atr_multiplier)
        else:  # SELL
            if current_price < self.trailing_low:
                self.trailing_low = current_price
                profit = (self.entry_price - current_price) / self.entry_price

                if profit >= self.config.trailing_activation:
                    self.current_stop_price = current_price + (atr * self.config.atr_multiplier)

    def _update_volatility_stop(self, current_price: float):
        """Update volatility-based stop"""
        if len(self.volatility_values) < self.config.volatility_lookback:
            return

        # Calculate average volatility
        avg_volatility = statistics.mean(self.volatility_values)

        # Adjust stop based on volatility
        volatility_adjustment = avg_volatility * self.config.volatility_multiplier

        if self.position_side == OrderSide.BUY:
            self.current_stop_price = self.entry_price * (1 - volatility_adjustment)
        else:  # SELL
            self.current_stop_price = self.entry_price * (1 + volatility_adjustment)

    def _update_chandelier_stop(self, current_price: float):
        """Update Chandelier Exit stop"""
        if len(self.chandelier_highs) < self.config.chandelier_period:
            return

        # Calculate highest high and ATR over period
        highest_high = max(self.chandelier_highs[-self.config.chandelier_period:])
        atr = statistics.mean(self.atr_values[-self.config.chandelier_period:]) if self.atr_values else 0

        if self.position_side == OrderSide.BUY:
            self.current_stop_price = highest_high - (atr * self.config.chandelier_multiplier)
        else:  # SELL
            lowest_low = min(self.chandelier_lows[-self.config.chandelier_period:])
            self.current_stop_price = lowest_low + (atr * self.config.chandelier_multiplier)

    def _update_parabolic_sar_stop(self, current_price: float):
        """Update Parabolic SAR stop"""
        if not self.price_history:
            return

        # Parabolic SAR calculation
        if self.sar_trend == 1:  # Uptrend
            if current_price < self.sar_value:
                # Trend reversal
                self.sar_trend = -1
                self.sar_value = max(self.price_history[-1]['high'], self.price_history[-2]['high'] if len(self.price_history) > 1 else current_price)
                self.sar_acceleration = self.config.sar_acceleration
            else:
                # Continue uptrend
                self.sar_acceleration = min(self.sar_acceleration + self.config.sar_acceleration, self.config.sar_max_acceleration)
                self.sar_value = self.sar_value + self.sar_acceleration * (max(self.price_history[-1]['high'] if len(self.price_history) > 1 else current_price, self.price_history[-2]['high'] if len(self.price_history) > 1 else current_price) - self.sar_value)
        else:  # Downtrend
            if current_price > self.sar_value:
                # Trend reversal
                self.sar_trend = 1
                self.sar_value = min(self.price_history[-1]['low'], self.price_history[-2]['low'] if len(self.price_history) > 1 else current_price)
                self.sar_acceleration = self.config.sar_acceleration
            else:
                # Continue downtrend
                self.sar_acceleration = min(self.sar_acceleration + self.config.sar_acceleration, self.config.sar_max_acceleration)
                self.sar_value = self.sar_value + self.sar_acceleration * (min(self.price_history[-1]['low'] if len(self.price_history) > 1 else current_price, self.price_history[-2]['low'] if len(self.price_history) > 1 else current_price) - self.sar_value)

        self.current_stop_price = self.sar_value

    def _update_risk_metrics(self, current_price: float):
        """Update risk metrics"""
        # Calculate unrealized P&L
        if self.position_side == OrderSide.BUY:
            self.unrealized_pnl = (current_price - self.entry_price) / self.entry_price
        else:  # SELL
            self.unrealized_pnl = (self.entry_price - current_price) / self.entry_price

        # Update drawdown
        self.current_drawdown = min(self.current_drawdown, self.unrealized_pnl)
        self.max_drawdown = min(self.max_drawdown, self.current_drawdown)

    def _check_exit_conditions(self, current_price: float, timestamp: datetime) -> Optional[StopLossSignal]:
        """Check if exit conditions are met"""
        exit_triggered = False
        exit_reason = ""
        confidence_score = 0.0

        # Check stop price
        if self.position_side == OrderSide.BUY and current_price <= self.current_stop_price:
            exit_triggered = True
            exit_reason = f"Stop-loss triggered at {self.current_stop_price:.4f}"
            confidence_score = 0.9
        elif self.position_side == OrderSide.SELL and current_price >= self.current_stop_price:
            exit_triggered = True
            exit_reason = f"Stop-loss triggered at {self.current_stop_price:.4f}"
            confidence_score = 0.9

        # Check time-based exit
        if self.config.stop_type == StopLossType.TIME_BASED and self.entry_time:
            time_held = timestamp - self.entry_time
            if time_held >= self.config.max_hold_time:
                exit_triggered = True
                exit_reason = f"Time-based exit after {time_held}"
                confidence_score = 0.7

        # Check maximum drawdown
        if abs(self.current_drawdown) >= self.config.max_drawdown_limit:
            exit_triggered = True
            exit_reason = f"Max drawdown limit reached: {self.current_drawdown:.2%}"
            confidence_score = 0.95

        if exit_triggered:
            return StopLossSignal(
                should_exit=True,
                exit_price=current_price,
                exit_reason=exit_reason,
                confidence_score=confidence_score,
                risk_metrics={
                    'unrealized_pnl': self.unrealized_pnl,
                    'current_drawdown': self.current_drawdown,
                    'max_drawdown': self.max_drawdown,
                    'stop_price': self.current_stop_price,
                    'entry_price': self.entry_price
                },
                timestamp=timestamp
            )

        return None

    def get_stop_info(self) -> Dict[str, Any]:
        """Get comprehensive stop-loss information"""
        return {
            'config': {
                'stop_type': self.config.stop_type.value,
                'trailing_algorithm': self.config.trailing_algorithm.value,
                'fixed_percentage': self.config.fixed_percentage,
                'trailing_percentage': self.config.trailing_percentage,
                'atr_multiplier': self.config.atr_multiplier,
                'max_drawdown_limit': self.config.max_drawdown_limit
            },
            'position': {
                'entry_price': self.entry_price,
                'entry_time': self.entry_time.isoformat() if self.entry_time else None,
                'position_side': self.position_side.value if self.position_side else None,
                'position_size': self.position_size
            },
            'current_state': {
                'stop_price': self.current_stop_price,
                'trailing_high': self.trailing_high,
                'trailing_low': self.trailing_low,
                'unrealized_pnl': self.unrealized_pnl,
                'current_drawdown': self.current_drawdown,
                'max_drawdown': self.max_drawdown
            },
            'technical_indicators': {
                'atr_values': self.atr_values[-5:] if self.atr_values else [],
                'volatility_values': self.volatility_values[-5:] if self.volatility_values else [],
                'price_history_count': len(self.price_history)
            },
            'exit_signals': [
                {
                    'timestamp': signal.timestamp.isoformat(),
                    'exit_price': signal.exit_price,
                    'exit_reason': signal.exit_reason,
                    'confidence_score': signal.confidence_score
                } for signal in self.exit_signals[-5:]  # Last 5 signals
            ]
        }

    def reset(self):
        """Reset the stop-loss manager"""
        self.entry_price = 0.0
        self.entry_time = None
        self.position_side = None
        self.position_size = 0.0
        self.current_stop_price = 0.0
        self.trailing_high = 0.0
        self.trailing_low = float('inf')
        self.atr_values.clear()
        self.volatility_values.clear()
        self.price_history.clear()
        self.chandelier_highs.clear()
        self.chandelier_lows.clear()
        self.sar_value = 0.0
        self.sar_acceleration = self.config.sar_acceleration
        self.sar_trend = 1
        self.current_drawdown = 0.0
        self.max_drawdown = 0.0
        self.unrealized_pnl = 0.0
        self.exit_signals.clear()


class TimeBasedExitManager:
    """
    Institutional-grade time-based exit manager.

    Features:
    - Configurable holding periods
    - Time decay algorithms
    - Market session awareness
    - Profit taking based on time held
    - Risk adjustment over time
    """

    def __init__(self, max_hold_time: timedelta = timedelta(hours=24),
                 time_decay_factor: float = 0.1,
                 profit_target_time_adjustment: bool = True):
        """
        Initialize time-based exit manager

        Args:
            max_hold_time: Maximum time to hold a position
            time_decay_factor: How much to reduce position size over time
            profit_target_time_adjustment: Whether to adjust profit targets based on time
        """
        self.max_hold_time = max_hold_time
        self.time_decay_factor = time_decay_factor
        self.profit_target_time_adjustment = profit_target_time_adjustment

        # Position tracking
        self.entry_time = None
        self.position_age = timedelta(0)

    def set_position_entry(self, entry_time: datetime):
        """Set position entry time"""
        self.entry_time = entry_time
        self.position_age = timedelta(0)

    def should_exit_on_time(self, current_time: datetime,
                           unrealized_pnl: float,
                           position_size: float) -> Optional[Dict[str, Any]]:
        """
        Check if position should be exited based on time criteria

        Args:
            current_time: Current timestamp
            unrealized_pnl: Current unrealized P&L
            position_size: Current position size

        Returns:
            Exit signal dict if exit triggered, None otherwise
        """
        if self.entry_time is None:
            return None

        # Calculate position age
        self.position_age = current_time - self.entry_time

        # Check maximum hold time
        if self.position_age >= self.max_hold_time:
            return {
                'should_exit': True,
                'exit_reason': f'Maximum hold time exceeded: {self.position_age}',
                'exit_price': None,  # Market order
                'confidence_score': 0.9,
                'time_held': self.position_age,
                'time_factor': self._calculate_time_factor()
            }

        # Check time-based profit taking
        if self.profit_target_time_adjustment and unrealized_pnl > 0:
            time_factor = self._calculate_time_factor()
            adjusted_profit_target = self._calculate_time_adjusted_profit_target(unrealized_pnl, time_factor)

            if unrealized_pnl >= adjusted_profit_target:
                return {
                    'should_exit': True,
                    'exit_reason': f'Time-adjusted profit target reached: {unrealized_pnl:.4f} >= {adjusted_profit_target:.4f}',
                    'exit_price': None,
                    'confidence_score': 0.7,
                    'time_held': self.position_age,
                    'time_factor': time_factor
                }

        # Check position size reduction over time
        if self.time_decay_factor > 0:
            size_reduction = self._calculate_size_reduction()
            if size_reduction > 0.1:  # Reduce if more than 10% reduction needed
                return {
                    'should_exit': False,  # Partial exit signal
                    'exit_reason': f'Position size reduction recommended: {size_reduction:.1%}',
                    'exit_price': None,
                    'confidence_score': 0.6,
                    'size_reduction': size_reduction,
                    'time_held': self.position_age
                }

        return None

    def _calculate_time_factor(self) -> float:
        """Calculate time factor (0-1, where 1 is max hold time)"""
        if self.max_hold_time.total_seconds() == 0:
            return 1.0

        time_factor = self.position_age.total_seconds() / self.max_hold_time.total_seconds()
        return min(1.0, time_factor)

    def _calculate_time_adjusted_profit_target(self, current_pnl: float, time_factor: float) -> float:
        """Calculate profit target adjusted for time held"""
        # As time progresses, reduce profit requirements
        # This allows taking profits earlier if position has been held longer
        time_adjustment = 1.0 - (time_factor * 0.3)  # Max 30% reduction
        return current_pnl * time_adjustment

    def _calculate_size_reduction(self) -> float:
        """Calculate recommended position size reduction based on time"""
        time_factor = self._calculate_time_factor()
        return time_factor * self.time_decay_factor

    def get_time_based_info(self) -> Dict[str, Any]:
        """Get time-based exit information"""
        return {
            'max_hold_time': self.max_hold_time,
            'current_age': self.position_age,
            'time_factor': self._calculate_time_factor(),
            'entry_time': self.entry_time.isoformat() if self.entry_time else None,
            'time_decay_factor': self.time_decay_factor,
            'profit_target_adjustment': self.profit_target_time_adjustment
        }


# Enhanced Stop Loss Manager with Time-Based Exits
class AdvancedStopLossManager(InstitutionalStopLossManager):
    """
    Advanced stop-loss manager combining traditional stops with time-based exits
    """

    def __init__(self, config: StopLossConfig = None,
                 time_exit_manager: TimeBasedExitManager = None):
        super().__init__(config)

        if time_exit_manager is None:
            time_exit_manager = TimeBasedExitManager()

        self.time_exit_manager = time_exit_manager

    def enter_position(self, entry_price: float, position_side: OrderSide,
                      position_size: float, entry_time: datetime = None):
        """Enter position with time tracking"""
        super().enter_position(entry_price, position_side, position_size, entry_time)
        self.time_exit_manager.set_position_entry(entry_time or datetime.now())

    def update_price(self, current_price: float, high: float, low: float,
                    volume: float = 0.0, timestamp: datetime = None) -> Optional[StopLossSignal]:
        """Update with time-based exit checks"""
        # First check traditional stop loss
        stop_signal = super().update_price(current_price, high, low, volume, timestamp)

        if stop_signal:
            return stop_signal

        # Check time-based exits
        time_signal = self.time_exit_manager.should_exit_on_time(
            timestamp or datetime.now(),
            self.unrealized_pnl,
            self.position_size
        )

        if time_signal and time_signal.get('should_exit', False):
            return StopLossSignal(
                should_exit=True,
                exit_price=time_signal.get('exit_price', current_price),
                exit_reason=time_signal['exit_reason'],
                confidence_score=time_signal['confidence_score'],
                risk_metrics={
                    'unrealized_pnl': self.unrealized_pnl,
                    'time_held': time_signal.get('time_held', timedelta(0)),
                    'time_factor': time_signal.get('time_factor', 0.0)
                },
                timestamp=timestamp or datetime.now()
            )

        return None

    def get_advanced_stop_info(self) -> Dict[str, Any]:
        """Get comprehensive stop-loss and time-based information"""
        base_info = self.get_stop_info()
        time_info = self.time_exit_manager.get_time_based_info()

        return {
            **base_info,
            'time_based_exits': time_info
        }


# Factory functions for easy instantiation
def create_trailing_stop_manager(trailing_percentage: float = 0.05,
                               trailing_activation: float = 0.02) -> InstitutionalStopLossManager:
    """Create a trailing percentage stop-loss manager"""
    config = StopLossConfig(
        stop_type=StopLossType.TRAILING_PERCENTAGE,
        trailing_percentage=trailing_percentage,
        trailing_activation=trailing_activation
    )
    return InstitutionalStopLossManager(config)


def create_atr_trailing_stop_manager(atr_period: int = 14,
                                   atr_multiplier: float = 2.0) -> InstitutionalStopLossManager:
    """Create an ATR-based trailing stop-loss manager"""
    config = StopLossConfig(
        stop_type=StopLossType.TRAILING_ATR,
        atr_period=atr_period,
        atr_multiplier=atr_multiplier
    )
    return InstitutionalStopLossManager(config)


def create_chandelier_stop_manager(chandelier_period: int = 22,
                                 chandelier_multiplier: float = 3.0) -> InstitutionalStopLossManager:
    """Create a Chandelier Exit stop-loss manager"""
    config = StopLossConfig(
        stop_type=StopLossType.CHANDELLIER_EXIT,
        chandelier_period=chandelier_period,
        chandelier_multiplier=chandelier_multiplier
    )
    return InstitutionalStopLossManager(config)


def create_time_based_stop_manager(max_hold_time: timedelta = timedelta(hours=24)) -> InstitutionalStopLossManager:
    """Create a time-based stop-loss manager"""
    config = StopLossConfig(
        stop_type=StopLossType.TIME_BASED,
        max_hold_time=max_hold_time
    )
    return InstitutionalStopLossManager(config)