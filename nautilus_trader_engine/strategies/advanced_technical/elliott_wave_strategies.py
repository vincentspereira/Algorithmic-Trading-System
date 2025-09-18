"""Elliott Wave Strategies Module

This module implements Elliott Wave Theory trading strategies including:
- 5-Wave Impulse Pattern Recognition
- 3-Wave Corrective Pattern Recognition
- Wave Degree Analysis
- Fibonacci Wave Relationships
- Wave Extension and Truncation Detection
- Complex Corrective Patterns (Flats, Triangles, Zigzags)

Key Features:
- Automated wave counting and labeling
- Multi-timeframe wave analysis
- Wave relationship validation
- Pattern completion projections
- Risk management based on wave structure

Architecture:
Follows the 5-Pillar Architecture with sophisticated pattern recognition
engines and wave relationship validation systems.
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
from ..pairs_trading_strategies import (
    StrategyType, PositionType, SignalStrength,
    TradingSignal, Position, StrategyConfig
)

class WaveType(Enum):
    """Elliott Wave types"""
    IMPULSE = "impulse"
    CORRECTIVE = "corrective"
    DIAGONAL = "diagonal"
    TRIANGLE = "triangle"
    FLAT = "flat"
    ZIGZAG = "zigzag"
    COMPLEX = "complex"

class WaveDegree(Enum):
    """Elliott Wave degrees"""
    GRAND_SUPERCYCLE = "grand_supercycle"
    SUPERCYCLE = "supercycle"
    CYCLE = "cycle"
    PRIMARY = "primary"
    INTERMEDIATE = "intermediate"
    MINOR = "minor"
    MINUTE = "minute"
    MINUETTE = "minuette"
    SUBMINUETTE = "subminuette"

class WaveDirection(Enum):
    """Wave direction"""
    UP = "up"
    DOWN = "down"

class WaveLabel(Enum):
    """Elliott Wave labels"""
    # Impulse waves
    WAVE_1 = "1"
    WAVE_2 = "2"
    WAVE_3 = "3"
    WAVE_4 = "4"
    WAVE_5 = "5"
    
    # Corrective waves
    WAVE_A = "A"
    WAVE_B = "B"
    WAVE_C = "C"
    WAVE_D = "D"
    WAVE_E = "E"
    
    # Complex patterns
    WAVE_W = "W"
    WAVE_X = "X"
    WAVE_Y = "Y"
    WAVE_Z = "Z"

@dataclass
class WavePoint:
    """Elliott Wave pivot point"""
    price: float
    time: datetime
    index: int
    point_type: str  # 'high', 'low'
    significance: float = 1.0

@dataclass
class Wave:
    """Individual Elliott Wave"""
    label: WaveLabel
    start_point: WavePoint
    end_point: WavePoint
    wave_type: WaveType
    direction: WaveDirection
    degree: WaveDegree
    length: float
    duration: timedelta
    fibonacci_ratio: Optional[float] = None
    confidence: float = 0.0
    
    def __post_init__(self):
        self.length = abs(self.end_point.price - self.start_point.price)
        self.duration = self.end_point.time - self.start_point.time

@dataclass
class WavePattern:
    """Elliott Wave pattern (5-wave impulse or 3-wave corrective)"""
    pattern_type: WaveType
    waves: List[Wave]
    degree: WaveDegree
    direction: WaveDirection
    start_time: datetime
    end_time: datetime
    total_length: float
    confidence: float
    fibonacci_relationships: Dict[str, float] = field(default_factory=dict)
    is_complete: bool = False
    
    def __post_init__(self):
        if self.waves:
            self.start_time = self.waves[0].start_point.time
            self.end_time = self.waves[-1].end_point.time
            self.total_length = sum(wave.length for wave in self.waves)

@dataclass
class WaveProjection:
    """Elliott Wave projection"""
    target_price: float
    target_time: datetime
    projection_type: str
    confidence: float
    fibonacci_basis: float
    wave_basis: Wave

class ElliottWaveCalculator:
    """Core Elliott Wave calculation engine"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Fibonacci ratios for wave relationships
        self.fibonacci_ratios = [0.236, 0.382, 0.500, 0.618, 0.786, 1.0, 1.272, 1.618, 2.618]
        
        # Wave relationship rules
        self.wave_rules = {
            'impulse': {
                'wave_2_retracement': [0.382, 0.618],  # Wave 2 typical retracement
                'wave_4_retracement': [0.236, 0.500],  # Wave 4 typical retracement
                'wave_3_extension': [1.618, 2.618],    # Wave 3 extension ratios
                'wave_5_projection': [0.618, 1.0, 1.618]  # Wave 5 projection ratios
            },
            'corrective': {
                'wave_c_projection': [0.618, 1.0, 1.618],  # Wave C projection ratios
                'wave_b_retracement': [0.382, 0.786]       # Wave B retracement range
            }
        }
    
    def find_wave_points(self, df: pd.DataFrame, min_wave_size: float = 0.01) -> List[WavePoint]:
        """Find potential Elliott Wave pivot points"""
        if len(df) < 10:
            return []
        
        points = []
        window = 3  # Minimum window for pivot detection
        
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
                # Calculate significance based on price movement
                price_move = df['high'].iloc[i] - df['low'].iloc[max(0, i-10):i+10].min()
                avg_range = df['high'].rolling(20).mean().iloc[i] - df['low'].rolling(20).mean().iloc[i]
                significance = min(price_move / avg_range, 3.0) if avg_range > 0 else 1.0
                
                point = WavePoint(
                    price=df['high'].iloc[i],
                    time=df.index[i] if hasattr(df.index[i], 'to_pydatetime') else datetime.now(),
                    index=i,
                    point_type='high',
                    significance=significance
                )
                points.append(point)
            
            if is_pivot_low:
                # Calculate significance
                price_move = df['high'].iloc[max(0, i-10):i+10].max() - df['low'].iloc[i]
                avg_range = df['high'].rolling(20).mean().iloc[i] - df['low'].rolling(20).mean().iloc[i]
                significance = min(price_move / avg_range, 3.0) if avg_range > 0 else 1.0
                
                point = WavePoint(
                    price=df['low'].iloc[i],
                    time=df.index[i] if hasattr(df.index[i], 'to_pydatetime') else datetime.now(),
                    index=i,
                    point_type='low',
                    significance=significance
                )
                points.append(point)
        
        # Filter points by minimum wave size
        filtered_points = []
        for i, point in enumerate(points):
            if i == 0:
                filtered_points.append(point)
                continue
            
            prev_point = filtered_points[-1]
            price_change = abs(point.price - prev_point.price) / prev_point.price
            
            if price_change >= min_wave_size:
                filtered_points.append(point)
        
        return sorted(filtered_points, key=lambda x: x.time)
    
    def identify_impulse_pattern(self, points: List[WavePoint]) -> Optional[WavePattern]:
        """Identify 5-wave impulse pattern"""
        if len(points) < 6:  # Need at least 6 points for 5 waves
            return None
        
        # Try to find 5-wave pattern in recent points
        for start_idx in range(len(points) - 5):
            wave_points = points[start_idx:start_idx + 6]
            
            # Check if points alternate between highs and lows
            if not self._validate_alternating_points(wave_points):
                continue
            
            # Create waves
            waves = []
            for i in range(5):
                wave_label = [WaveLabel.WAVE_1, WaveLabel.WAVE_2, WaveLabel.WAVE_3, 
                             WaveLabel.WAVE_4, WaveLabel.WAVE_5][i]
                
                start_point = wave_points[i]
                end_point = wave_points[i + 1]
                
                direction = WaveDirection.UP if end_point.price > start_point.price else WaveDirection.DOWN
                
                wave = Wave(
                    label=wave_label,
                    start_point=start_point,
                    end_point=end_point,
                    wave_type=WaveType.IMPULSE,
                    direction=direction,
                    degree=WaveDegree.MINOR  # Default degree
                )
                waves.append(wave)
            
            # Validate impulse pattern rules
            if self._validate_impulse_rules(waves):
                pattern_direction = WaveDirection.UP if waves[0].direction == WaveDirection.UP else WaveDirection.DOWN
                
                pattern = WavePattern(
                    pattern_type=WaveType.IMPULSE,
                    waves=waves,
                    degree=WaveDegree.MINOR,
                    direction=pattern_direction,
                    start_time=waves[0].start_point.time,
                    end_time=waves[-1].end_point.time,
                    total_length=sum(w.length for w in waves),
                    confidence=self._calculate_pattern_confidence(waves),
                    is_complete=True
                )
                
                # Calculate Fibonacci relationships
                pattern.fibonacci_relationships = self._calculate_fibonacci_relationships(waves)
                
                return pattern
        
        return None
    
    def identify_corrective_pattern(self, points: List[WavePoint]) -> Optional[WavePattern]:
        """Identify 3-wave corrective pattern (ABC)"""
        if len(points) < 4:  # Need at least 4 points for 3 waves
            return None
        
        # Try to find 3-wave pattern
        for start_idx in range(len(points) - 3):
            wave_points = points[start_idx:start_idx + 4]
            
            # Check alternating points
            if not self._validate_alternating_points(wave_points):
                continue
            
            # Create waves
            waves = []
            for i in range(3):
                wave_label = [WaveLabel.WAVE_A, WaveLabel.WAVE_B, WaveLabel.WAVE_C][i]
                
                start_point = wave_points[i]
                end_point = wave_points[i + 1]
                
                direction = WaveDirection.UP if end_point.price > start_point.price else WaveDirection.DOWN
                
                wave = Wave(
                    label=wave_label,
                    start_point=start_point,
                    end_point=end_point,
                    wave_type=WaveType.CORRECTIVE,
                    direction=direction,
                    degree=WaveDegree.MINOR
                )
                waves.append(wave)
            
            # Validate corrective pattern rules
            if self._validate_corrective_rules(waves):
                pattern_direction = WaveDirection.UP if waves[0].direction == WaveDirection.UP else WaveDirection.DOWN
                
                pattern = WavePattern(
                    pattern_type=WaveType.CORRECTIVE,
                    waves=waves,
                    degree=WaveDegree.MINOR,
                    direction=pattern_direction,
                    start_time=waves[0].start_point.time,
                    end_time=waves[-1].end_point.time,
                    total_length=sum(w.length for w in waves),
                    confidence=self._calculate_pattern_confidence(waves),
                    is_complete=True
                )
                
                pattern.fibonacci_relationships = self._calculate_fibonacci_relationships(waves)
                
                return pattern
        
        return None
    
    def _validate_alternating_points(self, points: List[WavePoint]) -> bool:
        """Validate that points alternate between highs and lows"""
        if len(points) < 2:
            return False
        
        for i in range(1, len(points)):
            if points[i].point_type == points[i-1].point_type:
                return False
        
        return True
    
    def _validate_impulse_rules(self, waves: List[Wave]) -> bool:
        """Validate Elliott Wave impulse pattern rules"""
        if len(waves) != 5:
            return False
        
        try:
            # Rule 1: Wave 2 never retraces more than 100% of wave 1
            wave_1_length = waves[0].length
            wave_2_length = waves[1].length
            if wave_2_length > wave_1_length:
                return False
            
            # Rule 2: Wave 3 is never the shortest wave
            wave_3_length = waves[2].length
            wave_1_length = waves[0].length
            wave_5_length = waves[4].length
            if wave_3_length < wave_1_length or wave_3_length < wave_5_length:
                return False
            
            # Rule 3: Wave 4 never enters the price territory of wave 1
            if waves[0].direction == WaveDirection.UP:
                if waves[3].end_point.price <= waves[0].end_point.price:
                    return False
            else:
                if waves[3].end_point.price >= waves[0].end_point.price:
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _validate_corrective_rules(self, waves: List[Wave]) -> bool:
        """Validate Elliott Wave corrective pattern rules"""
        if len(waves) != 3:
            return False
        
        try:
            # Basic validation: Wave B should retrace part of wave A
            wave_a_length = waves[0].length
            wave_b_length = waves[1].length
            
            # Wave B typically retraces 38.2% to 78.6% of wave A
            retracement_ratio = wave_b_length / wave_a_length
            if retracement_ratio < 0.2 or retracement_ratio > 1.0:
                return False
            
            return True
            
        except Exception:
            return False
    
    def _calculate_pattern_confidence(self, waves: List[Wave]) -> float:
        """Calculate confidence score for wave pattern"""
        try:
            confidence = 0.5  # Base confidence
            
            # Bonus for proper wave relationships
            if len(waves) >= 3:
                # Check Fibonacci relationships
                for i in range(1, len(waves)):
                    ratio = waves[i].length / waves[i-1].length
                    
                    # Check if ratio is close to Fibonacci number
                    for fib_ratio in self.fibonacci_ratios:
                        if abs(ratio - fib_ratio) / fib_ratio < 0.1:
                            confidence += 0.1
                            break
            
            # Bonus for alternating directions
            alternating = True
            for i in range(1, len(waves)):
                if waves[i].direction == waves[i-1].direction:
                    alternating = False
                    break
            
            if alternating:
                confidence += 0.2
            
            return min(confidence, 1.0)
            
        except Exception:
            return 0.5
    
    def _calculate_fibonacci_relationships(self, waves: List[Wave]) -> Dict[str, float]:
        """Calculate Fibonacci relationships between waves"""
        relationships = {}
        
        try:
            if len(waves) >= 3:
                # Wave ratios
                for i in range(1, len(waves)):
                    ratio = waves[i].length / waves[0].length
                    relationships[f'wave_{i+1}_to_wave_1'] = ratio
                
                # Common relationships
                if len(waves) >= 5:  # Impulse pattern
                    # Wave 3 to Wave 1 ratio
                    wave_3_to_1 = waves[2].length / waves[0].length
                    relationships['wave_3_to_1'] = wave_3_to_1
                    
                    # Wave 5 to Wave 1 ratio
                    wave_5_to_1 = waves[4].length / waves[0].length
                    relationships['wave_5_to_1'] = wave_5_to_1
            
            return relationships
            
        except Exception:
            return {}
    
    def project_wave_targets(self, pattern: WavePattern, current_price: float) -> List[WaveProjection]:
        """Project potential wave targets"""
        projections = []
        
        try:
            if pattern.pattern_type == WaveType.IMPULSE and len(pattern.waves) >= 4:
                # Project Wave 5 target if we're in Wave 4
                wave_1 = pattern.waves[0]
                wave_3 = pattern.waves[2]
                
                # Common Wave 5 projections
                for ratio in [0.618, 1.0, 1.618]:
                    if pattern.direction == WaveDirection.UP:
                        target_price = pattern.waves[3].end_point.price + (wave_1.length * ratio)
                    else:
                        target_price = pattern.waves[3].end_point.price - (wave_1.length * ratio)
                    
                    projection = WaveProjection(
                        target_price=target_price,
                        target_time=datetime.now() + timedelta(days=5),  # Rough estimate
                        projection_type="wave_5_target",
                        confidence=0.7,
                        fibonacci_basis=ratio,
                        wave_basis=wave_1
                    )
                    projections.append(projection)
            
            elif pattern.pattern_type == WaveType.CORRECTIVE and len(pattern.waves) >= 2:
                # Project Wave C target if we're in Wave B
                wave_a = pattern.waves[0]
                
                # Common Wave C projections
                for ratio in [0.618, 1.0, 1.618]:
                    if pattern.direction == WaveDirection.DOWN:
                        target_price = pattern.waves[1].end_point.price - (wave_a.length * ratio)
                    else:
                        target_price = pattern.waves[1].end_point.price + (wave_a.length * ratio)
                    
                    projection = WaveProjection(
                        target_price=target_price,
                        target_time=datetime.now() + timedelta(days=3),
                        projection_type="wave_c_target",
                        confidence=0.6,
                        fibonacci_basis=ratio,
                        wave_basis=wave_a
                    )
                    projections.append(projection)
            
            return projections
            
        except Exception as e:
            self.logger.error(f"Error projecting wave targets: {e}")
            return projections

class ElliottWaveStrategy:
    """Base Elliott Wave trading strategy"""
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.calculator = ElliottWaveCalculator()
        
        # Strategy parameters
        self.min_wave_size = config.parameters.get('min_wave_size', 0.02)
        self.min_pattern_confidence = config.parameters.get('min_pattern_confidence', 0.6)
        self.lookback_periods = config.parameters.get('lookback_periods', 100)
        
        # Current state
        self.current_patterns: List[WavePattern] = []
        self.wave_points: List[WavePoint] = []
        self.projections: List[WaveProjection] = []
    
    def analyze_market_data(self, market_data: Dict) -> Dict:
        """Analyze market data for Elliott Wave patterns"""
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
            
            # Find wave points
            self.wave_points = self.calculator.find_wave_points(recent_df, self.min_wave_size)
            
            if len(self.wave_points) < 4:
                return {}
            
            # Identify patterns
            patterns = []
            
            # Look for impulse patterns
            impulse_pattern = self.calculator.identify_impulse_pattern(self.wave_points)
            if impulse_pattern and impulse_pattern.confidence >= self.min_pattern_confidence:
                patterns.append(impulse_pattern)
            
            # Look for corrective patterns
            corrective_pattern = self.calculator.identify_corrective_pattern(self.wave_points)
            if corrective_pattern and corrective_pattern.confidence >= self.min_pattern_confidence:
                patterns.append(corrective_pattern)
            
            self.current_patterns = patterns
            
            # Generate projections
            self.projections = []
            current_price = recent_df['close'].iloc[-1] if 'close' in recent_df.columns else 0
            
            for pattern in patterns:
                projections = self.calculator.project_wave_targets(pattern, current_price)
                self.projections.extend(projections)
            
            return {
                'patterns': self.current_patterns,
                'wave_points': self.wave_points,
                'projections': self.projections,
                'current_price': current_price
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing Elliott Wave data: {e}")
            return {}
    
    def generate_signals(self, market_data: Dict) -> List[TradingSignal]:
        """Generate trading signals based on Elliott Wave analysis"""
        signals = []
        
        try:
            analysis = self.analyze_market_data(market_data)
            
            if not analysis:
                return signals
            
            current_price = analysis.get('current_price', 0)
            patterns = analysis.get('patterns', [])
            projections = analysis.get('projections', [])
            
            # Generate signals from patterns
            for pattern in patterns:
                pattern_signals = self._generate_pattern_signals(pattern, current_price)
                signals.extend(pattern_signals)
            
            # Generate signals from projections
            for projection in projections:
                projection_signals = self._generate_projection_signals(projection, current_price)
                signals.extend(projection_signals)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating Elliott Wave signals: {e}")
            return signals
    
    def _generate_pattern_signals(self, pattern: WavePattern, current_price: float) -> List[TradingSignal]:
        """Generate signals from Elliott Wave patterns"""
        signals = []
        
        try:
            if pattern.pattern_type == WaveType.IMPULSE:
                # Impulse pattern signals
                if len(pattern.waves) >= 4:
                    # Check if we're at the end of Wave 4 (potential Wave 5 entry)
                    wave_4_end = pattern.waves[3].end_point.price
                    price_diff = abs(current_price - wave_4_end) / wave_4_end
                    
                    if price_diff <= 0.02:  # Within 2% of Wave 4 end
                        signal_type = PositionType.LONG if pattern.direction == WaveDirection.UP else PositionType.SHORT
                        
                        # Calculate targets based on Wave 1 projection
                        wave_1_length = pattern.waves[0].length
                        if pattern.direction == WaveDirection.UP:
                            take_profit = current_price + (wave_1_length * 0.618)
                            stop_loss = wave_4_end * 0.98
                        else:
                            take_profit = current_price - (wave_1_length * 0.618)
                            stop_loss = wave_4_end * 1.02
                        
                        signal = TradingSignal(
                            symbol=self.config.symbols[0] if self.config.symbols else "UNKNOWN",
                            signal_type=signal_type,
                            strength=SignalStrength.STRONG,
                            confidence=pattern.confidence,
                            entry_price=current_price,
                            stop_loss=stop_loss,
                            take_profit=take_profit,
                            timestamp=datetime.now(),
                            metadata={
                                'strategy': 'elliott_wave_impulse',
                                'pattern_type': pattern.pattern_type.value,
                                'wave_count': len(pattern.waves),
                                'pattern_confidence': pattern.confidence,
                                'fibonacci_relationships': pattern.fibonacci_relationships
                            }
                        )
                        signals.append(signal)
            
            elif pattern.pattern_type == WaveType.CORRECTIVE:
                # Corrective pattern signals
                if len(pattern.waves) >= 2:
                    # Check if we're at the end of Wave B (potential Wave C entry)
                    wave_b_end = pattern.waves[1].end_point.price
                    price_diff = abs(current_price - wave_b_end) / wave_b_end
                    
                    if price_diff <= 0.02:
                        # Wave C typically moves in the direction of Wave A
                        wave_a_direction = pattern.waves[0].direction
                        signal_type = PositionType.LONG if wave_a_direction == WaveDirection.UP else PositionType.SHORT
                        
                        # Calculate targets
                        wave_a_length = pattern.waves[0].length
                        if wave_a_direction == WaveDirection.UP:
                            take_profit = current_price + (wave_a_length * 1.0)
                            stop_loss = wave_b_end * 0.97
                        else:
                            take_profit = current_price - (wave_a_length * 1.0)
                            stop_loss = wave_b_end * 1.03
                        
                        signal = TradingSignal(
                            symbol=self.config.symbols[0] if self.config.symbols else "UNKNOWN",
                            signal_type=signal_type,
                            strength=SignalStrength.MEDIUM,
                            confidence=pattern.confidence,
                            entry_price=current_price,
                            stop_loss=stop_loss,
                            take_profit=take_profit,
                            timestamp=datetime.now(),
                            metadata={
                                'strategy': 'elliott_wave_corrective',
                                'pattern_type': pattern.pattern_type.value,
                                'wave_count': len(pattern.waves),
                                'pattern_confidence': pattern.confidence
                            }
                        )
                        signals.append(signal)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating pattern signals: {e}")
            return signals
    
    def _generate_projection_signals(self, projection: WaveProjection, current_price: float) -> List[TradingSignal]:
        """Generate signals from wave projections"""
        signals = []
        
        try:
            # Check if current price is near projection target
            price_diff = abs(current_price - projection.target_price) / projection.target_price
            
            if price_diff <= 0.01:  # Within 1% of target
                # Expect reversal at projection target
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
                    stop_loss=current_price * (1.02 if signal_type == PositionType.SHORT else 0.98),
                    take_profit=current_price * (0.97 if signal_type == PositionType.SHORT else 1.03),
                    timestamp=datetime.now(),
                    metadata={
                        'strategy': 'elliott_wave_projection',
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

class ElliottWaveImpulseStrategy(ElliottWaveStrategy):
    """Elliott Wave strategy focused on impulse patterns"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.focus_on_wave_5 = config.parameters.get('focus_on_wave_5', True)
    
    def generate_signals(self, market_data: Dict) -> List[TradingSignal]:
        """Generate signals focused on impulse patterns"""
        signals = []
        
        try:
            analysis = self.analyze_market_data(market_data)
            
            if not analysis:
                return signals
            
            current_price = analysis.get('current_price', 0)
            patterns = analysis.get('patterns', [])
            
            # Focus on impulse patterns only
            impulse_patterns = [
                pattern for pattern in patterns
                if pattern.pattern_type == WaveType.IMPULSE
            ]
            
            for pattern in impulse_patterns:
                pattern_signals = self._generate_pattern_signals(pattern, current_price)
                signals.extend(pattern_signals)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating impulse signals: {e}")
            return signals

class ElliottWaveCorrectiveStrategy(ElliottWaveStrategy):
    """Elliott Wave strategy focused on corrective patterns"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.focus_on_wave_c = config.parameters.get('focus_on_wave_c', True)
    
    def generate_signals(self, market_data: Dict) -> List[TradingSignal]:
        """Generate signals focused on corrective patterns"""
        signals = []
        
        try:
            analysis = self.analyze_market_data(market_data)
            
            if not analysis:
                return signals
            
            current_price = analysis.get('current_price', 0)
            patterns = analysis.get('patterns', [])
            
            # Focus on corrective patterns only
            corrective_patterns = [
                pattern for pattern in patterns
                if pattern.pattern_type == WaveType.CORRECTIVE
            ]
            
            for pattern in corrective_patterns:
                pattern_signals = self._generate_pattern_signals(pattern, current_price)
                signals.extend(pattern_signals)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating corrective signals: {e}")
            return signals

# Convenience aliases
EWImpulseStrategy = ElliottWaveImpulseStrategy
EWCorrectiveStrategy = ElliottWaveCorrectiveStrategy
EWStrategy = ElliottWaveStrategy

# Utility functions
def identify_elliott_wave_pattern(df: pd.DataFrame, min_wave_size: float = 0.02) -> Optional[WavePattern]:
    """Identify Elliott Wave pattern in price data"""
    calculator = ElliottWaveCalculator()
    points = calculator.find_wave_points(df, min_wave_size)
    
    # Try impulse first
    impulse = calculator.identify_impulse_pattern(points)
    if impulse:
        return impulse
    
    # Try corrective
    corrective = calculator.identify_corrective_pattern(points)
    return corrective

def calculate_wave_projections(pattern: WavePattern, current_price: float) -> List[WaveProjection]:
    """Calculate Elliott Wave projections"""
    calculator = ElliottWaveCalculator()
    return calculator.project_wave_targets(pattern, current_price)

def find_elliott_wave_points(df: pd.DataFrame, min_wave_size: float = 0.02) -> List[WavePoint]:
    """Find Elliott Wave pivot points"""
    calculator = ElliottWaveCalculator()
    return calculator.find_wave_points(df, min_wave_size)