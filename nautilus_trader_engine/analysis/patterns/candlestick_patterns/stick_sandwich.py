"""
Stick Sandwich Candlestick Pattern Implementation
===============================================

Institutional-grade implementation of the Stick Sandwich pattern with 5-pillar architecture.

Pattern Description:
- Three-candle reversal pattern
- First candle: Bearish (down)
- Second candle: Bullish (up) with same close as first candle
- Third candle: Bearish (down) with same close as first/second candles
- Rare but reliable reversal signal
- Indicates strong support/resistance level

Reliability Factor: 0.71
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
from ...core.augmented_indicator import AugmentedIndicator


class PatternStrength(Enum):
    WEAK = 0.3
    MODERATE = 0.6
    STRONG = 0.8
    VERY_STRONG = 0.9


@dataclass
class StickSandwichSignal:
    """Enhanced signal object for Stick Sandwich pattern"""
    pattern_name: str = "STICK_SANDWICH"
    detected: bool = False
    strength: PatternStrength = PatternStrength.WEAK
    direction: str = "NEUTRAL"  # BULLISH, BEARISH, NEUTRAL
    confidence_score: float = 0.0
    volume_confirmation: float = 0.0
    smart_money_score: float = 0.0
    risk_reward_ratio: float = 0.0
    stop_loss_price: float = 0.0
    take_profit_price: float = 0.0
    pattern_range_high: float = 0.0
    pattern_range_low: float = 0.0
    breakout_level: float = 0.0

    # 5-Pillar Architecture Components
    volume_components: Dict[str, float] = None
    regime_components: Dict[str, float] = None
    timeframe_components: Dict[str, float] = None
    microstructure_components: Dict[str, float] = None
    risk_components: Dict[str, float] = None


class AugmentedStickSandwich(AugmentedIndicator):
    """
    Institutional-grade Stick Sandwich pattern detector with 5-pillar architecture.

    The Stick Sandwich is a rare but reliable three-candle reversal pattern that
    indicates a strong support or resistance level has been established.
    """

    def __init__(self,
                 volume_ma_period: int = 20,
                 atr_period: int = 14,
                 trend_ema_period: int = 200,
                 min_pattern_strength: float = 0.6,
                 volume_threshold_multiplier: float = 1.5,
                 smart_money_threshold: float = 2.0):
        """
        Initialize Stick Sandwich detector.

        Args:
            volume_ma_period: Period for volume moving average
            atr_period: Period for ATR calculation
            trend_ema_period: Period for trend EMA
            min_pattern_strength: Minimum pattern strength threshold
            volume_threshold_multiplier: Volume confirmation multiplier
            smart_money_threshold: Smart money detection threshold
        """
        super().__init__(name="STICK_SANDWICH")

        # Core parameters
        self.volume_ma_period = volume_ma_period
        self.atr_period = atr_period
        self.trend_ema_period = trend_ema_period
        self.min_pattern_strength = min_pattern_strength
        self.volume_threshold_multiplier = volume_threshold_multiplier
        self.smart_money_threshold = smart_money_threshold

        # Internal indicators for 5-pillar analysis
        self.volume_ma = None
        self.atr = None
        self.trend_ema = None

        # Pattern tracking
        self.candles_buffer = []
        self.max_buffer_size = 5

        # Initialize signal object
        self._signal = StickSandwichSignal()

    def update(self, open_price: float, high_price: float, low_price: float,
               close_price: float, volume: float) -> StickSandwichSignal:
        """
        Update pattern detector with new price/volume data.

        Args:
            open_price: Opening price
            high_price: High price
            low_price: Low price
            close_price: Closing price
            volume: Trading volume

        Returns:
            StickSandwichSignal: Enhanced pattern signal
        """
        # Update internal indicators
        self._update_internal_indicators(open_price, high_price, low_price, close_price, volume)

        # Add current candle to buffer
        current_candle = {
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        }

        self.candles_buffer.append(current_candle)
        if len(self.candles_buffer) > self.max_buffer_size:
            self.candles_buffer.pop(0)

        # Reset signal
        self._signal = StickSandwichSignal()

        # Need at least 3 candles for pattern detection
        if len(self.candles_buffer) >= 3:
            self._detect_pattern()

        return self._signal

    def _update_internal_indicators(self, open_price: float, high_price: float,
                                   low_price: float, close_price: float, volume: float):
        """Update internal indicators for 5-pillar analysis"""
        # Initialize indicators if needed
        if self.volume_ma is None:
            # Simple volume MA for now - would be replaced with proper VWMA
            self.volume_ma = []
            self.atr = []
            self.trend_ema = []

        # Update volume MA (simplified)
        self.volume_ma.append(volume)
        if len(self.volume_ma) > self.volume_ma_period:
            self.volume_ma.pop(0)

        # Update ATR (simplified)
        if len(self.atr) > 0:
            tr = max(high_price - low_price,
                    abs(high_price - close_price),
                    abs(low_price - close_price))
            atr_value = (self.atr[-1] * (self.atr_period - 1) + tr) / self.atr_period
        else:
            tr = high_price - low_price
            atr_value = tr

        self.atr.append(atr_value)
        if len(self.atr) > self.atr_period:
            self.atr.pop(0)

        # Update trend EMA (simplified)
        if len(self.trend_ema) > 0:
            ema_value = (close_price * 2 / (self.trend_ema_period + 1) +
                        self.trend_ema[-1] * (self.trend_ema_period - 1) / (self.trend_ema_period + 1))
        else:
            ema_value = close_price

        self.trend_ema.append(ema_value)
        if len(self.trend_ema) > self.trend_ema_period:
            self.trend_ema.pop(0)

    def _detect_pattern(self) -> None:
        """Detect Stick Sandwich pattern in the candle buffer"""
        if len(self.candles_buffer) < 3:
            return

        # Get last 3 candles
        c3, c2, c1 = self.candles_buffer[-3:]

        # Pattern recognition logic
        pattern_detected = self._check_stick_sandwich_criteria(c1, c2, c3)

        if pattern_detected:
            self._signal.detected = True
            self._analyze_pattern_strength(c1, c2, c3)
            self._calculate_confidence_score()
            self._determine_pattern_direction(c1, c2, c3)
            self._calculate_risk_parameters(c1, c2, c3)

    def _check_stick_sandwich_criteria(self, c1: Dict, c2: Dict, c3: Dict) -> bool:
        """
        Check if candles meet Stick Sandwich criteria.

        Pattern Rules:
        1. First candle (c1): Bearish (close < open)
        2. Second candle (c2): Bullish (close > open)
        3. Third candle (c3): Bearish (close < open)
        4. c1.close ≈ c2.close ≈ c3.close (same closing levels)
        5. c2 is smaller than c1 and c3
        """
        try:
            # Basic direction checks
            c1_bearish = c1['close'] < c1['open']
            c2_bullish = c2['close'] > c2['open']
            c3_bearish = c3['close'] < c3['open']

            if not (c1_bearish and c2_bullish and c3_bearish):
                return False

            # Closing price alignment (within 0.1% tolerance)
            close_tolerance = 0.001
            c1_c2_diff = abs(c1['close'] - c2['close']) / c1['close']
            c2_c3_diff = abs(c2['close'] - c3['close']) / c2['close']
            c1_c3_diff = abs(c1['close'] - c3['close']) / c1['close']

            closes_aligned = (c1_c2_diff <= close_tolerance and
                            c2_c3_diff <= close_tolerance and
                            c1_c3_diff <= close_tolerance)

            if not closes_aligned:
                return False

            # Size comparison - c2 should be smaller than c1 and c3
            c1_range = c1['high'] - c1['low']
            c2_range = c2['high'] - c2['low']
            c3_range = c3['high'] - c3['low']

            c2_smaller = c2_range < c1_range * 0.7 and c2_range < c3_range * 0.7

            return c2_smaller

        except (KeyError, ZeroDivisionError):
            return False

    def _analyze_pattern_strength(self, c1: Dict, c2: Dict, c3: Dict) -> None:
        """Analyze the strength of the detected pattern"""
        # Calculate pattern metrics
        c1_range = c1['high'] - c1['low']
        c2_range = c2['high'] - c2['low']
        c3_range = c3['high'] - c3['low']

        # Size ratio (smaller middle candle = stronger pattern)
        size_ratio = c2_range / ((c1_range + c3_range) / 2)
        size_score = max(0, 1 - size_ratio)  # Higher score for smaller middle candle

        # Shadow analysis
        c1_shadow_ratio = (c1['high'] - c1['low']) / abs(c1['close'] - c1['open']) if c1['close'] != c1['open'] else 1
        c3_shadow_ratio = (c3['high'] - c3['low']) / abs(c3['close'] - c3['open']) if c3['close'] != c3['open'] else 1

        shadow_score = min(1.0, (c1_shadow_ratio + c3_shadow_ratio) / 4)  # Prefer longer shadows

        # Combine scores
        strength_score = (size_score * 0.6 + shadow_score * 0.4)

        # Determine pattern strength
        if strength_score >= 0.8:
            self._signal.strength = PatternStrength.VERY_STRONG
        elif strength_score >= 0.6:
            self._signal.strength = PatternStrength.STRONG
        elif strength_score >= 0.4:
            self._signal.strength = PatternStrength.MODERATE
        else:
            self._signal.strength = PatternStrength.WEAK

    def _calculate_confidence_score(self) -> None:
        """Calculate overall confidence score using 5-pillar analysis"""
        # Pillar 1: Volume Confirmation
        volume_score = self._calculate_volume_score()
        self._signal.volume_components = {'confirmation_score': volume_score}

        # Pillar 2: Market Regime
        regime_score = self._calculate_regime_score()
        self._signal.regime_components = {'trend_alignment': regime_score}

        # Pillar 3: Multi-Timeframe (simplified - would need higher TF data)
        timeframe_score = 0.7  # Placeholder
        self._signal.timeframe_components = {'convergence_score': timeframe_score}

        # Pillar 4: Smart Money/Microstructure
        smart_money_score = self._calculate_smart_money_score()
        self._signal.microstructure_components = {'institutional_bias': smart_money_score}

        # Pillar 5: Risk Management
        risk_score = self._calculate_risk_score()
        self._signal.risk_components = {'reward_risk_ratio': risk_score}

        # Weighted confidence score
        weights = {
            'volume': 0.25,
            'regime': 0.20,
            'timeframe': 0.20,
            'smart_money': 0.20,
            'risk': 0.15
        }

        confidence = (
            volume_score * weights['volume'] +
            regime_score * weights['regime'] +
            timeframe_score * weights['timeframe'] +
            smart_money_score * weights['smart_money'] +
            risk_score * weights['risk']
        )

        self._signal.confidence_score = min(1.0, max(0.0, confidence))

    def _calculate_volume_score(self) -> float:
        """Calculate volume confirmation score"""
        if len(self.volume_ma) < 3:
            return 0.5

        avg_volume = np.mean(self.volume_ma[-3:])
        current_volume = self.candles_buffer[-1]['volume']

        if avg_volume > 0:
            volume_ratio = current_volume / avg_volume
            # Score based on volume threshold
            if volume_ratio >= self.volume_threshold_multiplier:
                return min(1.0, volume_ratio / (self.volume_threshold_multiplier * 2))
            else:
                return max(0.0, volume_ratio / self.volume_threshold_multiplier)

        return 0.5

    def _calculate_regime_score(self) -> float:
        """Calculate market regime alignment score"""
        if len(self.trend_ema) < 2:
            return 0.5

        current_price = self.candles_buffer[-1]['close']
        trend_price = self.trend_ema[-1]

        # Trend alignment (higher score if pattern aligns with trend)
        if current_price > trend_price:
            return 0.7  # Bullish pattern in uptrend
        else:
            return 0.4  # Bullish pattern in downtrend

    def _calculate_smart_money_score(self) -> float:
        """Calculate smart money involvement score"""
        # Simplified smart money detection
        # In practice, this would analyze order book data
        current_volume = self.candles_buffer[-1]['volume']

        if len(self.volume_ma) > 0:
            avg_volume = np.mean(self.volume_ma)
            if current_volume > avg_volume * self.smart_money_threshold:
                return 0.8  # High volume suggests institutional activity
            elif current_volume > avg_volume * 1.5:
                return 0.6  # Moderate institutional activity
            else:
                return 0.3  # Retail-dominated activity

        return 0.5

    def _calculate_risk_score(self) -> float:
        """Calculate risk-adjusted score"""
        if len(self.atr) > 0:
            current_atr = self.atr[-1]
            pattern_range = self._signal.pattern_range_high - self._signal.pattern_range_low

            if pattern_range > 0 and current_atr > 0:
                # Risk-reward ratio based on pattern size vs volatility
                rr_ratio = pattern_range / current_atr
                return min(1.0, rr_ratio / 3.0)  # Scale to 0-1 range

        return 0.5

    def _determine_pattern_direction(self, c1: Dict, c2: Dict, c3: Dict) -> None:
        """Determine if pattern is bullish or bearish"""
        # Stick Sandwich is typically a bullish reversal pattern
        # appearing after a downtrend
        self._signal.direction = "BULLISH"

    def _calculate_risk_parameters(self, c1: Dict, c2: Dict, c3: Dict) -> None:
        """Calculate stop loss and take profit levels"""
        # Pattern range
        highs = [c1['high'], c2['high'], c3['high']]
        lows = [c1['low'], c2['low'], c3['low']]

        self._signal.pattern_range_high = max(highs)
        self._signal.pattern_range_low = min(lows)

        # Breakout level (the closing level that all three candles share)
        self._signal.breakout_level = c3['close']

        # Stop loss below the pattern low
        self._signal.stop_loss_price = self._signal.pattern_range_low * 0.995  # 0.5% buffer

        # Take profit based on pattern height and risk-reward ratio
        pattern_height = self._signal.pattern_range_high - self._signal.pattern_range_low
        risk = abs(self._signal.breakout_level - self._signal.stop_loss_price)

        if risk > 0:
            reward = risk * 2.5  # 2.5:1 risk-reward ratio
            self._signal.take_profit_price = self._signal.breakout_level + reward
            self._signal.risk_reward_ratio = 2.5
        else:
            self._signal.take_profit_price = self._signal.breakout_level * 1.03  # 3% target
            self._signal.risk_reward_ratio = 1.5

    @property
    def signal(self) -> StickSandwichSignal:
        """Get current pattern signal"""
        return self._signal

    def reset(self) -> None:
        """Reset pattern detector state"""
        self.candles_buffer.clear()
        self.volume_ma.clear()
        self.atr.clear()
        self.trend_ema.clear()
        self._signal = StickSandwichSignal()


# Factory function for easy instantiation
def create_stick_sandwich_detector(**kwargs) -> AugmentedStickSandwich:
    """Create and return a configured Stick Sandwich detector"""
    return AugmentedStickSandwich(**kwargs)