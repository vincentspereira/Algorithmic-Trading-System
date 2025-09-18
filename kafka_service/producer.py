"""Kafka Event Producer for Market Data Streaming

Provides high-performance Kafka producer for streaming normalized market data
with proper error handling, batching, and performance monitoring.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import time

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError, KafkaTimeoutError

from shared.config import settings
from shared.utils.logging_utils import get_logger

# Configure logging
logger = get_logger(__name__)

@dataclass
class ProducerMetrics:
    """Metrics for Kafka producer performance"""
    messages_sent: int = 0
    messages_failed: int = 0
    total_bytes_sent: int = 0
    avg_latency_ms: float = 0.0
    last_send_time: Optional[datetime] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class KafkaEventProducer:
    """High-performance Kafka producer for market data events"""
    
    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None
        self.metrics = ProducerMetrics()
        self.is_running = False
        self._latency_samples = []
        self._max_samples = 1000
        
        # Kafka configuration
        self.bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
        self.batch_size = 16384  # 16KB batches for better throughput
        self.linger_ms = 5  # Wait up to 5ms to batch messages
        self.compression_type = 'snappy'  # Fast compression
        self.acks = 'all'  # Wait for all replicas acknowledgment for idempotence
        self.retries = 3
        self.max_in_flight_requests = 5
        
    async def start(self):
        """Start the Kafka producer"""
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=self._serialize_message,
                key_serializer=self._serialize_key,
                max_batch_size=self.batch_size,
                linger_ms=self.linger_ms,
                compression_type=None,
                acks=self.acks,
                
                
                enable_idempotence=True,  # Prevent duplicate messages
                request_timeout_ms=30000,
                retry_backoff_ms=100
            )
            
            await self.producer.start()
            self.is_running = True
            
            logger.info(f"Kafka producer started successfully, connected to {self.bootstrap_servers}")
            
        except Exception as e:
            logger.error(f"Failed to start Kafka producer: {e}")
            raise
    
    async def stop(self):
        """Stop the Kafka producer"""
        try:
            if self.producer:
                await self.producer.stop()
            
            self.is_running = False
            logger.info("Kafka producer stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping Kafka producer: {e}")
    
    async def close(self):
        """Close the Kafka producer (alias for stop)"""
        await self.stop()
    
    def _serialize_message(self, message: Dict[str, Any]) -> bytes:
        """Serialize message to JSON bytes"""
        try:
            return json.dumps(message, default=str).encode('utf-8')
        except Exception as e:
            logger.error(f"Failed to serialize message: {e}")
            raise
    
    def _serialize_key(self, key: str) -> bytes:
        """Serialize message key to bytes"""
        if key is None:
            return None
        return key.encode('utf-8')
    
    async def send_message(
        self, 
        topic: str, 
        message: Dict[str, Any], 
        key: Optional[str] = None,
        partition: Optional[int] = None
    ) -> bool:
        """Send a single message to Kafka topic"""
        if not self.is_running or not self.producer:
            logger.error("Kafka producer is not running")
            return False
        
        try:
            start_time = time.time()
            
            # Use symbol as key for partitioning if no key provided
            if key is None and 'symbol' in message:
                key = message['symbol']
            
            # Send message
            future = await self.producer.send(
                topic=topic,
                value=message,
                key=key,
                partition=partition
            )
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            self._update_metrics(message, latency_ms, success=True)
            
            logger.debug(f"Message sent to {topic} in {latency_ms:.2f}ms")
            return True
            
        except KafkaTimeoutError as e:
            logger.error(f"Kafka timeout sending to {topic}: {e}")
            self._update_metrics(message, 0, success=False, error=str(e))
            return False
            
        except KafkaError as e:
            logger.error(f"Kafka error sending to {topic}: {e}")
            self._update_metrics(message, 0, success=False, error=str(e))
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error sending to {topic}: {e}")
            self._update_metrics(message, 0, success=False, error=str(e))
            return False
    
    async def send_batch(
        self, 
        topic: str, 
        messages: List[Dict[str, Any]], 
        keys: Optional[List[str]] = None
    ) -> int:
        """Send a batch of messages to Kafka topic"""
        if not self.is_running or not self.producer:
            logger.error("Kafka producer is not running")
            return 0
        
        successful_sends = 0
        
        try:
            # Prepare batch
            batch_tasks = []
            
            for i, message in enumerate(messages):
                key = keys[i] if keys and i < len(keys) else message.get('symbol')
                
                task = self.send_message(topic, message, key)
                batch_tasks.append(task)
            
            # Execute batch
            results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Count successful sends
            for result in results:
                if isinstance(result, bool) and result:
                    successful_sends += 1
                elif isinstance(result, Exception):
                    logger.error(f"Batch send error: {result}")
            
            logger.info(f"Batch send completed: {successful_sends}/{len(messages)} successful")
            
        except Exception as e:
            logger.error(f"Batch send failed: {e}")
        
        return successful_sends
    
    def _update_metrics(self, message: Dict[str, Any], latency_ms: float, success: bool, error: str = None):
        """Update producer metrics"""
        if success:
            self.metrics.messages_sent += 1
            self.metrics.total_bytes_sent += len(json.dumps(message, default=str).encode('utf-8'))
            
            # Update latency tracking
            self._latency_samples.append(latency_ms)
            if len(self._latency_samples) > self._max_samples:
                self._latency_samples.pop(0)
            
            # Calculate average latency
            if self._latency_samples:
                self.metrics.avg_latency_ms = sum(self._latency_samples) / len(self._latency_samples)
        else:
            self.metrics.messages_failed += 1
            if error:
                self.metrics.errors.append(f"{datetime.now().isoformat()}: {error}")
                # Keep only last 100 errors
                if len(self.metrics.errors) > 100:
                    self.metrics.errors.pop(0)
        
        self.metrics.last_send_time = datetime.now()
    
    async def flush(self, timeout_ms: int = 10000):
        """Flush any pending messages"""
        if self.producer:
            try:
                await asyncio.wait_for(
                    self.producer.flush(),
                    timeout=timeout_ms / 1000
                )
                logger.debug("Producer flushed successfully")
            except asyncio.TimeoutError:
                logger.warning(f"Producer flush timeout after {timeout_ms}ms")
            except Exception as e:
                logger.error(f"Producer flush error: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get producer performance metrics"""
        return {
            "messages_sent": self.metrics.messages_sent,
            "messages_failed": self.metrics.messages_failed,
            "total_bytes_sent": self.metrics.total_bytes_sent,
            "avg_latency_ms": round(self.metrics.avg_latency_ms, 2),
            "success_rate": (
                self.metrics.messages_sent / 
                (self.metrics.messages_sent + self.metrics.messages_failed)
                if (self.metrics.messages_sent + self.metrics.messages_failed) > 0 else 0
            ),
            "last_send_time": self.metrics.last_send_time.isoformat() if self.metrics.last_send_time else None,
            "is_running": self.is_running,
            "recent_errors": self.metrics.errors[-10:] if self.metrics.errors else [],
            "throughput_msgs_per_sec": self._calculate_throughput()
        }
    
    def _calculate_throughput(self) -> float:
        """Calculate approximate throughput in messages per second"""
        if not self.metrics.last_send_time or self.metrics.messages_sent == 0:
            return 0.0
        
        # Simple approximation based on recent activity
        # In production, you'd want more sophisticated throughput calculation
        time_window_seconds = 60  # Last minute
        return min(self.metrics.messages_sent / time_window_seconds, self.metrics.messages_sent)
    
    async def create_topics_if_not_exist(self, topics: List[str]):
        """Create Kafka topics if they don't exist (requires admin privileges)"""
        try:
            from aiokafka.admin import AIOKafkaAdminClient, NewTopic
            
            admin_client = AIOKafkaAdminClient(
                bootstrap_servers=self.bootstrap_servers
            )
            
            await admin_client.start()
            
            try:
                # Get existing topics
                metadata = await admin_client.describe_cluster()
                existing_topics = set(metadata.topics)
                
                # Create missing topics
                new_topics = []
                for topic in topics:
                    if topic not in existing_topics:
                        new_topics.append(NewTopic(
                            name=topic,
                            num_partitions=3,  # Default partitions
                            replication_factor=1  # Single node setup
                        ))
                
                if new_topics:
                    await admin_client.create_topics(new_topics)
                    logger.info(f"Created {len(new_topics)} new Kafka topics")
                else:
                    logger.info("All required topics already exist")
                    
            finally:
                await admin_client.close()
                
        except Exception as e:
            logger.warning(f"Could not create topics (may require admin privileges): {e}")

# Hierarchical topic structure for market data
MARKET_DATA_TOPICS = {
    "real_time": {
        "stock": "market_data.stock.real_time",
        "etf": "market_data.etf.real_time",
        "future": "market_data.future.real_time",
        "option": "market_data.option.real_time",
        "forex": "market_data.forex.real_time",
        "commodity": "market_data.commodity.real_time",
        "crypto": "market_data.crypto.real_time"
    },
    "historical": {
        "stock": "market_data.stock.historical",
        "etf": "market_data.etf.historical",
        "future": "market_data.future.historical",
        "option": "market_data.option.historical",
        "forex": "market_data.forex.historical",
        "commodity": "market_data.commodity.historical",
        "crypto": "market_data.crypto.historical"
    },
    "events": {
        "trades": "market_data.events.trades",
        "orders": "market_data.events.orders",
        "positions": "market_data.events.positions",
        "errors": "market_data.events.errors",
        "system": "market_data.events.system"
    }
}

def get_all_topics() -> List[str]:
    """Get all defined Kafka topics"""
    topics = []
    for category in MARKET_DATA_TOPICS.values():
        if isinstance(category, dict):
            topics.extend(category.values())
        else:
            topics.append(category)
    return topics