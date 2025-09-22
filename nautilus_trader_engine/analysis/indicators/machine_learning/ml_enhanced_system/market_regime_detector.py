import logging
from collections import deque
from datetime import datetime
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from .data_models import MLConfig, MarketRegime, MarketRegimeData

logger = logging.getLogger(__name__)


class MarketRegimeDetector:
    """Dynamic market regime detection system"""

    def __init__(self, config: MLConfig):
        self.config = config
        self.regime_history = deque(maxlen=config.regime_lookback_period * 2)
        self.feature_history = deque(maxlen=config.regime_lookback_period * 2)

        # Initialize models if sklearn is available
        if SKLEARN_AVAILABLE:
            self.regime_classifier = RandomForestClassifier(
                n_estimators=100, max_depth=10, random_state=42
            )
            self.scaler = StandardScaler()
            self.model_trained = False
        else:
            self.regime_classifier = None
            self.scaler = None
            self.model_trained = False

        # Regime detection thresholds
        self.volatility_thresholds = {
            "low": 0.01,
            "normal": 0.03,
            "high": 0.06,
        }

        self.trend_thresholds = {
            "weak": 0.02,
            "moderate": 0.05,
            "strong": 0.10,
        }

    def detect_regime(
        self, price_data: List[float], volume_data: List[float], timestamp: datetime
    ) -> MarketRegimeData:
        """Detect current market regime"""
        if len(price_data) < 20:
            return MarketRegimeData(
                regime=MarketRegime.UNKNOWN,
                confidence=0.0,
                volatility=0.0,
                trend_strength=0.0,
                momentum=0.0,
                volume_profile="unknown",
                timestamp=timestamp,
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
            volatility=features["volatility"],
            trend_strength=features["trend_strength"],
            momentum=features["momentum"],
            volume_profile=features["volume_profile"],
            timestamp=timestamp,
            features=features,
        )

        self.regime_history.append(regime_data)
        self.feature_history.append(features)

        # Train model periodically
        if len(self.regime_history) >= 50 and len(self.regime_history) % 20 == 0:
            self._update_model()

        return regime_data

    def _calculate_regime_features(
        self, prices: List[float], volumes: List[float]
    ) -> Dict[str, float]:
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
            volume_trend = (
                np.corrcoef(range(len(volumes[-10:])), volumes[-10:])[0, 1]
                if len(volumes) >= 10
                else 0
            )
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
            price_range = (np.max(prices[-5:]) - np.min(prices[-5:])) / np.mean(
                prices[-5:]
            )
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
            "volatility": volatility,
            "trend_strength": trend_strength,
            "trend_direction": trend_direction,
            "momentum": momentum,
            "volume_ratio": current_volume_ratio,
            "volume_trend": volume_trend,
            "volume_profile": volume_profile,
            "price_range": price_range,
            "breakout_score": breakout_score,
            "returns_skew": (
                float(pd.Series(returns[-20:]).skew()) if len(returns) >= 20 else 0
            ),
            "returns_kurtosis": (
                float(pd.Series(returns[-20:]).kurtosis()) if len(returns) >= 20 else 0
            ),
        }

    def _rule_based_regime_detection(
        self, features: Dict[str, float]
    ) -> Tuple[MarketRegime, float]:
        """Rule-based regime detection fallback"""
        volatility = features["volatility"]
        trend_strength = features["trend_strength"]
        momentum = features["momentum"]
        breakout_score = features["breakout_score"]

        # High volatility regime
        if volatility > self.volatility_thresholds["high"]:
            return MarketRegime.HIGH_VOLATILITY, 0.8

        # Low volatility regime
        if volatility < self.volatility_thresholds["low"]:
            return MarketRegime.LOW_VOLATILITY, 0.8

        # Breakout regime
        if abs(breakout_score) > 0.5 and volatility > self.volatility_thresholds["normal"]:
            return MarketRegime.BREAKOUT, 0.7

        # Trending regimes
        if trend_strength > self.trend_thresholds["moderate"]:
            if momentum > 0:
                return MarketRegime.TRENDING_UP, 0.75
            else:
                return MarketRegime.TRENDING_DOWN, 0.75

        # Ranging regime (default)
        return MarketRegime.RANGING, 0.6

    def _ml_regime_detection(
        self, features: Dict[str, float]
    ) -> Tuple[MarketRegime, float]:
        """ML-based regime detection"""
        if not SKLEARN_AVAILABLE or not self.model_trained:
            return self._rule_based_regime_detection(features)

        try:
            # Prepare features for prediction
            feature_vector = np.array(
                [
                    features["volatility"],
                    features["trend_strength"],
                    features["momentum"],
                    features["volume_ratio"],
                    features["price_range"],
                    features["breakout_score"],
                ]
            ).reshape(1, -1)

            # Scale features
            feature_vector_scaled = self.scaler.transform(feature_vector)

            # Predict regime
            regime_pred = self.regime_classifier.predict(feature_vector_scaled)[0]
            confidence = np.max(
                self.regime_classifier.predict_proba(feature_vector_scaled)[0]
            )

            # Convert prediction to MarketRegime
            regime_map = {
                0: MarketRegime.RANGING,
                1: MarketRegime.TRENDING_UP,
                2: MarketRegime.TRENDING_DOWN,
                3: MarketRegime.HIGH_VOLATILITY,
                4: MarketRegime.LOW_VOLATILITY,
                5: MarketRegime.BREAKOUT,
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

            for i, (regime_data, features) in enumerate(
                zip(self.regime_history, self.feature_history)
            ):
                if i < len(self.regime_history) - 10:  # Don't use most recent data for training
                    feature_vector = [
                        features["volatility"],
                        features["trend_strength"],
                        features["momentum"],
                        features["volume_ratio"],
                        features["price_range"],
                        features["breakout_score"],
                    ]
                    X.append(feature_vector)

                    # Map regime to numeric label
                    regime_map = {
                        MarketRegime.RANGING: 0,
                        MarketRegime.TRENDING_UP: 1,
                        MarketRegime.TRENDING_DOWN: 2,
                        MarketRegime.HIGH_VOLATILITY: 3,
                        MarketRegime.LOW_VOLATILITY: 4,
                        MarketRegime.BREAKOUT: 5,
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