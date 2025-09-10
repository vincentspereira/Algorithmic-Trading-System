"""Tests for ML Trading Strategy"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from nautilus_trader_engine.ml.ml_strategy import (
    MLTradingStrategy, MLStrategyConfig, MLSignal, MLTradeDecision,
    MLSignalType, ModelEnsembleMethod, get_ml_strategy
)
from nautilus_trader_engine.ml.model_training import ModelType, PredictionHorizon
from nautilus_trader_engine.core.order_management import OrderType


class TestMLStrategyConfig:
    """Test ML strategy configuration"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = MLStrategyConfig(strategy_id="test_ml")
        
        assert config.model_types == [ModelType.RANDOM_FOREST, ModelType.XGBOOST]
        assert config.prediction_horizon == PredictionHorizon.DAILY
        assert config.ensemble_method == ModelEnsembleMethod.WEIGHTED_AVERAGE
        assert config.signal_threshold == 0.02
        assert config.confidence_threshold == 0.6
        assert config.base_position_size == 0.1
        assert config.max_position_size == 0.3
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = MLStrategyConfig(
            strategy_id="custom_ml",
            model_types=[ModelType.LINEAR_REGRESSION],
            prediction_horizon=PredictionHorizon.WEEKLY,
            signal_threshold=0.05,
            confidence_threshold=0.8
        )
        
        assert config.model_types == [ModelType.LINEAR_REGRESSION]
        assert config.prediction_horizon == PredictionHorizon.WEEKLY
        assert config.signal_threshold == 0.05
        assert config.confidence_threshold == 0.8


class TestMLSignal:
    """Test ML signal class"""
    
    def test_signal_creation(self):
        """Test ML signal creation"""
        signal = MLSignal(
            symbol="AAPL",
            signal_type=MLSignalType.BUY,
            strength=0.8,
            confidence=0.9,
            predicted_return=0.05,
            prediction_horizon=PredictionHorizon.DAILY,
            model_ids=["model_1", "model_2"],
            feature_count=20,
            signal_time=datetime.now(),
            valid_until=datetime.now() + timedelta(days=1)
        )
        
        assert signal.symbol == "AAPL"
        assert signal.signal_type == MLSignalType.BUY
        assert signal.strength == 0.8
        assert signal.confidence == 0.9
        assert signal.predicted_return == 0.05
        assert len(signal.model_ids) == 2


class TestMLTradingStrategy:
    """Test ML trading strategy"""
    
    @pytest.fixture
    def mock_config(self):
        """Mock strategy configuration"""
        return MLStrategyConfig(
            strategy_id="test_ml",
            symbols=["AAPL", "GOOGL"],
            signal_threshold=0.02,
            confidence_threshold=0.6
        )
    
    @pytest.fixture
    def mock_strategy(self, mock_config):
        """Mock ML strategy instance"""
        with patch('nautilus_trader_engine.ml.ml_strategy.get_feature_pipeline'), \
             patch('nautilus_trader_engine.ml.ml_strategy.get_model_trainer'):
            strategy = MLTradingStrategy(mock_config)
            return strategy
    
    @pytest.fixture
    def sample_market_data(self):
        """Sample market data for testing"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        data = pd.DataFrame({
            'open': np.random.uniform(100, 200, 100),
            'high': np.random.uniform(150, 250, 100),
            'low': np.random.uniform(50, 150, 100),
            'close': np.random.uniform(100, 200, 100),
            'volume': np.random.uniform(1000000, 5000000, 100)
        }, index=dates)
        
        return {"AAPL": data, "GOOGL": data.copy()}
    
    def test_strategy_initialization(self, mock_strategy):
        """Test strategy initialization"""
        assert isinstance(mock_strategy, MLTradingStrategy)
        assert mock_strategy.ml_config.strategy_id == "test_ml"
        assert mock_strategy.active_models == {}
        assert mock_strategy.model_weights == {}
    
    def test_data_validation(self, mock_strategy, sample_market_data):
        """Test data quality validation"""
        # Valid data
        valid_data = sample_market_data["AAPL"]
        assert mock_strategy._validate_data_quality(valid_data) == True
        
        # Insufficient data
        insufficient_data = valid_data.head(10)
        mock_strategy.ml_config.min_data_points = 50
        assert mock_strategy._validate_data_quality(insufficient_data) == False
        
        # Missing columns
        invalid_data = valid_data.drop(columns=['close'])
        assert mock_strategy._validate_data_quality(invalid_data) == False
    
    def test_prediction_combination_simple_average(self, mock_strategy):
        """Test simple average ensemble method"""
        mock_strategy.ml_config.ensemble_method = ModelEnsembleMethod.SIMPLE_AVERAGE
        
        predictions = [0.05, 0.03, 0.07]
        confidences = [0.8, 0.9, 0.7]
        model_ids = ["model_1", "model_2", "model_3"]
        
        ensemble_pred, ensemble_conf = mock_strategy._combine_predictions(
            predictions, confidences, model_ids
        )
        
        assert ensemble_pred == pytest.approx(0.05, rel=1e-2)
        assert ensemble_conf == pytest.approx(0.8, rel=1e-2)
    
    def test_prediction_combination_weighted_average(self, mock_strategy):
        """Test weighted average ensemble method"""
        mock_strategy.ml_config.ensemble_method = ModelEnsembleMethod.WEIGHTED_AVERAGE
        mock_strategy.model_weights = {
            "model_1": 0.5,
            "model_2": 0.3,
            "model_3": 0.2
        }
        
        predictions = [0.06, 0.04, 0.02]
        confidences = [0.9, 0.8, 0.7]
        model_ids = ["model_1", "model_2", "model_3"]
        
        ensemble_pred, ensemble_conf = mock_strategy._combine_predictions(
            predictions, confidences, model_ids
        )
        
        expected_pred = 0.06 * 0.5 + 0.04 * 0.3 + 0.02 * 0.2
        expected_conf = 0.9 * 0.5 + 0.8 * 0.3 + 0.7 * 0.2
        
        assert ensemble_pred == pytest.approx(expected_pred, rel=1e-2)
        assert ensemble_conf == pytest.approx(expected_conf, rel=1e-2)
    
    def test_prediction_to_signal_buy(self, mock_strategy):
        """Test converting positive prediction to buy signal"""
        prediction = 0.05  # Above threshold
        confidence = 0.8   # Above threshold
        model_ids = ["model_1"]
        
        signal = mock_strategy._prediction_to_signal(
            "AAPL", prediction, confidence, model_ids
        )
        
        assert signal is not None
        assert signal.symbol == "AAPL"
        assert signal.signal_type == MLSignalType.STRONG_BUY
        assert signal.confidence == 0.8
        assert signal.predicted_return == 0.05
    
    def test_prediction_to_signal_sell(self, mock_strategy):
        """Test converting negative prediction to sell signal"""
        prediction = -0.03  # Below negative threshold
        confidence = 0.7    # Above threshold
        model_ids = ["model_1"]
        
        signal = mock_strategy._prediction_to_signal(
            "AAPL", prediction, confidence, model_ids
        )
        
        assert signal is not None
        assert signal.signal_type == MLSignalType.SELL
        assert signal.predicted_return == -0.03
    
    def test_prediction_to_signal_hold(self, mock_strategy):
        """Test converting weak prediction to hold signal"""
        prediction = 0.01  # Below threshold
        confidence = 0.8   # Above threshold
        model_ids = ["model_1"]
        
        signal = mock_strategy._prediction_to_signal(
            "AAPL", prediction, confidence, model_ids
        )
        
        assert signal is not None
        assert signal.signal_type == MLSignalType.HOLD
    
    def test_prediction_to_signal_low_confidence(self, mock_strategy):
        """Test rejecting low confidence predictions"""
        prediction = 0.05  # Above threshold
        confidence = 0.5   # Below threshold
        model_ids = ["model_1"]
        
        signal = mock_strategy._prediction_to_signal(
            "AAPL", prediction, confidence, model_ids
        )
        
        assert signal is None
    
    def test_position_size_calculation(self, mock_strategy):
        """Test position size calculation"""
        signal = MLSignal(
            symbol="AAPL",
            signal_type=MLSignalType.BUY,
            strength=0.8,
            confidence=0.9,
            predicted_return=0.05,
            prediction_horizon=PredictionHorizon.DAILY,
            model_ids=["model_1"],
            feature_count=20,
            signal_time=datetime.now(),
            valid_until=datetime.now() + timedelta(days=1)
        )
        
        current_position = 0.0
        target_position = mock_strategy._calculate_position_size(signal, current_position)
        
        # With position scaling: base_size * strength * confidence
        expected_size = 0.1 * 0.8 * 0.9  # 0.072
        assert target_position == pytest.approx(expected_size, rel=1e-2)
    
    def test_position_size_max_limit(self, mock_strategy):
        """Test position size maximum limit"""
        signal = MLSignal(
            symbol="AAPL",
            signal_type=MLSignalType.STRONG_BUY,
            strength=1.0,
            confidence=1.0,
            predicted_return=0.10,
            prediction_horizon=PredictionHorizon.DAILY,
            model_ids=["model_1"],
            feature_count=20,
            signal_time=datetime.now(),
            valid_until=datetime.now() + timedelta(days=1)
        )
        
        # Set high base position to test max limit
        mock_strategy.ml_config.base_position_size = 0.5
        
        current_position = 0.0
        target_position = mock_strategy._calculate_position_size(signal, current_position)
        
        # Should be capped at max_position_size (0.3)
        assert target_position == 0.3
    
    def test_determine_action(self, mock_strategy):
        """Test action determination"""
        # Buy action
        action, quantity = mock_strategy._determine_action(0.0, 0.1)
        assert action == "buy"
        assert quantity == 0.1
        
        # Sell action
        action, quantity = mock_strategy._determine_action(0.1, 0.0)
        assert action == "sell"
        assert quantity == 0.1
        
        # Hold action (minimal change)
        action, quantity = mock_strategy._determine_action(0.1, 0.105)
        assert action == "hold"
        assert quantity == 0.0
    
    @pytest.mark.asyncio
    async def test_generate_signals_no_models(self, mock_strategy, sample_market_data):
        """Test signal generation with no active models"""
        # No active models
        mock_strategy.active_models = {}
        
        signals = await mock_strategy.generate_signals(sample_market_data)
        assert len(signals) == 0
    
    @pytest.mark.asyncio
    async def test_make_trading_decisions_hold_signal(self, mock_strategy):
        """Test trading decisions with hold signals"""
        hold_signal = MLSignal(
            symbol="AAPL",
            signal_type=MLSignalType.HOLD,
            strength=0.0,
            confidence=0.8,
            predicted_return=0.01,
            prediction_horizon=PredictionHorizon.DAILY,
            model_ids=["model_1"],
            feature_count=20,
            signal_time=datetime.now(),
            valid_until=datetime.now() + timedelta(days=1)
        )
        
        decisions = await mock_strategy.make_trading_decisions([hold_signal], {})
        assert len(decisions) == 0
    
    def test_risk_adjustment(self, mock_strategy):
        """Test risk adjustment application"""
        signal = MLSignal(
            symbol="AAPL",
            signal_type=MLSignalType.BUY,
            strength=0.8,
            confidence=0.7,  # Lower confidence
            predicted_return=0.05,
            prediction_horizon=PredictionHorizon.DAILY,
            model_ids=["model_1"],
            feature_count=20,
            signal_time=datetime.now(),
            valid_until=datetime.now() + timedelta(days=1)
        )
        
        original_quantity = 0.1
        adjusted_quantity = mock_strategy._apply_risk_adjustment(
            original_quantity, signal, 0.0
        )
        
        # Should be adjusted down due to lower confidence
        assert adjusted_quantity < original_quantity
        assert adjusted_quantity >= 0.01  # Minimum position size
    
    def test_performance_summary(self, mock_strategy):
        """Test ML performance summary"""
        # Add some mock signal history
        mock_strategy.signal_history = [
            MLSignal(
                symbol="AAPL",
                signal_type=MLSignalType.BUY,
                strength=0.8,
                confidence=0.9,
                predicted_return=0.05,
                prediction_horizon=PredictionHorizon.DAILY,
                model_ids=["model_1"],
                feature_count=20,
                signal_time=datetime.now(),
                valid_until=datetime.now() + timedelta(days=1)
            )
        ]
        
        # Add mock active models
        mock_strategy.active_models = {
            "model_1": {
                'symbol': 'AAPL',
                'model_type': ModelType.RANDOM_FOREST,
                'performance': Mock(test_r2=0.75),
                'training_date': datetime.now()
            }
        }
        mock_strategy.model_weights = {"model_1": 1.0}
        
        summary = mock_strategy.get_ml_performance_summary()
        
        assert 'strategy_config' in summary
        assert 'active_models' in summary
        assert 'performance_metrics' in summary
        assert summary['active_models'] == 1
        assert summary['performance_metrics']['total_signals'] == 1


class TestMLStrategyIntegration:
    """Integration tests for ML strategy"""
    
    @pytest.mark.asyncio
    async def test_full_signal_generation_pipeline(self):
        """Test complete signal generation pipeline"""
        config = MLStrategyConfig(
            strategy_id="integration_test",
            symbols=["AAPL"],
            signal_threshold=0.02,
            confidence_threshold=0.6
        )
        
        with patch('nautilus_trader_engine.ml.ml_strategy.get_feature_pipeline'), \
             patch('nautilus_trader_engine.ml.ml_strategy.get_model_trainer') as mock_trainer:
            
            # Mock model trainer
            mock_trainer.return_value.predict.return_value = Mock(
                predicted_value=0.05,
                prediction_confidence=0.8
            )
            
            strategy = MLTradingStrategy(config)
            
            # Mock active models
            strategy.active_models = {
                "model_1": {
                    'symbol': 'AAPL',
                    'model_type': ModelType.RANDOM_FOREST,
                    'performance': Mock(test_r2=0.75),
                    'training_date': datetime.now()
                }
            }
            strategy.model_weights = {"model_1": 1.0}
            
            # Create sample market data
            dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
            market_data = {
                "AAPL": pd.DataFrame({
                    'open': np.random.uniform(100, 200, 100),
                    'high': np.random.uniform(150, 250, 100),
                    'low': np.random.uniform(50, 150, 100),
                    'close': np.random.uniform(100, 200, 100),
                    'volume': np.random.uniform(1000000, 5000000, 100)
                }, index=dates)
            }
            
            # Generate signals
            signals = await strategy.generate_signals(market_data)
            
            assert len(signals) == 1
            assert signals[0].symbol == "AAPL"
            assert signals[0].signal_type == MLSignalType.STRONG_BUY
            assert signals[0].confidence == 0.8
    
    def test_global_strategy_instance(self):
        """Test global strategy instance management"""
        config = MLStrategyConfig(strategy_id="global_test")
        
        with patch('nautilus_trader_engine.ml.ml_strategy.get_feature_pipeline'), \
             patch('nautilus_trader_engine.ml.ml_strategy.get_model_trainer'):
            
            strategy1 = get_ml_strategy(config)
            strategy2 = get_ml_strategy()
            
            # Should return the same instance
            assert strategy1 is strategy2
            assert strategy1.ml_config.strategy_id == "global_test"


if __name__ == "__main__":
    pytest.main([__file__])