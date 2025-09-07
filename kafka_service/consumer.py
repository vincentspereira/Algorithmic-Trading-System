import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import time

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError, KafkaTimeoutError

from shared.config import settings
from shared.utils.logging_utils import get_logger

# Configure logging
logger = get_logger(__name__)

@dataclass
class ConsumerMetrics:
    """Metrics for Kafka consumer performance"""
    messages_received: int = 0
    total_bytes_received: int = 0
    avg_processing_latency_ms: float = 0.0
    last_receive_time: Optional[datetime] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class KafkaEventConsumer:
    """High-performance Kafka consumer for market data events"""
    
    def __init__(self, topics: List[str] = None, group_id: str = "nautilus_consumer_group"):
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.metrics = ConsumerMetrics()
        self.is_running = False
        self._processing_latency_samples = []
        self._max_samples = 1000
        self.topics = topics if topics is not None else []
        self.group_id = group_id
        
        # Kafka configuration
        self.bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
        
    async def start(self):
        """Start the Kafka consumer"""
        try:
            self.consumer = AIOKafkaConsumer(
                *self.topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                value_deserializer=self._deserialize_message,
                enable_auto_commit=True,
                auto_offset_reset="earliest"
            )
            
            await self.consumer.start()
            self.is_running = True
            
            logger.info(f"Kafka consumer started successfully for topics {self.topics}, connected to {self.bootstrap_servers}")
            
        except Exception as e:
            logger.error(f"Failed to start Kafka consumer: {e}")
            raise
    
    async def stop(self):
        """Stop the Kafka consumer"""
        try:
            if self.consumer:
                await self.consumer.stop()
            
            self.is_running = False
            logger.info("Kafka consumer stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping Kafka consumer: {e}")
    
    async def close(self):
        """Close the Kafka consumer (alias for stop)"""
        await self.stop()
    
    def _deserialize_message(self, message: bytes) -> Dict[str, Any]:
        """Deserialize message from JSON bytes"""
        try:
            return json.loads(message.decode('utf-8'))
        except Exception as e:
            logger.error(f"Failed to deserialize message: {e}")
            raise
    
    async def consume_messages(self):
        """Consume messages from Kafka topic"""
        if not self.is_running or not self.consumer:
            logger.error("Kafka consumer is not running")
            return
        
        try:
            async for msg in self.consumer:
                start_time = time.time()
                
                # Process message
                message_data = self._deserialize_message(msg.value)
                logger.debug(f"Consumed message from topic {msg.topic}: {message_data}")
                
                processing_latency_ms = (time.time() - start_time) * 1000
                self._update_metrics(message_data, processing_latency_ms, success=True)
                
                yield message_data
                
        except KafkaError as e:
            logger.error(f"Kafka error consuming messages: {e}")
            self._update_metrics({}, 0, success=False, error=str(e))
        except Exception as e:
            logger.error(f"Unexpected error consuming messages: {e}")
            self._update_metrics({}, 0, success=False, error=str(e))
    
    def _update_metrics(self, message: Dict[str, Any], latency_ms: float, success: bool, error: str = None):
        """Update consumer metrics"""
        if success:
            self.metrics.messages_received += 1
            self.metrics.total_bytes_received += len(json.dumps(message, default=str).encode('utf-8'))
            
            self._processing_latency_samples.append(latency_ms)
            if len(self.metrics.errors) > 100:
                self.metrics.errors.pop(0)
            
            if self._processing_latency_samples:
                self.metrics.avg_processing_latency_ms = sum(self._processing_latency_samples) / len(self._processing_latency_samples)
        else:
            if error:
                self.metrics.errors.append(f"{datetime.now().isoformat()}: {error}")
                if len(self.metrics.errors) > 100:
                    self.metrics.errors.pop(0)
        
        self.metrics.last_receive_time = datetime.now()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get consumer performance metrics"""
        return {
            "messages_received": self.metrics.messages_received,
            "total_bytes_received": self.metrics.total_bytes_received,
            "avg_processing_latency_ms": round(self.metrics.avg_processing_latency_ms, 2),
            "last_receive_time": self.metrics.last_receive_time.isoformat() if self.metrics.last_receive_time else None,
            "is_running": self.is_running,
            "recent_errors": self.metrics.errors[-10:] if self.metrics.errors else []
        }