
import asyncio
import json
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from confluent_kafka.admin import AdminClient, NewTopic
import structlog

logger = structlog.get_logger()

class KafkaClient:
    def __init__(self, bootstrap_servers: str):
        self.bootstrap_servers = bootstrap_servers
        self.producer = None
        self.consumer = None

    async def connect(self):
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            await self.producer.start()
            logger.info("Kafka producer started")
        except Exception as e:
            logger.error("Failed to start Kafka producer", error=str(e))
            raise

    async def disconnect(self):
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped")
        if self.consumer:
            await self.consumer.stop()
            logger.info("Kafka consumer stopped")

    async def send_message(self, topic: str, message: dict):
        if not self.producer:
            await self.connect()
        try:
            await self.producer.send_and_wait(topic, message)
            logger.info("Message sent to Kafka topic", topic=topic, message=message)
        except Exception as e:
            logger.error("Failed to send message to Kafka", topic=topic, error=str(e))

    async def consume_messages(self, topic: str, group_id: str, callback):
        self.consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=group_id,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest'
        )
        await self.consumer.start()
        logger.info("Kafka consumer started", topic=topic, group_id=group_id)
        try:
            async for msg in self.consumer:
                await callback(msg.value)
        finally:
            await self.consumer.stop()

    def create_topic(self, topic_name: str, num_partitions: int = 1, replication_factor: int = 1):
        admin_client = AdminClient({'bootstrap.servers': self.bootstrap_servers})
        new_topic = NewTopic(topic_name, num_partitions=num_partitions, replication_factor=replication_factor)
        fs = admin_client.create_topics([new_topic])
        for topic, f in fs.items():
            try:
                f.result()
                logger.info(f"Topic {topic} created")
            except Exception as e:
                if 'TOPIC_ALREADY_EXISTS' in str(e):
                    logger.info(f"Topic {topic} already exists")
                else:
                    logger.error(f"Failed to create topic {topic}: {e}")

