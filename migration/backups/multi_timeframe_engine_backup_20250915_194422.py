"""Multi-Timeframe Analysis Engine

Advanced multi-timeframe convergence analysis and signal stacking system
for technical indicators. Provides institutional-grade timeframe alignment
and signal confirmation across multiple time horizons.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, NamedTuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from collections import deque, defaultdict
import math
from scipy import stats

from .core_indicator_base import IndicatorSignal, SignalType, MarketRegime


class TimeframeType(Enum):
    """Standard timeframe types"""
    TICK = "tick"
    SECOND_1 = "1s"
    SECOND_5 = "5s"
    SECOND_15 = "15s"
    SECOND_30 = "30s"
    MINUTE_1 = "1m"
    MINUTE_2 = "2m"
    MINUTE_3 = "3m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR_1 = "1h"
    HOUR_2 = "2h"
    HOUR_4 = "4h"
    HOUR_6 = "6h"
    HOUR_8 = "8h"
    HOUR_12 = "12h"
    DAY_1 = "1d"
    DAY_3 = "3d"
    WEEK_1 = "1w"
    MONTH_1 = "1M"
    QUARTER_1 = "1Q"
    YEAR_1 = "1Y"


class TimeframeRelation(Enum):
    """Relationship between timeframes"""
    HIGHER = "higher"  # Higher timeframe (longer period)
    LOWER = "lower"   # Lower timeframe (shorter period)
    SAME = "same"     # Same timeframe
    UNRELATED = "unrelated"  # No clear relationship


class ConvergenceType(Enum):
    """Types of signal convergence"""
    BULLISH_ALIGNMENT = "bullish_alignment"  # All timeframes bullish
    BEARISH_ALIGNMENT = "bearish_alignment"  # All timeframes bearish
    MIXED_SIGNALS = "mixed_signals"          # Mixed signals across timeframes
    DIVERGENCE = "divergence"                # Conflicting signals
    CONFIRMATION = "confirmation"            # Lower TF confirms higher TF
    REJECTION = "rejection"                  # Lower TF rejects higher TF
    TRANSITION = "transition"                # Signals in transition


class SignalWeight(Enum):
    """Signal weighting schemes"""
    EQUAL = "equal"                    # Equal weight all timeframes
    TIMEFRAME_WEIGHTED = "tf_weighted" # Weight by timeframe importance
    STRENGTH_WEIGHTED = "str_weighted" # Weight by signal strength
    VOLUME_WEIGHTED = "vol_weighted"   # Weight by volume
    HYBRID = "hybrid"                  # Combination of methods
    ADAPTIVE = "adaptive"              # Adaptive based on market conditions


@dataclass
class TimeframeConfig:
    """Configuration for a specific timeframe"""
    timeframe: TimeframeType
    weight: float = 1.0
    lookback_periods: int = 100
    min_data_points: int = 20
    enable_regime_adaptation: bool = True
    
    # Signal filtering
    min_signal_strength: float = 0.2
    filter_noise: bool = True
    noise_threshold: float = 0.1
    
    # Convergence settings
    convergence_window: int = 5  # Periods to look for convergence
    divergence_threshold: float = 0.3  # Threshold for divergence detection


@dataclass
class MultiTimeframeConfig:
    """Configuration for multi-timeframe analysis"""
    # Timeframe settings
    timeframes: List[TimeframeConfig] = field(default_factory=list)
    primary_timeframe: TimeframeType = TimeframeType.HOUR_1
    
    # Weighting scheme
    weighting_method: SignalWeight = SignalWeight.HYBRID
    higher_tf_bias: float = 1.5  # Bias towards higher timeframes
    
    # Convergence analysis
    min_convergence_score: float = 0.6
    convergence_decay: float = 0.95  # How quickly convergence decays
    enable_divergence_detection: bool = True
    
    # Signal stacking
    enable_signal_stacking: bool = True
    stack_threshold: float = 0.7
    max_stack_size: int = 5
    
    # Performance optimization
    cache_signals: bool = True
    max_cache_size: int = 1000
    update_frequency: int = 1  # Update every N periods
    
    # Advanced features
    enable_fractal_analysis: bool = True
    enable_harmonic_analysis: bool = False
    enable_wave_analysis: bool = False


@dataclass
class TimeframeSignal:
    """Signal from a specific timeframe"""
    timeframe: TimeframeType
    signal: IndicatorSignal
    timestamp: datetime
    weight: float = 1.0
    asset: str = ""  # Asset identifier for cross-asset analysis
    
    # Signal metadata
    confidence: float = 0.0
    volume_confirmation: float = 0.0
    regime_alignment: float = 0.0
    
    # Technical details
    indicator_name: str = ""
    raw_value: float = 0.0
    normalized_value: float = 0.0
    
    # Validation
    is_valid: bool = True
    validation_score: float = 1.0
    noise_level: float = 0.0


@dataclass
class ConvergenceAnalysis:
    """Analysis of signal convergence across timeframes"""
    convergence_type: ConvergenceType
    convergence_score: float
    participating_timeframes: List[TimeframeType]
    
    # Detailed analysis
    bullish_timeframes: List[TimeframeType] = field(default_factory=list)
    bearish_timeframes: List[TimeframeType] = field(default_factory=list)
    neutral_timeframes: List[TimeframeType] = field(default_factory=list)
    
    # Strength metrics
    average_strength: float = 0.0
    weighted_strength: float = 0.0
    strength_consistency: float = 0.0
    
    # Timing analysis
    convergence_duration: int = 0  # Periods of convergence
    time_to_convergence: int = 0   # Periods to reach convergence
    expected_duration: int = 0     # Expected convergence duration
    
    # Confidence metrics
    confidence: float = 0.0
    reliability_score: float = 0.0
    historical_accuracy: float = 0.0


@dataclass
class MultiTimeframeSignal:
    """Aggregated signal from multiple timeframes"""
    primary_signal: IndicatorSignal
    convergence_analysis: ConvergenceAnalysis
    timeframe_signals: Dict[TimeframeType, TimeframeSignal]
    
    # Aggregated metrics
    composite_strength: float = 0.0
    composite_confidence: float = 0.0
    risk_adjusted_signal: float = 0.0
    
    # Timing information
    signal_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expected_duration: int = 0
    optimal_entry_timeframe: Optional[TimeframeType] = None
    optimal_exit_timeframe: Optional[TimeframeType] = None
    
    # Performance tracking
    signal_id: str = ""
    backtest_score: float = 0.0
    forward_test_score: float = 0.0


class MultiTimeframeEngine:
    """Advanced Multi-Timeframe Analysis Engine
    
    Provides sophisticated multi-timeframe signal analysis with:
    - Signal convergence detection
    - Timeframe-weighted signal stacking
    - Fractal and harmonic analysis
    - Adaptive weighting schemes
    - Performance-based optimization
    """
    
    def __init__(self, config: MultiTimeframeConfig = None):
        self.config = config or MultiTimeframeConfig()
        
        # Signal storage by timeframe
        self.timeframe_signals: Dict[TimeframeType, deque] = {}
        self.signal_cache: Dict[str, MultiTimeframeSignal] = {}
        
        # Initialize timeframe storage
        for tf_config in self.config.timeframes:
            self.timeframe_signals[tf_config.timeframe] = deque(
                maxlen=tf_config.lookback_periods
            )
        
        # Convergence tracking
        self.convergence_history: deque = deque(maxlen=500)
        self.divergence_events: deque = deque(maxlen=100)
        
        # Performance tracking
        self.signal_performance: Dict[str, Dict[str, float]] = defaultdict(dict)
        self.timeframe_weights: Dict[TimeframeType, float] = {}
        
        # Analysis components
        self.fractal_analyzer: Optional['FractalAnalyzer'] = None
        self.harmonic_analyzer: Optional['HarmonicAnalyzer'] = None
        
        # Initialize weights
        self._initialize_timeframe_weights()
        
        # Update counter
        self.update_counter = 0
    
    def add_signal(
        self,
        timeframe: TimeframeType,
        signal: IndicatorSignal,
        indicator_name: str = "",
        asset: str = "",
        additional_data: Dict[str, Any] = None
    ) -> None:
        """Add a signal from a specific timeframe"""
        
        # Create timeframe signal
        tf_signal = TimeframeSignal(
            timeframe=timeframe,
            signal=signal,
            timestamp=datetime.now(timezone.utc),
            indicator_name=indicator_name,
            weight=self.timeframe_weights.get(timeframe, 1.0),
            asset=asset
        )
        
        # Add additional data if provided
        if additional_data:
            tf_signal.confidence = additional_data.get('confidence', 0.0)
            tf_signal.volume_confirmation = additional_data.get('volume_confirmation', 0.0)
            tf_signal.raw_value = additional_data.get('raw_value', 0.0)
        
        # Validate signal
        tf_signal.is_valid, tf_signal.validation_score = self._validate_signal(tf_signal)
        
        # Store signal
        if timeframe not in self.timeframe_signals:
            self.timeframe_signals[timeframe] = deque(maxlen=100)
        
        self.timeframe_signals[timeframe].append(tf_signal)
    
    def calculate_cross_asset_correlation(
        self,
        asset1: str,
        asset2: str,
        timeframe: TimeframeType,
        periods: int = 50
    ) -> float:
        """Calculate correlation between two assets on a specific timeframe"""
        
        if timeframe not in self.timeframe_signals:
            return 0.0
        
        # Collect signals for each asset
        signals1 = [s for s in list(self.timeframe_signals[timeframe])[-periods:] if s.asset == asset1]
        signals2 = [s for s in list(self.timeframe_signals[timeframe])[-periods:] if s.asset == asset2]
        
        if len(signals1) < 10 or len(signals2) < 10:
            return 0.0
        
        values1 = [self._signal_to_numeric(s.signal) for s in signals1]
        values2 = [self._signal_to_numeric(s.signal) for s in signals2]
        
        min_len = min(len(values1), len(values2))
        values1 = values1[-min_len:]
        values2 = values2[-min_len:]
        
        if min_len < 5:
            return 0.0
        
        correlation = np.corrcoef(values1, values2)[0, 1]
        return correlation if not np.isnan(correlation) else 0.0
    
    def analyze_convergence(
        self,
        indicator_name: str = "",
        lookback_periods: int = 10
    ) -> MultiTimeframeSignal:
        """Analyze signal convergence across all timeframes"""
        
        self.update_counter += 1
        
        # Get recent signals from all timeframes
        recent_signals = self._get_recent_signals(lookback_periods)
        
        if not recent_signals:
            return self._create_empty_signal()
        
        # Perform convergence analysis
        convergence_analysis = self._analyze_signal_convergence(recent_signals)
        
        # Calculate cross-asset correlations if multiple assets present
        assets = set()
        for signals_list in recent_signals.values():
            for s in signals_list:
                if s.asset:
                    assets.add(s.asset)
        
        if len(assets) > 1:
            correlations = []
            asset_list = list(assets)
            for i in range(len(asset_list)):
                for j in range(i+1, len(asset_list)):
                    corr = self.calculate_cross_asset_correlation(
                        asset_list[i],
                        asset_list[j],
                        self.config.primary_timeframe
                    )
                    correlations.append(abs(corr))  # Use absolute correlation for strength
        
        avg_correlation = np.mean(correlations) if correlations else 0.0
        # Adjust convergence score: high correlation strengthens alignment
        convergence_analysis.convergence_score *= (1 + avg_correlation * 0.3)
        convergence_analysis.convergence_score = min(1.0, convergence_analysis.convergence_score)
        
        # Generate composite signal
        composite_signal = self._generate_composite_signal(recent_signals, convergence_analysis)
        
        # Create multi-timeframe signal
        mtf_signal = MultiTimeframeSignal(
            primary_signal=composite_signal,
            convergence_analysis=convergence_analysis,
            timeframe_signals={tf: signals[-1] for tf, signals in recent_signals.items() if signals}
        )
        
        # Calculate composite metrics
        mtf_signal.composite_strength = self._calculate_composite_strength(recent_signals)
        mtf_signal.composite_confidence = self._calculate_composite_confidence(recent_signals)
        mtf_signal.risk_adjusted_signal = self._calculate_risk_adjusted_signal(mtf_signal)
        
        # Determine optimal timeframes
        mtf_signal.optimal_entry_timeframe = self._find_optimal_entry_timeframe(recent_signals)
        mtf_signal.optimal_exit_timeframe = self._find_optimal_exit_timeframe(recent_signals)
        
        # Cache signal if enabled
        if self.config.cache_signals:
            signal_id = f"{indicator_name}_{datetime.now(timezone.utc).timestamp()}"
            mtf_signal.signal_id = signal_id
            self.signal_cache[signal_id] = mtf_signal
            
            # Manage cache size
            if len(self.signal_cache) > self.config.max_cache_size:
                oldest_key = min(self.signal_cache.keys())
                del self.signal_cache[oldest_key]
        
        # Update performance tracking
        if self.update_counter % 10 == 0:  # Every 10 updates
            self._update_performance_metrics()
        
        return mtf_signal
    
    def get_timeframe_hierarchy(self) -> List[TimeframeType]:
        """Get timeframes ordered by hierarchy (lowest to highest)"""
        
        # Define timeframe order (in minutes)
        timeframe_minutes = {
            TimeframeType.TICK: 0.001,
            TimeframeType.SECOND_1: 1/60,
            TimeframeType.SECOND_5: 5/60,
            TimeframeType.SECOND_15: 15/60,
            TimeframeType.SECOND_30: 30/60,
            TimeframeType.MINUTE_1: 1,
            TimeframeType.MINUTE_2: 2,
            TimeframeType.MINUTE_3: 3,
            TimeframeType.MINUTE_5: 5,
            TimeframeType.MINUTE_15: 15,
            TimeframeType.MINUTE_30: 30,
            TimeframeType.HOUR_1: 60,
            TimeframeType.HOUR_2: 120,
            TimeframeType.HOUR_4: 240,
            TimeframeType.HOUR_6: 360,
            TimeframeType.HOUR_8: 480,
            TimeframeType.HOUR_12: 720,
            TimeframeType.DAY_1: 1440,
            TimeframeType.DAY_3: 4320,
            TimeframeType.WEEK_1: 10080,
            TimeframeType.MONTH_1: 43200,
            TimeframeType.QUARTER_1: 129600,
            TimeframeType.YEAR_1: 525600
        }
        
        # Sort configured timeframes by duration
        configured_timeframes = [tf_config.timeframe for tf_config in self.config.timeframes]
        return sorted(configured_timeframes, key=lambda tf: timeframe_minutes.get(tf, 0))
    
    def get_signal_stack(
        self,
        timeframe: TimeframeType,
        stack_size: int = None
    ) -> List[TimeframeSignal]:
        """Get a stack of recent signals from a timeframe"""
        
        stack_size = stack_size or self.config.max_stack_size
        
        if timeframe not in self.timeframe_signals:
            return []
        
        signals = list(self.timeframe_signals[timeframe])
        return signals[-stack_size:] if len(signals) >= stack_size else signals
    
    def detect_fractal_patterns(self) -> Dict[str, Any]:
        """Detect fractal patterns across timeframes"""
        
        if not self.config.enable_fractal_analysis:
            return {}
        
        # This would implement fractal analysis
        # For now, return placeholder
        return {
            'fractal_dimension': 1.5,
            'self_similarity': 0.7,
            'fractal_support_resistance': []
        }
    
    def calculate_timeframe_correlation(
        self,
        tf1: TimeframeType,
        tf2: TimeframeType,
        periods: int = 50
    ) -> float:
        """Calculate correlation between two timeframes"""
        
        if tf1 not in self.timeframe_signals or tf2 not in self.timeframe_signals:
            return 0.0
        
        signals1 = list(self.timeframe_signals[tf1])[-periods:]
        signals2 = list(self.timeframe_signals[tf2])[-periods:]
        
        if len(signals1) < 10 or len(signals2) < 10:
            return 0.0
        
        # Extract signal values
        values1 = [self._signal_to_numeric(s.signal) for s in signals1]
        values2 = [self._signal_to_numeric(s.signal) for s in signals2]
        
        # Align lengths
        min_len = min(len(values1), len(values2))
        values1 = values1[-min_len:]
        values2 = values2[-min_len:]
        
        if min_len < 5:
            return 0.0
        
        # Calculate correlation
        try:
            correlation = np.corrcoef(values1, values2)[0, 1]
            return correlation if not np.isnan(correlation) else 0.0
        except:
            return 0.0
    
    # ===========================================
    # PRIVATE METHODS
    # ===========================================
    
    def _get_recent_signals(self, lookback_periods: int) -> Dict[TimeframeType, List[TimeframeSignal]]:
        """Get recent signals from all timeframes"""
        
        recent_signals = {}
        
        for timeframe, signals in self.timeframe_signals.items():
            if signals:
                recent = list(signals)[-lookback_periods:]
                if recent:
                    recent_signals[timeframe] = recent
        
        return recent_signals
    
    def _analyze_signal_convergence(
        self,
        signals: Dict[TimeframeType, List[TimeframeSignal]]
    ) -> ConvergenceAnalysis:
        """Analyze convergence across timeframe signals"""
        
        if not signals:
            return ConvergenceAnalysis(
                convergence_type=ConvergenceType.MIXED_SIGNALS,
                convergence_score=0.0,
                participating_timeframes=[]
            )
        
        # Get latest signal from each timeframe
        latest_signals = {tf: signals_list[-1] for tf, signals_list in signals.items()}
        
        # Categorize signals
        bullish_tfs = []
        bearish_tfs = []
        neutral_tfs = []
        
        for tf, signal in latest_signals.items():
            signal_value = self._signal_to_numeric(signal.signal)
            
            if signal_value > 0.1:
                bullish_tfs.append(tf)
            elif signal_value < -0.1:
                bearish_tfs.append(tf)
            else:
                neutral_tfs.append(tf)
        
        # Determine convergence type
        total_tfs = len(latest_signals)
        bullish_ratio = len(bullish_tfs) / total_tfs
        bearish_ratio = len(bearish_tfs) / total_tfs
        
        if bullish_ratio >= 0.8:
            convergence_type = ConvergenceType.BULLISH_ALIGNMENT
        elif bearish_ratio >= 0.8:
            convergence_type = ConvergenceType.BEARISH_ALIGNMENT
        elif abs(bullish_ratio - bearish_ratio) <= 0.2:
            convergence_type = ConvergenceType.MIXED_SIGNALS
        else:
            convergence_type = ConvergenceType.DIVERGENCE
        
        # Calculate convergence score
        convergence_score = max(bullish_ratio, bearish_ratio)
        
        # Calculate strength metrics
        signal_values = [self._signal_to_numeric(s.signal) for s in latest_signals.values()]
        average_strength = np.mean(np.abs(signal_values))
        
        # Weight by timeframe importance
        weighted_values = []
        total_weight = 0
        for tf, signal in latest_signals.items():
            weight = self.timeframe_weights.get(tf, 1.0)
            weighted_values.append(self._signal_to_numeric(signal.signal) * weight)
            total_weight += weight
        
        weighted_strength = np.sum(weighted_values) / total_weight if total_weight > 0 else 0
        
        # Calculate consistency
        strength_consistency = 1.0 - (np.std(np.abs(signal_values)) / (average_strength + 1e-6))
        strength_consistency = max(0.0, min(1.0, strength_consistency))
        
        return ConvergenceAnalysis(
            convergence_type=convergence_type,
            convergence_score=convergence_score,
            participating_timeframes=list(latest_signals.keys()),
            bullish_timeframes=bullish_tfs,
            bearish_timeframes=bearish_tfs,
            neutral_timeframes=neutral_tfs,
            average_strength=average_strength,
            weighted_strength=weighted_strength,
            strength_consistency=strength_consistency,
            confidence=convergence_score * strength_consistency
        )
    
    def _generate_composite_signal(
        self,
        signals: Dict[TimeframeType, List[TimeframeSignal]],
        convergence: ConvergenceAnalysis
    ) -> IndicatorSignal:
        """Generate composite signal from multiple timeframes"""
        
        if not signals:
            return IndicatorSignal(
                signal_type=SignalType.NEUTRAL,
                strength=0.0,
                confidence=0.0,
                timestamp=datetime.now(timezone.utc),
                value=0.0
            )
        
        # Get latest signals
        latest_signals = {tf: signals_list[-1] for tf, signals_list in signals.items()}
        
        # Calculate weighted signal
        weighted_sum = 0.0
        total_weight = 0.0
        
        for tf, signal in latest_signals.items():
            weight = self.timeframe_weights.get(tf, 1.0)
            signal_value = self._signal_to_numeric(signal.signal)
            
            # Apply convergence weighting
            if convergence.convergence_type in [ConvergenceType.BULLISH_ALIGNMENT, ConvergenceType.BEARISH_ALIGNMENT]:
                weight *= 1.2  # Boost weight for aligned signals
            elif convergence.convergence_type == ConvergenceType.DIVERGENCE:
                weight *= 0.8  # Reduce weight for divergent signals
            
            weighted_sum += signal_value * weight
            total_weight += weight
        
        # Calculate composite value
        composite_value = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        # Determine signal direction and strength
        if composite_value > 0:
            abs_val = abs(composite_value)
            signal_type = SignalType.STRONG_BUY if abs_val > 0.7 else SignalType.BUY
        elif composite_value < 0:
            abs_val = abs(composite_value)
            signal_type = SignalType.STRONG_SELL if abs_val > 0.7 else SignalType.SELL
        else:
            abs_val = 0.0
            signal_type = SignalType.NEUTRAL
        
        strength = max(0.0, min(1.0, abs_val))
        
        return IndicatorSignal(
            signal_type=signal_type,
            strength=strength,
            confidence=convergence.confidence,
            timestamp=datetime.now(timezone.utc),
            value=composite_value,
            normalized_value=composite_value
        )
    
    def _calculate_composite_strength(self, signals: Dict[TimeframeType, List[TimeframeSignal]]) -> float:
        """Calculate composite signal strength"""
        
        if not signals:
            return 0.0
        
        latest_signals = {tf: signals_list[-1] for tf, signals_list in signals.items()}
        
        # Calculate weighted strength
        weighted_strength = 0.0
        total_weight = 0.0
        
        for tf, signal in latest_signals.items():
            weight = self.timeframe_weights.get(tf, 1.0)
            strength_value = float(getattr(signal.signal, "strength", 0.0) or 0.0)
            
            weighted_strength += strength_value * weight
            total_weight += weight
        
        return weighted_strength / total_weight if total_weight > 0 else 0.0
    
    def _calculate_composite_confidence(self, signals: Dict[TimeframeType, List[TimeframeSignal]]) -> float:
        """Calculate composite confidence"""
        
        if not signals:
            return 0.0
        
        latest_signals = {tf: signals_list[-1] for tf, signals_list in signals.items()}
        
        # Calculate weighted confidence
        weighted_confidence = 0.0
        total_weight = 0.0
        
        for tf, signal in latest_signals.items():
            weight = self.timeframe_weights.get(tf, 1.0)
            confidence = signal.confidence or signal.signal.confidence
            
            weighted_confidence += confidence * weight
            total_weight += weight
        
        return weighted_confidence / total_weight if total_weight > 0 else 0.0
    
    def _calculate_risk_adjusted_signal(self, mtf_signal: MultiTimeframeSignal) -> float:
        """Calculate risk-adjusted signal value"""
        
        base_signal = self._signal_to_numeric(mtf_signal.primary_signal)
        confidence = mtf_signal.composite_confidence
        convergence_score = mtf_signal.convergence_analysis.convergence_score
        
        # Risk adjustment factors
        confidence_factor = confidence
        convergence_factor = convergence_score
        
        # Apply risk adjustment
        risk_adjusted = base_signal * confidence_factor * convergence_factor
        
        return risk_adjusted
    
    def _find_optimal_entry_timeframe(self, signals: Dict[TimeframeType, List[TimeframeSignal]]) -> Optional[TimeframeType]:
        """Find optimal timeframe for entry"""
        
        if not signals:
            return None
        
        # Score each timeframe for entry timing
        timeframe_scores = {}
        
        for tf, signal_list in signals.items():
            if not signal_list:
                continue
            
            latest_signal = signal_list[-1]
            
            # Score based on signal strength, confidence, and timeframe characteristics
            strength_score = float(getattr(latest_signal.signal, "strength", 0.0) or 0.0)
            confidence_score = latest_signal.confidence or latest_signal.signal.confidence
            
            # Lower timeframes better for precise entry
            tf_hierarchy = self.get_timeframe_hierarchy()
            tf_index = tf_hierarchy.index(tf) if tf in tf_hierarchy else len(tf_hierarchy)
            timing_score = 1.0 / (tf_index + 1)  # Higher score for lower timeframes
            
            total_score = (strength_score * 0.4 + confidence_score * 0.4 + timing_score * 0.2)
            timeframe_scores[tf] = total_score
        
        # Return timeframe with highest score
        if timeframe_scores:
            return max(timeframe_scores, key=timeframe_scores.get)
        
        return None
    
    def _find_optimal_exit_timeframe(self, signals: Dict[TimeframeType, List[TimeframeSignal]]) -> Optional[TimeframeType]:
        """Find optimal timeframe for exit"""
        
        if not signals:
            return None
        
        # For exits, higher timeframes are often better for trend confirmation
        timeframe_scores = {}
        
        for tf, signal_list in signals.items():
            if not signal_list:
                continue
            
            latest_signal = signal_list[-1]
            
            # Score based on signal strength and timeframe characteristics
            strength_score = float(getattr(latest_signal.signal, "strength", 0.0) or 0.0)
            confidence_score = latest_signal.confidence or latest_signal.signal.confidence
            
            # Higher timeframes better for exit confirmation
            tf_hierarchy = self.get_timeframe_hierarchy()
            tf_index = tf_hierarchy.index(tf) if tf in tf_hierarchy else 0
            timing_score = (tf_index + 1) / len(tf_hierarchy)  # Higher score for higher timeframes
            
            total_score = (strength_score * 0.3 + confidence_score * 0.3 + timing_score * 0.4)
            timeframe_scores[tf] = total_score
        
        # Return timeframe with highest score
        if timeframe_scores:
            return max(timeframe_scores, key=timeframe_scores.get)
        
        return None
    
    def _validate_signal(self, signal: TimeframeSignal) -> Tuple[bool, float]:
        """Validate a timeframe signal"""
        
        validation_score = 1.0
        is_valid = True
        
        # Check signal completeness
        if not signal.signal or getattr(signal.signal, "signal_type", None) is None:
            validation_score *= 0.5
            is_valid = False
        
        # Apply minimum strength threshold per timeframe
        try:
            min_threshold = next((cfg.min_signal_strength for cfg in self.config.timeframes if cfg.timeframe == signal.timeframe), 0.0)
        except Exception:
            min_threshold = 0.0
        if float(getattr(signal.signal, "strength", 0.0) or 0.0) < float(min_threshold):
            validation_score *= 0.7
        
        # Check timestamp recency
        if signal.timestamp:
            age_minutes = (datetime.now(timezone.utc) - signal.timestamp).total_seconds() / 60
            if age_minutes > 60:  # Signal older than 1 hour
                validation_score *= max(0.1, 1.0 - age_minutes / 1440)  # Decay over 24 hours
        
        # Check confidence level
        confidence = signal.confidence or signal.signal.confidence
        if confidence < 0.3:
            validation_score *= 0.7
        
        # Noise level check
        if hasattr(signal, 'noise_level') and signal.noise_level > 0.5:
            validation_score *= 0.6
        
        return is_valid and validation_score > 0.3, validation_score
    
    def _initialize_timeframe_weights(self):
        """Initialize timeframe weights based on configuration"""
        
        if self.config.weighting_method == SignalWeight.EQUAL:
            # Equal weights
            for tf_config in self.config.timeframes:
                self.timeframe_weights[tf_config.timeframe] = 1.0
        
        elif self.config.weighting_method == SignalWeight.TIMEFRAME_WEIGHTED:
            # Weight by timeframe hierarchy
            hierarchy = self.get_timeframe_hierarchy()
            for i, tf in enumerate(hierarchy):
                # Higher timeframes get more weight
                weight = 1.0 + (i / len(hierarchy)) * (self.config.higher_tf_bias - 1.0)
                self.timeframe_weights[tf] = weight
        
        else:
            # Default to configured weights
            for tf_config in self.config.timeframes:
                self.timeframe_weights[tf_config.timeframe] = tf_config.weight
    
    def _update_performance_metrics(self):
        """Update performance metrics for adaptive weighting"""
        
        if self.config.weighting_method != SignalWeight.ADAPTIVE:
            return
        
        # This would implement performance-based weight adjustment
        # For now, maintain current weights
        pass
    
    def _create_empty_signal(self) -> MultiTimeframeSignal:
        """Create empty multi-timeframe signal"""
        
        return MultiTimeframeSignal(
            primary_signal=IndicatorSignal(
                signal_type=SignalType.NEUTRAL,
                strength=0.0,
                confidence=0.0,
                timestamp=datetime.now(timezone.utc),
                value=0.0
            ),
            convergence_analysis=ConvergenceAnalysis(
                convergence_type=ConvergenceType.MIXED_SIGNALS,
                convergence_score=0.0,
                participating_timeframes=[]
            ),
            timeframe_signals={}
        )
    
    def _signal_to_numeric(self, signal: IndicatorSignal) -> float:
        """Convert signal to numeric value"""
        
        if not signal or getattr(signal, "signal_type", None) is None:
            return 0.0
        
        # Determine direction from signal type
        if signal.signal_type in (SignalType.BUY, SignalType.STRONG_BUY):
            direction = 1.0
        elif signal.signal_type in (SignalType.SELL, SignalType.STRONG_SELL):
            direction = -1.0
        else:
            direction = 0.0
        
        strength_multiplier = float(getattr(signal, "strength", 0.0) or 0.0)
        confidence_multiplier = float(getattr(signal, "confidence", 0.0) or 0.5)
        
        return direction * strength_multiplier * confidence_multiplier
    
    def _strength_to_numeric(self, strength: float) -> float:
        """Normalize strength float to [0, 1]"""
        try:
            return max(0.0, min(1.0, float(strength)))
        except Exception:
            return 0.0


# Helper function to create default multi-timeframe configuration
def create_default_mtf_config() -> MultiTimeframeConfig:
    """Create default multi-timeframe configuration"""
    
    timeframes = [
        TimeframeConfig(TimeframeType.MINUTE_5, weight=0.8),
        TimeframeConfig(TimeframeType.MINUTE_15, weight=1.0),
        TimeframeConfig(TimeframeType.HOUR_1, weight=1.2),
        TimeframeConfig(TimeframeType.HOUR_4, weight=1.5),
        TimeframeConfig(TimeframeType.DAY_1, weight=2.0)
    ]
    
    return MultiTimeframeConfig(
        timeframes=timeframes,
        primary_timeframe=TimeframeType.HOUR_1,
        weighting_method=SignalWeight.HYBRID,
        higher_tf_bias=1.5
    )


# Export classes
__all__ = [
    'MultiTimeframeEngine',
    'MultiTimeframeConfig',
    'TimeframeConfig',
    'MultiTimeframeSignal',
    'TimeframeSignal',
    'ConvergenceAnalysis',
    'TimeframeType',
    'ConvergenceType',
    'SignalWeight',
    'create_default_mtf_config'
]