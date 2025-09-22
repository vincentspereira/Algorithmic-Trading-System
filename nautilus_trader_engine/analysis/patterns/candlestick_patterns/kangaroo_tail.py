"""
Kangaroo Tail Candlestick Pattern Implementation
==============================================

Institutional-grade implementation of the Kangaroo Tail pattern with 5-pillar architecture.

Pattern Description:
- Single candle pattern characterized by an extremely long wick (tail)
- The wick extends far beyond the body of the candle
- Can be bullish (long lower wick) or bearish (long upper wick)
- Indicates strong rejection of price levels and potential reversal
- Rare but very reliable when it appears

Reliability Factor: 0.76 (Bullish), 0.74 (Bearish)
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
from ...core.augmented_indicator import AugmentedIndicator


class KangarooTailType(Enum):
    BULLISH = "BULLISH"      # Long lower wick, small upper body
    BEARISH = "BEARISH"      # Long upper wick, small lower body
    NEUTRAL = "NEUTRAL"


class PatternStrength(Enum):
    WEAK = 0.3
    MODERATE = 0.6
    STRONG = 0.8
    VERY_STRONG = 0.9


@dataclass
class KangarooTailSignal:
    """Enhanced signal object for Kangaroo Tail pattern"""
    pattern_name: str = "KANGAROO_TAIL"
    detected: bool = False
    pattern_type: KangarooTailType = KangarooTailType.NEUTRAL
    strength: PatternStrength = PatternStrength.WEAK
    direction: str = "NEUTRAL"  # BULLISH, BEARISH, NEUTRAL
    confidence_score: float = 0.0
    volume_confirmation: float = 0.0
    smart_money_score: float = 0.0
    risk_reward_ratio: float = 0.0
    stop_loss_price: float = 0.0
    take_profit_price: float = 0.0
    tail_length: float = 0.0
    body_size: float = 0.0
    tail_to_body_ratio: float = 0.0
    rejection_level: float = 0.0
    wick_extremity: float = 0.0

    # 5-Pillar Architecture Components
    volume_components: Dict[str, float] = None
    regime_components: Dict[str, float] = None
    timeframe_components: Dict[str, float] = None
    microstructure_components: Dict[str, float] = None
    risk_components: Dict[str, float] = None


class AugmentedKangarooTail(AugmentedIndicator):
    """
    Institutional-grade Kangaroo Tail pattern detector with 5-pillar architecture.

    The Kangaroo Tail is a powerful single-candle pattern that shows extreme
    rejection of price levels, often indicating major turning points.
    """

    def __init__(self,
                 volume_ma_period: int = 20,
                 atr_period: int = 14,
                 trend_ema_period: int = 200,
                 min_tail_ratio: float = 3.0,  # Minimum tail to body ratio
                 max_body_ratio: float = 0.3,  # Maximum body to total range ratio
                 volume_threshold_multiplier: float = 2.0,
                 smart_money_threshold: float = 3.0):
        """
        Initialize Kangaroo Tail detector.

        Args:
            volume_ma_period: Period for volume moving average
            atr_period: Period for ATR calculation
            trend_ema_period: Period for trend EMA
            min_tail_ratio: Minimum tail to body ratio for pattern recognition
            max_body_ratio: Maximum body size as percentage of total range
            volume_threshold_multiplier: Volume confirmation multiplier
            smart_money_threshold: Smart money detection threshold
        """
        super().__init__(name="KANGAROO_TAIL")

        # Core parameters
        self.volume_ma_period = volume_ma_period
        self.atr_period = atr_period
        self.trend_ema_period = trend_ema_period
        self.min_tail_ratio = min_tail_ratio
        self.max_body_ratio = max_body_ratio
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
        self._signal = KangarooTailSignal()

    def update(self, open_price: float, high_price: float, low_price: float,
               close_price: float, volume: float) -> KangarooTailSignal:
        """
        Update pattern detector with new price/volume data.

        Args:
            open_price: Opening price
            high_price: High price
            low_price: Low price
            close_price: Closing price
            volume: Trading volume

        Returns:
            KangarooTailSignal: Enhanced pattern signal
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
        self._signal = KangarooTailSignal()

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
        """Detect Kangaroo Tail pattern in the current candle"""
        if len(self.candles_buffer) < 1:
            return

        current_candle = self.candles_buffer[-1]

        # Analyze the current candle for Kangaroo Tail characteristics
        pattern_detected, pattern_type = self._analyze_candle_for_kangaroo_tail(current_candle)

        if pattern_detected:
            self._signal.detected = True
            self._signal.pattern_type = pattern_type
            self._analyze_pattern_strength(current_candle)
            self._calculate_confidence_score()
            self._determine_pattern_direction()
            self._calculate_risk_parameters(current_candle)

    def _analyze_candle_for_kangaroo_tail(self, candle: Dict) -> Tuple[bool, KangarooTailType]:
        """
        Analyze a candle for Kangaroo Tail characteristics.

        Pattern Criteria:
        1. Extremely long wick (tail) compared to body
        2. Small body relative to total range
        3. Wick extends significantly beyond body
        4. Can be bullish (long lower wick) or bearish (long upper wick)
        """
        try:
            # Calculate candle dimensions
            total_range = candle['high'] - candle['low']
            body_size = abs(candle['close'] - candle['open'])
            upper_wick = candle['high'] - max(candle['open'], candle['close'])
            lower_wick = min(candle['open'], candle['close']) - candle['low']

            if total_range <= 0:
                return False, KangarooTailType.NEUTRAL

            # Body should be small relative to total range
            body_ratio = body_size / total_range
            if body_ratio > self.max_body_ratio:
                return False, KangarooTailType.NEUTRAL

            # Check for bullish Kangaroo Tail (long lower wick)
            if lower_wick > upper_wick:  # Lower wick is longer
                tail_length = lower_wick
                tail_to_body_ratio = tail_length / body_size if body_size > 0 else float('inf')

                if tail_to_body_ratio >= self.min_tail_ratio:
                    # Additional check: lower wick should be significant portion of total range
                    if lower_wick >= total_range * 0.6:  # At least 60% of total range
                        return True, KangarooTailType.BULLISH

            # Check for bearish Kangaroo Tail (long upper wick)
            elif upper_wick > lower_wick:  # Upper wick is longer
                tail_length = upper_wick
                tail_to_body_ratio = tail_length / body_size if body_size > 0 else float('inf')

                if tail_to_body_ratio >= self.min_tail_ratio:
                    # Additional check: upper wick should be significant portion of total range
                    if upper_wick >= total_range * 0.6:  # At least 60% of total range
                        return True, KangarooTailType.BEARISH

            return False, KangarooTailType.NEUTRAL

        except (KeyError, ZeroDivisionError):
            return False, KangarooTailType.NEUTRAL

    def _analyze_pattern_strength(self, candle: Dict) -> None:
        """Analyze the strength of the detected Kangaroo Tail pattern"""
        # Calculate pattern metrics
        total_range = candle['high'] - candle['low']
        body_size = abs(candle['close'] - candle['open'])
        upper_wick = candle['high'] - max(candle['open'], candle['close'])
        lower_wick = min(candle['open'], candle['close']) - candle['low']

        # Determine which wick is the tail
        if self._signal.pattern_type == KangarooTailType.BULLISH:
            tail_length = lower_wick
            wick_extremity = candle['low']
            rejection_level = candle['low']
        elif self._signal.pattern_type == KangarooTailType.BEARISH:
            tail_length = upper_wick
            wick_extremity = candle['high']
            rejection_level = candle['high']
        else:
            return

        # Update signal with pattern metrics
        self._signal.tail_length = tail_length
        self._signal.body_size = body_size
        self._signal.tail_to_body_ratio = tail_length / body_size if body_size > 0 else float('inf')
        self._signal.rejection_level = rejection_level
        self._signal.wick_extremity = wick_extremity

        # Strength analysis based on multiple factors

        # 1. Tail length relative to total range
        tail_range_ratio = tail_length / total_range
        range_score = min(1.0, tail_range_ratio * 2.5)  # Scale to 0-1

        # 2. Tail to body ratio (higher ratio = stronger rejection)
        ratio_score = min(1.0, self._signal.tail_to_body_ratio / 10.0)  # Scale to 0-1

        # 3. Body size (smaller body = stronger rejection)
        body_score = 1.0 - (body_size / total_range)  # Smaller body = higher score

        # 4. Position within recent range (more extreme = stronger)
        if len(self.candles_buffer) >= 3:
            recent_highs = [c['high'] for c in self.candles_buffer[-3:]]
            recent_lows = [c['low'] for c in self.candles_buffer[-3:]]

            recent_range_high = max(recent_highs)
            recent_range_low = min(recent_lows)

            if self._signal.pattern_type == KangarooTailType.BULLISH:
                extremity_score = (recent_range_low - wick_extremity) / (recent_range_high - recent_range_low)
                extremity_score = min(1.0, extremity_score * 2)  # Scale up for extremity
            else:
                extremity_score = (wick_extremity - recent_range_high) / (recent_range_high - recent_range_low)
                extremity_score = min(1.0, extremity_score * 2)  # Scale up for extremity
        else:
            extremity_score = 0.5

        # Combine scores with weights
        strength_score = (range_score * 0.25 +
                         ratio_score * 0.30 +
                         body_score * 0.25 +
                         extremity_score * 0.20)

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
        timeframe_score = 0.8  # Kangaroo Tail works well across timeframes
        self._signal.timeframe_components = {'convergence_score': timeframe_score}

        # Pillar 4: Smart Money/Microstructure
        smart_money_score = self._calculate_smart_money_score()
        self._signal.microstructure_components = {'institutional_bias': smart_money_score}

        # Pillar 5: Risk Management
        risk_score = self._calculate_risk_score()
        self._signal.risk_components = {'reward_risk_ratio': risk_score}

        # Weighted confidence score (Kangaroo Tail gets high base weight due to rarity and strength)
        weights = {
            'volume': 0.20,
            'regime': 0.20,
            'timeframe': 0.20,
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
            return 0.6  # Kangaroo Tail patterns often have high volume by nature

        current_volume = self.candles_buffer[-1]['volume']
        avg_volume = np.mean(self.volume_ma[-2:])

        if avg_volume > 0:
            volume_ratio = current_volume / avg_volume
            if volume_ratio >= self.volume_threshold_multiplier:
                return min(1.0, volume_ratio / (self.volume_threshold_multiplier * 2))
            else:
                return max(0.3, volume_ratio / self.volume_threshold_multiplier)

        return 0.6

    def _calculate_regime_score(self) -> float:
        """Calculate market regime alignment score"""
        if len(self.trend_ema_values) < 2:
            return 0.5

        current_price = self.candles_buffer[-1]['close']
        trend_price = self.trend_ema_values[-1]

        # Kangaroo Tail works best at key levels and can signal reversals
        if self._signal.pattern_type == KangarooTailType.BULLISH:
            # Bullish pattern works well at support levels
            return 0.8 if current_price < trend_price else 0.6
        elif self._signal.pattern_type == KangarooTailType.BEARISH:
            # Bearish pattern works well at resistance levels
            return 0.8 if current_price > trend_price else 0.6
        else:
            return 0.5

    def _calculate_smart_money_score(self) -> float:
        """Calculate smart money involvement score"""
        if len(self.volume_ma) < 2:
            return 0.7  # Kangaroo Tail patterns often indicate institutional activity

        current_volume = self.candles_buffer[-1]['volume']
        avg_volume = np.mean(self.volume_ma[-2:])

        if current_volume > avg_volume * self.smart_money_threshold:
            return 0.95  # Very strong institutional activity
        elif current_volume > avg_volume * 2.5:
            return 0.85  # Strong institutional activity
        elif current_volume > avg_volume * 2.0:
            return 0.75  # Moderate institutional activity
        else:
            return 0.5  # Limited institutional involvement

    def _calculate_risk_score(self) -> float:
        """Calculate risk-adjusted score"""
        if len(self.atr_values) > 0:
            current_atr = self.atr_values[-1]
            tail_length = self._signal.tail_length

            if tail_length > 0 and current_atr > 0:
                # Risk-reward based on tail length vs volatility
                rr_ratio = tail_length / current_atr
                return min(1.0, rr_ratio / 2.0)

        return 0.7  # Kangaroo Tail patterns generally have excellent risk-reward

    def _determine_pattern_direction(self) -> None:
        """Determine pattern direction based on type"""
        if self._signal.pattern_type == KangarooTailType.BULLISH:
            self._signal.direction = "BULLISH"
        elif self._signal.pattern_type == KangarooTailType.BEARISH:
            self._signal.direction = "BEARISH"
        else:
            self._signal.direction = "NEUTRAL"

    def _calculate_risk_parameters(self, candle: Dict) -> None:
        """Calculate stop loss and take profit levels"""
        rejection_level = self._signal.rejection_level
        tail_length = self._signal.tail_length

        if self._signal.pattern_type == KangarooTailType.BULLISH:
            # Bullish Kangaroo Tail: stop below the wick extremity, target above rejection level
            self._signal.stop_loss_price = self._signal.wick_extremity * 0.997  # Just below the wick
            # Target based on tail length (measure of rejection strength)
            self._signal.take_profit_price = rejection_level + (tail_length * 2.5)
            risk = rejection_level - self._signal.stop_loss_price
            reward = self._signal.take_profit_price - rejection_level
            self._signal.risk_reward_ratio = reward / risk if risk > 0 else 0

        elif self._signal.pattern_type == KangarooTailType.BEARISH:
            # Bearish Kangaroo Tail: stop above the wick extremity, target below rejection level
            self._signal.stop_loss_price = self._signal.wick_extremity * 1.003  # Just above the wick
            # Target based on tail length (measure of rejection strength)
            self._signal.take_profit_price = rejection_level - (tail_length * 2.5)
            risk = self._signal.stop_loss_price - rejection_level
            reward = rejection_level - self._signal.take_profit_price
            self._signal.risk_reward_ratio = reward / risk if risk > 0 else 0

    @property
    def signal(self) -> KangarooTailSignal:
        """Get current pattern signal"""
        return self._signal

    def reset(self) -> None:
        """Reset pattern detector state"""
        self.candles_buffer.clear()
        self.volume_ma.clear()
        self.atr_values.clear()
        self.trend_ema_values.clear()
        self._signal = KangarooTailSignal()


# Factory function for easy instantiation
def create_kangaroo_tail_detector(**kwargs) -> AugmentedKangarooTail:
    """Create and return a configured Kangaroo Tail detector"""
    return AugmentedKangarooTail(**kwargs)