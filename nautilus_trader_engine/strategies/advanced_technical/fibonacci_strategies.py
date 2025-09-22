"""Fibonacci Strategies Module

This module implements comprehensive Fibonacci-based trading strategies including:
- Fibonacci Retracements (23.6%, 38.2%, 50%, 61.8%, 78.6%)
- Fibonacci Extensions (127.2%, 161.8%, 261.8%, 423.6%)
- Fibonacci Time Zones
- Fibonacci Arcs and Fans
- Fibonacci Clusters and Confluence
- Advanced Fibonacci Patterns

Key Features:
- Multi-timeframe Fibonacci analysis
- Dynamic Fibonacci level calculation
- Confluence zone identification
- Price and time-based Fibonacci projections
- Automated pattern recognition

Architecture:
Follows the 5-Pillar Architecture with mathematical precision in Fibonacci
calculations and advanced pattern recognition systems.
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

class FibonacciType(Enum):
    """Fibonacci analysis types"""
    RETRACEMENT = "retracement"
    EXTENSION = "extension"
    PROJECTION = "projection"
    TIME_ZONE = "time_zone"
    ARC = "arc"
    FAN = "fan"
    CLUSTER = "cluster"

class FibonacciLevel(Enum):
    """Standard Fibonacci levels"""
    # Retracement levels
    LEVEL_0 = 0.0
    LEVEL_236 = 0.236
    LEVEL_382 = 0.382
    LEVEL_500 = 0.500
    LEVEL_618 = 0.618
    LEVEL_786 = 0.786
    LEVEL_100 = 1.0
    
    # Extension levels
    LEVEL_1272 = 1.272
    LEVEL_1414 = 1.414
    LEVEL_1618 = 1.618
    LEVEL_2000 = 2.000
    LEVEL_2618 = 2.618
    LEVEL_3000 = 3.000
    LEVEL_4236 = 4.236

class FibonacciDirection(Enum):
    """Fibonacci calculation direction"""
    UPTREND = "uptrend"
    DOWNTREND = "downtrend"

@dataclass
class FibonacciPoint:
    """Fibonacci calculation point"""
    price: float
    time: datetime
    point_type: str  # 'swing_high', 'swing_low', 'pivot'
    significance: float = 1.0

@dataclass
class FibonacciLevelData:
    """Fibonacci level information"""
    level: FibonacciLevel
    price: float
    percentage: float
    level_type: FibonacciType
    direction: FibonacciDirection
    strength: float
    time_calculated: datetime
    source_points: List[FibonacciPoint] = field(default_factory=list)

@dataclass
class FibonacciCluster:
    """Fibonacci confluence cluster"""
    price_center: float
    price_range: Tuple[float, float]
    levels: List[FibonacciLevelData]
    strength: float
    confluence_count: int
    cluster_type: str

@dataclass
class FibonacciTimeZone:
    """Fibonacci time projection"""
    base_period: int
    fibonacci_periods: List[int]
    next_zones: List[datetime]
    strength: float

class FibonacciCalculator:
    """Core Fibonacci calculation engine"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Standard Fibonacci ratios
        self.retracement_levels = [0.0, 0.236, 0.382, 0.500, 0.618, 0.786, 1.0]
        self.extension_levels = [1.272, 1.414, 1.618, 2.000, 2.618, 3.000, 4.236]
        
        # Fibonacci sequence for time zones
        self.fibonacci_sequence = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610]
    
    def calculate_retracements(self, high_point: FibonacciPoint, 
                             low_point: FibonacciPoint) -> List[FibonacciLevelData]:
        """Calculate Fibonacci retracement levels"""
        levels = []
        
        # Determine direction
        if high_point.time > low_point.time:
            direction = FibonacciDirection.DOWNTREND
            price_range = high_point.price - low_point.price
        else:
            direction = FibonacciDirection.UPTREND
            price_range = high_point.price - low_point.price
        
        for ratio in self.retracement_levels:
            if direction == FibonacciDirection.DOWNTREND:
                # Retracement from high to low
                level_price = high_point.price - (price_range * ratio)
            else:
                # Retracement from low to high
                level_price = low_point.price + (price_range * ratio)
            
            # Calculate level strength based on golden ratio proximity
            strength = self._calculate_level_strength(ratio)
            
            level_data = FibonacciLevelData(
                level=self._ratio_to_enum(ratio),
                price=level_price,
                percentage=ratio * 100,
                level_type=FibonacciType.RETRACEMENT,
                direction=direction,
                strength=strength,
                time_calculated=datetime.now(),
                source_points=[high_point, low_point]
            )
            levels.append(level_data)
        
        return levels
    
    def calculate_extensions(self, point_a: FibonacciPoint, 
                           point_b: FibonacciPoint,
                           point_c: FibonacciPoint) -> List[FibonacciLevelData]:
        """Calculate Fibonacci extension levels (ABC pattern)"""
        levels = []
        
        # Calculate the base move (A to B)
        base_move = abs(point_b.price - point_a.price)
        
        # Determine direction from C
        if point_b.price > point_a.price:
            # Upward base move
            direction = FibonacciDirection.UPTREND
        else:
            # Downward base move
            direction = FibonacciDirection.DOWNTREND
        
        for ratio in self.extension_levels:
            if direction == FibonacciDirection.UPTREND:
                level_price = point_c.price + (base_move * ratio)
            else:
                level_price = point_c.price - (base_move * ratio)
            
            strength = self._calculate_level_strength(ratio)
            
            level_data = FibonacciLevelData(
                level=self._ratio_to_enum(ratio),
                price=level_price,
                percentage=ratio * 100,
                level_type=FibonacciType.EXTENSION,
                direction=direction,
                strength=strength,
                time_calculated=datetime.now(),
                source_points=[point_a, point_b, point_c]
            )
            levels.append(level_data)
        
        return levels
    
    def calculate_time_zones(self, start_time: datetime, 
                           base_period_hours: int = 24) -> FibonacciTimeZone:
        """Calculate Fibonacci time zones"""
        fibonacci_periods = []
        next_zones = []
        
        for fib_num in self.fibonacci_sequence[:10]:  # First 10 Fibonacci numbers
            period_hours = base_period_hours * fib_num
            fibonacci_periods.append(period_hours)
            
            next_zone_time = start_time + timedelta(hours=period_hours)
            next_zones.append(next_zone_time)
        
        return FibonacciTimeZone(
            base_period=base_period_hours,
            fibonacci_periods=fibonacci_periods,
            next_zones=next_zones,
            strength=0.7  # Default strength for time zones
        )
    
    def find_fibonacci_clusters(self, all_levels: List[FibonacciLevelData],
                              cluster_tolerance: float = 0.01) -> List[FibonacciCluster]:
        """Find Fibonacci confluence clusters"""
        if not all_levels:
            return []
        
        clusters = []
        processed_levels = set()
        
        for i, level in enumerate(all_levels):
            if i in processed_levels:
                continue
            
            # Find nearby levels
            cluster_levels = [level]
            cluster_center = level.price
            
            for j, other_level in enumerate(all_levels[i+1:], i+1):
                if j in processed_levels:
                    continue
                
                price_diff = abs(other_level.price - level.price) / level.price
                
                if price_diff <= cluster_tolerance:
                    cluster_levels.append(other_level)
                    processed_levels.add(j)
            
            if len(cluster_levels) >= 2:  # At least 2 levels for a cluster
                # Calculate cluster properties
                prices = [l.price for l in cluster_levels]
                cluster_center = sum(prices) / len(prices)
                price_range = (min(prices), max(prices))
                
                # Calculate cluster strength
                total_strength = sum(l.strength for l in cluster_levels)
                confluence_count = len(cluster_levels)
                cluster_strength = total_strength * (confluence_count / 10)  # Bonus for confluence
                
                cluster = FibonacciCluster(
                    price_center=cluster_center,
                    price_range=price_range,
                    levels=cluster_levels,
                    strength=min(cluster_strength, 1.0),
                    confluence_count=confluence_count,
                    cluster_type="fibonacci_confluence"
                )
                clusters.append(cluster)
            
            processed_levels.add(i)
        
        return sorted(clusters, key=lambda x: x.strength, reverse=True)
    
    def _calculate_level_strength(self, ratio: float) -> float:
        """Calculate strength of Fibonacci level based on golden ratio proximity"""
        # Golden ratio and its derivatives have higher strength
        golden_ratio = 0.618
        golden_ratios = [0.236, 0.382, 0.618, 0.786, 1.618, 2.618]
        
        if ratio in golden_ratios:
            return 1.0
        elif ratio == 0.5:  # 50% retracement is psychologically important
            return 0.9
        elif ratio in [1.0, 2.0]:  # 100% and 200% levels
            return 0.8
        else:
            return 0.6
    
    def _ratio_to_enum(self, ratio: float) -> FibonacciLevel:
        """Convert ratio to FibonacciLevel enum"""
        ratio_map = {
            0.0: FibonacciLevel.LEVEL_0,
            0.236: FibonacciLevel.LEVEL_236,
            0.382: FibonacciLevel.LEVEL_382,
            0.500: FibonacciLevel.LEVEL_500,
            0.618: FibonacciLevel.LEVEL_618,
            0.786: FibonacciLevel.LEVEL_786,
            1.0: FibonacciLevel.LEVEL_100,
            1.272: FibonacciLevel.LEVEL_1272,
            1.414: FibonacciLevel.LEVEL_1414,
            1.618: FibonacciLevel.LEVEL_1618,
            2.0: FibonacciLevel.LEVEL_2000,
            2.618: FibonacciLevel.LEVEL_2618,
            3.0: FibonacciLevel.LEVEL_3000,
            4.236: FibonacciLevel.LEVEL_4236
        }
        return ratio_map.get(ratio, FibonacciLevel.LEVEL_500)

class FibonacciStrategy:
    """Base Fibonacci trading strategy"""
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.calculator = FibonacciCalculator()
        
        # Strategy parameters
        self.level_tolerance = config.parameters.get('level_tolerance', 0.005)
        self.min_level_strength = config.parameters.get('min_level_strength', 0.7)
        self.cluster_tolerance = config.parameters.get('cluster_tolerance', 0.01)
        self.lookback_periods = config.parameters.get('lookback_periods', 50)
        
        # Current state
        self.current_levels: List[FibonacciLevelData] = []
        self.current_clusters: List[FibonacciCluster] = []
        self.swing_points: List[FibonacciPoint] = []
    
    def analyze_market_data(self, market_data: Dict) -> Dict:
        """Analyze market data for Fibonacci patterns"""
        try:
            if pd is None:
                self.logger.error("Pandas not available for data analysis")
                return {}
            
            # Convert market data to DataFrame
            if isinstance(market_data, dict) and 'close' in market_data:
                df = pd.DataFrame([market_data])
            else:
                df = pd.DataFrame(market_data)
            
            if df.empty or len(df) < 10:
                return {}
            
            # Find swing points
            self.swing_points = self._find_swing_points(df)
            
            if len(self.swing_points) < 2:
                return {}
            
            # Calculate Fibonacci levels
            all_levels = []
            
            # Calculate retracements from recent swing points
            for i in range(len(self.swing_points) - 1):
                point_a = self.swing_points[i]
                point_b = self.swing_points[i + 1]
                
                retracements = self.calculator.calculate_retracements(point_a, point_b)
                all_levels.extend(retracements)
            
            # Calculate extensions from ABC patterns
            if len(self.swing_points) >= 3:
                for i in range(len(self.swing_points) - 2):
                    point_a = self.swing_points[i]
                    point_b = self.swing_points[i + 1]
                    point_c = self.swing_points[i + 2]
                    
                    extensions = self.calculator.calculate_extensions(point_a, point_b, point_c)
                    all_levels.extend(extensions)
            
            self.current_levels = all_levels
            
            # Find confluence clusters
            self.current_clusters = self.calculator.find_fibonacci_clusters(
                all_levels, self.cluster_tolerance
            )
            
            return {
                'levels': self.current_levels,
                'clusters': self.current_clusters,
                'swing_points': self.swing_points,
                'current_price': df['close'].iloc[-1] if 'close' in df.columns else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing market data: {e}")
            return {}
    
    def _find_swing_points(self, df: pd.DataFrame, window: int = 5) -> List[FibonacciPoint]:
        """Find swing high and low points"""
        if len(df) < window * 2 + 1:
            return []
        
        swing_points = []
        
        # Limit to recent data
        recent_df = df.tail(self.lookback_periods) if len(df) > self.lookback_periods else df
        
        for i in range(window, len(recent_df) - window):
            current_idx = len(df) - len(recent_df) + i
            
            # Check for swing high
            is_swing_high = all(
                recent_df['high'].iloc[i] >= recent_df['high'].iloc[j]
                for j in range(i - window, i + window + 1)
                if j != i
            )
            
            # Check for swing low
            is_swing_low = all(
                recent_df['low'].iloc[i] <= recent_df['low'].iloc[j]
                for j in range(i - window, i + window + 1)
                if j != i
            )
            
            if is_swing_high:
                point = FibonacciPoint(
                    price=recent_df['high'].iloc[i],
                    time=recent_df.index[i] if hasattr(recent_df.index[i], 'to_pydatetime') else datetime.now(),
                    point_type='swing_high',
                    significance=self._calculate_point_significance(recent_df, i, 'high')
                )
                swing_points.append(point)
            
            if is_swing_low:
                point = FibonacciPoint(
                    price=recent_df['low'].iloc[i],
                    time=recent_df.index[i] if hasattr(recent_df.index[i], 'to_pydatetime') else datetime.now(),
                    point_type='swing_low',
                    significance=self._calculate_point_significance(recent_df, i, 'low')
                )
                swing_points.append(point)
        
        # Sort by time and return most significant points
        swing_points.sort(key=lambda x: x.time)
        return swing_points[-10:]  # Keep last 10 swing points
    
    def _calculate_point_significance(self, df: pd.DataFrame, index: int, price_type: str) -> float:
        """Calculate significance of a swing point"""
        try:
            # Calculate based on price range and volume (if available)
            price_range = df['high'].iloc[index] - df['low'].iloc[index]
            avg_range = df['high'].rolling(20).mean().iloc[index] - df['low'].rolling(20).mean().iloc[index]
            
            range_significance = min(price_range / avg_range, 2.0) if avg_range > 0 else 1.0
            
            # Volume significance (if available)
            volume_significance = 1.0
            if 'volume' in df.columns:
                current_volume = df['volume'].iloc[index]
                avg_volume = df['volume'].rolling(20).mean().iloc[index]
                volume_significance = min(current_volume / avg_volume, 2.0) if avg_volume > 0 else 1.0
            
            return min((range_significance + volume_significance) / 2, 1.0)
            
        except Exception:
            return 1.0
    
    def generate_signals(self, market_data: Dict) -> List[TradingSignal]:
        """Generate trading signals based on Fibonacci analysis"""
        signals = []
        
        try:
            analysis = self.analyze_market_data(market_data)
            
            if not analysis:
                return signals
            
            current_price = analysis.get('current_price', 0)
            levels = analysis.get('levels', [])
            clusters = analysis.get('clusters', [])
            
            # Generate signals from Fibonacci levels
            signals.extend(self._generate_level_signals(current_price, levels))
            
            # Generate signals from confluence clusters
            signals.extend(self._generate_cluster_signals(current_price, clusters))
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating Fibonacci signals: {e}")
            return signals
    
    def _generate_level_signals(self, current_price: float, 
                              levels: List[FibonacciLevelData]) -> List[TradingSignal]:
        """Generate signals from individual Fibonacci levels"""
        signals = []
        
        for level in levels:
            if level.strength < self.min_level_strength:
                continue
            
            price_diff = abs(current_price - level.price) / current_price
            
            if price_diff <= self.level_tolerance:
                # Price is near Fibonacci level
                if level.level_type == FibonacciType.RETRACEMENT:
                    # Retracement level - expect bounce
                    if current_price <= level.price * 1.002:  # Slightly below level
                        signal = TradingSignal(
                            symbol=self.config.symbols[0] if self.config.symbols else "UNKNOWN",
                            signal_type=PositionType.LONG,
                            strength=self._level_to_signal_strength(level.strength),
                            confidence=level.strength,
                            entry_price=current_price,
                            stop_loss=level.price * 0.98,
                            take_profit=level.price * 1.04,
                            timestamp=datetime.now(),
                            metadata={
                                'strategy': 'fibonacci_retracement',
                                'fib_level': level.percentage,
                                'level_type': level.level_type.value,
                                'direction': level.direction.value
                            }
                        )
                        signals.append(signal)
                
                elif level.level_type == FibonacciType.EXTENSION:
                    # Extension level - expect resistance/support
                    if level.direction == FibonacciDirection.UPTREND and current_price >= level.price * 0.998:
                        signal = TradingSignal(
                            symbol=self.config.symbols[0] if self.config.symbols else "UNKNOWN",
                            signal_type=PositionType.SHORT,
                            strength=self._level_to_signal_strength(level.strength),
                            confidence=level.strength,
                            entry_price=current_price,
                            stop_loss=level.price * 1.02,
                            take_profit=level.price * 0.96,
                            timestamp=datetime.now(),
                            metadata={
                                'strategy': 'fibonacci_extension',
                                'fib_level': level.percentage,
                                'level_type': level.level_type.value,
                                'direction': level.direction.value
                            }
                        )
                        signals.append(signal)
        
        return signals
    
    def _generate_cluster_signals(self, current_price: float, 
                                clusters: List[FibonacciCluster]) -> List[TradingSignal]:
        """Generate signals from Fibonacci confluence clusters"""
        signals = []
        
        for cluster in clusters[:3]:  # Top 3 strongest clusters
            if cluster.strength < 0.7:
                continue
            
            price_diff = abs(current_price - cluster.price_center) / current_price
            
            if price_diff <= self.level_tolerance * 1.5:  # Slightly wider tolerance for clusters
                # Strong confluence zone
                if current_price <= cluster.price_center * 1.003:
                    signal = TradingSignal(
                        symbol=self.config.symbols[0] if self.config.symbols else "UNKNOWN",
                        signal_type=PositionType.LONG,
                        strength=SignalStrength.STRONG,
                        confidence=cluster.strength,
                        entry_price=current_price,
                        stop_loss=cluster.price_range[0] * 0.99,
                        take_profit=cluster.price_center * 1.05,
                        timestamp=datetime.now(),
                        metadata={
                            'strategy': 'fibonacci_confluence',
                            'cluster_strength': cluster.strength,
                            'confluence_count': cluster.confluence_count,
                            'cluster_center': cluster.price_center
                        }
                    )
                    signals.append(signal)
        
        return signals
    
    def _level_to_signal_strength(self, level_strength: float) -> SignalStrength:
        """Convert level strength to signal strength"""
        if level_strength >= 0.9:
            return SignalStrength.STRONG
        elif level_strength >= 0.7:
            return SignalStrength.MEDIUM
        else:
            return SignalStrength.WEAK

class FibonacciRetracementStrategy(FibonacciStrategy):
    """Fibonacci retracement-focused strategy"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.focus_levels = config.parameters.get('focus_levels', [0.382, 0.618])
    
    def generate_signals(self, market_data: Dict) -> List[TradingSignal]:
        """Generate signals focused on retracement levels"""
        signals = []
        
        try:
            analysis = self.analyze_market_data(market_data)
            
            if not analysis:
                return signals
            
            current_price = analysis.get('current_price', 0)
            levels = analysis.get('levels', [])
            
            # Focus on retracement levels only
            retracement_levels = [
                level for level in levels
                if level.level_type == FibonacciType.RETRACEMENT
                and level.percentage / 100 in self.focus_levels
            ]
            
            signals.extend(self._generate_level_signals(current_price, retracement_levels))
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating Fibonacci retracement signals: {e}")
            return signals

class FibonacciExtensionStrategy(FibonacciStrategy):
    """Fibonacci extension-focused strategy"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.focus_levels = config.parameters.get('focus_levels', [1.618, 2.618])
    
    def generate_signals(self, market_data: Dict) -> List[TradingSignal]:
        """Generate signals focused on extension levels"""
        signals = []
        
        try:
            analysis = self.analyze_market_data(market_data)
            
            if not analysis:
                return signals
            
            current_price = analysis.get('current_price', 0)
            levels = analysis.get('levels', [])
            
            # Focus on extension levels only
            extension_levels = [
                level for level in levels
                if level.level_type == FibonacciType.EXTENSION
                and level.percentage / 100 in self.focus_levels
            ]
            
            signals.extend(self._generate_level_signals(current_price, extension_levels))
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating Fibonacci extension signals: {e}")
            return signals

class FibonacciTimeStrategy(FibonacciStrategy):
    """Fibonacci time zone strategy"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.base_period_hours = config.parameters.get('base_period_hours', 24)
        self.time_tolerance_hours = config.parameters.get('time_tolerance_hours', 2)
    
    def generate_signals(self, market_data: Dict) -> List[TradingSignal]:
        """Generate signals based on Fibonacci time zones"""
        signals = []
        
        try:
            if not self.swing_points:
                return signals
            
            current_time = datetime.now()
            
            # Calculate time zones from recent swing points
            for swing_point in self.swing_points[-3:]:  # Last 3 swing points
                time_zones = self.calculator.calculate_time_zones(
                    swing_point.time, self.base_period_hours
                )
                
                # Check if current time is near any Fibonacci time zone
                for zone_time in time_zones.next_zones:
                    time_diff_hours = abs((current_time - zone_time).total_seconds()) / 3600
                    
                    if time_diff_hours <= self.time_tolerance_hours:
                        # Near Fibonacci time zone - expect reversal
                        if isinstance(market_data, dict) and 'close' in market_data:
                            current_price = market_data['close']
                            
                            signal = TradingSignal(
                                symbol=self.config.symbols[0] if self.config.symbols else "UNKNOWN",
                                signal_type=PositionType.LONG,  # Default, should be refined with price action
                                strength=SignalStrength.MEDIUM,
                                confidence=time_zones.strength,
                                entry_price=current_price,
                                stop_loss=current_price * 0.97,
                                take_profit=current_price * 1.05,
                                timestamp=datetime.now(),
                                metadata={
                                    'strategy': 'fibonacci_time',
                                    'time_zone': zone_time.isoformat(),
                                    'hours_to_zone': time_diff_hours,
                                    'base_period': self.base_period_hours
                                }
                            )
                            signals.append(signal)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating Fibonacci time signals: {e}")
            return signals

# Convenience aliases
FibRetracementStrategy = FibonacciRetracementStrategy
FibExtensionStrategy = FibonacciExtensionStrategy
FibTimeStrategy = FibonacciTimeStrategy

# Utility functions
def calculate_fibonacci_retracements(high_price: float, low_price: float, 
                                   high_time: datetime, low_time: datetime) -> List[FibonacciLevelData]:
    """Calculate Fibonacci retracement levels"""
    calculator = FibonacciCalculator()
    high_point = FibonacciPoint(high_price, high_time, 'swing_high')
    low_point = FibonacciPoint(low_price, low_time, 'swing_low')
    return calculator.calculate_retracements(high_point, low_point)

def calculate_fibonacci_extensions(price_a: float, time_a: datetime,
                                 price_b: float, time_b: datetime,
                                 price_c: float, time_c: datetime) -> List[FibonacciLevelData]:
    """Calculate Fibonacci extension levels"""
    calculator = FibonacciCalculator()
    point_a = FibonacciPoint(price_a, time_a, 'swing_point')
    point_b = FibonacciPoint(price_b, time_b, 'swing_point')
    point_c = FibonacciPoint(price_c, time_c, 'swing_point')
    return calculator.calculate_extensions(point_a, point_b, point_c)

def find_fibonacci_confluence(levels: List[FibonacciLevelData], 
                            tolerance: float = 0.01) -> List[FibonacciCluster]:
    """Find Fibonacci confluence zones"""
    calculator = FibonacciCalculator()
    return calculator.find_fibonacci_clusters(levels, tolerance)