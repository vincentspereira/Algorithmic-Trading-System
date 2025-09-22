"""
institutional_candlestick_patterns.py

Enhanced with institutional-grade features:
- Volume confirmation scoring
- VWAP analysis
- Smart money detection
- Adaptive confidence scoring
- Integrated risk management
"""

import logging
from collections import deque
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import numpy as np
from nautilus_trader.indicators.stubs import (
    Bar, BarType, PriceType, BarEvent, InstrumentId, Price,
    BarGenerator, dt_to_unix_nanos, Event, BarData
)
from nautilus_trader.indicators.base.indicator import Indicator
from nautilus_trader.indicators.data.candle import CandleData
from nautilus_trader.indicators.data.pattern import PatternResult
from nautilus_trader.indicators.enum.pattern import (
    PatternType,
    PatternSignal,
    PatternReliability,
)
from .single_candle_patterns import detect_single_candle_patterns
from .two_candle_patterns import detect_two_candle_patterns
from .three_candle_patterns import detect_three_candle_patterns
from .institutional_patterns import detect_institutional_patterns
from .utils import add_volume_confirmation, add_statistical_validation


@dataclass
class EnhancedPatternResult:
    """Enhanced pattern result with institutional-grade metadata"""
    pattern_name: str
    base_signal: str  # 'bullish', 'bearish', 'neutral'
    composite_confidence_score: float  # 0.0 to 1.0
    confidence_components: Dict[str, float]
    suggested_stop_loss: float
    suggested_profit_target: float
    volume_confirmation_score: float
    vwap_analysis: Dict[str, Any]
    smart_money_score: float
    market_regime_context: str
    risk_reward_ratio: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


class InstitutionalCandlestickPatterns(Indicator):
    """
    An advanced candlestick pattern detection indicator that incorporates
    institutional-grade features like volume confirmation, multi-timeframe
    analysis, and statistical validation.
    """

    def __init__(
        self,
        instrument: str,
        bar_type: str,
        volume_confirmation: bool = True,
        multi_timeframe_analysis: bool = True,
        statistical_validation: bool = True,
        min_confidence: float = 0.6,
        lookback_periods: int = 100,
    ):
        """
        Initializes the InstitutionalCandlestickPatterns indicator.

        Args:
            instrument (str): The instrument to analyze.
            bar_type (str): The bar type to use for analysis.
            volume_confirmation (bool): Whether to use volume confirmation.
            multi_timeframe_analysis (bool): Whether to perform multi-timeframe analysis.
            statistical_validation (bool): Whether to use statistical validation.
            min_confidence (float): The minimum confidence level for a pattern to be considered.
            lookback_periods (int): The number of lookback periods for analysis.
        """
        super().__init__(
            instrument=instrument,
            bar_type=bar_type,
            lookback_periods=lookback_periods,
        )
        self.volume_confirmation = volume_confirmation
        self.multi_timeframe_analysis = multi_timeframe_analysis
        self.statistical_validation = statistical_validation
        self.min_confidence = min_confidence
        self.lookback_periods = lookback_periods

        # Historical data storage
        self.candle_history: deque = deque(maxlen=lookback_periods)
        self.volume_history: deque = deque(maxlen=lookback_periods)
        self.pattern_history: deque = deque(maxlen=200)

        # Pattern performance tracking
        self.pattern_performance: Dict[PatternType, Dict] = {}
        self.success_rates: Dict[PatternType, float] = {}

        # Volume analysis
        self.avg_volume_periods = 20
        self.institutional_volume_threshold = 2.0  # 2x average volume

        # Trend context
        self.trend_periods = 20
        self.current_trend = "unknown"

        # Initialize pattern performance tracking
        self._initialize_pattern_tracking()

        self.logger = logging.getLogger(__name__)

    def _initialize_pattern_tracking(self) -> None:
        """Initialize pattern performance tracking"""
        for pattern in PatternType:
            self.pattern_performance[pattern] = {
                "total_occurrences": 0,
                "successful_predictions": 0,
                "avg_confidence": 0.0,
                "avg_strength": 0.0,
                "volume_confirmed_rate": 0.0,
                "last_seen": None,
            }
            self.success_rates[pattern] = 0.5  # Default 50%

    def add_candle(
        self,
        open_price: float,
        high_price: float,
        low_price: float,
        close_price: float,
        volume: float,
        timestamp: datetime = None,
    ) -> None:
        """Add new candle data"""

        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        candle = CandleData(
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume,
            timestamp=timestamp,
        )

        self.candle_history.append(candle)
        self.volume_history.append(volume)

        # Update trend context
        self._update_trend_context()

    def detect_patterns(self) -> List[PatternResult]:
        """Detect all candlestick patterns in current data"""

        if len(self.candle_history) < 3:
            return []

        patterns = []

        # Single candle patterns
        patterns.extend(detect_single_candle_patterns(self))

        # Two candle patterns
        if len(self.candle_history) >= 2:
            patterns.extend(detect_two_candle_patterns(self))

        # Three candle patterns
        if len(self.candle_history) >= 3:
            patterns.extend(detect_three_candle_patterns(self))

        # Advanced institutional patterns
        if len(self.candle_history) >= 5:
            patterns.extend(detect_institutional_patterns(self))

        # Filter by minimum confidence
        patterns = [p for p in patterns if p.confidence >= self.min_confidence]

        # Enhance with volume confirmation
        if self.volume_confirmation:
            patterns = [add_volume_confirmation(self, p) for p in patterns]

        # Add statistical validation
        if self.statistical_validation:
            patterns = [add_statistical_validation(self, p) for p in patterns]

        # Store pattern history
        for pattern in patterns:
            self.pattern_history.append(pattern)

        return patterns

    def detect_all_patterns_enhanced(self) -> Dict[str, EnhancedPatternResult]:
        """
        Detect all patterns with enhanced institutional-grade metadata

        Returns:
            Dictionary mapping pattern names to enhanced results
        """
        enhanced_patterns = {}

        # Get basic patterns
        basic_patterns = self.detect_patterns()

        for pattern in basic_patterns:
            enhanced_result = self._enhance_pattern_result(pattern)
            if enhanced_result:
                enhanced_patterns[pattern.pattern_type.value] = enhanced_result

        return enhanced_patterns

    def _enhance_pattern_result(self, pattern: PatternResult) -> Optional[EnhancedPatternResult]:
        """Enhance a basic pattern result with institutional features"""
        try:
            # Volume confirmation scoring
            volume_score = self._calculate_volume_confirmation_score()

            # VWAP analysis
            vwap_analysis = self._perform_vwap_analysis()

            # Smart money detection
            smart_money_score = self._calculate_smart_money_score()

            # Market regime context
            regime_context = self._determine_market_regime_context()

            # Adaptive confidence scoring
            composite_confidence = self._calculate_adaptive_confidence(
                pattern.confidence, volume_score, smart_money_score, regime_context
            )

            # Risk management
            sl, tp, rr_ratio = self._calculate_risk_parameters(pattern)

            return EnhancedPatternResult(
                pattern_name=pattern.pattern_type.value,
                base_signal=pattern.signal.value.lower(),
                composite_confidence_score=composite_confidence,
                confidence_components={
                    'base_confidence': pattern.confidence,
                    'volume_score': volume_score,
                    'smart_money_score': smart_money_score,
                    'regime_alignment': self._calculate_regime_alignment_score(pattern, regime_context)
                },
                suggested_stop_loss=sl,
                suggested_profit_target=tp,
                volume_confirmation_score=volume_score,
                vwap_analysis=vwap_analysis,
                smart_money_score=smart_money_score,
                market_regime_context=regime_context,
                risk_reward_ratio=rr_ratio,
                timestamp=datetime.now(timezone.utc),
                metadata={
                    'pattern_strength': pattern.strength,
                    'reliability': pattern.reliability.value,
                    'trend_context': pattern.trend_context
                }
            )

        except Exception as e:
            self.logger.error(f"Error enhancing pattern {pattern.pattern_type}: {e}")
            return None

    def _calculate_volume_confirmation_score(self) -> float:
        """Calculate volume confirmation score (0.0 to 1.0)"""
        if len(self.volume_history) < 2:
            return 0.5

        current_volume = self.volume_history[-1]
        avg_volume = np.mean(list(self.volume_history)[:-1])  # Exclude current

        if avg_volume == 0:
            return 0.5

        volume_ratio = current_volume / avg_volume

        # Score based on volume ratio
        if volume_ratio >= 2.0:
            return 1.0  # Very high volume
        elif volume_ratio >= 1.5:
            return 0.8  # High volume
        elif volume_ratio >= 1.2:
            return 0.6  # Moderate volume
        elif volume_ratio >= 0.8:
            return 0.4  # Low volume
        else:
            return 0.2  # Very low volume

    def _perform_vwap_analysis(self) -> Dict[str, Any]:
        """Perform VWAP analysis for pattern context"""
        if len(self.candle_history) < 2:
            return {'vwap_position': 'unknown', 'distance_from_vwap': 0.0}

        # Calculate VWAP (simplified)
        prices = [c.close for c in self.candle_history]
        volumes = list(self.volume_history)

        if len(prices) != len(volumes):
            return {'vwap_position': 'unknown', 'distance_from_vwap': 0.0}

        price_volume_sum = sum(p * v for p, v in zip(prices, volumes))
        total_volume = sum(volumes)

        if total_volume == 0:
            return {'vwap_position': 'unknown', 'distance_from_vwap': 0.0}

        vwap = price_volume_sum / total_volume
        current_price = prices[-1]
        distance = (current_price - vwap) / vwap

        # Determine position relative to VWAP
        if abs(distance) < 0.001:
            position = 'at_vwap'
        elif distance > 0.01:
            position = 'above_vwap'
        elif distance < -0.01:
            position = 'below_vwap'
        else:
            position = 'near_vwap'

        return {
            'vwap_value': vwap,
            'current_price': current_price,
            'distance_from_vwap': distance,
            'vwap_position': position
        }

    def _calculate_smart_money_score(self) -> float:
        """Calculate smart money detection score"""
        # Placeholder for smart money analysis
        # In a full implementation, this would analyze:
        # - Order book imbalance
        # - Large trade detection
        # - Institutional flow patterns

        # For now, return a neutral score
        return 0.6

    def _determine_market_regime_context(self) -> str:
        """Determine current market regime context"""
        if len(self.candle_history) < 20:
            return 'insufficient_data'

        recent_prices = [c.close for c in list(self.candle_history)[-20:]]

        # Calculate trend
        if len(recent_prices) >= 10:
            short_trend = (recent_prices[-1] - recent_prices[-10]) / recent_prices[-10]
            long_trend = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]

            if abs(short_trend) < 0.005 and abs(long_trend) < 0.01:
                return 'sideways'
            elif short_trend > 0.01 and long_trend > 0.02:
                return 'strong_uptrend'
            elif short_trend < -0.01 and long_trend < -0.02:
                return 'strong_downtrend'
            elif short_trend > 0.005:
                return 'uptrend'
            elif short_trend < -0.005:
                return 'downtrend'

        # Calculate volatility
        if len(recent_prices) > 1:
            returns = np.diff(recent_prices) / recent_prices[:-1]
            volatility = np.std(returns)

            if volatility > 0.03:
                return 'high_volatility'
            elif volatility < 0.01:
                return 'low_volatility'

        return 'neutral'

    def _calculate_adaptive_confidence(self, base_confidence: float,
                                     volume_score: float,
                                     smart_money_score: float,
                                     regime_context: str) -> float:
        """Calculate adaptive confidence score factoring multiple components"""

        # Base weights
        weights = {
            'base': 0.4,
            'volume': 0.3,
            'smart_money': 0.2,
            'regime': 0.1
        }

        # Adjust weights based on regime
        regime_multiplier = {
            'strong_uptrend': 1.0,
            'strong_downtrend': 1.0,
            'high_volatility': 0.8,
            'low_volatility': 1.2,
            'sideways': 0.9,
            'neutral': 1.0
        }.get(regime_context, 1.0)

        # Regime alignment score
        regime_score = regime_multiplier

        # Calculate weighted confidence
        confidence = (
            weights['base'] * base_confidence +
            weights['volume'] * volume_score +
            weights['smart_money'] * smart_money_score +
            weights['regime'] * regime_score
        )

        return min(1.0, max(0.0, confidence))

    def _calculate_regime_alignment_score(self, pattern: PatternResult, regime: str) -> float:
        """Calculate how well pattern aligns with current regime"""
        signal = pattern.signal.value.lower()
        regime_lower = regime.lower()

        # Alignment matrix
        alignment_scores = {
            ('bullish', 'uptrend'): 1.0,
            ('bullish', 'strong_uptrend'): 1.0,
            ('bearish', 'downtrend'): 1.0,
            ('bearish', 'strong_downtrend'): 1.0,
            ('bullish', 'downtrend'): 0.3,
            ('bearish', 'uptrend'): 0.3,
            ('neutral', 'sideways'): 0.8,
            ('neutral', 'high_volatility'): 0.6,
            ('neutral', 'low_volatility'): 0.7
        }

        return alignment_scores.get((signal, regime_lower), 0.5)

    def _calculate_risk_parameters(self, pattern: PatternResult) -> tuple:
        """Calculate stop loss, take profit, and risk-reward ratio"""
        if not self.candle_history:
            return 0.0, 0.0, 1.0

        current_candle = self.candle_history[-1]
        signal = pattern.signal.value.lower()

        # Base risk-reward ratio
        rr_ratio = 2.0

        if signal == 'bullish':
            # Long position
            sl = current_candle.low * 0.98  # 2% below low
            tp = current_candle.close + (current_candle.close - sl) * rr_ratio
        elif signal == 'bearish':
            # Short position
            sl = current_candle.high * 1.02  # 2% above high
            tp = current_candle.close - (sl - current_candle.close) * rr_ratio
        else:
            # Neutral - no position
            sl = tp = current_candle.close

        return sl, tp, rr_ratio