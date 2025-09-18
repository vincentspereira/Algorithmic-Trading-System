"""
Test suite for enhanced prediction engine
"""

import asyncio
import pytest
import numpy as np
import pandas as pd
from unittest.mock import MagicMock, AsyncMock

from nautilus_trader_engine.ai.prediction_engine import (
    PredictionEngine,
    PredictionType,
    PredictionHorizon,
    MarketPrediction,
    FeatureEngineer,
)
from nautilus_trader_engine.ai.model_manager import ModelManager
from nautilus_trader_engine.ai.inference_engine import InferenceEngine
from nautilus_trader_engine.ai.pattern_recognition import PatternRecognitionEngine
from nautilus_trader_engine.ai.sentiment_analyzer import MarketSentimentAnalyzer


@pytest.fixture
def mock_model_manager():
    return AsyncMock(spec=ModelManager)

@pytest.fixture
def mock_inference_engine():
    return AsyncMock(spec=InferenceEngine)

@pytest.fixture
def mock_pattern_recognizer():
    return AsyncMock(spec=PatternRecognitionEngine)

@pytest.fixture
def mock_sentiment_analyzer():
    return AsyncMock(spec=MarketSentimentAnalyzer)

@pytest.fixture
def prediction_engine(
    mock_model_manager,
    mock_inference_engine,
    mock_pattern_recognizer,
    mock_sentiment_analyzer,
):
    """Instance of PredictionEngine with mocked dependencies."""
    return PredictionEngine(
        model_manager=mock_model_manager,
        inference_engine=mock_inference_engine,
        pattern_recognizer=mock_pattern_recognizer,
        sentiment_analyzer=mock_sentiment_analyzer,
    )

@pytest.mark.asyncio
async def test_prediction_engine_initialization(prediction_engine):
    """
    Tests that the PredictionEngine initializes correctly.
    """
    assert prediction_engine is not None
    assert isinstance(prediction_engine.model_manager, AsyncMock)
    assert isinstance(prediction_engine.inference_engine, AsyncMock)
    assert isinstance(prediction_engine.pattern_recognizer, AsyncMock)
    assert isinstance(prediction_engine.sentiment_analyzer, AsyncMock)

def sample_market_data(rows=100):
    """Generate sample market data."""
    dates = pd.to_datetime(pd.date_range(end=pd.Timestamp.now(), periods=rows, freq='1H'))
    data = {
        'open': np.random.uniform(98, 102, size=rows),
        'high': np.random.uniform(100, 105, size=rows),
        'low': np.random.uniform(95, 100, size=rows),
        'close': np.random.uniform(99, 103, size=rows),
        'volume': np.random.uniform(10000, 50000, size=rows),
    }
    df = pd.DataFrame(data, index=dates)
    # Ensure high is the highest and low is the lowest
    df['high'] = df[['open', 'high', 'low', 'close']].max(axis=1)
    df['low'] = df[['open', 'high', 'low', 'close']].min(axis=1)
    return df

@pytest.mark.asyncio
async def test_predict_price_direction(prediction_engine, mock_inference_engine):
    """
    Tests the predict method for price direction.
    """
    symbol = "AAPL"
    market_data = sample_market_data()
    horizon = PredictionHorizon.SHORT_TERM

    # Mock the inference engine to return a prediction
    mock_prediction = MarketPrediction(
        symbol=symbol,
        prediction_type=PredictionType.PRICE_DIRECTION,
        horizon=horizon,
        predicted_value="up",
        confidence=0.75,
    )
    mock_inference_engine.run_inference.return_value = [mock_prediction]

    predictions = await prediction_engine.predict(
        symbol=symbol,
        market_data=market_data,
        prediction_types=[PredictionType.PRICE_DIRECTION],
        horizon=horizon,
    )

    assert predictions is not None
    assert len(predictions) == 1
    prediction = predictions[0]
    assert isinstance(prediction, MarketPrediction)
    assert prediction.symbol == symbol
    assert prediction.prediction_type == PredictionType.PRICE_DIRECTION
    assert prediction.predicted_value == "up"
    assert prediction.confidence == 0.75
    mock_inference_engine.run_inference.assert_called_once()

def test_feature_engineer():
    """
    Tests the FeatureEngineer.
    """
    feature_engineer = FeatureEngineer()
    market_data = sample_market_data()
    features = feature_engineer.create_technical_features(market_data)
    assert isinstance(features, pd.DataFrame)
    assert 'sma_20' in features.columns
    assert 'rsi' in features.columns
    assert 'macd' in features.columns
    assert not features.isnull().values.any()