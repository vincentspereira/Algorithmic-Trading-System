#!/usr/bin/env python3
"""
Institutional-Grade Candlestick Pattern Detection Module

Comprehensive candlestick pattern recognition system with volume confirmation,
trend context analysis, and institutional-grade reliability scoring.
Implements patterns from the institutional requirements document.

Author: AI Assistant
Date: 2024-12-15
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class PatternType(Enum):
    """Candlestick pattern types"""
    # Reversal Patterns
    HAMMER = "hammer"
    HANGING_MAN = "hanging_man"
    SHOOTING_STAR = "shooting_star"
    INVERTED_HAMMER = "inverted_hammer"
    BULLISH_ENGULFING = "bullish_engulfing"
    BEARISH_ENGULFING = "bearish_engulfing"
    MORNING_STAR = "morning_star"
    EVENING_STAR = "evening_star"
    DOJI = "doji"
    DRAGONFLY_DOJI = "dragonfly_doji"
    GRAVESTONE_DOJI = "gravestone_doji"
    
    # Continuation Patterns
    SPINNING_TOP = "spinning_top"
    MARUBOZU_BULLISH = "marubozu_bullish"
    MARUBOZU_BEARISH = "marubozu_bearish"
    
    # Multi-candle Patterns
    THREE_WHITE_SOLDIERS = "three_white_soldiers"
    THREE_BLACK_CROWS = "three_black_crows"
    TWEEZER_TOP = "tweezer_top"
    TWEEZER_BOTTOM = "tweezer_bottom"
    HARAMI_BULLISH = "harami_bullish"
    HARAMI_BEARISH = "harami_bearish"
    
class TrendContext(Enum):
    """Market trend context"""
    UPTREND = "uptrend"
    DOWNTREND = "downtrend"
    SIDEWAYS = "sideways"
    UNKNOWN = "unknown"

class PatternReliability(Enum):
    """Pattern reliability levels"""
    VERY_HIGH = "very_high"  # 90%+
    HIGH = "high"           # 75-90%
    MEDIUM = "medium"       # 60-75%
    LOW = "low"            # 45-60%
    VERY_LOW = "very_low"   # <45%

@dataclass
class CandleData:
    """Individual candle data structure"""
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: datetime
    
    @property
    def body_size(self) -> float:
        """Size of the candle body"""
        return abs(self.close - self.open)
    
    @property
    def upper_shadow(self) -> float:
        """Upper shadow length"""
        return self.high - max(self.open, self.close)
    
    @property
    def lower_shadow(self) -> float:
        """Lower shadow length"""
        return min(self.open, self.close) - self.low
    
    @property
    def total_range(self) -> float:
        """Total candle range (high - low)"""
        return self.high - self.low
    
    @property
    def is_bullish(self) -> bool:
        """True if candle is bullish (close > open)"""
        return self.close > self.open
    
    @property
    def is_bearish(self) -> bool:
        """True if candle is bearish (close < open)"""
        return self.close < self.open
    
    @property
    def is_doji(self) -> bool:
        """True if candle is a doji (small body)"""
        return self.body_size <= (self.total_range * 0.1)

@dataclass
class PatternResult:
    """Pattern detection result"""
    pattern_type: PatternType
    reliability: PatternReliability
    confidence_score: float  # 0.0 to 1.0
    trend_context: TrendContext
    volume_confirmation: bool
    signal_strength: float  # 0.0 to 1.0
    candles_involved: List[CandleData]
    metadata: Dict[str, Any]
    timestamp: datetime

class CandlestickPatternDetector:
    """Institutional-grade candlestick pattern detector"""
    
    def __init__(self, 
                 trend_lookback: int = 20,
                 volume_confirmation_threshold: float = 1.2,
                 min_body_size_ratio: float = 0.1,
                 doji_threshold: float = 0.1):
        """
        Initialize the pattern detector
        
        Args:
            trend_lookback: Number of periods to look back for trend determination
            volume_confirmation_threshold: Volume multiplier for confirmation
            min_body_size_ratio: Minimum body size as ratio of total range
            doji_threshold: Maximum body size ratio for doji identification
        """
        self.trend_lookback = trend_lookback
        self.volume_confirmation_threshold = volume_confirmation_threshold
        self.min_body_size_ratio = min_body_size_ratio
        self.doji_threshold = doji_threshold
        
        # Historical data storage
        self.candle_history: List[CandleData] = []
        self.pattern_history: List[PatternResult] = []
        
        # Pattern reliability mappings based on institutional research
        self.pattern_reliability_map = {
            PatternType.BULLISH_ENGULFING: PatternReliability.HIGH,
            PatternType.BEARISH_ENGULFING: PatternReliability.HIGH,
            PatternType.MORNING_STAR: PatternReliability.VERY_HIGH,
            PatternType.EVENING_STAR: PatternReliability.VERY_HIGH,
            PatternType.HAMMER: PatternReliability.HIGH,
            PatternType.HANGING_MAN: PatternReliability.HIGH,
            PatternType.SHOOTING_STAR: PatternReliability.MEDIUM,
            PatternType.INVERTED_HAMMER: PatternReliability.MEDIUM,
            PatternType.THREE_WHITE_SOLDIERS: PatternReliability.VERY_HIGH,
            PatternType.THREE_BLACK_CROWS: PatternReliability.VERY_HIGH,
            PatternType.DOJI: PatternReliability.MEDIUM,
            PatternType.DRAGONFLY_DOJI: PatternReliability.HIGH,
            PatternType.GRAVESTONE_DOJI: PatternReliability.HIGH,
            PatternType.SPINNING_TOP: PatternReliability.LOW,
            PatternType.MARUBOZU_BULLISH: PatternReliability.MEDIUM,
            PatternType.MARUBOZU_BEARISH: PatternReliability.MEDIUM,
            PatternType.TWEEZER_TOP: PatternReliability.MEDIUM,
            PatternType.TWEEZER_BOTTOM: PatternReliability.MEDIUM,
            PatternType.HARAMI_BULLISH: PatternReliability.MEDIUM,
            PatternType.HARAMI_BEARISH: PatternReliability.MEDIUM
        }
    
    def add_candle(self, open_price: float, high: float, low: float, 
                   close: float, volume: float, timestamp: datetime) -> List[PatternResult]:
        """Add a new candle and detect patterns"""
        candle = CandleData(open_price, high, low, close, volume, timestamp)
        self.candle_history.append(candle)
        
        # Keep reasonable history
        max_history = max(100, self.trend_lookback * 2)
        if len(self.candle_history) > max_history:
            self.candle_history = self.candle_history[-max_history:]
        
        # Detect patterns
        detected_patterns = self._detect_all_patterns()
        
        # Add to pattern history
        self.pattern_history.extend(detected_patterns)
        if len(self.pattern_history) > 50:  # Keep recent patterns
            self.pattern_history = self.pattern_history[-50:]
        
        return detected_patterns
    
    def _detect_all_patterns(self) -> List[PatternResult]:
        """Detect all possible patterns in current candle data"""
        patterns = []
        
        if len(self.candle_history) < 1:
            return patterns
        
        # Single candle patterns
        patterns.extend(self._detect_single_candle_patterns())
        
        # Two candle patterns
        if len(self.candle_history) >= 2:
            patterns.extend(self._detect_two_candle_patterns())
        
        # Three candle patterns
        if len(self.candle_history) >= 3:
            patterns.extend(self._detect_three_candle_patterns())
        
        return patterns
    
    def _detect_single_candle_patterns(self) -> List[PatternResult]:
        """Detect single candle patterns"""
        patterns = []
        current = self.candle_history[-1]
        trend = self._determine_trend()
        
        # Doji patterns
        if current.is_doji:
            if current.lower_shadow > current.upper_shadow * 2:
                # Dragonfly Doji
                patterns.append(self._create_pattern_result(
                    PatternType.DRAGONFLY_DOJI, [current], trend
                ))
            elif current.upper_shadow > current.lower_shadow * 2:
                # Gravestone Doji
                patterns.append(self._create_pattern_result(
                    PatternType.GRAVESTONE_DOJI, [current], trend
                ))
            else:
                # Regular Doji
                patterns.append(self._create_pattern_result(
                    PatternType.DOJI, [current], trend
                ))
        
        # Hammer and Hanging Man
        elif self._is_hammer_like(current):
            if trend == TrendContext.DOWNTREND:
                patterns.append(self._create_pattern_result(
                    PatternType.HAMMER, [current], trend
                ))
            elif trend == TrendContext.UPTREND:
                patterns.append(self._create_pattern_result(
                    PatternType.HANGING_MAN, [current], trend
                ))
        
        # Shooting Star and Inverted Hammer
        elif self._is_shooting_star_like(current):
            if trend == TrendContext.UPTREND:
                patterns.append(self._create_pattern_result(
                    PatternType.SHOOTING_STAR, [current], trend
                ))
            elif trend == TrendContext.DOWNTREND:
                patterns.append(self._create_pattern_result(
                    PatternType.INVERTED_HAMMER, [current], trend
                ))
        
        # Spinning Top
        elif self._is_spinning_top(current):
            patterns.append(self._create_pattern_result(
                PatternType.SPINNING_TOP, [current], trend
            ))
        
        # Marubozu
        elif self._is_marubozu(current):
            if current.is_bullish:
                patterns.append(self._create_pattern_result(
                    PatternType.MARUBOZU_BULLISH, [current], trend
                ))
            else:
                patterns.append(self._create_pattern_result(
                    PatternType.MARUBOZU_BEARISH, [current], trend
                ))
        
        return patterns
    
    def _detect_two_candle_patterns(self) -> List[PatternResult]:
        """Detect two candle patterns"""
        patterns = []
        if len(self.candle_history) < 2:
            return patterns
        
        prev = self.candle_history[-2]
        current = self.candle_history[-1]
        trend = self._determine_trend()
        
        # Engulfing patterns
        if self._is_bullish_engulfing(prev, current):
            patterns.append(self._create_pattern_result(
                PatternType.BULLISH_ENGULFING, [prev, current], trend
            ))
        elif self._is_bearish_engulfing(prev, current):
            patterns.append(self._create_pattern_result(
                PatternType.BEARISH_ENGULFING, [prev, current], trend
            ))
        
        # Harami patterns
        elif self._is_bullish_harami(prev, current):
            patterns.append(self._create_pattern_result(
                PatternType.HARAMI_BULLISH, [prev, current], trend
            ))
        elif self._is_bearish_harami(prev, current):
            patterns.append(self._create_pattern_result(
                PatternType.HARAMI_BEARISH, [prev, current], trend
            ))
        
        # Tweezer patterns
        elif self._is_tweezer_top(prev, current):
            patterns.append(self._create_pattern_result(
                PatternType.TWEEZER_TOP, [prev, current], trend
            ))
        elif self._is_tweezer_bottom(prev, current):
            patterns.append(self._create_pattern_result(
                PatternType.TWEEZER_BOTTOM, [prev, current], trend
            ))
        
        return patterns
    
    def _detect_three_candle_patterns(self) -> List[PatternResult]:
        """Detect three candle patterns"""
        patterns = []
        if len(self.candle_history) < 3:
            return patterns
        
        candles = self.candle_history[-3:]
        trend = self._determine_trend()
        
        # Morning Star
        if self._is_morning_star(candles):
            patterns.append(self._create_pattern_result(
                PatternType.MORNING_STAR, candles, trend
            ))
        
        # Evening Star
        elif self._is_evening_star(candles):
            patterns.append(self._create_pattern_result(
                PatternType.EVENING_STAR, candles, trend
            ))
        
        # Three White Soldiers
        elif self._is_three_white_soldiers(candles):
            patterns.append(self._create_pattern_result(
                PatternType.THREE_WHITE_SOLDIERS, candles, trend
            ))
        
        # Three Black Crows
        elif self._is_three_black_crows(candles):
            patterns.append(self._create_pattern_result(
                PatternType.THREE_BLACK_CROWS, candles, trend
            ))
        
        return patterns
    
    def _determine_trend(self) -> TrendContext:
        """Determine current market trend"""
        if len(self.candle_history) < self.trend_lookback:
            return TrendContext.UNKNOWN
        
        recent_candles = self.candle_history[-self.trend_lookback:]
        closes = [c.close for c in recent_candles]
        
        # Simple trend determination using linear regression slope
        x = np.arange(len(closes))
        slope = np.polyfit(x, closes, 1)[0]
        
        # Calculate trend strength
        price_range = max(closes) - min(closes)
        avg_price = np.mean(closes)
        trend_strength = abs(slope * len(closes)) / avg_price
        
        if trend_strength < 0.02:  # Less than 2% trend
            return TrendContext.SIDEWAYS
        elif slope > 0:
            return TrendContext.UPTREND
        else:
            return TrendContext.DOWNTREND
    
    def _calculate_volume_confirmation(self, candles: List[CandleData]) -> bool:
        """Check if pattern has volume confirmation"""
        if len(self.candle_history) < 10:
            return False
        
        # Get average volume of recent candles
        recent_volumes = [c.volume for c in self.candle_history[-10:]]
        avg_volume = np.mean(recent_volumes)
        
        # Check if pattern candles have above-average volume
        pattern_volumes = [c.volume for c in candles]
        pattern_avg_volume = np.mean(pattern_volumes)
        
        return pattern_avg_volume >= (avg_volume * self.volume_confirmation_threshold)
    
    def _create_pattern_result(self, pattern_type: PatternType, 
                             candles: List[CandleData], 
                             trend: TrendContext) -> PatternResult:
        """Create a pattern result with all metadata"""
        reliability = self.pattern_reliability_map.get(pattern_type, PatternReliability.MEDIUM)
        volume_confirmation = self._calculate_volume_confirmation(candles)
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(
            pattern_type, candles, trend, volume_confirmation
        )
        
        # Calculate signal strength
        signal_strength = self._calculate_signal_strength(
            pattern_type, candles, trend, volume_confirmation
        )
        
        # Generate metadata
        metadata = {
            'candle_count': len(candles),
            'total_volume': sum(c.volume for c in candles),
            'price_range': max(c.high for c in candles) - min(c.low for c in candles),
            'body_sizes': [c.body_size for c in candles],
            'shadow_ratios': [(c.upper_shadow + c.lower_shadow) / c.total_range for c in candles if c.total_range > 0]
        }
        
        return PatternResult(
            pattern_type=pattern_type,
            reliability=reliability,
            confidence_score=confidence_score,
            trend_context=trend,
            volume_confirmation=volume_confirmation,
            signal_strength=signal_strength,
            candles_involved=candles,
            metadata=metadata,
            timestamp=candles[-1].timestamp
        )
    
    def _calculate_confidence_score(self, pattern_type: PatternType, 
                                  candles: List[CandleData], 
                                  trend: TrendContext, 
                                  volume_confirmation: bool) -> float:
        """Calculate pattern confidence score"""
        base_confidence = {
            PatternReliability.VERY_HIGH: 0.9,
            PatternReliability.HIGH: 0.8,
            PatternReliability.MEDIUM: 0.7,
            PatternReliability.LOW: 0.6,
            PatternReliability.VERY_LOW: 0.5
        }
        
        reliability = self.pattern_reliability_map.get(pattern_type, PatternReliability.MEDIUM)
        confidence = base_confidence[reliability]
        
        # Adjust for trend context
        if self._is_trend_aligned(pattern_type, trend):
            confidence += 0.1
        
        # Adjust for volume confirmation
        if volume_confirmation:
            confidence += 0.1
        
        # Adjust for pattern quality
        quality_score = self._assess_pattern_quality(candles)
        confidence += (quality_score - 0.5) * 0.2
        
        return np.clip(confidence, 0.0, 1.0)
    
    def _calculate_signal_strength(self, pattern_type: PatternType, 
                                 candles: List[CandleData], 
                                 trend: TrendContext, 
                                 volume_confirmation: bool) -> float:
        """Calculate signal strength"""
        # Base strength from pattern type
        strength_map = {
            PatternType.MORNING_STAR: 0.9,
            PatternType.EVENING_STAR: 0.9,
            PatternType.THREE_WHITE_SOLDIERS: 0.95,
            PatternType.THREE_BLACK_CROWS: 0.95,
            PatternType.BULLISH_ENGULFING: 0.8,
            PatternType.BEARISH_ENGULFING: 0.8,
            PatternType.HAMMER: 0.7,
            PatternType.HANGING_MAN: 0.7,
            PatternType.SHOOTING_STAR: 0.6,
            PatternType.INVERTED_HAMMER: 0.6
        }
        
        base_strength = strength_map.get(pattern_type, 0.5)
        
        # Adjust for volume
        if volume_confirmation:
            base_strength += 0.1
        
        # Adjust for trend alignment
        if self._is_trend_aligned(pattern_type, trend):
            base_strength += 0.1
        
        return np.clip(base_strength, 0.0, 1.0)
    
    def _is_trend_aligned(self, pattern_type: PatternType, trend: TrendContext) -> bool:
        """Check if pattern is aligned with trend context"""
        bullish_patterns = {
            PatternType.HAMMER, PatternType.BULLISH_ENGULFING, 
            PatternType.MORNING_STAR, PatternType.THREE_WHITE_SOLDIERS,
            PatternType.DRAGONFLY_DOJI, PatternType.INVERTED_HAMMER,
            PatternType.MARUBOZU_BULLISH, PatternType.TWEEZER_BOTTOM,
            PatternType.HARAMI_BULLISH
        }
        
        bearish_patterns = {
            PatternType.HANGING_MAN, PatternType.BEARISH_ENGULFING,
            PatternType.EVENING_STAR, PatternType.THREE_BLACK_CROWS,
            PatternType.GRAVESTONE_DOJI, PatternType.SHOOTING_STAR,
            PatternType.MARUBOZU_BEARISH, PatternType.TWEEZER_TOP,
            PatternType.HARAMI_BEARISH
        }
        
        if pattern_type in bullish_patterns:
            return trend == TrendContext.DOWNTREND  # Bullish reversal in downtrend
        elif pattern_type in bearish_patterns:
            return trend == TrendContext.UPTREND    # Bearish reversal in uptrend
        
        return True  # Neutral patterns are always aligned
    
    def _assess_pattern_quality(self, candles: List[CandleData]) -> float:
        """Assess the quality of the pattern formation"""
        if not candles:
            return 0.5
        
        quality_score = 0.5
        
        # Check body sizes
        body_sizes = [c.body_size for c in candles]
        avg_body_size = np.mean(body_sizes)
        
        if avg_body_size > 0:
            # Prefer patterns with reasonable body sizes
            ranges = [c.total_range for c in candles]
            avg_range = np.mean(ranges)
            body_to_range_ratio = avg_body_size / avg_range if avg_range > 0 else 0
            
            if 0.3 <= body_to_range_ratio <= 0.8:
                quality_score += 0.2
        
        # Check for consistent volumes
        volumes = [c.volume for c in candles]
        if len(volumes) > 1:
            volume_consistency = 1.0 - (np.std(volumes) / np.mean(volumes))
            quality_score += volume_consistency * 0.1
        
        return np.clip(quality_score, 0.0, 1.0)
    
    # Pattern recognition helper methods
    def _is_hammer_like(self, candle: CandleData) -> bool:
        """Check if candle is hammer-like"""
        if candle.total_range == 0:
            return False
        
        body_ratio = candle.body_size / candle.total_range
        lower_shadow_ratio = candle.lower_shadow / candle.total_range
        upper_shadow_ratio = candle.upper_shadow / candle.total_range
        
        return (body_ratio <= 0.3 and 
                lower_shadow_ratio >= 0.6 and 
                upper_shadow_ratio <= 0.1)
    
    def _is_shooting_star_like(self, candle: CandleData) -> bool:
        """Check if candle is shooting star-like"""
        if candle.total_range == 0:
            return False
        
        body_ratio = candle.body_size / candle.total_range
        upper_shadow_ratio = candle.upper_shadow / candle.total_range
        lower_shadow_ratio = candle.lower_shadow / candle.total_range
        
        return (body_ratio <= 0.3 and 
                upper_shadow_ratio >= 0.6 and 
                lower_shadow_ratio <= 0.1)
    
    def _is_spinning_top(self, candle: CandleData) -> bool:
        """Check if candle is a spinning top"""
        if candle.total_range == 0:
            return False
        
        body_ratio = candle.body_size / candle.total_range
        shadow_ratio = (candle.upper_shadow + candle.lower_shadow) / candle.total_range
        
        return body_ratio <= 0.3 and shadow_ratio >= 0.6
    
    def _is_marubozu(self, candle: CandleData) -> bool:
        """Check if candle is a marubozu"""
        if candle.total_range == 0:
            return False
        
        body_ratio = candle.body_size / candle.total_range
        shadow_ratio = (candle.upper_shadow + candle.lower_shadow) / candle.total_range
        
        return body_ratio >= 0.9 and shadow_ratio <= 0.1
    
    def _is_bullish_engulfing(self, prev: CandleData, current: CandleData) -> bool:
        """Check for bullish engulfing pattern"""
        return (prev.is_bearish and current.is_bullish and
                current.open < prev.close and current.close > prev.open)
    
    def _is_bearish_engulfing(self, prev: CandleData, current: CandleData) -> bool:
        """Check for bearish engulfing pattern"""
        return (prev.is_bullish and current.is_bearish and
                current.open > prev.close and current.close < prev.open)
    
    def _is_bullish_harami(self, prev: CandleData, current: CandleData) -> bool:
        """Check for bullish harami pattern"""
        return (prev.is_bearish and current.is_bullish and
                current.open > prev.close and current.close < prev.open)
    
    def _is_bearish_harami(self, prev: CandleData, current: CandleData) -> bool:
        """Check for bearish harami pattern"""
        return (prev.is_bullish and current.is_bearish and
                current.open < prev.close and current.close > prev.open)
    
    def _is_tweezer_top(self, prev: CandleData, current: CandleData) -> bool:
        """Check for tweezer top pattern"""
        high_diff = abs(prev.high - current.high) / max(prev.high, current.high)
        return high_diff <= 0.01 and prev.is_bullish and current.is_bearish
    
    def _is_tweezer_bottom(self, prev: CandleData, current: CandleData) -> bool:
        """Check for tweezer bottom pattern"""
        low_diff = abs(prev.low - current.low) / max(prev.low, current.low)
        return low_diff <= 0.01 and prev.is_bearish and current.is_bullish
    
    def _is_morning_star(self, candles: List[CandleData]) -> bool:
        """Check for morning star pattern"""
        if len(candles) != 3:
            return False
        
        first, second, third = candles
        return (first.is_bearish and second.is_doji and third.is_bullish and
                third.close > (first.open + first.close) / 2)
    
    def _is_evening_star(self, candles: List[CandleData]) -> bool:
        """Check for evening star pattern"""
        if len(candles) != 3:
            return False
        
        first, second, third = candles
        return (first.is_bullish and second.is_doji and third.is_bearish and
                third.close < (first.open + first.close) / 2)
    
    def _is_three_white_soldiers(self, candles: List[CandleData]) -> bool:
        """Check for three white soldiers pattern"""
        if len(candles) != 3:
            return False
        
        return all(c.is_bullish for c in candles) and all(
            candles[i].close > candles[i-1].close for i in range(1, 3)
        )
    
    def _is_three_black_crows(self, candles: List[CandleData]) -> bool:
        """Check for three black crows pattern"""
        if len(candles) != 3:
            return False
        
        return all(c.is_bearish for c in candles) and all(
            candles[i].close < candles[i-1].close for i in range(1, 3)
        )
    
    def get_pattern_statistics(self) -> Dict[str, Any]:
        """Get statistics about detected patterns"""
        if not self.pattern_history:
            return {'total_patterns': 0}
        
        pattern_counts = {}
        reliability_counts = {}
        trend_context_counts = {}
        
        for pattern in self.pattern_history:
            # Count by pattern type
            pattern_type = pattern.pattern_type.value
            pattern_counts[pattern_type] = pattern_counts.get(pattern_type, 0) + 1
            
            # Count by reliability
            reliability = pattern.reliability.value
            reliability_counts[reliability] = reliability_counts.get(reliability, 0) + 1
            
            # Count by trend context
            trend = pattern.trend_context.value
            trend_context_counts[trend] = trend_context_counts.get(trend, 0) + 1
        
        avg_confidence = np.mean([p.confidence_score for p in self.pattern_history])
        avg_signal_strength = np.mean([p.signal_strength for p in self.pattern_history])
        volume_confirmation_rate = np.mean([p.volume_confirmation for p in self.pattern_history])
        
        return {
            'total_patterns': len(self.pattern_history),
            'pattern_counts': pattern_counts,
            'reliability_counts': reliability_counts,
            'trend_context_counts': trend_context_counts,
            'average_confidence': avg_confidence,
            'average_signal_strength': avg_signal_strength,
            'volume_confirmation_rate': volume_confirmation_rate
        }

# Example usage and testing
if __name__ == "__main__":
    detector = CandlestickPatternDetector()
    
    # Simulate some OHLCV data
    np.random.seed(42)
    base_price = 100.0
    
    print("Candlestick Pattern Detection Test")
    print("=" * 40)
    
    for i in range(30):
        # Simulate realistic OHLCV data
        price_change = np.random.randn() * 0.5
        base_price += price_change
        
        open_price = base_price + np.random.randn() * 0.2
        high = max(open_price, base_price) + abs(np.random.randn() * 0.3)
        low = min(open_price, base_price) - abs(np.random.randn() * 0.3)
        close = base_price + np.random.randn() * 0.2
        volume = np.random.randint(1000, 10000)
        
        timestamp = datetime.now()
        patterns = detector.add_candle(open_price, high, low, close, volume, timestamp)
        
        if patterns:
            print(f"Day {i+1}: Detected {len(patterns)} pattern(s)")
            for pattern in patterns:
                print(f"  - {pattern.pattern_type.value}: {pattern.reliability.value}")
                print(f"    Confidence: {pattern.confidence_score:.3f}, Signal: {pattern.signal_strength:.3f}")
                print(f"    Trend: {pattern.trend_context.value}, Volume Confirmed: {pattern.volume_confirmation}")
    
    # Print statistics
    stats = detector.get_pattern_statistics()
    print("\nPattern Statistics:")
    print(f"Total patterns detected: {stats['total_patterns']}")
    print(f"Average confidence: {stats.get('average_confidence', 0):.3f}")
    print(f"Volume confirmation rate: {stats.get('volume_confirmation_rate', 0):.3f}")
    print(f"Pattern distribution: {stats.get('pattern_counts', {})}")