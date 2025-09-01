
import logging
import asyncio
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
import uvicorn

from app.api.endpoints import router
from app.core.config import ServiceConfiguration
from app.metrics.prometheus_metrics import metrics_manager
from app.status.service_status import ServiceStatus
from app.services.kafka_manager import KafkaManager

# Configure logging (assuming setup_logging is handled elsewhere or will be added)
logger = logging.getLogger(__name__)

# Initialize configuration and status
config = ServiceConfiguration()
service_status = ServiceStatus()
kafka_manager = KafkaManager()

# Initialize FastAPI application
app = FastAPI(
    title=config.title,
    description=config.description,
    version=config.version,
    docs_url=config.docs_url,
    redoc_url=config.redoc_url
)

# Add CORS middleware
app.add_middleware(CORSMiddleware, **config.get_cors_config())

# Middleware for metrics collection
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware to collect API metrics"""
    start_time_req = time.time()

    # Process request
    response = await call_next(request)

    # Record metrics
    duration = time.time() - start_time_req
    status = str(response.status_code)

    metrics_manager.record_api_request(
        method=request.method,
        endpoint=request.url.path,
        duration=duration,
        status=status
    )

    return response

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Nautilus Trader Engine...")

    # Initialize Kafka manager
    kafka_initialized = await kafka_manager.initialize()
    service_status.kafka_connected = kafka_initialized

    if kafka_initialized:
        logger.info("Kafka integration initialized successfully")
        # Start streaming service
        try:
            streaming_started = await kafka_manager.start_streaming_service()
            service_status.kafka_streaming = streaming_started
            if streaming_started:
                logger.info("Kafka streaming service started")
        except Exception as e:
            logger.error(f"Failed to start Kafka streaming service: {e}")
            service_status.kafka_streaming = False
    else:
        logger.warning("Kafka integration failed to initialize")

    logger.info("Nautilus Trader Engine started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Nautilus Trader Engine...")

    # Close Kafka connections
    try:
        await kafka_manager.close()
        logger.info("Kafka connections closed")
    except Exception as e:
        logger.error(f"Error closing Kafka connections: {e}")

    logger.info("Nautilus Trader Engine shutdown complete")

# Include the main router
app.include_router(router)

# Placeholder for trading and strategy management routers
# These will be integrated from nautilus_trader_engine/api/routers
# app.include_router(trading.router, prefix="/api/v1/trading", tags=["Trading"])
# app.include_router(strategy_management.router, prefix="/api/v1/strategies", tags=["Strategies"])

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0", # TODO: Get from config
        port=8000, # TODO: Get from config
        reload=True,
        log_level="info"
    )
