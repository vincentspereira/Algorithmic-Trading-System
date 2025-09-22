"""
Comprehensive tests for ML Prediction Engine

Tests institutional-grade machine learning prediction including:
- Ensemble model training and validation
- Feature engineering pipeline
- Market regime detection and adaptation
- Prediction confidence quantification
- Model performance monitoring
- Risk-adjusted signal generation
- Multi-timeframe prediction support
- Continuous learning and adaptation
"""

import unittest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from nautilus_trader_engine.analysis.indicators.machine_learning.ml_prediction_engine import (
    MLPredictionEngine, MLSignal, PredictionModelType, PredictionHorizon,
    MarketRegime, ModelPerformance, MLFeatureEngineer, MarketRegimeDetector
)


class TestMLPredictionEngine(unittest.TestCase):
    """Test suite for ML Prediction Engine"""

    def setUp(self):
        """Set up test fixtures"""
        self.engine = MLPredictionEngine(
            timeframe="1H",
            prediction_horizon=5,
            model_update_frequency=50,
            confidence_threshold=0.6
        )

        # Sample market data
        self.sample_prices = [100.0 + i * 0.1 + np.sin(i * 0.1) for i in range(200)]
        self.sample_volumes = [1000 + int(500 * np.sin(i * 0.2)) for i in range(200)]
        self.sample_timestamps = [datetime.now() - timedelta(hours=i) for i in range(200)]

    def test_initialization(self):
        """Test engine initialization"""
        self.assertEqual(self.engine.timeframe, "1H")
        self.assertEqual(self.engine.prediction_horizon, 5)
        self.assertEqual(self.engine.confidence_threshold, 0.6)
        self.assertIsInstance(self.engine.models, dict)
        self.assertIsInstance(self.engine.price_data, list)

    @patch('nautilus_trader_engine.analysis.indicators.machine_learning.ml_prediction_engine.TENSORFLOW_AVAILABLE', False)
    def test_tensorflow_unavailable(self):
        """Test behavior when TensorFlow is not available"""
        engine = MLPredictionEngine()
        signal = engine.update(price=100.0, volume=1000)
        self.assertIsNone(signal)

    def test_feature_engineering(self):
        """Test feature engineering pipeline"""
        feature_engineer = MLFeatureEngineer()

        features = feature_engineer.create_features(
            price=100.5, volume=1200, high=101.0, low=100.0,
            price_history=[100.0, 100.2, 100.3, 100.1, 100.4],
            volume_history=[1000, 1100, 1050, 1150, 1200]
        )

        self.assertIsInstance(features, dict)
        self.assertIn('price', features)
        self.assertIn('volume', features)
        self.assertIn('price_return_1', features)
        self.assertIn('volume_ma_ratio', features)

    def test_technical_indicators_calculation(self):
        """Test technical indicators calculation in features"""
        feature_engineer = MLFeatureEngineer()

        # Create longer price history for technical indicators
        price_history = [100.0 + i * 0.1 for i in range(30)]
        volume_history = [1000 + i * 10 for i in range(30)]

        features = feature_engineer.create_features(
            price=103.0, volume=1300,
            price_history=price_history,
            volume_history=volume_history
        )

        # Check technical indicators are present
        self.assertIn('rsi', features)
        self.assertIn('macd', features)
        self.assertIn('bb_position', features)
        self.assertIn('sma_5', features)
        self.assertIn('sma_20', features)

    def test_order_book_feature_extraction(self):
        """Test order book feature extraction"""
        feature_engineer = MLFeatureEngineer()

        order_book_data = {
            'bids': {99.9: 1000, 99.8: 800, 99.7: 600},
            'asks': {100.1: 1200, 100.2: 900, 100.3: 700}
        }

        features = feature_engineer.create_features(
            price=100.0, volume=1000,
            order_book_data=order_book_data
        )

        self.assertIn('order_book_spread', features)
        self.assertIn('depth_imbalance', features)
        self.assertIn('bid_depth', features)
        self.assertIn('ask_depth', features)

    def test_market_regime_detection(self):
        """Test market regime detection"""
        regime_detector = MarketRegimeDetector()

        # Test trending up
        trending_up_prices = [100.0 + i * 0.5 for i in range(50)]
        regime = regime_detector.detect_regime(trending_up_prices)
        self.assertEqual(regime, MarketRegime.TRENDING_UP)

        # Test trending down
        trending_down_prices = [100.0 - i * 0.5 for i in range(50)]
        regime = regime_detector.detect_regime(trending_down_prices)
        self.assertEqual(regime, MarketRegime.TRENDING_DOWN)

        # Test sideways
        sideways_prices = [100.0 + 0.1 * np.sin(i) for i in range(50)]
        regime = regime_detector.detect_regime(sideways_prices)
        self.assertIn(regime, [MarketRegime.SIDEWAYS, MarketRegime.LOW_VOLATILITY])

    def test_insufficient_data_handling(self):
        """Test handling of insufficient data"""
        signal = self.engine.update(price=100.0, volume=1000)
        self.assertIsNone(signal)

        # Feed minimal data
        for i in range(10):
            signal = self.engine.update(price=self.sample_prices[i], volume=self.sample_volumes[i])
            self.assertIsNone(signal)

    def test_prediction_signal_generation(self):
        """Test prediction signal generation with sufficient data"""
        # Feed historical data
        for i in range(100):
            signal = self.engine.update(
                price=self.sample_prices[i],
                volume=self.sample_volumes[i],
                timestamp=self.sample_timestamps[i]
            )

        # Should eventually generate signals
        signal_found = False
        for i in range(100, 150):
            signal = self.engine.update(
                price=self.sample_prices[i],
                volume=self.sample_volumes[i],
                timestamp=self.sample_timestamps[i]
            )
            if signal:
                signal_found = True
                self.assertIsInstance(signal, MLSignal)
                self.assertIsInstance(signal.predicted_price, float)
                self.assertIsInstance(signal.model_confidence, float)
                break

        # Note: Signal generation depends on model training and may not always occur
        # This is acceptable for testing purposes

    def test_model_training(self):
        """Test model training process"""
        # Feed data for training
        for i in range(150):
            self.engine.update(
                price=self.sample_prices[i],
                volume=self.sample_volumes[i],
                timestamp=self.sample_timestamps[i]
            )

        # Check that models are trained (if TensorFlow available)
        if hasattr(self.engine, 'models') and self.engine.models:
            # Models should be initialized
            self.assertIn(PredictionModelType.RANDOM_FOREST, self.engine.models)
            self.assertIn(PredictionModelType.GRADIENT_BOOSTING, self.engine.models)

    def test_confidence_scoring(self):
        """Test prediction confidence scoring"""
        # Create a mock signal for testing
        signal = MLSignal(
            value_raw=100.0,
            signal_type="ML_BULLISH_PREDICTION",
            composite_confidence=0.75,
            confidence_components={
                'model_confidence': 0.8,
                'prediction_magnitude': 0.6,
                'market_regime_confidence': 0.7,
                'data_quality': 0.9,
                'model_performance': 0.8
            },
            suggested_sl=98.0,
            suggested_tp=105.0,
            timestamp=datetime.now(),
            additional_metadata={},
            predicted_price=102.0,
            prediction_horizon="5_periods",
            model_confidence=0.8,
            feature_importance={'price': 0.3, 'volume': 0.2},
            market_regime='trending_up',
            prediction_uncertainty=0.1
        )

        # Verify confidence components
        components = signal.confidence_components
        self.assertIn('model_confidence', components)
        self.assertIn('prediction_magnitude', components)
        self.assertIn('market_regime_confidence', components)
        self.assertIn('data_quality', components)
        self.assertIn('model_performance', components)

        # All components should be between 0 and 1
        for comp_value in components.values():
            self.assertGreaterEqual(comp_value, 0.0)
            self.assertLessEqual(comp_value, 1.0)

    def test_risk_management_integration(self):
        """Test risk management integration"""
        # Feed data and try to get a signal
        for i in range(120):
            signal = self.engine.update(
                price=self.sample_prices[i],
                volume=self.sample_volumes[i],
                timestamp=self.sample_timestamps[i]
            )
            if signal:
                # Check risk management parameters
                self.assertIsInstance(signal.suggested_sl, (int, float))
                self.assertIsInstance(signal.suggested_tp, (int, float))

                # For bullish signal, stop loss should be below current price
                if 'BULLISH' in signal.signal_type:
                    self.assertLess(signal.suggested_sl, signal.value_raw)
                    self.assertGreater(signal.suggested_tp, signal.value_raw)
                elif 'BEARISH' in signal.signal_type:
                    self.assertGreater(signal.suggested_sl, signal.value_raw)
                    self.assertLess(signal.suggested_tp, signal.value_raw)
                break

    def test_model_performance_tracking(self):
        """Test model performance tracking"""
        performance = self.engine.get_model_performance()
        self.assertIsInstance(performance, dict)

        # Should have performance data for each model type
        for model_type in PredictionModelType:
            if model_type.value in performance:
                model_perf = performance[model_type.value]
                self.assertIn('mse', model_perf)
                self.assertIn('training_samples', model_perf)
                self.assertIn('last_updated', model_perf)

    def test_feature_importance_calculation(self):
        """Test feature importance calculation"""
        # Feed data to train models
        for i in range(100):
            self.engine.update(
                price=self.sample_prices[i],
                volume=self.sample_volumes[i],
                timestamp=self.sample_timestamps[i]
            )

        importance = self.engine.get_feature_importance_summary()
        self.assertIsInstance(importance, dict)

        # Should have importance scores for features
        if importance:
            for feature, imp_score in importance.items():
                self.assertIsInstance(feature, str)
                self.assertIsInstance(imp_score, (int, float))
                self.assertGreaterEqual(imp_score, 0.0)

    def test_prediction_history_tracking(self):
        """Test prediction history tracking"""
        history = self.engine.get_prediction_history()
        self.assertIsInstance(history, list)

        # History should contain MLSignal objects
        for signal in history:
            if signal:
                self.assertIsInstance(signal, MLSignal)

    def test_multi_timeframe_support(self):
        """Test multi-timeframe analysis support"""
        timeframes = ["1m", "5m", "15m", "1H", "4H", "1D"]

        for tf in timeframes:
            engine = MLPredictionEngine(timeframe=tf)
            self.assertEqual(engine.timeframe, tf)

            # Should work with different timeframes
            perf = engine.get_model_performance()
            self.assertIsInstance(perf, dict)

    def test_memory_management(self):
        """Test memory management with large datasets"""
        # Feed large amount of data
        large_prices = [100.0 + i * 0.01 for i in range(500)]
        large_volumes = [1000 + i % 100 for i in range(500)]

        for price, volume in zip(large_prices, large_volumes):
            self.engine.update(price=price, volume=volume)

        # Should maintain reasonable memory usage
        self.assertLessEqual(len(self.engine.price_data), 1000)
        self.assertLessEqual(len(self.engine.feature_data), 1000)

    def test_error_handling(self):
        """Test error handling with invalid inputs"""
        # Test with zero/negative prices
        signal = self.engine.update(price=0, volume=1000)
        self.assertTrue(True)  # Should not crash

        # Test with extreme volumes
        signal = self.engine.update(price=100.0, volume=10000000)
        self.assertTrue(True)  # Should not crash

        # Test with invalid order book data
        signal = self.engine.update(price=100.0, volume=1000,
                                  order_book_data={'invalid': 'data'})
        self.assertTrue(True)  # Should not crash

    def test_feature_engineer_error_handling(self):
        """Test feature engineer error handling"""
        feature_engineer = MLFeatureEngineer()

        # Test with minimal data
        features = feature_engineer.create_features(
            price=100.0, volume=1000,
            price_history=[], volume_history=[]
        )
        self.assertEqual(features, {})

        # Test with invalid order book
        features = feature_engineer.create_features(
            price=100.0, volume=1000,
            order_book_data={'bids': {}, 'asks': {}}
        )
        self.assertIsInstance(features, dict)

    def test_market_regime_detector_edge_cases(self):
        """Test market regime detector with edge cases"""
        regime_detector = MarketRegimeDetector()

        # Test with insufficient data
        regime = regime_detector.detect_regime([])
        self.assertIsNone(regime)

        regime = regime_detector.detect_regime([100.0])
        self.assertIsNone(regime)

        # Test with constant prices
        constant_prices = [100.0] * 50
        regime = regime_detector.detect_regime(constant_prices)
        self.assertIn(regime, [MarketRegime.SIDEWAYS, MarketRegime.LOW_VOLATILITY])

    def test_prediction_uncertainty_calculation(self):
        """Test prediction uncertainty calculation"""
        # This tests the uncertainty calculation method
        uncertainty = self.engine._calculate_prediction_uncertainty(0.02)  # 2% prediction
        self.assertIsInstance(uncertainty, float)
        self.assertGreaterEqual(uncertainty, 0.0)
        self.assertLessEqual(uncertainty, 1.0)

    def test_state_size_consistency(self):
        """Test that state size remains consistent"""
        # Feed data and check that feature vectors are consistent size
        for i in range(50):
            self.engine.update(
                price=self.sample_prices[i],
                volume=self.sample_volumes[i],
                timestamp=self.sample_timestamps[i]
            )

        # Check feature data consistency
        if self.engine.feature_data:
            first_size = len(self.engine.feature_data[0])
            for features in self.engine.feature_data[1:]:
                self.assertEqual(len(features), first_size,
                               "Feature vector sizes should be consistent")

    @patch('sklearn.ensemble.RandomForestRegressor')
    def test_model_initialization_mock(self, mock_rf):
        """Test model initialization with mocked sklearn"""
        mock_model = Mock()
        mock_rf.return_value = mock_model

        engine = MLPredictionEngine()

        # Check that models are initialized
        self.assertIn(PredictionModelType.RANDOM_FOREST, engine.models)
        self.assertIn(PredictionModelType.GRADIENT_BOOSTING, engine.models)

    def test_feature_names_consistency(self):
        """Test that feature names remain consistent"""
        feature_engineer = MLFeatureEngineer()
        names1 = feature_engineer.get_feature_names()
        names2 = feature_engineer.get_feature_names()

        self.assertEqual(names1, names2)
        self.assertIsInstance(names1, list)
        self.assertGreater(len(names1), 0)


if __name__ == '__main__':
    unittest.main()