"""
Kafka to AI Models Bridge for Real-Time Trading Signal Generation

This service consumes market data from Kafka, processes it, and generates
trading predictions using the existing AI forecasting models. It also serves
these predictions via a WebSocket connection for real-time frontend updates.

Author: Kilo Code
Version: 1.0.0
"""

import asyncio
import json
import logging
from typing import Dict, Any, List
import pandas as pd
import websockets

from nautilus_trader_engine.kafka_integration import KafkaConsumerService, KafkaConfig, MarketDataTopic
from nautilus_trader_engine.services.prediction_service import PredictionService
from ai_assistant.forecasting_models import ModelType, PredictionResult

# Configure logging
logger = logging.getLogger(__name__)

class KafkaAIBridge:
    """
    Connects Kafka data streams to AI models and serves predictions in real-time.
    """

    def __init__(self, kafka_config: KafkaConfig, model_type: ModelType = ModelType.ENSEMBLE):
        self.kafka_config = kafka_config
        self.consumer = KafkaConsumerService(kafka_config)
        self.prediction_service = PredictionService(model_type=model_type)
        self.websocket_server = None
        self.connected_clients = set()

    async def initialize(self):
        """Initializes the Kafka consumer and WebSocket server."""
        try:
            # Initialize Kafka consumer
            topics = [
                MarketDataTopic.STOCK_PRICES,
                MarketDataTopic.FOREX_RATES,
                MarketDataTopic.CRYPTO_PRICES,
            ]
            if not await self.consumer.initialize(topics):
                raise ConnectionError("Failed to initialize Kafka consumer.")

            # Register message handlers
            for topic in topics:
                self.consumer.register_handler(topic, self._handle_market_data)

            logger.info("KafkaAIBridge initialized successfully.")
            return True
        except Exception as e:
            logger.error(f"Error during KafkaAIBridge initialization: {e}", exc_info=True)
            return False

    async def start(self, websocket_host: str = "0.0.0.0", websocket_port: int = 8765):
        """Starts the Kafka consumer and WebSocket server."""
        try:
            # Start WebSocket server
            self.websocket_server = await websockets.serve(
                self._websocket_handler, websocket_host, websocket_port
            )
            logger.info(f"WebSocket server started on ws://{websocket_host}:{websocket_port}")

            # Start Kafka consumer
            asyncio.create_task(self.consumer.start_consuming())
            logger.info("Kafka consumer started.")

        except Exception as e:
            logger.error(f"Error starting KafkaAIBridge: {e}", exc_info=True)
            raise

    async def stop(self):
        """Stops the Kafka consumer and WebSocket server."""
        if self.consumer:
            await self.consumer.stop_consuming()
            await self.consumer.close()
            logger.info("Kafka consumer stopped.")

        if self.websocket_server:
            self.websocket_server.close()
            await self.websocket_server.wait_closed()
            logger.info("WebSocket server stopped.")

    async def _handle_market_data(self, message_data: Dict[str, Any]):
        """
        Handles incoming market data from Kafka, generates predictions,
        and broadcasts them to connected WebSocket clients.
        """
        try:
            prediction = self.prediction_service.predict(message_data)
            await self._broadcast_prediction(prediction)
        except Exception as e:
            logger.error(f"Error processing market data: {e}", exc_info=True)

    async def _websocket_handler(self, websocket, path):
        """Manages WebSocket connections."""
        self.connected_clients.add(websocket)
        logger.info(f"New client connected from {websocket.remote_address}")
        try:
            async for message in websocket:
                # The bridge does not process incoming messages, but this keeps the connection alive
                logger.debug(f"Received message from client: {message}")
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"Client connection closed: {e}")
        finally:
            self.connected_clients.remove(websocket)
            logger.info(f"Client disconnected from {websocket.remote_address}")

    async def _broadcast_prediction(self, prediction: PredictionResult):
        """Broadcasts a prediction to all connected WebSocket clients."""
        if not self.connected_clients:
            return

        prediction_json = json.dumps(prediction.to_dict())
        tasks = [client.send(prediction_json) for client in self.connected_clients]
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.debug(f"Broadcasted prediction for {prediction.ticker}")

async def main():
    """Main function to run the KafkaAIBridge."""
    logging.basicConfig(level=logging.INFO)
    kafka_config = KafkaConfig()
    bridge = KafkaAIBridge(kafka_config)

    if not await bridge.initialize():
        logger.error("Failed to initialize KafkaAIBridge. Exiting.")
        return

    try:
        await bridge.start()
        # Keep the service running
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutting down KafkaAIBridge...")
    finally:
        await bridge.stop()
        logger.info("KafkaAIBridge shut down gracefully.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted. Exiting.")