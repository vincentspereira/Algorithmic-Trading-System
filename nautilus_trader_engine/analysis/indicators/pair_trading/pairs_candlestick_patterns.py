"""Pairs Trading Candlestick Patterns.

This module provides candlestick pattern recognition specifically designed
for spread/ratio data in pairs trading strategies.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, NamedTuple
from dataclasses import dataclass
from enum import Enum
import warnings


class PatternType(Enum):
    """Types of candlestick patterns for pairs trading."""
    # Reversal Patterns
    SPREAD_HAMMER = "spread_hammer"
    SPREAD_HANGING_MAN = "spread_hanging_man"
    SPREAD_SHOOTING_STAR = "spread_shooting_star"
    SPREAD_INVERTED_HAMMER = "spread_inverted_hammer"
    SPREAD_ENGULFING_BULLISH = "spread_engulfing_bullish"
    SPREAD_ENGULFING_BEARISH = "spread_engulfing_bearish"
    SPREAD_MORNING_STAR = "spread_morning_star"
    SPREAD_EVENING_STAR = "spread_evening_star"
    SPREAD_DOJI = "spread_doji"
    SPREAD_DRAGONFLY_DOJI = "spread_dragonfly_doji"
    SPREAD_GRAVESTONE_DOJI = "spread_gravestone_doji"
    
    # Continuation Patterns
    SPREAD_MARUBOZU_BULLISH = "spread_marubozu_bullish"
    SPREAD_MARUBOZU_BEARISH = "spread_marubozu_bearish"
    SPREAD_SPINNING_TOP = "spread_spinning_top"
    
    # Pairs-Specific Patterns
    RATIO_CONVERGENCE_HAMMER = "ratio_convergence_hammer"
    RATIO_DIVERGENCE_STAR = "ratio_divergence_star"
    SPREAD_MEAN_REVERSION_DOJI = "spread_mean_reversion_doji"
    VOLUME_CONFIRMED_REVERSAL = "volume_confirmed_reversal"
    COINTEGRATION_BREAKOUT = "cointegration_breakout"


class PatternSignal(Enum):
    """Pattern signal types."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    REVERSAL = "reversal"
    CONTINUATION = "continuation"


@dataclass
class PatternResult:
    """Result of pattern recognition."""
    pattern_type: PatternType
    signal: PatternSignal
    strength: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    index: int
    volume_confirmation: bool
    trend_context: str  # 'uptrend', 'downtrend', 'sideways'
    metadata: Dict


class SpreadCandlestick(NamedTuple):
    """Candlestick representation for spread data."""
    open: float
    high: float
    low: float
    close: float
    volume: float
    body_size: float
    upper_shadow: float
    lower_shadow: float
    is_bullish: bool


class RatioCandlestick(NamedTuple):
    """Candlestick representation for ratio data."""
    open: float
    high: float
    low: float
    close: float
    volume: float
    body_size: float
    upper_shadow: float
    lower_shadow: float
    is_bullish: bool


class PairsCandlestickPatterns:
    """Candlestick pattern recognition for pairs trading."""
    
    def __init__(self, min_body_ratio: float = 0.1, min_shadow_ratio: float = 2.0,
                 doji_threshold: float = 0.05, volume_threshold: float = 1.2):
        self.min_body_ratio = min_body_ratio
        self.min_shadow_ratio = min_shadow_ratio
        self.doji_threshold = doji_threshold
        self.volume_threshold = volume_threshold
        self.epsilon = 1e-8
    
    def create_spread_candlesticks(self, spread_open: np.ndarray, spread_high: np.ndarray,
                                 spread_low: np.ndarray, spread_close: np.ndarray,
                                 spread_volume: np.ndarray) -> List[SpreadCandlestick]:
        """Create candlestick objects from spread OHLCV data."""
        candlesticks = []
        
        for i in range(len(spread_open)):
            body_size = abs(spread_close[i] - spread_open[i])
            upper_shadow = spread_high[i] - max(spread_open[i], spread_close[i])
            lower_shadow = min(spread_open[i], spread_close[i]) - spread_low[i]
            is_bullish = spread_close[i] > spread_open[i]
            
            candlestick = SpreadCandlestick(
                open=spread_open[i],
                high=spread_high[i],
                low=spread_low[i],
                close=spread_close[i],
                volume=spread_volume[i],
                body_size=body_size,
                upper_shadow=upper_shadow,
                lower_shadow=lower_shadow,
                is_bullish=is_bullish
            )
            candlesticks.append(candlestick)
        
        return candlesticks
    
    def create_ratio_candlesticks(self, ratio_open: np.ndarray, ratio_high: np.ndarray,
                                ratio_low: np.ndarray, ratio_close: np.ndarray,
                                ratio_volume: np.ndarray) -> List[RatioCandlestick]:
        """Create candlestick objects from ratio OHLCV data."""
        candlesticks = []
        
        for i in range(len(ratio_open)):
            body_size = abs(ratio_close[i] - ratio_open[i])
            upper_shadow = ratio_high[i] - max(ratio_open[i], ratio_close[i])
            lower_shadow = min(ratio_open[i], ratio_close[i]) - ratio_low[i]
            is_bullish = ratio_close[i] > ratio_open[i]
            
            candlestick = RatioCandlestick(
                open=ratio_open[i],
                high=ratio_high[i],
                low=ratio_low[i],
                close=ratio_close[i],
                volume=ratio_volume[i],
                body_size=body_size,
                upper_shadow=upper_shadow,
                lower_shadow=lower_shadow,
                is_bullish=is_bullish
            )
            candlesticks.append(candlestick)
        
        return candlesticks
    
    def detect_spread_patterns(self, spread_candlesticks: List[SpreadCandlestick],
                             trend_context: List[str] = None) -> List[PatternResult]:
        """Detect candlestick patterns in spread data."""
        patterns = []
        
        if trend_context is None:
            trend_context = self._determine_trend_context(spread_candlesticks)
        
        for i in range(len(spread_candlesticks)):
            candle = spread_candlesticks[i]
            
            # Single candlestick patterns
            patterns.extend(self._detect_single_candle_patterns(
                candle, i, 'spread', trend_context[i] if i < len(trend_context) else 'sideways'
            ))
            
            # Two candlestick patterns
            if i > 0:
                patterns.extend(self._detect_two_candle_patterns(
                    spread_candlesticks[i-1], candle, i, 'spread', 
                    trend_context[i] if i < len(trend_context) else 'sideways'
                ))
            
            # Three candlestick patterns
            if i > 1:
                patterns.extend(self._detect_three_candle_patterns(
                    spread_candlesticks[i-2], spread_candlesticks[i-1], candle, i, 'spread',
                    trend_context[i] if i < len(trend_context) else 'sideways'
                ))
        
        return patterns
    
    def detect_ratio_patterns(self, ratio_candlesticks: List[RatioCandlestick],
                            trend_context: List[str] = None) -> List[PatternResult]:
        """Detect candlestick patterns in ratio data."""
        patterns = []
        
        if trend_context is None:
            trend_context = self._determine_trend_context_ratio(ratio_candlesticks)
        
        for i in range(len(ratio_candlesticks)):
            candle = ratio_candlesticks[i]
            
            # Single candlestick patterns
            patterns.extend(self._detect_single_candle_patterns(
                candle, i, 'ratio', trend_context[i] if i < len(trend_context) else 'sideways'
            ))
            
            # Two candlestick patterns
            if i > 0:
                patterns.extend(self._detect_two_candle_patterns(
                    ratio_candlesticks[i-1], candle, i, 'ratio',
                    trend_context[i] if i < len(trend_context) else 'sideways'
                ))
            
            # Three candlestick patterns
            if i > 1:
                patterns.extend(self._detect_three_candle_patterns(
                    ratio_candlesticks[i-2], ratio_candlesticks[i-1], candle, i, 'ratio',
                    trend_context[i] if i < len(trend_context) else 'sideways'
                ))
        
        return patterns
    
    def _detect_single_candle_patterns(self, candle, index: int, data_type: str, 
                                     trend: str) -> List[PatternResult]:
        """Detect single candlestick patterns."""
        patterns = []
        
        # Doji patterns
        if self._is_doji(candle):
            if self._is_dragonfly_doji(candle):
                pattern_type = PatternType.SPREAD_DRAGONFLY_DOJI if data_type == 'spread' else PatternType.SPREAD_DRAGONFLY_DOJI
                signal = PatternSignal.BULLISH if trend == 'downtrend' else PatternSignal.NEUTRAL
            elif self._is_gravestone_doji(candle):
                pattern_type = PatternType.SPREAD_GRAVESTONE_DOJI if data_type == 'spread' else PatternType.SPREAD_GRAVESTONE_DOJI
                signal = PatternSignal.BEARISH if trend == 'uptrend' else PatternSignal.NEUTRAL
            else:
                pattern_type = PatternType.SPREAD_DOJI if data_type == 'spread' else PatternType.SPREAD_DOJI
                signal = PatternSignal.NEUTRAL
            
            patterns.append(PatternResult(
                pattern_type=pattern_type,
                signal=signal,
                strength=0.7,
                confidence=0.6,
                index=index,
                volume_confirmation=self._check_volume_confirmation(candle, index),
                trend_context=trend,
                metadata={'data_type': data_type, 'body_ratio': candle.body_size / (candle.high - candle.low + self.epsilon)}
            ))
        
        # Hammer patterns
        elif self._is_hammer(candle):
            if trend == 'downtrend':
                pattern_type = PatternType.SPREAD_HAMMER if data_type == 'spread' else PatternType.RATIO_CONVERGENCE_HAMMER
                signal = PatternSignal.BULLISH
                strength = 0.8
            else:
                pattern_type = PatternType.SPREAD_HANGING_MAN if data_type == 'spread' else PatternType.SPREAD_HANGING_MAN
                signal = PatternSignal.BEARISH
                strength = 0.7
            
            patterns.append(PatternResult(
                pattern_type=pattern_type,
                signal=signal,
                strength=strength,
                confidence=0.7,
                index=index,
                volume_confirmation=self._check_volume_confirmation(candle, index),
                trend_context=trend,
                metadata={'data_type': data_type, 'shadow_ratio': candle.lower_shadow / (candle.body_size + self.epsilon)}
            ))
        
        # Shooting star patterns
        elif self._is_shooting_star(candle):
            if trend == 'uptrend':
                pattern_type = PatternType.SPREAD_SHOOTING_STAR if data_type == 'spread' else PatternType.RATIO_DIVERGENCE_STAR
                signal = PatternSignal.BEARISH
                strength = 0.8
            else:
                pattern_type = PatternType.SPREAD_INVERTED_HAMMER if data_type == 'spread' else PatternType.SPREAD_INVERTED_HAMMER
                signal = PatternSignal.BULLISH
                strength = 0.7
            
            patterns.append(PatternResult(
                pattern_type=pattern_type,
                signal=signal,
                strength=strength,
                confidence=0.7,
                index=index,
                volume_confirmation=self._check_volume_confirmation(candle, index),
                trend_context=trend,
                metadata={'data_type': data_type, 'shadow_ratio': candle.upper_shadow / (candle.body_size + self.epsilon)}
            ))
        
        # Marubozu patterns
        elif self._is_marubozu(candle):
            if candle.is_bullish:
                pattern_type = PatternType.SPREAD_MARUBOZU_BULLISH
                signal = PatternSignal.CONTINUATION if trend == 'uptrend' else PatternSignal.BULLISH
            else:
                pattern_type = PatternType.SPREAD_MARUBOZU_BEARISH
                signal = PatternSignal.CONTINUATION if trend == 'downtrend' else PatternSignal.BEARISH
            
            patterns.append(PatternResult(
                pattern_type=pattern_type,
                signal=signal,
                strength=0.8,
                confidence=0.8,
                index=index,
                volume_confirmation=self._check_volume_confirmation(candle, index),
                trend_context=trend,
                metadata={'data_type': data_type, 'body_percentage': candle.body_size / (candle.high - candle.low + self.epsilon)}
            ))
        
        # Spinning top
        elif self._is_spinning_top(candle):
            patterns.append(PatternResult(
                pattern_type=PatternType.SPREAD_SPINNING_TOP,
                signal=PatternSignal.NEUTRAL,
                strength=0.5,
                confidence=0.5,
                index=index,
                volume_confirmation=self._check_volume_confirmation(candle, index),
                trend_context=trend,
                metadata={'data_type': data_type, 'indecision': True}
            ))
        
        return patterns
    
    def _detect_two_candle_patterns(self, prev_candle, curr_candle, index: int, 
                                  data_type: str, trend: str) -> List[PatternResult]:
        """Detect two-candlestick patterns."""
        patterns = []
        
        # Engulfing patterns
        if self._is_bullish_engulfing(prev_candle, curr_candle):
            patterns.append(PatternResult(
                pattern_type=PatternType.SPREAD_ENGULFING_BULLISH,
                signal=PatternSignal.BULLISH,
                strength=0.9,
                confidence=0.8,
                index=index,
                volume_confirmation=self._check_volume_confirmation(curr_candle, index),
                trend_context=trend,
                metadata={
                    'data_type': data_type,
                    'engulfing_ratio': curr_candle.body_size / (prev_candle.body_size + self.epsilon)
                }
            ))
        
        elif self._is_bearish_engulfing(prev_candle, curr_candle):
            patterns.append(PatternResult(
                pattern_type=PatternType.SPREAD_ENGULFING_BEARISH,
                signal=PatternSignal.BEARISH,
                strength=0.9,
                confidence=0.8,
                index=index,
                volume_confirmation=self._check_volume_confirmation(curr_candle, index),
                trend_context=trend,
                metadata={
                    'data_type': data_type,
                    'engulfing_ratio': curr_candle.body_size / (prev_candle.body_size + self.epsilon)
                }
            ))
        
        return patterns
    
    def _detect_three_candle_patterns(self, first_candle, second_candle, third_candle, 
                                    index: int, data_type: str, trend: str) -> List[PatternResult]:
        """Detect three-candlestick patterns."""
        patterns = []
        
        # Morning Star
        if self._is_morning_star(first_candle, second_candle, third_candle):
            patterns.append(PatternResult(
                pattern_type=PatternType.SPREAD_MORNING_STAR,
                signal=PatternSignal.BULLISH,
                strength=0.9,
                confidence=0.8,
                index=index,
                volume_confirmation=self._check_volume_confirmation(third_candle, index),
                trend_context=trend,
                metadata={
                    'data_type': data_type,
                    'star_body_ratio': second_candle.body_size / (first_candle.body_size + self.epsilon)
                }
            ))
        
        # Evening Star
        elif self._is_evening_star(first_candle, second_candle, third_candle):
            patterns.append(PatternResult(
                pattern_type=PatternType.SPREAD_EVENING_STAR,
                signal=PatternSignal.BEARISH,
                strength=0.9,
                confidence=0.8,
                index=index,
                volume_confirmation=self._check_volume_confirmation(third_candle, index),
                trend_context=trend,
                metadata={
                    'data_type': data_type,
                    'star_body_ratio': second_candle.body_size / (first_candle.body_size + self.epsilon)
                }
            ))
        
        return patterns
    
    def _is_doji(self, candle) -> bool:
        """Check if candlestick is a doji."""
        range_size = candle.high - candle.low
        if range_size == 0:
            return True
        return candle.body_size / range_size <= self.doji_threshold
    
    def _is_dragonfly_doji(self, candle) -> bool:
        """Check if candlestick is a dragonfly doji."""
        return (self._is_doji(candle) and 
                candle.lower_shadow > candle.body_size * 2 and
                candle.upper_shadow <= candle.body_size)
    
    def _is_gravestone_doji(self, candle) -> bool:
        """Check if candlestick is a gravestone doji."""
        return (self._is_doji(candle) and 
                candle.upper_shadow > candle.body_size * 2 and
                candle.lower_shadow <= candle.body_size)
    
    def _is_hammer(self, candle) -> bool:
        """Check if candlestick is a hammer."""
        return (candle.lower_shadow >= candle.body_size * self.min_shadow_ratio and
                candle.upper_shadow <= candle.body_size * 0.5 and
                candle.body_size > 0)
    
    def _is_shooting_star(self, candle) -> bool:
        """Check if candlestick is a shooting star."""
        return (candle.upper_shadow >= candle.body_size * self.min_shadow_ratio and
                candle.lower_shadow <= candle.body_size * 0.5 and
                candle.body_size > 0)
    
    def _is_marubozu(self, candle) -> bool:
        """Check if candlestick is a marubozu."""
        range_size = candle.high - candle.low
        if range_size == 0:
            return False
        return candle.body_size / range_size >= 0.95
    
    def _is_spinning_top(self, candle) -> bool:
        """Check if candlestick is a spinning top."""
        total_shadow = candle.upper_shadow + candle.lower_shadow
        return (candle.body_size > 0 and
                total_shadow >= candle.body_size * 2 and
                candle.upper_shadow > candle.body_size * 0.5 and
                candle.lower_shadow > candle.body_size * 0.5)
    
    def _is_bullish_engulfing(self, prev_candle, curr_candle) -> bool:
        """Check if pattern is bullish engulfing."""
        return (not prev_candle.is_bullish and
                curr_candle.is_bullish and
                curr_candle.open < prev_candle.close and
                curr_candle.close > prev_candle.open and
                curr_candle.body_size > prev_candle.body_size)
    
    def _is_bearish_engulfing(self, prev_candle, curr_candle) -> bool:
        """Check if pattern is bearish engulfing."""
        return (prev_candle.is_bullish and
                not curr_candle.is_bullish and
                curr_candle.open > prev_candle.close and
                curr_candle.close < prev_candle.open and
                curr_candle.body_size > prev_candle.body_size)
    
    def _is_morning_star(self, first_candle, second_candle, third_candle) -> bool:
        """Check if pattern is morning star."""
        return (not first_candle.is_bullish and
                second_candle.body_size < first_candle.body_size * 0.5 and
                third_candle.is_bullish and
                third_candle.close > (first_candle.open + first_candle.close) / 2)
    
    def _is_evening_star(self, first_candle, second_candle, third_candle) -> bool:
        """Check if pattern is evening star."""
        return (first_candle.is_bullish and
                second_candle.body_size < first_candle.body_size * 0.5 and
                not third_candle.is_bullish and
                third_candle.close < (first_candle.open + first_candle.close) / 2)
    
    def _check_volume_confirmation(self, candle, index: int) -> bool:
        """Check if pattern has volume confirmation."""
        # Simplified volume confirmation - in practice, would compare with average volume
        return candle.volume > 1000  # Placeholder logic
    
    def _determine_trend_context(self, candlesticks: List[SpreadCandlestick], 
                               lookback: int = 20) -> List[str]:
        """Determine trend context for each candlestick."""
        trends = []
        
        for i in range(len(candlesticks)):
            if i < lookback:
                trends.append('sideways')
                continue
            
            # Simple trend determination based on moving average slope
            recent_closes = [c.close for c in candlesticks[i-lookback:i]]
            if len(recent_closes) < 2:
                trends.append('sideways')
                continue
            
            slope = (recent_closes[-1] - recent_closes[0]) / len(recent_closes)
            
            if slope > 0.01:
                trends.append('uptrend')
            elif slope < -0.01:
                trends.append('downtrend')
            else:
                trends.append('sideways')
        
        return trends
    
    def _determine_trend_context_ratio(self, candlesticks: List[RatioCandlestick], 
                                     lookback: int = 20) -> List[str]:
        """Determine trend context for ratio candlesticks."""
        trends = []
        
        for i in range(len(candlesticks)):
            if i < lookback:
                trends.append('sideways')
                continue
            
            # Simple trend determination based on moving average slope
            recent_closes = [c.close for c in candlesticks[i-lookback:i]]
            if len(recent_closes) < 2:
                trends.append('sideways')
                continue
            
            slope = (recent_closes[-1] - recent_closes[0]) / len(recent_closes)
            
            if slope > 0.001:  # Smaller threshold for ratios
                trends.append('uptrend')
            elif slope < -0.001:
                trends.append('downtrend')
            else:
                trends.append('sideways')
        
        return trends


class SpreadPatternAnalyzer:
    """Advanced pattern analysis for spread/ratio relationships."""
    
    def __init__(self):
        self.pattern_detector = PairsCandlestickPatterns()
        self.epsilon = 1e-8
    
    def analyze_spread_patterns(self, spread_open: np.ndarray, spread_high: np.ndarray,
                              spread_low: np.ndarray, spread_close: np.ndarray,
                              spread_volume: np.ndarray) -> Dict:
        """Comprehensive spread pattern analysis."""
        # Create candlesticks
        candlesticks = self.pattern_detector.create_spread_candlesticks(
            spread_open, spread_high, spread_low, spread_close, spread_volume
        )
        
        # Detect patterns
        patterns = self.pattern_detector.detect_spread_patterns(candlesticks)
        
        # Analyze pattern statistics
        pattern_stats = self._calculate_pattern_statistics(patterns)
        
        # Generate trading recommendations
        recommendations = self._generate_pattern_recommendations(patterns)
        
        return {
            'candlesticks': candlesticks,
            'patterns': patterns,
            'pattern_statistics': pattern_stats,
            'recommendations': recommendations,
            'analysis_timestamp': pd.Timestamp.now()
        }
    
    def analyze_ratio_patterns(self, ratio_open: np.ndarray, ratio_high: np.ndarray,
                             ratio_low: np.ndarray, ratio_close: np.ndarray,
                             ratio_volume: np.ndarray) -> Dict:
        """Comprehensive ratio pattern analysis."""
        # Create candlesticks
        candlesticks = self.pattern_detector.create_ratio_candlesticks(
            ratio_open, ratio_high, ratio_low, ratio_close, ratio_volume
        )
        
        # Detect patterns
        patterns = self.pattern_detector.detect_ratio_patterns(candlesticks)
        
        # Analyze pattern statistics
        pattern_stats = self._calculate_pattern_statistics(patterns)
        
        # Generate trading recommendations
        recommendations = self._generate_pattern_recommendations(patterns)
        
        return {
            'candlesticks': candlesticks,
            'patterns': patterns,
            'pattern_statistics': pattern_stats,
            'recommendations': recommendations,
            'analysis_timestamp': pd.Timestamp.now()
        }
    
    def _calculate_pattern_statistics(self, patterns: List[PatternResult]) -> Dict:
        """Calculate statistics for detected patterns."""
        if not patterns:
            return {
                'total_patterns': 0,
                'pattern_types': {},
                'signal_distribution': {},
                'average_strength': 0.0,
                'average_confidence': 0.0,
                'volume_confirmation_rate': 0.0
            }
        
        # Count pattern types
        pattern_types = {}
        for pattern in patterns:
            pattern_type = pattern.pattern_type.value
            pattern_types[pattern_type] = pattern_types.get(pattern_type, 0) + 1
        
        # Count signal types
        signal_distribution = {}
        for pattern in patterns:
            signal_type = pattern.signal.value
            signal_distribution[signal_type] = signal_distribution.get(signal_type, 0) + 1
        
        # Calculate averages
        avg_strength = np.mean([p.strength for p in patterns])
        avg_confidence = np.mean([p.confidence for p in patterns])
        volume_confirmation_rate = np.mean([p.volume_confirmation for p in patterns])
        
        return {
            'total_patterns': len(patterns),
            'pattern_types': pattern_types,
            'signal_distribution': signal_distribution,
            'average_strength': avg_strength,
            'average_confidence': avg_confidence,
            'volume_confirmation_rate': volume_confirmation_rate
        }
    
    def _generate_pattern_recommendations(self, patterns: List[PatternResult]) -> List[Dict]:
        """Generate trading recommendations based on patterns."""
        recommendations = []
        
        # Group patterns by signal type and strength
        bullish_patterns = [p for p in patterns if p.signal == PatternSignal.BULLISH and p.strength > 0.7]
        bearish_patterns = [p for p in patterns if p.signal == PatternSignal.BEARISH and p.strength > 0.7]
        reversal_patterns = [p for p in patterns if p.signal == PatternSignal.REVERSAL and p.confidence > 0.6]
        
        # Generate recommendations for strong bullish patterns
        if bullish_patterns:
            strongest_bullish = max(bullish_patterns, key=lambda x: x.strength * x.confidence)
            recommendations.append({
                'action': 'LONG_SPREAD',
                'reason': f'Strong bullish pattern: {strongest_bullish.pattern_type.value}',
                'strength': strongest_bullish.strength,
                'confidence': strongest_bullish.confidence,
                'pattern_index': strongest_bullish.index,
                'volume_confirmed': strongest_bullish.volume_confirmation
            })
        
        # Generate recommendations for strong bearish patterns
        if bearish_patterns:
            strongest_bearish = max(bearish_patterns, key=lambda x: x.strength * x.confidence)
            recommendations.append({
                'action': 'SHORT_SPREAD',
                'reason': f'Strong bearish pattern: {strongest_bearish.pattern_type.value}',
                'strength': strongest_bearish.strength,
                'confidence': strongest_bearish.confidence,
                'pattern_index': strongest_bearish.index,
                'volume_confirmed': strongest_bearish.volume_confirmation
            })
        
        # Generate recommendations for reversal patterns
        if reversal_patterns:
            strongest_reversal = max(reversal_patterns, key=lambda x: x.confidence)
            recommendations.append({
                'action': 'PREPARE_REVERSAL',
                'reason': f'Potential reversal pattern: {strongest_reversal.pattern_type.value}',
                'strength': strongest_reversal.strength,
                'confidence': strongest_reversal.confidence,
                'pattern_index': strongest_reversal.index,
                'volume_confirmed': strongest_reversal.volume_confirmation
            })
        
        return recommendations
    
    def combine_spread_ratio_analysis(self, spread_analysis: Dict, ratio_analysis: Dict) -> Dict:
        """Combine spread and ratio pattern analysis for comprehensive insights."""
        combined_patterns = spread_analysis['patterns'] + ratio_analysis['patterns']
        
        # Sort by strength and confidence
        combined_patterns.sort(key=lambda x: x.strength * x.confidence, reverse=True)
        
        # Generate combined recommendations
        combined_recommendations = self._generate_combined_recommendations(
            spread_analysis['recommendations'], ratio_analysis['recommendations']
        )
        
        return {
            'spread_analysis': spread_analysis,
            'ratio_analysis': ratio_analysis,
            'combined_patterns': combined_patterns[:10],  # Top 10 patterns
            'combined_recommendations': combined_recommendations,
            'pattern_consensus': self._calculate_pattern_consensus(combined_patterns),
            'analysis_timestamp': pd.Timestamp.now()
        }
    
    def _generate_combined_recommendations(self, spread_recs: List[Dict], 
                                        ratio_recs: List[Dict]) -> List[Dict]:
        """Generate combined recommendations from spread and ratio analysis."""
        combined_recs = []
        
        # Look for consensus between spread and ratio recommendations
        spread_actions = {rec['action'] for rec in spread_recs}
        ratio_actions = {rec['action'] for rec in ratio_recs}
        
        consensus_actions = spread_actions.intersection(ratio_actions)
        
        for action in consensus_actions:
            spread_rec = next((r for r in spread_recs if r['action'] == action), None)
            ratio_rec = next((r for r in ratio_recs if r['action'] == action), None)
            
            if spread_rec and ratio_rec:
                combined_strength = (spread_rec['strength'] + ratio_rec['strength']) / 2
                combined_confidence = (spread_rec['confidence'] + ratio_rec['confidence']) / 2
                
                combined_recs.append({
                    'action': action,
                    'reason': f'Consensus between spread and ratio analysis',
                    'strength': combined_strength,
                    'confidence': combined_confidence,
                    'spread_pattern': spread_rec['reason'],
                    'ratio_pattern': ratio_rec['reason'],
                    'consensus': True
                })
        
        # Add non-consensus recommendations with lower priority
        for rec in spread_recs + ratio_recs:
            if rec['action'] not in consensus_actions:
                rec['consensus'] = False
                combined_recs.append(rec)
        
        return combined_recs
    
    def _calculate_pattern_consensus(self, patterns: List[PatternResult]) -> Dict:
        """Calculate consensus metrics across all patterns."""
        if not patterns:
            return {'consensus_signal': 'NEUTRAL', 'consensus_strength': 0.0}
        
        # Weight patterns by strength and confidence
        weighted_signals = []
        for pattern in patterns:
            weight = pattern.strength * pattern.confidence
            if pattern.signal == PatternSignal.BULLISH:
                weighted_signals.append(weight)
            elif pattern.signal == PatternSignal.BEARISH:
                weighted_signals.append(-weight)
            # Neutral and other signals contribute 0
        
        if not weighted_signals:
            return {'consensus_signal': 'NEUTRAL', 'consensus_strength': 0.0}
        
        consensus_score = np.mean(weighted_signals)
        consensus_strength = abs(consensus_score)
        
        if consensus_score > 0.1:
            consensus_signal = 'BULLISH'
        elif consensus_score < -0.1:
            consensus_signal = 'BEARISH'
        else:
            consensus_signal = 'NEUTRAL'
        
        return {
            'consensus_signal': consensus_signal,
            'consensus_strength': consensus_strength,
            'consensus_score': consensus_score,
            'pattern_count': len(patterns)
        }


# Example usage and testing functions
def test_pairs_candlestick_patterns():
    """Test the pairs candlestick pattern recognition."""
    print("Testing Pairs Candlestick Patterns...")
    
    # Generate sample spread data
    np.random.seed(42)
    n_periods = 100
    
    # Create sample spread OHLCV data
    base_spread = 10.0
    spread_returns = np.random.normal(0, 0.02, n_periods)
    spread_close = base_spread + np.cumsum(spread_returns)
    
    spread_open = np.roll(spread_close, 1)
    spread_open[0] = base_spread
    
    spread_high = np.maximum(spread_open, spread_close) + np.abs(np.random.normal(0, 0.5, n_periods))
    spread_low = np.minimum(spread_open, spread_close) - np.abs(np.random.normal(0, 0.5, n_periods))
    spread_volume = np.random.lognormal(8, 0.5, n_periods)
    
    # Create ratio data
    ratio_close = 1.0 + spread_close / 100.0  # Convert spread to ratio-like data
    ratio_open = np.roll(ratio_close, 1)
    ratio_open[0] = 1.0
    
    ratio_high = np.maximum(ratio_open, ratio_close) + np.abs(np.random.normal(0, 0.01, n_periods))
    ratio_low = np.minimum(ratio_open, ratio_close) - np.abs(np.random.normal(0, 0.01, n_periods))
    ratio_volume = spread_volume * 0.8
    
    # Initialize pattern analyzer
    analyzer = SpreadPatternAnalyzer()
    
    # Analyze spread patterns
    spread_analysis = analyzer.analyze_spread_patterns(
        spread_open, spread_high, spread_low, spread_close, spread_volume
    )
    
    print(f"\nSpread Pattern Analysis:")
    print(f"Total patterns detected: {spread_analysis['pattern_statistics']['total_patterns']}")
    print(f"Pattern types: {spread_analysis['pattern_statistics']['pattern_types']}")
    print(f"Signal distribution: {spread_analysis['pattern_statistics']['signal_distribution']}")
    print(f"Average strength: {spread_analysis['pattern_statistics']['average_strength']:.3f}")
    print(f"Average confidence: {spread_analysis['pattern_statistics']['average_confidence']:.3f}")
    
    # Analyze ratio patterns
    ratio_analysis = analyzer.analyze_ratio_patterns(
        ratio_open, ratio_high, ratio_low, ratio_close, ratio_volume
    )
    
    print(f"\nRatio Pattern Analysis:")
    print(f"Total patterns detected: {ratio_analysis['pattern_statistics']['total_patterns']}")
    print(f"Pattern types: {ratio_analysis['pattern_statistics']['pattern_types']}")
    print(f"Signal distribution: {ratio_analysis['pattern_statistics']['signal_distribution']}")
    
    # Combined analysis
    combined_analysis = analyzer.combine_spread_ratio_analysis(spread_analysis, ratio_analysis)
    
    print(f"\nCombined Analysis:")
    print(f"Pattern consensus: {combined_analysis['pattern_consensus']}")
    print(f"Combined recommendations: {len(combined_analysis['combined_recommendations'])}")
    
    # Show sample recommendations
    if combined_analysis['combined_recommendations']:
        print(f"\nSample Recommendation:")
        rec = combined_analysis['combined_recommendations'][0]
        print(f"Action: {rec['action']}")
        print(f"Reason: {rec['reason']}")
        print(f"Strength: {rec['strength']:.3f}")
        print(f"Confidence: {rec['confidence']:.3f}")
        print(f"Consensus: {rec.get('consensus', False)}")
    
    print("\nPairs Candlestick Patterns test completed successfully!")


if __name__ == "__main__":
    test_pairs_candlestick_patterns()