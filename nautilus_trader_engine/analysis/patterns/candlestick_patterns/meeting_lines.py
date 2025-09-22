"""
Meeting Lines Candlestick Pattern Implementation
==============================================

Institutional-grade implementation of the Meeting Lines pattern with 5-pillar architecture.

Pattern Description:
- Two-candle reversal pattern
- First candle: Strong directional move
- Second candle: Closes at the same level as the first candle's close
- Indicates a potential reversal at key levels
- Can be bullish (Bullish Meeting Lines) or bearish (Bearish Meeting Lines)

Reliability Factor: 0.68 (Bullish), 0.65 (Bearish)
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
from ...core.augmented_indicator import AugmentedIndicator


class MeetingLinesType(Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class PatternStrength(Enum):
    WEAK = 0.3
    MODERATE = 0.6
    STRONG = 0.8
    VERY_STRONG = 0.9


@dataclass
class MeetingLinesSignal:
    """Enhanced signal object for Meeting Lines pattern"""
    pattern_name: str = "MEETING_LINES"
    detected: bool = False
    pattern_type: MeetingLinesType = MeetingLinesType.NEUTRAL
    strength: PatternStrength = PatternStrength.WEAK
    direction: str = "NEUTRAL"  # BULLISH, BEARISH, NEUTRAL
    confidence_score: float = 0.0
    volume_confirmation: float = 0.0
    smart_money_score: float = 0.0
    risk_reward_ratio: float = 0.0
    stop_loss_price: float = 0.0
    take_profit_price: float = 0.0
    meeting_level: float = 0.0
    first_candle_range: float = 0.0
    second_candle_range: float = 0.0

    # 5-Pillar Architecture Components
    volume_components: Dict[str, float] = None
    regime_components: Dict[str, float] = None
    timeframe_components: Dict[str, float] = None
    microstructure_components: Dict[str, float] = None
    risk_components: Dict[str, float] = None


class AugmentedMeetingLines(AugmentedIndicator):
    """
    Institutional-grade Meeting Lines pattern detector with 5-pillar architecture.

    Meeting Lines occur when two candles close at the exact same level,
    indicating a potential reversal as the market tests a key level.
    """

    def __init__(self,
                 volume_ma_period: int = 20,
                 atr_period: int = 14,
                 trend_ema_period: int = 200,
                 close_tolerance_pct: float = 0.001,  # 0.1% tolerance for meeting level
                 min_strength_threshold: float = 0.6,
                 volume_threshold_multiplier: float = 1.5,
                 smart_money_threshold: float = 2.0):
        """
        Initialize Meeting Lines detector.

        Args:
            volume_ma_period: Period for volume moving average
            atr_period: Period for ATR calculation
            trend_ema_period: Period for trend EMA
            close_tolerance_pct: Percentage tolerance for meeting close levels
            min_strength_threshold: Minimum pattern strength threshold
            volume_threshold_multiplier: Volume confirmation multiplier
            smart_money_threshold: Smart money detection threshold
        """
        super().__init__(name="MEETING_LINES")

        # Core parameters
        self.volume_ma_period = volume_ma_period
        self.atr_period = atr_period
        self.trend_ema_period = trend_ema_period
        self.close_tolerance_pct = close_tolerance_pct
        self.min_strength_threshold = min_strength_threshold
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
        self._signal = MeetingLinesSignal()

    def update(self, open_price: float, high_price: float, low_price: float,
               close_price: float, volume: float) -> MeetingLinesSignal:
        """
        Update pattern detector with new price/volume data.

        Args:
            open_price: Opening price
            high_price: High price
            low_price: Low price
            close_price: Closing price
            volume: Trading volume

        Returns:
            MeetingLinesSignal: Enhanced pattern signal
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
        self._signal = MeetingLinesSignal()

        # Need at least 2 candles for pattern detection
        if len(self.candles_buffer) >= 2:
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
        """Detect Meeting Lines pattern in the candle buffer"""
        if len(self.candles_buffer) < 2:
            return

        # Get last 2 candles
        c2, c1 = self.candles_buffer[-2:]

        # Pattern recognition logic
        pattern_detected, pattern_type = self._check_meeting_lines_criteria(c1, c2)

        if pattern_detected:
            self._signal.detected = True
            self._signal.pattern_type = pattern_type
            self._analyze_pattern_strength(c1, c2)
            self._calculate_confidence_score()
            self._determine_pattern_direction(c1, c2)
            self._calculate_risk_parameters(c1, c2)

    def _check_meeting_lines_criteria(self, c1: Dict, c2: Dict) -> Tuple[bool, MeetingLinesType]:
        """
        Check if candles meet Meeting Lines criteria.

        Pattern Rules:
        1. Two consecutive candles
        2. Both candles close at the same level (within tolerance)
        3. First candle shows strong directional movement
        4. Second candle meets the first candle's close

        Types:
        - Bullish Meeting Lines: First candle bearish, second bullish, same close
        - Bearish Meeting Lines: First candle bullish, second bearish, same close
        """
        try:
            # Check if closes meet within tolerance
            close_diff_pct = abs(c1['close'] - c2['close']) / c2['close']
            closes_meet = close_diff_pct <= self.close_tolerance_pct

            if not closes_meet:
                return False, MeetingLinesType.NEUTRAL

            # Determine pattern type based on candle directions
            c1_bearish = c1['close'] < c1['open']
            c2_bullish = c2['close'] > c2['open']
            c1_bullish = c1['close'] > c1['open']
            c2_bearish = c2['close'] < c2['open']

            # Bullish Meeting Lines: Bearish + Bullish with same close
            if c1_bearish and c2_bullish:
                return True, MeetingLinesType.BULLISH

            # Bearish Meeting Lines: Bullish + Bearish with same close
            elif c1_bullish and c2_bearish:
                return True, MeetingLinesType.BEARISH

            # Neutral case (both same direction but meeting close)
            else:
                return True, MeetingLinesType.NEUTRAL

        except (KeyError, ZeroDivisionError):
            return False, MeetingLinesType.NEUTRAL

    def _analyze_pattern_strength(self, c1: Dict, c2: Dict) -> None:
        """Analyze the strength of the detected pattern"""
        # Calculate candle ranges
        c1_range = c1['high'] - c1['low']
        c2_range = c2['high'] - c2['low']

        self._signal.first_candle_range = c1_range
        self._signal.second_candle_range = c2_range
        self._signal.meeting_level = c2['close']

        # Strength based on candle sizes and meeting precision
        avg_range = (c1_range + c2_range) / 2

        # Larger candles indicate stronger conviction
        size_score = min(1.0, avg_range / (self._signal.meeting_level * 0.02))  # 2% of price as benchmark

        # Meeting precision (closer meeting = stronger pattern)
        meeting_precision = 1.0 - (abs(c1['close'] - c2['close']) / self._signal.meeting_level)
        precision_score = max(0.0, meeting_precision)

        # Directional change strength
        c1_body = abs(c1['close'] - c1['open'])
        c2_body = abs(c2['close'] - c2['open'])
        direction_change_score = min(1.0, (c1_body + c2_body) / avg_range)

        # Combine scores
        strength_score = (size_score * 0.4 + precision_score * 0.4 + direction_change_score * 0.2)

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

        # Pillar 3: Multi-Timeframe
        timeframe_score = 0.7  # Placeholder for higher timeframe analysis
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
        if len(self.volume_ma) < 2:
            return 0.5

        avg_volume = np.mean(self.volume_ma[-2:])
        current_volume = self.candles_buffer[-1]['volume']

        if avg_volume > 0:
            volume_ratio = current_volume / avg_volume
            if volume_ratio >= self.volume_threshold_multiplier:
                return min(1.0, volume_ratio / (self.volume_threshold_multiplier * 2))
            else:
                return max(0.0, volume_ratio / self.volume_threshold_multiplier)

        return 0.5

    def _calculate_regime_score(self) -> float:
        """Calculate market regime alignment score"""
        if len(self.trend_ema_values) < 2:
            return 0.5

        current_price = self.candles_buffer[-1]['close']
        trend_price = self.trend_ema_values[-1]

        # Pattern type affects regime alignment
        if self._signal.pattern_type == MeetingLinesType.BULLISH:
            # Bullish pattern in uptrend gets higher score
            return 0.8 if current_price > trend_price else 0.4
        elif self._signal.pattern_type == MeetingLinesType.BEARISH:
            # Bearish pattern in downtrend gets higher score
            return 0.8 if current_price < trend_price else 0.4
        else:
            return 0.5

    def _calculate_smart_money_score(self) -> float:
        """Calculate smart money involvement score"""
        if len(self.volume_ma) < 2:
            return 0.5

        current_volume = self.candles_buffer[-1]['volume']
        avg_volume = np.mean(self.volume_ma[-2:])

        if current_volume > avg_volume * self.smart_money_threshold:
            return 0.9  # Strong institutional activity
        elif current_volume > avg_volume * 2.0:
            return 0.7  # Moderate institutional activity
        elif current_volume > avg_volume * 1.5:
            return 0.5  # Light institutional activity
        else:
            return 0.2  # Retail-dominated activity

    def _calculate_risk_score(self) -> float:
        """Calculate risk-adjusted score"""
        if len(self.atr_values) > 0:
            current_atr = self.atr_values[-1]
            pattern_height = max(self._signal.first_candle_range, self._signal.second_candle_range)

            if pattern_height > 0 and current_atr > 0:
                rr_ratio = pattern_height / current_atr
                return min(1.0, rr_ratio / 2.0)

        return 0.5

    def _determine_pattern_direction(self, c1: Dict, c2: Dict) -> None:
        """Determine pattern direction based on type"""
        if self._signal.pattern_type == MeetingLinesType.BULLISH:
            self._signal.direction = "BULLISH"
        elif self._signal.pattern_type == MeetingLinesType.BEARISH:
            self._signal.direction = "BEARISH"
        else:
            self._signal.direction = "NEUTRAL"

    def _calculate_risk_parameters(self, c1: Dict, c2: Dict) -> None:
        """Calculate stop loss and take profit levels"""
        meeting_level = self._signal.meeting_level

        # Calculate pattern extremes
        highs = [c1['high'], c2['high']]
        lows = [c1['low'], c2['low']]

        pattern_high = max(highs)
        pattern_low = min(lows)

        # Stop loss and take profit based on pattern direction
        if self._signal.pattern_type == MeetingLinesType.BULLISH:
            # Bullish pattern: stop below pattern low, target above meeting level
            self._signal.stop_loss_price = pattern_low * 0.998  # Small buffer
            pattern_height = pattern_high - pattern_low
            self._signal.take_profit_price = meeting_level + (pattern_height * 2)
            self._signal.risk_reward_ratio = (self._signal.take_profit_price - meeting_level) / (meeting_level - self._signal.stop_loss_price)

        elif self._signal.pattern_type == MeetingLinesType.BEARISH:
            # Bearish pattern: stop above pattern high, target below meeting level
            self._signal.stop_loss_price = pattern_high * 1.002  # Small buffer
            pattern_height = pattern_high - pattern_low
            self._signal.take_profit_price = meeting_level - (pattern_height * 2)
            self._signal.risk_reward_ratio = (meeting_level - self._signal.take_profit_price) / (self._signal.stop_loss_price - meeting_level)

        else:
            # Neutral pattern: symmetric risk management
            self._signal.stop_loss_price = pattern_low * 0.995
            self._signal.take_profit_price = pattern_high * 1.005
            self._signal.risk_reward_ratio = 1.0

    @property
    def signal(self) -> MeetingLinesSignal:
        """Get current pattern signal"""
        return self._signal

    def reset(self) -> None:
        """Reset pattern detector state"""
        self.candles_buffer.clear()
        self.volume_ma.clear()
        self.atr_values.clear()
        self.trend_ema_values.clear()
        self._signal = MeetingLinesSignal()


# Factory function for easy instantiation
def create_meeting_lines_detector(**kwargs) -> AugmentedMeetingLines:
    """Create and return a configured Meeting Lines detector"""
    return AugmentedMeetingLines(**kwargs)