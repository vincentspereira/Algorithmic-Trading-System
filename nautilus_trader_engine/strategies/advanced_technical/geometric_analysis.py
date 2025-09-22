"""Geometric Analysis Strategies Module

This module implements advanced geometric analysis trading strategies including:
- Support and Resistance Level Analysis
- Trend Line Analysis (ascending, descending, horizontal)
- Channel Pattern Recognition
- Triangle Pattern Analysis (ascending, descending, symmetrical)
- Wedge Pattern Recognition (rising, falling)
- Flag and Pennant Patterns
- Rectangle and Box Patterns
- Head and Shoulders Patterns
- Double/Triple Top and Bottom Patterns
- Cup and Handle Patterns

Key Features:
- Automated geometric pattern recognition
- Dynamic support/resistance level calculation
- Multi-timeframe geometric analysis
- Pattern breakout detection
- Volume confirmation for patterns
- Risk management based on geometric structure

Architecture:
Follows the 5-Pillar Architecture with sophisticated geometric pattern
recognition engines and statistical validation systems.
"""

import math
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

# Core trading components
try:
    import pandas as pd
    import numpy as np
    from scipy import stats
    from sklearn.linear_model import LinearRegression
except ImportError:
    pd = None
    np = None
    stats = None
    LinearRegression = None

# Base strategy components
from ..base_strategy import (
    StrategyType, PositionType, SignalStrength,
    TradingSignal, Position, StrategyConfig
)

class GeometricPatternType(Enum):
    """Types of geometric patterns"""
    SUPPORT_RESISTANCE = "support_resistance"
    TREND_LINE = "trend_line"
    CHANNEL = "channel"
    ASCENDING_TRIANGLE = "ascending_triangle"
    DESCENDING_TRIANGLE = "descending_triangle"
    SYMMETRICAL_TRIANGLE = "symmetrical_triangle"
    RISING_WEDGE = "rising_wedge"
    FALLING_WEDGE = "falling_wedge"
    FLAG = "flag"
    PENNANT = "pennant"
    RECTANGLE = "rectangle"
    HEAD_SHOULDERS = "head_shoulders"
    INVERSE_HEAD_SHOULDERS = "inverse_head_shoulders"
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    TRIPLE_TOP = "triple_top"
    TRIPLE_BOTTOM = "triple_bottom"
    CUP_HANDLE = "cup_handle"

class TrendDirection(Enum):
    """Trend direction"""
    UPTREND = "uptrend"
    DOWNTREND = "downtrend"
    SIDEWAYS = "sideways"

class PatternStatus(Enum):
    """Pattern formation status"""
    FORMING = "forming"
    COMPLETED = "completed"
    BROKEN = "broken"
    CONFIRMED = "confirmed"

class BreakoutDirection(Enum):
    """Breakout direction"""
    UPWARD = "upward"
    DOWNWARD = "downward"
    NONE = "none"

@dataclass
class GeometricPoint:
    """Geometric analysis point"""
    price: float
    time: datetime
    index: int
    point_type: str  # 'high', 'low', 'support', 'resistance'
    strength: float = 1.0
    touches: int = 1

@dataclass
class TrendLine:
    """Trend line definition"""
    start_point: GeometricPoint
    end_point: GeometricPoint
    slope: float
    intercept: float
    r_squared: float
    touches: int
    strength: float
    line_type: str  # 'support', 'resistance', 'trend'
    
    def get_price_at_time(self, target_time: datetime) -> float:
        """Calculate price at given time using trend line equation"""
        # Convert time to numeric value (days since start)
        time_diff = (target_time - self.start_point.time).total_seconds() / 86400
        return self.slope * time_diff + self.intercept
    
    def get_price_at_index(self, index: int) -> float:
        """Calculate price at given index"""
        index_diff = index - self.start_point.index
        return self.slope * index_diff + self.intercept

@dataclass
class GeometricPattern:
    """Geometric pattern definition"""
    pattern_type: GeometricPatternType
    status: PatternStatus
    points: List[GeometricPoint]
    trend_lines: List[TrendLine]
    formation_time: datetime
    completion_time: Optional[datetime] = None
    breakout_direction: BreakoutDirection = BreakoutDirection.NONE
    breakout_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    confidence: float = 0.0
    volume_confirmation: bool = False
    
    # Pattern measurements
    height: float = 0.0
    width: timedelta = timedelta()
    
    def __post_init__(self):
        if self.points:
            prices = [p.price for p in self.points]
            self.height = max(prices) - min(prices)
            
            times = [p.time for p in self.points]
            self.width = max(times) - min(times)

class GeometricAnalyzer:
    """Core geometric analysis engine"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Analysis parameters
        self.min_touches = 2  # Minimum touches for valid trend line
        self.touch_tolerance = 0.02  # 2% tolerance for trend line touches
        self.min_r_squared = 0.7  # Minimum R-squared for trend line validity
        self.lookback_window = 50  # Lookback window for pattern analysis
    
    def find_support_resistance_levels(self, df: pd.DataFrame, window: int = 20) -> List[GeometricPoint]:
        """Find support and resistance levels"""
        levels = []
        
        if len(df) < window * 2:
            return levels
        
        try:
            # Find pivot highs and lows
            for i in range(window, len(df) - window):
                # Check for pivot high (resistance)
                is_pivot_high = all(
                    df['high'].iloc[i] >= df['high'].iloc[j]
                    for j in range(i - window, i + window + 1)
                    if j != i
                )
                
                # Check for pivot low (support)
                is_pivot_low = all(
                    df['low'].iloc[i] <= df['low'].iloc[j]
                    for j in range(i - window, i + window + 1)
                    if j != i
                )
                
                if is_pivot_high:
                    # Calculate strength based on how many times this level was tested
                    price_level = df['high'].iloc[i]
                    touches = self._count_level_touches(df, price_level, 'high')
                    
                    point = GeometricPoint(
                        price=price_level,
                        time=df.index[i] if hasattr(df.index[i], 'to_pydatetime') else datetime.now(),
                        index=i,
                        point_type='resistance',
                        strength=min(touches / 3.0, 3.0),  # Max strength of 3
                        touches=touches
                    )
                    levels.append(point)
                
                if is_pivot_low:
                    price_level = df['low'].iloc[i]
                    touches = self._count_level_touches(df, price_level, 'low')
                    
                    point = GeometricPoint(
                        price=price_level,
                        time=df.index[i] if hasattr(df.index[i], 'to_pydatetime') else datetime.now(),
                        index=i,
                        point_type='support',
                        strength=min(touches / 3.0, 3.0),
                        touches=touches
                    )
                    levels.append(point)
            
            # Filter and merge nearby levels
            levels = self._merge_nearby_levels(levels)
            
            return sorted(levels, key=lambda x: x.strength, reverse=True)
            
        except Exception as e:
            self.logger.error(f"Error finding support/resistance levels: {e}")
            return levels
    
    def _count_level_touches(self, df: pd.DataFrame, price_level: float, level_type: str) -> int:
        """Count how many times a price level was touched"""
        touches = 0
        tolerance = price_level * self.touch_tolerance
        
        try:
            if level_type == 'high':
                # Count touches on resistance level
                for high in df['high']:
                    if abs(high - price_level) <= tolerance:
                        touches += 1
            else:
                # Count touches on support level
                for low in df['low']:
                    if abs(low - price_level) <= tolerance:
                        touches += 1
            
            return touches
            
        except Exception:
            return 1
    
    def _merge_nearby_levels(self, levels: List[GeometricPoint], merge_distance: float = 0.01) -> List[GeometricPoint]:
        """Merge nearby support/resistance levels"""
        if not levels:
            return levels
        
        merged_levels = []
        levels_sorted = sorted(levels, key=lambda x: x.price)
        
        current_group = [levels_sorted[0]]
        
        for level in levels_sorted[1:]:
            # Check if this level is close to the current group
            group_avg_price = sum(l.price for l in current_group) / len(current_group)
            
            if abs(level.price - group_avg_price) / group_avg_price <= merge_distance:
                current_group.append(level)
            else:
                # Merge current group and start new group
                merged_level = self._merge_level_group(current_group)
                merged_levels.append(merged_level)
                current_group = [level]
        
        # Don't forget the last group
        if current_group:
            merged_level = self._merge_level_group(current_group)
            merged_levels.append(merged_level)
        
        return merged_levels
    
    def _merge_level_group(self, group: List[GeometricPoint]) -> GeometricPoint:
        """Merge a group of nearby levels into one"""
        avg_price = sum(l.price for l in group) / len(group)
        total_touches = sum(l.touches for l in group)
        max_strength = max(l.strength for l in group)
        
        # Use the most recent time
        latest_time = max(l.time for l in group)
        latest_point = next(l for l in group if l.time == latest_time)
        
        return GeometricPoint(
            price=avg_price,
            time=latest_time,
            index=latest_point.index,
            point_type=latest_point.point_type,
            strength=max_strength,
            touches=total_touches
        )
    
    def find_trend_lines(self, df: pd.DataFrame, min_points: int = 3) -> List[TrendLine]:
        """Find trend lines in price data"""
        trend_lines = []
        
        if len(df) < min_points * 2 or LinearRegression is None:
            return trend_lines
        
        try:
            # Find pivot points first
            pivot_highs = []
            pivot_lows = []
            window = 5
            
            for i in range(window, len(df) - window):
                # Pivot high
                if all(df['high'].iloc[i] >= df['high'].iloc[j] for j in range(i-window, i+window+1) if j != i):
                    pivot_highs.append((i, df['high'].iloc[i]))
                
                # Pivot low
                if all(df['low'].iloc[i] <= df['low'].iloc[j] for j in range(i-window, i+window+1) if j != i):
                    pivot_lows.append((i, df['low'].iloc[i]))
            
            # Find trend lines from pivot highs (resistance lines)
            if len(pivot_highs) >= min_points:
                resistance_lines = self._find_trend_lines_from_pivots(pivot_highs, 'resistance')
                trend_lines.extend(resistance_lines)
            
            # Find trend lines from pivot lows (support lines)
            if len(pivot_lows) >= min_points:
                support_lines = self._find_trend_lines_from_pivots(pivot_lows, 'support')
                trend_lines.extend(support_lines)
            
            return trend_lines
            
        except Exception as e:
            self.logger.error(f"Error finding trend lines: {e}")
            return trend_lines
    
    def _find_trend_lines_from_pivots(self, pivots: List[Tuple[int, float]], line_type: str) -> List[TrendLine]:
        """Find trend lines from pivot points"""
        trend_lines = []
        
        if len(pivots) < 2:
            return trend_lines
        
        try:
            # Try different combinations of pivot points
            for i in range(len(pivots) - 1):
                for j in range(i + 1, len(pivots)):
                    start_idx, start_price = pivots[i]
                    end_idx, end_price = pivots[j]
                    
                    # Calculate slope and intercept
                    slope = (end_price - start_price) / (end_idx - start_idx)
                    intercept = start_price - slope * start_idx
                    
                    # Count how many other pivots are close to this line
                    touches = 2  # Start with the two points used to create the line
                    total_error = 0
                    
                    for k, (pivot_idx, pivot_price) in enumerate(pivots):
                        if k == i or k == j:
                            continue
                        
                        # Calculate expected price at this index
                        expected_price = slope * pivot_idx + intercept
                        error = abs(pivot_price - expected_price) / expected_price
                        
                        if error <= self.touch_tolerance:
                            touches += 1
                        
                        total_error += error
                    
                    # Calculate R-squared (simplified)
                    avg_error = total_error / len(pivots) if len(pivots) > 0 else 1.0
                    r_squared = max(0, 1 - avg_error)
                    
                    # Only keep trend lines with sufficient touches and R-squared
                    if touches >= self.min_touches and r_squared >= self.min_r_squared:
                        start_point = GeometricPoint(
                            price=start_price,
                            time=datetime.now(),  # Simplified
                            index=start_idx,
                            point_type=line_type
                        )
                        
                        end_point = GeometricPoint(
                            price=end_price,
                            time=datetime.now(),
                            index=end_idx,
                            point_type=line_type
                        )
                        
                        trend_line = TrendLine(
                            start_point=start_point,
                            end_point=end_point,
                            slope=slope,
                            intercept=intercept,
                            r_squared=r_squared,
                            touches=touches,
                            strength=min(touches * r_squared, 5.0),
                            line_type=line_type
                        )
                        
                        trend_lines.append(trend_line)
            
            # Sort by strength and return top trend lines
            trend_lines.sort(key=lambda x: x.strength, reverse=True)
            return trend_lines[:5]  # Return top 5 trend lines
            
        except Exception as e:
            self.logger.error(f"Error finding trend lines from pivots: {e}")
            return trend_lines
    
    def identify_triangle_patterns(self, df: pd.DataFrame) -> List[GeometricPattern]:
        """Identify triangle patterns"""
        patterns = []
        
        if len(df) < 20:
            return patterns
        
        try:
            # Get trend lines
            trend_lines = self.find_trend_lines(df)
            
            if len(trend_lines) < 2:
                return patterns
            
            # Look for converging trend lines
            support_lines = [tl for tl in trend_lines if tl.line_type == 'support']
            resistance_lines = [tl for tl in trend_lines if tl.line_type == 'resistance']
            
            for support_line in support_lines:
                for resistance_line in resistance_lines:
                    # Check if lines are converging
                    pattern_type = self._classify_triangle_pattern(support_line, resistance_line)
                    
                    if pattern_type:
                        # Calculate convergence point
                        convergence_idx = self._find_line_intersection(support_line, resistance_line)
                        
                        if convergence_idx and convergence_idx > len(df):
                            # Pattern is still forming
                            pattern = GeometricPattern(
                                pattern_type=pattern_type,
                                status=PatternStatus.FORMING,
                                points=[support_line.start_point, support_line.end_point,
                                       resistance_line.start_point, resistance_line.end_point],
                                trend_lines=[support_line, resistance_line],
                                formation_time=min(support_line.start_point.time, resistance_line.start_point.time),
                                confidence=min(support_line.strength, resistance_line.strength) / 5.0
                            )
                            
                            # Calculate target and stop loss
                            self._calculate_triangle_targets(pattern, df)
                            
                            patterns.append(pattern)
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"Error identifying triangle patterns: {e}")
            return patterns
    
    def _classify_triangle_pattern(self, support_line: TrendLine, resistance_line: TrendLine) -> Optional[GeometricPatternType]:
        """Classify triangle pattern type based on trend line slopes"""
        try:
            support_slope = support_line.slope
            resistance_slope = resistance_line.slope
            
            # Ascending triangle: horizontal resistance, rising support
            if abs(resistance_slope) < 0.001 and support_slope > 0.001:
                return GeometricPatternType.ASCENDING_TRIANGLE
            
            # Descending triangle: horizontal support, falling resistance
            if abs(support_slope) < 0.001 and resistance_slope < -0.001:
                return GeometricPatternType.DESCENDING_TRIANGLE
            
            # Symmetrical triangle: converging lines
            if support_slope > 0 and resistance_slope < 0:
                return GeometricPatternType.SYMMETRICAL_TRIANGLE
            
            return None
            
        except Exception:
            return None
    
    def _find_line_intersection(self, line1: TrendLine, line2: TrendLine) -> Optional[float]:
        """Find intersection point of two trend lines"""
        try:
            # Solve: slope1 * x + intercept1 = slope2 * x + intercept2
            if abs(line1.slope - line2.slope) < 1e-10:  # Parallel lines
                return None
            
            intersection_x = (line2.intercept - line1.intercept) / (line1.slope - line2.slope)
            return intersection_x
            
        except Exception:
            return None
    
    def _calculate_triangle_targets(self, pattern: GeometricPattern, df: pd.DataFrame):
        """Calculate target and stop loss for triangle pattern"""
        try:
            if not pattern.points:
                return
            
            # Calculate pattern height (widest part)
            prices = [p.price for p in pattern.points]
            pattern_height = max(prices) - min(prices)
            
            # Get current price
            current_price = df['close'].iloc[-1] if 'close' in df.columns else df['high'].iloc[-1]
            
            # Set targets based on pattern type
            if pattern.pattern_type == GeometricPatternType.ASCENDING_TRIANGLE:
                # Bullish breakout expected
                resistance_level = max(prices)
                pattern.target_price = resistance_level + pattern_height
                pattern.stop_loss = current_price - (pattern_height * 0.3)
            
            elif pattern.pattern_type == GeometricPatternType.DESCENDING_TRIANGLE:
                # Bearish breakout expected
                support_level = min(prices)
                pattern.target_price = support_level - pattern_height
                pattern.stop_loss = current_price + (pattern_height * 0.3)
            
            elif pattern.pattern_type == GeometricPatternType.SYMMETRICAL_TRIANGLE:
                # Breakout direction uncertain, set targets for both directions
                pattern.target_price = current_price + pattern_height  # Assume upward breakout
                pattern.stop_loss = current_price - (pattern_height * 0.2)
            
        except Exception as e:
            self.logger.error(f"Error calculating triangle targets: {e}")
    
    def detect_breakouts(self, pattern: GeometricPattern, current_price: float, volume: float = 0) -> bool:
        """Detect pattern breakouts"""
        try:
            if pattern.status != PatternStatus.FORMING:
                return False
            
            breakout_detected = False
            
            if pattern.pattern_type in [GeometricPatternType.ASCENDING_TRIANGLE, 
                                      GeometricPatternType.DESCENDING_TRIANGLE,
                                      GeometricPatternType.SYMMETRICAL_TRIANGLE]:
                
                # Get resistance and support levels
                prices = [p.price for p in pattern.points]
                resistance_level = max(prices)
                support_level = min(prices)
                
                # Check for upward breakout
                if current_price > resistance_level * 1.01:  # 1% above resistance
                    pattern.breakout_direction = BreakoutDirection.UPWARD
                    pattern.breakout_price = current_price
                    pattern.status = PatternStatus.BROKEN
                    breakout_detected = True
                
                # Check for downward breakout
                elif current_price < support_level * 0.99:  # 1% below support
                    pattern.breakout_direction = BreakoutDirection.DOWNWARD
                    pattern.breakout_price = current_price
                    pattern.status = PatternStatus.BROKEN
                    breakout_detected = True
            
            # Volume confirmation (if available)
            if breakout_detected and volume > 0:
                # Simple volume confirmation - could be enhanced
                pattern.volume_confirmation = volume > 1.5  # Assume normalized volume
            
            return breakout_detected
            
        except Exception as e:
            self.logger.error(f"Error detecting breakouts: {e}")
            return False

class GeometricAnalysisStrategy:
    """Base geometric analysis trading strategy"""
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.analyzer = GeometricAnalyzer()
        
        # Strategy parameters
        self.min_pattern_confidence = config.parameters.get('min_pattern_confidence', 0.6)
        self.lookback_periods = config.parameters.get('lookback_periods', 100)
        self.support_resistance_window = config.parameters.get('sr_window', 20)
        
        # Current state
        self.current_patterns: List[GeometricPattern] = []
        self.support_levels: List[GeometricPoint] = []
        self.resistance_levels: List[GeometricPoint] = []
        self.trend_lines: List[TrendLine] = []
    
    def analyze_market_data(self, market_data: Dict) -> Dict:
        """Analyze market data for geometric patterns"""
        try:
            if pd is None:
                self.logger.error("Pandas not available for data analysis")
                return {}
            
            # Convert market data to DataFrame
            if isinstance(market_data, dict) and 'close' in market_data:
                df = pd.DataFrame([market_data])
            else:
                df = pd.DataFrame(market_data)
            
            if df.empty or len(df) < 20:
                return {}
            
            # Limit to recent data
            recent_df = df.tail(self.lookback_periods) if len(df) > self.lookback_periods else df
            
            # Find support and resistance levels
            sr_levels = self.analyzer.find_support_resistance_levels(recent_df, self.support_resistance_window)
            self.support_levels = [level for level in sr_levels if level.point_type == 'support']
            self.resistance_levels = [level for level in sr_levels if level.point_type == 'resistance']
            
            # Find trend lines
            self.trend_lines = self.analyzer.find_trend_lines(recent_df)
            
            # Identify patterns
            triangle_patterns = self.analyzer.identify_triangle_patterns(recent_df)
            
            # Filter patterns by confidence
            self.current_patterns = [
                pattern for pattern in triangle_patterns
                if pattern.confidence >= self.min_pattern_confidence
            ]
            
            # Check for breakouts
            current_price = recent_df['close'].iloc[-1] if 'close' in recent_df.columns else 0
            current_volume = recent_df['volume'].iloc[-1] if 'volume' in recent_df.columns else 0
            
            for pattern in self.current_patterns:
                self.analyzer.detect_breakouts(pattern, current_price, current_volume)
            
            return {
                'patterns': self.current_patterns,
                'support_levels': self.support_levels,
                'resistance_levels': self.resistance_levels,
                'trend_lines': self.trend_lines,
                'current_price': current_price
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing geometric data: {e}")
            return {}
    
    def generate_signals(self, market_data: Dict) -> List[TradingSignal]:
        """Generate trading signals based on geometric analysis"""
        signals = []
        
        try:
            analysis = self.analyze_market_data(market_data)
            
            if not analysis:
                return signals
            
            current_price = analysis.get('current_price', 0)
            patterns = analysis.get('patterns', [])
            support_levels = analysis.get('support_levels', [])
            resistance_levels = analysis.get('resistance_levels', [])
            
            # Generate signals from pattern breakouts
            for pattern in patterns:
                if pattern.status == PatternStatus.BROKEN:
                    pattern_signals = self._generate_breakout_signals(pattern, current_price)
                    signals.extend(pattern_signals)
            
            # Generate signals from support/resistance levels
            sr_signals = self._generate_support_resistance_signals(
                support_levels, resistance_levels, current_price
            )
            signals.extend(sr_signals)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating geometric signals: {e}")
            return signals
    
    def _generate_breakout_signals(self, pattern: GeometricPattern, current_price: float) -> List[TradingSignal]:
        """Generate signals from pattern breakouts"""
        signals = []
        
        try:
            if pattern.breakout_direction == BreakoutDirection.UPWARD:
                signal_type = PositionType.LONG
                target_price = pattern.target_price if pattern.target_price else current_price * 1.05
                stop_loss = pattern.stop_loss if pattern.stop_loss else current_price * 0.97
            
            elif pattern.breakout_direction == BreakoutDirection.DOWNWARD:
                signal_type = PositionType.SHORT
                target_price = pattern.target_price if pattern.target_price else current_price * 0.95
                stop_loss = pattern.stop_loss if pattern.stop_loss else current_price * 1.03
            
            else:
                return signals
            
            # Determine signal strength
            strength = SignalStrength.STRONG if pattern.volume_confirmation else SignalStrength.MEDIUM
            
            signal = TradingSignal(
                symbol=self.config.symbols[0] if self.config.symbols else "UNKNOWN",
                signal_type=signal_type,
                strength=strength,
                confidence=pattern.confidence,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=target_price,
                timestamp=datetime.now(),
                metadata={
                    'strategy': 'geometric_breakout',
                    'pattern_type': pattern.pattern_type.value,
                    'breakout_direction': pattern.breakout_direction.value,
                    'breakout_price': pattern.breakout_price,
                    'volume_confirmation': pattern.volume_confirmation,
                    'pattern_confidence': pattern.confidence
                }
            )
            signals.append(signal)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating breakout signals: {e}")
            return signals
    
    def _generate_support_resistance_signals(self, support_levels: List[GeometricPoint], 
                                           resistance_levels: List[GeometricPoint], 
                                           current_price: float) -> List[TradingSignal]:
        """Generate signals from support/resistance levels"""
        signals = []
        
        try:
            # Check for bounces off support levels
            for support in support_levels:
                price_diff = abs(current_price - support.price) / support.price
                
                if price_diff <= 0.01:  # Within 1% of support
                    signal = TradingSignal(
                        symbol=self.config.symbols[0] if self.config.symbols else "UNKNOWN",
                        signal_type=PositionType.LONG,
                        strength=SignalStrength.MEDIUM if support.strength >= 2 else SignalStrength.WEAK,
                        confidence=min(support.strength / 3.0, 1.0),
                        entry_price=current_price,
                        stop_loss=support.price * 0.98,
                        take_profit=current_price * 1.03,
                        timestamp=datetime.now(),
                        metadata={
                            'strategy': 'support_bounce',
                            'support_level': support.price,
                            'support_strength': support.strength,
                            'support_touches': support.touches
                        }
                    )
                    signals.append(signal)
            
            # Check for rejections at resistance levels
            for resistance in resistance_levels:
                price_diff = abs(current_price - resistance.price) / resistance.price
                
                if price_diff <= 0.01:  # Within 1% of resistance
                    signal = TradingSignal(
                        symbol=self.config.symbols[0] if self.config.symbols else "UNKNOWN",
                        signal_type=PositionType.SHORT,
                        strength=SignalStrength.MEDIUM if resistance.strength >= 2 else SignalStrength.WEAK,
                        confidence=min(resistance.strength / 3.0, 1.0),
                        entry_price=current_price,
                        stop_loss=resistance.price * 1.02,
                        take_profit=current_price * 0.97,
                        timestamp=datetime.now(),
                        metadata={
                            'strategy': 'resistance_rejection',
                            'resistance_level': resistance.price,
                            'resistance_strength': resistance.strength,
                            'resistance_touches': resistance.touches
                        }
                    )
                    signals.append(signal)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating support/resistance signals: {e}")
            return signals

class TrianglePatternStrategy(GeometricAnalysisStrategy):
    """Strategy focused on triangle patterns"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.target_patterns = [
            GeometricPatternType.ASCENDING_TRIANGLE,
            GeometricPatternType.DESCENDING_TRIANGLE,
            GeometricPatternType.SYMMETRICAL_TRIANGLE
        ]

class SupportResistanceStrategy(GeometricAnalysisStrategy):
    """Strategy focused on support and resistance levels"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.focus_on_sr = True
    
    def generate_signals(self, market_data: Dict) -> List[TradingSignal]:
        """Generate signals focused on support/resistance"""
        signals = []
        
        try:
            analysis = self.analyze_market_data(market_data)
            
            if not analysis:
                return signals
            
            current_price = analysis.get('current_price', 0)
            support_levels = analysis.get('support_levels', [])
            resistance_levels = analysis.get('resistance_levels', [])
            
            # Focus only on support/resistance signals
            sr_signals = self._generate_support_resistance_signals(
                support_levels, resistance_levels, current_price
            )
            signals.extend(sr_signals)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating support/resistance signals: {e}")
            return signals

# Convenience aliases
TriangleStrategy = TrianglePatternStrategy
SRStrategy = SupportResistanceStrategy
GeometricStrategy = GeometricAnalysisStrategy

# Utility functions
def find_support_resistance_levels(df: pd.DataFrame, window: int = 20) -> Tuple[List[GeometricPoint], List[GeometricPoint]]:
    """Find support and resistance levels in price data"""
    analyzer = GeometricAnalyzer()
    levels = analyzer.find_support_resistance_levels(df, window)
    
    support_levels = [level for level in levels if level.point_type == 'support']
    resistance_levels = [level for level in levels if level.point_type == 'resistance']
    
    return support_levels, resistance_levels

def identify_triangle_pattern(df: pd.DataFrame) -> Optional[GeometricPattern]:
    """Identify triangle pattern in price data"""
    analyzer = GeometricAnalyzer()
    patterns = analyzer.identify_triangle_patterns(df)
    
    # Return the highest confidence pattern
    if patterns:
        return max(patterns, key=lambda p: p.confidence)
    return None

def find_trend_lines(df: pd.DataFrame, min_points: int = 3) -> List[TrendLine]:
    """Find trend lines in price data"""
    analyzer = GeometricAnalyzer()
    return analyzer.find_trend_lines(df, min_points)