
import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import structlog

from api.app.api import health, market_data, indicators, orders, portfolio
from api.app.background.tasks import market_data_streamer, indicator_calculator
from api.app.core.config import api_settings
from api.app.models import APIResponse
from api.app.websockets import ConnectionManager
from nautilus_trader_engine.core.data_feed_manager import DataFeedManager
from nautilus_trader_engine.indicators.comprehensive_indicators import ComprehensiveIndicators
from api.app.services.kafka_service import KafkaService

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

app = FastAPI(
    title="Algorithmic Trading System API",
    description="Comprehensive API for real-time trading, market data, and technical analysis",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(market_data.router, prefix="/api/v1", tags=["Market Data"])
app.include_router(indicators.router, prefix="/api/v1", tags=["Indicators"])
app.include_router(orders.router, prefix="/api/v1", tags=["Orders"])
app.include_router(portfolio.router, prefix="/api/v1", tags=["Portfolio"])

# Global instances
connection_manager = ConnectionManager()
indicators_engine = ComprehensiveIndicators()
data_feed_manager = DataFeedManager()
kafka_service = KafkaService(bootstrap_servers=api_settings.KAFKA_BOOTSTRAP_SERVERS)

@app.on_event("startup")
async def startup_event():
    """Application startup tasks"""
    logger.info("Starting Algorithmic Trading System API")

    # Initialize services
    await data_feed_manager.initialize()

    await kafka_service.start()

    # Start background tasks
    asyncio.create_task(market_data_streamer(connection_manager, data_feed_manager))
    asyncio.create_task(indicator_calculator(connection_manager, data_feed_manager, indicators_engine))

    logger.info("API startup completed")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks"""
    logger.info("Shutting down Algorithmic Trading System API")

    # Close WebSocket connections
    for websocket in connection_manager.active_connections.copy():
        try:
            await websocket.close()
        except:
            pass

    # Cleanup services
    await data_feed_manager.cleanup()

    await kafka_service.stop()

    logger.info("API shutdown completed")

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 handler"""
    return JSONResponse(
        status_code=404,
        content=APIResponse(
            success=False,
            message="Endpoint not found",
            data={"path": str(request.url.path)}
        ).dict()
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Custom 500 handler"""
    logger.error("Internal server error", path=str(request.url.path), error=str(exc))
    return JSONResponse(
        status_code=500,
        content=APIResponse(
            success=False,
            message="Internal server error",
            data={"error_type": type(exc).__name__}
        ).dict()
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=api_settings.BACKTEST_SERVICE_HOST,
        port=api_settings.BACKTEST_SERVICE_PORT,
        reload=True,
        log_level="info"
    )
