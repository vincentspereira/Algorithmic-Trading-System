import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.backtesting.runner import BacktestRunner
from app.metrics.prometheus_metrics import metrics_manager
from app.status.service_status import service_status
from app.services.kafka_manager import KafkaManager

logger = logging.getLogger(__name__)

router = APIRouter()
kafka_manager = KafkaManager()

@router.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Nautilus Trader Engine - Phase 1",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/health")
async def health_check():
    """Health check endpoint for Docker and monitoring"""
    try:
        # Update system metrics
        metrics_manager.update_uptime()
        metrics_manager.update_resource_usage()

        # Update last health check time
        service_status.last_health_check = datetime.utcnow().isoformat()

        # Check if all critical services are connected
        if service_status.is_healthy():
            return {
                "status": "healthy",
                "timestamp": service_status.last_health_check,
                "services": service_status.to_dict()
            }
        else:
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "unhealthy",
                    "timestamp": service_status.last_health_check,
                    "services": service_status.to_dict()
                }
            )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@router.get("/status")
async def get_status():
    """Get detailed service status"""
    return {
        "service": "nautilus-trader-engine",
        "version": "1.0.0",
        "phase": "1",
        "environment": "development", # TODO: Get from config
        "services": service_status.to_dict(),
        "configuration": {
            "kafka_servers": "kafka:9092", # TODO: Get from config
            "postgres_host": "postgres", # TODO: Get from config
            "postgres_db": "trading_system", # TODO: Get from config
            "clickhouse_host": "clickhouse", # TODO: Get from config
            "duckdb_path": "/app/data/duckdb/trading_research.duckdb" # TODO: Get from config
        }
    }

@router.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint"""
    try:
        # Update system metrics before serving
        metrics_manager.update_uptime()
        metrics_manager.update_resource_usage()

        # Get metrics in Prometheus format
        metrics_output = metrics_manager.get_metrics()

        return Response(
            content=metrics_output,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
    except Exception as e:
        logger.error(f"Failed to generate metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"# Error generating metrics: {str(e)}\n"
        )

@router.post("/backtest/run")
async def run_backtest(request: Dict[str, Any] = None):
    """Run a backtest with specified parameters"""
    try:
        # Default parameters
        symbol = request.get("symbol", "AAPL") if request else "AAPL"
        year = request.get("year", 2023) if request else 2023
        initial_capital = request.get("initial_capital", 100000.0) if request else 100000.0

        logger.info(f"Starting backtest for {symbol} ({year}) with ${initial_capital:,.2f}")

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

@router.get("/backtest/status")
async def backtest_status():
    """Get backtest engine status"""
    try:
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

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

# Kafka Integration API Endpoints
@router.get("/kafka/status")
async def kafka_status():
    """Get Kafka streaming status"""
    try:
        if not service_status.kafka_connected:
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "disconnected",
                    "error": "Kafka not initialized",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        status = await kafka_manager.get_streaming_status()

        return {
            "status": "connected" if status.get("initialized") else "error",
            "kafka_streaming": status,
            "service_status": {
                "kafka_connected": service_status.kafka_connected,
                "kafka_streaming": service_status.kafka_streaming
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting Kafka status: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@router.post("/kafka/streaming/start")
async def start_streaming(request: Dict[str, Any]):
    """Start streaming for a symbol"""
    try:
        symbol = request.get("symbol")
        asset_class = request.get("asset_class", "stock")
        interval = request.get("interval", "1m")

        if not symbol:
            raise HTTPException(status_code=400, detail="Symbol is required")

        if not service_status.kafka_connected:
            raise HTTPException(status_code=503, detail="Kafka not connected")

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

@router.post("/kafka/streaming/stop")
async def stop_streaming(request: Dict[str, Any]):
    """Stop streaming for a symbol"""
    try:
        symbol = request.get("symbol")

        if not symbol:
            raise HTTPException(status_code=400, detail="Symbol is required")

        if not service_status.kafka_connected:
            raise HTTPException(status_code=503, detail="Kafka not connected")

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

@router.get("/kafka/streaming/symbols")
async def get_streaming_symbols():
    """Get list of currently streaming symbols"""
    try:
        if not service_status.kafka_connected:
            return {
                "symbols": [],
                "error": "Kafka not connected",
                "timestamp": datetime.utcnow().isoformat()
            }

        result = await kafka_manager.get_streaming_symbols()

        return result

    except Exception as e:
        logger.error(f"Error getting streaming symbols: {e}")
        return {
            "symbols": [],
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/kafka/topics")
async def get_kafka_topics():
    """Get list of available Kafka topics"""
    try:
        if not service_status.kafka_connected:
            return {
                "topics": [],
                "error": "Kafka not connected",
                "timestamp": datetime.utcnow().isoformat()
            }

        result = await kafka_manager.get_kafka_topics()

        return result

    except Exception as e:
        logger.error(f"Error getting Kafka topics: {e}")
        return {
            "topics": [],
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.post("/kafka/test")
async def test_kafka_connection():
    """Test Kafka connection and functionality"""
    try:
        if not service_status.kafka_connected:
            raise HTTPException(
                status_code=503,
                detail={
                    "success": False,
                    "error": "Kafka not connected",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        result = await kafka_manager.test_kafka_connection()

        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=503,
                detail=result
            )

    except Exception as e:
        logger.error(f"Error testing Kafka connection: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@router.post("/kafka/signal")
async def publish_trading_signal(signal: Dict[str, Any]):
    """Publish a trading signal to Kafka"""
    try:
        if not service_status.kafka_connected:
            raise HTTPException(status_code=503, detail="Kafka not connected")

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