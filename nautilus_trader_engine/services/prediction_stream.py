import asyncio
import json
import random
from datetime import datetime, timezone

class PredictionStream:
    """
    Manages the Kafka stream for market data consumption and prediction publishing.
    This class uses mock implementations for Kafka interactions for development purposes.
    """

    def __init__(self, kafka_consumer, kafka_producer, prediction_engine):
        self.consumer = kafka_consumer
        self.producer = kafka_producer
        self.prediction_engine = prediction_engine
        self.running = False

    async def _process_message(self, message: dict):
        """
        Processes a single message from the market data stream.
        A real implementation would perform feature engineering and then predict.
        """
        try:
            # In a real system, you would parse the message according to your data format
            symbol = message.get("symbol")
            price = message.get("price")
            timestamp = message.get("timestamp")

            if not all([symbol, price, timestamp]):
                print(f"Warning: Invalid message format: {message}")
                return

            print(f"Received tick for {symbol}: Price={price} at {timestamp}")

            # Add symbol to engine if not already tracked
            if symbol not in self.prediction_engine.symbols:
                self.prediction_engine.subscribe_to_symbol(symbol)
                print(f"Subscribed to new symbol: {symbol}")

            # In a full implementation, you'd buffer data, generate features, and then predict.
            # For this mock, we'll just trigger a prediction directly.
            prediction_result = await self.prediction_engine.get_prediction(symbol)
            
            # Publish the prediction to the predictions topic
            await self.producer.send("stock_predictions", prediction_result)
            print(f"Published prediction for {symbol}: {prediction_result}")

        except Exception as e:
            print(f"Error processing message: {e}")

    async def start_streaming(self):
        """
        Starts consuming from the market data topic and processing messages.
        """
        self.running = True
        print("Starting prediction stream...")
        # This simulates consuming from a Kafka topic
        while self.running:
            try:
                # In a real consumer, you'd be awaiting messages here.
                # e.g., message = await self.consumer.getone()
                # We'll simulate receiving a message.
                mock_message = {
                    "symbol": random.choice(["AAPL", "GOOGL", "MSFT"]),
                    "price": random.uniform(100, 1000),
                    "volume": random.randint(1000, 100000),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await self._process_message(mock_message)
                
                # Simulate a short delay between messages
                await asyncio.sleep(random.uniform(0.5, 2.0))

            except asyncio.CancelledError:
                self.running = False
                print("Prediction stream stopped.")
                break
            except Exception as e:
                print(f"An error occurred in the streaming loop: {e}")
                # In a real system, you'd have reconnection logic here
                await asyncio.sleep(5)

    def stop_streaming(self):
        """Stops the streaming loop."""
        self.running = False
        print("Stopping prediction stream...")

# Example usage
if __name__ == "__main__":
    # Mock Kafka and Prediction Engine classes for testing
    class MockKafka:
        async def send(self, topic, message):
            print(f"Mock Kafka Send -> Topic: {topic}, Message: {json.dumps(message, indent=2)}")

        async def getone(self):
            # This would be a real implementation detail
            pass

    class MockPredictionEngine:
        def __init__(self):
            self.symbols = set()

        def subscribe_to_symbol(self, symbol):
            self.symbols.add(symbol)

        async def get_prediction(self, symbol):
            return {
                "symbol": symbol,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "predictions": {
                    "1min": {"prediction": random.uniform(100, 102), "confidence": random.random()},
                }
            }

    async def main():
        # Setup mock components
        mock_consumer = MockKafka()
        mock_producer = MockKafka()
        mock_engine = MockPredictionEngine()
        
        # Initialize the stream
        stream = PredictionStream(mock_consumer, mock_producer, mock_engine)
        
        # Start the stream in a background task
        stream_task = asyncio.create_task(stream.start_streaming())
        
        # Let it run for a bit
        await asyncio.sleep(10)
        
        # Stop the stream
        stream.stop_streaming()
        await stream_task

    asyncio.run(main())