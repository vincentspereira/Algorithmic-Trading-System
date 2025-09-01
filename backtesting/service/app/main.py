
from fastapi import FastAPI
from celery import Celery

from app.api.endpoints import router
from shared.config import settings

import logging
import json
import redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Backtest Service")

app.include_router(router, prefix="/api")

# Configure Redis
try:
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=True
    )
    redis_client.ping()
except Exception as e:
    logger.error(f"Failed to initialize Redis client: {e}")
    redis_client = None

# Configure Celery
try:
    celery_app = Celery(
        'backtest_tasks',
        broker=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
        backend=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"
    )
except Exception as e:
    logger.error(f"Failed to initialize Celery app: {e}")
    celery_app = None

# Celery task for handling backtest updates
@celery_app.task
def process_backtest_result(backtest_id: str, result: dict):
    """Process and store backtest result"""
    logger.info(f"Processing result for backtest: {backtest_id}")
    if not redis_client:
        logger.error("Redis client not available. Cannot process backtest result.")
        return
    try:
        # Store in Redis for quick access
        redis_client.set(
            f"backtest_result:{backtest_id}",
            json.dumps(result),
            ex=3600  # 1 hour expiry
        )
        logger.info(f"Successfully processed result for backtest: {backtest_id}")

        # TODO: Store in ClickHouse for permanent storage

    except Exception as e:
        logger.error(f"Error processing backtest result for {backtest_id}: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.BACKTEST_SERVICE_HOST, port=settings.BACKTEST_SERVICE_PORT)
