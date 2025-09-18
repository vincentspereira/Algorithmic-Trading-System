
from datetime import datetime, timezone

from fastapi import APIRouter
from prometheus_client import generate_latest

from api.app.websockets import ConnectionManager
from nautilus_trader_engine.core.data_feed_manager import DataFeedManager

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    # This is a simplified health check. In a real-world scenario, you would
    # want to check the status of all dependencies (e.g., database, Kafka).
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc),
        "version": "1.0.0",
    }

@router.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    return generate_latest()
