
import asyncio
import json
import time
import unittest
import requests
import threading
import uvicorn
from api.main import app
from shared.kafka_client import KafkaClient

class TestVerticalSlice(unittest.TestCase):
    """
    Tests the "vertical slice" of the system, from the API endpoint to Kafka.
    """

    def setUp(self):
        """
        Set up the test environment by starting the FastAPI server in a separate thread.
        """
        self.server_thread = threading.Thread(target=self.run_server)
        self.server_thread.daemon = True
        self.server_thread.start()
        time.sleep(2)  # Give the server time to start

    def tearDown(self):
        """
        Clean up the test environment.
        """
        self.shutdown()

    def run_server(self):
        """
        Runs the FastAPI server.
        """
        config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
        self.server = uvicorn.Server(config)
        self.server.run()

    def shutdown(self):
        """
        Shuts down the FastAPI server.
        """
        self.server.should_exit = True
        self.server_thread.join()

    def test_order_submission_to_kafka(self):
        """
        Tests that an order submitted to the API is published to Kafka.
        """
        # Kafka consumer setup
        async def consume():
            kafka_client = KafkaClient(bootstrap_servers='localhost:9092')
            consumer = await kafka_client.consumer.start()
            try:
                # Wait for a message
                msg = await asyncio.wait_for(consumer.getone(), timeout=10)
                return msg.value
            finally:
                await consumer.stop()

        # API request
        order_data = {
            "symbol": {"symbol": "AAPL", "exchange": "NASDAQ", "asset_class": "STK"},
            "order_type": "MARKET",
            "side": "BUY",
            "quantity": 10.0,
            "time_in_force": "DAY"
        }
        headers = {"Authorization": "Bearer test-token"}
        response = requests.post("http://localhost:8000/api/v1/orders", json=order_data, headers=headers)
        self.assertEqual(response.status_code, 200)

        # Run the consumer and get the message
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        message = loop.run_until_complete(consume())
        loop.close()

        # Assertions
        self.assertIsNotNone(message)
        self.assertEqual(message['symbol']['symbol'], 'AAPL')
        self.assertEqual(message['order_type'], 'MARKET')
        self.assertEqual(message['side'], 'BUY')
        self.assertEqual(message['quantity'], 10.0)

if __name__ == '__main__':
    unittest.main()
