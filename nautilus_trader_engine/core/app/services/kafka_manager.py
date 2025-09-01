
import asyncio
import logging
from typing import Dict, Any, List

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer

from shared.config import settings

logger = logging.getLogger(__name__)

class KafkaManager:
    def __init__(self):
        self.producer = None
        self.consumer = None
        self.streaming_symbols: Dict[str, Any] = {}
        self.is_streaming = False

    async def initialize(self):
        try:
            self.producer = AIOKafkaProducer(bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                                             value_serializer=lambda v: v.encode('utf-8'))
            await self.producer.start()
            logger.info("Kafka producer initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            return False

    async def close(self):
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer closed")
        if self.consumer:
            await self.consumer.stop()
            logger.info("Kafka consumer closed")

    async def start_streaming_service(self):
        if self.is_streaming:
            return {"success": False, "error": "Streaming service already running"}

        self.is_streaming = True
        logger.info("Kafka streaming service started")
        return {"success": True, "message": "Streaming service started"}

    async def stop_streaming_service(self):
        if not self.is_streaming:
            return {"success": False, "error": "Streaming service not running"}

        self.is_streaming = False
        logger.info("Kafka streaming service stopped")
        return {"success": True, "message": "Streaming service stopped"}

    async def add_streaming_symbol(self, symbol: str, asset_class: str, interval: str):
        if symbol in self.streaming_symbols:
            return {"success": False, "error": f"Symbol {symbol} already streaming"}

        self.streaming_symbols[symbol] = {"asset_class": asset_class, "interval": interval}
        logger.info(f"Added {symbol} to streaming symbols")
        return {"success": True, "message": f"Started streaming for {symbol}"}

    async def remove_streaming_symbol(self, symbol: str):
        if symbol not in self.streaming_symbols:
            return {"success": False, "error": f"Symbol {symbol} not streaming"}

        del self.streaming_symbols[symbol]
        logger.info(f"Removed {symbol} from streaming symbols")
        return {"success": True, "message": f"Stopped streaming for {symbol}"}

    async def get_streaming_symbols(self) -> Dict[str, Any]:
        return {"symbols": list(self.streaming_symbols.keys()), "details": self.streaming_symbols}

    async def get_streaming_status(self) -> Dict[str, Any]:
        return {"initialized": self.producer is not None, "is_streaming": self.is_streaming, "symbols_count": len(self.streaming_symbols)}

    async def get_kafka_topics(self) -> List[str]:
        if not self.producer:
            return []
        try:
            # AIOKafkaProducer does not directly expose list_topics(),
            # so we need to create a temporary consumer to get topic metadata.
            temp_consumer = AIOKafkaConsumer(bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS)
            await temp_consumer.start()
            topics = await temp_consumer.list_topics()
            await temp_consumer.stop()
            return list(topics.keys())
        except Exception as e:
            logger.error(f"Failed to get Kafka topics: {e}")
            return []

    async def test_kafka_connection(self) -> Dict[str, Any]:
        try:
            test_topic = "test_connection_topic"
            test_message = {"test": "message", "timestamp": str(datetime.now())}
            await self.producer.send_and_wait(test_topic, json.dumps(test_message).encode('utf-8'))
            logger.info("Kafka test message sent successfully")
            return {"success": True, "message": "Kafka connection test successful"}
        except Exception as e:
            logger.error(f"Kafka connection test failed: {e}")
            return {"success": False, "error": str(e)}

    async def publish_trading_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        try:
            topic = "trading_signals"
            await self.producer.send_and_wait(topic, json.dumps(signal).encode('utf-8'))
            logger.info(f"Published trading signal to {topic}")
            return {"success": True, "message": "Trading signal published"}
        except Exception as e:
            logger.error(f"Failed to publish trading signal: {e}")
            return {"success": False, "error": str(e)}
