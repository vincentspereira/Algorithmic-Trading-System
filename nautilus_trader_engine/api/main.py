import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.openapi.utils import get_openapi

# New imports for Phase 4
from datetime import datetime
from .core.config import settings
from .routers import auth, backtest, optimization, features, strategy_builder, rl_optimization, trading, users
from nautilus_trader_engine.database.database import Base, engine
from .models.trading import (
    PortfolioResponse,
    PortfolioPosition,
    OrderRequest,
    OrderResponse,
    RiskSnapshot,
)
from .utils.mock_data import (
    generate_mock_portfolio,
    generate_mock_orders,
    generate_mock_risk_metrics,
    order_history
)
from .core.security import get_current_active_user

# --- Risk Management Service ---
from nautilus_trader_engine.services.risk_management_service import RiskManagementService
risk_management_service = RiskManagementService()

# --- Trading Service ---
from nautilus_trader_engine.services.trading_gateway import TradingGateway
trading_gateway = trading.trading_gateway # Use the gateway from the trading router

import logstash

# Configure logging
host = 'logstash'
port = 5044

# Get the logger and add a handler
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logstash.TCPLogstashHandler(host, port, version=1))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Nautilus Trader Engine API - Phase 4")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    # Initialize mock data
    generate_mock_orders()
    logger.info("Mock order history initialized.")

    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created.")

    # Connect to trading service
    await trading_gateway.connect()

    yield
    
    # Shutdown
    await trading_gateway.disconnect()
    logger.info("Shutting down Nautilus Trader Engine API - Phase 4")


# Initialize FastAPI application
app = FastAPI(
    title="Nautilus Trader Engine API",
    description="""
    ## Advanced Algorithmic Trading System API - Phase 4

    The Nautilus Trader Engine API provides comprehensive endpoints for algorithmic trading operations,
    including real-time trading, portfolio management, risk analysis, backtesting, and optimization.

    ### Key Features

    * **🔐 OAuth2/JWT Authentication** - Secure token-based authentication system
    * **📈 Real-time Trading** - Endpoints for portfolio, orders, and risk management
    * **📊 Advanced Backtesting** - Multiple backtesting engines (Backtrader, TradingGym)
    * **⚡ Hyperparameter Optimization** - Optuna-powered strategy optimization
    * **🎯 Feature Engineering** - Advanced technical indicators and feature extraction

    ### Phase 4 - Trading and Portfolio Endpoints
    This version introduces mock endpoints for managing trading operations, which will be connected
    to the live trading engine in a future phase.
    """,
    version="4.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    openapi_tags=[
        {
            "name": "Trading",
            "description": "Endpoints for managing trading operations including portfolio, orders, and risk.",
        },
        {
            "name": "Authentication",
            "description": "User authentication and token management.",
        },
        {
            "name": "Backtesting",
            "description": "Strategy backtesting and performance analysis.",
        },
        {
            "name": "Optimization",
            "description": "Hyperparameter optimization for trading strategies.",
        },
        {
            "name": "Features",
            "description": "Feature engineering and technical analysis.",
        },
        {
            "name": "System",
            "description": "System health checks and API information.",
        },
    ]
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS if settings.BACKEND_CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed messages"""
    logger.warning(f"Validation error on {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "status": "validation_error",
            "message": "Request validation failed",
            "details": exc.errors(),
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    logger.error(f"HTTP error {exc.status_code} on {request.url}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected error on {request.url}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "internal_error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# --- Trading Endpoints (Phase 4) ---

@app.get("/api/v1/portfolio", response_model=PortfolioResponse, tags=["Trading"], dependencies=[Depends(get_current_active_user)])
async def get_portfolio():
    """
    Retrieve the current portfolio status.

    Returns the user's current portfolio, including cash balance, a list of all positions with their market value,
    and the total portfolio value.
    """
    logger.info("Fetching portfolio status from Trading Gateway.")
    positions_dict = await trading_gateway.get_positions()
    
    portfolio_status = risk_management_service.get_portfolio_status()
    total_value = portfolio_status.get("portfolio_value", 0)

    positions = []
    total_positions_value = 0
    for symbol, data in positions_dict.items():
        quantity = data.get("quantity", 0)
        avg_price = data.get("average_cost", 0)
        market_value = quantity * avg_price  # Using avg_price as market price for now
        total_positions_value += market_value
        positions.append(
            PortfolioPosition(
                symbol=symbol,
                quantity=quantity,
                average_price=avg_price,
                market_value=market_value,
            )
        )

    cash = total_value - total_positions_value

    return PortfolioResponse(
        cash=cash,
        positions=positions,
        total_value=total_value,
    )

@app.post("/api/v1/order", response_model=OrderResponse, status_code=201, tags=["Trading"], dependencies=[Depends(get_current_active_user)])
async def place_order(order: OrderRequest):
    """
    Place a new trading order.

    Accepts order details and places an order through the Interactive Brokers gateway.
    """
    logger.info(f"Received order request: {order.dict()}")

    if order.order_type == "LIMIT" and order.price is None:
        raise HTTPException(status_code=422, detail="Price is required for LIMIT orders.")

    # Check trade risk before placing order
    if not risk_management_service.check_trade_risk(order.symbol, order.quantity, order.price):
        raise HTTPException(status_code=400, detail="Trade violates risk limits.")

    # Place order through trading service
    trade = await trading_gateway.place_order(
        instrument_id=order.symbol,
        side=order.side,
        quantity=order.quantity,
        price=order.price,
        order_type=order.order_type,
    )

    # Update position in risk management service
    risk_management_service.update_position(order.symbol, order.quantity, order.price)

    return trade

@app.get("/api/v1/orders", response_model=list[OrderResponse], tags=["Trading"], dependencies=[Depends(get_current_active_user)])
def get_orders(limit: int = 50):
    """
    Retrieve a list of historical orders.
    
    Returns a list of all historical orders with their current status.
    """
    logger.info(f"Fetching last {limit} orders.")
    return generate_mock_orders(limit)

@app.delete("/api/v1/order/{order_id}", response_model=OrderResponse, tags=["Trading"], dependencies=[Depends(get_current_active_user)])
async def cancel_order(order_id: str):
    """
    Cancel a specific order.

    Cancels an order by its ID through the Interactive Brokers gateway.
    """
    logger.info(f"Attempting to cancel order {order_id}.")

    await trading_gateway.cancel_order(order_id)

    return {"message": f"Order {order_id} cancellation request sent."}

@app.get("/api/v1/risk/snapshot", response_model=RiskSnapshot, tags=["Trading"], dependencies=[Depends(get_current_active_user)])
def get_risk_snapshot():
    """
    Get a real-time snapshot of risk metrics.
    
    Returns key risk metrics including portfolio VaR, position-level Greeks (Delta, Gamma, Theta, Vega),
    and concentration metrics.
    """
    logger.info("Fetching risk snapshot.")
    return risk_management_service.get_portfolio_status()

# Include existing routers
app.include_router(auth.router, prefix=settings.API_V1_STR, tags=["Authentication"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["Users"], dependencies=[Depends(get_current_active_user)])
app.include_router(trading.router, prefix=f"{settings.API_V1_STR}/trading", tags=["Trading"], dependencies=[Depends(get_current_active_user)])
app.include_router(backtest.router, prefix=f"{settings.API_V1_STR}/backtest", tags=["Backtesting"], dependencies=[Depends(get_current_active_user)])
app.include_router(optimization.router, prefix=f"{settings.API_V1_STR}/optimise", tags=["Optimization"], dependencies=[Depends(get_current_active_user)])
app.include_router(features.router, prefix=f"{settings.API_V1_STR}/features", tags=["Features"], dependencies=[Depends(get_current_active_user)])
app.include_router(strategy_builder.router, prefix=f"{settings.API_V1_STR}/strategy-builder", tags=["Strategy Builder"], dependencies=[Depends(get_current_active_user)])
app.include_router(rl_optimization.router, prefix=f"{settings.API_V1_STR}/rl-optimization", tags=["RL Optimization"], dependencies=[Depends(get_current_active_user)])

# Root endpoint
@app.get(
    "/",
    tags=["System"],
    summary="API Root Information",
    response_description="API information and feature list"
)
async def root():
    return {
        "message": "Nautilus Trader Engine API - Phase 4",
        "version": "4.0.0",
        "docs_url": "/docs",
        "api_prefix": settings.API_V1_STR,
    }

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "true").lower() == "true"
    
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run(
        "nautilus_trader_engine.api.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )