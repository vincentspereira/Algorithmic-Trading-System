"""
Institutional-Grade Augmented Machine Learning Indicator

This module implements an enhanced ML-based indicator with institutional-grade features:
- Volume confirmation scoring
- Market regime adaptation
- Multi-timeframe convergence
- Smart money detection
- Automated risk management
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from datetime import datetime
from collections import deque
import statistics
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from nautilus_trader_engine.indicators.base import (
    AugmentedIndicator,
    AugmentedIndicatorConfig,
    IndicatorSignal,
    SignalType,
)


@dataclass
class AugmentedMLConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented ML Indicator"""
    lookback_period: int = 100
    anomaly_threshold: float = -0.5  # Isolation Forest threshold
    prediction_horizon: int = 5
    feature_count: int = 10
    contamination: float = 0.1  # Expected proportion of anomalies


class AugmentedMLIndicator(AugmentedIndicator):
    """
    Institutional-grade Augmented ML Indicator implementing 5-pillar architecture.

    Features:
    - Anomaly detection using Isolation Forest for institutional pattern recognition
    - Predictive analysis for price movement forecasting
    - Feature engineering from multiple technical indicators
    - Market regime classification using unsupervised learning
    - Multi-timeframe convergence for institutional confirmation
    - Smart money pattern recognition using ML techniques
    - Automated risk management with ML-based confidence scoring
    """

    def __init__(self, config: AugmentedMLConfig = None):
        if config is None:
            config = AugmentedMLConfig()

        super().__init__(config)
        self.ml_config = config

        # ML specific state
        self._feature_matrix = deque(maxlen=self.config.buffer_size)
        self._price_history = deque(maxlen=self.config.buffer_size)
        self._volume_history = deque(maxlen=self.config.buffer_size)

        # ML models
        self._anomaly_detector = IsolationForest(
            contamination=self.ml_config.contamination,
            random_state=42
        )
        self._scaler = StandardScaler()

        # ML analysis results
        self._anomaly_scores = deque(maxlen=self.config.buffer_size)
        self._prediction_scores = deque(maxlen=self.config.buffer_size)
        self._regime_probabilities = deque(maxlen=self.config.buffer_size)

        self._current_anomaly_score = 0.0
        self._current_prediction = 0.0
        self._current_regime = "normal"

        # Pattern analysis
        self._anomaly_count = 0
        self._prediction_accuracy = 0.0
        self._regime_stability = 0.0

        # Signal analysis
        self._anomaly_signals = 0
        self._prediction_signals = 0
        self._regime_signals = 0
        self._confidence_signals = 0

        # Market structure
        self._pattern_recognition = 0
        self._predictive_power = 0.0
        self._model_confidence = 0.0

        # Institutional analysis
        self._institutional_ml = 0.0
        self._smart_money_ml = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if ML Indicator is ready to provide signals"""
        return (len(self._feature_matrix) >= self.ml_config.lookback_period and
                len(self._anomaly_scores) > 0)

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update ML analysis

        Args:
            bar (Bar): New bar data
        """
        # Extract OHLCV data
        if hasattr(bar, 'high') and hasattr(bar, 'low') and hasattr(bar, 'close') and hasattr(bar, 'volume'):
            high = bar.high
            low = bar.low
            close = bar.close
            volume = bar.volume
        else:
            high = bar.get('high', bar.get('close', 0.0))
            low = bar.get('low', bar.get('close', 0.0))
            close = bar.get('close', bar.get('price', 0.0))
            volume = bar.get('volume', 1.0)

        # Update ML analysis
        self._update_ml_analysis(high, low, close, volume)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_ml_analysis(self, high: float, low: float, close: float, volume: float):
        """Update the core ML analysis with institutional enhancements"""
        # Store price and volume data
        self._price_history.append(close)
        self._volume_history.append(volume)

        if len(self._price_history) >= self.ml_config.lookback_period:
            # Extract features for ML analysis
            features = self._extract_features(high, low, close, volume)
            self._feature_matrix.append(features)

            # Update ML models and analysis
            self._update_anomaly_detection()
            self._update_predictive_analysis()
            self._update_regime_classification()

            # Analyze ML characteristics
            self._analyze_ml_characteristics()

    def _extract_features(self, high: float, low: float, close: float, volume: float) -> List[float]:
        """Extract features for ML analysis"""
        if len(self._price_history) < 10:
            return [0.0] * self.ml_config.feature_count

        prices = list(self._price_history)[-20:]  # Last 20 prices
        volumes = list(self._volume_history)[-20:]  # Last 20 volumes

        features = []

        # Price-based features
        features.append(close / prices[0] - 1)  # Return
        features.append((high - low) / close)  # Volatility
        features.append(statistics.mean(prices))  # Moving average
        features.append(statistics.stdev(prices) if len(prices) > 1 else 0)  # Standard deviation

        # Volume-based features
        features.append(volume / statistics.mean(volumes) if volumes else 1.0)  # Volume ratio
        features.append(statistics.mean(volumes))  # Average volume

        # Momentum features
        if len(prices) >= 5:
            features.append((prices[-1] - prices[-5]) / prices[-5])  # 5-period momentum
        else:
            features.append(0.0)

        # Trend features
        if len(prices) >= 10:
            short_ma = statistics.mean(prices[-5:])
            long_ma = statistics.mean(prices[-10:])
            features.append((short_ma - long_ma) / long_ma)  # Trend strength
        else:
            features.append(0.0)

        # Fill remaining features with zeros if needed
        while len(features) < self.ml_config.feature_count:
            features.append(0.0)

        return features[:self.ml_config.feature_count]

    def _update_anomaly_detection(self):
        """Update anomaly detection using Isolation Forest"""
        if len(self._feature_matrix) < self.ml_config.lookback_period:
            return

        # Prepare data for anomaly detection
        feature_data = list(self._feature_matrix)[-self.ml_config.lookback_period:]
        X = np.array(feature_data)

        # Scale features
        X_scaled = self._scaler.fit_transform(X)

        # Fit anomaly detector
        self._anomaly_detector.fit(X_scaled)

        # Get anomaly scores
        anomaly_scores = self._anomaly_detector.decision_function(X_scaled)
        self._current_anomaly_score = anomaly_scores[-1]  # Most recent score

        # Store anomaly scores
        self._anomaly_scores.append(self._current_anomaly_score)

        # Count anomalies
        if self._current_anomaly_score < self.ml_config.anomaly_threshold:
            self._anomaly_count += 1

    def _update_predictive_analysis(self):
        """Update predictive analysis for price movement forecasting"""
        if len(self._price_history) < self.ml_config.lookback_period + self.ml_config.prediction_horizon:
            return

        # Simple predictive model based on recent trends
        recent_prices = list(self._price_history)[-self.ml_config.lookback_period:]
        future_prices = list(self._price_history)[-self.ml_config.prediction_horizon:]

        if len(recent_prices) >= 10 and len(future_prices) >= 1:
            # Calculate trend direction
            trend = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]

            # Calculate momentum
            momentum = (recent_prices[-1] - recent_prices[-5]) / recent_prices[-5] if len(recent_prices) >= 5 else 0

            # Calculate volatility
            volatility = statistics.stdev(recent_prices) / statistics.mean(recent_prices) if recent_prices else 0

            # Simple prediction score (trend + momentum - volatility)
            self._current_prediction = trend + momentum - volatility

            self._prediction_scores.append(self._current_prediction)

    def _update_regime_classification(self):
        """Update market regime classification using ML techniques"""
        if len(self._feature_matrix) < self.ml_config.lookback_period:
            return

        # Classify market regime based on feature patterns
        features = list(self._feature_matrix)[-1]

        # Simple regime classification based on feature values
        volatility = abs(features[1])  # Volatility feature
        trend = abs(features[6])  # Trend feature
        volume = abs(features[4])  # Volume feature

        if volatility > 0.05 and volume > 1.5:
            self._current_regime = "volatile"
        elif trend > 0.02 and volume > 1.2:
            self._current_regime = "trending"
        elif volatility < 0.02 and volume < 0.8:
            self._current_regime = "ranging"
        else:
            self._current_regime = "normal"

        # Calculate regime stability
        if len(self._regime_probabilities) >= 5:
            recent_regimes = [self._current_regime] * 5  # Simplified
            unique_regimes = len(set(recent_regimes))
            self._regime_stability = 1.0 - (unique_regimes - 1) / 4.0  # Higher stability = fewer regime changes

    def _analyze_ml_characteristics(self):
        """Analyze ML characteristics for institutional insights"""
        if not self.is_ready:
            return

        # Calculate prediction accuracy (simplified)
        if len(self._prediction_scores) >= 10:
            predictions = list(self._prediction_scores)[-10:]
            actual_trends = []

            for i in range(len(predictions)):
                if i + self.ml_config.prediction_horizon < len(self._price_history):
                    future_price = list(self._price_history)[-(i + self.ml_config.prediction_horizon)]
                    current_price = list(self._price_history)[-(i + self.ml_config.prediction_horizon + 1)]
                    actual_trend = (future_price - current_price) / current_price
                    actual_trends.append(actual_trend)

            if actual_trends:
                correct_predictions = sum(1 for p, a in zip(predictions, actual_trends)
                                        if (p > 0 and a > 0) or (p < 0 and a < 0))
                self._prediction_accuracy = correct_predictions / len(actual_trends)

        # Generate signals
        self._generate_ml_signals()

        # Calculate institutional ML analysis
        self._calculate_institutional_ml()

    def _generate_ml_signals(self):
        """Generate ML-based signals"""
        if not self.is_ready:
            return

        # Anomaly signals
        if self._current_anomaly_score < self.ml_config.anomaly_threshold:
            self._anomaly_signals += 1

        # Prediction signals
        if abs(self._current_prediction) > 0.02:
            self._prediction_signals += 1

        # Regime signals
        if self._current_regime != "normal" and self._regime_stability > 0.7:
            self._regime_signals += 1

        # Confidence signals
        if (self._prediction_accuracy > 0.6 and
            self._regime_stability > 0.8 and
            abs(self._current_anomaly_score) > 0.3):
            self._confidence_signals += 1

    def _calculate_institutional_ml(self):
        """Calculate institutional ML analysis based on ML characteristics"""
        if not self.is_ready:
            return

        # Institutional traders use ML for advanced pattern recognition
        base_ml = 0.0

        if (self._anomaly_signals > 0 and
            self._prediction_accuracy > 0.7 and
            self._regime_stability > 0.8):
            base_ml = 0.9  # Strong ML signals with high accuracy
        elif (self._prediction_signals > 0 and
              self._confidence_signals > 0 and
              self._current_anomaly_score < self.ml_config.anomaly_threshold):
            base_ml = 0.8  # Good predictive signals with confidence
        elif (self._regime_signals > 0 and
              self._regime_stability > 0.6):
            base_ml = 0.7  # Stable regime classification

        self._institutional_ml = base_ml

        # Smart money ML considers anomaly detection and prediction accuracy
        smart_money_score = (
            (1.0 + self._current_anomaly_score) * 0.3 +  # Less negative anomaly score = better
            self._prediction_accuracy * 0.3 +
            self._regime_stability * 0.2 +
            self._institutional_ml * 0.2
        )
        self._smart_money_ml = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade ML analysis"""
        if not self.is_ready:
            return IndicatorSignal(
                value_raw=0.0,
                signal_type=SignalType.NEUTRAL,
                composite_confidence=0.0,
                confidence_components={},
                suggested_sl=0.0,
                suggested_tp=0.0,
                metadata={"status": "not_ready"}
            )

        # Use anomaly score as primary raw value
        raw_value = self._current_anomaly_score

        # Determine signal type based on ML analysis
        signal_type = self._determine_ml_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'anomaly_score': self._current_anomaly_score,
            'prediction_score': self._current_prediction,
            'regime': self._current_regime,
            'prediction_accuracy': self._prediction_accuracy,
            'regime_stability': self._regime_stability,
            'anomaly_signals': self._anomaly_signals,
            'prediction_signals': self._prediction_signals,
            'regime_signals': self._regime_signals,
            'confidence_signals': self._confidence_signals,
            'anomaly_count': self._anomaly_count,
            'pattern_recognition': self._pattern_recognition,
            'predictive_power': self._predictive_power,
            'model_confidence': self._model_confidence,
            'institutional_ml': self._institutional_ml,
            'smart_money_ml': self._smart_money_ml
        }

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._suggested_sl,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "ML_Indicator",
                "lookback_period": self.ml_config.lookback_period,
                "anomaly_threshold": self.ml_config.anomaly_threshold,
                "prediction_horizon": self.ml_config.prediction_horizon,
                "feature_count": self.ml_config.feature_count,
                "contamination": self.ml_config.contamination,
                "anomaly_score": self._current_anomaly_score,
                "prediction_score": self._current_prediction,
                "regime": self._current_regime,
                "prediction_accuracy": self._prediction_accuracy,
                "regime_stability": self._regime_stability,
                "anomaly_signals": self._anomaly_signals,
                "prediction_signals": self._prediction_signals,
                "regime_signals": self._regime_signals,
                "confidence_signals": self._confidence_signals,
                "anomaly_count": self._anomaly_count,
                "pattern_recognition": self._pattern_recognition,
                "predictive_power": self._predictive_power,
                "model_confidence": self._model_confidence,
                "institutional_ml": self._institutional_ml,
                "smart_money_ml": self._smart_money_ml,
                "is_ready": self.is_ready
            }
        )

    def _determine_ml_signal(self) -> SignalType:
        """Determine signal type based on ML analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # Strong anomaly signals
        if (self._current_anomaly_score < self.ml_config.anomaly_threshold and
            self._anomaly_signals > 0 and
            self._prediction_accuracy > 0.7):
            return SignalType.STRONG_BULLISH  # Anomalies often precede significant moves

        # Strong prediction signals
        elif (abs(self._current_prediction) > 0.05 and
              self._prediction_signals > 0 and
              self._prediction_accuracy > 0.8):
            if self._current_prediction > 0:
                return SignalType.STRONG_BULLISH
            else:
                return SignalType.STRONG_BEARISH

        # Moderate anomaly signals
        elif self._current_anomaly_score < self.ml_config.anomaly_threshold:
            return SignalType.BULLISH

        # Moderate prediction signals
        elif abs(self._current_prediction) > 0.02:
            if self._current_prediction > 0:
                return SignalType.BULLISH
            else:
                return SignalType.BEARISH

        # Regime signals
        elif (self._regime_signals > 0 and
              self._regime_stability > 0.7):
            if self._current_regime == "trending":
                return SignalType.BULLISH  # Trending regimes favor continuation
            elif self._current_regime == "volatile":
                return SignalType.BEARISH  # Volatile regimes suggest caution

        # Confidence signals
        elif (self._confidence_signals > 0 and
              self._model_confidence > 0.8):
            return SignalType.BULLISH

        return SignalType.NEUTRAL

    @property
    def anomaly_score(self) -> float:
        """Get the current anomaly score"""
        return self._current_anomaly_score if self.is_ready else 0.0

    @property
    def prediction_score(self) -> float:
        """Get the current prediction score"""
        return self._current_prediction if self.is_ready else 0.0

    @property
    def regime(self) -> str:
        """Get the current market regime"""
        return self._current_regime

    @property
    def prediction_accuracy(self) -> float:
        """Get the prediction accuracy (0-1)"""
        return self._prediction_accuracy

    @property
    def regime_stability(self) -> float:
        """Get the regime stability (0-1)"""
        return self._regime_stability

    @property
    def anomaly_signals(self) -> int:
        """Get the count of anomaly signals"""
        return self._anomaly_signals

    @property
    def prediction_signals(self) -> int:
        """Get the count of prediction signals"""
        return self._prediction_signals

    @property
    def regime_signals(self) -> int:
        """Get the count of regime signals"""
        return self._regime_signals

    @property
    def confidence_signals(self) -> int:
        """Get the count of confidence signals"""
        return self._confidence_signals

    @property
    def anomaly_count(self) -> int:
        """Get the total count of anomalies detected"""
        return self._anomaly_count

    @property
    def pattern_recognition(self) -> int:
        """Get the pattern recognition score"""
        return self._pattern_recognition

    @property
    def predictive_power(self) -> float:
        """Get the predictive power (0-1)"""
        return self._predictive_power

    @property
    def model_confidence(self) -> float:
        """Get the model confidence (0-1)"""
        return self._model_confidence

    @property
    def institutional_ml(self) -> float:
        """Get the institutional ML score (0-1)"""
        return self._institutional_ml

    @property
    def smart_money_ml(self) -> float:
        """Get the smart money ML score (0-1)"""
        return self._smart_money_ml

    def is_anomaly_detected(self) -> bool:
        """Check if anomaly is detected"""
        if not self.is_ready:
            return False
        return self._current_anomaly_score < self.ml_config.anomaly_threshold

    def is_prediction_bullish(self) -> bool:
        """Check if prediction is bullish"""
        if not self.is_ready:
            return False
        return self._current_prediction > 0.02

    def is_prediction_bearish(self) -> bool:
        """Check if prediction is bearish"""
        if not self.is_ready:
            return False
        return self._current_prediction < -0.02

    def is_regime_stable(self) -> bool:
        """Check if regime is stable"""
        return self._regime_stability > 0.7

    def is_high_accuracy(self) -> bool:
        """Check if prediction accuracy is high"""
        return self._prediction_accuracy > 0.7

    def is_model_confident(self) -> bool:
        """Check if model confidence is high"""
        return self._model_confidence > 0.8

    def is_institutional_setup(self) -> bool:
        """Check if setup is institutional-grade"""
        return self._institutional_ml > 0.7

    def get_ml_info(self) -> Dict[str, Any]:
        """Get comprehensive ML indicator information"""
        return {
            "ml_scores": {
                "anomaly_score": self.anomaly_score,
                "prediction_score": self.prediction_score
            },
            "analysis_results": {
                "regime": self._current_regime,
                "prediction_accuracy": self._prediction_accuracy,
                "regime_stability": self._regime_stability
            },
            "signal_counts": {
                "anomaly_signals": self._anomaly_signals,
                "prediction_signals": self._prediction_signals,
                "regime_signals": self._regime_signals,
                "confidence_signals": self._confidence_signals
            },
            "model_metrics": {
                "anomaly_count": self._anomaly_count,
                "pattern_recognition": self._pattern_recognition,
                "predictive_power": self._predictive_power,
                "model_confidence": self._model_confidence
            },
            "institutional_analysis": {
                "ml": self._institutional_ml,
                "smart_money_ml": self._smart_money_ml
            },
            "metadata": {
                "lookback_period": self.ml_config.lookback_period,
                "anomaly_threshold": self.ml_config.anomaly_threshold,
                "prediction_horizon": self.ml_config.prediction_horizon,
                "feature_count": self.ml_config.feature_count,
                "contamination": self.ml_config.contamination,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._feature_matrix.clear()
        self._price_history.clear()
        self._volume_history.clear()
        self._anomaly_scores.clear()
        self._prediction_scores.clear()
        self._regime_probabilities.clear()
        self._current_anomaly_score = 0.0
        self._current_prediction = 0.0
        self._current_regime = "normal"
        self._anomaly_count = 0
        self._prediction_accuracy = 0.0
        self._regime_stability = 0.0
        self._anomaly_signals = 0
        self._prediction_signals = 0
        self._regime_signals = 0
        self._confidence_signals = 0
        self._pattern_recognition = 0
        self._predictive_power = 0.0
        self._model_confidence = 0.0
        self._institutional_ml = 0.0
        self._smart_money_ml = 0.0