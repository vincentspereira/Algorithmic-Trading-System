"""Signal Processing Utilities for Trading Strategies

This module provides signal processing utilities for trading strategies,
including signal generation, filtering, aggregation, and validation.

Author: AI Assistant
Date: 2024-12-15
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging
from collections import deque, defaultdict
from scipy import signal as scipy_signal
from scipy.stats import zscore

# Configure logging
logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Types of trading signals"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    STRONG_BUY = "strong_buy"
    STRONG_SELL = "strong_sell"
    NEUTRAL = "neutral"


class SignalStrength(Enum):
    """Signal strength levels"""
    WEAK = 1
    MODERATE = 2
    STRONG = 3
    VERY_STRONG = 4


class FilterType(Enum):
    """Signal filter types"""
    MOVING_AVERAGE = "moving_average"
    EXPONENTIAL = "exponential"
    KALMAN = "kalman"
    BUTTERWORTH = "butterworth"
    SAVGOL = "savgol"


@dataclass
class TradingSignal:
    """Trading signal with metadata"""
    signal_type: SignalType
    strength: SignalStrength
    confidence: float  # 0.0 to 1.0
    timestamp: datetime
    symbol: str
    price: float
    volume: Optional[float] = None
    indicators: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = "unknown"
    expiry: Optional[datetime] = None
    
    def is_expired(self) -> bool:
        """Check if signal has expired"""
        if self.expiry is None:
            return False
        return datetime.now() > self.expiry
    
    def is_buy_signal(self) -> bool:
        """Check if this is a buy signal"""
        return self.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]
    
    def is_sell_signal(self) -> bool:
        """Check if this is a sell signal"""
        return self.signal_type in [SignalType.SELL, SignalType.STRONG_SELL]


@dataclass
class SignalAggregationResult:
    """Result of signal aggregation"""
    final_signal: SignalType
    confidence: float
    contributing_signals: List[TradingSignal]
    weights: Dict[str, float]
    consensus_score: float


class SignalProcessor:
    """Advanced signal processing utilities"""
    
    def __init__(self, lookback_period: int = 100):
        self.lookback_period = lookback_period
        self.signal_history: deque = deque(maxlen=lookback_period)
        self.filters: Dict[str, Any] = {}
    
    def add_signal(self, signal: TradingSignal) -> None:
        """
        Add a signal to the history.
        
        Args:
            signal: TradingSignal to add
        """
        self.signal_history.append(signal)
    
    def generate_crossover_signal(
        self,
        fast_series: pd.Series,
        slow_series: pd.Series,
        symbol: str,
        current_price: float
    ) -> Optional[TradingSignal]:
        """
        Generate crossover signals from two series.
        
        Args:
            fast_series: Fast moving indicator
            slow_series: Slow moving indicator
            symbol: Trading symbol
            current_price: Current price
            
        Returns:
            TradingSignal or None
        """
        try:
            if len(fast_series) < 2 or len(slow_series) < 2:
                return None
            
            # Check for crossover
            fast_current = fast_series.iloc[-1]
            fast_previous = fast_series.iloc[-2]
            slow_current = slow_series.iloc[-1]
            slow_previous = slow_series.iloc[-2]
            
            # Bullish crossover (fast crosses above slow)
            if fast_previous <= slow_previous and fast_current > slow_current:
                # Calculate signal strength based on separation
                separation = abs(fast_current - slow_current) / slow_current
                strength = self._calculate_strength_from_separation(separation)
                confidence = min(0.9, separation * 10)  # Scale to confidence
                
                return TradingSignal(
                    signal_type=SignalType.BUY,
                    strength=strength,
                    confidence=confidence,
                    timestamp=datetime.now(),
                    symbol=symbol,
                    price=current_price,
                    source="crossover",
                    indicators={
                        "fast_value": fast_current,
                        "slow_value": slow_current,
                        "separation": separation
                    }
                )
            
            # Bearish crossover (fast crosses below slow)
            elif fast_previous >= slow_previous and fast_current < slow_current:
                separation = abs(fast_current - slow_current) / slow_current
                strength = self._calculate_strength_from_separation(separation)
                confidence = min(0.9, separation * 10)
                
                return TradingSignal(
                    signal_type=SignalType.SELL,
                    strength=strength,
                    confidence=confidence,
                    timestamp=datetime.now(),
                    symbol=symbol,
                    price=current_price,
                    source="crossover",
                    indicators={
                        "fast_value": fast_current,
                        "slow_value": slow_current,
                        "separation": separation
                    }
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating crossover signal: {e}")
            return None
    
    def generate_threshold_signal(
        self,
        indicator_series: pd.Series,
        upper_threshold: float,
        lower_threshold: float,
        symbol: str,
        current_price: float,
        overbought_signal: SignalType = SignalType.SELL,
        oversold_signal: SignalType = SignalType.BUY
    ) -> Optional[TradingSignal]:
        """
        Generate threshold-based signals (e.g., RSI overbought/oversold).
        
        Args:
            indicator_series: Indicator values
            upper_threshold: Upper threshold for overbought
            lower_threshold: Lower threshold for oversold
            symbol: Trading symbol
            current_price: Current price
            overbought_signal: Signal type for overbought condition
            oversold_signal: Signal type for oversold condition
            
        Returns:
            TradingSignal or None
        """
        try:
            if len(indicator_series) < 1:
                return None
            
            current_value = indicator_series.iloc[-1]
            
            # Overbought condition
            if current_value >= upper_threshold:
                distance_from_threshold = (current_value - upper_threshold) / (100 - upper_threshold)
                strength = self._calculate_strength_from_distance(distance_from_threshold)
                confidence = min(0.95, 0.5 + distance_from_threshold)
                
                return TradingSignal(
                    signal_type=overbought_signal,
                    strength=strength,
                    confidence=confidence,
                    timestamp=datetime.now(),
                    symbol=symbol,
                    price=current_price,
                    source="threshold",
                    indicators={
                        "indicator_value": current_value,
                        "threshold": upper_threshold,
                        "condition": "overbought"
                    }
                )
            
            # Oversold condition
            elif current_value <= lower_threshold:
                distance_from_threshold = (lower_threshold - current_value) / lower_threshold
                strength = self._calculate_strength_from_distance(distance_from_threshold)
                confidence = min(0.95, 0.5 + distance_from_threshold)
                
                return TradingSignal(
                    signal_type=oversold_signal,
                    strength=strength,
                    confidence=confidence,
                    timestamp=datetime.now(),
                    symbol=symbol,
                    price=current_price,
                    source="threshold",
                    indicators={
                        "indicator_value": current_value,
                        "threshold": lower_threshold,
                        "condition": "oversold"
                    }
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating threshold signal: {e}")
            return None
    
    def generate_divergence_signal(
        self,
        price_series: pd.Series,
        indicator_series: pd.Series,
        symbol: str,
        lookback: int = 20
    ) -> Optional[TradingSignal]:
        """
        Generate divergence signals between price and indicator.
        
        Args:
            price_series: Price data
            indicator_series: Indicator data
            symbol: Trading symbol
            lookback: Lookback period for divergence detection
            
        Returns:
            TradingSignal or None
        """
        try:
            if len(price_series) < lookback or len(indicator_series) < lookback:
                return None
            
            # Get recent data
            recent_prices = price_series.tail(lookback)
            recent_indicator = indicator_series.tail(lookback)
            
            # Calculate trends
            price_trend = self._calculate_trend(recent_prices)
            indicator_trend = self._calculate_trend(recent_indicator)
            
            current_price = price_series.iloc[-1]
            
            # Bullish divergence (price declining, indicator rising)
            if price_trend < -0.1 and indicator_trend > 0.1:
                strength = self._calculate_divergence_strength(price_trend, indicator_trend)
                confidence = min(0.8, abs(price_trend - indicator_trend) / 2)
                
                return TradingSignal(
                    signal_type=SignalType.BUY,
                    strength=strength,
                    confidence=confidence,
                    timestamp=datetime.now(),
                    symbol=symbol,
                    price=current_price,
                    source="divergence",
                    indicators={
                        "price_trend": price_trend,
                        "indicator_trend": indicator_trend,
                        "divergence_type": "bullish"
                    }
                )
            
            # Bearish divergence (price rising, indicator declining)
            elif price_trend > 0.1 and indicator_trend < -0.1:
                strength = self._calculate_divergence_strength(price_trend, indicator_trend)
                confidence = min(0.8, abs(price_trend - indicator_trend) / 2)
                
                return TradingSignal(
                    signal_type=SignalType.SELL,
                    strength=strength,
                    confidence=confidence,
                    timestamp=datetime.now(),
                    symbol=symbol,
                    price=current_price,
                    source="divergence",
                    indicators={
                        "price_trend": price_trend,
                        "indicator_trend": indicator_trend,
                        "divergence_type": "bearish"
                    }
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating divergence signal: {e}")
            return None
    
    def filter_signal(
        self,
        signal_series: pd.Series,
        filter_type: FilterType = FilterType.MOVING_AVERAGE,
        **kwargs
    ) -> pd.Series:
        """
        Apply filtering to signal series.
        
        Args:
            signal_series: Series to filter
            filter_type: Type of filter to apply
            **kwargs: Filter-specific parameters
            
        Returns:
            Filtered series
        """
        try:
            if filter_type == FilterType.MOVING_AVERAGE:
                window = kwargs.get('window', 5)
                return signal_series.rolling(window=window).mean()
            
            elif filter_type == FilterType.EXPONENTIAL:
                alpha = kwargs.get('alpha', 0.3)
                return signal_series.ewm(alpha=alpha).mean()
            
            elif filter_type == FilterType.BUTTERWORTH:
                order = kwargs.get('order', 2)
                cutoff = kwargs.get('cutoff', 0.1)
                b, a = scipy_signal.butter(order, cutoff, btype='low')
                return pd.Series(
                    scipy_signal.filtfilt(b, a, signal_series.values),
                    index=signal_series.index
                )
            
            elif filter_type == FilterType.SAVGOL:
                window_length = kwargs.get('window_length', 5)
                polyorder = kwargs.get('polyorder', 2)
                if window_length % 2 == 0:
                    window_length += 1  # Must be odd
                return pd.Series(
                    scipy_signal.savgol_filter(signal_series.values, window_length, polyorder),
                    index=signal_series.index
                )
            
            else:
                logger.warning(f"Unknown filter type: {filter_type}")
                return signal_series
                
        except Exception as e:
            logger.error(f"Error filtering signal: {e}")
            return signal_series
    
    def aggregate_signals(
        self,
        signals: List[TradingSignal],
        weights: Optional[Dict[str, float]] = None,
        method: str = "weighted_average"
    ) -> SignalAggregationResult:
        """
        Aggregate multiple signals into a single signal.
        
        Args:
            signals: List of signals to aggregate
            weights: Weights for each signal source
            method: Aggregation method
            
        Returns:
            SignalAggregationResult
        """
        try:
            if not signals:
                return SignalAggregationResult(
                    final_signal=SignalType.HOLD,
                    confidence=0.0,
                    contributing_signals=[],
                    weights={},
                    consensus_score=0.0
                )
            
            # Filter out expired signals
            valid_signals = [s for s in signals if not s.is_expired()]
            
            if not valid_signals:
                return SignalAggregationResult(
                    final_signal=SignalType.HOLD,
                    confidence=0.0,
                    contributing_signals=[],
                    weights={},
                    consensus_score=0.0
                )
            
            # Default equal weights if not provided
            if weights is None:
                unique_sources = list(set(s.source for s in valid_signals))
                weights = {source: 1.0 / len(unique_sources) for source in unique_sources}
            
            if method == "weighted_average":
                return self._aggregate_weighted_average(valid_signals, weights)
            elif method == "majority_vote":
                return self._aggregate_majority_vote(valid_signals, weights)
            elif method == "confidence_weighted":
                return self._aggregate_confidence_weighted(valid_signals)
            else:
                logger.warning(f"Unknown aggregation method: {method}")
                return self._aggregate_weighted_average(valid_signals, weights)
                
        except Exception as e:
            logger.error(f"Error aggregating signals: {e}")
            return SignalAggregationResult(
                final_signal=SignalType.HOLD,
                confidence=0.0,
                contributing_signals=signals,
                weights=weights or {},
                consensus_score=0.0
            )
    
    def calculate_signal_quality(
        self,
        signals: List[TradingSignal],
        actual_returns: Optional[pd.Series] = None
    ) -> Dict[str, float]:
        """
        Calculate signal quality metrics.
        
        Args:
            signals: List of historical signals
            actual_returns: Actual returns for validation
            
        Returns:
            Dictionary of quality metrics
        """
        try:
            if not signals:
                return {}
            
            # Basic statistics
            buy_signals = [s for s in signals if s.is_buy_signal()]
            sell_signals = [s for s in signals if s.is_sell_signal()]
            
            metrics = {
                'total_signals': len(signals),
                'buy_signals': len(buy_signals),
                'sell_signals': len(sell_signals),
                'signal_frequency': len(signals) / max(1, self._get_signal_timespan_days(signals)),
                'average_confidence': np.mean([s.confidence for s in signals]),
                'confidence_std': np.std([s.confidence for s in signals])
            }
            
            # Signal strength distribution
            strength_counts = defaultdict(int)
            for signal in signals:
                strength_counts[signal.strength.value] += 1
            
            metrics.update({
                f'strength_{k}_count': v for k, v in strength_counts.items()
            })
            
            # If actual returns provided, calculate performance metrics
            if actual_returns is not None:
                performance_metrics = self._calculate_signal_performance(signals, actual_returns)
                metrics.update(performance_metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating signal quality: {e}")
            return {}
    
    def _calculate_strength_from_separation(self, separation: float) -> SignalStrength:
        """Calculate signal strength from indicator separation"""
        if separation < 0.01:
            return SignalStrength.WEAK
        elif separation < 0.03:
            return SignalStrength.MODERATE
        elif separation < 0.05:
            return SignalStrength.STRONG
        else:
            return SignalStrength.VERY_STRONG
    
    def _calculate_strength_from_distance(self, distance: float) -> SignalStrength:
        """Calculate signal strength from threshold distance"""
        if distance < 0.2:
            return SignalStrength.WEAK
        elif distance < 0.4:
            return SignalStrength.MODERATE
        elif distance < 0.6:
            return SignalStrength.STRONG
        else:
            return SignalStrength.VERY_STRONG
    
    def _calculate_trend(self, series: pd.Series) -> float:
        """Calculate trend slope for a series"""
        if len(series) < 2:
            return 0.0
        
        x = np.arange(len(series))
        y = series.values
        
        # Linear regression slope
        slope = np.polyfit(x, y, 1)[0]
        
        # Normalize by series mean
        return slope / np.mean(y) if np.mean(y) != 0 else 0.0
    
    def _calculate_divergence_strength(self, price_trend: float, indicator_trend: float) -> SignalStrength:
        """Calculate divergence signal strength"""
        divergence_magnitude = abs(price_trend - indicator_trend)
        
        if divergence_magnitude < 0.2:
            return SignalStrength.WEAK
        elif divergence_magnitude < 0.4:
            return SignalStrength.MODERATE
        elif divergence_magnitude < 0.6:
            return SignalStrength.STRONG
        else:
            return SignalStrength.VERY_STRONG
    
    def _aggregate_weighted_average(self, signals: List[TradingSignal], weights: Dict[str, float]) -> SignalAggregationResult:
        """Aggregate signals using weighted average"""
        signal_values = []
        confidences = []
        signal_weights = []
        
        # Convert signals to numerical values
        signal_map = {
            SignalType.STRONG_SELL: -2,
            SignalType.SELL: -1,
            SignalType.HOLD: 0,
            SignalType.NEUTRAL: 0,
            SignalType.BUY: 1,
            SignalType.STRONG_BUY: 2
        }
        
        for signal in signals:
            weight = weights.get(signal.source, 0.0)
            signal_values.append(signal_map.get(signal.signal_type, 0))
            confidences.append(signal.confidence)
            signal_weights.append(weight)
        
        # Calculate weighted average
        if sum(signal_weights) > 0:
            weighted_signal = np.average(signal_values, weights=signal_weights)
            weighted_confidence = np.average(confidences, weights=signal_weights)
        else:
            weighted_signal = np.mean(signal_values)
            weighted_confidence = np.mean(confidences)
        
        # Convert back to signal type
        if weighted_signal >= 1.5:
            final_signal = SignalType.STRONG_BUY
        elif weighted_signal >= 0.5:
            final_signal = SignalType.BUY
        elif weighted_signal <= -1.5:
            final_signal = SignalType.STRONG_SELL
        elif weighted_signal <= -0.5:
            final_signal = SignalType.SELL
        else:
            final_signal = SignalType.HOLD
        
        # Calculate consensus score
        consensus_score = 1.0 - (np.std(signal_values) / 2.0) if len(signal_values) > 1 else 1.0
        
        return SignalAggregationResult(
            final_signal=final_signal,
            confidence=weighted_confidence,
            contributing_signals=signals,
            weights=weights,
            consensus_score=max(0.0, min(1.0, consensus_score))
        )
    
    def _aggregate_majority_vote(self, signals: List[TradingSignal], weights: Dict[str, float]) -> SignalAggregationResult:
        """Aggregate signals using majority vote"""
        vote_counts = defaultdict(float)
        
        for signal in signals:
            weight = weights.get(signal.source, 1.0)
            vote_counts[signal.signal_type] += weight
        
        # Find majority signal
        final_signal = max(vote_counts, key=vote_counts.get)
        
        # Calculate confidence based on vote margin
        total_votes = sum(vote_counts.values())
        winning_votes = vote_counts[final_signal]
        confidence = winning_votes / total_votes if total_votes > 0 else 0.0
        
        # Calculate consensus score
        consensus_score = confidence  # Higher confidence means higher consensus
        
        return SignalAggregationResult(
            final_signal=final_signal,
            confidence=confidence,
            contributing_signals=signals,
            weights=weights,
            consensus_score=consensus_score
        )
    
    def _aggregate_confidence_weighted(self, signals: List[TradingSignal]) -> SignalAggregationResult:
        """Aggregate signals weighted by their confidence"""
        if not signals:
            return SignalAggregationResult(
                final_signal=SignalType.HOLD,
                confidence=0.0,
                contributing_signals=[],
                weights={},
                consensus_score=0.0
            )
        
        # Use confidence as weights
        confidence_weights = {signal.source: signal.confidence for signal in signals}
        return self._aggregate_weighted_average(signals, confidence_weights)
    
    def _get_signal_timespan_days(self, signals: List[TradingSignal]) -> int:
        """Get timespan of signals in days"""
        if len(signals) < 2:
            return 1
        
        timestamps = [s.timestamp for s in signals if s.timestamp]
        if not timestamps:
            return 1
        
        return max(1, (max(timestamps) - min(timestamps)).days)
    
    def _calculate_signal_performance(self, signals: List[TradingSignal], returns: pd.Series) -> Dict[str, float]:
        """Calculate signal performance against actual returns"""
        # This would require aligning signals with returns and calculating hit rates
        # Simplified implementation for now
        return {
            'hit_rate': 0.0,  # Placeholder
            'average_return_per_signal': 0.0,  # Placeholder
            'signal_return_correlation': 0.0  # Placeholder
        }


class SignalValidator:
    """Validate and quality-check trading signals"""
    
    @staticmethod
    def validate_signal(signal: TradingSignal) -> Tuple[bool, List[str]]:
        """
        Validate a trading signal for completeness and consistency.
        
        Args:
            signal: TradingSignal to validate
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        try:
            # Check required fields
            if not signal.symbol:
                issues.append("Missing symbol")
            
            if signal.price <= 0:
                issues.append("Invalid price")
            
            if not (0.0 <= signal.confidence <= 1.0):
                issues.append("Confidence must be between 0 and 1")
            
            if signal.timestamp is None:
                issues.append("Missing timestamp")
            
            # Check signal consistency
            if signal.signal_type == SignalType.NEUTRAL and signal.strength != SignalStrength.WEAK:
                issues.append("Neutral signals should have weak strength")
            
            # Check expiry
            if signal.expiry and signal.expiry <= signal.timestamp:
                issues.append("Expiry time must be after signal timestamp")
            
            return len(issues) == 0, issues
            
        except Exception as e:
            return False, [f"Validation error: {str(e)}"]
    
    @staticmethod
    def check_signal_conflicts(signals: List[TradingSignal]) -> List[str]:
        """
        Check for conflicting signals.
        
        Args:
            signals: List of signals to check
            
        Returns:
            List of conflict descriptions
        """
        conflicts = []
        
        try:
            # Group by symbol and time window
            symbol_groups = defaultdict(list)
            for signal in signals:
                if not signal.is_expired():
                    symbol_groups[signal.symbol].append(signal)
            
            # Check for conflicts within each symbol
            for symbol, symbol_signals in symbol_groups.items():
                recent_signals = [
                    s for s in symbol_signals
                    if (datetime.now() - s.timestamp).total_seconds() < 3600  # Last hour
                ]
                
                if len(recent_signals) > 1:
                    buy_signals = [s for s in recent_signals if s.is_buy_signal()]
                    sell_signals = [s for s in recent_signals if s.is_sell_signal()]
                    
                    if buy_signals and sell_signals:
                        conflicts.append(f"Conflicting buy/sell signals for {symbol}")
            
            return conflicts
            
        except Exception as e:
            logger.error(f"Error checking signal conflicts: {e}")
            return [f"Conflict check error: {str(e)}"]


# Export main classes and functions
__all__ = [
    'SignalProcessor',
    'SignalValidator',
    'TradingSignal',
    'SignalAggregationResult',
    'SignalType',
    'SignalStrength',
    'FilterType'
]