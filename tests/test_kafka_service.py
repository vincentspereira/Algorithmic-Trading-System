
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from services.kafka_service import KafkaService

@pytest.fixture
def kafka_service():
    service = KafkaService(bootstrap_servers='mock_servers')
    service.kafka_client = MagicMock()
    service.kafka_client.connect = AsyncMock()
    service.kafka_client.disconnect = AsyncMock()
    service.kafka_client.send_message = AsyncMock()
    service.kafka_client.consume_messages = AsyncMock()
    service.kafka_client.create_topic = MagicMock()
    return service

@pytest.mark.asyncio
async def test_start(kafka_service):
    await kafka_service.start()
    kafka_service.kafka_client.connect.assert_called_once()
    kafka_service.kafka_client.create_topic.assert_called_with('trading_events')

@pytest.mark.asyncio
async def test_stop(kafka_service):
    await kafka_service.stop()
    kafka_service.kafka_client.disconnect.assert_called_once()

@pytest.mark.asyncio
async def test_process_trading_event(kafka_service):
    trading_event = {'type': 'BUY', 'symbol': 'AAPL', 'quantity': 100}
    await kafka_service.process_trading_event(trading_event)
    kafka_service.kafka_client.send_message.assert_called_with(
        'processed_trading_events', 
        {'status': 'processed', 'original_event': trading_event}
    )

@pytest.mark.asyncio
async def test_consume_events(kafka_service):
    await kafka_service.consume_events()
    kafka_service.kafka_client.consume_messages.assert_called_once()

