"""Kafka Event Producer

Basic Kafka producer for order events.
"""

import json
import logging
from typing import Dict, Any
from .config import KafkaConfig

logger = logging.getLogger(__name__)


class OrderEventProducer:
    """Basic Kafka producer for order events"""
    
    def __init__(self, kafka_config: KafkaConfig):
        self.kafka_config = kafka_config
        self.producer = None  # In production, this would be a real Kafka producer
        logger.info(f"OrderEventProducer initialized with config: {kafka_config}")
    
    async def start(self):
        """Start the producer"""
        logger.info("OrderEventProducer started")
    
    async def stop(self):
        """Stop the producer"""
        logger.info("OrderEventProducer stopped")
    
    async def send_order_created(self, order_data: Dict[str, Any]):
        """Send order created event"""
        topic = f"{self.kafka_config.topic_prefix}.order.created"
        message = {
            "event_type": "order_created",
            "timestamp": order_data.get("created_at"),
            "data": order_data
        }
        logger.info(f"Sending order created event to {topic}: {json.dumps(message, default=str)}")
    
    async def send_order_updated(self, order_data: Dict[str, Any]):
        """Send order updated event"""
        topic = f"{self.kafka_config.topic_prefix}.order.updated"
        message = {
            "event_type": "order_updated",
            "timestamp": order_data.get("updated_at"),
            "data": order_data
        }
        logger.info(f"Sending order updated event to {topic}: {json.dumps(message, default=str)}")
    
    async def send_order_cancelled(self, order_data: Dict[str, Any]):
        """Send order cancelled event"""
        topic = f"{self.kafka_config.topic_prefix}.order.cancelled"
        message = {
            "event_type": "order_cancelled",
            "timestamp": order_data.get("updated_at"),
            "data": order_data
        }
        logger.info(f"Sending order cancelled event to {topic}: {json.dumps(message, default=str)}")