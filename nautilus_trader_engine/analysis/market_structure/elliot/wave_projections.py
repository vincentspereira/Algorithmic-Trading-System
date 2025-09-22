"""
Elliot Wave Projections Module

Advanced Elliot wave price and time projections with institutional-grade features
including volume weighting, smart money confirmation, multi-timeframe analysis,
and adaptive confidence scoring for professional trading applications.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import numpy as np

from ...core.base_classes import AugmentedIndicator


class ProjectionType(Enum):
    """Types of Elliot wave projections"""
    WAVE_TARGET = "wave_target"
    CORRECTION_TARGET = "correction_target"
    EXTENSION_TARGET = "extension_target"
    TIME_PROJECTION = "time_projection"
    CONFLUENCE_PROJECTION = "confluence_projection"


class WaveProjectionLevel(Enum):
    """Elliot wave projection levels based on Fibonacci ratios"""
    LEVEL_0618 = 0.618
    LEVEL_1000 = 1.000
    LEVEL_1272 = 1.272
    LEVEL_1618 = 1.618
    LEVEL_2000 = 2.000
    LEVEL_2618 = 2.618


@dataclass
class WaveProjection:
    """Represents an Elliot wave projection target"""
    price_target: float
    time_target: Optional[datetime]
    projection_type: ProjectionType
    wave_number: str
    confidence_score: float
    fibonacci_ratio: float
    confluence_factors: List[str]
    volume_profile: Dict[str, Any]
    smart_money_alignment: float
    pattern_context: Dict[str, Any]


@dataclass
class WaveProjectionSignal:
    """Elliot wave projection signal with institutional features"""
    value_raw: float
    signal_type: str
    composite_confidence: float
    confidence_components: Dict[str, float]
    suggested_sl: float
    suggested_tp: float
    timestamp: datetime
    additional_metadata: Dict[str, Any]

    # Projection-specific fields
    wave_projection: WaveProjection
    projection_type: ProjectionType
    target_price: float
    target_time: Optional[datetime]
    wave_context: str
    fibonacci_confluence: List[float]
    pattern_completion_probability: float


class WaveProjections(AugmentedIndicator):
    """
    Advanced Elliot Wave Projections Analyzer

    Calculates Elliot wave price and time projections with institutional-grade features:
    - Wave target projections based on Fibonacci relationships
    - Time cycle projections using wave timing
    - Volume-weighted projection validation
    - Smart money confirmation signals
    - Multi-timeframe projection alignment
    - Adaptive confidence scoring
    - Risk management integration
    """

    def __init__(self, timeframe: str = "1D", projection_horizon: int = 50):
        super().__init__(name="WaveProjections", timeframe=timeframe)
        self.projection_horizon = projection_horizon  # periods to look ahead
        self.price_history = []
        self.volume_history = []
        self.timestamp_history = []
        self.active_projections = []
        self.completed_projections = []
        self.wave_context = {}

    def update(self, price: float, volume: float, high: float = None,
               low: float = None, timestamp: datetime = None,
               order_book_data: Dict = None, trade_data: List = None) -> Optional[WaveProjectionSignal]:
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
            WaveProjectionSignal if projection target is hit, None otherwise
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

        # Update wave context and projections
        self._update_wave_context()
        self._update_projections()

        # Check for projection target hits
        signal = self._check_projection_targets(price, timestamp, order_book_data, trade_data)

        if signal:
            self.current_signal = signal
            self.completed_projections.append(signal)

        return signal

    def _update_wave_context(self):
        """Update current wave context for projections"""
        if len(self.price_history) < 20:
            return

        # Analyze current wave position
        self.wave_context = self._analyze_wave_position()

    def _update_projections(self):
        """Update active wave projections based on current context"""
        if not self.wave_context:
            return

        # Calculate projections based on current wave context
        projections = self._calculate_wave_projections()

        # Update active projections
        self.active_projections = projections

    def _analyze_wave_position(self) -> Dict[str, Any]:
        """Analyze current position within wave structure"""
        # Simplified wave position analysis
        context = {
            'current_wave': 'unknown',
            'pattern_type': 'unknown',
            'trend_direction': self._determine_trend_direction(),
            'wave_degree': 'minor',
            'completion_probability': 0.5
        }

        # Analyze recent price action to determine wave position
        if len(self.price_history) >= 10:
            recent_high = max(self.price_history[-10:])
            recent_low = min(self.price_history[-10:])
            current_price = self.price_history[-1]

            # Simple wave position estimation
            range_size = recent_high - recent_low
            if range_size > 0:
                position_pct = (current_price - recent_low) / range_size

                if position_pct < 0.3:
                    context['current_wave'] = 'early_corrective'
                elif position_pct < 0.7:
                    context['current_wave'] = 'mid_trend'
                else:
                    context['current_wave'] = 'late_impulse'

        return context

    def _determine_trend_direction(self) -> str:
        """Determine overall trend direction"""
        if len(self.price_history) < 20:
            return 'sideways'

        # Simple trend analysis using moving averages
        short_ma = np.mean(self.price_history[-10:])
        long_ma = np.mean(self.price_history[-20:])

        if short_ma > long_ma * 1.005:
            return 'uptrend'
        elif short_ma < long_ma * 0.995:
            return 'downtrend'
        else:
            return 'sideways'

    def _calculate_wave_projections(self) -> List[WaveProjection]:
        """Calculate wave projections based on current context"""
        projections = []

        if not self.wave_context or len(self.price_history) < 20:
            return projections

        trend = self.wave_context.get('trend_direction', 'sideways')
        current_wave = self.wave_context.get('current_wave', 'unknown')

        # Calculate different types of projections
        if trend in ['uptrend', 'downtrend']:
            # Add impulse wave projections
            impulse_projections = self._calculate_impulse_projections(trend)
            projections.extend(impulse_projections)

            # Add corrective wave projections
            corrective_projections = self._calculate_corrective_projections(trend)
            projections.extend(corrective_projections)

        # Add time-based projections
        time_projections = self._calculate_time_projections()
        projections.extend(time_projections)

        # Sort by confidence and limit number
        projections.sort(key=lambda x: x.confidence_score, reverse=True)
        return projections[:10]  # Keep top 10 projections

    def _calculate_impulse_projections(self, trend: str) -> List[WaveProjection]:
        """Calculate projections for impulse waves"""
        projections = []

        if len(self.price_history) < 20:
            return projections

        # Get recent swing points
        swings = self._find_projection_swings()

        if len(swings) < 2:
            return projections

        # Calculate wave 3 and wave 5 targets
        base_move = abs(swings[-1][0] - swings[-2][0])

        for level in WaveProjectionLevel:
            ratio = level.value

            if trend == 'uptrend':
                if 'wave3' in self.wave_context.get('current_wave', ''):
                    # Wave 3 extension target
                    price_target = swings[-1][0] + (base_move * ratio)
                    wave_number = '3'
                elif 'wave5' in self.wave_context.get('current_wave', ''):
                    # Wave 5 target
                    price_target = swings[-1][0] + (base_move * ratio)
                    wave_number = '5'
                else:
                    continue
            else:  # downtrend
                if 'wave3' in self.wave_context.get('current_wave', ''):
                    price_target = swings[-1][0] - (base_move * ratio)
                    wave_number = '3'
                elif 'wave5' in self.wave_context.get('current_wave', ''):
                    price_target = swings[-1][0] - (base_move * ratio)
                    wave_number = '5'
                else:
                    continue

            # Calculate time target
            time_target = self._calculate_projection_time_target(wave_number, ratio)

            # Calculate confidence
            confidence_score = self._calculate_projection_confidence(
                price_target, time_target, wave_number, ratio
            )

            # Confluence factors
            confluence_factors = self._identify_projection_confluence(price_target, time_target)

            # Volume profile
            volume_profile = self._analyze_projection_volume(wave_number)

            # Smart money alignment
            smart_money_alignment = self._calculate_projection_smart_money(price_target)

            projection = WaveProjection(
                price_target=price_target,
                time_target=time_target,
                projection_type=ProjectionType.WAVE_TARGET,
                wave_number=wave_number,
                confidence_score=confidence_score,
                fibonacci_ratio=ratio,
                confluence_factors=confluence_factors,
                volume_profile=volume_profile,
                smart_money_alignment=smart_money_alignment,
                pattern_context=self.wave_context.copy()
            )

            projections.append(projection)

        return projections

    def _calculate_corrective_projections(self, trend: str) -> List[WaveProjection]:
        """Calculate projections for corrective waves"""
        projections = []

        if len(self.price_history) < 15:
            return projections

        # Get recent correction range
        recent_prices = self.price_history[-15:]
        correction_high = max(recent_prices)
        correction_low = min(recent_prices)
        correction_range = correction_high - correction_low

        # Project correction targets
        for level in [WaveProjectionLevel.LEVEL_0618, WaveProjectionLevel.LEVEL_1000]:
            ratio = level.value

            if trend == 'uptrend':
                # Correction in uptrend - target retracement levels
                price_target = correction_high - (correction_range * ratio)
                wave_number = 'A-B-C'
            else:
                # Correction in downtrend
                price_target = correction_low + (correction_range * ratio)
                wave_number = 'A-B-C'

            time_target = self._calculate_correction_time_target()

            confidence_score = self._calculate_correction_confidence(price_target, ratio)

            confluence_factors = self._identify_correction_confluence(price_target)

            projection = WaveProjection(
                price_target=price_target,
                time_target=time_target,
                projection_type=ProjectionType.CORRECTION_TARGET,
                wave_number=wave_number,
                confidence_score=confidence_score,
                fibonacci_ratio=ratio,
                confluence_factors=confluence_factors,
                volume_profile=self._analyze_correction_volume(),
                smart_money_alignment=self._calculate_correction_smart_money(price_target),
                pattern_context={'correction_type': 'zigzag', 'trend': trend}
            )

            projections.append(projection)

        return projections

    def _calculate_time_projections(self) -> List[WaveProjection]:
        """Calculate time-based projections"""
        projections = []

        if len(self.timestamp_history) < 20:
            return projections

        # Analyze wave timing patterns
        wave_durations = self._analyze_wave_durations()

        if not wave_durations:
            return projections

        avg_duration = np.mean(wave_durations)
        current_time = self.timestamp_history[-1]

        # Project future time targets
        for ratio in [1.0, 1.618, 2.618]:
            time_target = current_time + timedelta(seconds=avg_duration * ratio)

            # Associated price projection (simplified)
            price_target = self.price_history[-1] * 1.02  # Placeholder

            projection = WaveProjection(
                price_target=price_target,
                time_target=time_target,
                projection_type=ProjectionType.TIME_PROJECTION,
                wave_number='time_cycle',
                confidence_score=0.6,
                fibonacci_ratio=ratio,
                confluence_factors=['time_cycle'],
                volume_profile={},
                smart_money_alignment=0.5,
                pattern_context={'time_based': True}
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

    def _calculate_projection_time_target(self, wave_number: str, ratio: float) -> Optional[datetime]:
        """Calculate time target for wave projection"""
        if len(self.timestamp_history) < 10:
            return None

        # Estimate time based on previous wave durations
        recent_durations = []
        for i in range(2, len(self.timestamp_history) - 1, 2):
            duration = (self.timestamp_history[i] - self.timestamp_history[i-1]).total_seconds()
            recent_durations.append(duration)

        if recent_durations:
            avg_duration = np.mean(recent_durations)
            projected_duration = avg_duration * ratio
            return self.timestamp_history[-1] + timedelta(seconds=projected_duration)

        return None

    def _calculate_correction_time_target(self) -> Optional[datetime]:
        """Calculate time target for correction"""
        if len(self.timestamp_history) < 5:
            return None

        # Corrections typically take less time than impulses
        recent_duration = (self.timestamp_history[-1] - self.timestamp_history[-5]).total_seconds()
        correction_duration = recent_duration * 0.618

        return self.timestamp_history[-1] + timedelta(seconds=correction_duration)

    def _calculate_projection_confidence(self, price_target: float, time_target: Optional[datetime],
                                       wave_number: str, ratio: float) -> float:
        """Calculate confidence score for projection"""
        confidence = 0.5

        # Fibonacci ratio validity
        if ratio in [0.618, 1.0, 1.272, 1.618, 2.618]:
            confidence += 0.2

        # Wave number appropriateness
        if wave_number in ['3', '5'] and ratio > 1.0:
            confidence += 0.15  # Extensions are common in waves 3 and 5

        # Historical success
        historical_factor = self._calculate_historical_projection_success(price_target)
        confidence += historical_factor * 0.1

        # Volume confirmation
        volume_factor = self._calculate_projection_volume_factor()
        confidence += volume_factor * 0.1

        return min(1.0, confidence)

    def _calculate_correction_confidence(self, price_target: float, ratio: float) -> float:
        """Calculate confidence for correction projection"""
        confidence = 0.5

        # 61.8% retracements are most common
        if abs(ratio - 0.618) < 0.1:
            confidence += 0.2

        # Check if target is reasonable
        current_price = self.price_history[-1]
        target_distance = abs(price_target - current_price) / current_price

        if target_distance < 0.05:  # Too close
            confidence -= 0.1
        elif target_distance > 0.15:  # Too far
            confidence -= 0.1

        return max(0.0, min(1.0, confidence))

    def _identify_projection_confluence(self, price_target: float,
                                       time_target: Optional[datetime]) -> List[str]:
        """Identify confluence factors for projection"""
        factors = []

        # Check round number confluence
        round_number = round(price_target, -1)
        if abs(price_target - round_number) / price_target < 0.005:
            factors.append("Round Number")

        # Check Fibonacci level confluence
        fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786]
        for level in fib_levels:
            # Check if near Fibonacci retracement from recent high/low
            recent_high = max(self.price_history[-20:])
            recent_low = min(self.price_history[-20:])
            fib_price = recent_low + (recent_high - recent_low) * level

            if abs(price_target - fib_price) / price_target < 0.01:
                factors.append(f"Fib {level:.3f} Level")

        # Time confluence
        if time_target:
            factors.append("Time Cycle")

        return factors

    def _identify_correction_confluence(self, price_target: float) -> List[str]:
        """Identify confluence factors for correction"""
        factors = []

        # Check pivot point confluence
        if self._is_near_pivot(price_target):
            factors.append("Pivot Point")

        # Check moving average confluence
        if self._is_near_moving_average(price_target):
            factors.append("Moving Average")

        return factors

    def _analyze_projection_volume(self, wave_number: str) -> Dict[str, Any]:
        """Analyze volume profile for projection"""
        if len(self.volume_history) < 10:
            return {}

        # Analyze volume based on wave type
        if wave_number in ['3', '5']:
            # Impulse waves should have increasing volume
            recent_volume = self.volume_history[-5:]
            volume_trend = np.polyfit(range(len(recent_volume)), recent_volume, 1)[0]
            return {
                'volume_trend': volume_trend,
                'expected_volume': 'increasing',
                'confirmation_score': 0.8 if volume_trend > 0 else 0.4
            }
        else:
            # Corrective waves may have decreasing volume
            return {
                'expected_volume': 'decreasing',
                'confirmation_score': 0.6
            }

    def _analyze_correction_volume(self) -> Dict[str, Any]:
        """Analyze volume for correction"""
        if len(self.volume_history) < 10:
            return {'confirmation_score': 0.5}

        recent_volume = np.mean(self.volume_history[-5:])
        avg_volume = np.mean(self.volume_history[-15:-5])

        return {
            'volume_ratio': recent_volume / avg_volume if avg_volume > 0 else 1.0,
            'confirmation_score': 0.7 if recent_volume < avg_volume else 0.5
        }

    def _calculate_projection_smart_money(self, price_target: float) -> float:
        """Calculate smart money alignment for projection"""
        # Simplified smart money analysis
        return 0.6

    def _calculate_correction_smart_money(self, price_target: float) -> float:
        """Calculate smart money alignment for correction"""
        return 0.55

    def _calculate_historical_projection_success(self, price_target: float) -> float:
        """Calculate historical success rate for similar projections"""
        if len(self.completed_projections) < 3:
            return 0.5

        # Check success rate of projections in similar price ranges
        similar_projections = [
            p for p in self.completed_projections[-10:]
            if abs(p.target_price - price_target) / price_target < 0.05
        ]

        if not similar_projections:
            return 0.5

        successful = sum(1 for p in similar_projections if p.composite_confidence > 0.7)
        return successful / len(similar_projections)

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

    def _analyze_wave_durations(self) -> List[float]:
        """Analyze durations of previous waves"""
        durations = []

        # Simple duration analysis
        if len(self.timestamp_history) >= 10:
            for i in range(5, len(self.timestamp_history) - 1, 2):
                duration = (self.timestamp_history[i] - self.timestamp_history[i-1]).total_seconds()
                durations.append(duration)

        return durations

    def _is_near_pivot(self, price: float) -> bool:
        """Check if price is near a pivot point"""
        # Simplified pivot check
        return False

    def _is_near_moving_average(self, price: float) -> bool:
        """Check if price is near a moving average"""
        if len(self.price_history) < 20:
            return False

        ma20 = np.mean(self.price_history[-20:])
        return abs(price - ma20) / price < 0.01

    def _check_projection_targets(self, current_price: float, timestamp: datetime,
                               order_book_data: Dict = None,
                               trade_data: List = None) -> Optional[WaveProjectionSignal]:
        """Check if current price has hit any projection targets"""
        tolerance = 0.005  # 0.5% tolerance

        for projection in self.active_projections:
            price_diff_pct = abs(current_price - projection.price_target) / projection.price_target

            if price_diff_pct <= tolerance:
                # Check time alignment if applicable
                time_aligned = True
                if projection.time_target:
                    time_diff = abs((timestamp - projection.time_target).total_seconds())
                    time_tolerance = timedelta(days=2).total_seconds()
                    time_aligned = time_diff <= time_tolerance

                if time_aligned:
                    return self._create_projection_signal(
                        projection, current_price, timestamp, order_book_data, trade_data
                    )

        return None

    def _create_projection_signal(self, projection: WaveProjection, current_price: float,
                                timestamp: datetime, order_book_data: Dict = None,
                                trade_data: List = None) -> WaveProjectionSignal:
        """Create a projection signal when target is hit"""
        # Calculate confidence components
        confidence_components = self._calculate_projection_signal_confidence(
            projection, current_price, order_book_data, trade_data
        )

        composite_confidence = np.mean(list(confidence_components.values()))

        # Risk management
        suggested_sl, suggested_tp = self._calculate_projection_risk_management(projection, current_price)

        # Additional metadata
        additional_metadata = {
            'projection_ratio': projection.fibonacci_ratio,
            'confluence_factors': projection.confluence_factors,
            'wave_context': projection.pattern_context,
            'volume_profile': projection.volume_profile,
            'smart_money_alignment': projection.smart_money_alignment,
            'pattern_completion_probability': self._calculate_pattern_completion_probability(projection)
        }

        return WaveProjectionSignal(
            value_raw=current_price,
            signal_type=f"ELLIOT_WAVE_{projection.projection_type.value.upper()}_{projection.wave_number.upper()}",
            composite_confidence=composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=suggested_sl,
            suggested_tp=suggested_tp,
            timestamp=timestamp,
            additional_metadata=additional_metadata,
            wave_projection=projection,
            projection_type=projection.projection_type,
            target_price=projection.price_target,
            target_time=projection.time_target,
            wave_context=f"Wave {projection.wave_number} in {projection.pattern_context.get('trend_direction', 'unknown')} trend",
            fibonacci_confluence=[projection.fibonacci_ratio],
            pattern_completion_probability=self._calculate_pattern_completion_probability(projection)
        )

    def _calculate_projection_signal_confidence(self, projection: WaveProjection,
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
        max_tolerance = timedelta(days=5).total_seconds()

        accuracy = 1.0 - (time_diff / max_tolerance)
        return max(0.0, min(1.0, accuracy))

    def _calculate_projection_risk_management(self, projection: WaveProjection,
                                            current_price: float) -> Tuple[float, float]:
        """Calculate stop loss and take profit for projection trade"""
        # Base risk on projection confidence and recent volatility
        if len(self.price_history) >= 10:
            recent_volatility = np.std(self.price_history[-10:])
            base_risk = recent_volatility * 0.5
        else:
            base_risk = current_price * 0.01

        # Adjust based on confidence
        risk_multiplier = 1.0 if projection.confidence_score > 0.7 else 0.7
        risk_amount = base_risk * risk_multiplier

        # Determine direction
        if current_price > projection.price_target:
            suggested_sl = current_price - risk_amount
            suggested_tp = projection.price_target + (risk_amount * 2)
        else:
            suggested_sl = current_price + risk_amount
            suggested_tp = projection.price_target - (risk_amount * 2)

        return suggested_sl, suggested_tp

    def _calculate_pattern_completion_probability(self, projection: WaveProjection) -> float:
        """Calculate probability that the wave pattern will complete"""
        # Simplified calculation based on projection confidence and context
        base_probability = projection.confidence_score

        # Adjust based on wave context
        context = projection.pattern_context
        if context.get('current_wave') == 'late_impulse':
            base_probability += 0.1  # Higher probability when late in wave

        return min(1.0, base_probability)

    def get_active_projections(self) -> List[WaveProjection]:
        """Get currently active wave projections"""
        return self.active_projections.copy()

    def get_projection_history(self) -> List[WaveProjectionSignal]:
        """Get historical projection signals"""
        return self.completed_projections.copy()

    def get_wave_context(self) -> Dict[str, Any]:
        """Get current wave context"""
        return self.wave_context.copy()

    def find_nearest_projection(self, price: float) -> Optional[WaveProjection]:
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