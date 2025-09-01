import asyncio
import structlog
from datetime import datetime
from shared.kafka_client import KafkaClient
from services.kafka_service import KafkaService
from nautilus_trader_engine.core.risk_management import RiskManager
from nautilus_trader_engine.core.order_management import OrderManager

logger = structlog.get_logger()

class OrderProcessor:
    def __init__(self, bootstrap_servers: str):
        self.kafka_service = KafkaService(bootstrap_servers)
        self.risk_manager = RiskManager()
        self.order_manager = OrderManager()

    async def start(self):
        await self.kafka_service.start()
        await self.risk_manager.initialize()
        await self.order_manager.initialize()
        # Ensure the order_requests topic exists
        self.kafka_service.kafka_client.create_topic('order_requests')
        self.kafka_service.kafka_client.create_topic('order_status_updates')
        logger.info("OrderProcessor started and initialized managers.")

    async def stop(self):
        await self.kafka_service.stop()
        await self.risk_manager.cleanup()
        await self.order_manager.cleanup()
        logger.info("OrderProcessor stopped.")

    async def process_order_request(self, message: dict):
        request_id = message.get("request_id", "N/A")
        user_id = message.get("user_id", "N/A")
        symbol = message.get("symbol", {}).get("symbol", "N/A")
        order_type = message.get("order_type", "N/A")

        logger.info("Processing order request", request_id=request_id, user_id=user_id, symbol=symbol, order_type=order_type)

        try:
            # 1. Risk Management Check
            risk_check_result = await self.risk_manager.validate_order(
                symbol=symbol,
                side=message.get("side"),
                quantity=message.get("quantity"),
                price=message.get("price"),
                user_id=user_id
            )

            if not risk_check_result["approved"]:
                status_message = f"Order rejected by risk management: {risk_check_result['reason']}"
                logger.warning(status_message, request_id=request_id, user_id=user_id, symbol=symbol)
                await self.publish_order_status(request_id, user_id, symbol, "REJECTED", status_message, message)
                return

            # 2. Submit Order
            submit_result = await self.order_manager.submit_order(message) # Assuming submit_order takes the full message

            if submit_result["success"]:
                status_message = f"Order submitted successfully: {submit_result.get('message', '')}"
                logger.info(status_message, request_id=request_id, user_id=user_id, symbol=symbol)
                await self.publish_order_status(request_id, user_id, symbol, "SUBMITTED", status_message, message, submit_result.get('order_id'))
            else:
                status_message = f"Order submission failed: {submit_result.get('message', 'Unknown error')}"
                logger.error(status_message, request_id=request_id, user_id=user_id, symbol=symbol)
                await self.publish_order_status(request_id, user_id, symbol, "FAILED", status_message, message)

        except Exception as e:
            error_message = f"Error processing order request: {str(e)}"
            logger.error(error_message, request_id=request_id, user_id=user_id, symbol=symbol, exc_info=True)
            await self.publish_order_status(request_id, user_id, symbol, "ERROR", error_message, message)

    async def publish_order_status(self, request_id: str, user_id: str, symbol: str, status: str, message: str, original_request: dict, order_id: str = None):
        status_event = {
            "request_id": request_id,
            "user_id": user_id,
            "symbol": symbol,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "original_request": original_request,
            "order_id": order_id
        }
        await self.kafka_service.kafka_client.send_message('order_status_updates', status_event)
        logger.info("Published order status update", request_id=request_id, status=status)

    async def consume_order_requests(self):
        await self.kafka_service.kafka_client.consume_messages(
            topic='order_requests',
            group_id='order_processor_group',
            callback=self.process_order_request
        )

async def main():
    bootstrap_servers = 'kafka:29092' # Assuming Kafka is accessible via 'kafka' hostname in Docker network
    processor = OrderProcessor(bootstrap_servers)
    await processor.start()
    
    logger.info("OrderProcessor is now consuming order requests...")
    try:
        await processor.consume_order_requests()
    except asyncio.CancelledError:
        logger.info("OrderProcessor consumption cancelled.")
    finally:
        await processor.stop()

if __name__ == "__main__":
    asyncio.run(main())
