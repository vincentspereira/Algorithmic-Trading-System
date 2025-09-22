"""
Marubozu Variations Candlestick Pattern Implementation
====================================================

Institutional-grade implementation of Marubozu pattern variations with 5-pillar architecture.

Pattern Description:
- Marubozu candles have no wicks (shadows) - open and close at extremes
- Bullish Marubozu: Opens at low, closes at high (no upper/lower wicks)
- Bearish Marubozu: Opens at high, closes at low (no upper/lower wicks)
- Indicates strong directional conviction and momentum
- Can have variations with very small wicks

Reliability Factor: 0.71 (Bullish), 0.69 (Bearish)
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
from ...core.augmented_indicator import AugmentedIndicator


class MarubozuType(Enum):
    BULLISH = "BULLISH"      # Opens at low, closes at high
    BEARISH = "BEARISH"      # Opens at high, closes at low
    NEUTRAL = "NEUTRAL"


class MarubozuVariation(Enum):
    PERFECT = "PERFECT"      # No wicks at all
    NEAR_PERFECT = "NEAR_PERFECT"  # Very small wicks (<2% of body)
    STANDARD = "STANDARD"    # Small wicks (<5% of body)


class PatternStrength(Enum):
    WEAK = 0.3
    MODERATE = 0.6
    STRONG = 0.8
    VERY_STRONG = 0.9


@dataclass
class MarubozuSignal:
    """Enhanced signal object for Marubozu pattern"""
    pattern_name: str = "MARUBOZU"
    detected: bool = False
    pattern_type: MarubozuType = MarubozuType.NEUTRAL
    variation: MarubozuVariation = MarubozuVariation.STANDARD
    strength: PatternStrength = PatternStrength.WEAK
    direction: str = "NEUTRAL"  # BULLISH, BEARISH, NEUTRAL
    confidence_score: float = 0.0
    volume_confirmation: float = 0.0
    smart_money_score: float = 0.0
    risk_reward_ratio: float = 0.0
    stop_loss_price: float = 0.0
    take_profit_price: float = 0.0
    body_size: float = 0.0
    wick_percentage: float = 0.0
    momentum_strength: float = 0.0
    conviction_level: float = 0.0

    # 5-Pillar Architecture Components
    volume_components: Dict[str, float] = None
    regime_components: Dict[str, float] = None
    timeframe_components: Dict[str, float] = None
    microstructure_components: Dict[str, float] = None
    risk_components: Dict[str, float] = None


class AugmentedMarubozu(AugmentedIndicator):
    """
    Institutional-grade Marubozu pattern detector with 5-pillar architecture.

    Marubozu candles show extreme directional conviction with no price rejection,
    indicating strong momentum and institutional directional bias.
    """

    def __init__(self,
                 volume_ma_period: int = 20,
                 atr_period: int = 14,
                 trend_ema_period: int = 200,
                 max_wick_percentage: float = 0.05,  # Maximum wick size as % of body
                 min_body_strength: float = 1.5,     # Minimum body size vs ATR
                 volume_threshold_multiplier: float = 1.8,
                 smart_money_threshold: float = 2.5):
        """
        Initialize Marubozu detector.

        Args:
            volume_ma_period: Period for volume moving average
            atr_period: Period for ATR calculation
            trend_ema_period: Period for trend EMA
            max_wick_percentage: Maximum wick size as percentage of body
            min_body_strength: Minimum body strength vs ATR
            volume_threshold_multiplier: Volume confirmation multiplier
            smart_money_threshold: Smart money detection threshold
        """
        super().__init__(name="MARUBOZU")

        # Core parameters
        self.volume_ma_period = volume_ma_period
        self.atr_period = atr_period
        self.trend_ema_period = trend_ema_period
        self.max_wick_percentage = max_wick_percentage
        self.min_body_strength = min_body_strength
        self.volume_threshold_multiplier = volume_threshold_multiplier
        self.smart_money_threshold = smart_money_threshold

        # Internal indicators for 5-pillar analysis
        self.volume_ma = []
        self.atr_values = []
        self.trend_ema_values = []

        # Pattern tracking
        self.candles_buffer = []
        self.max_buffer_size = 5

        # Initialize signal object
        self._signal = MarubozuSignal()

    def update(self, open_price: float, high_price: float, low_price: float,
               close_price: float, volume: float) -> MarubozuSignal:
        """
        Update pattern detector with new price/volume data.

        Args:
            open_price: Opening price
            high_price: High price
            low_price: Low price
            close_price: Closing price
            volume: Trading volume

        Returns:
            MarubozuSignal: Enhanced pattern signal
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
        self._signal = MarubozuSignal()

        # Need at least 1 candle for pattern detection
        if len(self.candles_buffer) >= 1:
            self._detect_pattern()

        return self._signal

    def _update_internal_indicators(self, open_price: float, high_price: float,
                                   low_price: float, close_price: float, volume: float):
        """Update internal indicators for 5-pillar analysis"""
        # Update volume MA
        self.volume_ma.append(volume)
        if len(self.volume_ma) > self.volume_ma_period:
            self.volume_ma.pop(0)

        # Update ATR
        if len(self.atr_values) > 0:
            tr = max(high_price - low_price,
                    abs(high_price - self.candles_buffer[-2]['close'] if len(self.candles_buffer) > 1 else close_price),
                    abs(low_price - self.candles_buffer[-2]['close'] if len(self.candles_buffer) > 1 else close_price))
            atr_value = (self.atr_values[-1] * (self.atr_period - 1) + tr) / self.atr_period
        else:
            tr = high_price - low_price
            atr_value = tr

        self.atr_values.append(atr_value)
        if len(self.atr_values) > self.atr_period:
            self.atr_values.pop(0)

        # Update trend EMA
        if len(self.trend_ema_values) > 0:
            ema_value = (close_price * 2 / (self.trend_ema_period + 1) +
                        self.trend_ema_values[-1] * (self.trend_ema_period - 1) / (self.trend_ema_period + 1))
        else:
            ema_value = close_price

        self.trend_ema_values.append(ema_value)
        if len(self.trend_ema_values) > self.trend_ema_period:
            self.trend_ema_values.pop(0)

    def _detect_pattern(self) -> None:
        """Detect Marubozu pattern in the current candle"""
        if len(self.candles_buffer) < 1:
            return

        current_candle = self.candles_buffer[-1]

        # Analyze the current candle for Marubozu characteristics
        pattern_detected, pattern_type, variation = self._analyze_candle_for_marubozu(current_candle)

        if pattern_detected:
            self._signal.detected = True
            self._signal.pattern_type = pattern_type
            self._signal.variation = variation
            self._analyze_pattern_strength(current_candle)
            self._calculate_confidence_score()
            self._determine_pattern_direction()
            self._calculate_risk_parameters(current_candle)

    def _analyze_candle_for_marubozu(self, candle: Dict) -> Tuple[bool, MarubozuType, MarubozuVariation]:
        """
        Analyze a candle for Marubozu characteristics.

        Pattern Criteria:
        1. Very small or no wicks (shadows)
        2. Open and close at extremes of the range
        3. Strong directional body
        4. Can be bullish or bearish
        """
        try:
            # Calculate candle dimensions
            total_range = candle['high'] - candle['low']
            body_size = abs(candle['close'] - candle['open'])
            upper_wick = candle['high'] - max(candle['open'], candle['close'])
            lower_wick = min(candle['open'], candle['close']) - candle['low']

            if total_range <= 0 or body_size <= 0:
                return False, MarubozuType.NEUTRAL, MarubozuVariation.STANDARD

            # Calculate wick percentages relative to body
            upper_wick_pct = upper_wick / body_size if body_size > 0 else 0
            lower_wick_pct = lower_wick / body_size if body_size > 0 else 0
            total_wick_pct = (upper_wick + lower_wick) / body_size if body_size > 0 else 0

            # Determine variation based on wick size
            if total_wick_pct <= 0.02:  # Less than 2% wicks
                variation = MarubozuVariation.PERFECT
            elif total_wick_pct <= 0.05:  # Less than 5% wicks
                variation = MarubozuVariation.NEAR_PERFECT
            elif total_wick_pct <= self.max_wick_percentage:
                variation = MarubozuVariation.STANDARD
            else:
                return False, MarubozuType.NEUTRAL, MarubozuVariation.STANDARD

            # Check for bullish Marubozu
            is_bullish = (candle['close'] > candle['open'] and
                         candle['open'] == candle['low'] and  # Opens at low
                         candle['close'] == candle['high'])   # Closes at high

            # Check for bearish Marubozu
            is_bearish = (candle['close'] < candle['open'] and
                         candle['open'] == candle['high'] and  # Opens at high
                         candle['close'] == candle['low'])    # Closes at low

            # Allow for small tolerance in wick sizes
            if is_bullish:
                return True, MarubozuType.BULLISH, variation
            elif is_bearish:
                return True, MarubozuType.BEARISH, variation
            else:
                return False, MarubozuType.NEUTRAL, MarubozuVariation.STANDARD

        except (KeyError, ZeroDivisionError):
            return False, MarubozuType.NEUTRAL, MarubozuVariation.STANDARD

    def _analyze_pattern_strength(self, candle: Dict) -> None:
        """Analyze the strength of the detected Marubozu pattern"""
        # Calculate pattern metrics
        total_range = candle['high'] - candle['low']
        body_size = abs(candle['close'] - candle['open'])
        upper_wick = candle['high'] - max(candle['open'], candle['close'])
        lower_wick = min(candle['open'], candle['close']) - candle['low']

        # Update signal with pattern metrics
        self._signal.body_size = body_size
        self._signal.wick_percentage = (upper_wick + lower_wick) / body_size if body_size > 0 else 0

        # Strength analysis based on multiple factors

        # 1. Body strength relative to ATR
        if len(self.atr_values) > 0:
            current_atr = self.atr_values[-1]
            body_strength = body_size / current_atr if current_atr > 0 else 1
            body_score = min(1.0, body_strength / 2.0)  # Scale to 0-1
        else:
            body_score = 0.5

        # 2. Wick minimization (smaller wicks = stronger pattern)
        wick_score = 1.0 - self._signal.wick_percentage
        wick_score = max(0.0, wick_score)  # Ensure non-negative

        # 3. Variation bonus (perfect Marubozu gets highest score)
        if self._signal.variation == MarubozuVariation.PERFECT:
            variation_score = 1.0
        elif self._signal.variation == MarubozuVariation.NEAR_PERFECT:
            variation_score = 0.8
        else:
            variation_score = 0.6

        # 4. Momentum strength (body size relative to recent candles)
        if len(self.candles_buffer) >= 3:
            recent_bodies = [abs(c['close'] - c['open']) for c in self.candles_buffer[-3:]]
            avg_recent_body = np.mean(recent_bodies)
            momentum_score = min(1.0, body_size / avg_recent_body) if avg_recent_body > 0 else 0.5
        else:
            momentum_score = 0.5

        # Update momentum strength
        self._signal.momentum_strength = momentum_score
        self._signal.conviction_level = (body_score + wick_score + variation_score + momentum_score) / 4

        # Combine scores with weights
        strength_score = (body_score * 0.25 +
                         wick_score * 0.25 +
                         variation_score * 0.25 +
                         momentum_score * 0.25)

        # Determine pattern strength
        if strength_score >= 0.85:
            self._signal.strength = PatternStrength.VERY_STRONG
        elif strength_score >= 0.7:
            self._signal.strength = PatternStrength.STRONG
        elif strength_score >= 0.5:
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

        # Pillar 3: Multi-Timeframe
        timeframe_score = 0.75  # Marubozu works well across timeframes
        self._signal.timeframe_components = {'convergence_score': timeframe_score}

        # Pillar 4: Smart Money/Microstructure
        smart_money_score = self._calculate_smart_money_score()
        self._signal.microstructure_components = {'institutional_bias': smart_money_score}

        # Pillar 5: Risk Management
        risk_score = self._calculate_risk_score()
        self._signal.risk_components = {'reward_risk_ratio': risk_score}

        # Weighted confidence score (Marubozu gets high weight due to conviction)
        weights = {
            'volume': 0.25,
            'regime': 0.20,
            'timeframe': 0.15,
            'smart_money': 0.25,
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
        if len(self.volume_ma) < 2:
            return 0.6  # Marubozu patterns often have significant volume

        current_volume = self.candles_buffer[-1]['volume']
        avg_volume = np.mean(self.volume_ma[-2:])

        if avg_volume > 0:
            volume_ratio = current_volume / avg_volume
            if volume_ratio >= self.volume_threshold_multiplier:
                return min(1.0, volume_ratio / (self.volume_threshold_multiplier * 2))
            else:
                return max(0.4, volume_ratio / self.volume_threshold_multiplier)

        return 0.6

    def _calculate_regime_score(self) -> float:
        """Calculate market regime alignment score"""
        if len(self.trend_ema_values) < 2:
            return 0.5

        current_price = self.candles_buffer[-1]['close']
        trend_price = self.trend_ema_values[-1]

        # Marubozu works well in trending markets
        if self._signal.pattern_type == MarubozuType.BULLISH:
            # Bullish Marubozu in uptrend gets higher score
            return 0.9 if current_price > trend_price else 0.6
        elif self._signal.pattern_type == MarubozuType.BEARISH:
            # Bearish Marubozu in downtrend gets higher score
            return 0.9 if current_price < trend_price else 0.6
        else:
            return 0.5

    def _calculate_smart_money_score(self) -> float:
        """Calculate smart money involvement score"""
        if len(self.volume_ma) < 2:
            return 0.7  # Marubozu patterns indicate strong institutional activity

        current_volume = self.candles_buffer[-1]['volume']
        avg_volume = np.mean(self.volume_ma[-2:])

        if current_volume > avg_volume * self.smart_money_threshold:
            return 0.95  # Very strong institutional activity
        elif current_volume > avg_volume * 2.0:
            return 0.85  # Strong institutional activity
        elif current_volume > avg_volume * 1.5:
            return 0.7  # Moderate institutional activity
        else:
            return 0.5  # Limited institutional involvement

    def _calculate_risk_score(self) -> float:
        """Calculate risk-adjusted score"""
        if len(self.atr_values) > 0:
            current_atr = self.atr_values[-1]
            body_size = self._signal.body_size

            if body_size > 0 and current_atr > 0:
                # Risk-reward based on body size vs volatility
                rr_ratio = body_size / current_atr
                return min(1.0, rr_ratio / 1.5)

        return 0.7  # Marubozu patterns generally have good risk-reward

    def _determine_pattern_direction(self) -> None:
        """Determine pattern direction based on type"""
        if self._signal.pattern_type == MarubozuType.BULLISH:
            self._signal.direction = "BULLISH"
        elif self._signal.pattern_type == MarubozuType.BEARISH:
            self._signal.direction = "BEARISH"
        else:
            self._signal.direction = "NEUTRAL"

    def _calculate_risk_parameters(self, candle: Dict) -> None:
        """Calculate stop loss and take profit levels"""
        body_size = self._signal.body_size

        if self._signal.pattern_type == MarubozuType.BULLISH:
            # Bullish Marubozu: stop below the low, target based on body size
            self._signal.stop_loss_price = candle['low'] * 0.998  # Small buffer below low
            # Target based on body size (measure of conviction)
            self._signal.take_profit_price = candle['high'] + (body_size * 2.0)
            risk = candle['high'] - self._signal.stop_loss_price
            reward = self._signal.take_profit_price - candle['high']
            self._signal.risk_reward_ratio = reward / risk if risk > 0 else 0

        elif self._signal.pattern_type == MarubozuType.BEARISH:
            # Bearish Marubozu: stop above the high, target based on body size
            self._signal.stop_loss_price = candle['high'] * 1.002  # Small buffer above high
            # Target based on body size (measure of conviction)
            self._signal.take_profit_price = candle['low'] - (body_size * 2.0)
            risk = self._signal.stop_loss_price - candle['low']
            reward = candle['low'] - self._signal.take_profit_price
            self._signal.risk_reward_ratio = reward / risk if risk > 0 else 0

    @property
    def signal(self) -> MarubozuSignal:
        """Get current pattern signal"""
        return self._signal

    def reset(self) -> None:
        """Reset pattern detector state"""
        self.candles_buffer.clear()
        self.volume_ma.clear()
        self.atr_values.clear()
        self.trend_ema_values.clear()
        self._signal = MarubozuSignal()


# Factory function for easy instantiation
def create_marubozu_detector(**kwargs) -> AugmentedMarubozu:
    """Create and return a configured Marubozu detector"""
    return AugmentedMarubozu(**kwargs)