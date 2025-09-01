
import pytest
from unittest.mock import AsyncMock, patch

from app.services.kafka_manager import KafkaManager

@pytest.fixture
def kafka_manager():
    with patch('aiokafka.AIOKafkaProducer') as MockProducer:
        with patch('aiokafka.AIOKafkaConsumer') as MockConsumer:
            manager = KafkaManager()
            manager.producer = MockProducer.return_value
            manager.consumer = MockConsumer.return_value
            yield manager

@pytest.mark.asyncio
async def test_kafka_manager_initialize(kafka_manager):
    kafka_manager.producer.start = AsyncMock()
    result = await kafka_manager.initialize()
    assert result is True
    kafka_manager.producer.start.assert_called_once()

@pytest.mark.asyncio
async def test_kafka_manager_send_message(kafka_manager):
    kafka_manager.producer.send_and_wait = AsyncMock()
    await kafka_manager.send_message("test_topic", {"key": "value"})
    kafka_manager.producer.send_and_wait.assert_called_once_with("test_topic", {"key": "value"})
