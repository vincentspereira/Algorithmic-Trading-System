"""Gann Theory Strategies Module

This module implements W.D. Gann's trading methodologies including:
- Gann Angles (1x1, 2x1, 1x2, etc.)
- Gann Square of Nine
- Gann Time Cycles
- Gann Fan Analysis
- Gann Grid Systems

Key Features:
- Mathematical precision in angle calculations
- Time and price square relationships
- Dynamic support/resistance from Gann levels
- Multi-timeframe Gann analysis
- Automated Gann pattern recognition

Architecture:
Follows the 5-Pillar Architecture with mathematical engines for precise
Gann calculations and pattern recognition systems.
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

class GannAngleType(Enum):
    """Gann angle types"""
    ANGLE_1X8 = "1x8"
    ANGLE_1X4 = "1x4"
    ANGLE_1X3 = "1x3"
    ANGLE_1X2 = "1x2"
    ANGLE_1X1 = "1x1"  # 45-degree angle
    ANGLE_2X1 = "2x1"
    ANGLE_3X1 = "3x1"
    ANGLE_4X1 = "4x1"
    ANGLE_8X1 = "8x1"

class GannDirection(Enum):
    """Gann line direction"""
    UP = "up"
    DOWN = "down"

class GannSignalType(Enum):
    """Gann-specific signal types"""
    ANGLE_SUPPORT = "angle_support"
    ANGLE_RESISTANCE = "angle_resistance"
    ANGLE_BREAK = "angle_break"
    SQUARE_LEVEL = "square_level"
    TIME_CYCLE = "time_cycle"
    FAN_CONVERGENCE = "fan_convergence"

@dataclass
class GannAngle:
    """Gann angle definition"""
    angle_type: GannAngleType
    direction: GannDirection
    start_price: float
    start_time: datetime
    slope: float
    angle_degrees: float
    current_level: float
    
    def calculate_price_at_time(self, target_time: datetime) -> float:
        """Calculate price level at specific time"""
        time_diff = (target_time - self.start_time).total_seconds() / 3600  # hours
        
        if self.direction == GannDirection.UP:
            return self.start_price + (self.slope * time_diff)
        else:
            return self.start_price - (self.slope * time_diff)
    
    def get_angle_strength(self) -> float:
        """Get angle strength based on type"""
        strength_map = {
            GannAngleType.ANGLE_1X1: 1.0,  # Strongest
            GannAngleType.ANGLE_2X1: 0.8,
            GannAngleType.ANGLE_1X2: 0.8,
            GannAngleType.ANGLE_3X1: 0.6,
            GannAngleType.ANGLE_1X3: 0.6,
            GannAngleType.ANGLE_4X1: 0.4,
            GannAngleType.ANGLE_1X4: 0.4,
            GannAngleType.ANGLE_8X1: 0.2,
            GannAngleType.ANGLE_1X8: 0.2
        }
        return strength_map.get(self.angle_type, 0.5)

@dataclass
class GannLevel:
    """Gann support/resistance level"""
    price: float
    time: datetime
    level_type: str
    strength: float
    angle_source: Optional[GannAngle] = None
    square_source: Optional[int] = None

@dataclass
class GannTimeProjection:
    """Gann time cycle projection"""
    cycle_length: int  # in time units
    next_cycle_time: datetime
    cycle_type: str
    strength: float
    historical_accuracy: float = 0.0

class GannCalculator:
    """Core Gann calculation engine"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Gann angle ratios
        self.angle_ratios = {
            GannAngleType.ANGLE_1X8: 1/8,
            GannAngleType.ANGLE_1X4: 1/4,
            GannAngleType.ANGLE_1X3: 1/3,
            GannAngleType.ANGLE_1X2: 1/2,
            GannAngleType.ANGLE_1X1: 1/1,
            GannAngleType.ANGLE_2X1: 2/1,
            GannAngleType.ANGLE_3X1: 3/1,
            GannAngleType.ANGLE_4X1: 4/1,
            GannAngleType.ANGLE_8X1: 8/1
        }
    
    def calculate_gann_angles(self, start_price: float, start_time: datetime,
                            price_unit: float = 1.0, time_unit: int = 1) -> List[GannAngle]:
        """Calculate Gann angles from a pivot point"""
        angles = []
        
        for angle_type, ratio in self.angle_ratios.items():
            # Calculate slope (price change per time unit)
            slope = (price_unit * ratio) / time_unit
            
            # Calculate angle in degrees
            angle_degrees = math.degrees(math.atan(ratio))
            
            # Create upward angle
            up_angle = GannAngle(
                angle_type=angle_type,
                direction=GannDirection.UP,
                start_price=start_price,
                start_time=start_time,
                slope=slope,
                angle_degrees=angle_degrees,
                current_level=start_price
            )
            angles.append(up_angle)
            
            # Create downward angle
            down_angle = GannAngle(
                angle_type=angle_type,
                direction=GannDirection.DOWN,
                start_price=start_price,
                start_time=start_time,
                slope=slope,
                angle_degrees=angle_degrees,
                current_level=start_price
            )
            angles.append(down_angle)
        
        return angles
    
    def calculate_gann_square(self, center_price: float, max_range: float = 100.0) -> List[float]:
        """Calculate Gann Square of Nine levels"""
        levels = []
        
        # Calculate square root of center price
        sqrt_center = math.sqrt(center_price)
        
        # Generate levels based on square root increments
        for i in range(-50, 51):  # -50 to +50 increments
            if i == 0:
                continue
                
            new_sqrt = sqrt_center + (i * 0.1)  # 0.1 increment
            if new_sqrt > 0:
                new_price = new_sqrt ** 2
                
                # Only include levels within reasonable range
                if abs(new_price - center_price) <= max_range:
                    levels.append(new_price)
        
        return sorted(levels)
    
    def calculate_gann_time_cycles(self, start_date: datetime, 
                                 historical_cycles: List[int]) -> List[GannTimeProjection]:
        """Calculate Gann time cycle projections"""
        projections = []
        
        # Common Gann time cycles (in trading days)
        standard_cycles = [7, 14, 21, 30, 45, 60, 90, 120, 144, 180, 252, 360]
        
        # Combine standard cycles with historical patterns
        all_cycles = list(set(standard_cycles + historical_cycles))
        
        for cycle_length in all_cycles:
            next_cycle = start_date + timedelta(days=cycle_length)
            
            # Calculate cycle strength based on historical accuracy
            strength = self._calculate_cycle_strength(cycle_length, historical_cycles)
            
            projection = GannTimeProjection(
                cycle_length=cycle_length,
                next_cycle_time=next_cycle,
                cycle_type="standard" if cycle_length in standard_cycles else "custom",
                strength=strength
            )
            projections.append(projection)
        
        return projections
    
    def _calculate_cycle_strength(self, cycle_length: int, historical_cycles: List[int]) -> float:
        """Calculate strength of time cycle based on historical occurrence"""
        if not historical_cycles:
            return 0.5
        
        # Count occurrences of similar cycles (±2 days tolerance)
        similar_cycles = [
            c for c in historical_cycles 
            if abs(c - cycle_length) <= 2
        ]
        
        frequency = len(similar_cycles) / len(historical_cycles)
        return min(frequency * 2, 1.0)  # Cap at 1.0
    
    def find_gann_support_resistance(self, angles: List[GannAngle], 
                                   current_time: datetime,
                                   current_price: float,
                                   tolerance: float = 0.01) -> List[GannLevel]:
        """Find current Gann support and resistance levels"""
        levels = []
        
        for angle in angles:
            # Calculate current angle level
            angle_price = angle.calculate_price_at_time(current_time)
            
            # Check if current price is near this angle
            price_diff = abs(current_price - angle_price) / current_price
            
            if price_diff <= tolerance:
                level_type = "support" if angle.direction == GannDirection.UP else "resistance"
                if current_price > angle_price:
                    level_type = "support"
                else:
                    level_type = "resistance"
                
                level = GannLevel(
                    price=angle_price,
                    time=current_time,
                    level_type=level_type,
                    strength=angle.get_angle_strength(),
                    angle_source=angle
                )
                levels.append(level)
        
        return sorted(levels, key=lambda x: x.strength, reverse=True)

class GannStrategy:
    """Base Gann trading strategy"""
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.calculator = GannCalculator()
        
        # Strategy parameters
        self.angle_tolerance = config.parameters.get('angle_tolerance', 0.01)
        self.time_tolerance = config.parameters.get('time_tolerance', 0.1)
        self.min_angle_strength = config.parameters.get('min_angle_strength', 0.6)
        
        # Current state
        self.current_angles: List[GannAngle] = []
        self.current_levels: List[GannLevel] = []
        self.time_projections: List[GannTimeProjection] = []
    
    def analyze_market_data(self, market_data: Dict) -> Dict:
        """Analyze market data for Gann patterns"""
        try:
            # Extract OHLCV data
            if pd is None:
                self.logger.error("Pandas not available for data analysis")
                return {}
            
            # Convert market data to DataFrame if needed
            if isinstance(market_data, dict) and 'close' in market_data:
                df = pd.DataFrame([market_data])
            else:
                df = pd.DataFrame(market_data)
            
            if df.empty:
                return {}
            
            # Find pivot points for Gann angle calculation
            pivot_points = self._find_pivot_points(df)
            
            # Calculate Gann angles from recent pivots
            if pivot_points:
                latest_pivot = pivot_points[-1]
                self.current_angles = self.calculator.calculate_gann_angles(
                    start_price=latest_pivot['price'],
                    start_time=latest_pivot['time']
                )
            
            # Find current support/resistance levels
            current_time = datetime.now()
            current_price = df['close'].iloc[-1]
            
            self.current_levels = self.calculator.find_gann_support_resistance(
                self.current_angles,
                current_time,
                current_price,
                self.angle_tolerance
            )
            
            return {
                'angles': self.current_angles,
                'levels': self.current_levels,
                'pivot_points': pivot_points,
                'current_price': current_price
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing market data: {e}")
            return {}
    
    def _find_pivot_points(self, df: pd.DataFrame, window: int = 5) -> List[Dict]:
        """Find pivot points in price data"""
        if len(df) < window * 2 + 1:
            return []
        
        pivots = []
        
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
                pivots.append({
                    'type': 'high',
                    'price': df['high'].iloc[i],
                    'time': df.index[i] if hasattr(df.index[i], 'to_pydatetime') else datetime.now(),
                    'index': i
                })
            
            if is_pivot_low:
                pivots.append({
                    'type': 'low',
                    'price': df['low'].iloc[i],
                    'time': df.index[i] if hasattr(df.index[i], 'to_pydatetime') else datetime.now(),
                    'index': i
                })
        
        return sorted(pivots, key=lambda x: x['index'])
    
    def generate_signals(self, market_data: Dict) -> List[TradingSignal]:
        """Generate trading signals based on Gann analysis"""
        signals = []
        
        try:
            # Analyze market data
            analysis = self.analyze_market_data(market_data)
            
            if not analysis:
                return signals
            
            current_price = analysis.get('current_price', 0)
            levels = analysis.get('levels', [])
            
            # Generate signals based on Gann levels
            for level in levels[:3]:  # Top 3 strongest levels
                if level.strength < self.min_angle_strength:
                    continue
                
                # Determine signal type and strength
                signal_strength = self._calculate_signal_strength(level, current_price)
                
                if level.level_type == "support" and current_price <= level.price * 1.005:
                    # Price near support - potential buy signal
                    signal = TradingSignal(
                        symbol=self.config.symbols[0] if self.config.symbols else "UNKNOWN",
                        signal_type=PositionType.LONG,
                        strength=signal_strength,
                        confidence=level.strength,
                        entry_price=current_price,
                        stop_loss=level.price * 0.98,
                        take_profit=level.price * 1.04,
                        timestamp=datetime.now(),
                        metadata={
                            'strategy': 'gann',
                            'signal_source': 'angle_support',
                            'angle_type': level.angle_source.angle_type.value if level.angle_source else None,
                            'level_strength': level.strength
                        }
                    )
                    signals.append(signal)
                
                elif level.level_type == "resistance" and current_price >= level.price * 0.995:
                    # Price near resistance - potential sell signal
                    signal = TradingSignal(
                        symbol=self.config.symbols[0] if self.config.symbols else "UNKNOWN",
                        signal_type=PositionType.SHORT,
                        strength=signal_strength,
                        confidence=level.strength,
                        entry_price=current_price,
                        stop_loss=level.price * 1.02,
                        take_profit=level.price * 0.96,
                        timestamp=datetime.now(),
                        metadata={
                            'strategy': 'gann',
                            'signal_source': 'angle_resistance',
                            'angle_type': level.angle_source.angle_type.value if level.angle_source else None,
                            'level_strength': level.strength
                        }
                    )
                    signals.append(signal)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating Gann signals: {e}")
            return signals
    
    def _calculate_signal_strength(self, level: GannLevel, current_price: float) -> SignalStrength:
        """Calculate signal strength based on level properties"""
        # Base strength on Gann level strength
        if level.strength >= 0.8:
            return SignalStrength.STRONG
        elif level.strength >= 0.6:
            return SignalStrength.MEDIUM
        else:
            return SignalStrength.WEAK

class GannAngleStrategy(GannStrategy):
    """Gann angle-specific trading strategy"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.focus_angles = config.parameters.get('focus_angles', [GannAngleType.ANGLE_1X1])
    
    def generate_signals(self, market_data: Dict) -> List[TradingSignal]:
        """Generate signals focused on specific Gann angles"""
        signals = []
        
        try:
            analysis = self.analyze_market_data(market_data)
            
            if not analysis:
                return signals
            
            current_price = analysis.get('current_price', 0)
            angles = analysis.get('angles', [])
            
            # Focus on specific angles
            focused_angles = [
                angle for angle in angles
                if angle.angle_type in self.focus_angles
            ]
            
            current_time = datetime.now()
            
            for angle in focused_angles:
                angle_price = angle.calculate_price_at_time(current_time)
                price_diff = abs(current_price - angle_price) / current_price
                
                if price_diff <= self.angle_tolerance:
                    # Price is touching the angle line
                    if angle.direction == GannDirection.UP and current_price >= angle_price:
                        # Bullish angle support
                        signal = TradingSignal(
                            symbol=self.config.symbols[0] if self.config.symbols else "UNKNOWN",
                            signal_type=PositionType.LONG,
                            strength=SignalStrength.STRONG if angle.angle_type == GannAngleType.ANGLE_1X1 else SignalStrength.MEDIUM,
                            confidence=angle.get_angle_strength(),
                            entry_price=current_price,
                            stop_loss=angle_price * 0.98,
                            take_profit=angle_price * 1.06,
                            timestamp=datetime.now(),
                            metadata={
                                'strategy': 'gann_angle',
                                'angle_type': angle.angle_type.value,
                                'angle_direction': angle.direction.value,
                                'angle_degrees': angle.angle_degrees
                            }
                        )
                        signals.append(signal)
                    
                    elif angle.direction == GannDirection.DOWN and current_price <= angle_price:
                        # Bearish angle resistance
                        signal = TradingSignal(
                            symbol=self.config.symbols[0] if self.config.symbols else "UNKNOWN",
                            signal_type=PositionType.SHORT,
                            strength=SignalStrength.STRONG if angle.angle_type == GannAngleType.ANGLE_1X1 else SignalStrength.MEDIUM,
                            confidence=angle.get_angle_strength(),
                            entry_price=current_price,
                            stop_loss=angle_price * 1.02,
                            take_profit=angle_price * 0.94,
                            timestamp=datetime.now(),
                            metadata={
                                'strategy': 'gann_angle',
                                'angle_type': angle.angle_type.value,
                                'angle_direction': angle.direction.value,
                                'angle_degrees': angle.angle_degrees
                            }
                        )
                        signals.append(signal)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating Gann angle signals: {e}")
            return signals

class GannSquareStrategy(GannStrategy):
    """Gann Square of Nine trading strategy"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.square_range = config.parameters.get('square_range', 50.0)
    
    def generate_signals(self, market_data: Dict) -> List[TradingSignal]:
        """Generate signals based on Gann Square levels"""
        signals = []
        
        try:
            if isinstance(market_data, dict) and 'close' in market_data:
                current_price = market_data['close']
            else:
                return signals
            
            # Calculate Gann Square levels
            square_levels = self.calculator.calculate_gann_square(
                center_price=current_price,
                max_range=self.square_range
            )
            
            # Find nearest levels
            nearest_levels = self._find_nearest_square_levels(current_price, square_levels)
            
            for level_price in nearest_levels:
                price_diff = abs(current_price - level_price) / current_price
                
                if price_diff <= 0.005:  # Within 0.5% of square level
                    if current_price < level_price:
                        # Price approaching resistance
                        signal = TradingSignal(
                            symbol=self.config.symbols[0] if self.config.symbols else "UNKNOWN",
                            signal_type=PositionType.SHORT,
                            strength=SignalStrength.MEDIUM,
                            confidence=0.7,
                            entry_price=current_price,
                            stop_loss=level_price * 1.01,
                            take_profit=level_price * 0.97,
                            timestamp=datetime.now(),
                            metadata={
                                'strategy': 'gann_square',
                                'square_level': level_price,
                                'level_type': 'resistance'
                            }
                        )
                        signals.append(signal)
                    
                    else:
                        # Price approaching support
                        signal = TradingSignal(
                            symbol=self.config.symbols[0] if self.config.symbols else "UNKNOWN",
                            signal_type=PositionType.LONG,
                            strength=SignalStrength.MEDIUM,
                            confidence=0.7,
                            entry_price=current_price,
                            stop_loss=level_price * 0.99,
                            take_profit=level_price * 1.03,
                            timestamp=datetime.now(),
                            metadata={
                                'strategy': 'gann_square',
                                'square_level': level_price,
                                'level_type': 'support'
                            }
                        )
                        signals.append(signal)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating Gann square signals: {e}")
            return signals
    
    def _find_nearest_square_levels(self, current_price: float, 
                                  square_levels: List[float], 
                                  max_levels: int = 5) -> List[float]:
        """Find nearest Gann square levels to current price"""
        # Sort levels by distance from current price
        levels_with_distance = [
            (level, abs(level - current_price))
            for level in square_levels
        ]
        
        levels_with_distance.sort(key=lambda x: x[1])
        
        return [level for level, _ in levels_with_distance[:max_levels]]

class GannTimeStrategy(GannStrategy):
    """Gann time cycle trading strategy"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.historical_cycles = config.parameters.get('historical_cycles', [])
        self.cycle_tolerance_days = config.parameters.get('cycle_tolerance_days', 2)
    
    def generate_signals(self, market_data: Dict) -> List[TradingSignal]:
        """Generate signals based on Gann time cycles"""
        signals = []
        
        try:
            current_time = datetime.now()
            
            # Calculate time projections
            self.time_projections = self.calculator.calculate_gann_time_cycles(
                start_date=current_time - timedelta(days=252),  # 1 year back
                historical_cycles=self.historical_cycles
            )
            
            # Check for approaching time cycles
            for projection in self.time_projections:
                days_to_cycle = (projection.next_cycle_time - current_time).days
                
                if abs(days_to_cycle) <= self.cycle_tolerance_days:
                    # Time cycle is approaching or just passed
                    if isinstance(market_data, dict) and 'close' in market_data:
                        current_price = market_data['close']
                        
                        # Generate reversal signal based on cycle
                        signal_strength = SignalStrength.STRONG if projection.strength > 0.7 else SignalStrength.MEDIUM
                        
                        # Assume reversal signal (could be refined with price action)
                        signal = TradingSignal(
                            symbol=self.config.symbols[0] if self.config.symbols else "UNKNOWN",
                            signal_type=PositionType.LONG,  # Default to long, should be refined
                            strength=signal_strength,
                            confidence=projection.strength,
                            entry_price=current_price,
                            stop_loss=current_price * 0.97,
                            take_profit=current_price * 1.05,
                            timestamp=datetime.now(),
                            metadata={
                                'strategy': 'gann_time',
                                'cycle_length': projection.cycle_length,
                                'cycle_type': projection.cycle_type,
                                'days_to_cycle': days_to_cycle,
                                'cycle_strength': projection.strength
                            }
                        )
                        signals.append(signal)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating Gann time signals: {e}")
            return signals

# Convenience classes
GannFanStrategy = GannAngleStrategy  # Alias for fan analysis
GannGridStrategy = GannStrategy      # Alias for grid analysis

# Utility functions
def calculate_gann_angles(start_price: float, start_time: datetime) -> List[GannAngle]:
    """Calculate Gann angles from a pivot point"""
    calculator = GannCalculator()
    return calculator.calculate_gann_angles(start_price, start_time)

def calculate_gann_square(center_price: float, max_range: float = 100.0) -> List[float]:
    """Calculate Gann Square of Nine levels"""
    calculator = GannCalculator()
    return calculator.calculate_gann_square(center_price, max_range)

def find_gann_support_resistance(angles: List[GannAngle], current_time: datetime,
                               current_price: float, tolerance: float = 0.01) -> List[GannLevel]:
    """Find current Gann support and resistance levels"""
    calculator = GannCalculator()
    return calculator.find_gann_support_resistance(angles, current_time, current_price, tolerance)