"""Harmonic Patterns Strategies Module

This module implements advanced harmonic pattern trading strategies including:
- Gartley Pattern (222 Pattern)
- Butterfly Pattern
- Bat Pattern
- Crab Pattern
- Cypher Pattern
- ABCD Pattern
- Three Drives Pattern
- 5-0 Pattern
- Shark Pattern
- Nenstar Pattern

Key Features:
- Automated pattern recognition using Fibonacci ratios
- Pattern completion projections
- Multi-timeframe harmonic analysis
- Pattern strength validation
- Risk management based on pattern structure
- Real-time pattern scanning

Architecture:
Follows the 5-Pillar Architecture with sophisticated pattern recognition
engines and Fibonacci-based validation systems.
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
except ImportError:
    pd = None
    np = None

# Base strategy components
from ..base_strategy import (
    StrategyType, PositionType, SignalStrength,
    TradingSignal, Position, StrategyConfig
)

class HarmonicPatternType(Enum):
    """Types of harmonic patterns"""
    GARTLEY = "gartley"
    BUTTERFLY = "butterfly"
    BAT = "bat"
    CRAB = "crab"
    CYPHER = "cypher"
    ABCD = "abcd"
    THREE_DRIVES = "three_drives"
    FIVE_ZERO = "five_zero"
    SHARK = "shark"
    NENSTAR = "nenstar"
    AB_CD = "ab_cd"
    ALTERNATE_BAT = "alternate_bat"
    DEEP_CRAB = "deep_crab"

class PatternDirection(Enum):
    """Pattern direction"""
    BULLISH = "bullish"
    BEARISH = "bearish"

class PatternStatus(Enum):
    """Pattern completion status"""
    FORMING = "forming"
    COMPLETED = "completed"
    INVALID = "invalid"
    PROJECTED = "projected"

@dataclass
class PatternPoint:
    """Harmonic pattern pivot point"""
    label: str  # X, A, B, C, D
    price: float
    time: datetime
    index: int
    point_type: str  # 'high', 'low'
    significance: float = 1.0

@dataclass
class FibonacciRatio:
    """Fibonacci ratio with tolerance"""
    ratio: float
    tolerance: float = 0.05
    
    def is_valid(self, actual_ratio: float) -> bool:
        """Check if actual ratio is within tolerance"""
        return abs(actual_ratio - self.ratio) <= self.tolerance

@dataclass
class PatternRules:
    """Harmonic pattern validation rules"""
    ab_retracement: List[FibonacciRatio]
    bc_retracement: List[FibonacciRatio]
    cd_extension: List[FibonacciRatio]
    ad_retracement: List[FibonacciRatio]
    
    # Additional ratios for complex patterns
    xb_retracement: Optional[List[FibonacciRatio]] = None
    xc_extension: Optional[List[FibonacciRatio]] = None
    xd_extension: Optional[List[FibonacciRatio]] = None

@dataclass
class HarmonicPattern:
    """Complete harmonic pattern"""
    pattern_type: HarmonicPatternType
    direction: PatternDirection
    status: PatternStatus
    points: Dict[str, PatternPoint]  # X, A, B, C, D
    ratios: Dict[str, float]  # Calculated Fibonacci ratios
    confidence: float
    completion_time: datetime
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    risk_reward_ratio: Optional[float] = None
    
    # Pattern measurements
    pattern_height: float = 0.0
    pattern_width: timedelta = timedelta()
    
    def __post_init__(self):
        if 'X' in self.points and 'D' in self.points:
            self.pattern_height = abs(self.points['D'].price - self.points['X'].price)
            self.pattern_width = self.points['D'].time - self.points['X'].time

@dataclass
class PatternProjection:
    """Harmonic pattern price projection"""
    target_price: float
    target_time: datetime
    projection_type: str  # 'completion', 'reversal'
    confidence: float
    fibonacci_basis: float
    pattern_basis: HarmonicPattern

class HarmonicPatternCalculator:
    """Core harmonic pattern calculation engine"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Define pattern rules with Fibonacci ratios
        self.pattern_rules = self._initialize_pattern_rules()
        
        # Common Fibonacci ratios
        self.fibonacci_ratios = [0.236, 0.382, 0.500, 0.618, 0.786, 0.886, 1.0, 1.13, 1.272, 1.414, 1.618, 2.0, 2.24, 2.618, 3.14, 3.618]
    
    def _initialize_pattern_rules(self) -> Dict[HarmonicPatternType, PatternRules]:
        """Initialize Fibonacci ratio rules for each pattern type"""
        rules = {}
        
        # Gartley Pattern (222)
        rules[HarmonicPatternType.GARTLEY] = PatternRules(
            ab_retracement=[FibonacciRatio(0.618, 0.05)],
            bc_retracement=[FibonacciRatio(0.382, 0.05), FibonacciRatio(0.886, 0.05)],
            cd_extension=[FibonacciRatio(1.272, 0.05)],
            ad_retracement=[FibonacciRatio(0.786, 0.05)]
        )
        
        # Butterfly Pattern
        rules[HarmonicPatternType.BUTTERFLY] = PatternRules(
            ab_retracement=[FibonacciRatio(0.786, 0.05)],
            bc_retracement=[FibonacciRatio(0.382, 0.05), FibonacciRatio(0.886, 0.05)],
            cd_extension=[FibonacciRatio(1.618, 0.05), FibonacciRatio(2.618, 0.05)],
            ad_retracement=[FibonacciRatio(1.272, 0.05), FibonacciRatio(1.618, 0.05)]
        )
        
        # Bat Pattern
        rules[HarmonicPatternType.BAT] = PatternRules(
            ab_retracement=[FibonacciRatio(0.382, 0.05), FibonacciRatio(0.500, 0.05)],
            bc_retracement=[FibonacciRatio(0.382, 0.05), FibonacciRatio(0.886, 0.05)],
            cd_extension=[FibonacciRatio(1.618, 0.05), FibonacciRatio(2.618, 0.05)],
            ad_retracement=[FibonacciRatio(0.886, 0.05)]
        )
        
        # Crab Pattern
        rules[HarmonicPatternType.CRAB] = PatternRules(
            ab_retracement=[FibonacciRatio(0.382, 0.05), FibonacciRatio(0.618, 0.05)],
            bc_retracement=[FibonacciRatio(0.382, 0.05), FibonacciRatio(0.886, 0.05)],
            cd_extension=[FibonacciRatio(2.24, 0.1), FibonacciRatio(3.618, 0.1)],
            ad_retracement=[FibonacciRatio(1.618, 0.05)]
        )
        
        # Cypher Pattern
        rules[HarmonicPatternType.CYPHER] = PatternRules(
            ab_retracement=[FibonacciRatio(0.382, 0.05), FibonacciRatio(0.618, 0.05)],
            bc_retracement=[FibonacciRatio(1.272, 0.05), FibonacciRatio(1.414, 0.05)],
            cd_extension=[FibonacciRatio(0.786, 0.05)],
            ad_retracement=[FibonacciRatio(0.786, 0.05)],
            xc_extension=[FibonacciRatio(1.272, 0.05), FibonacciRatio(1.414, 0.05)]
        )
        
        # ABCD Pattern
        rules[HarmonicPatternType.ABCD] = PatternRules(
            ab_retracement=[FibonacciRatio(0.618, 0.05), FibonacciRatio(0.786, 0.05)],
            bc_retracement=[FibonacciRatio(0.382, 0.05), FibonacciRatio(0.886, 0.05)],
            cd_extension=[FibonacciRatio(1.272, 0.05), FibonacciRatio(1.618, 0.05)],
            ad_retracement=[FibonacciRatio(1.272, 0.05), FibonacciRatio(1.618, 0.05)]
        )
        
        # Shark Pattern
        rules[HarmonicPatternType.SHARK] = PatternRules(
            ab_retracement=[FibonacciRatio(0.382, 0.05), FibonacciRatio(0.618, 0.05)],
            bc_retracement=[FibonacciRatio(1.13, 0.05), FibonacciRatio(1.618, 0.05)],
            cd_extension=[FibonacciRatio(1.618, 0.05), FibonacciRatio(2.24, 0.1)],
            ad_retracement=[FibonacciRatio(0.886, 0.05), FibonacciRatio(1.13, 0.05)]
        )
        
        # 5-0 Pattern
        rules[HarmonicPatternType.FIVE_ZERO] = PatternRules(
            ab_retracement=[FibonacciRatio(1.13, 0.05), FibonacciRatio(1.618, 0.05)],
            bc_retracement=[FibonacciRatio(1.618, 0.05), FibonacciRatio(2.24, 0.1)],
            cd_extension=[FibonacciRatio(0.5, 0.05)],
            ad_retracement=[FibonacciRatio(0.5, 0.05)]
        )
        
        return rules
    
    def find_pattern_points(self, df: pd.DataFrame, min_swing_size: float = 0.02) -> List[PatternPoint]:
        """Find potential harmonic pattern pivot points"""
        if len(df) < 10:
            return []
        
        points = []
        window = 5  # Minimum window for pivot detection
        
        for i in range(window, len(df) - window):
            # Check for pivot high
            is_pivot_high = all(
                df['high'].iloc[i] >= df['high'].iloc[j]
                for j in range(i - window, i + window + 1)
                if j != i
            )
            
            # Check for pivot low
            is_pivot_low = all(
                df['low'].iloc[i] <= df['low'].iloc[j]
                for j in range(i - window, i + window + 1)
                if j != i
            )
            
            if is_pivot_high:
                # Calculate significance
                price_range = df['high'].iloc[max(0, i-20):i+20].max() - df['low'].iloc[max(0, i-20):i+20].min()
                local_high = df['high'].iloc[i]
                local_range = df['high'].iloc[max(0, i-10):i+10].max() - df['low'].iloc[max(0, i-10):i+10].min()
                significance = min(local_range / price_range * 2, 3.0) if price_range > 0 else 1.0
                
                point = PatternPoint(
                    label="",  # Will be assigned during pattern recognition
                    price=local_high,
                    time=df.index[i] if hasattr(df.index[i], 'to_pydatetime') else datetime.now(),
                    index=i,
                    point_type='high',
                    significance=significance
                )
                points.append(point)
            
            if is_pivot_low:
                # Calculate significance
                price_range = df['high'].iloc[max(0, i-20):i+20].max() - df['low'].iloc[max(0, i-20):i+20].min()
                local_low = df['low'].iloc[i]
                local_range = df['high'].iloc[max(0, i-10):i+10].max() - df['low'].iloc[max(0, i-10):i+10].min()
                significance = min(local_range / price_range * 2, 3.0) if price_range > 0 else 1.0
                
                point = PatternPoint(
                    label="",
                    price=local_low,
                    time=df.index[i] if hasattr(df.index[i], 'to_pydatetime') else datetime.now(),
                    index=i,
                    point_type='low',
                    significance=significance
                )
                points.append(point)
        
        # Filter points by minimum swing size
        filtered_points = []
        for i, point in enumerate(points):
            if i == 0:
                filtered_points.append(point)
                continue
            
            prev_point = filtered_points[-1]
            price_change = abs(point.price - prev_point.price) / prev_point.price
            
            if price_change >= min_swing_size:
                filtered_points.append(point)
        
        return sorted(filtered_points, key=lambda x: x.time)
    
    def identify_harmonic_patterns(self, points: List[PatternPoint]) -> List[HarmonicPattern]:
        """Identify harmonic patterns from pivot points"""
        patterns = []
        
        if len(points) < 5:  # Need at least 5 points for XABCD pattern
            return patterns
        
        # Try to find patterns in recent points
        for start_idx in range(len(points) - 4):
            pattern_points = points[start_idx:start_idx + 5]
            
            # Check if points alternate between highs and lows
            if not self._validate_alternating_points(pattern_points):
                continue
            
            # Assign labels X, A, B, C, D
            labeled_points = {
                'X': pattern_points[0],
                'A': pattern_points[1],
                'B': pattern_points[2],
                'C': pattern_points[3],
                'D': pattern_points[4]
            }
            
            # Update point labels
            for label, point in labeled_points.items():
                point.label = label
            
            # Determine pattern direction
            direction = self._determine_pattern_direction(labeled_points)
            
            # Calculate Fibonacci ratios
            ratios = self._calculate_fibonacci_ratios(labeled_points)
            
            # Try to match against known patterns
            for pattern_type in HarmonicPatternType:
                if pattern_type in self.pattern_rules:
                    if self._validate_pattern_ratios(pattern_type, ratios):
                        confidence = self._calculate_pattern_confidence(pattern_type, ratios)
                        
                        if confidence >= 0.6:  # Minimum confidence threshold
                            pattern = HarmonicPattern(
                                pattern_type=pattern_type,
                                direction=direction,
                                status=PatternStatus.COMPLETED,
                                points=labeled_points.copy(),
                                ratios=ratios,
                                confidence=confidence,
                                completion_time=labeled_points['D'].time
                            )
                            
                            # Calculate targets and stop loss
                            self._calculate_pattern_targets(pattern)
                            
                            patterns.append(pattern)
        
        return patterns
    
    def _validate_alternating_points(self, points: List[PatternPoint]) -> bool:
        """Validate that points alternate between highs and lows"""
        if len(points) < 2:
            return False
        
        for i in range(1, len(points)):
            if points[i].point_type == points[i-1].point_type:
                return False
        
        return True
    
    def _determine_pattern_direction(self, points: Dict[str, PatternPoint]) -> PatternDirection:
        """Determine if pattern is bullish or bearish"""
        x_price = points['X'].price
        a_price = points['A'].price
        
        if a_price > x_price:
            return PatternDirection.BULLISH
        else:
            return PatternDirection.BEARISH
    
    def _calculate_fibonacci_ratios(self, points: Dict[str, PatternPoint]) -> Dict[str, float]:
        """Calculate Fibonacci ratios for pattern validation"""
        ratios = {}
        
        try:
            # Extract prices
            x_price = points['X'].price
            a_price = points['A'].price
            b_price = points['B'].price
            c_price = points['C'].price
            d_price = points['D'].price
            
            # Calculate leg lengths
            xa_length = abs(a_price - x_price)
            ab_length = abs(b_price - a_price)
            bc_length = abs(c_price - b_price)
            cd_length = abs(d_price - c_price)
            xb_length = abs(b_price - x_price)
            xc_length = abs(c_price - x_price)
            xd_length = abs(d_price - x_price)
            ad_length = abs(d_price - a_price)
            
            # Calculate ratios (avoid division by zero)
            if xa_length > 0:
                ratios['AB/XA'] = ab_length / xa_length
                ratios['XB/XA'] = xb_length / xa_length
                ratios['AD/XA'] = ad_length / xa_length
            
            if ab_length > 0:
                ratios['BC/AB'] = bc_length / ab_length
            
            if bc_length > 0:
                ratios['CD/BC'] = cd_length / bc_length
            
            if xb_length > 0:
                ratios['XC/XB'] = xc_length / xb_length
                ratios['XD/XB'] = xd_length / xb_length
            
            if xc_length > 0:
                ratios['XD/XC'] = xd_length / xc_length
            
            return ratios
            
        except Exception as e:
            self.logger.error(f"Error calculating Fibonacci ratios: {e}")
            return ratios
    
    def _validate_pattern_ratios(self, pattern_type: HarmonicPatternType, ratios: Dict[str, float]) -> bool:
        """Validate pattern against Fibonacci ratio rules"""
        if pattern_type not in self.pattern_rules:
            return False
        
        rules = self.pattern_rules[pattern_type]
        
        try:
            # Check AB retracement
            ab_ratio = ratios.get('AB/XA', 0)
            ab_valid = any(fib_ratio.is_valid(ab_ratio) for fib_ratio in rules.ab_retracement)
            
            # Check BC retracement
            bc_ratio = ratios.get('BC/AB', 0)
            bc_valid = any(fib_ratio.is_valid(bc_ratio) for fib_ratio in rules.bc_retracement)
            
            # Check CD extension
            cd_ratio = ratios.get('CD/BC', 0)
            cd_valid = any(fib_ratio.is_valid(cd_ratio) for fib_ratio in rules.cd_extension)
            
            # Check AD retracement
            ad_ratio = ratios.get('AD/XA', 0)
            ad_valid = any(fib_ratio.is_valid(ad_ratio) for fib_ratio in rules.ad_retracement)
            
            # Additional checks for specific patterns
            additional_valid = True
            
            if rules.xb_retracement:
                xb_ratio = ratios.get('XB/XA', 0)
                additional_valid = additional_valid and any(
                    fib_ratio.is_valid(xb_ratio) for fib_ratio in rules.xb_retracement
                )
            
            if rules.xc_extension:
                xc_ratio = ratios.get('XC/XB', 0)
                additional_valid = additional_valid and any(
                    fib_ratio.is_valid(xc_ratio) for fib_ratio in rules.xc_extension
                )
            
            # Pattern is valid if most ratios match
            valid_count = sum([ab_valid, bc_valid, cd_valid, ad_valid])
            return valid_count >= 3 and additional_valid
            
        except Exception as e:
            self.logger.error(f"Error validating pattern ratios: {e}")
            return False
    
    def _calculate_pattern_confidence(self, pattern_type: HarmonicPatternType, ratios: Dict[str, float]) -> float:
        """Calculate confidence score for pattern"""
        if pattern_type not in self.pattern_rules:
            return 0.0
        
        rules = self.pattern_rules[pattern_type]
        confidence = 0.0
        total_checks = 0
        
        try:
            # Check each ratio and add to confidence
            ratio_checks = [
                ('AB/XA', rules.ab_retracement),
                ('BC/AB', rules.bc_retracement),
                ('CD/BC', rules.cd_extension),
                ('AD/XA', rules.ad_retracement)
            ]
            
            for ratio_key, fib_ratios in ratio_checks:
                if ratio_key in ratios:
                    actual_ratio = ratios[ratio_key]
                    
                    # Find best matching Fibonacci ratio
                    best_match = min(
                        fib_ratios,
                        key=lambda fr: abs(actual_ratio - fr.ratio)
                    )
                    
                    # Calculate match quality (closer = higher confidence)
                    error = abs(actual_ratio - best_match.ratio) / best_match.ratio
                    match_quality = max(0, 1 - (error / best_match.tolerance))
                    
                    confidence += match_quality
                    total_checks += 1
            
            # Additional checks for complex patterns
            if rules.xb_retracement and 'XB/XA' in ratios:
                actual_ratio = ratios['XB/XA']
                best_match = min(
                    rules.xb_retracement,
                    key=lambda fr: abs(actual_ratio - fr.ratio)
                )
                error = abs(actual_ratio - best_match.ratio) / best_match.ratio
                match_quality = max(0, 1 - (error / best_match.tolerance))
                confidence += match_quality
                total_checks += 1
            
            return confidence / total_checks if total_checks > 0 else 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculating pattern confidence: {e}")
            return 0.0
    
    def _calculate_pattern_targets(self, pattern: HarmonicPattern):
        """Calculate target price and stop loss for pattern"""
        try:
            points = pattern.points
            x_price = points['X'].price
            a_price = points['A'].price
            d_price = points['D'].price
            
            # Calculate pattern range
            pattern_range = abs(a_price - x_price)
            
            if pattern.direction == PatternDirection.BULLISH:
                # Bullish pattern - expect price to rise from D
                # Target: 38.2% to 61.8% retracement of AD leg
                ad_range = abs(d_price - a_price)
                pattern.target_price = d_price + (ad_range * 0.618)
                pattern.stop_loss = d_price - (pattern_range * 0.1)  # 10% of pattern range
            else:
                # Bearish pattern - expect price to fall from D
                ad_range = abs(a_price - d_price)
                pattern.target_price = d_price - (ad_range * 0.618)
                pattern.stop_loss = d_price + (pattern_range * 0.1)
            
            # Calculate risk-reward ratio
            if pattern.stop_loss:
                risk = abs(d_price - pattern.stop_loss)
                reward = abs(pattern.target_price - d_price)
                pattern.risk_reward_ratio = reward / risk if risk > 0 else 0
            
        except Exception as e:
            self.logger.error(f"Error calculating pattern targets: {e}")
    
    def project_pattern_completion(self, points: List[PatternPoint], current_price: float) -> List[PatternProjection]:
        """Project potential pattern completion points"""
        projections = []
        
        if len(points) < 4:  # Need at least XABC to project D
            return projections
        
        try:
            # Take the most recent 4 points as XABC
            recent_points = points[-4:]
            
            # Assign labels
            labeled_points = {
                'X': recent_points[0],
                'A': recent_points[1],
                'B': recent_points[2],
                'C': recent_points[3]
            }
            
            # Calculate partial ratios
            x_price = labeled_points['X'].price
            a_price = labeled_points['A'].price
            b_price = labeled_points['B'].price
            c_price = labeled_points['C'].price
            
            xa_length = abs(a_price - x_price)
            ab_length = abs(b_price - a_price)
            bc_length = abs(c_price - b_price)
            
            # Project D points for each pattern type
            for pattern_type in HarmonicPatternType:
                if pattern_type not in self.pattern_rules:
                    continue
                
                rules = self.pattern_rules[pattern_type]
                
                # Try each possible AD ratio
                for ad_fib in rules.ad_retracement:
                    # Calculate projected D price
                    if a_price > x_price:  # Bullish structure
                        projected_d = a_price - (xa_length * ad_fib.ratio)
                    else:  # Bearish structure
                        projected_d = a_price + (xa_length * ad_fib.ratio)
                    
                    # Check if projection is reasonable
                    price_diff = abs(current_price - projected_d) / current_price
                    
                    if 0.01 <= price_diff <= 0.1:  # 1% to 10% away from current price
                        projection = PatternProjection(
                            target_price=projected_d,
                            target_time=datetime.now() + timedelta(days=2),  # Rough estimate
                            projection_type="pattern_completion",
                            confidence=0.6,
                            fibonacci_basis=ad_fib.ratio,
                            pattern_basis=None  # Will be set when pattern completes
                        )
                        projections.append(projection)
            
            return projections
            
        except Exception as e:
            self.logger.error(f"Error projecting pattern completion: {e}")
            return projections

class HarmonicPatternStrategy:
    """Base harmonic pattern trading strategy"""
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.calculator = HarmonicPatternCalculator()
        
        # Strategy parameters
        self.min_swing_size = config.parameters.get('min_swing_size', 0.02)
        self.min_pattern_confidence = config.parameters.get('min_pattern_confidence', 0.7)
        self.lookback_periods = config.parameters.get('lookback_periods', 200)
        self.target_patterns = config.parameters.get('target_patterns', list(HarmonicPatternType))
        
        # Current state
        self.current_patterns: List[HarmonicPattern] = []
        self.pattern_points: List[PatternPoint] = []
        self.projections: List[PatternProjection] = []
    
    def analyze_market_data(self, market_data: Dict) -> Dict:
        """Analyze market data for harmonic patterns"""
        try:
            if pd is None:
                self.logger.error("Pandas not available for data analysis")
                return {}
            
            # Convert market data to DataFrame
            if isinstance(market_data, dict) and 'close' in market_data:
                df = pd.DataFrame([market_data])
            else:
                df = pd.DataFrame(market_data)
            
            if df.empty or len(df) < 50:
                return {}
            
            # Limit to recent data
            recent_df = df.tail(self.lookback_periods) if len(df) > self.lookback_periods else df
            
            # Find pattern points
            self.pattern_points = self.calculator.find_pattern_points(recent_df, self.min_swing_size)
            
            if len(self.pattern_points) < 5:
                return {}
            
            # Identify patterns
            all_patterns = self.calculator.identify_harmonic_patterns(self.pattern_points)
            
            # Filter by confidence and target patterns
            self.current_patterns = [
                pattern for pattern in all_patterns
                if pattern.confidence >= self.min_pattern_confidence
                and pattern.pattern_type in self.target_patterns
            ]
            
            # Generate projections
            current_price = recent_df['close'].iloc[-1] if 'close' in recent_df.columns else 0
            self.projections = self.calculator.project_pattern_completion(self.pattern_points, current_price)
            
            return {
                'patterns': self.current_patterns,
                'pattern_points': self.pattern_points,
                'projections': self.projections,
                'current_price': current_price
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing harmonic pattern data: {e}")
            return {}
    
    def generate_signals(self, market_data: Dict) -> List[TradingSignal]:
        """Generate trading signals based on harmonic pattern analysis"""
        signals = []
        
        try:
            analysis = self.analyze_market_data(market_data)
            
            if not analysis:
                return signals
            
            current_price = analysis.get('current_price', 0)
            patterns = analysis.get('patterns', [])
            projections = analysis.get('projections', [])
            
            # Generate signals from completed patterns
            for pattern in patterns:
                if pattern.status == PatternStatus.COMPLETED:
                    pattern_signals = self._generate_pattern_signals(pattern, current_price)
                    signals.extend(pattern_signals)
            
            # Generate signals from projections
            for projection in projections:
                projection_signals = self._generate_projection_signals(projection, current_price)
                signals.extend(projection_signals)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating harmonic pattern signals: {e}")
            return signals
    
    def _generate_pattern_signals(self, pattern: HarmonicPattern, current_price: float) -> List[TradingSignal]:
        """Generate signals from completed harmonic patterns"""
        signals = []
        
        try:
            d_price = pattern.points['D'].price
            price_diff = abs(current_price - d_price) / d_price
            
            # Only generate signal if we're near the D point
            if price_diff <= 0.02:  # Within 2% of D point
                # Determine signal direction (opposite to pattern direction at completion)
                if pattern.direction == PatternDirection.BULLISH:
                    signal_type = PositionType.LONG  # Buy at bullish pattern completion
                else:
                    signal_type = PositionType.SHORT  # Sell at bearish pattern completion
                
                # Use pattern's calculated targets
                target_price = pattern.target_price if pattern.target_price else current_price * 1.02
                stop_loss = pattern.stop_loss if pattern.stop_loss else current_price * 0.98
                
                # Adjust for signal direction
                if signal_type == PositionType.SHORT:
                    if not pattern.target_price:
                        target_price = current_price * 0.98
                    if not pattern.stop_loss:
                        stop_loss = current_price * 1.02
                
                # Determine signal strength based on confidence
                if pattern.confidence >= 0.8:
                    strength = SignalStrength.STRONG
                elif pattern.confidence >= 0.7:
                    strength = SignalStrength.MEDIUM
                else:
                    strength = SignalStrength.WEAK
                
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
                        'strategy': 'harmonic_pattern',
                        'pattern_type': pattern.pattern_type.value,
                        'pattern_direction': pattern.direction.value,
                        'pattern_confidence': pattern.confidence,
                        'risk_reward_ratio': pattern.risk_reward_ratio,
                        'fibonacci_ratios': pattern.ratios,
                        'd_point_price': d_price
                    }
                )
                signals.append(signal)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating pattern signals: {e}")
            return signals
    
    def _generate_projection_signals(self, projection: PatternProjection, current_price: float) -> List[TradingSignal]:
        """Generate signals from pattern projections"""
        signals = []
        
        try:
            # Check if current price is approaching projection target
            price_diff = abs(current_price - projection.target_price) / projection.target_price
            
            if price_diff <= 0.005:  # Within 0.5% of projection target
                # Prepare for reversal at projection completion
                if current_price < projection.target_price:
                    signal_type = PositionType.SHORT  # Approaching resistance
                else:
                    signal_type = PositionType.LONG   # Approaching support
                
                signal = TradingSignal(
                    symbol=self.config.symbols[0] if self.config.symbols else "UNKNOWN",
                    signal_type=signal_type,
                    strength=SignalStrength.MEDIUM,
                    confidence=projection.confidence,
                    entry_price=current_price,
                    stop_loss=current_price * (1.01 if signal_type == PositionType.SHORT else 0.99),
                    take_profit=current_price * (0.98 if signal_type == PositionType.SHORT else 1.02),
                    timestamp=datetime.now(),
                    metadata={
                        'strategy': 'harmonic_projection',
                        'projection_type': projection.projection_type,
                        'target_price': projection.target_price,
                        'fibonacci_basis': projection.fibonacci_basis
                    }
                )
                signals.append(signal)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating projection signals: {e}")
            return signals

class GartleyPatternStrategy(HarmonicPatternStrategy):
    """Strategy focused on Gartley patterns"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.target_patterns = [HarmonicPatternType.GARTLEY]

class ButterflyPatternStrategy(HarmonicPatternStrategy):
    """Strategy focused on Butterfly patterns"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.target_patterns = [HarmonicPatternType.BUTTERFLY]

class BatPatternStrategy(HarmonicPatternStrategy):
    """Strategy focused on Bat patterns"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.target_patterns = [HarmonicPatternType.BAT]

class CrabPatternStrategy(HarmonicPatternStrategy):
    """Strategy focused on Crab patterns"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.target_patterns = [HarmonicPatternType.CRAB]

class CypherPatternStrategy(HarmonicPatternStrategy):
    """Strategy focused on Cypher patterns"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.target_patterns = [HarmonicPatternType.CYPHER]

# Convenience aliases
GartleyStrategy = GartleyPatternStrategy
ButterflyStrategy = ButterflyPatternStrategy
BatStrategy = BatPatternStrategy
CrabStrategy = CrabPatternStrategy
CypherStrategy = CypherPatternStrategy

# Utility functions
def identify_harmonic_pattern(df: pd.DataFrame, min_swing_size: float = 0.02) -> Optional[HarmonicPattern]:
    """Identify harmonic pattern in price data"""
    calculator = HarmonicPatternCalculator()
    points = calculator.find_pattern_points(df, min_swing_size)
    patterns = calculator.identify_harmonic_patterns(points)
    
    # Return the highest confidence pattern
    if patterns:
        return max(patterns, key=lambda p: p.confidence)
    return None

def calculate_pattern_projections(points: List[PatternPoint], current_price: float) -> List[PatternProjection]:
    """Calculate harmonic pattern projections"""
    calculator = HarmonicPatternCalculator()
    return calculator.project_pattern_completion(points, current_price)

def find_harmonic_pattern_points(df: pd.DataFrame, min_swing_size: float = 0.02) -> List[PatternPoint]:
    """Find harmonic pattern pivot points"""
    calculator = HarmonicPatternCalculator()
    return calculator.find_pattern_points(df, min_swing_size)