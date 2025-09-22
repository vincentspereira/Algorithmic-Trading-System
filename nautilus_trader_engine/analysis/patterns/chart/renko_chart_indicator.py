"""
Institutional-Grade Renko Chart Indicator

This module implements an enhanced Renko chart indicator with institutional-grade features:
- Volume confirmation scoring
- Market regime adaptation
- Multi-timeframe convergence
- Smart money detection
- Automated risk management

Renko charts filter out noise and focus on price movement in fixed amounts (bricks).
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from collections import deque
from enum import Enum

from nautilus_trader.model.data import Bar

from nautilus_trader_engine.indicators.base import (
    AugmentedIndicator,
    AugmentedIndicatorConfig,
    IndicatorSignal,
    SignalType,
)


class RenkoDirection(Enum):
    """Renko brick direction"""
    UP = "up"
    DOWN = "down"
    NEUTRAL = "neutral"


@dataclass
class RenkoBrick:
    """Renko brick data structure"""
    direction: RenkoDirection
    open_price: float
    close_price: float
    high_price: float
    low_price: float
    timestamp: datetime
    volume: float = 0.0


@dataclass
class RenkoConfig(AugmentedIndicatorConfig):
    """Configuration for Renko Chart indicator"""
    brick_size: float = 1.0  # Fixed price movement for each brick
    brick_size_type: str = "fixed"  # "fixed" or "atr" (Average True Range)
    atr_period: int = 14  # ATR period for dynamic brick sizing
    max_bricks: int = 100  # Maximum bricks to keep in history


class RenkoChartIndicator(AugmentedIndicator):
    """
    Institutional-grade Renko Chart indicator implementing 5-pillar architecture.

    Renko charts plot price movement in fixed amounts (bricks), filtering out noise
    and focusing on trend direction and strength.

    Features:
    - Trend identification with noise reduction
    - Support/resistance level identification at brick boundaries
    - Momentum and trend strength assessment
    - Market regime adaptation based on brick direction changes
    - Multi-timeframe convergence for institutional confirmation
    - Smart money trend analysis for institutional flow detection
    - Automated risk management for trend-following strategies
    """

    def __init__(self, config: RenkoConfig = None):
        if config is None:
            config = RenkoConfig()

        super().__init__(config)
        self.renko_config = config

        # Renko chart data
        self._bricks = deque(maxlen=self.renko_config.max_bricks)
        self._current_brick = None
        self._pending_price = None

        # Price tracking for brick formation
        self._last_price = None
        self._brick_size = self.renko_config.brick_size

        # ATR calculation for dynamic brick sizing
        self._atr_values = deque(maxlen=self.renko_config.atr_period)
        self._highs = deque(maxlen=self.renko_config.buffer_size)
        self._lows = deque(maxlen=self.renko_config.buffer_size)
        self._closes = deque(maxlen=self.renko_config.buffer_size)

        # Trend analysis
        self._trend_direction = RenkoDirection.NEUTRAL
        self._trend_strength = 0.0
        self._momentum_alignment = 0.0

        # Signal analysis
        self._direction_change_signals = 0
        self._brick_sequence_signals = 0
        self._breakout_signals = 0
        self._signal_strength = 0.0

        # Market structure
        self._support_levels = []
        self._resistance_levels = []
        self._brick_touches = 0

        # Institutional analysis
        self._institutional_renko = 0.0
        self._smart_money_trend = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Renko Chart is ready to provide signals"""
        return len(self._bricks) >= 2 and self._current_brick is not None

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update Renko chart analysis

        Args:
            bar (Bar): New bar data
        """
        # Extract OHLC data
        if hasattr(bar, 'high') and hasattr(bar, 'low') and hasattr(bar, 'close'):
            open_price = bar.open if hasattr(bar, 'open') else bar.close
            high = bar.high
            low = bar.low
            close = bar.close
            volume = bar.volume if hasattr(bar, 'volume') else 0.0
        else:
            open_price = bar.get('open', bar.get('close', 0.0))
            high = bar.get('high', bar.get('close', 0.0))
            low = bar.get('low', bar.get('close', 0.0))
            close = bar.get('close', bar.get('price', 0.0))
            volume = bar.get('volume', 0.0)

        # Update ATR for dynamic brick sizing
        if self.renko_config.brick_size_type == "atr":
            self._update_atr(high, low, close)

        # Update Renko bricks
        self._update_renko_chart(close, volume, bar.timestamp if hasattr(bar, 'timestamp') else datetime.now())

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_atr(self, high: float, low: float, close: float):
        """Update Average True Range for dynamic brick sizing"""
        self._highs.append(high)
        self._lows.append(low)
        self._closes.append(close)

        if len(self._closes) >= 2:
            # Calculate True Range
            tr1 = high - low
            tr2 = abs(high - self._closes[-2])
            tr3 = abs(low - self._closes[-2])
            true_range = max(tr1, tr2, tr3)

            self._atr_values.append(true_range)

            if len(self._atr_values) >= self.renko_config.atr_period:
                # Calculate ATR as simple moving average
                atr = sum(list(self._atr_values)[-self.renko_config.atr_period:]) / self.renko_config.atr_period
                # Set brick size as percentage of ATR
                self._brick_size = atr * 0.5  # 50% of ATR as brick size

    def _update_renko_chart(self, price: float, volume: float, timestamp: datetime):
        """Update Renko chart with new price data"""
        if self._last_price is None:
            # Initialize first brick
            self._last_price = price
            self._current_brick = RenkoBrick(
                direction=RenkoDirection.NEUTRAL,
                open_price=price,
                close_price=price,
                high_price=price,
                low_price=price,
                timestamp=timestamp,
                volume=volume
            )
            return

        # Calculate price movement from last brick close
        last_brick_close = self._current_brick.close_price
        price_movement = price - last_brick_close

        # Check if price movement exceeds brick size
        if abs(price_movement) >= self._brick_size:
            # Determine brick direction
            if price_movement > 0:
                new_direction = RenkoDirection.UP
                brick_open = last_brick_close
                brick_close = last_brick_close + self._brick_size
            else:
                new_direction = RenkoDirection.DOWN
                brick_open = last_brick_close
                brick_close = last_brick_close - self._brick_size

            # Create new brick
            new_brick = RenkoBrick(
                direction=new_direction,
                open_price=brick_open,
                close_price=brick_close,
                high_price=max(brick_open, brick_close),
                low_price=min(brick_open, brick_close),
                timestamp=timestamp,
                volume=volume
            )

            # Add to bricks history
            self._bricks.append(new_brick)
            self._current_brick = new_brick

            # Update last price
            self._last_price = price

            # Analyze brick characteristics
            self._analyze_brick_characteristics()

    def _analyze_brick_characteristics(self):
        """Analyze Renko brick characteristics"""
        if not self.is_ready:
            return

        # Determine trend direction from recent bricks
        recent_bricks = list(self._bricks)[-5:]  # Last 5 bricks
        up_bricks = sum(1 for b in recent_bricks if b.direction == RenkoDirection.UP)
        down_bricks = sum(1 for b in recent_bricks if b.direction == RenkoDirection.DOWN)

        if up_bricks > down_bricks:
            self._trend_direction = RenkoDirection.UP
        elif down_bricks > up_bricks:
            self._trend_direction = RenkoDirection.DOWN
        else:
            self._trend_direction = RenkoDirection.NEUTRAL

        # Calculate trend strength
        total_bricks = len(recent_bricks)
        dominant_bricks = max(up_bricks, down_bricks)
        self._trend_strength = dominant_bricks / total_bricks if total_bricks > 0 else 0.0

        # Calculate momentum alignment
        if len(self._bricks) >= 3:
            # Check if recent bricks are in the same direction
            last_three = list(self._bricks)[-3:]
            directions = [b.direction for b in last_three]

            if all(d == RenkoDirection.UP for d in directions):
                self._momentum_alignment = 1.0
            elif all(d == RenkoDirection.DOWN for d in directions):
                self._momentum_alignment = 1.0
            elif directions[0] != directions[-1] and directions[1] != directions[-1]:
                # Mixed directions indicate potential reversal
                self._momentum_alignment = 0.3
            else:
                self._momentum_alignment = 0.7

        # Track signals
        self._track_brick_signals()

        # Update market structure
        self._update_market_structure()

        # Calculate institutional renko analysis
        self._calculate_institutional_renko()

    def _track_brick_signals(self):
        """Track Renko brick signals"""
        if not self.is_ready or len(self._bricks) < 2:
            return

        # Track direction changes
        prev_brick = self._bricks[-2]
        current_brick = self._bricks[-1]

        if prev_brick.direction != current_brick.direction and prev_brick.direction != RenkoDirection.NEUTRAL:
            self._direction_change_signals += 1

        # Track brick sequences (consecutive bricks in same direction)
        if len(self._bricks) >= 3:
            last_three = list(self._bricks)[-3:]
            if all(b.direction == RenkoDirection.UP for b in last_three):
                self._brick_sequence_signals += 1
            elif all(b.direction == RenkoDirection.DOWN for b in last_three):
                self._brick_sequence_signals += 1

        # Track breakouts (large price movements)
        if abs(current_brick.close_price - current_brick.open_price) > self._brick_size * 1.5:
            self._breakout_signals += 1

        # Calculate overall signal strength
        signal_components = [
            self._direction_change_signals > 0,
            self._brick_sequence_signals > 0,
            self._breakout_signals > 0,
            self._trend_strength > 0.6,
            self._momentum_alignment > 0.7
        ]
        self._signal_strength = sum(signal_components) / len(signal_components)

    def _update_market_structure(self):
        """Update market structure analysis"""
        if not self.is_ready:
            return

        current_brick = self._bricks[-1]

        # Brick boundaries act as support/resistance
        if current_brick.direction == RenkoDirection.UP:
            # Up brick close acts as support
            self._support_levels.append(current_brick.close_price)
            if len(self._support_levels) > 10:
                self._support_levels.pop(0)
        elif current_brick.direction == RenkoDirection.DOWN:
            # Down brick close acts as resistance
            self._resistance_levels.append(current_brick.close_price)
            if len(self._resistance_levels) > 10:
                self._resistance_levels.pop(0)

        # Count brick touches (price revisiting brick levels)
        if len(self._bricks) >= 2:
            prev_brick = self._bricks[-2]
            if abs(current_brick.close_price - prev_brick.close_price) < self._brick_size * 0.1:
                self._brick_touches += 1

    def _calculate_institutional_renko(self):
        """Calculate institutional renko analysis"""
        if not self.is_ready:
            return

        # Institutional traders use Renko for clear trend identification
        base_renko = 0.0

        if self._trend_strength > 0.8 and self._momentum_alignment > 0.9:
            base_renko = 0.9  # Very strong, consistent trend
        elif self._trend_strength > 0.7 and self._momentum_alignment > 0.7:
            base_renko = 0.7  # Strong trend with good momentum
        elif self._trend_strength > 0.6:
            base_renko = 0.5  # Moderate trend
        elif self._brick_touches > 5:
            base_renko = 0.3  # Consolidation phase

        self._institutional_renko = base_renko

        # Smart money trend considers all renko components
        smart_money_score = (
            self._trend_strength * 0.3 +
            self._momentum_alignment * 0.3 +
            self._signal_strength * 0.2 +
            self._institutional_renko * 0.2
        )
        self._smart_money_trend = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade Renko analysis"""
        if not self.is_ready:
            return IndicatorSignal(
                value_raw=0.0,
                signal_type=SignalType.NEUTRAL,
                composite_confidence=0.0,
                confidence_components={},
                suggested_sl=0.0,
                suggested_tp=0.0,
                metadata={"status": "not_ready"}
            )

        # Use current brick close as primary raw value
        raw_value = self._current_brick.close_price if self._current_brick else 0.0

        # Determine signal type based on Renko analysis
        signal_type = self._determine_renko_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'trend_strength': self._trend_strength,
            'momentum_alignment': self._momentum_alignment,
            'signal_strength': self._signal_strength,
            'brick_size': self._brick_size,
            'institutional_renko': self._institutional_renko,
            'smart_money_trend': self._smart_money_trend
        }

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._suggested_sl,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "Renko_Chart",
                "current_brick": {
                    "direction": self._current_brick.direction.value if self._current_brick else "neutral",
                    "open": self._current_brick.open_price if self._current_brick else 0.0,
                    "close": self._current_brick.close_price if self._current_brick else 0.0,
                    "high": self._current_brick.high_price if self._current_brick else 0.0,
                    "low": self._current_brick.low_price if self._current_brick else 0.0,
                    "volume": self._current_brick.volume if self._current_brick else 0.0
                },
                "trend_direction": self._trend_direction.value,
                "trend_strength": self._trend_strength,
                "momentum_alignment": self._momentum_alignment,
                "direction_change_signals": self._direction_change_signals,
                "brick_sequence_signals": self._brick_sequence_signals,
                "breakout_signals": self._breakout_signals,
                "signal_strength": self._signal_strength,
                "brick_touches": self._brick_touches,
                "support_levels_count": len(self._support_levels),
                "resistance_levels_count": len(self._resistance_levels),
                "total_bricks": len(self._bricks),
                "brick_size": self._brick_size,
                "brick_size_type": self.renko_config.brick_size_type,
                "institutional_renko": self._institutional_renko,
                "smart_money_trend": self._smart_money_trend,
                "is_ready": self.is_ready
            }
        )

    def _determine_renko_signal(self) -> SignalType:
        """Determine signal type based on Renko analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # Strong bullish signals
        if (self._trend_direction == RenkoDirection.UP and
            self._momentum_alignment > 0.8 and
            self._trend_strength > 0.7 and
            self._signal_strength > 0.6):
            return SignalType.STRONG_BULLISH

        # Strong bearish signals
        elif (self._trend_direction == RenkoDirection.DOWN and
              self._momentum_alignment > 0.8 and
              self._trend_strength > 0.7 and
              self._signal_strength > 0.6):
            return SignalType.STRONG_BEARISH

        # Moderate bullish signals
        elif self._trend_direction == RenkoDirection.UP:
            return SignalType.BULLISH

        # Moderate bearish signals
        elif self._trend_direction == RenkoDirection.DOWN:
            return SignalType.BEARISH

        # Direction change signals (potential reversals)
        elif self._direction_change_signals > 0 and self._trend_strength < 0.4:
            return SignalType.NEUTRAL  # Could indicate reversal setup

        return SignalType.NEUTRAL

    @property
    def current_brick(self) -> Optional[RenkoBrick]:
        """Get the current Renko brick"""
        return self._current_brick

    @property
    def bricks(self) -> List[RenkoBrick]:
        """Get the list of Renko bricks"""
        return list(self._bricks)

    @property
    def trend_direction(self) -> RenkoDirection:
        """Get the current trend direction"""
        return self._trend_direction

    @property
    def trend_strength(self) -> float:
        """Get the current trend strength (0-1)"""
        return self._trend_strength

    @property
    def momentum_alignment(self) -> float:
        """Get the momentum alignment score (0-1)"""
        return self._momentum_alignment

    @property
    def signal_strength(self) -> float:
        """Get the overall signal strength (0-1)"""
        return self._signal_strength

    @property
    def brick_size(self) -> float:
        """Get the current brick size"""
        return self._brick_size

    @property
    def direction_change_signals(self) -> int:
        """Get the count of direction change signals"""
        return self._direction_change_signals

    @property
    def brick_sequence_signals(self) -> int:
        """Get the count of brick sequence signals"""
        return self._brick_sequence_signals

    @property
    def breakout_signals(self) -> int:
        """Get the count of breakout signals"""
        return self._breakout_signals

    @property
    def brick_touches(self) -> int:
        """Get the count of brick touches"""
        return self._brick_touches

    @property
    def support_levels(self) -> list:
        """Get the list of support levels"""
        return self._support_levels.copy()

    @property
    def resistance_levels(self) -> list:
        """Get the list of resistance levels"""
        return self._resistance_levels.copy()

    @property
    def institutional_renko(self) -> float:
        """Get the institutional renko score (0-1)"""
        return self._institutional_renko

    @property
    def smart_money_trend(self) -> float:
        """Get the smart money trend score (0-1)"""
        return self._smart_money_trend

    def is_uptrend(self) -> bool:
        """Check if current trend is up"""
        return self._trend_direction == RenkoDirection.UP

    def is_downtrend(self) -> bool:
        """Check if current trend is down"""
        return self._trend_direction == RenkoDirection.DOWN

    def is_strong_trend(self) -> float:
        """Check if trend is strong"""
        return self._trend_strength > 0.7

    def is_momentum_aligned(self) -> bool:
        """Check if momentum is aligned"""
        return self._momentum_alignment > 0.8

    def is_breakout_detected(self) -> bool:
        """Check if breakout is detected"""
        return self._breakout_signals > 0

    def is_institutional_setup(self) -> bool:
        """Check if setup is institutional-grade"""
        return self._institutional_renko > 0.8

    def get_renko_chart_info(self) -> Dict[str, Any]:
        """Get comprehensive Renko chart information"""
        return {
            "current_brick": {
                "direction": self._current_brick.direction.value if self._current_brick else "neutral",
                "open": self._current_brick.open_price if self._current_brick else 0.0,
                "close": self._current_brick.close_price if self._current_brick else 0.0,
                "high": self._current_brick.high_price if self._current_brick else 0.0,
                "low": self._current_brick.low_price if self._current_brick else 0.0,
                "volume": self._current_brick.volume if self._current_brick else 0.0,
                "timestamp": self._current_brick.timestamp.isoformat() if self._current_brick else None
            },
            "trend_analysis": {
                "direction": self._trend_direction.value,
                "strength": self._trend_strength,
                "momentum_alignment": self._momentum_alignment
            },
            "signal_analysis": {
                "strength": self._signal_strength,
                "direction_change_signals": self._direction_change_signals,
                "brick_sequence_signals": self._brick_sequence_signals,
                "breakout_signals": self._breakout_signals
            },
            "market_structure": {
                "brick_touches": self._brick_touches,
                "support_levels": len(self._support_levels),
                "resistance_levels": len(self._resistance_levels),
                "total_bricks": len(self._bricks)
            },
            "institutional_analysis": {
                "renko": self._institutional_renko,
                "smart_money_trend": self._smart_money_trend
            },
            "configuration": {
                "brick_size": self._brick_size,
                "brick_size_type": self.renko_config.brick_size_type,
                "atr_period": self.renko_config.atr_period,
                "max_bricks": self.renko_config.max_bricks,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._bricks.clear()
        self._current_brick = None
        self._pending_price = None
        self._last_price = None
        self._brick_size = self.renko_config.brick_size
        self._atr_values.clear()
        self._highs.clear()
        self._lows.clear()
        self._closes.clear()
        self._trend_direction = RenkoDirection.NEUTRAL
        self._trend_strength = 0.0
        self._momentum_alignment = 0.0
        self._direction_change_signals = 0
        self._brick_sequence_signals = 0
        self._breakout_signals = 0
        self._signal_strength = 0.0
        self._support_levels.clear()
        self._resistance_levels.clear()
        self._brick_touches = 0
        self._institutional_renko = 0.0
        self._smart_money_trend = 0.0