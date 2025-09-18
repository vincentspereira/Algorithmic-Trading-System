"""
Kafka Integration Test Script

This script demonstrates and tests the Kafka integration functionality
for the algorithmic trading system.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import asyncio
import json
import time
from typing import Dict, Any
import logging

from nautilus_trader_engine.core.kafka_integration import (
    MarketDataStreamer,
    KafkaConfig,
    MarketDataTopic,
    KafkaProducerService,
    KafkaConsumerService,
)
from nautilus_trader_engine.core.data_feeds import DataFeedManager, AssetClass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


import unittest
from unittest.mock import patch, AsyncMock

# Mock KafkaProducer and KafkaConsumer for testing purposes
mock_kafka_producer = AsyncMock()
mock_kafka_consumer = AsyncMock()


class TestKafkaIntegration(unittest.TestCase):
    """Main test class for Kafka integration components."""

    def setUp(self):
        """Set up test environment."""
        self.loop = asyncio.get_event_loop()
        self.kafka_config = KafkaConfig(
            bootstrap_servers="localhost:9092",
            client_id="test_client",
            group_id="test_group",
        )

    @patch('nautilus_trader_engine.core.kafka_integration.KafkaProducerService', new=mock_kafka_producer)
    @patch('nautilus_trader_engine.core.kafka_integration.KafkaConsumerService', new=mock_kafka_consumer)
    def test_kafka_producer_init(self):
        """Test Kafka producer initialization."""
        producer = KafkaProducerService(self.kafka_config)
        self.assertIsNotNone(producer)

    @patch('nautilus_trader_engine.core.kafka_integration.KafkaProducerService', new=mock_kafka_producer)
    @patch('nautilus_trader_engine.core.kafka_integration.KafkaConsumerService', new=mock_kafka_consumer)
    def test_kafka_consumer_init(self):
        """Test Kafka consumer initialization."""
        consumer = KafkaConsumerService(self.kafka_config)
        self.assertIsNotNone(consumer)

    @patch('nautilus_trader_engine.core.kafka_integration.KafkaProducerService', new=mock_kafka_producer)
    @patch('nautilus_trader_engine.core.kafka_integration.KafkaConsumerService', new=mock_kafka_consumer)
    def test_market_data_streamer_init(self):
        """Test MarketDataStreamer initialization."""
        streamer = MarketDataStreamer(self.kafka_config)
        self.assertIsNotNone(streamer)
        self.assertIsNotNone(streamer.producer)
        self.assertIsNotNone(streamer.consumer)

if __name__ == "__main__":
    unittest.main()