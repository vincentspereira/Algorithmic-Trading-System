"""
Comprehensive API Layer for Algorithmic Trading System
FastAPI-based REST, WebSocket, GraphQL, and gRPC services

This module provides:
- REST API endpoints for CRUD operations
- Real-time WebSocket streams for market data and signals
- GraphQL queries for complex data relationships
- gRPC services for high-performance order execution
- Authentication and authorization
- Rate limiting and monitoring

Author: Vincent S. Pereira
Version: 1.0.0
Phase: 1 - Core System Development
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import json
import uuid

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import uvicorn
from pydantic import BaseModel, Field, validator
import redis
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import structlog

# Import our custom modules
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nautilus_trader_engine.indicators.comprehensive_indicators import ComprehensiveIndicators
from nautilus_trader_engine.core.data_feed_manager import DataFeedManager
from nautilus_trader_engine.core.order_management import OrderManager
from nautilus_trader_engine.core.risk_management import RiskManager

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

# Prometheus metrics
api_requests = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
api_duration = Histogram('api_request_duration_seconds', 'API request duration')
active_websockets = Gauge('active_websockets', 'Number of active WebSocket connections')
indicator_calculations = Counter('indicator_calculations_total', 'Total indicator calculations', ['indicator_type'])
order_submissions = Counter('order_submissions_total', 'Total order submissions', ['order_type', 'status'])

# ===========================================
# PYDANTIC MODELS FOR REQUEST/RESPONSE
# ===========================================

class TradingSymbol(BaseModel):
    """Trading symbol model"""
    symbol: str = Field(..., example="AAPL")
    exchange: str = Field(..., example="NASDAQ")
    asset_class: str = Field(..., example="STK")
    
    @validator('symbol')
    def symbol_must_be_uppercase(cls, v):
        return v.upper()

class MarketDataRequest(BaseModel):
    """Market data request model"""
    symbols: List[TradingSymbol]
    period: str = Field(default="1d", example="1d")
    interval: str = Field(default="1m", example="1m")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class IndicatorRequest(BaseModel):
    """Technical indicator request model"""
    symbol: TradingSymbol
    indicator_types: List[str] = Field(..., example=["rsi", "macd", "bollinger_bands"])
    include_volume_weighted: bool = Field(default=True)
    include_patterns: bool = Field(default=True)
    period_override: Optional[Dict[str, int]] = None

class OrderRequest(BaseModel):
    """Order submission request model"""
    symbol: TradingSymbol
    order_type: str = Field(..., example="MARKET")  # MARKET, LIMIT, STOP
    side: str = Field(..., example="BUY")  # BUY, SELL
    quantity: float = Field(..., gt=0, example=100.0)
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = Field(default="DAY", example="DAY")
    
    @validator('side')
    def side_must_be_valid(cls, v):
        if v.upper() not in ['BUY', 'SELL']:
            raise ValueError('Side must be BUY or SELL')
        return v.upper()

class PortfolioPosition(BaseModel):
    """Portfolio position model"""
    symbol: TradingSymbol
    quantity: float
    avg_cost: float
    market_value: float
    unrealized_pnl: float
    realized_pnl: float
    last_updated: datetime

class APIResponse(BaseModel):
    """Standard API response model"""
    success: bool
    data: Optional[Any] = None
    message: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

# ===========================================
# WEBSOCKET CONNECTION MANAGER
# ===========================================

class ConnectionManager:
    """WebSocket connection manager for real-time data streaming"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.symbol_subscriptions: Dict[str, List[WebSocket]] = {}
        self.client_info: Dict[WebSocket, Dict] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.client_info[websocket] = {
            "client_id": client_id,
            "connected_at": datetime.now(),
            "subscriptions": []
        }
        active_websockets.inc()
        logger.info("WebSocket connected", client_id=client_id, total_connections=len(self.active_connections))
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            
            # Remove from symbol subscriptions
            client_info = self.client_info.get(websocket, {})
            for symbol in client_info.get("subscriptions", []):
                if symbol in self.symbol_subscriptions:
                    if websocket in self.symbol_subscriptions[symbol]:
                        self.symbol_subscriptions[symbol].remove(websocket)
            
            if websocket in self.client_info:
                del self.client_info[websocket]
            
            active_websockets.dec()
            logger.info("WebSocket disconnected", total_connections=len(self.active_connections))
    
    async def subscribe_symbol(self, websocket: WebSocket, symbol: str):
        """Subscribe client to symbol updates"""
        if symbol not in self.symbol_subscriptions:
            self.symbol_subscriptions[symbol] = []
        
        if websocket not in self.symbol_subscriptions[symbol]:
            self.symbol_subscriptions[symbol].append(websocket)
            
            if websocket in self.client_info:
                self.client_info[websocket]["subscriptions"].append(symbol)
        
        logger.info("Symbol subscription added", symbol=symbol, 
                   subscribers=len(self.symbol_subscriptions[symbol]))
    
    async def broadcast_to_symbol(self, symbol: str, message: dict):
        """Broadcast message to all subscribers of a symbol"""
        if symbol in self.symbol_subscriptions:
            disconnected = []
            for websocket in self.symbol_subscriptions[symbol]:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error("Failed to send message", symbol=symbol, error=str(e))
                    disconnected.append(websocket)
            
            # Clean up disconnected clients
            for websocket in disconnected:
                self.disconnect(websocket)
    
    async def broadcast_all(self, message: dict):
        """Broadcast message to all connected clients"""
        disconnected = []
        for websocket in self.active_connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error("Failed to broadcast message", error=str(e))
                disconnected.append(websocket)
        
        # Clean up disconnected clients
        for websocket in disconnected:
            self.disconnect(websocket)

# ===========================================
# FASTAPI APPLICATION SETUP
# ===========================================

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

# Security
security = HTTPBearer()

# Global instances
connection_manager = ConnectionManager()
indicators_engine = ComprehensiveIndicators()
data_feed_manager = DataFeedManager()
order_manager = OrderManager()
risk_manager = RiskManager()

# Redis for caching (if available)
try:
    redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
    redis_client.ping()
    REDIS_AVAILABLE = True
    logger.info("Redis connection established")
except:
    REDIS_AVAILABLE = False
    redis_client = None
    logger.warning("Redis not available, using in-memory caching")

# ===========================================
# AUTHENTICATION & MIDDLEWARE
# ===========================================

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token (simplified for demo)"""
    # In production, implement proper JWT validation
    token = credentials.credentials
    if not token or token == "invalid":
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    return {"user_id": "demo_user", "permissions": ["read", "write", "trade"]}

# ===========================================
# UTILITY FUNCTIONS
# ===========================================

def get_cache_key(prefix: str, **kwargs) -> str:
    """Generate cache key from parameters"""
    key_parts = [prefix]
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}:{v}")
    return ":".join(key_parts)

async def get_cached_data(key: str) -> Optional[Any]:
    """Get data from cache"""
    if not REDIS_AVAILABLE:
        return None
    
    try:
        data = redis_client.get(key)
        return json.loads(data) if data else None
    except Exception as e:
        logger.error("Cache read error", key=key, error=str(e))
        return None

async def set_cached_data(key: str, data: Any, ttl: int = 300):
    """Set data in cache with TTL"""
    if not REDIS_AVAILABLE:
        return
    
    try:
        redis_client.setex(key, ttl, json.dumps(data, default=str))
    except Exception as e:
        logger.error("Cache write error", key=key, error=str(e))

# ===========================================
# HEALTH & METRICS ENDPOINTS
# ===========================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "version": "1.0.0",
        "services": {
            "redis": REDIS_AVAILABLE,
            "data_feeds": await data_feed_manager.health_check(),
            "indicators": True,
            "websockets": len(connection_manager.active_connections)
        }
    }

@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    return generate_latest()

# ===========================================
# MARKET DATA ENDPOINTS
# ===========================================

@app.post("/api/v1/market-data", response_model=APIResponse)
async def get_market_data(
    request: MarketDataRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(verify_token)
):
    """Get historical market data for symbols"""
    with api_duration.time():
        api_requests.labels(method="POST", endpoint="/market-data", status="started").inc()
        
        try:
            # Check cache first
            cache_key = get_cache_key("market_data", 
                                    symbols=[s.symbol for s in request.symbols],
                                    period=request.period,
                                    interval=request.interval)
            
            cached_data = await get_cached_data(cache_key)
            if cached_data:
                api_requests.labels(method="POST", endpoint="/market-data", status="cache_hit").inc()
                return APIResponse(success=True, data=cached_data, message="Data retrieved from cache")
            
            # Fetch fresh data
            results = {}
            for symbol in request.symbols:
                try:
                    data = await data_feed_manager.get_historical_data(
                        symbol=symbol.symbol,
                        period=request.period,
                        interval=request.interval,
                        start_date=request.start_date,
                        end_date=request.end_date
                    )
                    # Convert DataFrame to JSON-serializable format
                    if hasattr(data, 'to_dict'):
                        data_dict = data.to_dict('records')
                        results[symbol.symbol] = {
                            "data": data_dict,
                            "symbol": symbol.symbol,
                            "period": request.period,
                            "interval": request.interval,
                            "rows": len(data_dict)
                        }
                    else:
                        results[symbol.symbol] = data
                except Exception as e:
                    logger.error("Failed to fetch data", symbol=symbol.symbol, error=str(e))
                    results[symbol.symbol] = {"error": str(e)}
            
            # Cache successful results
            background_tasks.add_task(set_cached_data, cache_key, results, 300)
            
            api_requests.labels(method="POST", endpoint="/market-data", status="success").inc()
            return APIResponse(success=True, data=results, message=f"Retrieved data for {len(results)} symbols")
            
        except Exception as e:
            api_requests.labels(method="POST", endpoint="/market-data", status="error").inc()
            logger.error("Market data request failed", error=str(e))
            raise HTTPException(status_code=500, detail=f"Failed to retrieve market data: {str(e)}")

@app.get("/api/v1/market-data/quote/{symbol}")
async def get_real_time_quote(symbol: str, user: dict = Depends(verify_token)):
    """Get real-time quote for a symbol"""
    try:
        quote = await data_feed_manager.get_real_time_quote(symbol.upper())
        return APIResponse(success=True, data=quote, message=f"Real-time quote for {symbol}")
    except Exception as e:
        logger.error("Real-time quote failed", symbol=symbol, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get quote: {str(e)}")

# ===========================================
# TECHNICAL INDICATORS ENDPOINTS  
# ===========================================

@app.post("/api/v1/indicators", response_model=APIResponse)
async def calculate_indicators(
    request: IndicatorRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(verify_token)
):
    """Calculate technical indicators for a symbol"""
    with api_duration.time():
        try:
            # Check cache first
            cache_key = get_cache_key("indicators",
                                    symbol=request.symbol.symbol,
                                    indicators=sorted(request.indicator_types),
                                    volume_weighted=request.include_volume_weighted,
                                    patterns=request.include_patterns)
            
            cached_data = await get_cached_data(cache_key)
            if cached_data:
                return APIResponse(success=True, data=cached_data, message="Indicators retrieved from cache")
            
            # Get market data first
            market_data = await data_feed_manager.get_historical_data(
                symbol=request.symbol.symbol,
                period="1y",  # Use more data for better indicator calculations
                interval="1d"
            )
            
            if market_data is None or (hasattr(market_data, 'empty') and market_data.empty):
                raise HTTPException(status_code=404, detail=f"No market data found for {request.symbol.symbol}")
            
            # Prepare data for indicators
            data_dict = {
                'open': market_data['Open'],
                'high': market_data['High'], 
                'low': market_data['Low'],
                'close': market_data['Close'],
                'volume': market_data['Volume']
            }
            
            # Calculate all indicators
            all_indicators = indicators_engine.calculate_all_indicators(
                data_dict,
                include_patterns=request.include_patterns,
                include_volume_weighted=request.include_volume_weighted
            )
            
            # Filter requested indicators if specified
            if request.indicator_types and request.indicator_types != ["all"]:
                filtered_indicators = {}
                for indicator_name, result in all_indicators.items():
                    for requested_type in request.indicator_types:
                        if requested_type.lower() in indicator_name.lower():
                            filtered_indicators[indicator_name] = {
                                "name": result.indicator_name,
                                "category": result.category.value,
                                "signal": result.signal,
                                "strength": result.strength,
                                "confidence": result.confidence,
                                "volume_weighted": result.volume_weighted,
                                "metadata": result.metadata
                            }
                all_indicators = filtered_indicators
            else:
                # Convert to serializable format
                serializable_indicators = {}
                for name, result in all_indicators.items():
                    serializable_indicators[name] = {
                        "name": result.indicator_name,
                        "category": result.category.value,
                        "signal": result.signal,
                        "strength": result.strength,
                        "confidence": result.confidence,
                        "volume_weighted": result.volume_weighted,
                        "metadata": result.metadata
                    }
                all_indicators = serializable_indicators
            
            # Get summary
            summary = indicators_engine.get_indicator_summary(
                {k: type('MockResult', (), {
                    'indicator_name': v['name'],
                    'category': type('MockCategory', (), {'value': v['category']})(),
                    'signal': v['signal'],
                    'strength': v['strength'],
                    'confidence': v['confidence'],
                    'volume_weighted': v['volume_weighted']
                })() for k, v in all_indicators.items()}
            )
            
            result_data = {
                "symbol": request.symbol.symbol,
                "indicators": all_indicators,
                "summary": summary,
                "calculation_time": datetime.now(),
                "data_points": len(market_data)
            }
            
            # Update metrics
            for indicator_type in request.indicator_types:
                indicator_calculations.labels(indicator_type=indicator_type).inc()
            
            # Cache results
            background_tasks.add_task(set_cached_data, cache_key, result_data, 600)
            
            return APIResponse(success=True, data=result_data, 
                             message=f"Calculated {len(all_indicators)} indicators")
            
        except Exception as e:
            logger.error("Indicator calculation failed", symbol=request.symbol.symbol, error=str(e))
            raise HTTPException(status_code=500, detail=f"Indicator calculation failed: {str(e)}")

@app.get("/api/v1/indicators/available")
async def get_available_indicators(user: dict = Depends(verify_token)):
    """Get list of available indicators"""
    indicators_info = {
        "trend_indicators": [
            "sma", "ema", "vwma", "vw_ema", "hull_ma", "kama", "dema", "tema", 
            "mcginley_dynamic", "zero_lag_ema", "linear_regression"
        ],
        "momentum_indicators": [
            "rsi", "vw_rsi", "macd", "vw_macd", "stochastic", "williams_r", 
            "cci", "awesome_oscillator", "fisher_transform"
        ],
        "volatility_indicators": [
            "bollinger_bands", "atr", "vw_atr", "vw_atrp", "keltner_channels", 
            "donchian_channels", "historical_volatility", "adx"
        ],
        "volume_indicators": [
            "vwap", "obv", "enhanced_vwap", "enhanced_obv", "ad_line", 
            "mfi", "cmf", "volume_roc", "pvt", "emv"
        ],
        "candlestick_patterns": [
            "doji", "hammer", "hanging_man", "shooting_star", "marubozu", 
            "spinning_top", "engulfing", "harami", "morning_star", "evening_star"
        ]
    }
    
    return APIResponse(success=True, data=indicators_info, 
                     message="Available indicators by category")

# ===========================================
# ORDER MANAGEMENT ENDPOINTS
# ===========================================

@app.post("/api/v1/orders", response_model=APIResponse)
async def submit_order(
    request: OrderRequest,
    user: dict = Depends(verify_token)
):
    """Submit a new trading order"""
    try:
        # Check user permissions
        if "trade" not in user.get("permissions", []):
            raise HTTPException(status_code=403, detail="Trading permission required")
        
        # Risk management check
        risk_check = await risk_manager.validate_order(
            symbol=request.symbol.symbol,
            side=request.side,
            quantity=request.quantity,
            price=request.price,
            user_id=user["user_id"]
        )
        
        if not risk_check["approved"]:
            raise HTTPException(status_code=400, detail=f"Order rejected: {risk_check['reason']}")
        
        # Submit order
        order_result = await order_manager.submit_order(
            symbol=request.symbol.symbol,
            order_type=request.order_type,
            side=request.side,
            quantity=request.quantity,
            price=request.price,
            stop_price=request.stop_price,
            time_in_force=request.time_in_force,
            user_id=user["user_id"]
        )
        
        # Update metrics
        order_submissions.labels(
            order_type=request.order_type,
            status="submitted" if order_result["success"] else "failed"
        ).inc()
        
        # Broadcast order update via WebSocket
        await connection_manager.broadcast_all({
            "type": "order_update",
            "data": order_result,
            "timestamp": datetime.now().isoformat()
        })
        
        return APIResponse(
            success=order_result["success"],
            data=order_result,
            message=f"Order {order_result.get('order_id', 'unknown')} {'submitted' if order_result['success'] else 'failed'}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        order_submissions.labels(order_type=request.order_type, status="error").inc()
        logger.error("Order submission failed", error=str(e), symbol=request.symbol.symbol)
        raise HTTPException(status_code=500, detail=f"Order submission failed: {str(e)}")

@app.get("/api/v1/orders")
async def get_orders(
    status: Optional[str] = None,
    symbol: Optional[str] = None,
    limit: int = 100,
    user: dict = Depends(verify_token)
):
    """Get user's orders with optional filtering"""
    try:
        orders = await order_manager.get_orders(
            user_id=user["user_id"],
            status=status,
            symbol=symbol,
            limit=limit
        )
        
        return APIResponse(
            success=True,
            data={"orders": orders, "count": len(orders)},
            message=f"Retrieved {len(orders)} orders"
        )
        
    except Exception as e:
        logger.error("Failed to retrieve orders", user_id=user["user_id"], error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve orders: {str(e)}")

@app.delete("/api/v1/orders/{order_id}")
async def cancel_order(order_id: str, user: dict = Depends(verify_token)):
    """Cancel an existing order"""
    try:
        result = await order_manager.cancel_order(order_id, user["user_id"])
        
        # Broadcast cancellation via WebSocket
        await connection_manager.broadcast_all({
            "type": "order_cancelled",
            "data": {"order_id": order_id, "result": result},
            "timestamp": datetime.now().isoformat()
        })
        
        return APIResponse(
            success=result["success"],
            data=result,
            message=f"Order {order_id} {'cancelled' if result['success'] else 'cancellation failed'}"
        )
        
    except Exception as e:
        logger.error("Order cancellation failed", order_id=order_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Order cancellation failed: {str(e)}")

# ===========================================
# PORTFOLIO ENDPOINTS
# ===========================================

@app.get("/api/v1/portfolio/positions")
async def get_portfolio_positions(user: dict = Depends(verify_token)):
    """Get user's portfolio positions"""
    try:
        positions = await order_manager.get_positions(user["user_id"])
        
        portfolio_summary = {
            "total_value": sum(pos.get("market_value", 0) for pos in positions),
            "total_pnl": sum(pos.get("unrealized_pnl", 0) for pos in positions),
            "position_count": len(positions),
            "last_updated": datetime.now()
        }
        
        return APIResponse(
            success=True,
            data={"positions": positions, "summary": portfolio_summary},
            message=f"Retrieved {len(positions)} positions"
        )
        
    except Exception as e:
        logger.error("Failed to retrieve positions", user_id=user["user_id"], error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve positions: {str(e)}")

@app.get("/api/v1/portfolio/performance")
async def get_portfolio_performance(
    period: str = "1d",
    user: dict = Depends(verify_token)
):
    """Get portfolio performance metrics"""
    try:
        performance = await order_manager.get_portfolio_performance(
            user_id=user["user_id"],
            period=period
        )
        
        return APIResponse(
            success=True,
            data=performance,
            message=f"Portfolio performance for {period}"
        )
        
    except Exception as e:
        logger.error("Failed to retrieve performance", user_id=user["user_id"], error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve performance: {str(e)}")

# ===========================================
# WEBSOCKET ENDPOINTS
# ===========================================

@app.websocket("/ws/market-data/{client_id}")
async def websocket_market_data(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time market data"""
    await connection_manager.connect(websocket, client_id)
    
    try:
        while True:
            # Wait for subscription messages
            data = await websocket.receive_json()
            
            if data.get("type") == "subscribe":
                symbol = data.get("symbol", "").upper()
                if symbol:
                    await connection_manager.subscribe_symbol(websocket, symbol)
                    await websocket.send_json({
                        "type": "subscription_confirmed",
                        "symbol": symbol,
                        "timestamp": datetime.now().isoformat()
                    })
            
            elif data.get("type") == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                })
                
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
        logger.info("Market data WebSocket disconnected", client_id=client_id)
    except Exception as e:
        logger.error("WebSocket error", client_id=client_id, error=str(e))
        connection_manager.disconnect(websocket)

@app.websocket("/ws/trading/{client_id}")
async def websocket_trading(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time trading updates"""
    await connection_manager.connect(websocket, client_id)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "subscribe_orders":
                # Subscribe to order updates for this user
                await websocket.send_json({
                    "type": "order_subscription_confirmed",
                    "timestamp": datetime.now().isoformat()
                })
            
            elif data.get("type") == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                })
                
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
        logger.info("Trading WebSocket disconnected", client_id=client_id)
    except Exception as e:
        logger.error("Trading WebSocket error", client_id=client_id, error=str(e))
        connection_manager.disconnect(websocket)

# ===========================================
# BACKGROUND TASKS
# ===========================================

async def market_data_streamer():
    """Background task to stream real-time market data"""
    while True:
        try:
            # Get active symbol subscriptions
            active_symbols = list(connection_manager.symbol_subscriptions.keys())
            
            if active_symbols:
                # Fetch real-time data for subscribed symbols
                for symbol in active_symbols:
                    try:
                        quote = await data_feed_manager.get_real_time_quote(symbol)
                        if quote:
                            await connection_manager.broadcast_to_symbol(symbol, {
                                "type": "market_data",
                                "symbol": symbol,
                                "data": quote,
                                "timestamp": datetime.now().isoformat()
                            })
                    except Exception as e:
                        logger.error("Failed to stream data", symbol=symbol, error=str(e))
            
            await asyncio.sleep(1)  # Update frequency: 1 second
            
        except Exception as e:
            logger.error("Market data streamer error", error=str(e))
            await asyncio.sleep(5)  # Error recovery delay

async def indicator_calculator():
    """Background task to calculate indicators for subscribed symbols"""
    while True:
        try:
            active_symbols = list(connection_manager.symbol_subscriptions.keys())
            
            if active_symbols:
                for symbol in active_symbols:
                    try:
                        # Calculate key indicators
                        market_data = await data_feed_manager.get_historical_data(
                            symbol=symbol, period="1d", interval="1m"
                        )
                        
                        if not market_data.empty:
                            # Quick indicator calculation
                            data_dict = {
                                'open': market_data['Open'],
                                'high': market_data['High'],
                                'low': market_data['Low'],
                                'close': market_data['Close'],
                                'volume': market_data['Volume']
                            }
                            
                            # Calculate a subset of key indicators
                            rsi_result = indicators_engine.traditional_indicators.rsi(data_dict['close'], 14)
                            macd_result = indicators_engine.traditional_indicators.macd(data_dict['close'], 12, 26, 9)
                            
                            indicator_update = {
                                "type": "indicators",
                                "symbol": symbol,
                                "data": {
                                    "rsi": {
                                        "value": float(rsi_result.value.iloc[-1]) if hasattr(rsi_result.value, 'iloc') else rsi_result.value,
                                        "signal": rsi_result.signal,
                                        "strength": rsi_result.strength
                                    },
                                    "macd": {
                                        "signal": macd_result.signal,
                                        "strength": macd_result.strength
                                    }
                                },
                                "timestamp": datetime.now().isoformat()
                            }
                            
                            await connection_manager.broadcast_to_symbol(symbol, indicator_update)
                            
                    except Exception as e:
                        logger.error("Failed to calculate indicators", symbol=symbol, error=str(e))
            
            await asyncio.sleep(30)  # Update frequency: 30 seconds
            
        except Exception as e:
            logger.error("Indicator calculator error", error=str(e))
            await asyncio.sleep(60)  # Error recovery delay

# ===========================================
# APPLICATION LIFECYCLE
# ===========================================

@app.on_event("startup")
async def startup_event():
    """Application startup tasks"""
    logger.info("Starting Algorithmic Trading System API")
    
    # Initialize services
    await data_feed_manager.initialize()
    await order_manager.initialize()
    await risk_manager.initialize()
    
    # Start background tasks
    asyncio.create_task(market_data_streamer())
    asyncio.create_task(indicator_calculator())
    
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
    await order_manager.cleanup()
    await risk_manager.cleanup()
    
    logger.info("API shutdown completed")

# ===========================================
# ERROR HANDLERS
# ===========================================

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
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )