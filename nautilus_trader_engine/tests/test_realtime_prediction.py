import pytest
import asyncio
from nautilus_trader_engine.services.realtime_prediction import RealtimePredictionEngine

# Mock classes for dependencies
class MockModelManager:
    def get_model(self, model_name):
        print(f"Mock-loading model: {model_name}")
        return None

class MockKafkaProducer:
    def __init__(self):
        self.sent_messages = []
    
    async def send(self, topic, message):
        self.sent_messages.append((topic, message))
        print(f"Mock Kafka: Sent to {topic}: {message}")

@pytest.fixture
def prediction_engine():
    """Fixture to create a RealtimePredictionEngine instance for testing."""
    model_manager = MockModelManager()
    kafka_producer = MockKafkaProducer()
    return RealtimePredictionEngine(model_manager, kafka_producer)

@pytest.mark.asyncio
async def test_subscribe_and_get_prediction(prediction_engine):
    """
    Tests subscribing to a symbol and getting a single prediction.
    """
    symbol = "TEST.MOCK.1"
    prediction_engine.subscribe_to_symbol(symbol)
    
    assert symbol in prediction_engine.symbols
    
    prediction = await prediction_engine.get_prediction(symbol)
    
    assert prediction["symbol"] == symbol
    assert "timestamp" in prediction
    assert "predictions" in prediction
    assert "1min" in prediction["predictions"]
    assert "confidence" in prediction["predictions"]["1min"]

@pytest.mark.asyncio
async def test_get_prediction_unsubscribed_symbol(prediction_engine):
    """
    Tests that getting a prediction for an unsubscribed symbol returns an error.
    """
    prediction = await prediction_engine.get_prediction("UNSEEN.SYMBOL")
    assert "error" in prediction
    assert prediction["error"] == "Symbol not tracked"

@pytest.mark.asyncio
async def test_get_historical_predictions(prediction_engine):
    """
    Tests the generation of mock historical predictions.
    """
    symbol = "TEST.MOCK.HIST"
    limit = 50
    prediction_engine.subscribe_to_symbol(symbol)
    
    historical_data = await prediction_engine.get_historical_predictions(symbol, limit=limit)
    
    assert isinstance(historical_data, list)
    assert len(historical_data) == limit
    
    first_item = historical_data[0]
    assert first_item["symbol"] == symbol
    assert "timestamp" in first_item
    assert "predictions" in first_item

@pytest.mark.asyncio
async def test_unsubscribe_symbol(prediction_engine):
    """
    Tests that unsubscribing removes the symbol from the tracking set.
    """
    symbol = "TEST.MOCK.2"
    prediction_engine.subscribe_to_symbol(symbol)
    assert symbol in prediction_engine.symbols
    
    prediction_engine.unsubscribe_from_symbol(symbol)
    assert symbol not in prediction_engine.symbols
    
    # After unsubscribing, getting a prediction should fail
    prediction = await prediction_engine.get_prediction(symbol)
    assert "error" in prediction

@pytest.mark.asyncio
async def test_prediction_loop_integration(prediction_engine):
    """
    A small integration test for the prediction loop.
    This test is time-based and might be flaky in some CI environments.
    """
    symbol1 = "MOCK.LOOP.1"
    symbol2 = "MOCK.LOOP.2"
    prediction_engine.subscribe_to_symbol(symbol1)
    prediction_engine.subscribe_to_symbol(symbol2)

    # We can't run the infinite loop in a test, but we can call the get_prediction method
    # that the loop would use. In a real scenario with a real Kafka consumer,
    # this test would be more involved.

    # This is a simplified check to ensure `get_prediction` works for multiple symbols.
    p1 = await prediction_engine.get_prediction(symbol1)
    p2 = await prediction_engine.get_prediction(symbol2)

    assert p1["symbol"] == symbol1
    assert p2["symbol"] == symbol2

# To run these tests, you would use `pytest` in your terminal.
# The tests are designed to be self-contained and use mock objects to avoid
# dependencies on external systems like Kafka or a real model registry.