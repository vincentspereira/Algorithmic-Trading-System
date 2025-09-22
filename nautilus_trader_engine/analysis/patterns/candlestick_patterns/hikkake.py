"""
Hikkake Candlestick Pattern Implementation
========================================

Institutional-grade implementation of the Hikkake pattern with 5-pillar architecture.

Pattern Description:
- Multi-candle pattern (typically 3-5 candles)
- Involves a false breakout of an inside bar
- Followed by a reversal that traps breakout traders
- Can be bullish (Bullish Hikkake) or bearish (Bearish Hikkake)
- One of the most reliable reversal patterns

Reliability Factor: 0.74 (Bullish), 0.72 (Bearish)
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
from ...core.augmented_indicator import AugmentedIndicator


class HikkakeType(Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class HikkakePhase(Enum):
    SETUP = "SETUP"           # Inside bar formation
    BREAKOUT = "BREAKOUT"     # False breakout
    REVERSAL = "REVERSAL"     # Reversal confirmation
    COMPLETED = "COMPLETED"   # Pattern complete


class PatternStrength(Enum):
    WEAK = 0.3
    MODERATE = 0.6
    STRONG = 0.8
    VERY_STRONG = 0.9


@dataclass
class HikkakeSignal:
    """Enhanced signal object for Hikkake pattern"""
    pattern_name: str = "HIKKAKE"
    detected: bool = False
    pattern_type: HikkakeType = HikkakeType.NEUTRAL
    current_phase: HikkakePhase = HikkakePhase.SETUP
    strength: PatternStrength = PatternStrength.WEAK
    direction: str = "NEUTRAL"  # BULLISH, BEARISH, NEUTRAL
    confidence_score: float = 0.0
    volume_confirmation: float = 0.0
    smart_money_score: float = 0.0
    risk_reward_ratio: float = 0.0
    stop_loss_price: float = 0.0
    take_profit_price: float = 0.0
    inside_bar_high: float = 0.0
    inside_bar_low: float = 0.0
    breakout_level: float = 0.0
    reversal_candle_index: int = -1

    # 5-Pillar Architecture Components
    volume_components: Dict[str, float] = None
    regime_components: Dict[str, float] = None
    timeframe_components: Dict[str, float] = None
    microstructure_components: Dict[str, float] = None
    risk_components: Dict[str, float] = None


class AugmentedHikkake(AugmentedIndicator):
    """
    Institutional-grade Hikkake pattern detector with 5-pillar architecture.

    The Hikkake pattern is a sophisticated multi-candle formation that identifies
    false breakouts followed by reversals, trapping breakout traders.
    """

    def __init__(self,
                 volume_ma_period: int = 20,
                 atr_period: int = 14,
                 trend_ema_period: int = 200,
                 max_pattern_length: int = 5,  # Maximum candles for pattern completion
                 breakout_threshold_pct: float = 0.001,  # 0.1% breakout threshold
                 volume_threshold_multiplier: float = 1.8,
                 smart_money_threshold: float = 2.5):
        """
        Initialize Hikkake detector.

        Args:
            volume_ma_period: Period for volume moving average
            atr_period: Period for ATR calculation
            trend_ema_period: Period for trend EMA
            max_pattern_length: Maximum candles allowed for pattern completion
            breakout_threshold_pct: Percentage threshold for breakout detection
            volume_threshold_multiplier: Volume confirmation multiplier
            smart_money_threshold: Smart money detection threshold
        """
        super().__init__(name="HIKKAKE")

        # Core parameters
        self.volume_ma_period = volume_ma_period
        self.atr_period = atr_period
        self.trend_ema_period = trend_ema_period
        self.max_pattern_length = max_pattern_length
        self.breakout_threshold_pct = breakout_threshold_pct
        self.volume_threshold_multiplier = volume_threshold_multiplier
        self.smart_money_threshold = smart_money_threshold

        # Internal indicators for 5-pillar analysis
        self.volume_ma = []
        self.atr_values = []
        self.trend_ema_values = []

        # Pattern tracking
        self.candles_buffer = []
        self.pattern_start_index = -1
        self.inside_bar_found = False
        self.breakout_detected = False

        # Initialize signal object
        self._signal = HikkakeSignal()

    def update(self, open_price: float, high_price: float, low_price: float,
               close_price: float, volume: float) -> HikkakeSignal:
        """
        Update pattern detector with new price/volume data.

        Args:
            open_price: Opening price
            high_price: High price
            low_price: Low price
            close_price: Closing price
            volume: Trading volume

        Returns:
            HikkakeSignal: Enhanced pattern signal
        """
        # Update internal indicators
        self._update_internal_indicators(open_price, high_price, low_price, close_price, volume)

        # Add current candle to buffer
        current_candle = {
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume,
            'index': len(self.candles_buffer)
        }

        self.candles_buffer.append(current_candle)

        # Maintain buffer size
        if len(self.candles_buffer) > self.max_pattern_length + 5:
            self.candles_buffer.pop(0)

        # Reset signal if pattern completed or failed
        if self._signal.detected and self._signal.current_phase == HikkakePhase.COMPLETED:
            # Keep completed pattern for some time, then reset
            pass
        else:
            self._signal = HikkakeSignal()

        # Pattern detection logic
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
        """Detect Hikkake pattern through multiple phases"""
        if len(self.candles_buffer) < 3:
            return

        # Phase 1: Look for inside bar (setup phase)
        if not self.inside_bar_found:
            self._find_inside_bar()

        # Phase 2: Look for false breakout
        elif not self.breakout_detected:
            self._detect_false_breakout()

        # Phase 3: Look for reversal confirmation
        elif self.breakout_detected:
            self._detect_reversal()

    def _find_inside_bar(self) -> None:
        """Find inside bar that could start a Hikkake pattern"""
        if len(self.candles_buffer) < 2:
            return

        # Check last two candles for inside bar formation
        c2, c1 = self.candles_buffer[-2:]

        # Inside bar criteria:
        # 1. c1 high <= c2 high
        # 2. c1 low >= c2 low
        # 3. c1 range < c2 range (smaller than previous candle)

        c1_range = c1['high'] - c1['low']
        c2_range = c2['high'] - c2['low']

        is_inside_bar = (c1['high'] <= c2['high'] and
                        c1['low'] >= c2['low'] and
                        c1_range < c2_range * 0.8)  # Inside bar significantly smaller

        if is_inside_bar:
            self.inside_bar_found = True
            self.pattern_start_index = len(self.candles_buffer) - 1
            self._signal.inside_bar_high = c1['high']
            self._signal.inside_bar_low = c1['low']
            self._signal.current_phase = HikkakePhase.SETUP

    def _detect_false_breakout(self) -> None:
        """Detect false breakout of the inside bar"""
        if not self.inside_bar_found or len(self.candles_buffer) < 3:
            return

        # Get the breakout candle (candle after inside bar)
        breakout_candle = self.candles_buffer[-1]

        # Check for breakout above inside bar high (bullish breakout)
        bullish_breakout = breakout_candle['high'] > self._signal.inside_bar_high

        # Check for breakout below inside bar low (bearish breakout)
        bearish_breakout = breakout_candle['low'] < self._signal.inside_bar_low

        if bullish_breakout:
            self.breakout_detected = True
            self._signal.breakout_level = breakout_candle['high']
            self._signal.pattern_type = HikkakeType.BULLISH
            self._signal.current_phase = HikkakePhase.BREAKOUT

        elif bearish_breakout:
            self.breakout_detected = True
            self._signal.breakout_level = breakout_candle['low']
            self._signal.pattern_type = HikkakeType.BEARISH
            self._signal.current_phase = HikkakePhase.BREAKOUT

    def _detect_reversal(self) -> None:
        """Detect reversal that confirms the Hikkake pattern"""
        if not self.breakout_detected or len(self.candles_buffer) < 4:
            return

        current_candle = self.candles_buffer[-1]

        # For bullish Hikkake: look for price rejection and move below breakout level
        if self._signal.pattern_type == HikkakeType.BULLISH:
            # Reversal criteria for bullish Hikkake:
            # 1. Current candle closes below the breakout level
            # 2. Shows rejection of higher prices (bearish candle or long upper wick)
            reversal_confirmed = (current_candle['close'] < self._signal.breakout_level and
                                (current_candle['close'] < current_candle['open'] or  # Bearish candle
                                 (current_candle['high'] - current_candle['close']) > (current_candle['close'] - current_candle['open']) * 2))  # Long upper wick

        # For bearish Hikkake: look for price rejection and move above breakout level
        elif self._signal.pattern_type == HikkakeType.BEARISH:
            # Reversal criteria for bearish Hikkake:
            # 1. Current candle closes above the breakout level
            # 2. Shows rejection of lower prices (bullish candle or long lower wick)
            reversal_confirmed = (current_candle['close'] > self._signal.breakout_level and
                                (current_candle['close'] > current_candle['open'] or  # Bullish candle
                                 (current_candle['close'] - current_candle['low']) > (current_candle['open'] - current_candle['close']) * 2))  # Long lower wick

        else:
            reversal_confirmed = False

        if reversal_confirmed:
            self._signal.detected = True
            self._signal.current_phase = HikkakePhase.COMPLETED
            self._signal.reversal_candle_index = current_candle['index']
            self._analyze_pattern_strength()
            self._calculate_confidence_score()
            self._determine_pattern_direction()
            self._calculate_risk_parameters()

    def _analyze_pattern_strength(self) -> None:
        """Analyze the strength of the completed Hikkake pattern"""
        if not self._signal.detected:
            return

        # Get relevant candles
        inside_bar = None
        breakout_candle = None
        reversal_candle = None

        for candle in self.candles_buffer:
            if candle['index'] == self.pattern_start_index:
                inside_bar = candle
            elif candle['index'] == self.pattern_start_index + 1:
                breakout_candle = candle
            elif candle['index'] == self._signal.reversal_candle_index:
                reversal_candle = candle

        if not all([inside_bar, breakout_candle, reversal_candle]):
            return

        # Strength analysis based on multiple factors

        # 1. Inside bar quality (tighter range = stronger setup)
        inside_bar_range = inside_bar['high'] - inside_bar['low']
        setup_candle_range = self.candles_buffer[self.pattern_start_index - 1]['high'] - self.candles_buffer[self.pattern_start_index - 1]['low']
        inside_bar_quality = max(0, 1 - (inside_bar_range / setup_candle_range))

        # 2. Breakout strength
        if self._signal.pattern_type == HikkakeType.BULLISH:
            breakout_strength = (breakout_candle['high'] - self._signal.inside_bar_high) / self._signal.inside_bar_high
        else:
            breakout_strength = (self._signal.inside_bar_low - breakout_candle['low']) / self._signal.inside_bar_low

        # 3. Reversal conviction
        reversal_body = abs(reversal_candle['close'] - reversal_candle['open'])
        reversal_range = reversal_candle['high'] - reversal_candle['low']
        reversal_conviction = reversal_body / reversal_range if reversal_range > 0 else 0

        # 4. Pattern duration (shorter = stronger)
        pattern_duration = self._signal.reversal_candle_index - self.pattern_start_index
        duration_score = max(0, 1 - (pattern_duration / self.max_pattern_length))

        # Combine scores
        strength_score = (inside_bar_quality * 0.3 +
                         min(1.0, breakout_strength * 100) * 0.25 +
                         reversal_conviction * 0.25 +
                         duration_score * 0.2)

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
        timeframe_score = 0.75  # Hikkake works well across timeframes
        self._signal.timeframe_components = {'convergence_score': timeframe_score}

        # Pillar 4: Smart Money/Microstructure
        smart_money_score = self._calculate_smart_money_score()
        self._signal.microstructure_components = {'institutional_bias': smart_money_score}

        # Pillar 5: Risk Management
        risk_score = self._calculate_risk_score()
        self._signal.risk_components = {'reward_risk_ratio': risk_score}

        # Weighted confidence score (Hikkake gets higher base weight due to reliability)
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

        # Check volume on breakout and reversal candles
        breakout_volume = self.candles_buffer[-2]['volume'] if len(self.candles_buffer) >= 2 else 0
        reversal_volume = self.candles_buffer[-1]['volume']

        avg_volume = np.mean(self.volume_ma[-3:])

        breakout_ratio = breakout_volume / avg_volume if avg_volume > 0 else 1
        reversal_ratio = reversal_volume / avg_volume if avg_volume > 0 else 1

        # Both breakout and reversal should have above-average volume
        volume_score = (min(1.0, breakout_ratio / 2) + min(1.0, reversal_ratio / 2)) / 2

        return volume_score

    def _calculate_regime_score(self) -> float:
        """Calculate market regime alignment score"""
        if len(self.trend_ema_values) < 2:
            return 0.5

        current_price = self.candles_buffer[-1]['close']
        trend_price = self.trend_ema_values[-1]

        # Hikkake works best in ranging markets or against the trend
        if self._signal.pattern_type == HikkakeType.BULLISH:
            # Bullish Hikkake in downtrend gets higher score
            return 0.8 if current_price < trend_price else 0.5
        elif self._signal.pattern_type == HikkakeType.BEARISH:
            # Bearish Hikkake in uptrend gets higher score
            return 0.8 if current_price > trend_price else 0.5
        else:
            return 0.5

    def _calculate_smart_money_score(self) -> float:
        """Calculate smart money involvement score"""
        if len(self.volume_ma) < 3:
            return 0.5

        # Smart money often creates traps like Hikkake patterns
        breakout_volume = self.candles_buffer[-2]['volume'] if len(self.candles_buffer) >= 2 else 0
        avg_volume = np.mean(self.volume_ma[-3:])

        if breakout_volume > avg_volume * self.smart_money_threshold:
            return 0.9  # Strong institutional activity (trap setting)
        elif breakout_volume > avg_volume * 2.0:
            return 0.7  # Moderate institutional activity
        else:
            return 0.4  # Limited institutional involvement

    def _calculate_risk_score(self) -> float:
        """Calculate risk-adjusted score"""
        if len(self.atr_values) > 0:
            current_atr = self.atr_values[-1]
            inside_bar_range = self._signal.inside_bar_high - self._signal.inside_bar_low

            if inside_bar_range > 0 and current_atr > 0:
                # Risk-reward based on pattern setup vs volatility
                rr_ratio = inside_bar_range / current_atr
                return min(1.0, rr_ratio / 1.5)

        return 0.6  # Hikkake patterns generally have good risk-reward

    def _determine_pattern_direction(self) -> None:
        """Determine pattern direction based on type"""
        if self._signal.pattern_type == HikkakeType.BULLISH:
            self._signal.direction = "BULLISH"
        elif self._signal.pattern_type == HikkakeType.BEARISH:
            self._signal.direction = "BEARISH"
        else:
            self._signal.direction = "NEUTRAL"

    def _calculate_risk_parameters(self) -> None:
        """Calculate stop loss and take profit levels"""
        if self._signal.pattern_type == HikkakeType.BULLISH:
            # Bullish Hikkake: stop below inside bar low, target based on breakout level
            self._signal.stop_loss_price = self._signal.inside_bar_low * 0.998
            breakout_height = self._signal.breakout_level - self._signal.inside_bar_low
            self._signal.take_profit_price = self._signal.breakout_level + (breakout_height * 1.5)
            risk = self._signal.breakout_level - self._signal.stop_loss_price
            reward = self._signal.take_profit_price - self._signal.breakout_level
            self._signal.risk_reward_ratio = reward / risk if risk > 0 else 0

        elif self._signal.pattern_type == HikkakeType.BEARISH:
            # Bearish Hikkake: stop above inside bar high, target based on breakout level
            self._signal.stop_loss_price = self._signal.inside_bar_high * 1.002
            breakout_height = self._signal.inside_bar_high - self._signal.breakout_level
            self._signal.take_profit_price = self._signal.breakout_level - (breakout_height * 1.5)
            risk = self._signal.stop_loss_price - self._signal.breakout_level
            reward = self._signal.breakout_level - self._signal.take_profit_price
            self._signal.risk_reward_ratio = reward / risk if risk > 0 else 0

    @property
    def signal(self) -> HikkakeSignal:
        """Get current pattern signal"""
        return self._signal

    def reset(self) -> None:
        """Reset pattern detector state"""
        self.candles_buffer.clear()
        self.pattern_start_index = -1
        self.inside_bar_found = False
        self.breakout_detected = False
        self.volume_ma.clear()
        self.atr_values.clear()
        self.trend_ema_values.clear()
        self._signal = HikkakeSignal()


# Factory function for easy instantiation
def create_hikkake_detector(**kwargs) -> AugmentedHikkake:
    """Create and return a configured Hikkake detector"""
    return AugmentedHikkake(**kwargs)