"""Consolidated Pattern Recognition Indicators

This module contains all candlestick pattern recognition indicators consolidated from multiple files:
- Single candle patterns (Hammer, Doji, Marubozu, Shooting Star, etc.)
- Two candle patterns (Engulfing, Harami, Piercing Line, Dark Cloud Cover, etc.)
- Three candle patterns (Morning/Evening Star, Three Soldiers/Crows, etc.)
- Four+ candle patterns (Complex patterns and formations)

All patterns support:
- Volume weighting for institutional analysis
- Smart money flow detection
- Pattern reliability scoring
- Risk-reward ratio calculations
- Multi-timeframe confirmation
- Performance optimization for HFT environments

Author: Vincent S. Pereira
Version: 1.0.0 (Consolidated)
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, List, Any, Tuple, Union
from datetime import datetime
from collections import deque
from enum import Enum
from dataclasses import dataclass
import logging

from .core_indicator_base import (
    AugmentedIndicator,
    IndicatorConfig,
    IndicatorResult,
    IndicatorSignal,
    IndicatorType,
    SignalType,
    MarketRegime,
    RiskLevel,
    performance_monitor,
    robust_calculation,
    memory_efficient
)

logger = logging.getLogger(__name__)

# ===========================================
# PATTERN ENUMS AND DATA CLASSES
# ===========================================

class PatternType(Enum):
    """Pattern classification types"""
    REVERSAL = "reversal"
    CONTINUATION = "continuation"
    NEUTRAL = "neutral"
    INDECISION = "indecision"

class PatternStrength(Enum):
    """Pattern strength classification"""
    VERY_WEAK = "very_weak"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"

class VolumeProfile(Enum):
    """Volume profile classification"""
    LOW_VOLUME = "low_volume"
    NORMAL_VOLUME = "normal_volume"
    HIGH_VOLUME = "high_volume"
    INSTITUTIONAL_VOLUME = "institutional_volume"
    CLIMAX_VOLUME = "climax_volume"

@dataclass
class PatternAnalysis:
    """Comprehensive pattern analysis"""
    pattern_name: str
    pattern_type: PatternType
    detected: bool
    confidence: float
    strength: PatternStrength
    volume_profile: VolumeProfile
    volume_confirmation: float
    smart_money_involvement: float
    institutional_bias: str
    risk_reward_ratio: float
    target_price: Optional[float]
    stop_loss: Optional[float]
    pattern_reliability: float
    market_regime: MarketRegime
    timestamp: datetime

class CandleProperties:
    """Enhanced candle properties for pattern analysis"""
    def __init__(self, open_price: float, high: float, low: float, close: float, volume: float):
        self.open_price = open_price
        self.high = high
        self.low = low
        self.close_price = close
        self.volume = volume
        # Aliases for compatibility with detection logic
        self.open = open_price
        self.close = close
        
        # Calculate basic properties
        self.body_size = abs(close - open_price)
        self.upper_shadow = high - max(open_price, close)
        self.lower_shadow = min(open_price, close) - low
        self.total_range = high - low
        self.body_ratio = self.body_size / self.total_range if self.total_range > 0 else 0
        
        # Determine candle type
        self.is_bullish = close > open_price
        self.is_bearish = close < open_price
        self.is_doji = self.body_size <= (self.total_range * 0.1)

# Pattern reliability scores based on historical performance
PATTERN_RELIABILITY = {
    'hammer': 0.72,
    'inverted_hammer': 0.65,
    'shooting_star': 0.68,
    'hanging_man': 0.63,
    'doji': 0.55,
    'marubozu': 0.70,
    'engulfing_bullish': 0.75,
    'engulfing_bearish': 0.73,
    'harami_bullish': 0.62,
    'harami_bearish': 0.60,
    'piercing_line': 0.68,
    'dark_cloud_cover': 0.66,
    'morning_star': 0.78,
    'evening_star': 0.76,
    'three_white_soldiers': 0.74,
    'three_black_crows': 0.72,
    'upside_tasuki_gap': 0.65,
    'bullish_hikkake': 0.60,
    'mat_hold': 0.70
}

# ===========================================
# CONSOLIDATED PATTERN DETECTOR
# ===========================================

class ConsolidatedPatternDetector(AugmentedIndicator):
    """Consolidated Pattern Recognition Indicator
    
    Features:
    - All major candlestick patterns in one class
    - Volume-weighted pattern analysis
    - Smart money flow detection
    - Institutional bias calculation
    - Risk-reward optimization
    - Multi-timeframe confirmation
    """
    
    def __init__(self, config: IndicatorConfig, volume_lookback: int = 20, name: str = "PatternDetector"):
        super().__init__(config)
        self.indicator_type = IndicatorType.PATTERN
        
        self.volume_lookback = volume_lookback
        self.pattern_reliability = PATTERN_RELIABILITY
        
        # Pattern detection history
        self.detected_patterns = deque(maxlen=config.memory_limit if config.enable_hft_optimizations else 100)
        self.volume_history = deque(maxlen=volume_lookback)
        # Maintain candle history for multi-candle patterns
        self.candle_history = deque(maxlen=config.memory_limit if getattr(config, 'enable_hft_optimizations', False) else 100)
        
    def reset(self) -> None:
        """Reset detector state and inherited buffers for reuse."""
        try:
            super().reset()
        except Exception:
            pass
        # Clear local histories and caches
        try:
            self.detected_patterns.clear()
        except Exception:
            pass
        try:
            self.volume_history.clear()
        except Exception:
            pass
        try:
            self.candle_history.clear()
        except Exception:
            pass
        self._latest_pattern = None
        self._last_signal = None
        self._last_result = None
        # Reset regime and institutional metrics if present
        if hasattr(self, 'current_regime'):
            self.current_regime = MarketRegime.UNKNOWN
        if hasattr(self, 'regime_confidence'):
            self.regime_confidence = 0.0
        if hasattr(self, 'order_flow_imbalance'):
            self.order_flow_imbalance = 0.0
        if hasattr(self, 'institutional_bias'):
            self.institutional_bias = 0.0
        if hasattr(self, 'anomaly_score'):
            self.anomaly_score = 0.0
        if hasattr(self, 'behavioral_bias'):
            self.behavioral_bias = 0.0
        if hasattr(self, 'model_confidence'):
            self.model_confidence = 0.5
        if hasattr(self, 'auto_stop_loss'):
            self.auto_stop_loss = None
        if hasattr(self, 'auto_take_profit'):
            self.auto_take_profit = None
        if hasattr(self, 'position_sizing_factor'):
            self.position_sizing_factor = 1.0
        
    def _calculate_volume_weighted_value(self) -> float:
        """Provide a representative value for base class volume-weighted update."""
        try:
            last = self.detected_patterns[-1]
            return float(getattr(last, 'confidence', 0.0))
        except Exception:
            return 0.0
        
    @performance_monitor
    @memory_efficient()
    @robust_calculation(default_value=None)
    def calculate(self, price: float, volume: float, timestamp: datetime, 
                 ohlc_data: Optional[Dict[str, float]] = None) -> Optional[IndicatorResult]:
        """Main pattern detection method"""
        if not ohlc_data:
            return None
            
        self._add_data_point(price, volume, timestamp)
        self.volume_history.append(volume)
        
        # Create and record current candle
        current_candle = CandleProperties(
            ohlc_data['open'], ohlc_data['high'], 
            ohlc_data['low'], ohlc_data['close'], volume
        )
        # Maintain candle history for multi-candle pattern detection
        if not hasattr(self, 'candle_history'):
            self.candle_history = deque(maxlen=self.config.memory_limit if getattr(self.config, 'enable_hft_optimizations', False) else 100)
        self.candle_history.append(current_candle)
        
        # Detect all patterns
        detected_patterns = []
        
        # Single candle patterns
        detected_patterns.extend(self._detect_single_candle_patterns(current_candle, timestamp))
        
        # Two candle patterns (if we have enough data)
        if len(self.candle_history) >= 2:
            detected_patterns.extend(self._detect_two_candle_patterns(timestamp))
        
        # Three candle patterns (if we have enough data)
        if len(self.candle_history) >= 3:
            detected_patterns.extend(self._detect_three_candle_patterns(timestamp))
        if len(self.candle_history) >= 4:
            detected_patterns.extend(self._detect_four_candle_patterns(timestamp))
        if len(self.candle_history) >= 5:
            detected_patterns.extend(self._detect_five_candle_patterns(timestamp))
        
        # Filter and rank patterns by confidence
        significant_patterns = [p for p in detected_patterns if p.detected and p.confidence > 0.5]
        
        if not significant_patterns:
            return None
        
        # Get the highest confidence pattern
        best_pattern = max(significant_patterns, key=lambda x: x.confidence)
        
        # Track detection history
        self.detected_patterns.append(best_pattern)
        
        # Generate enriched institutional signal using subclass hook
        self._latest_pattern = best_pattern
        indicator_signal = self._generate_institutional_signal(
            value=float(best_pattern.confidence),
            timestamp=timestamp
        )
        
        return IndicatorResult(
            value=best_pattern.confidence,
            signal=indicator_signal,
            confidence=best_pattern.confidence,
            metadata={
                'pattern_name': best_pattern.pattern_name,
                'pattern_type': best_pattern.pattern_type.value,
                'strength': best_pattern.strength.value,
                'volume_profile': best_pattern.volume_profile.value,
                'smart_money_involvement': best_pattern.smart_money_involvement,
                'institutional_bias': best_pattern.institutional_bias,
                'risk_reward_ratio': best_pattern.risk_reward_ratio,
                'target_price': best_pattern.target_price,
                'stop_loss': best_pattern.stop_loss,
                'all_patterns': [{
                    'name': p.pattern_name,
                    'confidence': p.confidence,
                    'type': p.pattern_type.value
                } for p in significant_patterns]
            },
            timestamp=timestamp
        )
    
    def _detect_single_candle_patterns(self, candle: CandleProperties, timestamp: datetime) -> List[PatternAnalysis]:
        """Detect all single candle patterns"""
        patterns = []
        
        # Hammer pattern
        hammer_result = self._detect_hammer(candle, timestamp)
        if hammer_result:
            patterns.append(hammer_result)
        
        # Inverted Hammer pattern
        inverted_hammer_result = self._detect_inverted_hammer(candle, timestamp)
        if inverted_hammer_result:
            patterns.append(inverted_hammer_result)
        
        # Shooting Star pattern
        shooting_star_result = self._detect_shooting_star(candle, timestamp)
        if shooting_star_result:
            patterns.append(shooting_star_result)
        
        # Doji pattern
        doji_result = self._detect_doji(candle, timestamp)
        if doji_result:
            patterns.append(doji_result)
        
        # Marubozu pattern
        marubozu_result = self._detect_marubozu(candle, timestamp)
        if marubozu_result:
            patterns.append(marubozu_result)
        
        # Additional single-candle patterns
        hanging_man_result = self._detect_hanging_man(candle, timestamp)
        if hanging_man_result:
            patterns.append(hanging_man_result)
        
        spinning_top_result = self._detect_spinning_top(candle, timestamp)
        if spinning_top_result:
            patterns.append(spinning_top_result)
        
        long_legged_doji_result = self._detect_long_legged_doji(candle, timestamp)
        if long_legged_doji_result:
            patterns.append(long_legged_doji_result)
        
        dragonfly_doji_result = self._detect_dragonfly_doji(candle, timestamp)
        if dragonfly_doji_result:
            patterns.append(dragonfly_doji_result)
        
        gravestone_doji_result = self._detect_gravestone_doji(candle, timestamp)
        if gravestone_doji_result:
            patterns.append(gravestone_doji_result)
        
        four_price_doji_result = self._detect_four_price_doji(candle, timestamp)
        if four_price_doji_result:
            patterns.append(four_price_doji_result)
        
        # Advanced single-candle patterns
        belt_hold_bullish_result = self._detect_belt_hold_bullish(candle, timestamp)
        if belt_hold_bullish_result:
            patterns.append(belt_hold_bullish_result)
        
        belt_hold_bearish_result = self._detect_belt_hold_bearish(candle, timestamp)
        if belt_hold_bearish_result:
            patterns.append(belt_hold_bearish_result)
        
        rickshaw_man_result = self._detect_rickshaw_man(candle, timestamp)
        if rickshaw_man_result:
            patterns.append(rickshaw_man_result)
        
        high_wave_candle_result = self._detect_high_wave_candle(candle, timestamp)
        if high_wave_candle_result:
            patterns.append(high_wave_candle_result)
        
        return patterns
    
    def _detect_two_candle_patterns(self, timestamp: datetime) -> List[PatternAnalysis]:
        """Detect all two candle patterns"""
        patterns = []
        
        if len(self.prices) < 2 or len(self.candle_history) < 2:
            return patterns
        
        current_candle = self.candle_history[-1]
        prev_candle = self.candle_history[-2]
        
        # Engulfing patterns
        bullish_engulfing = self._detect_bullish_engulfing(prev_candle, current_candle, timestamp)
        if bullish_engulfing:
            patterns.append(bullish_engulfing)
        
        bearish_engulfing = self._detect_bearish_engulfing(prev_candle, current_candle, timestamp)
        if bearish_engulfing:
            patterns.append(bearish_engulfing)
        
        # Harami patterns
        bullish_harami = self._detect_bullish_harami(prev_candle, current_candle, timestamp)
        if bullish_harami:
            patterns.append(bullish_harami)
        
        bearish_harami = self._detect_bearish_harami(prev_candle, current_candle, timestamp)
        if bearish_harami:
            patterns.append(bearish_harami)
        
        # Piercing Line
        piercing_line = self._detect_piercing_line(prev_candle, current_candle, timestamp)
        if piercing_line:
            patterns.append(piercing_line)
        
        # Dark Cloud Cover
        dark_cloud = self._detect_dark_cloud_cover(prev_candle, current_candle, timestamp)
        if dark_cloud:
            patterns.append(dark_cloud)
        
        # Tweezer patterns
        tweezer_top = self._detect_tweezer_top(prev_candle, current_candle, timestamp)
        if tweezer_top:
            patterns.append(tweezer_top)
        
        tweezer_bottom = self._detect_tweezer_bottom(prev_candle, current_candle, timestamp)
        if tweezer_bottom:
            patterns.append(tweezer_bottom)
        
        # Kicking patterns
        kicking_bullish = self._detect_kicking_bullish(prev_candle, current_candle, timestamp)
        if kicking_bullish:
            patterns.append(kicking_bullish)
        
        kicking_bearish = self._detect_kicking_bearish(prev_candle, current_candle, timestamp)
        if kicking_bearish:
            patterns.append(kicking_bearish)
        
        return patterns
    
    def _detect_three_candle_patterns(self, timestamp: datetime) -> List[PatternAnalysis]:
        """Detect all three candle patterns"""
        patterns = []
        
        if len(self.prices) < 3 or len(self.candle_history) < 3:
            return patterns
        
        candle1 = self.candle_history[-3]  # First candle
        candle2 = self.candle_history[-2]  # Middle candle
        candle3 = self.candle_history[-1]  # Current candle
        
        # Morning Star
        morning_star = self._detect_morning_star(candle1, candle2, candle3, timestamp)
        if morning_star:
            patterns.append(morning_star)
        
        # Evening Star
        evening_star = self._detect_evening_star(candle1, candle2, candle3, timestamp)
        if evening_star:
            patterns.append(evening_star)
        
        # Three White Soldiers
        three_white_soldiers = self._detect_three_white_soldiers(candle1, candle2, candle3, timestamp)
        if three_white_soldiers:
            patterns.append(three_white_soldiers)
        
        # Three Black Crows
        three_black_crows = self._detect_three_black_crows(candle1, candle2, candle3, timestamp)
        if three_black_crows:
            patterns.append(three_black_crows)
        
        # Abandoned Baby patterns
        abandoned_baby_bullish = self._detect_abandoned_baby_bullish(candle1, candle2, candle3, timestamp)
        if abandoned_baby_bullish:
            patterns.append(abandoned_baby_bullish)
        
        abandoned_baby_bearish = self._detect_abandoned_baby_bearish(candle1, candle2, candle3, timestamp)
        if abandoned_baby_bearish:
            patterns.append(abandoned_baby_bearish)
        
        # Three Inside Up/Down
        three_inside_up = self._detect_three_inside_up(candle1, candle2, candle3, timestamp)
        if three_inside_up:
            patterns.append(three_inside_up)
        
        three_inside_down = self._detect_three_inside_down(candle1, candle2, candle3, timestamp)
        if three_inside_down:
            patterns.append(three_inside_down)
        
        # Three Outside Up/Down
        three_outside_up = self._detect_three_outside_up(candle1, candle2, candle3, timestamp)
        if three_outside_up:
            patterns.append(three_outside_up)
        
        three_outside_down = self._detect_three_outside_down(candle1, candle2, candle3, timestamp)
        if three_outside_down:
            patterns.append(three_outside_down)

        upside_tasuki_gap = self._detect_upside_tasuki_gap(candle1, candle2, candle3, timestamp)
        if upside_tasuki_gap:
            patterns.append(upside_tasuki_gap)
        
        return patterns
    
    def _detect_four_candle_patterns(self, timestamp: datetime) -> List[PatternAnalysis]:
        patterns = []
        if len(self.candle_history) < 4:
            return patterns
        
        candle1 = self.candle_history[-4]
        candle2 = self.candle_history[-3]
        candle3 = self.candle_history[-2]
        candle4 = self.candle_history[-1]
        
        bullish_hikkake = self._detect_bullish_hikkake(candle1, candle2, candle3, candle4, timestamp)
        if bullish_hikkake:
            patterns.append(bullish_hikkake)
        
        return patterns
    
    def _detect_five_candle_patterns(self, timestamp: datetime) -> List[PatternAnalysis]:
        patterns = []
        if len(self.candle_history) < 5:
            return patterns
        
        candle1 = self.candle_history[-5]
        candle2 = self.candle_history[-4]
        candle3 = self.candle_history[-3]
        candle4 = self.candle_history[-2]
        candle5 = self.candle_history[-1]
        
        mat_hold = self._detect_mat_hold(candle1, candle2, candle3, candle4, candle5, timestamp)
        if mat_hold:
            patterns.append(mat_hold)
        
        return patterns
    
    def _detect_hammer(self, candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect hammer pattern with volume analysis"""
        # Hammer criteria
        is_hammer = (
            candle.lower_shadow >= 2 * candle.body_size and
            candle.upper_shadow <= 0.15 * candle.total_range and
            candle.body_ratio <= 0.35
        )
        
        if not is_hammer:
            return None
        
        # Calculate confidence with volume weighting
        base_confidence = 0.65
        volume_boost = self._calculate_volume_boost()
        smart_money_score = self._calculate_smart_money_score()
        
        confidence = min(base_confidence + volume_boost + smart_money_score, 1.0)
        
        return PatternAnalysis(
            pattern_name="Hammer",
            pattern_type=PatternType.REVERSAL,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=volume_boost,
            smart_money_involvement=smart_money_score,
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=2.5,  # Typical hammer risk-reward
            target_price=None,  # Would calculate based on ATR
            stop_loss=None,     # Would calculate based on ATR
            pattern_reliability=self.pattern_reliability.get('hammer', 0.72),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_inverted_hammer(self, candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect inverted hammer pattern"""
        is_inverted_hammer = (
            candle.upper_shadow >= 2 * candle.body_size and
            candle.lower_shadow <= 0.15 * candle.total_range and
            candle.body_ratio <= 0.35
        )
        
        if not is_inverted_hammer:
            return None
        
        confidence = min(0.60 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Inverted_Hammer",
            pattern_type=PatternType.REVERSAL,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=2.0,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('inverted_hammer', 0.65),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_shooting_star(self, candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect shooting star pattern"""
        is_shooting_star = (
            candle.upper_shadow >= 2 * candle.body_size and
            candle.lower_shadow <= 0.15 * candle.total_range and
            candle.body_ratio <= 0.35 and
            self._is_in_uptrend()  # Should appear in uptrend
        )
        
        if not is_shooting_star:
            return None
        
        confidence = min(0.63 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Shooting_Star",
            pattern_type=PatternType.REVERSAL,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=2.2,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('shooting_star', 0.68),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_doji(self, candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect doji pattern"""
        if not candle.is_doji:
            return None
        
        confidence = min(0.50 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Doji",
            pattern_type=PatternType.INDECISION,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias="neutral",
            risk_reward_ratio=1.5,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('doji', 0.55),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_marubozu(self, candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect marubozu pattern"""
        is_marubozu = (
            candle.body_ratio >= 0.95 and
            candle.upper_shadow <= 0.02 * candle.total_range and
            candle.lower_shadow <= 0.02 * candle.total_range
        )
        
        if not is_marubozu:
            return None
        
        confidence = min(0.68 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Marubozu",
            pattern_type=PatternType.CONTINUATION,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=2.0,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('marubozu', 0.70),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_hanging_man(self, candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect hanging man pattern (bearish hammer at top of uptrend)"""
        # Same criteria as hammer but in uptrend context
        is_hanging_man = (
            candle.lower_shadow >= 2 * candle.body_size and
            candle.upper_shadow <= 0.1 * candle.body_size and
            candle.body_size > 0 and
            self._is_in_uptrend()  # Key difference from hammer
        )
        
        if not is_hanging_man:
            return None
        
        confidence = min(0.70 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Hanging_Man",
            pattern_type=PatternType.REVERSAL,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=2.5,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('hanging_man', 0.72),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_spinning_top(self, candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect spinning top pattern"""
        is_spinning_top = (
            candle.body_size <= 0.3 * candle.total_range and
            candle.upper_shadow >= 0.3 * candle.total_range and
            candle.lower_shadow >= 0.3 * candle.total_range and
            candle.body_size > 0
        )
        
        if not is_spinning_top:
            return None
        
        confidence = min(0.60 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Spinning_Top",
            pattern_type=PatternType.INDECISION,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=1.8,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('spinning_top', 0.58),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_long_legged_doji(self, candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect long-legged doji pattern"""
        is_long_legged_doji = (
            candle.is_doji and
            candle.upper_shadow >= 0.4 * candle.total_range and
            candle.lower_shadow >= 0.4 * candle.total_range
        )
        
        if not is_long_legged_doji:
            return None
        
        confidence = min(0.68 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Long_Legged_Doji",
            pattern_type=PatternType.INDECISION,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=2.0,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('long_legged_doji', 0.65),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_dragonfly_doji(self, candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect dragonfly doji pattern"""
        is_dragonfly_doji = (
            candle.is_doji and
            candle.lower_shadow >= 2 * candle.body_size and
            candle.upper_shadow <= 0.1 * candle.total_range
        )
        
        if not is_dragonfly_doji:
            return None
        
        confidence = min(0.72 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Dragonfly_Doji",
            pattern_type=PatternType.REVERSAL,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=2.4,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('dragonfly_doji', 0.70),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_gravestone_doji(self, candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect gravestone doji pattern"""
        is_gravestone_doji = (
            candle.is_doji and
            candle.upper_shadow >= 2 * candle.body_size and
            candle.lower_shadow <= 0.1 * candle.total_range
        )
        
        if not is_gravestone_doji:
            return None
        
        confidence = min(0.72 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Gravestone_Doji",
            pattern_type=PatternType.REVERSAL,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=2.4,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('gravestone_doji', 0.70),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_four_price_doji(self, candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect four price doji pattern (all OHLC equal)"""
        is_four_price_doji = (
            candle.open == candle.high == candle.low == candle.close
        )
        
        if not is_four_price_doji:
            return None
        
        confidence = min(0.85 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Four_Price_Doji",
            pattern_type=PatternType.INDECISION,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=1.5,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('four_price_doji', 0.80),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    # ===========================================
    # TWO-CANDLE PATTERN DETECTION METHODS
    # ===========================================
    
    def _detect_bullish_engulfing(self, prev_candle: CandleProperties, current_candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect bullish engulfing pattern"""
        is_bullish_engulfing = (
            prev_candle.is_bearish and
            current_candle.is_bullish and
            current_candle.open < prev_candle.close and
            current_candle.close > prev_candle.open and
            current_candle.body_size > prev_candle.body_size
        )
        
        if not is_bullish_engulfing:
            return None
        
        confidence = min(0.75 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Bullish_Engulfing",
            pattern_type=PatternType.REVERSAL,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=2.8,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('bullish_engulfing', 0.78),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_bearish_engulfing(self, prev_candle: CandleProperties, current_candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect bearish engulfing pattern"""
        is_bearish_engulfing = (
            prev_candle.is_bullish and
            current_candle.is_bearish and
            current_candle.open > prev_candle.close and
            current_candle.close < prev_candle.open and
            current_candle.body_size > prev_candle.body_size
        )
        
        if not is_bearish_engulfing:
            return None
        
        confidence = min(0.75 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Bearish_Engulfing",
            pattern_type=PatternType.REVERSAL,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=2.8,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('bearish_engulfing', 0.78),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_bullish_harami(self, prev_candle: CandleProperties, current_candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect bullish harami pattern"""
        is_bullish_harami = (
            prev_candle.is_bearish and
            current_candle.is_bullish and
            current_candle.open > prev_candle.close and
            current_candle.close < prev_candle.open and
            current_candle.body_size < prev_candle.body_size * 0.8
        )
        
        if not is_bullish_harami:
            return None
        
        confidence = min(0.65 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Bullish_Harami",
            pattern_type=PatternType.REVERSAL,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=2.3,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('bullish_harami', 0.68),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_bearish_harami(self, prev_candle: CandleProperties, current_candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect bearish harami pattern"""
        is_bearish_harami = (
            prev_candle.is_bullish and
            current_candle.is_bearish and
            current_candle.open < prev_candle.close and
            current_candle.close > prev_candle.open and
            current_candle.body_size < prev_candle.body_size * 0.8
        )
        
        if not is_bearish_harami:
            return None
        
        confidence = min(0.65 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Bearish_Harami",
            pattern_type=PatternType.REVERSAL,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=2.3,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('bearish_harami', 0.68),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_piercing_line(self, prev_candle: CandleProperties, current_candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect piercing line pattern"""
        is_piercing_line = (
            prev_candle.is_bearish and
            current_candle.is_bullish and
            current_candle.open < prev_candle.low and
            current_candle.close > (prev_candle.open + prev_candle.close) / 2 and
            current_candle.close < prev_candle.open
        )
        
        if not is_piercing_line:
            return None
        
        confidence = min(0.70 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Piercing_Line",
            pattern_type=PatternType.REVERSAL,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=2.5,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('piercing_line', 0.72),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_dark_cloud_cover(self, prev_candle: CandleProperties, current_candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect dark cloud cover pattern"""
        is_dark_cloud = (
            prev_candle.is_bullish and
            current_candle.is_bearish and
            current_candle.open > prev_candle.high and
            current_candle.close < (prev_candle.open + prev_candle.close) / 2 and
            current_candle.close > prev_candle.open
        )
        
        if not is_dark_cloud:
            return None
        
        confidence = min(0.70 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Dark_Cloud_Cover",
            pattern_type=PatternType.REVERSAL,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=2.5,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('dark_cloud_cover', 0.72),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_tweezer_top(self, prev_candle: CandleProperties, current_candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect tweezer top pattern"""
        high_tolerance = 0.002  # 0.2% tolerance
        is_tweezer_top = (
            abs(prev_candle.high - current_candle.high) / prev_candle.high < high_tolerance and
            prev_candle.is_bullish and
            current_candle.is_bearish and
            self._is_in_uptrend()
        )
        
        if not is_tweezer_top:
            return None
        
        confidence = min(0.68 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Tweezer_Top",
            pattern_type=PatternType.REVERSAL,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=2.2,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('tweezer_top', 0.65),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_tweezer_bottom(self, prev_candle: CandleProperties, current_candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect tweezer bottom pattern"""
        low_tolerance = 0.002  # 0.2% tolerance
        is_tweezer_bottom = (
            abs(prev_candle.low - current_candle.low) / prev_candle.low < low_tolerance and
            prev_candle.is_bearish and
            current_candle.is_bullish and
            not self._is_in_uptrend()
        )
        
        if not is_tweezer_bottom:
            return None
        
        confidence = min(0.68 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Tweezer_Bottom",
            pattern_type=PatternType.REVERSAL,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=2.2,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('tweezer_bottom', 0.65),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_kicking_bullish(self, prev_candle: CandleProperties, current_candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect bullish kicking pattern"""
        is_kicking_bullish = (
            prev_candle.is_bearish and
            current_candle.is_bullish and
            prev_candle.body_ratio > 0.9 and  # Marubozu-like
            current_candle.body_ratio > 0.9 and  # Marubozu-like
            current_candle.open > prev_candle.close  # Gap up
        )
        
        if not is_kicking_bullish:
            return None
        
        confidence = min(0.80 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Kicking_Bullish",
            pattern_type=PatternType.REVERSAL,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=3.0,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('kicking_bullish', 0.82),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_kicking_bearish(self, prev_candle: CandleProperties, current_candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect bearish kicking pattern"""
        is_kicking_bearish = (
            prev_candle.is_bullish and
            current_candle.is_bearish and
            prev_candle.body_ratio > 0.9 and  # Marubozu-like
            current_candle.body_ratio > 0.9 and  # Marubozu-like
            current_candle.open < prev_candle.close  # Gap down
        )
        
        if not is_kicking_bearish:
            return None
        
        confidence = min(0.80 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Kicking_Bearish",
            pattern_type=PatternType.REVERSAL,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=3.0,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('kicking_bearish', 0.82),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    # ===========================================
    # THREE-CANDLE PATTERN DETECTION METHODS
    # ===========================================
    
    def _detect_morning_star(self, candle1: CandleProperties, candle2: CandleProperties, candle3: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect morning star pattern"""
        is_morning_star = (
            candle1.is_bearish and
            candle2.body_size < candle1.body_size * 0.3 and  # Small body (star)
            candle3.is_bullish and
            candle3.close > (candle1.open + candle1.close) / 2 and
            candle2.high < min(candle1.low, candle3.low)  # Gap down and up
        )
        
        if not is_morning_star:
            return None
        
        confidence = min(0.78 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Morning_Star",
            pattern_type=PatternType.REVERSAL,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=3.2,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('morning_star', 0.85),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_evening_star(self, candle1: CandleProperties, candle2: CandleProperties, candle3: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect evening star pattern"""
        is_evening_star = (
            candle1.is_bullish and
            candle2.body_size < candle1.body_size * 0.3 and  # Small body (star)
            candle3.is_bearish and
            candle3.close < (candle1.open + candle1.close) / 2 and
            candle2.low > max(candle1.high, candle3.high)  # Gap up and down
        )
        
        if not is_evening_star:
            return None
        
        confidence = min(0.78 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Evening_Star",
            pattern_type=PatternType.REVERSAL,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=3.2,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('evening_star', 0.85),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_three_white_soldiers(self, candle1: CandleProperties, candle2: CandleProperties, candle3: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect three white soldiers pattern"""
        is_three_white_soldiers = (
            candle1.is_bullish and candle2.is_bullish and candle3.is_bullish and
            candle2.close > candle1.close and candle3.close > candle2.close and
            candle2.open > candle1.open and candle2.open < candle1.close and
            candle3.open > candle2.open and candle3.open < candle2.close and
            all(c.body_ratio > 0.6 for c in [candle1, candle2, candle3])  # Strong bodies
        )
        
        if not is_three_white_soldiers:
            return None
        
        confidence = min(0.82 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Three_White_Soldiers",
            pattern_type=PatternType.CONTINUATION,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=3.5,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('three_white_soldiers', 0.88),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_three_black_crows(self, candle1: CandleProperties, candle2: CandleProperties, candle3: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect three black crows pattern"""
        is_three_black_crows = (
            candle1.is_bearish and candle2.is_bearish and candle3.is_bearish and
            candle2.close < candle1.close and candle3.close < candle2.close and
            candle2.open < candle1.open and candle2.open > candle1.close and
            candle3.open < candle2.open and candle3.open > candle2.close and
            all(c.body_ratio > 0.6 for c in [candle1, candle2, candle3])  # Strong bodies
        )
        
        if not is_three_black_crows:
            return None
        
        confidence = min(0.82 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Three_Black_Crows",
            pattern_type=PatternType.CONTINUATION,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=3.5,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('three_black_crows', 0.88),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_abandoned_baby_bullish(self, candle1: CandleProperties, candle2: CandleProperties, candle3: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect bullish abandoned baby pattern"""
        is_abandoned_baby_bullish = (
            candle1.is_bearish and
            candle2.is_doji and  # Doji in the middle
            candle3.is_bullish and
            candle2.high < candle1.low and  # Gap down
            candle2.high < candle3.low and  # Gap up
            candle3.close > (candle1.open + candle1.close) / 2
        )
        
        if not is_abandoned_baby_bullish:
            return None
        
        confidence = min(0.85 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Abandoned_Baby_Bullish",
            pattern_type=PatternType.REVERSAL,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=3.8,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('abandoned_baby_bullish', 0.90),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_abandoned_baby_bearish(self, candle1: CandleProperties, candle2: CandleProperties, candle3: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect bearish abandoned baby pattern"""
        is_abandoned_baby_bearish = (
            candle1.is_bullish and
            candle2.is_doji and  # Doji in the middle
            candle3.is_bearish and
            candle2.low > candle1.high and  # Gap up
            candle2.low > candle3.high and  # Gap down
            candle3.close < (candle1.open + candle1.close) / 2
        )
        
        if not is_abandoned_baby_bearish:
            return None
        
        confidence = min(0.85 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Abandoned_Baby_Bearish",
            pattern_type=PatternType.REVERSAL,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=3.8,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('abandoned_baby_bearish', 0.90),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_three_inside_up(self, candle1: CandleProperties, candle2: CandleProperties, candle3: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect three inside up pattern"""
        # First check for harami pattern (first two candles)
        is_harami = (
            candle1.is_bearish and
            candle2.is_bullish and
            candle2.open > candle1.close and
            candle2.close < candle1.open and
            candle2.body_size < candle1.body_size * 0.8
        )
        
        is_three_inside_up = (
            is_harami and
            candle3.is_bullish and
            candle3.close > candle1.open  # Confirmation
        )
        
        if not is_three_inside_up:
            return None
        
        confidence = min(0.75 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Three_Inside_Up",
            pattern_type=PatternType.REVERSAL,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=2.8,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('three_inside_up', 0.78),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_three_inside_down(self, candle1: CandleProperties, candle2: CandleProperties, candle3: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect three inside down pattern"""
        # First check for harami pattern (first two candles)
        is_harami = (
            candle1.is_bullish and
            candle2.is_bearish and
            candle2.open < candle1.close and
            candle2.close > candle1.open and
            candle2.body_size < candle1.body_size * 0.8
        )
        
        is_three_inside_down = (
            is_harami and
            candle3.is_bearish and
            candle3.close < candle1.open  # Confirmation
        )
        
        if not is_three_inside_down:
            return None
        
        confidence = min(0.75 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Three_Inside_Down",
            pattern_type=PatternType.REVERSAL,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=2.8,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('three_inside_down', 0.78),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_three_outside_up(self, candle1: CandleProperties, candle2: CandleProperties, candle3: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect three outside up pattern"""
        # First check for engulfing pattern (first two candles)
        is_engulfing = (
            candle1.is_bearish and
            candle2.is_bullish and
            candle2.open < candle1.close and
            candle2.close > candle1.open and
            candle2.body_size > candle1.body_size
        )
        
        is_three_outside_up = (
            is_engulfing and
            candle3.is_bullish and
            candle3.close > candle2.close  # Confirmation
        )
        
        if not is_three_outside_up:
            return None
        
        confidence = min(0.80 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Three_Outside_Up",
            pattern_type=PatternType.REVERSAL,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=3.0,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('three_outside_up', 0.82),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_three_outside_down(self, candle1: CandleProperties, candle2: CandleProperties, candle3: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect three outside down pattern"""
        # First check for engulfing pattern (first two candles)
        is_engulfing = (
            candle1.is_bullish and
            candle2.is_bearish and
            candle2.open > candle1.close and
            candle2.close < candle1.open and
            candle2.body_size > candle1.body_size
        )
        
        is_three_outside_down = (
            is_engulfing and
            candle3.is_bearish and
            candle3.close < candle2.close  # Confirmation
        )
        
        if not is_three_outside_down:
            return None
        
        confidence = min(0.80 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Three_Outside_Down",
            pattern_type=PatternType.REVERSAL,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=3.0,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('three_outside_down', 0.82),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    # ===========================================
    # ADVANCED PATTERN DETECTION METHODS
    # ===========================================
    
    def _detect_belt_hold_bullish(self, candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect bullish belt hold pattern"""
        is_belt_hold = (
            candle.is_bullish and
            candle.lower_shadow <= 0.05 * candle.total_range and
            candle.body_ratio >= 0.85 and
            candle.open == candle.low
        )
        
        if not is_belt_hold:
            return None
        
        confidence = min(0.68 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Belt_Hold_Bullish",
            pattern_type=PatternType.REVERSAL,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=2.2,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('belt_hold_bullish', 0.65),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_belt_hold_bearish(self, candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect bearish belt hold pattern"""
        is_belt_hold = (
            candle.is_bearish and
            candle.upper_shadow <= 0.05 * candle.total_range and
            candle.body_ratio >= 0.85 and
            candle.open == candle.high
        )
        
        if not is_belt_hold:
            return None
        
        confidence = min(0.68 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Belt_Hold_Bearish",
            pattern_type=PatternType.REVERSAL,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=2.2,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('belt_hold_bearish', 0.65),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_rickshaw_man(self, candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect rickshaw man pattern"""
        is_rickshaw = (
            candle.is_doji and
            candle.upper_shadow >= 0.35 * candle.total_range and
            candle.lower_shadow >= 0.35 * candle.total_range and
            abs(candle.upper_shadow - candle.lower_shadow) <= 0.1 * candle.total_range
        )
        
        if not is_rickshaw:
            return None
        
        confidence = min(0.62 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Rickshaw_Man",
            pattern_type=PatternType.INDECISION,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=1.8,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('rickshaw_man', 0.60),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_high_wave_candle(self, candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        """Detect high wave candle pattern"""
        is_high_wave = (
            candle.body_size <= 0.25 * candle.total_range and
            (candle.upper_shadow >= 0.6 * candle.total_range or candle.lower_shadow >= 0.6 * candle.total_range) and
            candle.total_range > self._get_average_range()
        )
        
        if not is_high_wave:
            return None
        
        confidence = min(0.58 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="High_Wave_Candle",
            pattern_type=PatternType.INDECISION,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=1.6,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('high_wave_candle', 0.55),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_upside_tasuki_gap(self, candle1: CandleProperties, candle2: CandleProperties, candle3: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        if not self._is_in_uptrend():
            return None
            
        is_bullish_gap = candle1.is_bullish and candle2.is_bullish and candle2.open > candle1.close
        is_gap_fill_attempt = candle3.is_bearish and candle3.open < candle2.close and candle3.open > candle2.open and candle3.close > candle1.close and candle3.close < candle2.open
        
        if not (is_bullish_gap and is_gap_fill_attempt):
            return None
            
        confidence = min(0.65 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Upside_Tasuki_Gap",
            pattern_type=PatternType.CONTINUATION,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=2.5,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('upside_tasuki_gap', 0.65),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_bullish_hikkake(self, candle1: CandleProperties, candle2: CandleProperties, candle3: CandleProperties, candle4: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        if self._is_in_uptrend():
            return None
            
        is_inside_bar = candle2.high < candle1.high and candle2.low > candle1.low
        fake_breakdown = candle3.low < candle2.low and candle3.close > candle2.low
        reversal_confirmation = candle4.close > candle3.high
        
        if not (is_inside_bar and fake_breakdown and reversal_confirmation):
            return None
            
        confidence = min(0.60 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Bullish_Hikkake",
            pattern_type=PatternType.REVERSAL,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=2.0,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('bullish_hikkake', 0.60),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _detect_mat_hold(self, candle1: CandleProperties, candle2: CandleProperties, candle3: CandleProperties, candle4: CandleProperties, candle5: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
        if not self._is_in_uptrend():
            return None
            
        is_long_bull = candle1.is_bullish and candle1.body_size > 0.7 * candle1.total_range
        small_downs = all(c.is_bearish and c.body_size < 0.3 * candle1.body_size for c in [candle2, candle3, candle4]) and all(c.close > candle1.open for c in [candle2, candle3, candle4])
        strong_close = candle5.is_bullish and candle5.close > max(c.high for c in [candle1, candle2, candle3, candle4])
        
        if not (is_long_bull and small_downs and strong_close):
            return None
            
        confidence = min(0.70 + self._calculate_volume_boost() + self._calculate_smart_money_score(), 1.0)
        
        return PatternAnalysis(
            pattern_name="Mat_Hold",
            pattern_type=PatternType.CONTINUATION,
            detected=True,
            confidence=confidence,
            strength=self._determine_pattern_strength(confidence),
            volume_profile=self._classify_volume_profile(),
            volume_confirmation=self._calculate_volume_boost(),
            smart_money_involvement=self._calculate_smart_money_score(),
            institutional_bias=self._calculate_institutional_bias(),
            risk_reward_ratio=3.0,
            target_price=None,
            stop_loss=None,
            pattern_reliability=self.pattern_reliability.get('mat_hold', 0.70),
            market_regime=self._detect_market_regime(),
            timestamp=timestamp
        )
    
    def _get_average_range(self) -> float:
        """Calculate average range of recent candles"""
        if len(self.candle_history) < 10:
            return 0.0
        
        recent_ranges = [candle.total_range for candle in self.candle_history[-10:]]
        return sum(recent_ranges) / len(recent_ranges)
    
    # ===========================================
    # HELPER METHODS
    # ===========================================
    
    def _calculate_volume_boost(self) -> float:
        """Calculate volume-based confidence boost"""
        if len(self.volume_history) < 2:
            return 0.0
        
        current_volume = self.volume_history[-1]
        avg_volume = np.mean(list(self.volume_history)[:-1])
        
        if avg_volume == 0:
            return 0.0
        
        volume_ratio = current_volume / avg_volume
        return min(volume_ratio / 3.0, 0.25)  # Cap at 0.25
    
    def _calculate_smart_money_score(self) -> float:
        """Calculate smart money involvement score"""
        # Simplified smart money detection
        if len(self.volume_history) < self.volume_lookback:
            return 0.0
        
        current_volume = self.volume_history[-1]
        volume_percentile = np.percentile(list(self.volume_history), 80)
        
        if current_volume > volume_percentile:
            return 0.15
        return 0.0
    
    def _classify_volume_profile(self) -> VolumeProfile:
        """Classify current volume profile"""
        if len(self.volume_history) < 2:
            return VolumeProfile.NORMAL_VOLUME
        
        current_volume = self.volume_history[-1]
        avg_volume = np.mean(list(self.volume_history)[:-1])
        
        if avg_volume == 0:
            return VolumeProfile.NORMAL_VOLUME
        
        ratio = current_volume / avg_volume
        
        if ratio > 3.0:
            return VolumeProfile.CLIMAX_VOLUME
        elif ratio > 2.0:
            return VolumeProfile.INSTITUTIONAL_VOLUME
        elif ratio > 1.5:
            return VolumeProfile.HIGH_VOLUME
        elif ratio < 0.5:
            return VolumeProfile.LOW_VOLUME
        else:
            return VolumeProfile.NORMAL_VOLUME
    
    def _determine_pattern_strength(self, confidence: float) -> PatternStrength:
        """Determine pattern strength based on confidence"""
        if confidence >= 0.9:
            return PatternStrength.VERY_STRONG
        elif confidence >= 0.75:
            return PatternStrength.STRONG
        elif confidence >= 0.6:
            return PatternStrength.MODERATE
        elif confidence >= 0.45:
            return PatternStrength.WEAK
        else:
            return PatternStrength.VERY_WEAK
    
    def _calculate_institutional_bias(self) -> str:
        """Calculate institutional bias"""
        smart_money_score = self._calculate_smart_money_score()
        volume_profile = self._classify_volume_profile()
        
        if smart_money_score > 0.1 and volume_profile in [VolumeProfile.INSTITUTIONAL_VOLUME, VolumeProfile.CLIMAX_VOLUME]:
            return "strong_institutional"
        elif volume_profile == VolumeProfile.HIGH_VOLUME:
            return "moderate_institutional"
        else:
            return "retail"
    
    def _is_in_uptrend(self) -> bool:
        """Simple uptrend detection"""
        if len(self.prices) < 5:
            return False
        
        recent_prices = list(self.prices)[-5:]
        return recent_prices[-1] > recent_prices[0]
    
    def _pattern_to_signal(self, pattern: PatternAnalysis) -> SignalType:
        """Convert pattern to signal type"""
        if pattern.pattern_type == PatternType.REVERSAL:
            if pattern.pattern_name in ['Hammer', 'Inverted_Hammer']:
                return SignalType.BUY
            elif pattern.pattern_name in ['Shooting_Star', 'Hanging_Man']:
                return SignalType.SELL
        elif pattern.pattern_type == PatternType.CONTINUATION:
            if pattern.institutional_bias in ['bullish', 'strong_bullish']:
                return SignalType.BUY
            elif pattern.institutional_bias in ['bearish', 'strong_bearish']:
                return SignalType.SELL
        
        return SignalType.HOLD

    # Enhanced signal hook used by base class
    def _generate_enhanced_signal(self, value: float, timestamp: datetime) -> IndicatorSignal:
        """Subclass hook used by base to construct a technical signal before institutional enrichment."""
        pattern = getattr(self, '_latest_pattern', None)
        if pattern is None:
            return IndicatorSignal(
                signal_type=SignalType.NEUTRAL,
                strength=0.0,
                confidence=0.5,
                timestamp=timestamp,
                value=value,
            )
        strength_map = {
            PatternStrength.VERY_WEAK: 0.2,
            PatternStrength.WEAK: 0.4,
            PatternStrength.MODERATE: 0.6,
            PatternStrength.STRONG: 0.8,
            PatternStrength.VERY_STRONG: 1.0,
        }
        strength_numeric = strength_map.get(pattern.strength, 0.5)
        volume_confirmed = bool(
            pattern.volume_profile in {VolumeProfile.HIGH_VOLUME, VolumeProfile.INSTITUTIONAL_VOLUME, VolumeProfile.CLIMAX_VOLUME}
            or float(pattern.volume_confirmation) > 0.5
        )
        sig = IndicatorSignal(
            signal_type=self._pattern_to_signal(pattern),
            strength=strength_numeric,
            confidence=float(pattern.confidence),
            timestamp=timestamp,
            value=float(pattern.confidence),
            volume_confirmation=volume_confirmed,
            volume_strength=float(pattern.volume_confirmation),
            market_regime=getattr(self, 'current_regime', MarketRegime.UNKNOWN),
            regime_confidence=getattr(self, 'regime_confidence', 0.0),
            normalized_value=float(pattern.confidence),
        )
        # Attach pattern metadata for downstream consumers
        try:
            md = getattr(sig, 'metadata', {}) or {}
            md.update({
                'pattern_name': pattern.pattern_name,
                'pattern_type': pattern.pattern_type.value,
                'pattern_reliability': pattern.pattern_reliability,
                'volume_profile': pattern.volume_profile.value,
                'smart_money_involvement': pattern.smart_money_involvement,
                'institutional_bias': pattern.institutional_bias,
                'risk_reward_ratio': pattern.risk_reward_ratio,
                'target_price': pattern.target_price,
                'stop_loss': pattern.stop_loss,
            })
            sig.metadata = md
        except Exception:
            pass
        return sig

# ===========================================
# FACTORY FUNCTIONS
# ===========================================


def create_pattern_detector(config: IndicatorConfig, **kwargs) -> ConsolidatedPatternDetector:
    """Factory function to create pattern detector"""
    return ConsolidatedPatternDetector(config, **kwargs)

# Export list
__all__ = [
    'ConsolidatedPatternDetector',
    'PatternAnalysis',
    'PatternType',
    'PatternStrength',
    'VolumeProfile',
    'CandleProperties',
    'create_pattern_detector'
]