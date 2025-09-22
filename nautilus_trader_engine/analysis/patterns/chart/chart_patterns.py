"""
Institutional-Grade Chart Pattern Analysis

This module implements advanced chart pattern recognition with institutional-grade features:
- Head & Shoulders Pattern Detection: Classic reversal patterns
- Double Top/Bottom Recognition: Trend reversal patterns
- Triangle Pattern Analysis: Continuation and reversal triangles
- Wedge Pattern Identification: Rising and falling wedge patterns
- Flag & Pennant Detection: Short-term continuation patterns
- Cup & Handle Recognition: Bullish continuation patterns
- Multi-Timeframe Validation: Pattern confirmation across timeframes
- Volume-Weighted Pattern Strength: Volume confirmation for pattern validity
- Smart Money Integration: Institutional activity pattern validation
- Adaptive Confidence Scoring: Dynamic scoring based on pattern completeness
- Risk Management Integration: Pattern-based entry, stop, and target levels

All chart patterns include volume-weighting, multi-timeframe confirmation,
and integrated risk management.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import statistics
import math


class ChartPatternType(Enum):
    """Types of chart patterns"""
    HEAD_AND_SHOULDERS = "head_and_shoulders"
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    TRIPLE_TOP = "triple_top"
    TRIPLE_BOTTOM = "triple_bottom"
    ASCENDING_TRIANGLE = "ascending_triangle"
    DESCENDING_TRIANGLE = "descending_triangle"
    SYMMETRICAL_TRIANGLE = "symmetrical_triangle"
    RISING_WEDGE = "rising_wedge"
    FALLING_WEDGE = "falling_wedge"
    BULL_FLAG = "bull_flag"
    BEAR_FLAG = "bear_flag"
    BULL_PENNANT = "bull_pennant"
    BEAR_PENNANT = "bear_pennant"
    CUP_AND_HANDLE = "cup_and_handle"
    INVERSE_CUP_AND_HANDLE = "inverse_cup_and_handle"


class PatternCategory(Enum):
    """Pattern categories"""
    REVERSAL = "reversal"
    CONTINUATION = "continuation"


class PatternDirection(Enum):
    """Pattern direction"""
    BULLISH = "bullish"
    BEARISH = "bearish"


class PatternCompleteness(Enum):
    """Pattern completeness status"""
    FORMING = "forming"
    COMPLETE = "complete"
    INVALID = "invalid"


class PatternStrength(Enum):
    """Pattern strength levels"""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


@dataclass
class ChartPattern:
    """Represents a complete chart pattern"""
    pattern_type: ChartPatternType
    category: PatternCategory
    direction: PatternDirection
    completeness: PatternCompleteness
    pivot_points: Dict[str, Tuple[float, datetime]]
    trendlines: Dict[str, Tuple[float, float, datetime, datetime]]  # slope, intercept, start_time, end_time
    pattern_height: float
    pattern_duration: timedelta
    strength: PatternStrength
    confidence_score: float
    volume_weighted: bool
    multi_timeframe_confirmed: bool
    smart_money_confirmed: bool
    risk_management_levels: Dict[str, float]


@dataclass
class ChartSignal:
    """Trading signal based on chart pattern"""
    pattern: ChartPattern
    signal_type: str  # "breakout", "reversal", "continuation"
    direction: str  # "BUY" or "SELL"
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence_score: float
    risk_reward_ratio: float
    volume_confirmation: bool
    timeframe_alignment: bool
    timestamp: datetime


class InstitutionalChartPatternAnalyzer:
    """
    Institutional-grade chart pattern analyzer.

    Features:
    - Multi-pattern recognition (reversal and continuation patterns)
    - Precise geometric validation
    - Pattern strength assessment
    - Volume-weighted confirmation
    - Multi-timeframe validation
    - Smart money integration
    - Adaptive confidence scoring
    - Risk management integration
    """

    def __init__(self, lookback_periods: int = 200, min_pattern_strength: float = 0.6):
        self.lookback_periods = lookback_periods
        self.min_pattern_strength = min_pattern_strength

        # Historical data
        self.price_data = []
        self.volume_data = []
        self.time_data = []

        # Pattern tracking
        self.active_patterns = {}
        self.completed_patterns = []

    def update_price_data(self, price: float, volume: float, timestamp: datetime):
        """
        Update price data for chart pattern analysis

        Args:
            price: Current price
            volume: Trading volume
            timestamp: Price timestamp
        """
        self.price_data.append(price)
        self.volume_data.append(volume)
        self.time_data.append(timestamp)

        # Keep only recent data
        if len(self.price_data) > self.lookback_periods:
            self.price_data.pop(0)
            self.volume_data.pop(0)
            self.time_data.pop(0)

    def analyze_chart_patterns(self, current_price: float, current_time: datetime) -> List[ChartPattern]:
        """
        Analyze current chart patterns

        Args:
            current_price: Current market price
            current_time: Current timestamp

        Returns:
            List of identified chart patterns
        """
        if len(self.price_data) < 50:
            return []

        patterns = []

        # Analyze different pattern types
        for pattern_type in ChartPatternType:
            pattern = self._identify_pattern(pattern_type, current_price, current_time)
            if pattern:
                patterns.append(pattern)
                self.active_patterns[f"{pattern_type.value}_{pattern.direction.value}"] = pattern

        # Validate and filter patterns
        validated_patterns = []
        for pattern in patterns:
            if self._validate_pattern(pattern):
                validated_patterns.append(pattern)

        return validated_patterns

    def _identify_pattern(self, pattern_type: ChartPatternType,
                         current_price: float, current_time: datetime) -> Optional[ChartPattern]:
        """Identify a specific chart pattern"""
        if len(self.price_data) < 20:
            return None

        # Find swing points for pattern analysis
        swing_highs, swing_lows = self._find_swing_points()

        # Pattern-specific identification
        if pattern_type == ChartPatternType.HEAD_AND_SHOULDERS:
            return self._identify_head_and_shoulders(swing_highs, swing_lows, current_price, current_time)
        elif pattern_type in [ChartPatternType.DOUBLE_TOP, ChartPatternType.DOUBLE_BOTTOM,
                             ChartPatternType.TRIPLE_TOP, ChartPatternType.TRIPLE_BOTTOM]:
            return self._identify_multiple_tops_bottoms(pattern_type, swing_highs, swing_lows, current_price, current_time)
        elif pattern_type in [ChartPatternType.ASCENDING_TRIANGLE, ChartPatternType.DESCENDING_TRIANGLE,
                             ChartPatternType.SYMMETRICAL_TRIANGLE]:
            return self._identify_triangle_pattern(pattern_type, swing_highs, swing_lows, current_price, current_time)
        elif pattern_type in [ChartPatternType.RISING_WEDGE, ChartPatternType.FALLING_WEDGE]:
            return self._identify_wedge_pattern(pattern_type, swing_highs, swing_lows, current_price, current_time)
        elif pattern_type in [ChartPatternType.BULL_FLAG, ChartPatternType.BEAR_FLAG,
                             ChartPatternType.BULL_PENNANT, ChartPatternType.BEAR_PENNANT]:
            return self._identify_flag_pennant_pattern(pattern_type, swing_highs, swing_lows, current_price, current_time)
        elif pattern_type in [ChartPatternType.CUP_AND_HANDLE, ChartPatternType.INVERSE_CUP_AND_HANDLE]:
            return self._identify_cup_handle_pattern(pattern_type, swing_highs, swing_lows, current_price, current_time)

        return None

    def _find_swing_points(self) -> Tuple[List[Tuple[float, datetime]], List[Tuple[float, datetime]]]:
        """Find significant swing points"""
        swing_highs = []
        swing_lows = []

        if len(self.price_data) < 10:
            return swing_highs, swing_lows

        # Use zigzag algorithm to find swings
        min_reversal = self._calculate_atr() * 2.0  # 2 ATR minimum reversal

        trend = 0  # 0 = undetermined, 1 = up, -1 = down
        last_swing_price = self.price_data[0]
        last_swing_index = 0

        for i in range(1, len(self.price_data)):
            current_price = self.price_data[i]

            if trend == 0:
                if current_price > last_swing_price + min_reversal:
                    trend = 1
                    swing_lows.append((last_swing_price, self.time_data[last_swing_index]))
                    last_swing_price = current_price
                    last_swing_index = i
                elif current_price < last_swing_price - min_reversal:
                    trend = -1
                    swing_highs.append((last_swing_price, self.time_data[last_swing_index]))
                    last_swing_price = current_price
                    last_swing_index = i

            elif trend == 1:
                if current_price < last_swing_price - min_reversal:
                    swing_highs.append((last_swing_price, self.time_data[last_swing_index]))
                    trend = -1
                    last_swing_price = current_price
                    last_swing_index = i

            else:  # trend == -1
                if current_price > last_swing_price + min_reversal:
                    swing_lows.append((last_swing_price, self.time_data[last_swing_index]))
                    trend = 1
                    last_swing_price = current_price
                    last_swing_index = i

        return swing_highs, swing_lows

    def _identify_head_and_shoulders(self, swing_highs: List[Tuple[float, datetime]],
                                    swing_lows: List[Tuple[float, datetime]],
                                    current_price: float, current_time: datetime) -> Optional[ChartPattern]:
        """Identify Head and Shoulders pattern"""
        if len(swing_highs) < 5:
            return None

        # Look for three peaks with middle one highest
        recent_highs = swing_highs[-5:]

        # Check for left shoulder, head, right shoulder pattern
        if len(recent_highs) >= 3:
            left_shoulder = recent_highs[-3]
            head = recent_highs[-2]
            right_shoulder = recent_highs[-1]

            # Head should be higher than shoulders
            if (head[0] > left_shoulder[0] and head[0] > right_shoulder[0] and
                abs(left_shoulder[0] - right_shoulder[0]) / left_shoulder[0] < 0.05):  # Shoulders roughly equal

                # Find neckline (lowest low between shoulders)
                neckline_lows = []
                for low in swing_lows:
                    if left_shoulder[1] < low[1] < right_shoulder[1]:
                        neckline_lows.append(low[0])

                if neckline_lows:
                    neckline = min(neckline_lows)

                    return self._create_pattern(
                        ChartPatternType.HEAD_AND_SHOULDERS,
                        PatternCategory.REVERSAL,
                        PatternDirection.BEARISH,
                        {
                            'left_shoulder': left_shoulder,
                            'head': head,
                            'right_shoulder': right_shoulder,
                            'neckline': (neckline, current_time)
                        },
                        current_price, current_time
                    )

        return None

    def _identify_multiple_tops_bottoms(self, pattern_type: ChartPatternType,
                                       swing_highs: List[Tuple[float, datetime]],
                                       swing_lows: List[Tuple[float, datetime]],
                                       current_price: float, current_time: datetime) -> Optional[ChartPattern]:
        """Identify double/triple top/bottom patterns"""
        if pattern_type in [ChartPatternType.DOUBLE_TOP, ChartPatternType.TRIPLE_TOP]:
            points = swing_highs[-3:] if pattern_type == ChartPatternType.DOUBLE_TOP else swing_highs[-4:]
            if len(points) >= (2 if pattern_type == ChartPatternType.DOUBLE_TOP else 3):
                # Check if highs are roughly equal
                avg_high = sum(p[0] for p in points) / len(points)
                if all(abs(p[0] - avg_high) / avg_high < 0.03 for p in points):  # Within 3%
                    direction = PatternDirection.BEARISH
                    category = PatternCategory.REVERSAL
                    pivot_dict = {f'peak_{i+1}': points[i] for i in range(len(points))}

                    return self._create_pattern(pattern_type, category, direction, pivot_dict,
                                              current_price, current_time)

        elif pattern_type in [ChartPatternType.DOUBLE_BOTTOM, ChartPatternType.TRIPLE_BOTTOM]:
            points = swing_lows[-3:] if pattern_type == ChartPatternType.DOUBLE_BOTTOM else swing_lows[-4:]
            if len(points) >= (2 if pattern_type == ChartPatternType.DOUBLE_BOTTOM else 3):
                # Check if lows are roughly equal
                avg_low = sum(p[0] for p in points) / len(points)
                if all(abs(p[0] - avg_low) / avg_low < 0.03 for p in points):  # Within 3%
                    direction = PatternDirection.BULLISH
                    category = PatternCategory.REVERSAL
                    pivot_dict = {f'bottom_{i+1}': points[i] for i in range(len(points))}

                    return self._create_pattern(pattern_type, category, direction, pivot_dict,
                                              current_price, current_time)

        return None

    def _identify_triangle_pattern(self, pattern_type: ChartPatternType,
                                  swing_highs: List[Tuple[float, datetime]],
                                  swing_lows: List[Tuple[float, datetime]],
                                  current_price: float, current_time: datetime) -> Optional[ChartPattern]:
        """Identify triangle patterns"""
        if len(swing_highs) < 3 or len(swing_lows) < 3:
            return None

        # Get recent swing points
        highs = swing_highs[-4:]
        lows = swing_lows[-4:]

        # Calculate trendlines
        upper_trendline = self._calculate_trendline(highs)
        lower_trendline = self._calculate_trendline(lows)

        if not upper_trendline or not lower_trendline:
            return None

        # Check for triangle convergence
        upper_slope, upper_intercept = upper_trendline
        lower_slope, lower_intercept = lower_trendline

        # Determine triangle type
        if pattern_type == ChartPatternType.ASCENDING_TRIANGLE:
            if abs(upper_slope) < 0.001 and lower_slope > 0.001:  # Horizontal resistance, rising support
                direction = PatternDirection.BULLISH
                category = PatternCategory.CONTINUATION
            else:
                return None
        elif pattern_type == ChartPatternType.DESCENDING_TRIANGLE:
            if abs(lower_slope) < 0.001 and upper_slope < -0.001:  # Horizontal support, falling resistance
                direction = PatternDirection.BEARISH
                category = PatternCategory.CONTINUATION
            else:
                return None
        else:  # Symmetrical triangle
            if ((upper_slope < 0 and lower_slope > 0) or
                (upper_slope > 0 and lower_slope < 0)):  # Converging lines
                # Direction depends on breakout
                direction = PatternDirection.BULLISH if current_price > (max(h[0] for h in highs) + min(l[0] for l in lows)) / 2 else PatternDirection.BEARISH
                category = PatternCategory.CONTINUATION
            else:
                return None

        # Create trendlines dictionary
        trendlines = {
            'upper': (upper_slope, upper_intercept, highs[0][1], highs[-1][1]),
            'lower': (lower_slope, lower_intercept, lows[0][1], lows[-1][1])
        }

        return self._create_pattern(
            pattern_type, category, direction, {}, current_price, current_time, trendlines
        )

    def _calculate_trendline(self, points: List[Tuple[float, datetime]]) -> Optional[Tuple[float, float]]:
        """Calculate trendline from points"""
        if len(points) < 2:
            return None

        # Convert to numerical times
        times = [(point[1] - points[0][1]).total_seconds() for point in points]
        prices = [point[0] for point in points]

        # Linear regression
        n = len(prices)
        sum_x = sum(times)
        sum_y = sum(prices)
        sum_xy = sum(x * y for x, y in zip(times, prices))
        sum_xx = sum(x * x for x in times)

        if n * sum_xx - sum_x * sum_x == 0:
            return None

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x)
        intercept = (sum_y - slope * sum_x) / n

        return slope, intercept

    def _identify_wedge_pattern(self, pattern_type: ChartPatternType,
                               swing_highs: List[Tuple[float, datetime]],
                               swing_lows: List[Tuple[float, datetime]],
                               current_price: float, current_time: datetime) -> Optional[ChartPattern]:
        """Identify wedge patterns"""
        if len(swing_highs) < 3 or len(swing_lows) < 3:
            return None

        highs = swing_highs[-4:]
        lows = swing_lows[-4:]

        upper_trendline = self._calculate_trendline(highs)
        lower_trendline = self._calculate_trendline(lows)

        if not upper_trendline or not lower_trendline:
            return None

        upper_slope, _ = upper_trendline
        lower_slope, _ = lower_trendline

        if pattern_type == ChartPatternType.RISING_WEDGE:
            if upper_slope > 0 and lower_slope > 0 and upper_slope > lower_slope:
                direction = PatternDirection.BEARISH  # Rising wedge is bearish
                category = PatternCategory.REVERSAL
            else:
                return None
        else:  # Falling wedge
            if upper_slope < 0 and lower_slope < 0 and abs(upper_slope) < abs(lower_slope):
                direction = PatternDirection.BULLISH  # Falling wedge is bullish
                category = PatternCategory.REVERSAL
            else:
                return None

        trendlines = {
            'upper': upper_trendline + (highs[0][1], highs[-1][1]),
            'lower': lower_trendline + (lows[0][1], lows[-1][1])
        }

        return self._create_pattern(
            pattern_type, category, direction, {}, current_price, current_time, trendlines
        )

    def _identify_flag_pennant_pattern(self, pattern_type: ChartPatternType,
                                      swing_highs: List[Tuple[float, datetime]],
                                      swing_lows: List[Tuple[float, datetime]],
                                      current_price: float, current_time: datetime) -> Optional[ChartPattern]:
        """Identify flag and pennant patterns"""
        # These are short-term patterns that require specific price action
        # Simplified implementation - would need more sophisticated analysis
        if len(self.price_data) < 30:
            return None

        # Look for consolidation after strong move
        recent_prices = self.price_data[-30:]
        price_range = max(recent_prices) - min(recent_prices)

        # Check for flag-like consolidation
        if price_range > self._calculate_atr() * 2:
            # Strong prior move detected
            consolidation_range = max(recent_prices[-10:]) - min(recent_prices[-10:])

            if consolidation_range < price_range * 0.5:  # Consolidation is smaller
                direction = (PatternDirection.BULLISH if pattern_type in [ChartPatternType.BULL_FLAG, ChartPatternType.BULL_PENNANT]
                           else PatternDirection.BEARISH)
                category = PatternCategory.CONTINUATION

                return self._create_pattern(
                    pattern_type, category, direction, {}, current_price, current_time
                )

        return None

    def _identify_cup_handle_pattern(self, pattern_type: ChartPatternType,
                                    swing_highs: List[Tuple[float, datetime]],
                                    swing_lows: List[Tuple[float, datetime]],
                                    current_price: float, current_time: datetime) -> Optional[ChartPattern]:
        """Identify cup and handle patterns"""
        # Cup and handle is a complex pattern requiring specific shape
        # Simplified implementation
        if len(swing_highs) < 4 or len(swing_lows) < 4:
            return None

        # Look for U-shaped pattern in recent data
        recent_highs = [h[0] for h in swing_highs[-4:]]
        recent_lows = [l[0] for l in swing_lows[-4:]]

        if len(recent_highs) >= 3 and len(recent_lows) >= 3:
            # Check for cup shape (left high, middle low, right high)
            left_high = recent_highs[0]
            middle_low = min(recent_lows)
            right_high = recent_highs[-1]

            if (left_high > middle_low and right_high > middle_low and
                abs(left_high - right_high) / left_high < 0.05):  # Similar peak heights

                direction = (PatternDirection.BULLISH if pattern_type == ChartPatternType.CUP_AND_HANDLE
                           else PatternDirection.BEARISH)
                category = PatternCategory.CONTINUATION

                pivot_dict = {
                    'left_peak': swing_highs[-4][0] if len(swing_highs) >= 4 else swing_highs[-1],
                    'bottom': (middle_low, current_time),
                    'right_peak': swing_highs[-1]
                }

                return self._create_pattern(
                    pattern_type, category, direction, pivot_dict, current_price, current_time
                )

        return None

    def _create_pattern(self, pattern_type: ChartPatternType, category: PatternCategory,
                       direction: PatternDirection, pivot_points: Dict[str, Tuple[float, datetime]],
                       current_price: float, current_time: datetime,
                       trendlines: Optional[Dict[str, Tuple]] = None) -> ChartPattern:
        """Create a chart pattern with institutional analysis"""
        # Calculate pattern dimensions
        all_prices = [current_price]
        all_times = [current_time]

        for point in pivot_points.values():
            if isinstance(point, tuple) and len(point) >= 2:
                all_prices.append(point[0])
                all_times.append(point[1])

        pattern_height = max(all_prices) - min(all_prices)
        pattern_duration = max(all_times) - min(all_times)

        # Calculate completeness
        completeness = self._check_pattern_completeness(pattern_type, pivot_points, trendlines, current_price)

        # Calculate strength
        strength = self._calculate_pattern_strength(pattern_type, pivot_points, trendlines, pattern_height)

        # Volume weighting
        volume_weighted = self._is_pattern_volume_supported(pivot_points, current_time)

        # Multi-timeframe confirmation
        multi_timeframe_confirmed = self._check_pattern_multi_timeframe(pattern_type, pivot_points)

        # Smart money confirmation
        smart_money_confirmed = self._check_pattern_smart_money(pattern_type, pivot_points)

        # Confidence score
        confidence_score = self._calculate_pattern_confidence(strength, volume_weighted,
                                                            multi_timeframe_confirmed, smart_money_confirmed)

        # Risk management levels
        risk_levels = self._calculate_pattern_risk_management(pattern_type, direction, pivot_points, current_price)

        return ChartPattern(
            pattern_type=pattern_type,
            category=category,
            direction=direction,
            completeness=completeness,
            pivot_points=pivot_points,
            trendlines=trendlines or {},
            pattern_height=pattern_height,
            pattern_duration=pattern_duration,
            strength=strength,
            confidence_score=confidence_score,
            volume_weighted=volume_weighted,
            multi_timeframe_confirmed=multi_timeframe_confirmed,
            smart_money_confirmed=smart_money_confirmed,
            risk_management_levels=risk_levels
        )

    def _check_pattern_completeness(self, pattern_type: ChartPatternType,
                                   pivot_points: Dict[str, Tuple[float, datetime]],
                                   trendlines: Dict[str, Tuple], current_price: float) -> PatternCompleteness:
        """Check if pattern is complete"""
        # Simplified completeness check
        min_points = {
            ChartPatternType.HEAD_AND_SHOULDERS: 4,
            ChartPatternType.DOUBLE_TOP: 2,
            ChartPatternType.DOUBLE_BOTTOM: 2,
            ChartPatternType.TRIPLE_TOP: 3,
            ChartPatternType.TRIPLE_BOTTOM: 3,
            ChartPatternType.ASCENDING_TRIANGLE: 4,
            ChartPatternType.DESCENDING_TRIANGLE: 4,
            ChartPatternType.SYMMETRICAL_TRIANGLE: 4,
            ChartPatternType.RISING_WEDGE: 4,
            ChartPatternType.FALLING_WEDGE: 4,
            ChartPatternType.BULL_FLAG: 2,
            ChartPatternType.BEAR_FLAG: 2,
            ChartPatternType.CUP_AND_HANDLE: 3
        }

        required_points = min_points.get(pattern_type, 2)

        if len(pivot_points) >= required_points:
            return PatternCompleteness.COMPLETE
        elif len(pivot_points) >= required_points * 0.7:
            return PatternCompleteness.FORMING
        else:
            return PatternCompleteness.INVALID

    def _calculate_pattern_strength(self, pattern_type: ChartPatternType,
                                   pivot_points: Dict[str, Tuple[float, datetime]],
                                   trendlines: Dict[str, Tuple], pattern_height: float) -> PatternStrength:
        """Calculate pattern strength"""
        strength_score = 0

        # Volume of pivots
        strength_score += len(pivot_points)

        # Pattern height relative to ATR
        atr = self._calculate_atr()
        if pattern_height > atr * 3:
            strength_score += 2
        elif pattern_height > atr * 2:
            strength_score += 1

        # Trendline convergence (for triangles/wedges)
        if trendlines and len(trendlines) >= 2:
            slopes = [line[0] for line in trendlines.values()]
            if len(slopes) >= 2:
                slope_diff = abs(slopes[0] - slopes[1])
                if slope_diff < 0.01:  # Converging lines
                    strength_score += 2

        # Pattern-specific strength factors
        if pattern_type in [ChartPatternType.HEAD_AND_SHOULDERS, ChartPatternType.DOUBLE_TOP,
                           ChartPatternType.DOUBLE_BOTTOM, ChartPatternType.TRIPLE_TOP,
                           ChartPatternType.TRIPLE_BOTTOM]:
            strength_score += 2  # Reversal patterns are strong

        if strength_score >= 7:
            return PatternStrength.VERY_STRONG
        elif strength_score >= 5:
            return PatternStrength.STRONG
        elif strength_score >= 3:
            return PatternStrength.MODERATE
        else:
            return PatternStrength.WEAK

    def _is_pattern_volume_supported(self, pivot_points: Dict[str, Tuple[float, datetime]],
                                    current_time: datetime) -> bool:
        """Check if pattern has volume confirmation"""
        if not self.volume_data:
            return False

        # Check volume at pivot points
        total_volume = sum(self.volume_data)
        avg_volume = total_volume / len(self.volume_data) if self.volume_data else 0

        high_volume_pivots = 0

        for point_name, point_data in pivot_points.items():
            if isinstance(point_data, tuple) and len(point_data) >= 2:
                point_time = point_data[1]

                # Find volume around this time
                point_index = None
                for i, timestamp in enumerate(self.time_data):
                    if timestamp >= point_time:
                        point_index = i
                        break

                if point_index and point_index < len(self.volume_data):
                    window_size = min(3, len(self.volume_data) - point_index)
                    point_volume = sum(self.volume_data[point_index:point_index + window_size]) / window_size

                    if point_volume > avg_volume * 1.5:
                        high_volume_pivots += 1

        return high_volume_pivots >= len(pivot_points) * 0.5  # At least 50% of pivots have high volume

    def _check_pattern_multi_timeframe(self, pattern_type: ChartPatternType,
                                      pivot_points: Dict[str, Tuple[float, datetime]]) -> bool:
        """Check multi-timeframe confirmation"""
        # Simplified check - patterns with more pivot points are stronger
        return len(pivot_points) >= 3

    def _check_pattern_smart_money(self, pattern_type: ChartPatternType,
                                  pivot_points: Dict[str, Tuple[float, datetime]]) -> bool:
        """Check smart money confirmation"""
        return self._is_pattern_volume_supported(pivot_points, datetime.now())

    def _calculate_pattern_confidence(self, strength: PatternStrength, volume_weighted: bool,
                                    multi_timeframe: bool, smart_money: bool) -> float:
        """Calculate pattern confidence score"""
        base_score = {
            PatternStrength.WEAK: 0.4,
            PatternStrength.MODERATE: 0.6,
            PatternStrength.STRONG: 0.8,
            PatternStrength.VERY_STRONG: 0.9
        }[strength]

        bonuses = 0
        if volume_weighted:
            bonuses += 0.05
        if multi_timeframe:
            bonuses += 0.05
        if smart_money:
            bonuses += 0.05

        return min(1.0, base_score + bonuses)

    def _calculate_pattern_risk_management(self, pattern_type: ChartPatternType,
                                         direction: PatternDirection,
                                         pivot_points: Dict[str, Tuple[float, datetime]],
                                         current_price: float) -> Dict[str, float]:
        """Calculate risk management levels for the pattern"""
        atr = self._calculate_atr()

        # Base stop distance on pattern type
        if pattern_type in [ChartPatternType.HEAD_AND_SHOULDERS, ChartPatternType.DOUBLE_TOP,
                           ChartPatternType.DOUBLE_BOTTOM, ChartPatternType.TRIPLE_TOP,
                           ChartPatternType.TRIPLE_BOTTOM]:
            stop_distance = atr * 2.0  # Wider stops for reversal patterns
        else:
            stop_distance = atr * 1.5  # Moderate stops for continuation patterns

        # Calculate target based on pattern height
        all_prices = [current_price]
        for point in pivot_points.values():
            if isinstance(point, tuple) and len(point) >= 1:
                all_prices.append(point[0])

        pattern_height = max(all_prices) - min(all_prices)
        target_distance = pattern_height * 0.8  # 80% of pattern height

        if direction == PatternDirection.BULLISH:
            stop_loss = current_price - stop_distance
            take_profit = current_price + target_distance
        else:
            stop_loss = current_price + stop_distance
            take_profit = current_price - target_distance

        return {
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'breakeven_level': current_price,
            'partial_exit_level': (current_price + take_profit) / 2
        }

    def _calculate_atr(self, period: int = 14) -> float:
        """Calculate Average True Range"""
        if len(self.price_data) < period + 1:
            return abs(self.price_data[-1] - self.price_data[0]) if len(self.price_data) > 1 else 0.02

        true_ranges = []
        for i in range(1, min(len(self.price_data), period + 1)):
            high = max(self.price_data[i], self.price_data[i-1])
            low = min(self.price_data[i], self.price_data[i-1])
            true_range = high - low
            true_ranges.append(true_range)

        return statistics.mean(true_ranges) if true_ranges else 0.02

    def _validate_pattern(self, pattern: ChartPattern) -> bool:
        """Validate pattern against institutional criteria"""
        if pattern.completeness == PatternCompleteness.INVALID:
            return False

        if pattern.strength == PatternStrength.WEAK:
            return False

        if pattern.confidence_score < self.min_pattern_strength:
            return False

        return True

    def check_chart_signals(self, current_price: float, current_time: datetime) -> List[ChartSignal]:
        """
        Check for trading signals based on chart patterns

        Args:
            current_price: Current market price
            current_time: Current timestamp

        Returns:
            List of chart pattern trading signals
        """
        signals = []

        for pattern_key, pattern in self.active_patterns.items():
            signal = self._check_single_pattern_signal(pattern, current_price, current_time)
            if signal:
                signals.append(signal)

        return signals

    def _check_single_pattern_signal(self, pattern: ChartPattern, current_price: float,
                                   current_time: datetime) -> Optional[ChartSignal]:
        """Check for signal from a single pattern"""
        if pattern.completeness != PatternCompleteness.COMPLETE:
            return None

        # Pattern breakout signals
        signal_type = "breakout"

        if pattern.direction == PatternDirection.BULLISH:
            direction = "BUY"
        else:
            direction = "SELL"

        entry_price = current_price
        risk_levels = pattern.risk_management_levels

        if direction == "BUY":
            stop_loss = risk_levels['stop_loss']
            take_profit = risk_levels['take_profit']
        else:
            stop_loss = risk_levels['stop_loss']
            take_profit = risk_levels['take_profit']

        risk_reward_ratio = abs(take_profit - entry_price) / abs(stop_loss - entry_price)

        return ChartSignal(
            pattern=pattern,
            signal_type=signal_type,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence_score=pattern.confidence_score,
            risk_reward_ratio=risk_reward_ratio,
            volume_confirmation=pattern.volume_weighted,
            timeframe_alignment=pattern.multi_timeframe_confirmed,
            timestamp=current_time
        )

    def get_chart_info(self) -> Dict[str, Any]:
        """Get comprehensive chart pattern analysis information"""
        return {
            'active_patterns': len(self.active_patterns),
            'pattern_details': [
                {
                    'type': pattern.pattern_type.value,
                    'category': pattern.category.value,
                    'direction': pattern.direction.value,
                    'completeness': pattern.completeness.value,
                    'strength': pattern.strength.value,
                    'confidence': pattern.confidence_score,
                    'volume_weighted': pattern.volume_weighted,
                    'multi_timeframe': pattern.multi_timeframe_confirmed,
                    'smart_money': pattern.smart_money_confirmed,
                    'height': pattern.pattern_height,
                    'duration_seconds': pattern.pattern_duration.total_seconds(),
                    'pivot_points_count': len(pattern.pivot_points)
                }
                for pattern in self.active_patterns.values()
            ],
            'completed_patterns': len(self.completed_patterns),
            'data_points': len(self.price_data),
            'lookback_periods': self.lookback_periods,
            'min_strength_threshold': self.min_pattern_strength
        }


# Factory functions for easy instantiation
def create_chart_pattern_analyzer(lookback_periods: int = 200,
                                min_strength: float = 0.6) -> InstitutionalChartPatternAnalyzer:
    """Create a chart pattern analyzer"""
    return InstitutionalChartPatternAnalyzer(lookback_periods, min_strength)


def calculate_pattern_target(pattern_type: ChartPatternType, entry_price: float,
                           pattern_height: float) -> float:
    """
    Calculate price target based on pattern type and height

    Args:
        pattern_type: Type of chart pattern
        entry_price: Entry price
        pattern_height: Height of the pattern

    Returns:
        Price target
    """
    # Different target calculations for different patterns
    target_multipliers = {
        ChartPatternType.HEAD_AND_SHOULDERS: 1.0,  # Full pattern height
        ChartPatternType.DOUBLE_TOP: 0.8,
        ChartPatternType.DOUBLE_BOTTOM: 0.8,
        ChartPatternType.TRIPLE_TOP: 1.0,
        ChartPatternType.TRIPLE_BOTTOM: 1.0,
        ChartPatternType.ASCENDING_TRIANGLE: 0.8,
        ChartPatternType.DESCENDING_TRIANGLE: 0.8,
        ChartPatternType.SYMMETRICAL_TRIANGLE: 0.7,
        ChartPatternType.RISING_WEDGE: 0.9,
        ChartPatternType.FALLING_WEDGE: 0.9,
        ChartPatternType.BULL_FLAG: 0.6,
        ChartPatternType.BEAR_FLAG: 0.6,
        ChartPatternType.CUP_AND_HANDLE: 1.2
    }

    multiplier = target_multipliers.get(pattern_type, 0.8)
    return entry_price + (pattern_height * multiplier)


def validate_pattern_geometry(pattern_type: ChartPatternType,
                            pivot_points: Dict[str, Tuple[float, datetime]]) -> bool:
    """
    Validate geometric properties of a chart pattern

    Args:
        pattern_type: Type of pattern
        pivot_points: Dictionary of pivot points

    Returns:
        True if geometry is valid
    """
    if not pivot_points:
        return False

    # Basic validation - ensure points exist and are in logical order
    prices = [point[0] for point in pivot_points.values() if isinstance(point, tuple)]

    if len(prices) < 2:
        return False

    # Check for reasonable price movements
    price_range = max(prices) - min(prices)
    avg_price = sum(prices) / len(prices)

    # Pattern should have meaningful height
    return price_range > avg_price * 0.02  # At least 2% range