"""
Nautilus Trader Engine - Main Application Entry Point
Phase 1: Foundational Setup

This module serves as the main entry point for the Nautilus Trader Engine service.
It provides basic health checks and will be expanded in future phases.
"""

import os
import logging
import asyncio
import time
import psutil
import argparse
from typing import Dict, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
import uvicorn

from metrics import get_metrics, initialize_metrics, time_api_request
from kafka_manager import get_kafka_manager, initialize_kafka_manager, close_kafka_manager
from nautilus_trader_engine.adapters.interactive_brokers import InteractiveBrokersAdapter
from nautilus_trader_engine.config.ib_config import get_ib_trading_node_config
from nautilus_trader_engine.api.routers import trading
from nautilus_trader_engine.utils.logging_config import setup_logging
from nautilus_trader_engine.config.database_config import (
    get_postgres_config,
    get_clickhouse_config,
    get_duckdb_config,
)

# Configure structured logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="Nautilus Trader Engine",
    description="High-performance algorithmic trading engine for Phase 1 infrastructure",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for service status
service_status = {
    "kafka_connected": False,
    "kafka_streaming": False,
    "postgres_connected": False,
    "clickhouse_connected": False,
    "duckdb_connected": False,
    "ib_connected": False,
    "last_health_check": None
}
ib_adapter: Optional[InteractiveBrokersAdapter] = None

# Initialize metrics
metrics = initialize_metrics()
start_time = time.time()

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
    
    metrics.record_api_request(
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
    
    # Initialize connections (placeholder for Phase 1)
    await initialize_connections()
    
    # Initialize IB Adapter
    global ib_adapter
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, default="paper", choices=["paper", "live"])
    args, _ = parser.parse_known_args()

    loop = asyncio.get_running_loop()
    ib_config = get_ib_trading_node_config(args.mode).connection_config
    ib_adapter = InteractiveBrokersAdapter(loop, ib_config)
    await ib_adapter.start()
    service_status["ib_connected"] = ib_adapter._is_connected

    # Initialize Kafka manager
    kafka_initialized = await initialize_kafka_manager()
    service_status["kafka_connected"] = kafka_initialized
    
    if kafka_initialized:
        logger.info("Kafka integration initialized successfully")
        # Start streaming service
        try:
            kafka_manager = await get_kafka_manager()
            streaming_started = await kafka_manager.start_streaming_service()
            service_status["kafka_streaming"] = streaming_started
            if streaming_started:
                logger.info("Kafka streaming service started")
        except Exception as e:
            logger.error(f"Failed to start Kafka streaming service: {e}")
            service_status["kafka_streaming"] = False
    else:
        logger.warning("Kafka integration failed to initialize")
    
    # Initialize system metrics
    await update_system_metrics()
    
    logger.info("Nautilus Trader Engine started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Nautilus Trader Engine...")

    # Stop IB Adapter
    if ib_adapter:
        await ib_adapter.stop()
        logger.info("IB Adapter stopped")

    # Close Kafka connections
    try:
        await close_kafka_manager()
        logger.info("Kafka connections closed")
    except Exception as e:
        logger.error(f"Error closing Kafka connections: {e}")
    
    logger.info("Nautilus Trader Engine shutdown complete")

async def initialize_connections():
    """Initialize database and service connections"""
    try:
        # Kafka connection check
        kafka_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
        logger.info(f"Kafka servers configured: {kafka_servers}")
        service_status["kafka_connected"] = True
        metrics.update_db_connection_status("kafka", True)

        # Get database configurations
        postgres_config = get_postgres_config()
        clickhouse_config = get_clickhouse_config()
        duckdb_config = get_duckdb_config()

        # Log PostgreSQL configuration
        logger.info(f"PostgreSQL configured: {postgres_config['host']}/{postgres_config['db']} "
                    f"with pool size {postgres_config['pool_size']}")
        service_status["postgres_connected"] = True
        metrics.update_db_connection_status("postgres", True)

        # Log ClickHouse configuration
        logger.info(f"ClickHouse configured: {clickhouse_config['host']}")
        service_status["clickhouse_connected"] = True
        metrics.update_db_connection_status("clickhouse", True)

        # Log DuckDB configuration
        logger.info(f"DuckDB configured: {duckdb_config['path']}")
        service_status["duckdb_connected"] = True
        metrics.update_db_connection_status("duckdb", True)

        service_status["last_health_check"] = datetime.utcnow().isoformat()

    except Exception as e:
        logger.error(f"Failed to initialize connections: {e}")
        raise


async def update_system_metrics():
    """Update system health and resource metrics"""
    try:
        # Update uptime
        uptime = time.time() - start_time
        metrics.update_uptime(uptime)
        
        # Update system health
        metrics.update_system_health("kafka", service_status["kafka_connected"])
        metrics.update_system_health("postgres", service_status["postgres_connected"])
        metrics.update_system_health("clickhouse", service_status["clickhouse_connected"])
        metrics.update_system_health("duckdb", service_status["duckdb_connected"])
        metrics.update_system_health("ib", service_status["ib_connected"])
        
        # Update resource usage
        process = psutil.Process()
        memory_info = process.memory_info()
        cpu_percent = process.cpu_percent()
        
        metrics.update_resource_usage(memory_info.rss, cpu_percent)
        
    except Exception as e:
        logger.error(f"Failed to update system metrics: {e}")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Nautilus Trader Engine - Phase 1",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Docker and monitoring"""
    try:
        # Update system metrics
        await update_system_metrics()
        
        # Update last health check time
        service_status["last_health_check"] = datetime.utcnow().isoformat()
        
        # Check if all critical services are connected
        all_connected = all([
            service_status["kafka_connected"],
            service_status["postgres_connected"],
            service_status["clickhouse_connected"],
            service_status["duckdb_connected"],
            service_status["ib_connected"]
        ])
        
        if all_connected:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "healthy",
                    "timestamp": service_status["last_health_check"],
                    "services": service_status
                }
            )
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "timestamp": service_status["last_health_check"],
                    "services": service_status
                }
            )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@app.get("/status")
async def get_status():
    """Get detailed service status"""
    return {
        "service": "nautilus-trader-engine",
        "version": "1.0.0",
        "phase": "1",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "services": service_status,
        "configuration": {
            "kafka_servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
            "postgres_host": os.getenv("POSTGRES_HOST", "postgres"),
            "postgres_db": os.getenv("POSTGRES_DB", "trading_system"),
            "clickhouse_host": os.getenv("CLICKHOUSE_HOST", "clickhouse"),
            "duckdb_path": os.getenv("DUCKDB_DATABASE_PATH", "/app/data/duckdb/trading_research.duckdb")
        }
    }

@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint"""
    try:
        # Update system metrics before serving
        await update_system_metrics()
        
        # Get metrics in Prometheus format
        metrics_output = metrics.get_metrics()
        
        return Response(
            content=metrics_output,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
    except Exception as e:
        logger.error(f"Failed to generate metrics: {e}")
        return Response(
            content=f"# Error generating metrics: {str(e)}\n",
            media_type="text/plain; version=0.0.4; charset=utf-8",
            status_code=500
        )

# Include the trading router
app.include_router(trading.router, prefix="/api/v1/trading", tags=["Trading"])

# Include the trading router
app.include_router(trading.router, prefix="/api/v1/trading", tags=["Trading"])

# Phase 1 placeholder endpoints (will be expanded in Phase 2)
@app.get("/api/v1/info")
async def api_info():
    """API information endpoint"""
    return {
        "api_version": "v1",
        "phase": "1",
        "description": "Phase 1 - Foundational Setup",
        "available_endpoints": [
            "/",
            "/health",
            "/status",
            "/metrics",
            "/api/v1/info",
            "/api/v1/backtest/run",
            "/api/v1/kafka/status",
            "/api/v1/kafka/streaming/start",
            "/api/v1/kafka/streaming/stop",
            "/api/v1/kafka/streaming/symbols",
            "/api/v1/kafka/topics",
            "/api/v1/kafka/test"
        ],
        "coming_in_phase_2": [
            "/api/v1/optimize",
            "/api/v1/features/{symbol}",
            "/api/v1/backtest/history"
        ]
    }

@app.post("/api/v1/backtest/run")
async def run_backtest(request: Dict[str, Any] = None):
    """Run a backtest with specified parameters"""
    try:
        # Default parameters
        symbol = request.get("symbol", "AAPL") if request else "AAPL"
        year = request.get("year", 2023) if request else 2023
        initial_capital = request.get("initial_capital", 100000.0) if request else 100000.0
        
        logger.info(f"Starting backtest for {symbol} ({year}) with ${initial_capital:,.2f}")
        
        # Import backtest runner
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        from run_initial_backtest import BacktestRunner
        
        # Create and run backtest
        runner = BacktestRunner(
            symbol=symbol,
            year=year,
            initial_capital=initial_capital
        )
        
        # Fetch data
        if not runner.fetch_data():
            raise HTTPException(status_code=400, detail="Failed to fetch market data")
        
        # Run backtests
        backtrader_result = runner.run_backtrader_backtest()
        trading_gym_result = runner.run_trading_gym_backtest()
        
        # Prepare response
        response = {
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "parameters": {
                "symbol": symbol,
                "year": year,
                "initial_capital": initial_capital,
                "fast_period": runner.fast_period,
                "slow_period": runner.slow_period
            },
            "data_points": len(runner.data) if runner.data is not None else 0,
            "results": {
                "backtrader": backtrader_result,
                "trading_gym": trading_gym_result
            }
        }
        
        logger.info(f"Backtest completed successfully for {symbol}")
        return response
        
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")

@app.get("/api/v1/backtest/status")
async def backtest_status():
    """Get backtest engine status"""
    try:
        # Test if backtest modules are available
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        from run_initial_backtest import BacktestRunner
        from backtesting.backtrader_engine import BacktraderEngine
        from backtesting.trading_gym_engine import TradingGymEngine
        
        return {
            "status": "ready",
            "engines": {
                "backtrader": "available",
                "trading_gym": "available"
            },
            "default_parameters": {
                "symbol": "AAPL",
                "year": 2023,
                "initial_capital": 100000.0,
                "fast_period": 10,
                "slow_period": 30
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except ImportError as e:
        return {
            "status": "error",
            "error": f"Backtest modules not available: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

# Kafka Integration API Endpoints
@app.get("/api/v1/kafka/status")
async def kafka_status():
    """Get Kafka streaming status"""
    try:
        if not service_status["kafka_connected"]:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "disconnected",
                    "error": "Kafka not initialized",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        kafka_manager = await get_kafka_manager()
        status = await kafka_manager.get_streaming_status()
        
        return {
            "status": "connected" if status.get("initialized") else "error",
            "kafka_streaming": status,
            "service_status": {
                "kafka_connected": service_status["kafka_connected"],
                "kafka_streaming": service_status["kafka_streaming"]
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting Kafka status: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@app.post("/api/v1/kafka/streaming/start")
async def start_streaming(request: Dict[str, Any]):
    """Start streaming for a symbol"""
    try:
        symbol = request.get("symbol")
        asset_class = request.get("asset_class", "stock")
        interval = request.get("interval", "1m")
        
        if not symbol:
            raise HTTPException(status_code=400, detail="Symbol is required")
        
        if not service_status["kafka_connected"]:
            raise HTTPException(status_code=503, detail="Kafka not connected")
        
        kafka_manager = await get_kafka_manager()
        result = await kafka_manager.add_streaming_symbol(symbol, asset_class, interval)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting streaming: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/kafka/streaming/stop")
async def stop_streaming(request: Dict[str, Any]):
    """Stop streaming for a symbol"""
    try:
        symbol = request.get("symbol")
        
        if not symbol:
            raise HTTPException(status_code=400, detail="Symbol is required")
        
        if not service_status["kafka_connected"]:
            raise HTTPException(status_code=503, detail="Kafka not connected")
        
        kafka_manager = await get_kafka_manager()
        result = await kafka_manager.remove_streaming_symbol(symbol)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping streaming: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/kafka/streaming/symbols")
async def get_streaming_symbols():
    """Get list of currently streaming symbols"""
    try:
        if not service_status["kafka_connected"]:
            return {
                "symbols": [],
                "error": "Kafka not connected",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        kafka_manager = await get_kafka_manager()
        result = await kafka_manager.get_streaming_symbols()
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting streaming symbols: {e}")
        return {
            "symbols": [],
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@app.get("/api/v1/kafka/topics")
async def get_kafka_topics():
    """Get list of available Kafka topics"""
    try:
        if not service_status["kafka_connected"]:
            return {
                "topics": [],
                "error": "Kafka not connected",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        kafka_manager = await get_kafka_manager()
        result = await kafka_manager.get_kafka_topics()
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting Kafka topics: {e}")
        return {
            "topics": [],
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@app.post("/api/v1/kafka/test")
async def test_kafka_connection():
    """Test Kafka connection and functionality"""
    try:
        if not service_status["kafka_connected"]:
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "error": "Kafka not connected",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        kafka_manager = await get_kafka_manager()
        result = await kafka_manager.test_kafka_connection()
        
        if result["success"]:
            return result
        else:
            return JSONResponse(
                status_code=503,
                content=result
            )
            
    except Exception as e:
        logger.error(f"Error testing Kafka connection: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@app.post("/api/v1/kafka/signal")
async def publish_trading_signal(signal: Dict[str, Any]):
    """Publish a trading signal to Kafka"""
    try:
        if not service_status["kafka_connected"]:
            raise HTTPException(status_code=503, detail="Kafka not connected")
        
        kafka_manager = await get_kafka_manager()
        result = await kafka_manager.publish_trading_signal(signal)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error publishing trading signal: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def main():
    """Main function to run the application."""
    parser = argparse.ArgumentParser(description="Nautilus Trader Engine")
    parser.add_argument(
        "--mode",
        type=str,
        default="paper",
        choices=["paper", "live"],
        help="Trading mode: 'paper' or 'live'",
    )
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    
    args = parser.parse_args()

    # Run the application
    uvicorn.run(
        "main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )

if __name__ == "__main__":
    main()