import asyncio
import structlog
from shared.kafka_client import KafkaClient

logger = structlog.get_logger()

class KafkaService:
    def __init__(self, bootstrap_servers: str):
        self.kafka_client = KafkaClient(bootstrap_servers)

    async def start(self):
        await self.kafka_client.connect()
        self.kafka_client.create_topic('trading_events')

    async def stop(self):
        await self.kafka_client.disconnect()

    async def process_trading_event(self, trading_event: dict):
        logger.info("Processing trading event", trading_event=trading_event)
        # In a real application, this is where you would put your business logic
        # for processing the trading event. For example, you might:
        # 1. Validate the event
        # 2. Enrich the event with additional data
        # 3. Trigger a trading action
        # 4. Store the event in a database
        await self.kafka_client.send_message('processed_trading_events', {'status': 'processed', 'original_event': trading_event})

    async def consume_events(self):
        await self.kafka_client.consume_messages(
            topic='trading_events',
            group_id='trading_event_processor',
            callback=self.process_trading_event
        )

async def main():
    bootstrap_servers = 'localhost:9092'
    kafka_service = KafkaService(bootstrap_servers)
    await kafka_service.start()

    # Start consuming messages in the background
    consumer_task = asyncio.create_task(kafka_service.consume_events())

    # Produce a sample message
    await kafka_service.kafka_client.send_message('trading_events', {'type': 'BUY', 'symbol': 'AAPL', 'quantity': 100})

    # Wait for a while to allow the consumer to process the message
    await asyncio.sleep(5)

    # Stop the service
    await kafka_service.stop()
    consumer_task.cancel()

if __name__ == "__main__":
    asyncio.run(main())