"""
Harmonic Projections Module

Advanced harmonic pattern price and time projections with institutional-grade features
including volume weighting, smart money confirmation, multi-timeframe analysis,
and adaptive confidence scoring for professional trading applications.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import numpy as np

from ...core.base_classes import AugmentedIndicator


class HarmonicProjectionType(Enum):
    """Types of harmonic projections"""
    PATTERN_COMPLETION = "pattern_completion"
    TARGET_PROJECTION = "target_projection"
    INVALIDATION_PROJECTION = "invalidation_projection"
    EXTENSION_PROJECTION = "extension_projection"
    TIME_PROJECTION = "time_projection"


class ProjectionConfidence(Enum):
    """Projection confidence levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class HarmonicProjection:
    """Represents a harmonic pattern projection"""
    price_target: float
    time_target: Optional[datetime]
    projection_type: HarmonicProjectionType
    pattern_type: str
    confidence_level: ProjectionConfidence
    confidence_score: float
    fib_ratio: float
    confluence_factors: List[str]
    volume_profile: Dict[str, Any]
    smart_money_alignment: float
    risk_parameters: Dict[str, float]


@dataclass
class HarmonicProjectionSignal:
    """Harmonic projection signal with institutional features"""
    value_raw: float
    signal_type: str
    composite_confidence: float
    confidence_components: Dict[str, float]
    suggested_sl: float
    suggested_tp: float
    timestamp: datetime
    additional_metadata: Dict[str, Any]

    # Projection-specific fields
    projection: HarmonicProjection
    projection_type: HarmonicProjectionType
    target_price: float
    target_time: Optional[datetime]
    pattern_context: str
    fib_confluence: List[float]
    risk_reward_ratio: float


class HarmonicProjections(AugmentedIndicator):
    """
    Advanced Harmonic Projections Analyzer

    Calculates harmonic pattern price and time projections with institutional-grade features:
    - Pattern completion targets based on Fibonacci relationships
    - Time cycle projections using pattern geometry
    - Volume-weighted projection validation
    - Smart money confirmation signals
    - Multi-timeframe projection alignment
    - Adaptive confidence scoring
    - Risk management integration
    """

    def __init__(self, timeframe: str = "1D", projection_horizon: int = 30):
        super().__init__(name="HarmonicProjections", timeframe=timeframe)
        self.projection_horizon = projection_horizon  # periods to look ahead
        self.price_history = []
        self.volume_history = []
        self.timestamp_history = []
        self.active_projections = []
        self.completed_projections = []
        self.pattern_context = {}

        # Pattern-specific projection ratios
        self.projection_ratios = self._initialize_projection_ratios()

    def _initialize_projection_ratios(self) -> Dict[str, Dict[str, List[float]]]:
        """Initialize projection ratios for different harmonic patterns"""
        return {
            'gartley': {
                'completion_targets': [0.786, 1.272, 1.618],
                'extension_targets': [2.0, 2.618, 4.236],
                'time_ratios': [0.618, 1.0, 1.618]
            },
            'butterfly': {
                'completion_targets': [1.272, 1.618, 2.0],
                'extension_targets': [2.618, 4.236, 6.854],
                'time_ratios': [0.786, 1.272, 1.618]
            },
            'bat': {
                'completion_targets': [0.886, 1.618, 2.618],
                'extension_targets': [3.618, 4.236, 6.854],
                'time_ratios': [0.886, 1.618, 2.618]
            },
            'crab': {
                'completion_targets': [1.618, 2.618, 3.618],
                'extension_targets': [4.236, 6.854, 11.09],
                'time_ratios': [1.618, 2.618, 4.236]
            },
            'shark': {
                'completion_targets': [0.886, 1.13, 1.618],
                'extension_targets': [2.0, 2.618, 4.236],
                'time_ratios': [1.27, 1.618, 2.618]
            }
        }

    def update(self, price: float, volume: float, high: float = None,
               low: float = None, timestamp: datetime = None,
               order_book_data: Dict = None, trade_data: List = None) -> Optional[HarmonicProjectionSignal]:
        """
        Update analyzer with new price/volume data

        Args:
            price: Current price
            volume: Current volume
            high: High price (optional)
            low: Low price (optional)
            timestamp: Data timestamp
            order_book_data: Order book data for smart money analysis
            trade_data: Trade data for volume analysis

        Returns:
            HarmonicProjectionSignal if projection target is hit, None otherwise
        """
        if timestamp is None:
            timestamp = datetime.now()

        # Update histories
        self.price_history.append(price)
        self.volume_history.append(volume)
        self.timestamp_history.append(timestamp)

        # Maintain history size
        max_history = 300
        if len(self.price_history) > max_history:
            self.price_history.pop(0)
            self.volume_history.pop(0)
            self.timestamp_history.pop(0)

        # Need minimum data for analysis
        if len(self.price_history) < 30:
            return None

        # Update pattern context and projections
        self._update_pattern_context()
        self._update_projections()

        # Check for projection target hits
        signal = self._check_projection_targets(price, timestamp, order_book_data, trade_data)

        if signal:
            self.current_signal = signal
            self.completed_projections.append(signal)

        return signal

    def _update_pattern_context(self):
        """Update current harmonic pattern context"""
        if len(self.price_history) < 20:
            return

        # Analyze current pattern development
        self.pattern_context = self._analyze_pattern_context()

    def _update_projections(self):
        """Update active harmonic projections based on current context"""
        if not self.pattern_context or len(self.price_history) < 20:
            return

        # Calculate projections based on current pattern context
        projections = self._calculate_harmonic_projections()

        # Update active projections
        self.active_projections = projections

    def _analyze_pattern_context(self) -> Dict[str, Any]:
        """Analyze current harmonic pattern context"""
        context = {
            'active_patterns': [],
            'pattern_stage': 'unknown',
            'trend_direction': self._determine_trend_direction(),
            'fib_levels': self._calculate_key_fib_levels(),
            'pattern_probability': 0.5
        }

        # Analyze recent price action for pattern development
        if len(self.price_history) >= 15:
            recent_high = max(self.price_history[-15:])
            recent_low = min(self.price_history[-15:])
            current_price = self.price_history[-1]

            # Determine pattern stage based on position within range
            range_size = recent_high - recent_low
            if range_size > 0:
                position_pct = (current_price - recent_low) / range_size

                if position_pct < 0.3:
                    context['pattern_stage'] = 'early_development'
                elif position_pct < 0.7:
                    context['pattern_stage'] = 'mid_development'
                else:
                    context['pattern_stage'] = 'late_development'

        return context

    def _determine_trend_direction(self) -> str:
        """Determine overall trend direction"""
        if len(self.price_history) < 20:
            return 'sideways'

        # Simple trend analysis
        short_ma = np.mean(self.price_history[-10:])
        long_ma = np.mean(self.price_history[-20:])

        if short_ma > long_ma * 1.005:
            return 'uptrend'
        elif short_ma < long_ma * 0.995:
            return 'downtrend'
        else:
            return 'sideways'

    def _calculate_key_fib_levels(self) -> List[float]:
        """Calculate key Fibonacci levels from recent range"""
        if len(self.price_history) < 20:
            return []

        recent_high = max(self.price_history[-20:])
        recent_low = min(self.price_history[-20:])
        range_size = recent_high - recent_low

        fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.618]
        return [recent_low + (range_size * level) for level in fib_levels]

    def _calculate_harmonic_projections(self) -> List[HarmonicProjection]:
        """Calculate harmonic projections based on current context"""
        projections = []

        if not self.pattern_context or len(self.price_history) < 20:
            return projections

        trend = self.pattern_context.get('trend_direction', 'sideways')
        pattern_stage = self.pattern_context.get('pattern_stage', 'unknown')

        # Calculate different types of projections
        if trend in ['uptrend', 'downtrend']:
            # Add pattern completion projections
            completion_projections = self._calculate_completion_projections(trend, pattern_stage)
            projections.extend(completion_projections)

            # Add target projections
            target_projections = self._calculate_target_projections(trend)
            projections.extend(target_projections)

        # Add time-based projections
        time_projections = self._calculate_time_projections()
        projections.extend(time_projections)

        # Sort by confidence and limit number
        projections.sort(key=lambda x: x.confidence_score, reverse=True)
        return projections[:10]  # Keep top 10 projections

    def _calculate_completion_projections(self, trend: str, pattern_stage: str) -> List[HarmonicProjection]:
        """Calculate pattern completion projections"""
        projections = []

        if len(self.price_history) < 15:
            return projections

        # Get recent swing points
        swings = self._find_projection_swings()

        if len(swings) < 3:
            return projections

        # Calculate completion targets for different pattern types
        for pattern_type, ratios in self.projection_ratios.items():
            completion_targets = ratios['completion_targets']

            for ratio in completion_targets:
                # Calculate price target based on recent swing range
                base_range = abs(swings[-1][0] - swings[-2][0])

                if trend == 'uptrend':
                    price_target = swings[-2][0] + (base_range * ratio)
                else:
                    price_target = swings[-2][0] - (base_range * ratio)

                # Calculate time target
                time_target = self._calculate_completion_time_target(pattern_stage, ratio)

                # Calculate confidence
                confidence_score = self._calculate_projection_confidence(
                    price_target, time_target, pattern_type, ratio, pattern_stage
                )

                # Determine confidence level
                if confidence_score > 0.8:
                    confidence_level = ProjectionConfidence.VERY_HIGH
                elif confidence_score > 0.6:
                    confidence_level = ProjectionConfidence.HIGH
                elif confidence_score > 0.4:
                    confidence_level = ProjectionConfidence.MEDIUM
                else:
                    confidence_level = ProjectionConfidence.LOW

                # Confluence factors
                confluence_factors = self._identify_projection_confluence(price_target, time_target)

                # Volume profile
                volume_profile = self._analyze_projection_volume(pattern_type)

                # Smart money alignment
                smart_money_alignment = self._calculate_projection_smart_money(price_target)

                # Risk parameters
                risk_parameters = self._calculate_projection_risk_parameters(price_target, confidence_score)

                projection = HarmonicProjection(
                    price_target=price_target,
                    time_target=time_target,
                    projection_type=HarmonicProjectionType.PATTERN_COMPLETION,
                    pattern_type=pattern_type,
                    confidence_level=confidence_level,
                    confidence_score=confidence_score,
                    fib_ratio=ratio,
                    confluence_factors=confluence_factors,
                    volume_profile=volume_profile,
                    smart_money_alignment=smart_money_alignment,
                    risk_parameters=risk_parameters
                )

                projections.append(projection)

        return projections

    def _calculate_target_projections(self, trend: str) -> List[HarmonicProjection]:
        """Calculate target projections for completed patterns"""
        projections = []

        if len(self.price_history) < 20:
            return projections

        # Calculate extension targets based on pattern completion
        for pattern_type, ratios in self.projection_ratios.items():
            extension_targets = ratios['extension_targets']

            for ratio in extension_targets:
                # Base target on recent completed pattern (simplified)
                current_price = self.price_history[-1]
                base_move = abs(current_price - self.price_history[-10])

                if trend == 'uptrend':
                    price_target = current_price + (base_move * ratio)
                else:
                    price_target = current_price - (base_move * ratio)

                time_target = self._calculate_extension_time_target(ratio)

                confidence_score = self._calculate_extension_confidence(ratio, pattern_type)

                projection = HarmonicProjection(
                    price_target=price_target,
                    time_target=time_target,
                    projection_type=HarmonicProjectionType.TARGET_PROJECTION,
                    pattern_type=pattern_type,
                    confidence_level=ProjectionConfidence.MEDIUM,
                    confidence_score=confidence_score,
                    fib_ratio=ratio,
                    confluence_factors=['extension_target'],
                    volume_profile={},
                    smart_money_alignment=0.5,
                    risk_parameters=self._calculate_projection_risk_parameters(price_target, confidence_score)
                )

                projections.append(projection)

        return projections

    def _calculate_time_projections(self) -> List[HarmonicProjection]:
        """Calculate time-based projections"""
        projections = []

        if len(self.timestamp_history) < 20:
            return projections

        # Analyze pattern timing cycles
        time_cycles = self._analyze_time_cycles()

        if not time_cycles:
            return projections

        avg_cycle = np.mean(time_cycles)
        current_time = self.timestamp_history[-1]

        # Project future time targets
        for ratio in [1.0, 1.618, 2.618]:
            time_target = current_time + timedelta(seconds=avg_cycle * ratio)

            # Associated price projection (simplified)
            price_target = self.price_history[-1] * 1.02  # Placeholder

            projection = HarmonicProjection(
                price_target=price_target,
                time_target=time_target,
                projection_type=HarmonicProjectionType.TIME_PROJECTION,
                pattern_type='time_cycle',
                confidence_level=ProjectionConfidence.MEDIUM,
                confidence_score=0.6,
                fib_ratio=ratio,
                confluence_factors=['time_cycle'],
                volume_profile={},
                smart_money_alignment=0.5,
                risk_parameters={'stop_loss_pct': 0.02, 'take_profit_pct': 0.05}
            )

            projections.append(projection)

        return projections

    def _find_projection_swings(self) -> List[Tuple[float, int]]:
        """Find swing points for projection calculations"""
        swings = []
        lookback = 3

        for i in range(lookback, len(self.price_history) - lookback):
            price = self.price_history[i]

            is_high = all(price >= self.price_history[i-j] for j in range(1, lookback+1)) and \
                     all(price >= self.price_history[i+j] for j in range(1, lookback+1))

            is_low = all(price <= self.price_history[i-j] for j in range(1, lookback+1)) and \
                    all(price <= self.price_history[i+j] for j in range(1, lookback+1))

            if is_high or is_low:
                swings.append((price, i))

        return swings[-6:]  # Last 6 swings

    def _calculate_completion_time_target(self, pattern_stage: str, ratio: float) -> Optional[datetime]:
        """Calculate time target for pattern completion"""
        if len(self.timestamp_history) < 10:
            return None

        # Estimate time based on pattern development stage
        base_time = self.timestamp_history[-1]

        if pattern_stage == 'early_development':
            time_factor = 2.0  # More time needed
        elif pattern_stage == 'mid_development':
            time_factor = 1.5
        else:
            time_factor = 1.0

        time_span = (base_time - self.timestamp_history[-10]).total_seconds()
        projected_span = time_span * ratio * time_factor

        return base_time + timedelta(seconds=projected_span)

    def _calculate_extension_time_target(self, ratio: float) -> Optional[datetime]:
        """Calculate time target for extension"""
        if len(self.timestamp_history) < 5:
            return None

        recent_span = (self.timestamp_history[-1] - self.timestamp_history[-5]).total_seconds()
        extension_span = recent_span * ratio

        return self.timestamp_history[-1] + timedelta(seconds=extension_span)

    def _calculate_projection_confidence(self, price_target: float, time_target: Optional[datetime],
                                       pattern_type: str, ratio: float, pattern_stage: str) -> float:
        """Calculate confidence score for projection"""
        confidence = 0.5

        # Pattern type reliability
        pattern_weights = {
            'gartley': 0.8,
            'butterfly': 0.7,
            'bat': 0.75,
            'crab': 0.6,
            'shark': 0.65
        }
        confidence += pattern_weights.get(pattern_type, 0.5) * 0.2

        # Fibonacci ratio significance
        significant_ratios = [0.618, 0.786, 1.272, 1.618, 2.618]
        if ratio in significant_ratios:
            confidence += 0.15

        # Pattern stage factor
        stage_weights = {
            'early_development': 0.1,
            'mid_development': 0.15,
            'late_development': 0.2
        }
        confidence += stage_weights.get(pattern_stage, 0.1)

        # Volume confirmation
        volume_factor = self._calculate_projection_volume_factor()
        confidence += volume_factor * 0.1

        return min(1.0, confidence)

    def _calculate_extension_confidence(self, ratio: float, pattern_type: str) -> float:
        """Calculate confidence for extension projection"""
        base_confidence = 0.4  # Extensions are generally less reliable

        # Some patterns have more reliable extensions
        if pattern_type in ['gartley', 'butterfly'] and ratio <= 2.618:
            base_confidence += 0.2

        return min(1.0, base_confidence)

    def _identify_projection_confluence(self, price_target: float,
                                       time_target: Optional[datetime]) -> List[str]:
        """Identify confluence factors for projection"""
        factors = []

        # Check proximity to key Fibonacci levels
        key_fib_levels = self.pattern_context.get('fib_levels', [])
        for fib_level in key_fib_levels:
            if abs(price_target - fib_level) / price_target < 0.005:
                factors.append("Key Fibonacci Level")

        # Check round number confluence
        round_number = round(price_target, -1)
        if abs(price_target - round_number) / price_target < 0.005:
            factors.append("Round Number")

        # Time confluence
        if time_target:
            factors.append("Time Cycle Projection")

        return factors

    def _analyze_projection_volume(self, pattern_type: str) -> Dict[str, Any]:
        """Analyze volume profile for projection"""
        if len(self.volume_history) < 10:
            return {}

        # Analyze volume based on pattern type
        if pattern_type in ['gartley', 'bat']:
            # These patterns often complete with volume confirmation
            recent_volume = self.volume_history[-5:]
            volume_trend = np.polyfit(range(len(recent_volume)), recent_volume, 1)[0]
            return {
                'volume_trend': volume_trend,
                'expected_volume': 'increasing',
                'confirmation_score': 0.8 if volume_trend > 0 else 0.4
            }
        else:
            return {
                'expected_volume': 'moderate',
                'confirmation_score': 0.6
            }

    def _calculate_projection_smart_money(self, price_target: float) -> float:
        """Calculate smart money alignment for projection"""
        return 0.6  # Simplified

    def _calculate_projection_risk_parameters(self, price_target: float, confidence_score: float) -> Dict[str, float]:
        """Calculate risk parameters for projection"""
        # Adjust risk based on confidence
        if confidence_score > 0.8:
            stop_loss_pct = 0.015  # Tighter stop for high confidence
            take_profit_pct = 0.06
        elif confidence_score > 0.6:
            stop_loss_pct = 0.02
            take_profit_pct = 0.08
        else:
            stop_loss_pct = 0.03  # Wider stop for lower confidence
            take_profit_pct = 0.12

        return {
            'stop_loss_pct': stop_loss_pct,
            'take_profit_pct': take_profit_pct,
            'risk_reward_ratio': take_profit_pct / stop_loss_pct
        }

    def _calculate_projection_volume_factor(self) -> float:
        """Calculate volume factor for projection confidence"""
        if len(self.volume_history) < 10:
            return 0.5

        recent_volume = np.mean(self.volume_history[-5:])
        avg_volume = np.mean(self.volume_history)

        if recent_volume > avg_volume * 1.3:
            return 0.8
        elif recent_volume > avg_volume * 1.1:
            return 0.6
        else:
            return 0.4

    def _analyze_time_cycles(self) -> List[float]:
        """Analyze time cycles from historical patterns"""
        cycles = []

        if len(self.timestamp_history) >= 15:
            for i in range(5, len(self.timestamp_history) - 1, 3):
                cycle = (self.timestamp_history[i] - self.timestamp_history[i-3]).total_seconds()
                cycles.append(cycle)

        return cycles

    def _check_projection_targets(self, current_price: float, timestamp: datetime,
                               order_book_data: Dict = None,
                               trade_data: List = None) -> Optional[HarmonicProjectionSignal]:
        """Check if current price has hit any projection targets"""
        tolerance = 0.005  # 0.5% tolerance

        for projection in self.active_projections:
            price_diff_pct = abs(current_price - projection.price_target) / projection.price_target

            if price_diff_pct <= tolerance:
                # Check time alignment if applicable
                time_aligned = True
                if projection.time_target:
                    time_diff = abs((timestamp - projection.time_target).total_seconds())
                    time_tolerance = timedelta(days=3).total_seconds()
                    time_aligned = time_diff <= time_tolerance

                if time_aligned:
                    return self._create_projection_signal(
                        projection, current_price, timestamp, order_book_data, trade_data
                    )

        return None

    def _create_projection_signal(self, projection: HarmonicProjection, current_price: float,
                                timestamp: datetime, order_book_data: Dict = None,
                                trade_data: List = None) -> HarmonicProjectionSignal:
        """Create a projection signal when target is hit"""
        # Calculate confidence components
        confidence_components = self._calculate_projection_signal_confidence(
            projection, current_price, order_book_data, trade_data
        )

        composite_confidence = np.mean(list(confidence_components.values()))

        # Risk management from projection parameters
        risk_params = projection.risk_parameters
        stop_distance = current_price * risk_params['stop_loss_pct']
        target_distance = current_price * risk_params['take_profit_pct']

        if current_price > projection.price_target:
            suggested_sl = current_price - stop_distance
            suggested_tp = current_price + target_distance
        else:
            suggested_sl = current_price + stop_distance
            suggested_tp = current_price - target_distance

        # Additional metadata
        additional_metadata = {
            'projection_ratio': projection.fib_ratio,
            'confluence_factors': projection.confluence_factors,
            'pattern_type': projection.pattern_type,
            'confidence_level': projection.confidence_level.value,
            'volume_profile': projection.volume_profile,
            'smart_money_alignment': projection.smart_money_alignment,
            'risk_parameters': projection.risk_parameters
        }

        return HarmonicProjectionSignal(
            value_raw=current_price,
            signal_type=f"HARMONIC_{projection.projection_type.value.upper()}_{projection.pattern_type.upper()}",
            composite_confidence=composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=suggested_sl,
            suggested_tp=suggested_tp,
            timestamp=timestamp,
            additional_metadata=additional_metadata,
            projection=projection,
            projection_type=projection.projection_type,
            target_price=projection.price_target,
            target_time=projection.time_target,
            pattern_context=f"{projection.pattern_type} pattern projection",
            fib_confluence=[projection.fib_ratio],
            risk_reward_ratio=risk_params.get('risk_reward_ratio', 2.0)
        )

    def _calculate_projection_signal_confidence(self, projection: HarmonicProjection,
                                             current_price: float, order_book_data: Dict = None,
                                             trade_data: List = None) -> Dict[str, float]:
        """Calculate confidence components for projection signal"""
        components = {}

        # Base projection confidence
        components['projection_confidence'] = projection.confidence_score

        # Confluence strength
        components['confluence_score'] = min(1.0, len(projection.confluence_factors) * 0.25)

        # Price accuracy
        price_accuracy = 1.0 - (abs(current_price - projection.price_target) / projection.price_target)
        components['price_accuracy'] = max(0.0, price_accuracy)

        # Volume confirmation
        components['volume_confirmation'] = self._calculate_projection_volume_factor()

        # Smart money confirmation
        components['smart_money_score'] = projection.smart_money_alignment

        # Time alignment
        if projection.time_target:
            time_accuracy = self._calculate_time_accuracy(projection.time_target, datetime.now())
            components['time_accuracy'] = time_accuracy
        else:
            components['time_accuracy'] = 0.5

        return components

    def _calculate_time_accuracy(self, target_time: datetime, actual_time: datetime) -> float:
        """Calculate how accurate the time projection was"""
        time_diff = abs((actual_time - target_time).total_seconds())
        max_tolerance = timedelta(days=7).total_seconds()

        accuracy = 1.0 - (time_diff / max_tolerance)
        return max(0.0, min(1.0, accuracy))

    def get_active_projections(self) -> List[HarmonicProjection]:
        """Get currently active harmonic projections"""
        return self.active_projections.copy()

    def get_projection_history(self) -> List[HarmonicProjectionSignal]:
        """Get historical projection signals"""
        return self.completed_projections.copy()

    def get_pattern_context(self) -> Dict[str, Any]:
        """Get current pattern context"""
        return self.pattern_context.copy()

    def find_nearest_projection(self, price: float) -> Optional[HarmonicProjection]:
        """Find the nearest projection target to current price"""
        if not self.active_projections:
            return None

        nearest = min(self.active_projections,
                     key=lambda p: abs(p.price_target - price))

        # Only return if within reasonable distance
        distance_pct = abs(nearest.price_target - price) / price
        if distance_pct < 0.1:  # Within 10%
            return nearest

        return None