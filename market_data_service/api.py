"""Market Data Service API

FastAPI service providing REST endpoints for multi-source data feed management
with fallback mechanisms, provider health monitoring, and real-time streaming.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from market_data_service.data_feed_manager import (
    DataFeedManager, 
    AssetClass, 
    DataProvider,
    MarketDataPoint,
    get_data_feed_manager
)
from market_data_service.provider_configs import (
    get_provider_config,
    get_providers_for_asset_class,
    get_available_providers,
    validate_provider_credentials
)
from shared.config import settings
from shared.utils.logging_utils import get_logger

logger = get_logger(__name__)

# Global data feed manager instance
data_feed_manager: Optional[DataFeedManager] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global data_feed_manager
    
    # Startup
    logger.info("Starting Market Data Service...")
    data_feed_manager = DataFeedManager()
    await data_feed_manager.start()
    logger.info("Market Data Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Market Data Service...")
    if data_feed_manager:
        await data_feed_manager.stop()
    logger.info("Market Data Service stopped")

# Create FastAPI app
app = FastAPI(
    title="Market Data Service",
    description="Multi-source data feed management with automatic fallback",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=getattr(settings, 'ALLOWED_ORIGINS', ["*"]),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for API
class MarketDataResponse(BaseModel):
    """Response model for market data"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    asset_class: str
    provider: str
    data_type: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class HistoricalDataRequest(BaseModel):
    """Request model for historical data"""
    symbol: str
    asset_class: AssetClass
    start_date: datetime
    end_date: datetime
    interval: str = "1d"

class ProviderHealthResponse(BaseModel):
    """Response model for provider health status"""
    timestamp: str
    providers: Dict[str, Dict[str, Any]]
    circuit_breakers: Dict[str, Dict[str, Any]]

class ProviderConfigResponse(BaseModel):
    """Response model for provider configuration"""
    name: str
    display_name: str
    tier: str
    api_key_required: bool
    has_api_key: bool
    supported_exchanges: List[str]
    supported_countries: List[str]
    data_quality_score: float
    free_tier_available: bool
    features: Dict[str, bool]

class BulkDataRequest(BaseModel):
    """Request model for bulk data retrieval"""
    symbols: List[str]
    asset_class: AssetClass
    data_type: str = "real_time"  # real_time or historical
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    interval: str = "1d"

# Dependency to get data feed manager
async def get_manager() -> DataFeedManager:
    """Dependency to get the global data feed manager"""
    if data_feed_manager is None:
        raise HTTPException(status_code=503, detail="Data feed manager not initialized")
    return data_feed_manager

# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Market Data Service",
        "version": "1.0.0"
    }

@app.get("/providers", response_model=List[ProviderConfigResponse])
async def get_providers():
    """Get all available data providers and their configurations"""
    providers = []
    available_providers = get_available_providers()
    credentials_status = validate_provider_credentials()
    
    for provider_name in available_providers:
        config = get_provider_config(provider_name)
        if config:
            providers.append(ProviderConfigResponse(
                name=config.name,
                display_name=config.display_name,
                tier=config.tier.value,
                api_key_required=config.api_key_required,
                has_api_key=credentials_status.get(provider_name, False),
                supported_exchanges=config.supported_exchanges,
                supported_countries=config.supported_countries,
                data_quality_score=config.data_quality_score,
                free_tier_available=config.free_tier_available,
                features={
                    "real_time_data": config.features.real_time_data,
                    "historical_data": config.features.historical_data,
                    "options_data": config.features.options_data,
                    "futures_data": config.features.futures_data,
                    "forex_data": config.features.forex_data,
                    "crypto_data": config.features.crypto_data,
                    "fundamental_data": config.features.fundamental_data,
                    "news_data": config.features.news_data
                }
            ))
    
    return providers

@app.get("/providers/health", response_model=ProviderHealthResponse)
async def get_provider_health(manager: DataFeedManager = Depends(get_manager)):
    """Get health status of all data providers"""
    health_status = await manager.get_provider_health_status()
    return ProviderHealthResponse(**health_status)

@app.get("/providers/{asset_class}")
async def get_providers_for_asset(asset_class: AssetClass):
    """Get ordered list of providers for a specific asset class"""
    providers = get_providers_for_asset_class(asset_class.value)
    return {
        "asset_class": asset_class.value,
        "providers": providers,
        "count": len(providers)
    }

@app.get("/data/real-time/{symbol}", response_model=Optional[MarketDataResponse])
async def get_real_time_data(
    symbol: str,
    asset_class: AssetClass = Query(..., description="Asset class of the symbol"),
    manager: DataFeedManager = Depends(get_manager)
):
    """Get real-time market data for a symbol"""
    try:
        data = await manager.get_real_time_data(symbol.upper(), asset_class)
        
        if data:
            return MarketDataResponse(
                symbol=data.symbol,
                timestamp=data.timestamp,
                open=data.open,
                high=data.high,
                low=data.low,
                close=data.close,
                volume=data.volume,
                asset_class=data.asset_class.value,
                provider=data.provider.value,
                data_type=data.data_type.value,
                metadata=data.metadata
            )
        else:
            raise HTTPException(
                status_code=404, 
                detail=f"No real-time data available for {symbol} ({asset_class.value})"
            )
            
    except Exception as e:
        logger.error(f"Error fetching real-time data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/data/historical", response_model=List[MarketDataResponse])
async def get_historical_data(
    request: HistoricalDataRequest,
    manager: DataFeedManager = Depends(get_manager)
):
    """Get historical market data for a symbol"""
    try:
        data_points = await manager.get_historical_data(
            request.symbol.upper(),
            request.asset_class,
            request.start_date,
            request.end_date,
            request.interval
        )
        
        return [
            MarketDataResponse(
                symbol=data.symbol,
                timestamp=data.timestamp,
                open=data.open,
                high=data.high,
                low=data.low,
                close=data.close,
                volume=data.volume,
                asset_class=data.asset_class.value,
                provider=data.provider.value,
                data_type=data.data_type.value,
                metadata=data.metadata
            )
            for data in data_points
        ]
        
    except Exception as e:
        logger.error(f"Error fetching historical data for {request.symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/data/bulk", response_model=Dict[str, List[MarketDataResponse]])
async def get_bulk_data(
    request: BulkDataRequest,
    background_tasks: BackgroundTasks,
    manager: DataFeedManager = Depends(get_manager)
):
    """Get bulk data for multiple symbols"""
    try:
        results = {}
        
        if request.data_type == "real_time":
            # Fetch real-time data for all symbols concurrently
            tasks = [
                manager.get_real_time_data(symbol.upper(), request.asset_class)
                for symbol in request.symbols
            ]
            
            data_points = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, symbol in enumerate(request.symbols):
                symbol_upper = symbol.upper()
                data = data_points[i]
                
                if isinstance(data, Exception):
                    logger.error(f"Error fetching data for {symbol_upper}: {data}")
                    results[symbol_upper] = []
                elif data:
                    results[symbol_upper] = [MarketDataResponse(
                        symbol=data.symbol,
                        timestamp=data.timestamp,
                        open=data.open,
                        high=data.high,
                        low=data.low,
                        close=data.close,
                        volume=data.volume,
                        asset_class=data.asset_class.value,
                        provider=data.provider.value,
                        data_type=data.data_type.value,
                        metadata=data.metadata
                    )]
                else:
                    results[symbol_upper] = []
        
        elif request.data_type == "historical":
            if not request.start_date or not request.end_date:
                raise HTTPException(
                    status_code=400, 
                    detail="start_date and end_date required for historical data"
                )
            
            # Fetch historical data for all symbols concurrently
            tasks = [
                manager.get_historical_data(
                    symbol.upper(), 
                    request.asset_class,
                    request.start_date,
                    request.end_date,
                    request.interval
                )
                for symbol in request.symbols
            ]
            
            data_lists = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, symbol in enumerate(request.symbols):
                symbol_upper = symbol.upper()
                data_list = data_lists[i]
                
                if isinstance(data_list, Exception):
                    logger.error(f"Error fetching historical data for {symbol_upper}: {data_list}")
                    results[symbol_upper] = []
                else:
                    results[symbol_upper] = [
                        MarketDataResponse(
                            symbol=data.symbol,
                            timestamp=data.timestamp,
                            open=data.open,
                            high=data.high,
                            low=data.low,
                            close=data.close,
                            volume=data.volume,
                            asset_class=data.asset_class.value,
                            provider=data.provider.value,
                            data_type=data.data_type.value,
                            metadata=data.metadata
                        )
                        for data in data_list
                    ]
        
        else:
            raise HTTPException(
                status_code=400, 
                detail="data_type must be 'real_time' or 'historical'"
            )
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk data request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/data/stream/{symbol}")
async def stream_real_time_data(
    symbol: str,
    asset_class: AssetClass = Query(..., description="Asset class of the symbol"),
    interval_seconds: int = Query(1, ge=1, le=60, description="Update interval in seconds"),
    manager: DataFeedManager = Depends(get_manager)
):
    """Stream real-time data for a symbol (Server-Sent Events)"""
    from fastapi.responses import StreamingResponse
    import json
    
    async def generate_stream():
        """Generate streaming data"""
        while True:
            try:
                data = await manager.get_real_time_data(symbol.upper(), asset_class)
                
                if data:
                    response_data = MarketDataResponse(
                        symbol=data.symbol,
                        timestamp=data.timestamp,
                        open=data.open,
                        high=data.high,
                        low=data.low,
                        close=data.close,
                        volume=data.volume,
                        asset_class=data.asset_class.value,
                        provider=data.provider.value,
                        data_type=data.data_type.value,
                        metadata=data.metadata
                    )
                    
                    yield f"data: {response_data.model_dump_json()}\n\n"
                else:
                    yield f"data: {{\"error\": \"No data available for {symbol}\"}}\n\n"
                
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in streaming data for {symbol}: {e}")
                yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
                await asyncio.sleep(interval_seconds)
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )

@app.post("/providers/test/{provider_name}")
async def test_provider(
    provider_name: str,
    test_symbol: str = "AAPL",
    asset_class: AssetClass = AssetClass.STOCK,
    manager: DataFeedManager = Depends(get_manager)
):
    """Test a specific data provider"""
    try:
        # Check if provider exists
        if provider_name not in manager.providers:
            raise HTTPException(
                status_code=404, 
                detail=f"Provider {provider_name} not found or not configured"
            )
        
        provider = manager.providers[provider_name]
        
        # Test real-time data
        start_time = datetime.now()
        
        async with provider:
            data = await provider.get_real_time_data(test_symbol, asset_class)
        
        end_time = datetime.now()
        response_time_ms = (end_time - start_time).total_seconds() * 1000
        
        return {
            "provider": provider_name,
            "test_symbol": test_symbol,
            "asset_class": asset_class.value,
            "success": data is not None,
            "response_time_ms": round(response_time_ms, 2),
            "data": {
                "symbol": data.symbol,
                "timestamp": data.timestamp.isoformat(),
                "close": data.close,
                "volume": data.volume
            } if data else None,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error testing provider {provider_name}: {e}")
        return {
            "provider": provider_name,
            "test_symbol": test_symbol,
            "asset_class": asset_class.value,
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/metrics")
async def get_service_metrics(manager: DataFeedManager = Depends(get_manager)):
    """Get service performance metrics"""
    try:
        # Get Kafka producer metrics if available
        kafka_metrics = {}
        if manager.kafka_producer:
            kafka_metrics = manager.kafka_producer.get_metrics()
        
        # Get provider failure counts
        provider_metrics = {
            "failure_counts": manager.failure_counts,
            "circuit_breakers_active": {
                provider.value: count >= manager.circuit_breaker_threshold
                for provider, count in manager.failure_counts.items()
            }
        }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "kafka_producer": kafka_metrics,
            "providers": provider_metrics,
            "service_uptime": "N/A",  # Would need to track startup time
            "total_providers_configured": len(manager.providers)
        }
        
    except Exception as e:
        logger.error(f"Error getting service metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Run the service
    uvicorn.run(
        "market_data_service.api:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )