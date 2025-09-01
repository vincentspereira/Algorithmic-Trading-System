
from uuid import UUID

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from kafka import KafkaProducer
import redis

from app.models import BacktestRequest, BacktestResult, BacktestStatus
from app.websockets import ConnectionManager
from shared.config import settings

import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
manager = ConnectionManager()

# Configure Kafka producer
try:
    kafka_producer = KafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
except Exception as e:
    logger.error(f"Failed to initialize Kafka producer: {e}")
    kafka_producer = None

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

@router.post("/backtest", response_model=BacktestResult)
async def create_backtest(request: BacktestRequest):
    """Create a new backtest"""
    logger.info(f"Received backtest request: {request.request_id}")
    if not kafka_producer or not redis_client:
        raise HTTPException(
            status_code=503,
            detail="Service unavailable. Please check the logs for more details."
        )
    try:
        # Store request in Redis
        redis_client.set(
            f"backtest:{request.request_id}",
            request.json(),
            ex=3600  # 1 hour expiry
        )

        # Publish to Kafka
        kafka_producer.send(
            'backtest_requests',
            value={
                'request_id': str(request.request_id),
                'strategy': request.strategy.dict()
            }
        )

        # Create initial result
        result = BacktestResult(
            request_id=request.request_id,
            status=BacktestStatus.PENDING
        )
        logger.info(f"Backtest request {request.request_id} created successfully.")
        return result

    except Exception as e:
        logger.error(f"Failed to create backtest {request.request_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create backtest: {str(e)}"
        )

@router.get("/backtest/{backtest_id}", response_model=BacktestResult)
async def get_backtest_status(backtest_id: UUID):
    """Get backtest status"""
    logger.info(f"Fetching status for backtest: {backtest_id}")
    if not redis_client:
        raise HTTPException(
            status_code=503,
            detail="Service unavailable. Please check the logs for more details."
        )
    try:
        result = redis_client.get(f"backtest_result:{backtest_id}")
        if not result:
            logger.warning(f"Backtest {backtest_id} not found.")
            raise HTTPException(
                status_code=404,
                detail="Backtest not found"
            )
        logger.info(f"Successfully fetched status for backtest: {backtest_id}")
        return BacktestResult.parse_raw(result)

    except Exception as e:
        logger.error(f"Failed to get status for backtest {backtest_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get backtest status: {str(e)}"
        )

@router.websocket("/ws/backtest/{backtest_id}")
async def websocket_endpoint(websocket: WebSocket, backtest_id: UUID):
    """WebSocket endpoint for real-time updates"""
    logger.info(f"WebSocket connection established for backtest: {backtest_id}")
    await manager.connect(websocket, backtest_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info(f"WebSocket connection disconnected for backtest: {backtest_id}")
        manager.disconnect(websocket, backtest_id)
