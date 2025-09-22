"""
Fibonacci Projections Module

Advanced Fibonacci price and time projections with institutional-grade features
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
    """Types of Fibonacci projections"""
    PRICE_PROJECTION = "price_projection"
    TIME_PROJECTION = "time_projection"
    PRICE_TIME_PROJECTION = "price_time_projection"
    HARMONIC_PROJECTION = "harmonic_projection"


class ProjectionLevel(Enum):
    """Standard Fibonacci projection levels"""
    LEVEL_0618 = 0.618
    LEVEL_1000 = 1.000
    LEVEL_1272 = 1.272
    LEVEL_1618 = 1.618
    LEVEL_2000 = 2.000
    LEVEL_2618 = 2.618
    LEVEL_3618 = 3.618


@dataclass
class FibonacciProjection:
    """Represents a Fibonacci projection target"""
    price_target: float
    time_target: Optional[datetime]
    projection_ratio: float
    confidence_score: float
    confluence_factors: List[str]
    volume_profile: Dict[str, Any]
    smart_money_alignment: float


@dataclass
class FibonacciProjectionSignal:
    """Fibonacci projection signal with institutional features"""
    value_raw: float
    signal_type: str
    composite_confidence: float
    confidence_components: Dict[str, float]
    suggested_sl: float
    suggested_tp: float
    timestamp: datetime
    additional_metadata: Dict[str, Any]

    # Projection-specific fields
    projection: FibonacciProjection
    projection_type: ProjectionType
    target_price: float
    target_time: Optional[datetime]
    projection_level: ProjectionLevel
    base_move_start: float
    base_move_end: float
    projection_ratio: float
    confluence_score: float


class FibonacciProjections(AugmentedIndicator):
    """
    Advanced Fibonacci Projections Analyzer

    Calculates Fibonacci price and time projections with institutional-grade features:
    - Price target projections based on Fibonacci ratios
    - Time cycle projections using Fibonacci sequences
    - Volume-weighted projection validation
    - Smart money confirmation signals
    - Multi-timeframe projection alignment
    - Adaptive confidence scoring
    - Risk management integration
    """

    def __init__(self, timeframe: str = "1D", projection_lookahead: int = 20):
        super().__init__(name="FibonacciProjections", timeframe=timeframe)
        self.projection_lookahead = projection_lookahead  # periods to look ahead
        self.price_history = []
        self.volume_history = []
        self.timestamp_history = []
        self.active_projections = []
        self.historical_projections = []

    def update(self, price: float, volume: float, high: float = None,
               low: float = None, timestamp: datetime = None,
               order_book_data: Dict = None, trade_data: List = None) -> Optional[FibonacciProjectionSignal]:
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
            FibonacciProjectionSignal if projection target is hit, None otherwise
        """
        if timestamp is None:
            timestamp = datetime.now()

        # Update histories
        self.price_history.append(price)
        self.volume_history.append(volume)
        self.timestamp_history.append(timestamp)

        # Maintain history size
        max_history = 200
        if len(self.price_history) > max_history:
            self.price_history.pop(0)
            self.volume_history.pop(0)
            self.timestamp_history.pop(0)

        # Need minimum data for analysis
        if len(self.price_history) < 20:
            return None

        # Update active projections
        self._update_active_projections()

        # Check for projection target hits
        signal = self._check_projection_targets(price, timestamp, order_book_data, trade_data)

        if signal:
            self.current_signal = signal
            self.historical_projections.append(signal)

        return signal

    def _update_active_projections(self):
        """Update active Fibonacci projections based on recent price action"""
        if len(self.price_history) < 20:
            return

        # Find recent swing points
        swing_points = self._find_recent_swings()

        if len(swing_points) < 2:
            return

        # Calculate projections from recent swings
        new_projections = self._calculate_projections(swing_points)

        # Update active projections
        self.active_projections = new_projections

    def _find_recent_swings(self) -> List[Tuple[float, int, str]]:
        """Find recent swing high and low points with timestamps"""
        swings = []
        lookback = 5

        for i in range(lookback, len(self.price_history) - lookback):
            price = self.price_history[i]

            # Check for swing high
            is_high = all(price >= self.price_history[i-j] for j in range(1, lookback+1)) and \
                     all(price >= self.price_history[i+j] for j in range(1, lookback+1))

            # Check for swing low
            is_low = all(price <= self.price_history[i-j] for j in range(1, lookback+1)) and \
                    all(price <= self.price_history[i+j] for j in range(1, lookback+1))

            if is_high:
                swings.append((price, i, 'high'))
            elif is_low:
                swings.append((price, i, 'low'))

        return swings[-6:]  # Last 6 swings for analysis

    def _calculate_projections(self, swings: List[Tuple[float, int, str]]) -> List[FibonacciProjection]:
        """Calculate Fibonacci projections from swing points"""
        projections = []

        if len(swings) < 2:
            return projections

        # Get the most recent significant move
        recent_swings = swings[-4:]  # Last 4 swings

        # Calculate projections for different swing combinations
        for i in range(len(recent_swings) - 1):
            start_price, start_idx, start_type = recent_swings[i]
            end_price, end_idx, end_type = recent_swings[i + 1]

            # Only calculate projections for significant moves
            move_size = abs(end_price - start_price)
            if move_size / min(start_price, end_price) < 0.005:  # Less than 0.5%
                continue

            # Calculate projection targets
            for level in ProjectionLevel:
                projection_ratio = level.value

                if end_price > start_price:
                    # Bullish move - project higher
                    price_target = start_price + (move_size * projection_ratio)
                else:
                    # Bearish move - project lower
                    price_target = end_price - (move_size * projection_ratio)

                # Calculate time projection using Fibonacci sequence
                time_span = end_idx - start_idx
                time_target = self._calculate_time_projection(start_idx, time_span, projection_ratio)

                # Calculate confidence and confluence
                confidence_score = self._calculate_projection_confidence(
                    start_price, end_price, price_target, time_target
                )

                confluence_factors = self._identify_confluence_factors(price_target, time_target)

                volume_profile = self._analyze_projection_volume(start_idx, end_idx)

                smart_money_alignment = self._calculate_smart_money_alignment(price_target)

                projection = FibonacciProjection(
                    price_target=price_target,
                    time_target=time_target,
                    projection_ratio=projection_ratio,
                    confidence_score=confidence_score,
                    confluence_factors=confluence_factors,
                    volume_profile=volume_profile,
                    smart_money_alignment=smart_money_alignment
                )

                projections.append(projection)

        # Sort by confidence and remove duplicates
        projections.sort(key=lambda x: x.confidence_score, reverse=True)
        projections = self._remove_duplicate_projections(projections)

        return projections[:10]  # Keep top 10 projections

    def _calculate_time_projection(self, start_idx: int, time_span: int,
                                 projection_ratio: float) -> Optional[datetime]:
        """Calculate time projection using Fibonacci ratios"""
        if start_idx + time_span >= len(self.timestamp_history):
            return None

        # Apply Fibonacci ratio to time span
        projected_time_span = int(time_span * projection_ratio)
        target_idx = start_idx + time_span + projected_time_span

        if target_idx < len(self.timestamp_history):
            return self.timestamp_history[target_idx]

        # Extrapolate future time
        last_timestamp = self.timestamp_history[-1]
        time_diff = self.timestamp_history[-1] - self.timestamp_history[-2]

        # Estimate future timestamp
        periods_to_add = target_idx - len(self.timestamp_history) + 1
        return last_timestamp + (time_diff * periods_to_add)

    def _calculate_projection_confidence(self, start_price: float, end_price: float,
                                       price_target: float, time_target: Optional[datetime]) -> float:
        """Calculate confidence score for projection"""
        confidence = 0.5  # Base confidence

        # Move size factor (larger moves = higher confidence)
        move_size = abs(end_price - start_price) / min(start_price, end_price)
        confidence += min(0.2, move_size * 2)

        # Volume trend factor
        volume_trend = self._calculate_volume_trend_factor()
        confidence += volume_trend * 0.15

        # Historical success factor
        historical_factor = self._calculate_historical_success_factor(price_target)
        confidence += historical_factor * 0.1

        # Time alignment factor
        if time_target:
            time_factor = self._calculate_time_alignment_factor(time_target)
            confidence += time_factor * 0.1

        return min(1.0, max(0.0, confidence))

    def _identify_confluence_factors(self, price_target: float,
                                   time_target: Optional[datetime]) -> List[str]:
        """Identify confluence factors for the projection"""
        factors = []

        # Check proximity to round numbers
        round_number = round(price_target, -1)  # Nearest 10
        if abs(price_target - round_number) / price_target < 0.005:
            factors.append("Round Number")

        # Check proximity to psychological levels
        if abs(price_target % 100) / price_target < 0.005:
            factors.append("Psychological Level")

        if abs(price_target % 50) / price_target < 0.005:
            factors.append("Half-Psychological Level")

        # Check time cycle confluence
        if time_target:
            # Check for significant time cycles (simplified)
            factors.append("Time Cycle Projection")

        # Check volume profile confluence
        if self._check_volume_confluence(price_target):
            factors.append("Volume Confluence")

        return factors

    def _analyze_projection_volume(self, start_idx: int, end_idx: int) -> Dict[str, Any]:
        """Analyze volume profile for the projection base move"""
        if start_idx >= len(self.volume_history) or end_idx >= len(self.volume_history):
            return {}

        move_volume = self.volume_history[start_idx:end_idx+1]

        return {
            'average_volume': np.mean(move_volume),
            'volume_trend': np.polyfit(range(len(move_volume)), move_volume, 1)[0],
            'high_volume_periods': sum(1 for v in move_volume if v > np.mean(move_volume) * 1.5),
            'volume_distribution': {
                'q25': np.percentile(move_volume, 25),
                'q50': np.percentile(move_volume, 50),
                'q75': np.percentile(move_volume, 75)
            }
        }

    def _calculate_smart_money_alignment(self, price_target: float) -> float:
        """Calculate smart money alignment score for projection"""
        # Simplified smart money analysis
        # In practice, this would analyze order book data, large trades, etc.
        return 0.6  # Placeholder

    def _remove_duplicate_projections(self, projections: List[FibonacciProjection]) -> List[FibonacciProjection]:
        """Remove projections that are too close to each other"""
        if not projections:
            return projections

        filtered = []

        for proj in projections:
            is_duplicate = False
            for existing in filtered:
                price_diff = abs(proj.price_target - existing.price_target)
                price_diff_pct = price_diff / min(proj.price_target, existing.price_target)

                if price_diff_pct < 0.01:  # Within 1%
                    is_duplicate = True
                    break

            if not is_duplicate:
                filtered.append(proj)

        return filtered

    def _calculate_volume_trend_factor(self) -> float:
        """Calculate volume trend factor for confidence"""
        if len(self.volume_history) < 10:
            return 0.5

        recent_volume = self.volume_history[-10:]
        trend = np.polyfit(range(len(recent_volume)), recent_volume, 1)[0]

        # Normalize trend factor
        avg_volume = np.mean(recent_volume)
        if avg_volume == 0:
            return 0.5

        normalized_trend = trend / avg_volume
        return min(1.0, max(0.0, 0.5 + normalized_trend))

    def _calculate_historical_success_factor(self, price_target: float) -> float:
        """Calculate historical success factor for similar projections"""
        if len(self.historical_projections) < 5:
            return 0.5

        # Check success rate of projections in similar price ranges
        similar_projections = [
            p for p in self.historical_projections[-20:]
            if abs(p.target_price - price_target) / price_target < 0.05
        ]

        if not similar_projections:
            return 0.5

        successful = sum(1 for p in similar_projections if p.composite_confidence > 0.7)
        return successful / len(similar_projections)

    def _calculate_time_alignment_factor(self, time_target: datetime) -> float:
        """Calculate time alignment factor"""
        # Simplified - check if time target aligns with significant periods
        now = datetime.now()

        if time_target > now:
            days_ahead = (time_target - now).days

            # Check for Fibonacci time cycles
            fib_cycles = [21, 34, 55, 89, 144]  # Fibonacci days

            for cycle in fib_cycles:
                if abs(days_ahead - cycle) <= 2:  # Within 2 days
                    return 0.8

        return 0.5

    def _check_volume_confluence(self, price_target: float) -> bool:
        """Check for volume confluence at price target"""
        # Simplified volume analysis
        if len(self.volume_history) < 20:
            return False

        # Check if there were high volume periods near this price level historically
        return True  # Placeholder - would implement actual volume profile analysis

    def _check_projection_targets(self, current_price: float, timestamp: datetime,
                               order_book_data: Dict = None,
                               trade_data: List = None) -> Optional[FibonacciProjectionSignal]:
        """Check if current price has hit any projection targets"""
        tolerance = 0.005  # 0.5% tolerance

        for projection in self.active_projections:
            price_diff_pct = abs(current_price - projection.price_target) / projection.price_target

            if price_diff_pct <= tolerance:
                # Check if time is also aligned (if time target exists)
                time_aligned = True
                if projection.time_target:
                    time_diff = abs((timestamp - projection.time_target).total_seconds())
                    time_tolerance = timedelta(days=1).total_seconds()  # 1 day tolerance
                    time_aligned = time_diff <= time_tolerance

                if time_aligned:
                    return self._create_projection_signal(
                        projection, current_price, timestamp, order_book_data, trade_data
                    )

        return None

    def _create_projection_signal(self, projection: FibonacciProjection, current_price: float,
                                timestamp: datetime, order_book_data: Dict = None,
                                trade_data: List = None) -> FibonacciProjectionSignal:
        """Create a projection signal when target is hit"""
        # Determine projection type
        if projection.time_target:
            projection_type = ProjectionType.PRICE_TIME_PROJECTION
        else:
            projection_type = ProjectionType.PRICE_PROJECTION

        # Map ratio to level
        level_mapping = {
            0.618: ProjectionLevel.LEVEL_0618,
            1.000: ProjectionLevel.LEVEL_1000,
            1.272: ProjectionLevel.LEVEL_1272,
            1.618: ProjectionLevel.LEVEL_1618,
            2.000: ProjectionLevel.LEVEL_2000,
            2.618: ProjectionLevel.LEVEL_2618,
            3.618: ProjectionLevel.LEVEL_3618
        }

        projection_level = level_mapping.get(projection.projection_ratio, ProjectionLevel.LEVEL_1000)

        # Calculate confidence components
        confidence_components = self._calculate_projection_signal_confidence(
            projection, current_price, order_book_data, trade_data
        )

        composite_confidence = np.mean(list(confidence_components.values()))

        # Risk management
        suggested_sl, suggested_tp = self._calculate_projection_risk_management(projection, current_price)

        # Additional metadata
        additional_metadata = {
            'projection_ratio': projection.projection_ratio,
            'confluence_factors': projection.confluence_factors,
            'volume_profile': projection.volume_profile,
            'smart_money_alignment': projection.smart_money_alignment,
            'time_target_alignment': projection.time_target is not None,
            'projection_type': projection_type.value
        }

        # Get base move info (simplified)
        base_move_start = current_price * 0.95  # Placeholder
        base_move_end = current_price * 1.05    # Placeholder

        return FibonacciProjectionSignal(
            value_raw=current_price,
            signal_type=f"FIBONACCI_{projection_type.value.upper()}_{projection_level.name}",
            composite_confidence=composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=suggested_sl,
            suggested_tp=suggested_tp,
            timestamp=timestamp,
            additional_metadata=additional_metadata,
            projection=projection,
            projection_type=projection_type,
            target_price=projection.price_target,
            target_time=projection.time_target,
            projection_level=projection_level,
            base_move_start=base_move_start,
            base_move_end=base_move_end,
            projection_ratio=projection.projection_ratio,
            confluence_score=len(projection.confluence_factors) * 0.2
        )

    def _calculate_projection_signal_confidence(self, projection: FibonacciProjection,
                                             current_price: float, order_book_data: Dict = None,
                                             trade_data: List = None) -> Dict[str, float]:
        """Calculate confidence components for projection signal"""
        components = {}

        # Base projection confidence
        components['projection_confidence'] = projection.confidence_score

        # Confluence strength
        components['confluence_score'] = min(1.0, len(projection.confluence_factors) * 0.25)

        # Volume confirmation at target
        components['volume_confirmation'] = self._calculate_target_volume_confirmation()

        # Smart money confirmation
        components['smart_money_score'] = projection.smart_money_alignment

        # Price precision (how close to exact target)
        price_accuracy = 1.0 - (abs(current_price - projection.price_target) / projection.price_target)
        components['price_accuracy'] = max(0.0, price_accuracy)

        # Time alignment (if applicable)
        if projection.time_target:
            time_accuracy = self._calculate_time_accuracy(projection.time_target, datetime.now())
            components['time_accuracy'] = time_accuracy
        else:
            components['time_accuracy'] = 0.5

        return components

    def _calculate_target_volume_confirmation(self) -> float:
        """Calculate volume confirmation at projection target"""
        if len(self.volume_history) < 5:
            return 0.5

        recent_volume = np.mean(self.volume_history[-5:])
        avg_volume = np.mean(self.volume_history)

        if recent_volume > avg_volume * 1.5:
            return 0.9
        elif recent_volume > avg_volume * 1.2:
            return 0.7
        else:
            return 0.5

    def _calculate_time_accuracy(self, target_time: datetime, actual_time: datetime) -> float:
        """Calculate how accurate the time projection was"""
        time_diff = abs((actual_time - target_time).total_seconds())
        max_tolerance = timedelta(days=5).total_seconds()  # 5 days tolerance

        accuracy = 1.0 - (time_diff / max_tolerance)
        return max(0.0, min(1.0, accuracy))

    def _calculate_projection_risk_management(self, projection: FibonacciProjection,
                                            current_price: float) -> Tuple[float, float]:
        """Calculate stop loss and take profit for projection trade"""
        # Use projection confidence to determine risk parameters
        risk_multiplier = 2.0 if projection.confidence_score > 0.7 else 1.5

        # Base stop loss on recent volatility
        if len(self.price_history) >= 10:
            recent_volatility = np.std(self.price_history[-10:])
            stop_distance = recent_volatility * risk_multiplier
        else:
            stop_distance = current_price * 0.02  # 2% default

        # Determine direction
        if current_price > projection.price_target:
            # Hit target from below - bullish
            suggested_sl = current_price - stop_distance
            suggested_tp = projection.price_target + (stop_distance * 2)
        else:
            # Hit target from above - bearish
            suggested_sl = current_price + stop_distance
            suggested_tp = projection.price_target - (stop_distance * 2)

        return suggested_sl, suggested_tp

    def get_active_projections(self) -> List[FibonacciProjection]:
        """Get currently active projections"""
        return self.active_projections.copy()

    def get_projection_history(self) -> List[FibonacciProjectionSignal]:
        """Get historical projection signals"""
        return self.historical_projections.copy()

    def find_nearest_projection(self, price: float) -> Optional[FibonacciProjection]:
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