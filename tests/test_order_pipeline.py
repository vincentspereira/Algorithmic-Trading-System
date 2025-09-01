import pytest
import asyncio
import httpx
from aiokafka import AIOKafkaConsumer
import json
from datetime import datetime

# Assuming the API is running on localhost:8000 and Kafka on localhost:9092
API_URL = "http://localhost:8000"
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"

@pytest.fixture(scope="module")
async def kafka_consumer():
    consumer = AIOKafkaConsumer(
        'order_requests', 'order_status_updates',
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="test_consumer_group",
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='earliest'
    )
    await consumer.start()
    try:
        yield consumer
    finally:
        await consumer.stop()

@pytest.mark.asyncio
async def test_order_submission_pipeline(kafka_consumer):
    # 1. Send an order request to the API
    order_data = {
        "symbol": {"symbol": "TEST", "exchange": "NASDAQ", "asset_class": "STK"},
        "order_type": "MARKET",
        "side": "BUY",
        "quantity": 10.0,
        "price": None,
        "stop_price": None,
        "time_in_force": "DAY"
    }
    headers = {"Authorization": "Bearer demo_token"}

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_URL}/api/v1/orders", json=order_data, headers=headers)

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["success"] is True
    assert "request_id" in response_data["data"]
    request_id = response_data["data"]["request_id"]

    # 2. Verify that the order_requests Kafka topic receives the message
    order_request_received = False
    order_status_received = False

    # Consume messages for a short period
    start_time = datetime.now()
    while (datetime.now() - start_time).total_seconds() < 10: # Wait up to 10 seconds
        try:
            msg = await asyncio.wait_for(kafka_consumer.getone(), timeout=1)
            if msg.topic == 'order_requests':
                if msg.value.get("request_id") == request_id:
                    order_request_received = True
                    print(f"Order request received: {msg.value}")
            elif msg.topic == 'order_status_updates':
                if msg.value.get("request_id") == request_id:
                    order_status_received = True
                    print(f"Order status update received: {msg.value}")

            if order_request_received and order_status_received:
                break
        except asyncio.TimeoutError:
            pass # No message in the last second, continue waiting

    assert order_request_received is True, "Order request not received by Kafka consumer"
    assert order_status_received is True, "Order status update not received by Kafka consumer"
