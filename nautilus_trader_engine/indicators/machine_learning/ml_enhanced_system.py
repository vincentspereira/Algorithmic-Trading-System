"""ML-Enhanced Trading System

Advanced machine learning and AI enhancements for technical indicators including:
- Dynamic market regime detection with supervisor models
- Meta-labeling system for signal filtering
- Real-time probabilistic forecasting with Monte Carlo simulation
- Factor-based signal validation and cross-asset awareness
- Signal decay modeling and confidence scoring
- Reinforcement learning integration framework

Implements the four pillars of ML/AI enhancement:
1. Advanced ML/AI Integration
2. Contextual & Cross-Asset Awareness
3. Statistical & Probabilistic Rigor
4. Performance & Execution Integration
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple, Union
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
import json
import pickle
from abc import ABC, abstractmethod

try:
    from sklearn.ensemble import RandomForestClassifier, IsolationForest
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, precision_score, recall_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("Warning: scikit-learn not available. ML features will be limited.")

from .enhanced_base import (
    VolumeWeightedIndicator,
    IndicatorConfig,
    IndicatorResult,
    IndicatorType,
    SignalType
)

try:
    from utils.logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
from nautilus_trader_engine.indicators.consolidated_indicators import ConsolidatedIndicators

    logger = logging.getLogger(__name__)

class MarketRegime(Enum):
    """Market regime classifications"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    BREAKOUT = "breakout"
    REVERSAL = "reversal"
    UNKNOWN = "unknown"

class SignalQuality(Enum):
    """Signal quality classifications"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    FILTERED = "filtered"

@dataclass
class MLConfig:
    """Configuration for ML enhancements"""
    enable_regime_detection: bool = True
    enable_meta_labeling: bool = True
    enable_probabilistic_forecasting: bool = True
    enable_factor_validation: bool = True
    enable_signal_decay: bool = True
    
    # Model parameters
    regime_lookback_period: int = 100
    meta_labeling_period: int = 50
    monte_carlo_simulations: int = 1000
    confidence_threshold: float = 0.7
    
    # Factor validation
    correlation_threshold: float = 0.6
    factor_weight: float = 0.3
    
    # Signal decay
    signal_half_life: float = 10.0  # periods
    decay_function: str = "exponential"  # exponential, linear, power

@dataclass
class MarketRegimeData:
    """Market regime detection data"""
    regime: MarketRegime
    confidence: float
    volatility: float
    trend_strength: float
    momentum: float
    volume_profile: str
    timestamp: datetime
    features: Dict[str, float] = field(default_factory=dict)

@dataclass
class MetaLabelResult:
    """Meta-labeling result"""
    signal_quality: SignalQuality
    predicted_profitability: float
    confidence: float
    risk_score: float
    recommended_position_size: float
    features_used: List[str]
    model_version: str

@dataclass
class ProbabilisticForecast:
    """Probabilistic forecast result"""
    mean_prediction: float
    std_prediction: float
    confidence_intervals: Dict[str, Tuple[float, float]]  # e.g., {'95%': (lower, upper)}
    probability_distributions: Dict[str, float]  # e.g., {'above_vwap': 0.75}
    scenario_probabilities: Dict[str, float]
    monte_carlo_paths: Optional[np.ndarray] = None

class MarketRegimeDetector:
    """Dynamic market regime detection system"""
    
    def __init__(self, config: MLConfig):
        self.config = config
        self.regime_history = deque(maxlen=config.regime_lookback_period * 2)
        self.feature_history = deque(maxlen=config.regime_lookback_period * 2)
        
        # Initialize models if sklearn is available
        if SKLEARN_AVAILABLE:
            self.regime_classifier = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            self.scaler = StandardScaler()
            self.model_trained = False
        else:
            self.regime_classifier = None
            self.scaler = None
            self.model_trained = False
        
        # Regime detection thresholds
        self.volatility_thresholds = {
            'low': 0.01,
            'normal': 0.03,
            'high': 0.06
        }
        
        self.trend_thresholds = {
            'weak': 0.02,
            'moderate': 0.05,
            'strong': 0.10
        }
    
    def detect_regime(self, price_data: List[float], volume_data: List[float], 
                     timestamp: datetime) -> MarketRegimeData:
        """Detect current market regime"""
        if len(price_data) < 20:
            return MarketRegimeData(
                regime=MarketRegime.UNKNOWN,
                confidence=0.0,
                volatility=0.0,
                trend_strength=0.0,
                momentum=0.0,
                volume_profile="unknown",
                timestamp=timestamp
            )
        
        # Calculate regime features
        features = self._calculate_regime_features(price_data, volume_data)
        
        # Use ML model if available and trained
        if self.model_trained and SKLEARN_AVAILABLE:
            regime, confidence = self._ml_regime_detection(features)
        else:
            regime, confidence = self._rule_based_regime_detection(features)
        
        regime_data = MarketRegimeData(
            regime=regime,
            confidence=confidence,
            volatility=features['volatility'],
            trend_strength=features['trend_strength'],
            momentum=features['momentum'],
            volume_profile=features['volume_profile'],
            timestamp=timestamp,
            features=features
        )
        
        self.regime_history.append(regime_data)
        self.feature_history.append(features)
        
        # Train model periodically
        if len(self.regime_history) >= 50 and len(self.regime_history) % 20 == 0:
            self._update_model()
        
        return regime_data
    
    def _calculate_regime_features(self, prices: List[float], volumes: List[float]) -> Dict[str, float]:
        """Calculate features for regime detection"""
        prices = np.array(prices)
        volumes = np.array(volumes)
        
        # Price-based features
        returns = np.diff(prices) / prices[:-1]
        volatility = np.std(returns[-20:]) if len(returns) >= 20 else np.std(returns)
        
        # Trend features
        if len(prices) >= 20:
            short_ma = np.mean(prices[-5:])
            long_ma = np.mean(prices[-20:])
            trend_strength = abs(short_ma - long_ma) / long_ma if long_ma != 0 else 0
            trend_direction = 1 if short_ma > long_ma else -1
        else:
            trend_strength = 0
            trend_direction = 0
        
        # Momentum features
        if len(prices) >= 10:
            momentum = (prices[-1] - prices[-10]) / prices[-10] if prices[-10] != 0 else 0
        else:
            momentum = 0
        
        # Volume features
        if len(volumes) >= 20:
            avg_volume = np.mean(volumes[-20:])
            current_volume_ratio = volumes[-1] / avg_volume if avg_volume > 0 else 1
            volume_trend = np.corrcoef(range(len(volumes[-10:])), volumes[-10:])[0, 1] if len(volumes) >= 10 else 0
        else:
            current_volume_ratio = 1
            volume_trend = 0
        
        # Volume profile classification
        if current_volume_ratio > 2.0:
            volume_profile = "high"
        elif current_volume_ratio > 1.5:
            volume_profile = "above_average"
        elif current_volume_ratio < 0.5:
            volume_profile = "low"
        else:
            volume_profile = "normal"
        
        # Price action features
        if len(prices) >= 5:
            price_range = (np.max(prices[-5:]) - np.min(prices[-5:])) / np.mean(prices[-5:])
        else:
            price_range = 0
        
        # Breakout detection
        if len(prices) >= 20:
            recent_high = np.max(prices[-20:])
            recent_low = np.min(prices[-20:])
            current_price = prices[-1]
            
            breakout_score = 0
            if current_price > recent_high * 0.98:  # Near recent high
                breakout_score = 1
            elif current_price < recent_low * 1.02:  # Near recent low
                breakout_score = -1
        else:
            breakout_score = 0
        
        return {
            'volatility': volatility,
            'trend_strength': trend_strength,
            'trend_direction': trend_direction,
            'momentum': momentum,
            'volume_ratio': current_volume_ratio,
            'volume_trend': volume_trend,
            'volume_profile': volume_profile,
            'price_range': price_range,
            'breakout_score': breakout_score,
            'returns_skew': float(pd.Series(returns[-20:]).skew()) if len(returns) >= 20 else 0,
            'returns_kurtosis': float(pd.Series(returns[-20:]).kurtosis()) if len(returns) >= 20 else 0
        }
    
    def _rule_based_regime_detection(self, features: Dict[str, float]) -> Tuple[MarketRegime, float]:
        """Rule-based regime detection fallback"""
        volatility = features['volatility']
        trend_strength = features['trend_strength']
        momentum = features['momentum']
        breakout_score = features['breakout_score']
        
        # High volatility regime
        if volatility > self.volatility_thresholds['high']:
            return MarketRegime.HIGH_VOLATILITY, 0.8
        
        # Low volatility regime
        if volatility < self.volatility_thresholds['low']:
            return MarketRegime.LOW_VOLATILITY, 0.8
        
        # Breakout regime
        if abs(breakout_score) > 0.5 and volatility > self.volatility_thresholds['normal']:
            return MarketRegime.BREAKOUT, 0.7
        
        # Trending regimes
        if trend_strength > self.trend_thresholds['moderate']:
            if momentum > 0:
                return MarketRegime.TRENDING_UP, 0.75
            else:
                return MarketRegime.TRENDING_DOWN, 0.75
        
        # Ranging regime (default)
        return MarketRegime.RANGING, 0.6
    
    def _ml_regime_detection(self, features: Dict[str, float]) -> Tuple[MarketRegime, float]:
        """ML-based regime detection"""
        if not SKLEARN_AVAILABLE or not self.model_trained:
            return self._rule_based_regime_detection(features)
        
        try:
            # Prepare features for prediction
            feature_vector = np.array([
                features['volatility'],
                features['trend_strength'],
                features['momentum'],
                features['volume_ratio'],
                features['price_range'],
                features['breakout_score']
            ]).reshape(1, -1)
            
            # Scale features
            feature_vector_scaled = self.scaler.transform(feature_vector)
            
            # Predict regime
            regime_pred = self.regime_classifier.predict(feature_vector_scaled)[0]
            confidence = np.max(self.regime_classifier.predict_proba(feature_vector_scaled)[0])
            
            # Convert prediction to MarketRegime
            regime_map = {
                0: MarketRegime.RANGING,
                1: MarketRegime.TRENDING_UP,
                2: MarketRegime.TRENDING_DOWN,
                3: MarketRegime.HIGH_VOLATILITY,
                4: MarketRegime.LOW_VOLATILITY,
                5: MarketRegime.BREAKOUT
            }
            
            regime = regime_map.get(regime_pred, MarketRegime.UNKNOWN)
            return regime, confidence
            
        except Exception as e:
            logger.warning(f"ML regime detection failed: {e}. Falling back to rule-based.")
            return self._rule_based_regime_detection(features)
    
    def _update_model(self):
        """Update the regime detection model"""
        if not SKLEARN_AVAILABLE or len(self.regime_history) < 30:
            return
        
        try:
            # Prepare training data
            X = []
            y = []
            
            for i, (regime_data, features) in enumerate(zip(self.regime_history, self.feature_history)):
                if i < len(self.regime_history) - 10:  # Don't use most recent data for training
                    feature_vector = [
                        features['volatility'],
                        features['trend_strength'],
                        features['momentum'],
                        features['volume_ratio'],
                        features['price_range'],
                        features['breakout_score']
                    ]
                    X.append(feature_vector)
                    
                    # Map regime to numeric label
                    regime_map = {
                        MarketRegime.RANGING: 0,
                        MarketRegime.TRENDING_UP: 1,
                        MarketRegime.TRENDING_DOWN: 2,
                        MarketRegime.HIGH_VOLATILITY: 3,
                        MarketRegime.LOW_VOLATILITY: 4,
                        MarketRegime.BREAKOUT: 5
                    }
                    y.append(regime_map.get(regime_data.regime, 0))
            
            if len(X) < 20:
                return
            
            X = np.array(X)
            y = np.array(y)
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Train model
            self.regime_classifier.fit(X_scaled, y)
            self.model_trained = True
            
            logger.info(f"Regime detection model updated with {len(X)} samples")
            
        except Exception as e:
            logger.error(f"Failed to update regime detection model: {e}")

class MetaLabelingSystem:
    """Meta-labeling system for signal filtering and quality assessment"""
    
    def __init__(self, config: MLConfig):
        self.config = config
        self.signal_history = deque(maxlen=config.meta_labeling_period * 4)
        self.performance_history = deque(maxlen=config.meta_labeling_period * 4)
        
        if SKLEARN_AVAILABLE:
            self.meta_classifier = RandomForestClassifier(
                n_estimators=50,
                max_depth=8,
                random_state=42
            )
            self.profitability_regressor = RandomForestClassifier(
                n_estimators=50,
                max_depth=6,
                random_state=42
            )
            self.scaler = StandardScaler()
            self.model_trained = False
        else:
            self.meta_classifier = None
            self.profitability_regressor = None
            self.scaler = None
            self.model_trained = False
    
    def evaluate_signal(self, signal: SignalType, confidence: float, 
                       market_features: Dict[str, float], 
                       regime_data: MarketRegimeData) -> MetaLabelResult:
        """Evaluate signal quality using meta-labeling"""
        
        # Extract features for meta-labeling
        features = self._extract_meta_features(signal, confidence, market_features, regime_data)
        
        if self.model_trained and SKLEARN_AVAILABLE:
            quality, profitability, meta_confidence = self._ml_signal_evaluation(features)
        else:
            quality, profitability, meta_confidence = self._rule_based_signal_evaluation(features)
        
        # Calculate risk score and position sizing
        risk_score = self._calculate_risk_score(features, regime_data)
        position_size = self._calculate_position_size(profitability, risk_score, meta_confidence)
        
        result = MetaLabelResult(
            signal_quality=quality,
            predicted_profitability=profitability,
            confidence=meta_confidence,
            risk_score=risk_score,
            recommended_position_size=position_size,
            features_used=list(features.keys()),
            model_version="1.0"
        )
        
        # Store for model training
        self.signal_history.append((features, signal, confidence))
        
        return result
    
    def _extract_meta_features(self, signal: SignalType, confidence: float,
                              market_features: Dict[str, float],
                              regime_data: MarketRegimeData) -> Dict[str, float]:
        """Extract features for meta-labeling"""
        features = {
            'signal_strength': 1.0 if signal == SignalType.BUY else (-1.0 if signal == SignalType.SELL else 0.0),
            'original_confidence': confidence,
            'regime_confidence': regime_data.confidence,
            'volatility': regime_data.volatility,
            'trend_strength': regime_data.trend_strength,
            'momentum': regime_data.momentum,
        }
        
        # Add market features
        features.update(market_features)
        
        # Add regime-specific features
        regime_encoding = {
            MarketRegime.TRENDING_UP: 1.0,
            MarketRegime.TRENDING_DOWN: -1.0,
            MarketRegime.RANGING: 0.0,
            MarketRegime.HIGH_VOLATILITY: 0.5,
            MarketRegime.LOW_VOLATILITY: -0.5,
            MarketRegime.BREAKOUT: 0.8,
            MarketRegime.REVERSAL: -0.8,
            MarketRegime.UNKNOWN: 0.0
        }
        features['regime_encoding'] = regime_encoding.get(regime_data.regime, 0.0)
        
        # Historical performance features
        if len(self.performance_history) >= 10:
            recent_performance = list(self.performance_history)[-10:]
            features['recent_win_rate'] = sum(1 for p in recent_performance if p > 0) / len(recent_performance)
            features['avg_recent_return'] = np.mean(recent_performance)
            features['return_volatility'] = np.std(recent_performance)
        else:
            features['recent_win_rate'] = 0.5
            features['avg_recent_return'] = 0.0
            features['return_volatility'] = 0.0
        
        return features
    
    def _rule_based_signal_evaluation(self, features: Dict[str, float]) -> Tuple[SignalQuality, float, float]:
        """Rule-based signal evaluation fallback"""
        confidence = features['original_confidence']
        regime_conf = features['regime_confidence']
        volatility = features['volatility']
        
        # Base quality assessment
        if confidence > 0.8 and regime_conf > 0.7:
            quality = SignalQuality.EXCELLENT
            profitability = 0.75
            meta_confidence = 0.85
        elif confidence > 0.6 and regime_conf > 0.6:
            quality = SignalQuality.GOOD
            profitability = 0.60
            meta_confidence = 0.70
        elif confidence > 0.4:
            quality = SignalQuality.FAIR
            profitability = 0.45
            meta_confidence = 0.55
        else:
            quality = SignalQuality.POOR
            profitability = 0.30
            meta_confidence = 0.30
        
        # Adjust for high volatility
        if volatility > 0.05:
            profitability *= 0.8
            meta_confidence *= 0.9
        
        # Filter very poor signals
        if confidence < 0.3 or (volatility > 0.08 and confidence < 0.5):
            quality = SignalQuality.FILTERED
            profitability = 0.0
            meta_confidence = 0.0
        
        return quality, profitability, meta_confidence
    
    def _ml_signal_evaluation(self, features: Dict[str, float]) -> Tuple[SignalQuality, float, float]:
        """ML-based signal evaluation"""
        if not SKLEARN_AVAILABLE or not self.model_trained:
            return self._rule_based_signal_evaluation(features)
        
        try:
            # Prepare features
            feature_vector = np.array([
                features['signal_strength'],
                features['original_confidence'],
                features['regime_confidence'],
                features['volatility'],
                features['trend_strength'],
                features['momentum'],
                features['regime_encoding']
            ]).reshape(1, -1)
            
            # Scale features
            feature_vector_scaled = self.scaler.transform(feature_vector)
            
            # Predict quality and profitability
            quality_pred = self.meta_classifier.predict(feature_vector_scaled)[0]
            quality_conf = np.max(self.meta_classifier.predict_proba(feature_vector_scaled)[0])
            
            profitability_pred = self.profitability_regressor.predict(feature_vector_scaled)[0]
            
            # Map predictions
            quality_map = {
                0: SignalQuality.FILTERED,
                1: SignalQuality.POOR,
                2: SignalQuality.FAIR,
                3: SignalQuality.GOOD,
                4: SignalQuality.EXCELLENT
            }
            
            quality = quality_map.get(quality_pred, SignalQuality.FAIR)
            profitability = max(0.0, min(1.0, profitability_pred / 100.0))  # Normalize to 0-1
            
            return quality, profitability, quality_conf
            
        except Exception as e:
            logger.warning(f"ML signal evaluation failed: {e}. Falling back to rule-based.")
            return self._rule_based_signal_evaluation(features)
    
    def _calculate_risk_score(self, features: Dict[str, float], regime_data: MarketRegimeData) -> float:
        """Calculate risk score for the signal"""
        base_risk = 0.5
        
        # Volatility risk
        vol_risk = min(0.4, regime_data.volatility * 10)
        
        # Regime risk
        regime_risk_map = {
            MarketRegime.HIGH_VOLATILITY: 0.3,
            MarketRegime.BREAKOUT: 0.2,
            MarketRegime.REVERSAL: 0.25,
            MarketRegime.TRENDING_UP: 0.1,
            MarketRegime.TRENDING_DOWN: 0.1,
            MarketRegime.RANGING: 0.15,
            MarketRegime.LOW_VOLATILITY: 0.05,
            MarketRegime.UNKNOWN: 0.4
        }
        regime_risk = regime_risk_map.get(regime_data.regime, 0.2)
        
        # Confidence risk (inverse relationship)
        conf_risk = (1.0 - features['original_confidence']) * 0.3
        
        total_risk = min(1.0, base_risk + vol_risk + regime_risk + conf_risk)
        return total_risk
    
    def _calculate_position_size(self, profitability: float, risk_score: float, confidence: float) -> float:
        """Calculate recommended position size"""
        # Base position size from Kelly criterion approximation
        win_prob = profitability
        avg_win = 0.02  # Assume 2% average win
        avg_loss = 0.01  # Assume 1% average loss
        
        if avg_loss > 0:
            kelly_fraction = (win_prob * avg_win - (1 - win_prob) * avg_loss) / avg_win
        else:
            kelly_fraction = 0.1
        
        # Adjust for risk and confidence
        risk_adjustment = 1.0 - risk_score
        confidence_adjustment = confidence
        
        position_size = max(0.0, min(1.0, kelly_fraction * risk_adjustment * confidence_adjustment))
        
        # Conservative cap
        return min(position_size, 0.25)  # Max 25% position size
    
    def update_performance(self, signal_id: str, actual_return: float):
        """Update performance tracking for model training"""
        self.performance_history.append(actual_return)
        
        # Trigger model retraining periodically
        if len(self.performance_history) >= 30 and len(self.performance_history) % 10 == 0:
            self._retrain_models()
    
    def _retrain_models(self):
        """Retrain meta-labeling models"""
        if not SKLEARN_AVAILABLE or len(self.signal_history) < 20 or len(self.performance_history) < 20:
            return
        
        try:
            # Prepare training data
            X = []
            y_quality = []
            y_profitability = []
            
            min_len = min(len(self.signal_history), len(self.performance_history))
            
            for i in range(min_len - 10):  # Leave recent data for validation
                features, signal, confidence = self.signal_history[i]
                actual_return = self.performance_history[i]
                
                feature_vector = [
                    features['signal_strength'],
                    features['original_confidence'],
                    features['regime_confidence'],
                    features['volatility'],
                    features['trend_strength'],
                    features['momentum'],
                    features['regime_encoding']
                ]
                X.append(feature_vector)
                
                # Label quality based on actual performance
                if actual_return > 0.02:
                    y_quality.append(4)  # Excellent
                elif actual_return > 0.01:
                    y_quality.append(3)  # Good
                elif actual_return > 0:
                    y_quality.append(2)  # Fair
                elif actual_return > -0.01:
                    y_quality.append(1)  # Poor
                else:
                    y_quality.append(0)  # Filtered
                
                y_profitability.append(max(0, min(100, actual_return * 100)))  # Scale to 0-100
            
            if len(X) < 15:
                return
            
            X = np.array(X)
            y_quality = np.array(y_quality)
            y_profitability = np.array(y_profitability)
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Train models
            self.meta_classifier.fit(X_scaled, y_quality)
            self.profitability_regressor.fit(X_scaled, y_profitability)
            self.model_trained = True
            
            logger.info(f"Meta-labeling models retrained with {len(X)} samples")
            
        except Exception as e:
            logger.error(f"Failed to retrain meta-labeling models: {e}")

class ProbabilisticForecaster:
    """Real-time probabilistic forecasting with Monte Carlo simulation"""
    
    def __init__(self, config: MLConfig):
        self.config = config
        self.price_history = deque(maxlen=200)
        self.volume_history = deque(maxlen=200)
        self.volatility_history = deque(maxlen=100)
    
    def generate_forecast(self, current_price: float, current_volume: float,
                         market_features: Dict[str, float],
                         regime_data: MarketRegimeData,
                         forecast_horizon: int = 10) -> ProbabilisticForecast:
        """Generate probabilistic forecast using Monte Carlo simulation"""
        
        self.price_history.append(current_price)
        self.volume_history.append(current_volume)
        
        if len(self.price_history) < 20:
            return self._default_forecast(current_price)
        
        # Estimate parameters for simulation
        returns = np.diff(list(self.price_history)) / np.array(list(self.price_history)[:-1])
        
        # Regime-adjusted parameters
        mu, sigma = self._estimate_regime_parameters(returns, regime_data)
        
        # Run Monte Carlo simulation
        paths = self._monte_carlo_simulation(
            current_price, mu, sigma, forecast_horizon, self.config.monte_carlo_simulations
        )
        
        # Calculate statistics
        final_prices = paths[:, -1]
        mean_prediction = np.mean(final_prices)
        std_prediction = np.std(final_prices)
        
        # Confidence intervals
        confidence_intervals = {
            '68%': (np.percentile(final_prices, 16), np.percentile(final_prices, 84)),
            '95%': (np.percentile(final_prices, 2.5), np.percentile(final_prices, 97.5)),
            '99%': (np.percentile(final_prices, 0.5), np.percentile(final_prices, 99.5))
        }
        
        # Probability calculations
        probability_distributions = self._calculate_probabilities(
            final_prices, current_price, market_features
        )
        
        # Scenario probabilities
        scenario_probabilities = self._calculate_scenario_probabilities(
            paths, current_price, regime_data
        )
        
        return ProbabilisticForecast(
            mean_prediction=mean_prediction,
            std_prediction=std_prediction,
            confidence_intervals=confidence_intervals,
            probability_distributions=probability_distributions,
            scenario_probabilities=scenario_probabilities,
            monte_carlo_paths=paths if self.config.monte_carlo_simulations <= 100 else None
        )
    
    def _estimate_regime_parameters(self, returns: np.ndarray, 
                                  regime_data: MarketRegimeData) -> Tuple[float, float]:
        """Estimate drift and volatility parameters based on regime"""
        base_mu = np.mean(returns[-20:]) if len(returns) >= 20 else 0.0
        base_sigma = np.std(returns[-20:]) if len(returns) >= 20 else 0.02
        
        # Regime adjustments
        regime_adjustments = {
            MarketRegime.TRENDING_UP: (1.5, 0.8),
            MarketRegime.TRENDING_DOWN: (-1.5, 0.8),
            MarketRegime.RANGING: (0.0, 0.6),
            MarketRegime.HIGH_VOLATILITY: (0.0, 2.0),
            MarketRegime.LOW_VOLATILITY: (0.0, 0.4),
            MarketRegime.BREAKOUT: (2.0, 1.5),
            MarketRegime.REVERSAL: (-1.0, 1.2),
            MarketRegime.UNKNOWN: (0.0, 1.0)
        }
        
        mu_mult, sigma_mult = regime_adjustments.get(regime_data.regime, (0.0, 1.0))
        
        adjusted_mu = base_mu * mu_mult if mu_mult != 0 else base_mu
        adjusted_sigma = base_sigma * sigma_mult
        
        return adjusted_mu, adjusted_sigma
    
    def _monte_carlo_simulation(self, initial_price: float, mu: float, sigma: float,
                               horizon: int, n_simulations: int) -> np.ndarray:
        """Run Monte Carlo price simulation"""
        dt = 1.0  # Daily time step
        paths = np.zeros((n_simulations, horizon + 1))
        paths[:, 0] = initial_price
        
        for t in range(1, horizon + 1):
            # Geometric Brownian Motion
            random_shocks = np.random.normal(0, 1, n_simulations)
            paths[:, t] = paths[:, t-1] * np.exp(
                (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * random_shocks
            )
        
        return paths
    
    def _calculate_probabilities(self, final_prices: np.ndarray, current_price: float,
                               market_features: Dict[str, float]) -> Dict[str, float]:
        """Calculate various probability distributions"""
        probabilities = {}
        
        # Basic probabilities
        probabilities['above_current'] = np.mean(final_prices > current_price)
        probabilities['below_current'] = np.mean(final_prices < current_price)
        
        # Threshold probabilities
        probabilities['gain_5pct'] = np.mean(final_prices > current_price * 1.05)
        probabilities['loss_5pct'] = np.mean(final_prices < current_price * 0.95)
        probabilities['gain_10pct'] = np.mean(final_prices > current_price * 1.10)
        probabilities['loss_10pct'] = np.mean(final_prices < current_price * 0.90)
        
        # VWAP probability (if available)
        if 'vwap' in market_features:
            vwap = market_features['vwap']
            probabilities['above_vwap'] = np.mean(final_prices > vwap)
        
        # Support/Resistance probabilities (if available)
        if 'support_level' in market_features:
            support = market_features['support_level']
            probabilities['above_support'] = np.mean(final_prices > support)
        
        if 'resistance_level' in market_features:
            resistance = market_features['resistance_level']
            probabilities['below_resistance'] = np.mean(final_prices < resistance)
        
        return probabilities
    
    def _calculate_scenario_probabilities(self, paths: np.ndarray, current_price: float,
                                        regime_data: MarketRegimeData) -> Dict[str, float]:
        """Calculate scenario-based probabilities"""
        scenarios = {}
        
        # Trend continuation scenarios
        final_prices = paths[:, -1]
        max_prices = np.max(paths, axis=1)
        min_prices = np.min(paths, axis=1)
        
        # Bull scenario: consistent upward movement
        bull_condition = (final_prices > current_price * 1.02) & (min_prices > current_price * 0.98)
        scenarios['bull_scenario'] = np.mean(bull_condition)
        
        # Bear scenario: consistent downward movement
        bear_condition = (final_prices < current_price * 0.98) & (max_prices < current_price * 1.02)
        scenarios['bear_scenario'] = np.mean(bear_condition)
        
        # Sideways scenario: limited movement
        sideways_condition = (final_prices > current_price * 0.98) & (final_prices < current_price * 1.02)
        scenarios['sideways_scenario'] = np.mean(sideways_condition)
        
        # Volatile scenario: high volatility
        volatility_per_path = np.std(np.diff(paths, axis=1), axis=1)
        high_vol_threshold = np.percentile(volatility_per_path, 75)
        scenarios['volatile_scenario'] = np.mean(volatility_per_path > high_vol_threshold)
        
        # Breakout scenarios
        breakout_up = np.mean(max_prices > current_price * 1.05)
        breakout_down = np.mean(min_prices < current_price * 0.95)
        scenarios['breakout_up'] = breakout_up
        scenarios['breakout_down'] = breakout_down
        
        return scenarios
    
    def _default_forecast(self, current_price: float) -> ProbabilisticForecast:
        """Default forecast when insufficient data"""
        return ProbabilisticForecast(
            mean_prediction=current_price,
            std_prediction=current_price * 0.02,
            confidence_intervals={
                '68%': (current_price * 0.98, current_price * 1.02),
                '95%': (current_price * 0.95, current_price * 1.05),
                '99%': (current_price * 0.90, current_price * 1.10)
            },
            probability_distributions={
                'above_current': 0.5,
                'below_current': 0.5,
                'gain_5pct': 0.3,
                'loss_5pct': 0.3
            },
            scenario_probabilities={
                'bull_scenario': 0.25,
                'bear_scenario': 0.25,
                'sideways_scenario': 0.5
            }
        )

class SignalDecayModel:
    """Model signal decay over time"""
    
    def __init__(self, config: MLConfig):
        self.config = config
        self.signal_timestamps = deque(maxlen=1000)
        self.signal_strengths = deque(maxlen=1000)
    
    def calculate_decayed_signal(self, original_signal: SignalType, original_confidence: float,
                               signal_timestamp: datetime, current_timestamp: datetime) -> Tuple[SignalType, float]:
        """Calculate signal strength after time decay"""
        
        time_diff = (current_timestamp - signal_timestamp).total_seconds() / 60  # minutes
        
        if time_diff <= 0:
            return original_signal, original_confidence
        
        # Calculate decay factor
        decay_factor = self._calculate_decay_factor(time_diff)
        
        # Apply decay
        decayed_confidence = original_confidence * decay_factor
        
        # Determine if signal should be filtered out
        if decayed_confidence < 0.1:
            return SignalType.NEUTRAL, 0.0
        
        return original_signal, decayed_confidence
    
    def _calculate_decay_factor(self, time_elapsed: float) -> float:
        """Calculate decay factor based on elapsed time"""
        half_life = self.config.signal_half_life
        
        if self.config.decay_function == "exponential":
            return np.exp(-np.log(2) * time_elapsed / half_life)
        elif self.config.decay_function == "linear":
            return max(0, 1 - time_elapsed / (2 * half_life))
        elif self.config.decay_function == "power":
            return (1 + time_elapsed / half_life) ** -2
        else:
            return np.exp(-np.log(2) * time_elapsed / half_life)  # Default to exponential

class MLEnhancedIndicatorSystem:
    """Main ML-enhanced indicator system integrating all components"""
    
    def __init__(self, config: MLConfig = None):
        self.config = config or MLConfig()
        
        # Initialize components
        self.regime_detector = MarketRegimeDetector(self.config) if self.config.enable_regime_detection else None
        self.meta_labeler = MetaLabelingSystem(self.config) if self.config.enable_meta_labeling else None
        self.forecaster = ProbabilisticForecaster(self.config) if self.config.enable_probabilistic_forecasting else None
        self.decay_model = SignalDecayModel(self.config) if self.config.enable_signal_decay else None
        
        # System state
        self.current_regime = None
        self.active_signals = deque(maxlen=100)
        
        logger.info(f"ML-Enhanced Indicator System initialized with config: {self.config}")
    
    def process_signal(self, signal: SignalType, confidence: float, 
                      price_data: List[float], volume_data: List[float],
                      market_features: Dict[str, float], timestamp: datetime) -> Dict[str, Any]:
        """Process signal through ML enhancement pipeline"""
        
        results = {
            'original_signal': signal,
            'original_confidence': confidence,
            'timestamp': timestamp
        }
        
        # 1. Market Regime Detection
        if self.regime_detector:
            regime_data = self.regime_detector.detect_regime(price_data, volume_data, timestamp)
            self.current_regime = regime_data
            results['regime_data'] = regime_data
        else:
            regime_data = MarketRegimeData(
                regime=MarketRegime.UNKNOWN,
                confidence=0.5,
                volatility=0.02,
                trend_strength=0.0,
                momentum=0.0,
                volume_profile="normal",
                timestamp=timestamp
            )
        
        # 2. Meta-Labeling
        if self.meta_labeler:
            meta_result = self.meta_labeler.evaluate_signal(signal, confidence, market_features, regime_data)
            results['meta_label_result'] = meta_result
            
            # Update signal based on meta-labeling
            if meta_result.signal_quality == SignalQuality.FILTERED:
                signal = SignalType.NEUTRAL
                confidence = 0.0
            else:
                confidence = min(confidence, meta_result.confidence)
        
        # 3. Signal Decay (for existing signals)
        if self.decay_model:
            signal, confidence = self.decay_model.calculate_decayed_signal(
                signal, confidence, timestamp, timestamp
            )
        
        # 4. Probabilistic Forecasting
        if self.forecaster and len(price_data) > 0:
            forecast = self.forecaster.generate_forecast(
                price_data[-1], volume_data[-1] if volume_data else 1.0,
                market_features, regime_data
            )
            results['probabilistic_forecast'] = forecast
        
        # 5. Final signal processing
        results.update({
            'enhanced_signal': signal,
            'enhanced_confidence': confidence,
            'processing_timestamp': datetime.now()
        })
        
        # Store active signal
        if signal != SignalType.NEUTRAL:
            self.active_signals.append({
                'signal': signal,
                'confidence': confidence,
                'timestamp': timestamp,
                'regime': regime_data.regime if regime_data else MarketRegime.UNKNOWN
            })
        
        return results
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status and statistics"""
        status = {
            'current_regime': self.current_regime.regime.value if self.current_regime else "unknown",
            'active_signals_count': len(self.active_signals),
            'components_enabled': {
                'regime_detection': self.config.enable_regime_detection,
                'meta_labeling': self.config.enable_meta_labeling,
                'probabilistic_forecasting': self.config.enable_probabilistic_forecasting,
                'signal_decay': self.config.enable_signal_decay
            }
        }
        
        if self.regime_detector:
            status['regime_model_trained'] = self.regime_detector.model_trained
        
        if self.meta_labeler:
            status['meta_model_trained'] = self.meta_labeler.model_trained
        
        return status

# Factory function
def create_ml_enhanced_system(config: MLConfig = None) -> MLEnhancedIndicatorSystem:
    """Create ML-enhanced indicator system"""
    return MLEnhancedIndicatorSystem(config)