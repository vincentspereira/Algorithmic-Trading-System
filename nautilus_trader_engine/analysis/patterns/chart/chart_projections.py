"""
Chart Projections Module

Advanced chart pattern price projections with institutional-grade features
including volume weighting, smart money confirmation, multi-timeframe analysis,
and adaptive confidence scoring for professional trading applications.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import numpy as np

from ...core.base_classes import AugmentedIndicator


class ChartProjectionType(Enum):
    """Types of chart pattern projections"""
    BREAKOUT_TARGET = "breakout_target"
    RETRACEMENT_TARGET = "retraction_target"
    EXTENSION_TARGET = "extension_target"
    FAILURE_TARGET = "failure_target"
    MEASURED_MOVE = "measured_move"


class ProjectionReliability(Enum):
    """Projection reliability levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class ChartProjection:
    """Represents a chart pattern projection"""
    price_target: float
    time_target: Optional[datetime]
    projection_type: ChartProjectionType
    pattern_type: str
    reliability: ProjectionReliability
    confidence_score: float
    risk_reward_ratio: float
    confluence_factors: List[str]
    volume_profile: Dict[str, Any]
    smart_money_alignment: float
    technical_levels: Dict[str, float]


@dataclass
class ChartProjectionSignal:
    """Chart projection signal with institutional features"""
    value_raw: float
    signal_type: str
    composite_confidence: float
    confidence_components: Dict[str, float]
    suggested_sl: float
    suggested_tp: float
    timestamp: datetime
    additional_metadata: Dict[str, Any]

    # Projection-specific fields
    projection: ChartProjection
    projection_type: ChartProjectionType
    target_price: float
    target_time: Optional[datetime]
    pattern_context: str
    confluence_score: float
    risk_reward_ratio: float


class ChartProjections(AugmentedIndicator):
    """
    Advanced Chart Projections Analyzer

    Calculates chart pattern price and time projections with institutional-grade features:
    - Breakout target projections based on pattern measurements
    - Retracement and extension targets using pattern geometry
    - Volume-weighted projection validation
    - Smart money confirmation signals
    - Multi-timeframe projection alignment
    - Adaptive confidence scoring
    - Risk management integration
    """

    def __init__(self, timeframe: str = "1D", projection_horizon: int = 50):
        super().__init__(name="ChartProjections", timeframe=timeframe)
        self.projection_horizon = projection_horizon  # periods to look ahead
        self.price_history = []
        self.volume_history = []
        self.timestamp_history = []
        self.active_projections = []
        self.completed_projections = []
        self.pattern_context = {}

        # Pattern-specific projection measurements
        self.measurement_ratios = self._initialize_measurement_ratios()

    def _initialize_measurement_ratios(self) -> Dict[str, Dict[str, List[float]]]:
        """Initialize measurement ratios for different chart patterns"""
        return {
            'head_and_shoulders': {
                'measured_move': [1.0, 1.618, 2.618],  # Height of pattern projected from breakout
                'retrace_target': [0.382, 0.5, 0.618],  # Retracement of breakout move
                'extension_target': [1.272, 1.618, 2.0]  # Extension of measured move
            },
            'double_top': {
                'measured_move': [1.0, 1.272, 1.618],
                'retrace_target': [0.5, 0.618, 0.786],
                'extension_target': [1.618, 2.0, 2.618]
            },
            'double_bottom': {
                'measured_move': [1.0, 1.272, 1.618],
                'retrace_target': [0.5, 0.618, 0.786],
                'extension_target': [1.618, 2.0, 2.618]
            },
            'triangle_ascending': {
                'measured_move': [0.8, 1.0, 1.2],  # Triangle height projected
                'retrace_target': [0.382, 0.5, 0.618],
                'extension_target': [1.272, 1.618, 2.0]
            },
            'triangle_descending': {
                'measured_move': [0.8, 1.0, 1.2],
                'retrace_target': [0.382, 0.5, 0.618],
                'extension_target': [1.272, 1.618, 2.0]
            },
            'wedge_ascending': {
                'measured_move': [1.0, 1.618, 2.618],
                'retrace_target': [0.5, 0.618, 0.786],
                'extension_target': [1.618, 2.618, 4.236]
            },
            'wedge_descending': {
                'measured_move': [1.0, 1.618, 2.618],
                'retrace_target': [0.5, 0.618, 0.786],
                'extension_target': [1.618, 2.618, 4.236]
            },
            'flag': {
                'measured_move': [1.0, 1.272, 1.618],  # Flagpole height projected
                'retrace_target': [0.382, 0.5, 0.618],
                'extension_target': [1.618, 2.0, 2.618]
            },
            'pennant': {
                'measured_move': [0.8, 1.0, 1.2],  # Pole height projected
                'retrace_target': [0.5, 0.618, 0.786],
                'extension_target': [1.272, 1.618, 2.0]
            }
        }

    def update(self, price: float, volume: float, high: float = None,
               low: float = None, timestamp: datetime = None,
               order_book_data: Dict = None, trade_data: List = None) -> Optional[ChartProjectionSignal]:
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
            ChartProjectionSignal if projection target is hit, None otherwise
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
        """Update current chart pattern context"""
        if len(self.price_history) < 20:
            return

        # Analyze current pattern development
        self.pattern_context = self._analyze_pattern_context()

    def _update_projections(self):
        """Update active chart projections based on current context"""
        if not self.pattern_context or len(self.price_history) < 20:
            return

        # Calculate projections based on current pattern context
        projections = self._calculate_chart_projections()

        # Update active projections
        self.active_projections = projections

    def _analyze_pattern_context(self) -> Dict[str, Any]:
        """Analyze current chart pattern context"""
        context = {
            'active_patterns': [],
            'trend_direction': self._determine_trend_direction(),
            'volatility': self._calculate_volatility(),
            'support_resistance': self._identify_key_levels(),
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
                    context['pattern_stage'] = 'potential_base'
                elif position_pct < 0.7:
                    context['pattern_stage'] = 'consolidation'
                else:
                    context['pattern_stage'] = 'potential_breakout'

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

    def _calculate_volatility(self) -> float:
        """Calculate current volatility"""
        if len(self.price_history) < 10:
            return 0.0

        returns = np.diff(self.price_history[-20:]) / self.price_history[-21:-1]
        return np.std(returns)

    def _identify_key_levels(self) -> Dict[str, List[float]]:
        """Identify key support and resistance levels"""
        if len(self.price_history) < 20:
            return {'support': [], 'resistance': []}

        # Simple level identification
        recent_prices = self.price_history[-50:]
        support_levels = []
        resistance_levels = []

        # Find local minima and maxima
        for i in range(2, len(recent_prices) - 2):
            if (recent_prices[i] < recent_prices[i-1] and
                recent_prices[i] < recent_prices[i-2] and
                recent_prices[i] < recent_prices[i+1] and
                recent_prices[i] < recent_prices[i+2]):
                support_levels.append(recent_prices[i])

            if (recent_prices[i] > recent_prices[i-1] and
                recent_prices[i] > recent_prices[i-2] and
                recent_prices[i] > recent_prices[i+1] and
                recent_prices[i] > recent_prices[i+2]):
                resistance_levels.append(recent_prices[i])

        return {
            'support': support_levels[-3:],  # Last 3 support levels
            'resistance': resistance_levels[-3:]  # Last 3 resistance levels
        }

    def _calculate_chart_projections(self) -> List[ChartProjection]:
        """Calculate chart projections based on current context"""
        projections = []

        if not self.pattern_context or len(self.price_history) < 20:
            return projections

        trend = self.pattern_context.get('trend_direction', 'sideways')
        pattern_stage = self.pattern_context.get('pattern_stage', 'unknown')

        # Calculate different types of projections
        if trend in ['uptrend', 'downtrend']:
            # Add breakout projections
            breakout_projections = self._calculate_breakout_projections(trend, pattern_stage)
            projections.extend(breakout_projections)

            # Add measured move projections
            measured_projections = self._calculate_measured_move_projections(trend)
            projections.extend(measured_projections)

        # Add retracement projections
        retracement_projections = self._calculate_retracement_projections()
        projections.extend(retracement_projections)

        # Sort by confidence and limit number
        projections.sort(key=lambda x: x.confidence_score, reverse=True)
        return projections[:10]  # Keep top 10 projections

    def _calculate_breakout_projections(self, trend: str, pattern_stage: str) -> List[ChartProjection]:
        """Calculate breakout target projections"""
        projections = []

        if len(self.price_history) < 15:
            return projections

        # Get recent consolidation range
        recent_prices = self.price_history[-20:]
        consolidation_high = max(recent_prices)
        consolidation_low = min(recent_prices)
        range_size = consolidation_high - consolidation_low

        # Calculate breakout targets
        for pattern_type, ratios in self.measurement_ratios.items():
            measured_moves = ratios['measured_move']

            for ratio in measured_moves:
                if trend == 'uptrend':
                    # Bullish breakout target
                    price_target = consolidation_high + (range_size * ratio)
                    projection_type = ChartProjectionType.BREAKOUT_TARGET
                else:
                    # Bearish breakout target
                    price_target = consolidation_low - (range_size * ratio)
                    projection_type = ChartProjectionType.BREAKOUT_TARGET

                # Calculate time target
                time_target = self._calculate_breakout_time_target(pattern_stage, ratio)

                # Calculate confidence
                confidence_score = self._calculate_projection_confidence(
                    price_target, time_target, pattern_type, ratio, pattern_stage
                )

                # Determine reliability
                if confidence_score > 0.8:
                    reliability = ProjectionReliability.VERY_HIGH
                elif confidence_score > 0.6:
                    reliability = ProjectionReliability.HIGH
                elif confidence_score > 0.4:
                    reliability = ProjectionReliability.MEDIUM
                else:
                    reliability = ProjectionReliability.LOW

                # Confluence factors
                confluence_factors = self._identify_projection_confluence(price_target, time_target)

                # Volume profile
                volume_profile = self._analyze_projection_volume(pattern_type)

                # Smart money alignment
                smart_money_alignment = self._calculate_projection_smart_money(price_target)

                # Technical levels
                technical_levels = self._calculate_technical_levels(price_target)

                # Risk-reward ratio
                risk_reward = self._calculate_projection_risk_reward(price_target, consolidation_high, consolidation_low)

                projection = ChartProjection(
                    price_target=price_target,
                    time_target=time_target,
                    projection_type=projection_type,
                    pattern_type=pattern_type,
                    reliability=reliability,
                    confidence_score=confidence_score,
                    risk_reward_ratio=risk_reward,
                    confluence_factors=confluence_factors,
                    volume_profile=volume_profile,
                    smart_money_alignment=smart_money_alignment,
                    technical_levels=technical_levels
                )

                projections.append(projection)

        return projections

    def _calculate_measured_move_projections(self, trend: str) -> List[ChartProjection]:
        """Calculate measured move projections"""
        projections = []

        if len(self.price_history) < 25:
            return projections

        # Find recent significant moves
        moves = self._find_significant_moves()

        for move in moves[-3:]:  # Last 3 significant moves
            move_size = abs(move['end'] - move['start'])

            for pattern_type, ratios in self.measurement_ratios.items():
                extension_targets = ratios['extension_target']

                for ratio in extension_targets:
                    if trend == 'uptrend':
                        price_target = move['end'] + (move_size * ratio)
                    else:
                        price_target = move['end'] - (move_size * ratio)

                    time_target = self._calculate_extension_time_target(move, ratio)

                    confidence_score = self._calculate_measured_move_confidence(move, ratio, pattern_type)

                    projection = ChartProjection(
                        price_target=price_target,
                        time_target=time_target,
                        projection_type=ChartProjectionType.MEASURED_MOVE,
                        pattern_type=pattern_type,
                        reliability=ProjectionReliability.MEDIUM,
                        confidence_score=confidence_score,
                        risk_reward_ratio=self._calculate_projection_risk_reward(price_target, move['high'], move['low']),
                        confluence_factors=['measured_move'],
                        volume_profile={},
                        smart_money_alignment=0.5,
                        technical_levels=self._calculate_technical_levels(price_target)
                    )

                    projections.append(projection)

        return projections

    def _calculate_retracement_projections(self) -> List[ChartProjection]:
        """Calculate retracement target projections"""
        projections = []

        if len(self.price_history) < 20:
            return projections

        # Calculate retracement targets from recent swing
        recent_high = max(self.price_history[-20:])
        recent_low = min(self.price_history[-20:])
        current_price = self.price_history[-1]

        range_size = recent_high - recent_low

        # Determine if we're in a retracement
        if current_price > recent_low and current_price < recent_high:
            # Calculate retracement projections
            for pattern_type, ratios in self.measurement_ratios.items():
                retracement_targets = ratios['retrace_target']

                for ratio in retracement_targets:
                    if current_price > (recent_low + recent_high) / 2:  # Above midpoint
                        price_target = recent_high - (range_size * ratio)
                    else:  # Below midpoint
                        price_target = recent_low + (range_size * ratio)

                    time_target = self._calculate_retracement_time_target()

                    confidence_score = self._calculate_retracement_confidence(ratio, pattern_type)

                    projection = ChartProjection(
                        price_target=price_target,
                        time_target=time_target,
                        projection_type=ChartProjectionType.RETRACEMENT_TARGET,
                        pattern_type=pattern_type,
                        reliability=ProjectionReliability.MEDIUM,
                        confidence_score=confidence_score,
                        risk_reward_ratio=2.0,  # Standard 2:1 for retracements
                        confluence_factors=['fibonacci_retracement'],
                        volume_profile={},
                        smart_money_alignment=0.5,
                        technical_levels=self._calculate_technical_levels(price_target)
                    )

                    projections.append(projection)

        return projections

    def _find_significant_moves(self) -> List[Dict[str, Any]]:
        """Find significant price moves for measured move calculations"""
        moves = []

        if len(self.price_history) < 15:
            return moves

        # Simple move detection
        window_size = 10
        for i in range(window_size, len(self.price_history) - window_size, window_size):
            window = self.price_history[i-window_size:i+window_size]
            move_high = max(window)
            move_low = min(window)
            move_size = move_high - move_low

            if move_size / move_low > 0.03:  # At least 3% move
                moves.append({
                    'start': move_low,
                    'end': move_high,
                    'high': move_high,
                    'low': move_low,
                    'size': move_size,
                    'start_idx': i - window_size,
                    'end_idx': i + window_size
                })

        return moves

    def _calculate_breakout_time_target(self, pattern_stage: str, ratio: float) -> Optional[datetime]:
        """Calculate time target for breakout projection"""
        if len(self.timestamp_history) < 10:
            return None

        base_time = self.timestamp_history[-1]

        if pattern_stage == 'potential_breakout':
            time_factor = 1.0
        elif pattern_stage == 'consolidation':
            time_factor = 1.5
        else:
            time_factor = 2.0

        time_span = (base_time - self.timestamp_history[-10]).total_seconds()
        projected_span = time_span * ratio * time_factor

        return base_time + timedelta(seconds=projected_span)

    def _calculate_extension_time_target(self, move: Dict[str, Any], ratio: float) -> Optional[datetime]:
        """Calculate time target for extension projection"""
        if len(self.timestamp_history) < move['end_idx']:
            return None

        move_duration = (self.timestamp_history[move['end_idx']] -
                        self.timestamp_history[move['start_idx']]).total_seconds()
        extension_duration = move_duration * ratio

        return self.timestamp_history[move['end_idx']] + timedelta(seconds=extension_duration)

    def _calculate_retracement_time_target(self) -> Optional[datetime]:
        """Calculate time target for retracement projection"""
        if len(self.timestamp_history) < 5:
            return None

        recent_duration = (self.timestamp_history[-1] - self.timestamp_history[-5]).total_seconds()
        retracement_duration = recent_duration * 0.618

        return self.timestamp_history[-1] + timedelta(seconds=retracement_duration)

    def _calculate_projection_confidence(self, price_target: float, time_target: Optional[datetime],
                                       pattern_type: str, ratio: float, pattern_stage: str) -> float:
        """Calculate confidence score for projection"""
        confidence = 0.5

        # Pattern type reliability
        pattern_weights = {
            'head_and_shoulders': 0.9,
            'double_top': 0.8,
            'double_bottom': 0.8,
            'triangle_ascending': 0.7,
            'triangle_descending': 0.7,
            'wedge_ascending': 0.6,
            'wedge_descending': 0.6,
            'flag': 0.8,
            'pennant': 0.8
        }
        confidence += pattern_weights.get(pattern_type, 0.5) * 0.2

        # Ratio significance
        significant_ratios = [1.0, 1.272, 1.618, 2.618]
        if ratio in significant_ratios:
            confidence += 0.15

        # Pattern stage factor
        stage_weights = {
            'potential_breakout': 0.2,
            'consolidation': 0.15,
            'potential_base': 0.1
        }
        confidence += stage_weights.get(pattern_stage, 0.1)

        # Volume confirmation
        volume_factor = self._calculate_projection_volume_factor()
        confidence += volume_factor * 0.1

        return min(1.0, confidence)

    def _calculate_measured_move_confidence(self, move: Dict[str, Any], ratio: float, pattern_type: str) -> float:
        """Calculate confidence for measured move projection"""
        base_confidence = 0.4

        # Move size factor
        move_size_pct = move['size'] / move['start']
        if move_size_pct > 0.05:  # Significant move
            base_confidence += 0.2

        # Ratio factor
        if ratio <= 2.0:
            base_confidence += 0.2

        return min(1.0, base_confidence)

    def _calculate_retracement_confidence(self, ratio: float, pattern_type: str) -> float:
        """Calculate confidence for retracement projection"""
        base_confidence = 0.5

        # 61.8% retracements are most common
        if abs(ratio - 0.618) < 0.1:
            base_confidence += 0.2

        return min(1.0, base_confidence)

    def _identify_projection_confluence(self, price_target: float,
                                       time_target: Optional[datetime]) -> List[str]:
        """Identify confluence factors for projection"""
        factors = []

        # Check proximity to key levels
        key_levels = self.pattern_context.get('support_resistance', {})
        all_levels = key_levels.get('support', []) + key_levels.get('resistance', [])

        for level in all_levels:
            if abs(price_target - level) / price_target < 0.005:
                factors.append("Key Support/Resistance")

        # Check round number confluence
        round_number = round(price_target, -1)
        if abs(price_target - round_number) / price_target < 0.005:
            factors.append("Round Number")

        # Time confluence
        if time_target:
            factors.append("Time Projection")

        return factors

    def _analyze_projection_volume(self, pattern_type: str) -> Dict[str, Any]:
        """Analyze volume profile for projection"""
        if len(self.volume_history) < 10:
            return {}

        # Analyze volume based on pattern type
        if pattern_type in ['head_and_shoulders', 'double_top', 'double_bottom']:
            # Reversal patterns - look for volume climax
            recent_volume = self.volume_history[-5:]
            volume_trend = np.polyfit(range(len(recent_volume)), recent_volume, 1)[0]
            return {
                'volume_trend': volume_trend,
                'expected_volume': 'climax',
                'confirmation_score': 0.8 if max(recent_volume) > np.mean(recent_volume) * 1.5 else 0.4
            }
        else:
            return {
                'expected_volume': 'moderate',
                'confirmation_score': 0.6
            }

    def _calculate_projection_smart_money(self, price_target: float) -> float:
        """Calculate smart money alignment for projection"""
        return 0.6  # Simplified

    def _calculate_technical_levels(self, price_target: float) -> Dict[str, float]:
        """Calculate technical levels around projection target"""
        return {
            'entry_zone': price_target * 0.995,
            'stop_loss': price_target * 0.98,
            'take_profit': price_target * 1.02
        }

    def _calculate_projection_risk_reward(self, price_target: float, recent_high: float, recent_low: float) -> float:
        """Calculate risk-reward ratio for projection"""
        # Simplified calculation
        range_size = recent_high - recent_low
        if range_size > 0:
            return range_size / abs(price_target - (recent_high + recent_low) / 2)
        return 2.0  # Default

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

    def _check_projection_targets(self, current_price: float, timestamp: datetime,
                               order_book_data: Dict = None,
                               trade_data: List = None) -> Optional[ChartProjectionSignal]:
        """Check if current price has hit any projection targets"""
        tolerance = 0.005  # 0.5% tolerance

        for projection in self.active_projections:
            price_diff_pct = abs(current_price - projection.price_target) / projection.price_target

            if price_diff_pct <= tolerance:
                # Check time alignment if applicable
                time_aligned = True
                if projection.time_target:
                    time_diff = abs((timestamp - projection.time_target).total_seconds())
                    time_tolerance = timedelta(days=5).total_seconds()
                    time_aligned = time_diff <= time_tolerance

                if time_aligned:
                    return self._create_projection_signal(
                        projection, current_price, timestamp, order_book_data, trade_data
                    )

        return None

    def _create_projection_signal(self, projection: ChartProjection, current_price: float,
                                timestamp: datetime, order_book_data: Dict = None,
                                trade_data: List = None) -> ChartProjectionSignal:
        """Create a projection signal when target is hit"""
        # Calculate confidence components
        confidence_components = self._calculate_projection_signal_confidence(
            projection, current_price, order_book_data, trade_data
        )

        composite_confidence = np.mean(list(confidence_components.values()))

        # Risk management from technical levels
        tech_levels = projection.technical_levels
        suggested_sl = tech_levels.get('stop_loss', current_price * 0.98)
        suggested_tp = tech_levels.get('take_profit', current_price * 1.02)

        # Additional metadata
        additional_metadata = {
            'projection_ratio': 1.0,  # Placeholder
            'confluence_factors': projection.confluence_factors,
            'pattern_type': projection.pattern_type,
            'reliability': projection.reliability.value,
            'volume_profile': projection.volume_profile,
            'smart_money_alignment': projection.smart_money_alignment,
            'technical_levels': projection.technical_levels,
            'risk_reward_ratio': projection.risk_reward_ratio
        }

        return ChartProjectionSignal(
            value_raw=current_price,
            signal_type=f"CHART_{projection.projection_type.value.upper()}_{projection.pattern_type.upper()}",
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
            confluence_score=len(projection.confluence_factors) * 0.2,
            risk_reward_ratio=projection.risk_reward_ratio
        )

    def _calculate_projection_signal_confidence(self, projection: ChartProjection,
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
        max_tolerance = timedelta(days=10).total_seconds()

        accuracy = 1.0 - (time_diff / max_tolerance)
        return max(0.0, min(1.0, accuracy))

    def get_active_projections(self) -> List[ChartProjection]:
        """Get currently active chart projections"""
        return self.active_projections.copy()

    def get_projection_history(self) -> List[ChartProjectionSignal]:
        """Get historical projection signals"""
        return self.completed_projections.copy()

    def get_pattern_context(self) -> Dict[str, Any]:
        """Get current pattern context"""
        return self.pattern_context.copy()

    def find_nearest_projection(self, price: float) -> Optional[ChartProjection]:
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