"""Market Regime Adaptation Engine

Advanced market regime detection and adaptive parameter adjustment system
for all technical indicators. Provides institutional-grade regime analysis
with automatic parameter optimization.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, NamedTuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from collections import deque
import math
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from .core_indicator_base import MarketRegime, RiskLevel
from nautilus_trader_engine.indicators.consolidated_indicators import ConsolidatedIndicators



class RegimeDetectionMethod(Enum):
    """Regime detection methods"""
    VOLATILITY_BASED = "volatility_based"
    TREND_BASED = "trend_based"
    VOLUME_BASED = "volume_based"
    CORRELATION_BASED = "correlation_based"
    MACHINE_LEARNING = "machine_learning"
    HYBRID = "hybrid"
    MARKOV_SWITCHING = "markov_switching"


class RegimeTransition(Enum):
    """Regime transition states"""
    STABLE = "stable"
    TRANSITIONING = "transitioning"
    UNCERTAIN = "uncertain"
    REVERTING = "reverting"


@dataclass
class RegimeCharacteristics:
    """Characteristics of a market regime"""
    volatility_level: float = 0.0
    trend_strength: float = 0.0
    trend_direction: float = 0.0
    volume_profile: float = 0.0
    correlation_level: float = 0.0
    momentum_persistence: float = 0.0
    mean_reversion_tendency: float = 0.0
    
    # Statistical properties
    skewness: float = 0.0
    kurtosis: float = 0.0
    autocorrelation: float = 0.0
    
    # Market microstructure
    bid_ask_spread: float = 0.0
    order_flow_imbalance: float = 0.0
    institutional_activity: float = 0.0


@dataclass
class RegimeAdaptationConfig:
    """Configuration for regime adaptation"""
    # Detection parameters
    detection_method: RegimeDetectionMethod = RegimeDetectionMethod.HYBRID
    lookback_period: int = 252  # 1 year
    min_regime_duration: int = 20  # Minimum days in regime
    confidence_threshold: float = 0.7
    
    # Adaptation parameters
    adaptation_speed: float = 0.1  # How quickly to adapt (0-1)
    parameter_bounds: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    enable_dynamic_bounds: bool = True
    
    # Regime-specific settings
    regime_parameters: Dict[MarketRegime, Dict[str, float]] = field(default_factory=dict)
    
    # Advanced features
    enable_regime_prediction: bool = True
    enable_transition_detection: bool = True
    enable_regime_clustering: bool = True
    
    # Performance optimization
    update_frequency: int = 1  # Update every N periods
    cache_regime_features: bool = True


@dataclass
class RegimeState:
    """Current regime state information"""
    current_regime: MarketRegime
    confidence: float
    duration: int  # Days in current regime
    transition_state: RegimeTransition
    
    # Regime characteristics
    characteristics: RegimeCharacteristics
    
    # Transition probabilities
    transition_probabilities: Dict[MarketRegime, float] = field(default_factory=dict)
    
    # Historical context
    previous_regime: Optional[MarketRegime] = None
    regime_history: List[Tuple[MarketRegime, datetime, int]] = field(default_factory=list)
    
    # Prediction
    predicted_next_regime: Optional[MarketRegime] = None
    prediction_confidence: float = 0.0
    expected_regime_duration: int = 0
    
    # Metadata
    last_update: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    regime_start_date: Optional[datetime] = None

class RegimeAdaptationEngine:
    """Regime adaptation engine for market analysis"""

    def __init__(self, config: RegimeAdaptationConfig = None):
        self.config = config or RegimeAdaptationConfig()
        
        # Historical data storage
        self.prices: List[float] = []
        self.volumes: List[float] = []
        self.timestamps: List[datetime] = []
        self.returns: List[float] = []
        
        # Current state
        self.current_state = RegimeState(
            current_regime=MarketRegime.UNKNOWN,
            confidence=0.0,
            duration=0,
            transition_state=RegimeTransition.UNCERTAIN,
            characteristics=RegimeCharacteristics()
        )
        
        # Performance and tracking
        self.regime_performance: Dict[MarketRegime, Dict[str, float]] = {}
        self.adaptation_history: deque = deque(maxlen=1000)
        
        # Transition matrix
        self.transition_matrix: np.ndarray = np.zeros((len(MarketRegime), len(MarketRegime)))
        self.regime_durations: Dict[MarketRegime, List[int]] = {regime: [] for regime in MarketRegime}
        
        # Parameter adaptation cache
        self.adapted_parameters: Dict[str, Dict[str, float]] = {}
        self.parameter_history: deque = deque(maxlen=500)
        
        # Initialize default regime parameters
        self._initialize_default_parameters()
        
        # Update counter for performance optimization
        self.update_counter = 0
    
    def update(
        self,
        price: float,
        volume: float = 0.0,
        timestamp: datetime = None,
        additional_features: Dict[str, float] = None
    ) -> RegimeState:
        """Update regime detection with new market data"""
        
        timestamp = timestamp or datetime.now(timezone.utc)
        
        # Store market data
        self.prices.append(price)
        self.volumes.append(volume)
        self.timestamps.append(timestamp)
        
        # Calculate returns
        if len(self.prices) >= 2:
            returns = (price - self.prices[-2]) / self.prices[-2]
            self.returns.append(returns)
        
        # Update regime detection (with frequency control)
        self.update_counter += 1
        if self.update_counter % self.config.update_frequency == 0:
            self._detect_regime(additional_features)
            self._update_transition_probabilities()
            if self.config.enable_regime_prediction:
                self._predict_next_regime()
        
        return self.current_state
    
    def get_adapted_parameters(
        self,
        indicator_name: str,
        base_parameters: Dict[str, float]
    ) -> Dict[str, float]:
        """Get regime-adapted parameters for an indicator"""
        
        if self.current_state.current_regime == MarketRegime.UNKNOWN:
            return base_parameters
        
        # Get regime-specific adaptations
        regime_adaptations = self.config.regime_parameters.get(
            self.current_state.current_regime, {}
        )
        
        # Apply generic multipliers
        multipliers = self.get_regime_multipliers()
        adapted = base_parameters.copy()
        for key, value in base_parameters.items():
            adapted[key] = self._adapt_parameter(key, value, indicator_name)
        return adapted
    
    def _update_regime_state(self, new_regime: MarketRegime, confidence: float, features: Dict[str, float]):
        """Update the current regime state"""
        
        previous_regime = self.current_state.current_regime
        
        # Check for regime change
        if new_regime != previous_regime:
            # Record regime change
            if previous_regime != MarketRegime.UNKNOWN:
                self.current_state.regime_history.append(
                    (previous_regime, datetime.now(timezone.utc), self.current_state.duration)
                )
                
                # Update regime durations for statistics
                self.regime_durations[previous_regime].append(self.current_state.duration)
            
            # Update state
            self.current_state.previous_regime = previous_regime
            self.current_state.current_regime = new_regime
            self.current_state.duration = 1
            self.current_state.regime_start_date = datetime.now(timezone.utc)
            self.current_state.transition_state = RegimeTransition.TRANSITIONING
        else:
            # Same regime, increment duration
            self.current_state.duration += 1
            
            # Update transition state based on duration
            if self.current_state.duration > self.config.min_regime_duration:
                self.current_state.transition_state = RegimeTransition.STABLE
            elif self.current_state.duration > 5:
                self.current_state.transition_state = RegimeTransition.UNCERTAIN
        
        # Update confidence and characteristics
        self.current_state.confidence = confidence
        self.current_state.characteristics = self._create_regime_characteristics(features)
        self.current_state.last_update = datetime.now(timezone.utc)

    def get_regime_multipliers(self) -> Dict[str, float]:
        """Get regime-based multipliers for various indicator components"""
        
        regime = self.current_state.current_regime
        confidence = self.current_state.confidence
        
        multipliers = {
            'sensitivity': 1.0,
            'smoothing': 1.0,
            'threshold': 1.0,
            'period': 1.0,
            'volatility_adjustment': 1.0,
            'trend_adjustment': 1.0,
            'volume_weight': 1.0
        }
        
        # Regime-specific adjustments
        if regime == MarketRegime.HIGH_VOLATILITY:
            multipliers.update({
                'sensitivity': 0.7,
                'smoothing': 1.3,
                'threshold': 1.2,
                'period': 1.1
            })
        elif regime == MarketRegime.LOW_VOLATILITY:
            multipliers.update({
                'sensitivity': 1.3,
                'smoothing': 0.8,
                'threshold': 0.9,
                'period': 0.9
            })
        elif regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
            multipliers.update({
                'sensitivity': 1.1,
                'smoothing': 0.9,
                'trend_adjustment': 1.2,
                'period': 0.95
            })
        elif regime == MarketRegime.SIDEWAYS:
            multipliers.update({
                'sensitivity': 0.9,
                'smoothing': 1.1,
                'threshold': 1.1,
                'period': 1.05
            })
        elif regime == MarketRegime.CRISIS:
            multipliers.update({
                'sensitivity': 0.6,
                'smoothing': 1.5,
                'threshold': 1.4,
                'period': 1.2,
                'volatility_adjustment': 1.5
            })
        
        # Apply confidence weighting (blend toward neutral 1.0)
        for key, value in multipliers.items():
            if key != 'volume_weight':
                multipliers[key] = 1.0 + (value - 1.0) * confidence
        
        return multipliers

    def should_recalibrate_indicator(self, indicator_name: str) -> bool:
        """Determine if an indicator should be recalibrated due to regime change"""
        # Regime just changed and still within minimum duration
        if (self.current_state.duration <= self.config.min_regime_duration and 
            self.current_state.previous_regime is not None):
            return True
        # Confidence low
        if self.current_state.confidence < self.config.confidence_threshold:
            return True
        # Transitioning
        if self.current_state.transition_state == RegimeTransition.TRANSITIONING:
            return True
        return False

    def get_regime_forecast(self, horizon: int = 20) -> Dict[MarketRegime, float]:
        """Get regime probability forecast for specified horizon"""
        if not self.config.enable_regime_prediction:
            return {regime: 1.0/len(MarketRegime) for regime in MarketRegime}
        current_regime_idx = list(MarketRegime).index(self.current_state.current_regime)
        transition_power = np.linalg.matrix_power(self.transition_matrix, horizon)
        forecast_probs = transition_power[current_regime_idx]
        regime_forecast = {regime: float(forecast_probs[i]) for i, regime in enumerate(MarketRegime)}
        return regime_forecast

    # ===========================================
    # PRIVATE METHODS
    # ===========================================

    def _detect_regime(self, additional_features: Dict[str, float] = None):
        """Detect current market regime"""
        if len(self.returns) < 20:
            return
        features = self._calculate_regime_features(additional_features)
        if self.config.detection_method == RegimeDetectionMethod.VOLATILITY_BASED:
            regime, confidence = self._detect_volatility_regime(features)
        elif self.config.detection_method == RegimeDetectionMethod.TREND_BASED:
            regime, confidence = self._detect_trend_regime(features)
        elif self.config.detection_method == RegimeDetectionMethod.VOLUME_BASED:
            regime, confidence = self._detect_volume_regime(features)
        elif self.config.detection_method == RegimeDetectionMethod.MACHINE_LEARNING:
            regime, confidence = self._detect_ml_regime(features)
        elif self.config.detection_method == RegimeDetectionMethod.HYBRID:
            regime, confidence = self._detect_hybrid_regime(features)
        else:
            regime, confidence = self._detect_hybrid_regime(features)
        self._update_regime_state(regime, confidence, features)

    def _calculate_regime_features(self, additional_features: Dict[str, float] = None) -> Dict[str, float]:
        """Calculate features for regime detection"""
        if len(self.returns) < 20:
            return {}
        returns_array = np.array(list(self.returns)[-60:])
        prices_array = np.array(list(self.prices)[-60:])
        volumes_array = np.array(list(self.volumes)[-60:]) if self.volumes else np.ones(len(returns_array))
        features: Dict[str, float] = {}
        # Volatility features
        features['volatility'] = float(np.std(returns_array))
        features['volatility_ma'] = float(np.mean([np.std(returns_array[i:i+20]) for i in range(0, max(len(returns_array)-20, 1), 5)]))
        features['volatility_trend'] = float(np.corrcoef(np.arange(len(returns_array)), np.abs(returns_array))[0, 1]) if len(returns_array) > 1 else 0.0
        # Trend features
        features['trend_strength'] = float(abs(np.corrcoef(np.arange(len(prices_array)), prices_array)[0, 1])) if len(prices_array) > 1 else 0.0
        features['trend_direction'] = float(np.sign(prices_array[-1] - prices_array[0])) if len(prices_array) > 1 else 0.0
        features['trend_consistency'] = float(self._calculate_trend_consistency(returns_array))
        # Momentum features
        if len(returns_array) >= 10 and np.std(returns_array[-10:]) > 0:
            features['momentum'] = float(np.mean(returns_array[-10:]) / np.std(returns_array[-10:]))
        else:
            features['momentum'] = 0.0
        features['momentum_persistence'] = float(self._calculate_momentum_persistence(returns_array))
        # Volume features
        if len(volumes_array) > 1:
            features['volume_trend'] = float(np.corrcoef(np.arange(len(volumes_array)), volumes_array)[0, 1])
            features['volume_volatility'] = float(np.std(volumes_array) / np.mean(volumes_array)) if np.mean(volumes_array) > 0 else 0.0
        # Statistical features
        features['skewness'] = float(stats.skew(returns_array)) if len(returns_array) > 2 else 0.0
        features['kurtosis'] = float(stats.kurtosis(returns_array)) if len(returns_array) > 3 else 0.0
        features['autocorrelation'] = float(self._calculate_autocorrelation(returns_array))
        # Mean reversion
        features['mean_reversion'] = float(self._calculate_mean_reversion_tendency(returns_array))
        # Hurst exponent
        features['hurst_exponent'] = float(self._calculate_hurst_exponent(prices_array)) if len(prices_array) > 10 else 0.5
        # Additional features
        if additional_features:
            features.update(additional_features)
        return features

    def _detect_volatility_regime(self, features: Dict[str, float]) -> Tuple[MarketRegime, float]:
        """Detect regime based on volatility characteristics"""
        volatility = features.get('volatility', 0.0)
        vol_ma = features.get('volatility_ma', volatility)
        high_vol_threshold = 0.03
        low_vol_threshold = 0.01
        crisis_threshold = 0.05
        confidence = min(abs(volatility - vol_ma) / vol_ma * 10, 1.0) if vol_ma > 0 else 0.5
        if volatility > crisis_threshold:
            return MarketRegime.CRISIS, confidence
        elif volatility > high_vol_threshold:
            return MarketRegime.HIGH_VOLATILITY, confidence
        elif volatility < low_vol_threshold:
            return MarketRegime.LOW_VOLATILITY, confidence
        else:
            trend_strength = features.get('trend_strength', 0.0)
            if trend_strength > 0.5:
                trend_direction = features.get('trend_direction', 0.0)
                if trend_direction > 0:
                    return MarketRegime.TRENDING_UP, confidence
                else:
                    return MarketRegime.TRENDING_DOWN, confidence
            else:
                return MarketRegime.SIDEWAYS, confidence

    def _detect_trend_regime(self, features: Dict[str, float]) -> Tuple[MarketRegime, float]:
        """Detect regime based on trend characteristics"""
        trend_strength = features.get('trend_strength', 0.0)
        trend_direction = features.get('trend_direction', 0.0)
        trend_consistency = features.get('trend_consistency', 0.0)
        confidence = min(trend_strength + trend_consistency, 1.0)
        if trend_strength > 0.7 and trend_consistency > 0.6:
            if trend_direction > 0:
                return MarketRegime.TRENDING_UP, confidence
            else:
                return MarketRegime.TRENDING_DOWN, confidence
        elif trend_strength < 0.3:
            return MarketRegime.SIDEWAYS, confidence
        else:
            volatility = features.get('volatility', 0.0)
            if volatility > 0.03:
                return MarketRegime.HIGH_VOLATILITY, confidence * 0.8
            else:
                return MarketRegime.LOW_VOLATILITY, confidence * 0.8

    def _detect_volume_regime(self, features: Dict[str, float]) -> Tuple[MarketRegime, float]:
        """Detect regime based on volume characteristics"""
        # For now, defer to hybrid approach
        return self._detect_hybrid_regime(features)

    def _detect_ml_regime(self, features: Dict[str, float]) -> Tuple[MarketRegime, float]:
        """Detect regime using machine learning (placeholder)"""
        # Without a trained classifier available, fall back to hybrid
        return self._detect_hybrid_regime(features)

    def _detect_hybrid_regime(self, features: Dict[str, float]) -> Tuple[MarketRegime, float]:
        """Hybrid approach combining multiple methods"""
        vol_regime, vol_conf = self._detect_volatility_regime(features)
        trend_regime, trend_conf = self._detect_trend_regime(features)
        vol_weight = 0.4
        trend_weight = 0.6
        regime_scores = {regime: 0.0 for regime in MarketRegime}
        regime_scores[vol_regime] += vol_weight * vol_conf
        regime_scores[trend_regime] += trend_weight * trend_conf
        best_regime = max(regime_scores, key=regime_scores.get)
        best_confidence = float(regime_scores[best_regime])
        return best_regime, best_confidence

    def _create_regime_characteristics(self, features: Dict[str, float]) -> RegimeCharacteristics:
        """Create regime characteristics from features"""
        return RegimeCharacteristics(
            volatility_level=features.get('volatility', 0.0),
            trend_strength=features.get('trend_strength', 0.0),
            trend_direction=features.get('trend_direction', 0.0),
            volume_profile=features.get('volume_trend', 0.0),
            momentum_persistence=features.get('momentum_persistence', 0.0),
            mean_reversion_tendency=features.get('mean_reversion', 0.0),
            skewness=features.get('skewness', 0.0),
            kurtosis=features.get('kurtosis', 0.0),
            autocorrelation=features.get('autocorrelation', 0.0)
        )

    def _adapt_parameter(self, param_name: str, base_value: float, indicator_name: str) -> float:
        """Adapt a parameter based on current regime"""
        multipliers = self.get_regime_multipliers()
        param_multiplier_map = {
            'period': 'period',
            'length': 'period',
            'window': 'period',
            'smoothing': 'smoothing',
            'alpha': 'sensitivity',
            'threshold': 'threshold',
            'upper_threshold': 'threshold',
            'lower_threshold': 'threshold',
            'overbought': 'threshold',
            'oversold': 'threshold'
        }
        multiplier_type = param_multiplier_map.get(param_name.lower(), 'sensitivity')
        multiplier = multipliers.get(multiplier_type, 1.0)
        adapted_value = base_value * multiplier
        bounds_key = f"{indicator_name}_{param_name}"
        if bounds_key in self.config.parameter_bounds:
            min_val, max_val = self.config.parameter_bounds[bounds_key]
            adapted_value = max(min_val, min(adapted_value, max_val))
        return adapted_value

    def _update_transition_probabilities(self):
        """Update regime transition probability matrix"""
        if len(self.current_state.regime_history) < 2:
            return
        transition_counts = np.zeros((len(MarketRegime), len(MarketRegime)))
        for i in range(len(self.current_state.regime_history) - 1):
            from_regime = self.current_state.regime_history[i][0]
            to_regime = self.current_state.regime_history[i + 1][0]
            from_idx = list(MarketRegime).index(from_regime)
            to_idx = list(MarketRegime).index(to_regime)
            transition_counts[from_idx, to_idx] += 1
        for i in range(len(MarketRegime)):
            row_sum = transition_counts[i].sum()
            if row_sum > 0:
                self.transition_matrix[i] = transition_counts[i] / row_sum

    def _predict_next_regime(self):
        """Predict the next likely regime"""
        if self.current_state.current_regime == MarketRegime.UNKNOWN:
            return
        current_regime_idx = list(MarketRegime).index(self.current_state.current_regime)
        transition_probs = self.transition_matrix[current_regime_idx]
        if transition_probs.sum() > 0:
            next_regime_idx = int(np.argmax(transition_probs))
            next_regime = list(MarketRegime)[next_regime_idx]
            prediction_confidence = float(transition_probs[next_regime_idx])
            self.current_state.predicted_next_regime = next_regime
            self.current_state.prediction_confidence = prediction_confidence
            if next_regime in self.regime_durations and self.regime_durations[next_regime]:
                self.current_state.expected_regime_duration = int(np.mean(self.regime_durations[next_regime]))

    def _initialize_default_parameters(self):
        """Initialize default regime-specific parameters"""
        default_params = {
            MarketRegime.HIGH_VOLATILITY: {
                'rsi_period': 21,
                'macd_fast': 15,
                'macd_slow': 30,
                'bb_period': 25,
                'atr_period': 21
            },
            MarketRegime.LOW_VOLATILITY: {
                'rsi_period': 10,
                'macd_fast': 8,
                'macd_slow': 17,
                'bb_period': 15,
                'atr_period': 10
            },
            MarketRegime.TRENDING_UP: {
                'rsi_overbought': 80,
                'rsi_oversold': 40,
                'macd_signal': 8
            },
            MarketRegime.TRENDING_DOWN: {
                'rsi_overbought': 60,
                'rsi_oversold': 20,
                'macd_signal': 8
            },
            MarketRegime.SIDEWAYS: {
                'rsi_overbought': 70,
                'rsi_oversold': 30,
                'bb_std_dev': 2.5
            },
            MarketRegime.CRISIS: {
                'rsi_period': 30,
                'macd_fast': 20,
                'macd_slow': 40,
                'bb_period': 30,
                'atr_period': 30
            }
        }
        self.config.regime_parameters = default_params

    # Helper methods for feature calculation
    def _calculate_trend_consistency(self, returns: np.ndarray) -> float:
        """Calculate trend consistency score"""
        if len(returns) < 10:
            return 0.0
        signs = np.sign(returns)
        consistency_score = 0.0
        current_streak = 1
        for i in range(1, len(signs)):
            if signs[i] == signs[i-1] and signs[i] != 0:
                current_streak += 1
            else:
                consistency_score += current_streak / len(signs)
                current_streak = 1
        return float(min(consistency_score, 1.0))

    def _calculate_momentum_persistence(self, returns: np.ndarray) -> float:
        """Calculate momentum persistence"""
        if len(returns) < 5:
            return 0.0
        momentum_periods = []
        for i in range(4, len(returns)):
            momentum = float(np.mean(returns[i-4:i+1]))
            momentum_periods.append(momentum)
        if len(momentum_periods) < 2:
            return 0.0
        return float(abs(np.corrcoef(momentum_periods[:-1], momentum_periods[1:])[0, 1]))

    def _calculate_autocorrelation(self, returns: np.ndarray, lag: int = 1) -> float:
        """Calculate autocorrelation of returns"""
        if len(returns) <= lag:
            return 0.0
        return float(np.corrcoef(returns[:-lag], returns[lag:])[0, 1])

    def _calculate_mean_reversion_tendency(self, returns: np.ndarray) -> float:
        """Calculate mean reversion tendency"""
        if len(returns) < 10:
            return 0.0
        mean_return = float(np.mean(returns))
        deviations = returns - mean_return
        reversion_score = 0.0
        count = 0
        std_ret = float(np.std(returns))
        for i in range(len(deviations) - 1):
            if abs(deviations[i]) > std_ret and std_ret > 0:
                if np.sign(deviations[i]) != np.sign(deviations[i + 1]):
                    reversion_score += 1
                count += 1
        return float(reversion_score / count) if count > 0 else 0.0

    def _calculate_hurst_exponent(self, prices: np.ndarray) -> float:
        """Calculate Hurst exponent for mean reversion/trending behavior"""
        if len(prices) < 20:
            return 0.5
        lags = range(2, min(20, max(len(prices) // 4, 3)))
        tau = [float(np.sqrt(np.std(np.subtract(prices[lag:], prices[:-lag])))) for lag in lags]
        if len(tau) < 2:
            return 0.5
        log_lags = np.log(list(lags))
        log_tau = np.log(tau)
        hurst = float(np.polyfit(log_lags, log_tau, 1)[0])
        return max(0.0, min(1.0, hurst))

# Export the regime adaptation engine
__all__ = [
    'RegimeAdaptationEngine',
    'RegimeAdaptationConfig',
    'RegimeState',
    'RegimeCharacteristics',
    'RegimeDetectionMethod',
    'RegimeTransition'
]