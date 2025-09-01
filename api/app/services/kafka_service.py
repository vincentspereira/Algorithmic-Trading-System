
import asyncio
import json

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import structlog

logger = structlog.get_logger()

class KafkaService:
    def __init__(self, bootstrap_servers: str):
        self.bootstrap_servers = bootstrap_servers
        self.producer = None
        self.consumer = None

    async def start(self):
        self.producer = AIOKafkaProducer(bootstrap_servers=self.bootstrap_servers,
                                         value_serializer=lambda v: json.dumps(v).encode('utf-8'))
        await self.producer.start()

    async def stop(self):
        if self.producer:
            await self.producer.stop()

    async def send_message(self, topic: str, message: dict):
        if self.producer:
            await self.producer.send_and_wait(topic, message)

    async def consume_messages(self, topic: str, group_id: str, callback):
        self.consumer = AIOKafkaConsumer(topic, bootstrap_servers=self.bootstrap_servers, group_id=group_id,
                                       value_deserializer=lambda m: json.loads(m.decode('utf-8')))
        await self.consumer.start()
        try:
            async for msg in self.consumer:
                await callback(msg.value)
        finally:
            await self.consumer.stop()
