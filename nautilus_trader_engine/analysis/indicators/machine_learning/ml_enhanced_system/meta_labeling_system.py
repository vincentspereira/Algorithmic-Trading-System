import logging
from typing import Dict, Tuple

import numpy as np

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from nautilus_trader.model.data import Bar

from .data_models import MLConfig, MetaLabelResult, SignalQuality

logger = logging.getLogger(__name__)


class MetaLabelingSystem:
    """Evaluates trading signals using a meta-labeling model"""

    def __init__(self, config: MLConfig):
        self.config = config
        self.performance_history = []

        if SKLEARN_AVAILABLE:
            self.meta_model = RandomForestClassifier(n_estimators=100, random_state=42)
            self.scaler = StandardScaler()
            self.model_trained = False
        else:
            self.meta_model = None
            self.scaler = None
            self.model_trained = False

    def evaluate_signal(
        self, bar: Bar, primary_signal: int, signal_confidence: float
    ) -> MetaLabelResult:
        """Evaluate a trading signal and decide whether to act on it"""
        meta_features = self._extract_meta_features(bar, primary_signal, signal_confidence)

        if self.model_trained and SKLEARN_AVAILABLE:
            signal_quality, confidence = self._ml_signal_evaluation(meta_features)
        else:
            signal_quality, confidence = self._rule_based_signal_evaluation(
                meta_features
            )

        risk_score = self._calculate_risk_score(meta_features)
        position_size = self._calculate_position_size(risk_score, confidence)

        return MetaLabelResult(
            signal_quality=signal_quality,
            confidence=confidence,
            risk_score=risk_score,
            position_size=position_size,
            meta_features=meta_features,
        )

    def _extract_meta_features(
        self, bar: Bar, primary_signal: int, signal_confidence: float
    ) -> Dict[str, float]:
        """Extract features for the meta-labeling model"""
        return {
            "primary_signal": float(primary_signal),
            "signal_confidence": signal_confidence,
            "volatility": bar.high - bar.low,
            "momentum": bar.close - bar.open,
            "volume": float(bar.volume),
        }

    def _rule_based_signal_evaluation(
        self, meta_features: Dict[str, float]
    ) -> Tuple[SignalQuality, float]:
        """Fallback rule-based signal evaluation"""
        if meta_features["signal_confidence"] < 0.5:
            return SignalQuality.POOR, 0.7
        if meta_features["volatility"] > (bar.close * 0.05):  # High volatility
            return SignalQuality.POOR, 0.6
        if meta_features["signal_confidence"] > 0.8:
            return SignalQuality.GOOD, 0.8

        return SignalQuality.NEUTRAL, 0.5

    def _ml_signal_evaluation(
        self, meta_features: Dict[str, float]
    ) -> Tuple[SignalQuality, float]:
        """ML-based signal evaluation"""
        if not SKLEARN_AVAILABLE or not self.model_trained:
            return self._rule_based_signal_evaluation(meta_features)

        try:
            feature_vector = np.array(list(meta_features.values())).reshape(1, -1)
            feature_vector_scaled = self.scaler.transform(feature_vector)

            prediction = self.meta_model.predict(feature_vector_scaled)[0]
            confidence = np.max(self.meta_model.predict_proba(feature_vector_scaled))

            quality_map = {
                0: SignalQuality.POOR,
                1: SignalQuality.NEUTRAL,
                2: SignalQuality.GOOD,
            }
            return quality_map.get(prediction, SignalQuality.NEUTRAL), confidence
        except Exception as e:
            logger.warning(f"ML signal evaluation failed: {e}. Falling back to rules.")
            return self._rule_based_signal_evaluation(meta_features)

    def _calculate_risk_score(self, meta_features: Dict[str, float]) -> float:
        """Calculate a risk score for the signal"""
        volatility_risk = min(meta_features["volatility"] / 5.0, 1.0)
        confidence_risk = 1.0 - meta_features["signal_confidence"]
        return (volatility_risk * 0.6) + (confidence_risk * 0.4)

    def _calculate_position_size(self, risk_score: float, confidence: float) -> float:
        """Calculate position size based on risk and confidence"""
        base_size = self.config.base_position_size
        if confidence < 0.6:
            return base_size * 0.5
        if risk_score > 0.7:
            return base_size * 0.75
        if confidence > 0.8 and risk_score < 0.4:
            return base_size * 1.5
        return base_size

    def update_performance(self, signal_result: MetaLabelResult, actual_outcome: float):
        """Update with the actual outcome of a trade"""
        self.performance_history.append((signal_result, actual_outcome))
        if len(self.performance_history) % self.config.retrain_interval == 0:
            self._retrain_models()

    def _retrain_models(self):
        """Retrain the meta-labeling model"""
        if not SKLEARN_AVAILABLE or len(self.performance_history) < 50:
            return

        try:
            X = [res.meta_features for res, _ in self.performance_history]
            y = [outcome for _, outcome in self.performance_history]

            # Convert to numerical labels (e.g., profit -> 2, neutral -> 1, loss -> 0)
            y_labels = [2 if o > 0.001 else (0 if o < -0.001 else 1) for o in y]

            X_train, _, y_train, _ = train_test_split(
                X, y_labels, test_size=0.2, random_state=42
            )

            X_train_scaled = self.scaler.fit_transform(X_train)

            self.meta_model.fit(X_train_scaled, y_train)
            self.model_trained = True
            logger.info("Meta-labeling model retrained.")
        except Exception as e:
            logger.error(f"Failed to retrain meta-labeling model: {e}")