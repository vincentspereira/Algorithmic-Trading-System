"""
Market Pattern Recognition System
Advanced pattern detection and analysis for trading systems
"""

import asyncio
import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Union
import logging
from collections import deque
import time

try:
    from scipy import signal, stats
    from scipy.ndimage import gaussian_filter1d
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    signal = None
    stats = None
    gaussian_filter1d = None

try:
    from sklearn.cluster import DBSCAN
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    DBSCAN = None
    StandardScaler = None


class PatternType(Enum):
    """Types of market patterns"""
    # Candlestick patterns
    DOJI = "doji"
    HAMMER = "hammer"
    SHOOTING_STAR = "shooting_star"
    ENGULFING_BULLISH = "engulfing_bullish"
    ENGULFING_BEARISH = "engulfing_bearish"
    MORNING_STAR = "morning_star"
    EVENING_STAR = "evening_star"
    
    # Chart patterns
    HEAD_AND_SHOULDERS = "head_and_shoulders"
    INVERSE_HEAD_AND_SHOULDERS = "inverse_head_and_shoulders"
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    TRIANGLE_ASCENDING = "triangle_ascending"
    TRIANGLE_DESCENDING = "triangle_descending"
    TRIANGLE_SYMMETRICAL = "triangle_symmetrical"
    WEDGE_RISING = "wedge_rising"
    WEDGE_FALLING = "wedge_falling"
    
    # Volume patterns
    VOLUME_SPIKE = "volume_spike"
    VOLUME_DIVERGENCE = "volume_divergence"
    ACCUMULATION = "accumulation"
    DISTRIBUTION = "distribution"
    
    # Trend patterns
    TREND_REVERSAL = "trend_reversal"
    BREAKOUT = "breakout"
    BREAKDOWN = "breakdown"
    SUPPORT_RESISTANCE = "support_resistance"
    
    # Anomaly patterns
    PRICE_ANOMALY = "price_anomaly"
    VOLUME_ANOMALY = "volume_anomaly"
    CORRELATION_BREAK = "correlation_break"


class PatternSignal(Enum):
    """Pattern trading signals"""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    NEUTRAL = "neutral"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class PatternConfidence(Enum):
    """Pattern confidence levels"""
    VERY_LOW = 0.2
    LOW = 0.4
    MEDIUM = 0.6
    HIGH = 0.8
    VERY_HIGH = 0.9


@dataclass
class MarketData:
    """Market data structure for pattern analysis"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    symbol: str = ""
    
    def body_size(self) -> float:
        """Calculate candlestick body size"""
        return abs(self.close - self.open)
    
    def upper_shadow(self) -> float:
        """Calculate upper shadow length"""
        return self.high - max(self.open, self.close)
    
    def lower_shadow(self) -> float:
        """Calculate lower shadow length"""
        return min(self.open, self.close) - self.low
    
    def is_bullish(self) -> bool:
        """Check if candle is bullish"""
        return self.close > self.open
    
    def is_bearish(self) -> bool:
        """Check if candle is bearish"""
        return self.close < self.open


@dataclass
class PatternMatch:
    """Detected pattern match"""
    pattern_type: PatternType
    confidence: float
    signal: PatternSignal
    start_time: datetime
    end_time: datetime
    price_level: float
    volume_confirmation: bool = False
    
    # Pattern-specific data
    key_levels: List[float] = field(default_factory=list)
    pattern_data: Dict[str, Any] = field(default_factory=dict)
    
    # Technical indicators
    rsi: Optional[float] = None
    macd: Optional[float] = None
    bollinger_position: Optional[float] = None
    
    # Risk metrics
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    risk_reward_ratio: Optional[float] = None
    
    # Metadata
    timeframe: str = "1m"
    symbol: str = ""
    detection_time: datetime = field(default_factory=datetime.now)


class PatternDetector(ABC):
    """Abstract base class for pattern detectors"""
    
    @abstractmethod
    def detect(self, data: List[MarketData]) -> List[PatternMatch]:
        """Detect patterns in market data"""
        pass
    
    @abstractmethod
    def get_required_periods(self) -> int:
        """Get minimum number of periods required for detection"""
        pass


class CandlestickPatternDetector(PatternDetector):
    """Detector for candlestick patterns"""
    
    def __init__(self, min_body_ratio: float = 0.1, shadow_ratio: float = 2.0):
        self.min_body_ratio = min_body_ratio
        self.shadow_ratio = shadow_ratio
        self.logger = logging.getLogger(__name__)
    
    def get_required_periods(self) -> int:
        return 3  # Most candlestick patterns need 1-3 candles
    
    def detect(self, data: List[MarketData]) -> List[PatternMatch]:
        """Detect candlestick patterns"""
        if len(data) < self.get_required_periods():
            return []
        
        patterns = []
        
        # Single candle patterns
        patterns.extend(self._detect_doji(data))
        patterns.extend(self._detect_hammer(data))
        patterns.extend(self._detect_shooting_star(data))
        
        # Multi-candle patterns
        if len(data) >= 2:
            patterns.extend(self._detect_engulfing(data))
        
        if len(data) >= 3:
            patterns.extend(self._detect_morning_evening_star(data))
        
        return patterns
    
    def _detect_doji(self, data: List[MarketData]) -> List[PatternMatch]:
        """Detect Doji patterns"""
        patterns = []
        current = data[-1]
        
        # Doji: open and close are very close
        body_size = current.body_size()
        total_range = current.high - current.low
        
        if total_range > 0 and body_size / total_range < 0.1:
            confidence = 1.0 - (body_size / total_range) * 10
            
            patterns.append(PatternMatch(
                pattern_type=PatternType.DOJI,
                confidence=confidence,
                signal=PatternSignal.NEUTRAL,
                start_time=current.timestamp,
                end_time=current.timestamp,
                price_level=current.close,
                pattern_data={
                    'body_ratio': body_size / total_range,
                    'upper_shadow': current.upper_shadow(),
                    'lower_shadow': current.lower_shadow()
                }
            ))
        
        return patterns  
  
    def _detect_hammer(self, data: List[MarketData]) -> List[PatternMatch]:
        """Detect Hammer patterns"""
        patterns = []
        current = data[-1]
        
        body_size = current.body_size()
        lower_shadow = current.lower_shadow()
        upper_shadow = current.upper_shadow()
        total_range = current.high - current.low
        
        # Hammer: small body, long lower shadow, short upper shadow
        if (total_range > 0 and 
            lower_shadow > body_size * 2 and 
            upper_shadow < body_size and
            body_size / total_range > self.min_body_ratio):
            
            confidence = min(0.9, lower_shadow / (body_size + 0.001) * 0.2)
            
            patterns.append(PatternMatch(
                pattern_type=PatternType.HAMMER,
                confidence=confidence,
                signal=PatternSignal.BUY,
                start_time=current.timestamp,
                end_time=current.timestamp,
                price_level=current.close,
                pattern_data={
                    'body_size': body_size,
                    'lower_shadow': lower_shadow,
                    'upper_shadow': upper_shadow,
                    'shadow_ratio': lower_shadow / (body_size + 0.001)
                }
            ))
        
        return patterns
    
    def _detect_shooting_star(self, data: List[MarketData]) -> List[PatternMatch]:
        """Detect Shooting Star patterns"""
        patterns = []
        current = data[-1]
        
        body_size = current.body_size()
        lower_shadow = current.lower_shadow()
        upper_shadow = current.upper_shadow()
        total_range = current.high - current.low
        
        # Shooting Star: small body, long upper shadow, short lower shadow
        if (total_range > 0 and 
            upper_shadow > body_size * 2 and 
            lower_shadow < body_size and
            body_size / total_range > self.min_body_ratio):
            
            confidence = min(0.9, upper_shadow / (body_size + 0.001) * 0.2)
            
            patterns.append(PatternMatch(
                pattern_type=PatternType.SHOOTING_STAR,
                confidence=confidence,
                signal=PatternSignal.SELL,
                start_time=current.timestamp,
                end_time=current.timestamp,
                price_level=current.close,
                pattern_data={
                    'body_size': body_size,
                    'lower_shadow': lower_shadow,
                    'upper_shadow': upper_shadow,
                    'shadow_ratio': upper_shadow / (body_size + 0.001)
                }
            ))
        
        return patterns    

    def _detect_engulfing(self, data: List[MarketData]) -> List[PatternMatch]:
        """Detect Bullish/Bearish Engulfing patterns"""
        patterns = []
        if len(data) < 2:
            return patterns
        
        prev_candle = data[-2]
        current = data[-1]
        
        # Bullish Engulfing
        if (prev_candle.is_bearish() and current.is_bullish() and
            current.open < prev_candle.close and current.close > prev_candle.open):
            
            engulfing_ratio = current.body_size() / (prev_candle.body_size() + 0.001)
            confidence = min(0.9, engulfing_ratio * 0.5)
            
            patterns.append(PatternMatch(
                pattern_type=PatternType.ENGULFING_BULLISH,
                confidence=confidence,
                signal=PatternSignal.BUY,
                start_time=prev_candle.timestamp,
                end_time=current.timestamp,
                price_level=current.close,
                pattern_data={
                    'engulfing_ratio': engulfing_ratio,
                    'prev_body': prev_candle.body_size(),
                    'current_body': current.body_size()
                }
            ))
        
        # Bearish Engulfing
        elif (prev_candle.is_bullish() and current.is_bearish() and
              current.open > prev_candle.close and current.close < prev_candle.open):
            
            engulfing_ratio = current.body_size() / (prev_candle.body_size() + 0.001)
            confidence = min(0.9, engulfing_ratio * 0.5)
            
            patterns.append(PatternMatch(
                pattern_type=PatternType.ENGULFING_BEARISH,
                confidence=confidence,
                signal=PatternSignal.SELL,
                start_time=prev_candle.timestamp,
                end_time=current.timestamp,
                price_level=current.close,
                pattern_data={
                    'engulfing_ratio': engulfing_ratio,
                    'prev_body': prev_candle.body_size(),
                    'current_body': current.body_size()
                }
            ))
        
        return patterns
    
    def _detect_morning_evening_star(self, data: List[MarketData]) -> List[PatternMatch]:
        """Detect Morning Star and Evening Star patterns"""
        patterns = []
        if len(data) < 3:
            return patterns
        
        first = data[-3]
        middle = data[-2]
        last = data[-1]
        
        # Morning Star: bearish -> small body -> bullish
        if (first.is_bearish() and last.is_bullish() and
            middle.body_size() < first.body_size() * 0.5 and
            middle.body_size() < last.body_size() * 0.5 and
            last.close > (first.open + first.close) / 2):
            
            confidence = 0.7 + (last.close - first.close) / (first.high - first.low) * 0.2
            
            patterns.append(PatternMatch(
                pattern_type=PatternType.MORNING_STAR,
                confidence=min(0.9, confidence),
                signal=PatternSignal.BUY,
                start_time=first.timestamp,
                end_time=last.timestamp,
                price_level=last.close,
                pattern_data={
                    'first_body': first.body_size(),
                    'middle_body': middle.body_size(),
                    'last_body': last.body_size(),
                    'price_recovery': (last.close - first.close) / (first.high - first.low)
                }
            ))
        
        # Evening Star: bullish -> small body -> bearish
        elif (first.is_bullish() and last.is_bearish() and
              middle.body_size() < first.body_size() * 0.5 and
              middle.body_size() < last.body_size() * 0.5 and
              last.close < (first.open + first.close) / 2):
            
            confidence = 0.7 + (first.close - last.close) / (first.high - first.low) * 0.2
            
            patterns.append(PatternMatch(
                pattern_type=PatternType.EVENING_STAR,
                confidence=min(0.9, confidence),
                signal=PatternSignal.SELL,
                start_time=first.timestamp,
                end_time=last.timestamp,
                price_level=last.close,
                pattern_data={
                    'first_body': first.body_size(),
                    'middle_body': middle.body_size(),
                    'last_body': last.body_size(),
                    'price_decline': (first.close - last.close) / (first.high - first.low)
                }
            ))
        
        return patterns


class ChartPatternDetector(PatternDetector):
    """Detector for chart patterns like head and shoulders, triangles, etc."""
    
    def __init__(self, min_periods: int = 20, tolerance: float = 0.02):
        self.min_periods = min_periods
        self.tolerance = tolerance  # Price tolerance for pattern matching
        self.logger = logging.getLogger(__name__)
    
    def get_required_periods(self) -> int:
        return self.min_periods
    
    def detect(self, data: List[MarketData]) -> List[PatternMatch]:
        """Detect chart patterns"""
        if len(data) < self.min_periods:
            return []
        
        patterns = []
        
        # Convert to price arrays for analysis
        highs = np.array([d.high for d in data])
        lows = np.array([d.low for d in data])
        closes = np.array([d.close for d in data])
        
        # Detect various chart patterns
        patterns.extend(self._detect_head_and_shoulders(data, highs, lows))
        patterns.extend(self._detect_double_top_bottom(data, highs, lows))
        patterns.extend(self._detect_triangles(data, highs, lows))
        patterns.extend(self._detect_wedges(data, highs, lows))
        
        return patterns
    
    def _detect_head_and_shoulders(self, data: List[MarketData], highs: np.ndarray, lows: np.ndarray) -> List[PatternMatch]:
        """Detect Head and Shoulders patterns"""
        patterns = []
        
        if not SCIPY_AVAILABLE:
            return patterns
        
        # Find peaks in the price data
        peaks, _ = signal.find_peaks(highs, distance=5, prominence=np.std(highs) * 0.5)
        
        if len(peaks) >= 3:
            # Look for head and shoulders pattern in recent peaks
            for i in range(len(peaks) - 2):
                left_shoulder = peaks[i]
                head = peaks[i + 1]
                right_shoulder = peaks[i + 2]
                
                # Check if middle peak is higher (head)
                if (highs[head] > highs[left_shoulder] and 
                    highs[head] > highs[right_shoulder]):
                    
                    # Check if shoulders are roughly equal
                    shoulder_diff = abs(highs[left_shoulder] - highs[right_shoulder])
                    avg_shoulder = (highs[left_shoulder] + highs[right_shoulder]) / 2
                    
                    if shoulder_diff / avg_shoulder < self.tolerance * 2:
                        # Find neckline (lows between shoulders)
                        neckline_start = left_shoulder
                        neckline_end = right_shoulder
                        neckline_low = np.min(lows[neckline_start:neckline_end + 1])
                        
                        confidence = 0.8 - (shoulder_diff / avg_shoulder)
                        
                        patterns.append(PatternMatch(
                            pattern_type=PatternType.HEAD_AND_SHOULDERS,
                            confidence=min(0.9, confidence),
                            signal=PatternSignal.SELL,
                            start_time=data[left_shoulder].timestamp,
                            end_time=data[right_shoulder].timestamp,
                            price_level=neckline_low,
                            key_levels=[highs[left_shoulder], highs[head], highs[right_shoulder], neckline_low],
                            pattern_data={
                                'left_shoulder': highs[left_shoulder],
                                'head': highs[head],
                                'right_shoulder': highs[right_shoulder],
                                'neckline': neckline_low,
                                'shoulder_symmetry': 1 - (shoulder_diff / avg_shoulder)
                            }
                        ))
        
        # Inverse Head and Shoulders (using lows)
        troughs, _ = signal.find_peaks(-lows, distance=5, prominence=np.std(lows) * 0.5)
        
        if len(troughs) >= 3:
            for i in range(len(troughs) - 2):
                left_shoulder = troughs[i]
                head = troughs[i + 1]
                right_shoulder = troughs[i + 2]
                
                # Check if middle trough is lower (head)
                if (lows[head] < lows[left_shoulder] and 
                    lows[head] < lows[right_shoulder]):
                    
                    # Check if shoulders are roughly equal
                    shoulder_diff = abs(lows[left_shoulder] - lows[right_shoulder])
                    avg_shoulder = (lows[left_shoulder] + lows[right_shoulder]) / 2
                    
                    if shoulder_diff / avg_shoulder < self.tolerance * 2:
                        # Find neckline (highs between shoulders)
                        neckline_start = left_shoulder
                        neckline_end = right_shoulder
                        neckline_high = np.max(highs[neckline_start:neckline_end + 1])
                        
                        confidence = 0.8 - (shoulder_diff / avg_shoulder)
                        
                        patterns.append(PatternMatch(
                            pattern_type=PatternType.INVERSE_HEAD_AND_SHOULDERS,
                            confidence=min(0.9, confidence),
                            signal=PatternSignal.BUY,
                            start_time=data[left_shoulder].timestamp,
                            end_time=data[right_shoulder].timestamp,
                            price_level=neckline_high,
                            key_levels=[lows[left_shoulder], lows[head], lows[right_shoulder], neckline_high],
                            pattern_data={
                                'left_shoulder': lows[left_shoulder],
                                'head': lows[head],
                                'right_shoulder': lows[right_shoulder],
                                'neckline': neckline_high,
                                'shoulder_symmetry': 1 - (shoulder_diff / avg_shoulder)
                            }
                        ))
        
        return patterns    

    def _detect_double_top_bottom(self, data: List[MarketData], highs: np.ndarray, lows: np.ndarray) -> List[PatternMatch]:
        """Detect Double Top and Double Bottom patterns"""
        patterns = []
        
        if not SCIPY_AVAILABLE:
            return patterns
        
        # Double Top
        peaks, _ = signal.find_peaks(highs, distance=10, prominence=np.std(highs) * 0.3)
        
        if len(peaks) >= 2:
            for i in range(len(peaks) - 1):
                peak1 = peaks[i]
                peak2 = peaks[i + 1]
                
                # Check if peaks are roughly equal
                peak_diff = abs(highs[peak1] - highs[peak2])
                avg_peak = (highs[peak1] + highs[peak2]) / 2
                
                if peak_diff / avg_peak < self.tolerance:
                    # Find valley between peaks
                    valley_idx = peak1 + np.argmin(lows[peak1:peak2 + 1])
                    valley_low = lows[valley_idx]
                    
                    confidence = 0.7 + (1 - peak_diff / avg_peak) * 0.2
                    
                    patterns.append(PatternMatch(
                        pattern_type=PatternType.DOUBLE_TOP,
                        confidence=min(0.9, confidence),
                        signal=PatternSignal.SELL,
                        start_time=data[peak1].timestamp,
                        end_time=data[peak2].timestamp,
                        price_level=valley_low,
                        key_levels=[highs[peak1], highs[peak2], valley_low],
                        pattern_data={
                            'first_peak': highs[peak1],
                            'second_peak': highs[peak2],
                            'valley': valley_low,
                            'peak_symmetry': 1 - (peak_diff / avg_peak)
                        }
                    ))
        
        # Double Bottom
        troughs, _ = signal.find_peaks(-lows, distance=10, prominence=np.std(lows) * 0.3)
        
        if len(troughs) >= 2:
            for i in range(len(troughs) - 1):
                trough1 = troughs[i]
                trough2 = troughs[i + 1]
                
                # Check if troughs are roughly equal
                trough_diff = abs(lows[trough1] - lows[trough2])
                avg_trough = (lows[trough1] + lows[trough2]) / 2
                
                if trough_diff / avg_trough < self.tolerance:
                    # Find peak between troughs
                    peak_idx = trough1 + np.argmax(highs[trough1:trough2 + 1])
                    peak_high = highs[peak_idx]
                    
                    confidence = 0.7 + (1 - trough_diff / avg_trough) * 0.2
                    
                    patterns.append(PatternMatch(
                        pattern_type=PatternType.DOUBLE_BOTTOM,
                        confidence=min(0.9, confidence),
                        signal=PatternSignal.BUY,
                        start_time=data[trough1].timestamp,
                        end_time=data[trough2].timestamp,
                        price_level=peak_high,
                        key_levels=[lows[trough1], lows[trough2], peak_high],
                        pattern_data={
                            'first_trough': lows[trough1],
                            'second_trough': lows[trough2],
                            'peak': peak_high,
                            'trough_symmetry': 1 - (trough_diff / avg_trough)
                        }
                    ))
        
        return patterns
    
    def _detect_triangles(self, data: List[MarketData], highs: np.ndarray, lows: np.ndarray) -> List[PatternMatch]:
        """Detect Triangle patterns (Ascending, Descending, Symmetrical)"""
        patterns = []
        
        if len(data) < 20:
            return patterns
        
        # Use recent data for triangle detection
        recent_data = data[-20:]
        recent_highs = highs[-20:]
        recent_lows = lows[-20:]
        
        # Calculate trend lines
        x = np.arange(len(recent_highs))
        
        # Fit trend lines to highs and lows
        try:
            high_slope, high_intercept = np.polyfit(x, recent_highs, 1)
            low_slope, low_intercept = np.polyfit(x, recent_lows, 1)
            
            # Ascending Triangle: horizontal resistance, rising support
            if abs(high_slope) < 0.01 and low_slope > 0.01:
                convergence_point = len(recent_data) + (high_intercept - low_intercept) / (low_slope - high_slope)
                
                if 5 < convergence_point < 50:  # Reasonable convergence
                    patterns.append(PatternMatch(
                        pattern_type=PatternType.TRIANGLE_ASCENDING,
                        confidence=0.7,
                        signal=PatternSignal.BUY,
                        start_time=recent_data[0].timestamp,
                        end_time=recent_data[-1].timestamp,
                        price_level=recent_data[-1].close,
                        pattern_data={
                            'resistance_level': high_intercept + high_slope * (len(recent_data) - 1),
                            'support_slope': low_slope,
                            'convergence_distance': convergence_point
                        }
                    ))
            
            # Descending Triangle: falling resistance, horizontal support
            elif high_slope < -0.01 and abs(low_slope) < 0.01:
                convergence_point = len(recent_data) + (high_intercept - low_intercept) / (low_slope - high_slope)
                
                if 5 < convergence_point < 50:
                    patterns.append(PatternMatch(
                        pattern_type=PatternType.TRIANGLE_DESCENDING,
                        confidence=0.7,
                        signal=PatternSignal.SELL,
                        start_time=recent_data[0].timestamp,
                        end_time=recent_data[-1].timestamp,
                        price_level=recent_data[-1].close,
                        pattern_data={
                            'support_level': low_intercept + low_slope * (len(recent_data) - 1),
                            'resistance_slope': high_slope,
                            'convergence_distance': convergence_point
                        }
                    ))
            
            # Symmetrical Triangle: converging trend lines
            elif high_slope < -0.01 and low_slope > 0.01:
                convergence_point = (high_intercept - low_intercept) / (low_slope - high_slope)
                
                if 5 < convergence_point < 50:
                    patterns.append(PatternMatch(
                        pattern_type=PatternType.TRIANGLE_SYMMETRICAL,
                        confidence=0.6,
                        signal=PatternSignal.NEUTRAL,
                        start_time=recent_data[0].timestamp,
                        end_time=recent_data[-1].timestamp,
                        price_level=recent_data[-1].close,
                        pattern_data={
                            'resistance_slope': high_slope,
                            'support_slope': low_slope,
                            'convergence_point': convergence_point,
                            'apex_price': high_intercept + high_slope * convergence_point
                        }
                    ))
        
        except (np.linalg.LinAlgError, ValueError):
            # Handle cases where polyfit fails
            pass
        
        return patterns
    
    def _detect_wedges(self, data: List[MarketData], highs: np.ndarray, lows: np.ndarray) -> List[PatternMatch]:
        """Detect Wedge patterns (Rising and Falling)"""
        patterns = []
        
        if len(data) < 15:
            return patterns
        
        recent_data = data[-15:]
        recent_highs = highs[-15:]
        recent_lows = lows[-15:]
        
        x = np.arange(len(recent_highs))
        
        try:
            high_slope, high_intercept = np.polyfit(x, recent_highs, 1)
            low_slope, low_intercept = np.polyfit(x, recent_lows, 1)
            
            # Rising Wedge: both trend lines rising, but resistance rises slower
            if (high_slope > 0 and low_slope > 0 and 
                low_slope > high_slope and 
                (low_slope - high_slope) > 0.01):
                
                patterns.append(PatternMatch(
                    pattern_type=PatternType.WEDGE_RISING,
                    confidence=0.6,
                    signal=PatternSignal.SELL,
                    start_time=recent_data[0].timestamp,
                    end_time=recent_data[-1].timestamp,
                    price_level=recent_data[-1].close,
                    pattern_data={
                        'resistance_slope': high_slope,
                        'support_slope': low_slope,
                        'slope_difference': low_slope - high_slope
                    }
                ))
            
            # Falling Wedge: both trend lines falling, but support falls slower
            elif (high_slope < 0 and low_slope < 0 and 
                  high_slope < low_slope and 
                  (low_slope - high_slope) > 0.01):
                
                patterns.append(PatternMatch(
                    pattern_type=PatternType.WEDGE_FALLING,
                    confidence=0.6,
                    signal=PatternSignal.BUY,
                    start_time=recent_data[0].timestamp,
                    end_time=recent_data[-1].timestamp,
                    price_level=recent_data[-1].close,
                    pattern_data={
                        'resistance_slope': high_slope,
                        'support_slope': low_slope,
                        'slope_difference': low_slope - high_slope
                    }
                ))
        
        except (np.linalg.LinAlgError, ValueError):
            pass
        
        return patterns


class VolumePatternDetector(PatternDetector):
    """Detector for volume-based patterns"""
    
    def __init__(self, volume_spike_threshold: float = 2.0, lookback_periods: int = 20):
        self.volume_spike_threshold = volume_spike_threshold
        self.lookback_periods = lookback_periods
        self.logger = logging.getLogger(__name__)
    
    def get_required_periods(self) -> int:
        return self.lookback_periods
    
    def detect(self, data: List[MarketData]) -> List[PatternMatch]:
        """Detect volume patterns"""
        if len(data) < self.lookback_periods:
            return []
        
        patterns = []
        
        volumes = np.array([d.volume for d in data])
        prices = np.array([d.close for d in data])
        
        patterns.extend(self._detect_volume_spikes(data, volumes))
        patterns.extend(self._detect_volume_divergence(data, volumes, prices))
        patterns.extend(self._detect_accumulation_distribution(data, volumes, prices))
        
        return patterns
    
    def _detect_volume_spikes(self, data: List[MarketData], volumes: np.ndarray) -> List[PatternMatch]:
        """Detect volume spikes"""
        patterns = []
        
        if len(volumes) < self.lookback_periods:
            return patterns
        
        # Calculate rolling average volume
        avg_volume = np.mean(volumes[:-1])  # Exclude current period
        current_volume = volumes[-1]
        
        # Detect spike
        if current_volume > avg_volume * self.volume_spike_threshold:
            spike_ratio = current_volume / avg_volume
            confidence = min(0.9, (spike_ratio - 1) * 0.2)
            
            # Determine signal based on price movement
            current_candle = data[-1]
            signal = PatternSignal.BUY if current_candle.is_bullish() else PatternSignal.SELL
            
            patterns.append(PatternMatch(
                pattern_type=PatternType.VOLUME_SPIKE,
                confidence=confidence,
                signal=signal,
                start_time=current_candle.timestamp,
                end_time=current_candle.timestamp,
                price_level=current_candle.close,
                volume_confirmation=True,
                pattern_data={
                    'spike_ratio': spike_ratio,
                    'avg_volume': avg_volume,
                    'current_volume': current_volume,
                    'price_direction': 'bullish' if current_candle.is_bullish() else 'bearish'
                }
            ))
        
        return patterns
    
    def _detect_volume_divergence(self, data: List[MarketData], volumes: np.ndarray, prices: np.ndarray) -> List[PatternMatch]:
        """Detect price-volume divergence"""
        patterns = []
        
        if len(data) < 10:
            return patterns
        
        # Calculate recent trends
        recent_periods = 5
        recent_prices = prices[-recent_periods:]
        recent_volumes = volumes[-recent_periods:]
        
        # Price trend
        price_slope = np.polyfit(range(recent_periods), recent_prices, 1)[0]
        
        # Volume trend
        volume_slope = np.polyfit(range(recent_periods), recent_volumes, 1)[0]
        
        # Detect divergence
        if price_slope > 0 and volume_slope < 0:  # Rising price, falling volume
            confidence = 0.6
            patterns.append(PatternMatch(
                pattern_type=PatternType.VOLUME_DIVERGENCE,
                confidence=confidence,
                signal=PatternSignal.SELL,
                start_time=data[-recent_periods].timestamp,
                end_time=data[-1].timestamp,
                price_level=data[-1].close,
                pattern_data={
                    'price_trend': 'rising',
                    'volume_trend': 'falling',
                    'price_slope': price_slope,
                    'volume_slope': volume_slope
                }
            ))
        
        elif price_slope < 0 and volume_slope > 0:  # Falling price, rising volume
            confidence = 0.6
            patterns.append(PatternMatch(
                pattern_type=PatternType.VOLUME_DIVERGENCE,
                confidence=confidence,
                signal=PatternSignal.BUY,
                start_time=data[-recent_periods].timestamp,
                end_time=data[-1].timestamp,
                price_level=data[-1].close,
                pattern_data={
                    'price_trend': 'falling',
                    'volume_trend': 'rising',
                    'price_slope': price_slope,
                    'volume_slope': volume_slope
                }
            ))
        
        return patterns
    
    def _detect_accumulation_distribution(self, data: List[MarketData], volumes: np.ndarray, prices: np.ndarray) -> List[PatternMatch]:
        """Detect accumulation and distribution patterns"""
        patterns = []
        
        if len(data) < 10:
            return patterns
        
        # Calculate Accumulation/Distribution Line
        ad_line = []
        for i, candle in enumerate(data):
            if candle.high != candle.low:
                money_flow_multiplier = ((candle.close - candle.low) - (candle.high - candle.close)) / (candle.high - candle.low)
                money_flow_volume = money_flow_multiplier * candle.volume
                
                if i == 0:
                    ad_line.append(money_flow_volume)
                else:
                    ad_line.append(ad_line[-1] + money_flow_volume)
            else:
                ad_line.append(ad_line[-1] if ad_line else 0)
        
        # Analyze recent trend in A/D line
        if len(ad_line) >= 5:
            recent_ad = ad_line[-5:]
            ad_slope = np.polyfit(range(5), recent_ad, 1)[0]
            
            # Strong accumulation
            if ad_slope > np.std(ad_line) * 0.5:
                patterns.append(PatternMatch(
                    pattern_type=PatternType.ACCUMULATION,
                    confidence=0.7,
                    signal=PatternSignal.BUY,
                    start_time=data[-5].timestamp,
                    end_time=data[-1].timestamp,
                    price_level=data[-1].close,
                    volume_confirmation=True,
                    pattern_data={
                        'ad_slope': ad_slope,
                        'ad_current': ad_line[-1],
                        'strength': 'strong' if ad_slope > np.std(ad_line) else 'moderate'
                    }
                ))
            
            # Strong distribution
            elif ad_slope < -np.std(ad_line) * 0.5:
                patterns.append(PatternMatch(
                    pattern_type=PatternType.DISTRIBUTION,
                    confidence=0.7,
                    signal=PatternSignal.SELL,
                    start_time=data[-5].timestamp,
                    end_time=data[-1].timestamp,
                    price_level=data[-1].close,
                    volume_confirmation=True,
                    pattern_data={
                        'ad_slope': ad_slope,
                        'ad_current': ad_line[-1],
                        'strength': 'strong' if abs(ad_slope) > np.std(ad_line) else 'moderate'
                    }
                ))
        
        return patterns


class AnomalyDetector(PatternDetector):
    """Detector for market anomalies and unusual patterns"""
    
    def __init__(self, z_score_threshold: float = 2.5, lookback_periods: int = 50):
        self.z_score_threshold = z_score_threshold
        self.lookback_periods = lookback_periods
        self.logger = logging.getLogger(__name__)
    
    def get_required_periods(self) -> int:
        return self.lookback_periods
    
    def detect(self, data: List[MarketData]) -> List[PatternMatch]:
        """Detect anomalous patterns"""
        if len(data) < self.lookback_periods:
            return []
        
        patterns = []
        
        prices = np.array([d.close for d in data])
        volumes = np.array([d.volume for d in data])
        returns = np.diff(np.log(prices))
        
        patterns.extend(self._detect_price_anomalies(data, prices, returns))
        patterns.extend(self._detect_volume_anomalies(data, volumes))
        
        return patterns
    
    def _detect_price_anomalies(self, data: List[MarketData], prices: np.ndarray, returns: np.ndarray) -> List[PatternMatch]:
        """Detect price anomalies using statistical methods"""
        patterns = []
        
        if len(returns) < 2:
            return patterns
        
        # Calculate z-score for latest return
        mean_return = np.mean(returns[:-1])
        std_return = np.std(returns[:-1])
        
        if std_return > 0:
            latest_return = returns[-1]
            z_score = abs(latest_return - mean_return) / std_return
            
            if z_score > self.z_score_threshold:
                confidence = min(0.9, (z_score - self.z_score_threshold) * 0.2 + 0.5)
                
                # Determine signal based on direction
                signal = PatternSignal.STRONG_BUY if latest_return > 0 else PatternSignal.STRONG_SELL
                
                patterns.append(PatternMatch(
                    pattern_type=PatternType.PRICE_ANOMALY,
                    confidence=confidence,
                    signal=signal,
                    start_time=data[-1].timestamp,
                    end_time=data[-1].timestamp,
                    price_level=data[-1].close,
                    pattern_data={
                        'z_score': z_score,
                        'return': latest_return,
                        'mean_return': mean_return,
                        'std_return': std_return,
                        'anomaly_type': 'positive' if latest_return > 0 else 'negative'
                    }
                ))
        
        return patterns
    
    def _detect_volume_anomalies(self, data: List[MarketData], volumes: np.ndarray) -> List[PatternMatch]:
        """Detect volume anomalies"""
        patterns = []
        
        if len(volumes) < 2:
            return patterns
        
        # Calculate z-score for latest volume
        mean_volume = np.mean(volumes[:-1])
        std_volume = np.std(volumes[:-1])
        
        if std_volume > 0:
            latest_volume = volumes[-1]
            z_score = (latest_volume - mean_volume) / std_volume
            
            if z_score > self.z_score_threshold:
                confidence = min(0.9, (z_score - self.z_score_threshold) * 0.1 + 0.6)
                
                # Volume spike usually indicates strong interest
                current_candle = data[-1]
                signal = PatternSignal.BUY if current_candle.is_bullish() else PatternSignal.SELL
                
                patterns.append(PatternMatch(
                    pattern_type=PatternType.VOLUME_ANOMALY,
                    confidence=confidence,
                    signal=signal,
                    start_time=current_candle.timestamp,
                    end_time=current_candle.timestamp,
                    price_level=current_candle.close,
                    volume_confirmation=True,
                    pattern_data={
                        'volume_z_score': z_score,
                        'volume': latest_volume,
                        'mean_volume': mean_volume,
                        'std_volume': std_volume,
                        'volume_ratio': latest_volume / mean_volume
                    }
                ))
        
        return patterns


class PatternRecognitionEngine:
    """
    Main pattern recognition engine that coordinates multiple detectors
    
    Features:
    - Multiple pattern detector integration
    - Real-time pattern detection
    - Pattern confidence scoring
    - Signal generation and filtering
    - Performance monitoring
    - Pattern history tracking
    """
    
    def __init__(self, 
                 enable_candlestick: bool = True,
                 enable_chart_patterns: bool = True,
                 enable_volume_patterns: bool = True,
                 enable_anomaly_detection: bool = True,
                 min_confidence: float = 0.5,
                 max_patterns_per_detection: int = 10):
        
        self.enable_candlestick = enable_candlestick
        self.enable_chart_patterns = enable_chart_patterns
        self.enable_volume_patterns = enable_volume_patterns
        self.enable_anomaly_detection = enable_anomaly_detection
        self.min_confidence = min_confidence
        self.max_patterns_per_detection = max_patterns_per_detection
        
        # Initialize detectors
        self.detectors: List[PatternDetector] = []
        
        if enable_candlestick:
            self.detectors.append(CandlestickPatternDetector())
        
        if enable_chart_patterns:
            self.detectors.append(ChartPatternDetector())
        
        if enable_volume_patterns:
            self.detectors.append(VolumePatternDetector())
        
        if enable_anomaly_detection:
            self.detectors.append(AnomalyDetector())
        
        # Pattern history
        self._pattern_history: deque = deque(maxlen=1000)
        self._detection_count = 0
        self._last_detection_time = None
        
        # Performance metrics
        self._metrics = {
            'total_detections': 0,
            'patterns_found': 0,
            'avg_confidence': 0.0,
            'detection_time_ms': 0.0,
            'pattern_type_counts': {},
            'signal_distribution': {signal.value: 0 for signal in PatternSignal}
        }
        
        self.logger = logging.getLogger(__name__)
    
    async def detect_patterns(self, data: List[MarketData], symbol: str = "") -> List[PatternMatch]:
        """
        Detect patterns in market data using all enabled detectors
        
        Args:
            data: List of market data points
            symbol: Symbol identifier
            
        Returns:
            List of detected patterns sorted by confidence
        """
        start_time = time.time()
        
        if not data:
            return []
        
        all_patterns = []
        
        # Run each detector
        for detector in self.detectors:
            try:
                if len(data) >= detector.get_required_periods():
                    detector_patterns = detector.detect(data)
                    
                    # Add symbol and timeframe info
                    for pattern in detector_patterns:
                        pattern.symbol = symbol
                        pattern.timeframe = self._infer_timeframe(data)
                    
                    all_patterns.extend(detector_patterns)
                    
            except Exception as e:
                self.logger.error(f"Error in detector {type(detector).__name__}: {e}")
        
        # Filter by confidence
        filtered_patterns = [p for p in all_patterns if p.confidence >= self.min_confidence]
        
        # Sort by confidence (highest first)
        filtered_patterns.sort(key=lambda x: x.confidence, reverse=True)
        
        # Limit number of patterns
        final_patterns = filtered_patterns[:self.max_patterns_per_detection]
        
        # Update metrics
        detection_time = (time.time() - start_time) * 1000
        self._update_metrics(final_patterns, detection_time)
        
        # Store in history
        for pattern in final_patterns:
            self._pattern_history.append(pattern)
        
        self._last_detection_time = datetime.now()
        
        return final_patterns
    
    def _infer_timeframe(self, data: List[MarketData]) -> str:
        """Infer timeframe from data timestamps"""
        if len(data) < 2:
            return "unknown"
        
        time_diff = (data[-1].timestamp - data[-2].timestamp).total_seconds()
        
        if time_diff <= 60:
            return "1m"
        elif time_diff <= 300:
            return "5m"
        elif time_diff <= 900:
            return "15m"
        elif time_diff <= 3600:
            return "1h"
        elif time_diff <= 86400:
            return "1d"
        else:
            return "unknown"
    
    def _update_metrics(self, patterns: List[PatternMatch], detection_time_ms: float):
        """Update performance metrics"""
        self._metrics['total_detections'] += 1
        self._metrics['patterns_found'] += len(patterns)
        self._metrics['detection_time_ms'] = detection_time_ms
        
        if patterns:
            # Update average confidence
            total_confidence = sum(p.confidence for p in patterns)
            pattern_count = self._metrics['patterns_found']
            
            if pattern_count > 0:
                self._metrics['avg_confidence'] = (
                    (self._metrics['avg_confidence'] * (pattern_count - len(patterns)) + total_confidence) / pattern_count
                )
            
            # Update pattern type counts
            for pattern in patterns:
                pattern_type = pattern.pattern_type.value
                self._metrics['pattern_type_counts'][pattern_type] = (
                    self._metrics['pattern_type_counts'].get(pattern_type, 0) + 1
                )
                
                # Update signal distribution
                self._metrics['signal_distribution'][pattern.signal.value] += 1
    
    def get_pattern_history(self, 
                          pattern_type: Optional[PatternType] = None,
                          symbol: Optional[str] = None,
                          hours_back: int = 24) -> List[PatternMatch]:
        """Get historical patterns with optional filtering"""
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        filtered_patterns = []
        for pattern in self._pattern_history:
            # Time filter
            if pattern.detection_time < cutoff_time:
                continue
            
            # Pattern type filter
            if pattern_type and pattern.pattern_type != pattern_type:
                continue
            
            # Symbol filter
            if symbol and pattern.symbol != symbol:
                continue
            
            filtered_patterns.append(pattern)
        
        return filtered_patterns
    
    def get_pattern_statistics(self) -> Dict[str, Any]:
        """Get comprehensive pattern recognition statistics"""
        return {
            'metrics': self._metrics.copy(),
            'detector_count': len(self.detectors),
            'enabled_detectors': {
                'candlestick': self.enable_candlestick,
                'chart_patterns': self.enable_chart_patterns,
                'volume_patterns': self.enable_volume_patterns,
                'anomaly_detection': self.enable_anomaly_detection
            },
            'configuration': {
                'min_confidence': self.min_confidence,
                'max_patterns_per_detection': self.max_patterns_per_detection
            },
            'history_size': len(self._pattern_history),
            'last_detection': self._last_detection_time.isoformat() if self._last_detection_time else None
        }
    
    def get_signal_summary(self, hours_back: int = 1) -> Dict[str, Any]:
        """Get summary of recent trading signals"""
        recent_patterns = self.get_pattern_history(hours_back=hours_back)
        
        if not recent_patterns:
            return {
                'total_patterns': 0,
                'signals': {},
                'avg_confidence': 0.0,
                'strongest_signal': None
            }
        
        # Count signals
        signal_counts = {}
        for pattern in recent_patterns:
            signal = pattern.signal.value
            signal_counts[signal] = signal_counts.get(signal, 0) + 1
        
        # Find strongest signal
        strongest_pattern = max(recent_patterns, key=lambda x: x.confidence)
        
        return {
            'total_patterns': len(recent_patterns),
            'signals': signal_counts,
            'avg_confidence': sum(p.confidence for p in recent_patterns) / len(recent_patterns),
            'strongest_signal': {
                'pattern_type': strongest_pattern.pattern_type.value,
                'signal': strongest_pattern.signal.value,
                'confidence': strongest_pattern.confidence,
                'symbol': strongest_pattern.symbol,
                'detection_time': strongest_pattern.detection_time.isoformat()
            }
        }
    
    async def analyze_symbol(self, symbol: str, data: List[MarketData]) -> Dict[str, Any]:
        """Comprehensive pattern analysis for a specific symbol"""
        patterns = await self.detect_patterns(data, symbol)
        
        analysis = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'data_points': len(data),
            'patterns_detected': len(patterns),
            'patterns': []
        }
        
        for pattern in patterns:
            pattern_info = {
                'type': pattern.pattern_type.value,
                'signal': pattern.signal.value,
                'confidence': pattern.confidence,
                'price_level': pattern.price_level,
                'timeframe': pattern.timeframe,
                'start_time': pattern.start_time.isoformat(),
                'end_time': pattern.end_time.isoformat(),
                'volume_confirmation': pattern.volume_confirmation,
                'key_levels': pattern.key_levels,
                'pattern_data': pattern.pattern_data
            }
            
            # Add risk metrics if available
            if pattern.stop_loss:
                pattern_info['stop_loss'] = pattern.stop_loss
            if pattern.take_profit:
                pattern_info['take_profit'] = pattern.take_profit
            if pattern.risk_reward_ratio:
                pattern_info['risk_reward_ratio'] = pattern.risk_reward_ratio
            
            analysis['patterns'].append(pattern_info)
        
        # Add overall assessment
        if patterns:
            bullish_patterns = [p for p in patterns if p.signal in [PatternSignal.BUY, PatternSignal.STRONG_BUY]]
            bearish_patterns = [p for p in patterns if p.signal in [PatternSignal.SELL, PatternSignal.STRONG_SELL]]
            
            bullish_score = sum(p.confidence for p in bullish_patterns)
            bearish_score = sum(p.confidence for p in bearish_patterns)
            
            if bullish_score > bearish_score * 1.2:
                overall_signal = "BULLISH"
            elif bearish_score > bullish_score * 1.2:
                overall_signal = "BEARISH"
            else:
                overall_signal = "NEUTRAL"
            
            analysis['overall_assessment'] = {
                'signal': overall_signal,
                'bullish_score': bullish_score,
                'bearish_score': bearish_score,
                'confidence': max(bullish_score, bearish_score) / len(patterns)
            }
        else:
            analysis['overall_assessment'] = {
                'signal': 'NEUTRAL',
                'bullish_score': 0.0,
                'bearish_score': 0.0,
                'confidence': 0.0
            }
        
        return analysis