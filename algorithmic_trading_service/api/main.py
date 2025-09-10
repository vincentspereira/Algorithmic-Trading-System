"""Core Trading Engine API

Comprehensive trading service providing order management, strategy execution,
risk management, and portfolio tracking capabilities.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager
from enum import Enum

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Query, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import uvicorn
import logging

# Import shared components
from shared.config import settings
from shared.utils.logging_utils import get_logger
from database.database_manager import get_database_manager, DatabaseManager

logger = get_logger(__name__)
security = HTTPBearer()

# ===========================================
# ENUMS AND MODELS
# ===========================================

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"

class TimeInForce(str, Enum):
    DAY = "DAY"
    GTC = "GTC"  # Good Till Cancelled
    IOC = "IOC"  # Immediate or Cancel
    FOK = "FOK"  # Fill or Kill

class StrategyStatus(str, Enum):
    INACTIVE = "INACTIVE"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ERROR = "ERROR"

# ===========================================
# PYDANTIC MODELS
# ===========================================

class OrderRequest(BaseModel):
    """Order placement request"""
    symbol: str = Field(..., description="Trading symbol (e.g., AAPL, TSLA)")
    side: OrderSide = Field(..., description="Order side (BUY/SELL)")
    order_type: OrderType = Field(..., description="Order type")
    quantity: float = Field(..., gt=0, description="Order quantity")
    price: Optional[float] = Field(None, gt=0, description="Limit price (required for LIMIT orders)")
    stop_price: Optional[float] = Field(None, gt=0, description="Stop price (required for STOP orders)")
    time_in_force: TimeInForce = Field(TimeInForce.DAY, description="Time in force")
    account_id: str = Field(..., description="Trading account ID")
    strategy_id: Optional[str] = Field(None, description="Associated strategy ID")

class OrderResponse(BaseModel):
    """Order response model"""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float]
    stop_price: Optional[float]
    status: OrderStatus
    filled_quantity: float = 0.0
    avg_fill_price: Optional[float] = None
    time_in_force: TimeInForce
    created_at: datetime
    updated_at: datetime
    account_id: str
    strategy_id: Optional[str] = None

class PositionResponse(BaseModel):
    """Position response model"""
    symbol: str
    quantity: float
    avg_cost: float
    market_value: float
    unrealized_pnl: float
    realized_pnl: float
    last_updated: datetime
    account_id: str

class StrategyRequest(BaseModel):
    """Strategy creation/update request"""
    name: str = Field(..., description="Strategy name")
    description: Optional[str] = Field(None, description="Strategy description")
    strategy_type: str = Field(..., description="Strategy type (e.g., MovingAverageCrossover)")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Strategy parameters")
    symbols: List[str] = Field(..., description="Symbols to trade")
    account_id: str = Field(..., description="Trading account ID")
    risk_parameters: Dict[str, Any] = Field(default_factory=dict, description="Risk management parameters")

class StrategyResponse(BaseModel):
    """Strategy response model"""
    strategy_id: str
    name: str
    description: Optional[str]
    strategy_type: str
    parameters: Dict[str, Any]
    symbols: List[str]
    status: StrategyStatus
    account_id: str
    risk_parameters: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    performance_metrics: Dict[str, Any] = Field(default_factory=dict)

class RiskMetrics(BaseModel):
    """Risk metrics response"""
    account_id: str
    total_portfolio_value: float
    total_exposure: float
    available_buying_power: float
    margin_used: float
    day_pnl: float
    total_pnl: float
    max_drawdown: float
    sharpe_ratio: Optional[float] = None
    var_95: Optional[float] = None  # Value at Risk 95%
    calculated_at: datetime

# ===========================================
# CORE TRADING ENGINE
# ===========================================

class TradingEngine:
    """Core trading engine for order management and execution"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.active_orders: Dict[str, Dict] = {}
        self.active_strategies: Dict[str, Dict] = {}
        self.websocket_connections: List[WebSocket] = []
        
    async def place_order(self, order_request: OrderRequest, user_id: str) -> OrderResponse:
        """Place a new trading order"""
        try:
            # Generate order ID
            order_id = str(uuid.uuid4())
            
            # Validate order
            await self._validate_order(order_request, user_id)
            
            # Create order record
            order_data = {
                "id": order_id,
                "user_id": user_id,
                "account_id": order_request.account_id,
                "order_id": order_id,
                "symbol": order_request.symbol,
                "side": order_request.side.value,
                "order_type": order_request.order_type.value,
                "quantity": order_request.quantity,
                "price": order_request.price,
                "stop_price": order_request.stop_price,
                "status": OrderStatus.PENDING.value,
                "time_in_force": order_request.time_in_force.value,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "order_metadata": {
                    "strategy_id": order_request.strategy_id,
                    "source": "api"
                }
            }
            
            # Store in database
            async with self.db_manager.get_postgres_session() as session:
                # Insert order (simplified - would use SQLAlchemy ORM in production)
                query = """
                INSERT INTO orders (id, user_id, account_id, order_id, symbol, side, order_type, 
                                  quantity, price, stop_price, status, time_in_force, created_at, 
                                  updated_at, order_metadata)
                VALUES (%(id)s, %(user_id)s, %(account_id)s, %(order_id)s, %(symbol)s, %(side)s, 
                        %(order_type)s, %(quantity)s, %(price)s, %(stop_price)s, %(status)s, 
                        %(time_in_force)s, %(created_at)s, %(updated_at)s, %(order_metadata)s)
                """
                await session.execute(query, order_data)
                await session.commit()
            
            # Add to active orders
            self.active_orders[order_id] = order_data
            
            # Submit to broker (placeholder - would integrate with actual broker APIs)
            await self._submit_to_broker(order_data)
            
            # Notify via WebSocket
            await self._notify_order_update(order_data)
            
            return OrderResponse(
                order_id=order_id,
                symbol=order_request.symbol,
                side=order_request.side,
                order_type=order_request.order_type,
                quantity=order_request.quantity,
                price=order_request.price,
                stop_price=order_request.stop_price,
                status=OrderStatus.PENDING,
                time_in_force=order_request.time_in_force,
                created_at=order_data["created_at"],
                updated_at=order_data["updated_at"],
                account_id=order_request.account_id,
                strategy_id=order_request.strategy_id
            )
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to place order: {str(e)}")
    
    async def cancel_order(self, order_id: str, user_id: str) -> bool:
        """Cancel an existing order"""
        try:
            # Check if order exists and belongs to user
            if order_id not in self.active_orders:
                raise HTTPException(status_code=404, detail="Order not found")
            
            order = self.active_orders[order_id]
            if order["user_id"] != user_id:
                raise HTTPException(status_code=403, detail="Unauthorized")
            
            # Update order status
            order["status"] = OrderStatus.CANCELLED.value
            order["updated_at"] = datetime.utcnow()
            
            # Update in database
            async with self.db_manager.get_postgres_session() as session:
                query = """
                UPDATE orders SET status = %(status)s, updated_at = %(updated_at)s 
                WHERE order_id = %(order_id)s
                """
                await session.execute(query, {
                    "status": OrderStatus.CANCELLED.value,
                    "updated_at": datetime.utcnow(),
                    "order_id": order_id
                })
                await session.commit()
            
            # Cancel with broker (placeholder)
            await self._cancel_with_broker(order_id)
            
            # Remove from active orders
            del self.active_orders[order_id]
            
            # Notify via WebSocket
            await self._notify_order_update(order)
            
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to cancel order: {str(e)}")
    
    async def get_orders(self, user_id: str, account_id: Optional[str] = None, 
                        status: Optional[OrderStatus] = None) -> List[OrderResponse]:
        """Get orders for a user"""
        try:
            # Build query
            query = "SELECT * FROM orders WHERE user_id = %(user_id)s"
            params = {"user_id": user_id}
            
            if account_id:
                query += " AND account_id = %(account_id)s"
                params["account_id"] = account_id
            
            if status:
                query += " AND status = %(status)s"
                params["status"] = status.value
            
            query += " ORDER BY created_at DESC"
            
            # Execute query
            orders = await self.db_manager.execute_query(query, params)
            
            # Convert to response models
            return [
                OrderResponse(
                    order_id=order["order_id"],
                    symbol=order["symbol"],
                    side=OrderSide(order["side"]),
                    order_type=OrderType(order["order_type"]),
                    quantity=order["quantity"],
                    price=order["price"],
                    stop_price=order["stop_price"],
                    status=OrderStatus(order["status"]),
                    filled_quantity=order.get("filled_quantity", 0.0),
                    avg_fill_price=order.get("avg_fill_price"),
                    time_in_force=TimeInForce(order["time_in_force"]),
                    created_at=order["created_at"],
                    updated_at=order["updated_at"],
                    account_id=order["account_id"],
                    strategy_id=order.get("order_metadata", {}).get("strategy_id")
                )
                for order in orders
            ]
            
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get orders: {str(e)}")
    
    async def get_positions(self, user_id: str, account_id: str) -> List[PositionResponse]:
        """Get positions for an account"""
        try:
            query = """
            SELECT * FROM positions 
            WHERE user_id = %(user_id)s AND account_id = %(account_id)s
            """
            
            positions = await self.db_manager.execute_query(query, {
                "user_id": user_id,
                "account_id": account_id
            })
            
            return [
                PositionResponse(
                    symbol=pos["symbol"],
                    quantity=pos["quantity"],
                    avg_cost=pos["avg_cost"],
                    market_value=pos.get("market_value", 0.0),
                    unrealized_pnl=pos.get("unrealized_pnl", 0.0),
                    realized_pnl=pos.get("realized_pnl", 0.0),
                    last_updated=pos["last_updated"],
                    account_id=pos["account_id"]
                )
                for pos in positions
            ]
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get positions: {str(e)}")
    
    async def _validate_order(self, order_request: OrderRequest, user_id: str):
        """Validate order request"""
        # Check account ownership
        query = "SELECT id FROM trading_accounts WHERE id = %(account_id)s AND user_id = %(user_id)s"
        accounts = await self.db_manager.execute_query(query, {
            "account_id": order_request.account_id,
            "user_id": user_id
        })
        
        if not accounts:
            raise HTTPException(status_code=403, detail="Account not found or unauthorized")
        
        # Validate order parameters
        if order_request.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT] and not order_request.price:
            raise HTTPException(status_code=400, detail="Price required for limit orders")
        
        if order_request.order_type in [OrderType.STOP, OrderType.STOP_LIMIT] and not order_request.stop_price:
            raise HTTPException(status_code=400, detail="Stop price required for stop orders")
    
    async def _submit_to_broker(self, order_data: Dict):
        """Submit order to broker (placeholder)"""
        # This would integrate with actual broker APIs (Alpaca, IBKR, etc.)
        logger.info(f"Submitting order {order_data['order_id']} to broker")
        
        # Simulate order submission
        await asyncio.sleep(0.1)
        
        # Update order status to SUBMITTED
        order_data["status"] = OrderStatus.SUBMITTED.value
        order_data["updated_at"] = datetime.utcnow()
    
    async def _cancel_with_broker(self, order_id: str):
        """Cancel order with broker (placeholder)"""
        logger.info(f"Cancelling order {order_id} with broker")
        await asyncio.sleep(0.1)
    
    async def _notify_order_update(self, order_data: Dict):
        """Notify clients of order updates via WebSocket"""
        if self.websocket_connections:
            message = {
                "type": "order_update",
                "data": {
                    "order_id": order_data["order_id"],
                    "status": order_data["status"],
                    "updated_at": order_data["updated_at"].isoformat()
                }
            }
            
            # Send to all connected clients
            for websocket in self.websocket_connections.copy():
                try:
                    await websocket.send_json(message)
                except:
                    self.websocket_connections.remove(websocket)

# ===========================================
# FASTAPI APPLICATION
# ===========================================

# Global trading engine instance
trading_engine: Optional[TradingEngine] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global trading_engine
    
    # Startup
    logger.info("Starting Trading Engine Service...")
    
    # Initialize database manager
    db_manager = await get_database_manager()
    await db_manager.initialize()
    
    # Initialize trading engine
    trading_engine = TradingEngine(db_manager)
    
    logger.info("Trading Engine Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Trading Engine Service...")
    if db_manager:
        await db_manager.cleanup()
    logger.info("Trading Engine Service stopped")

# Create FastAPI app
app = FastAPI(
    title="Algorithmic Trading Engine",
    description="Core trading engine providing order management, strategy execution, and portfolio tracking",
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

# ===========================================
# AUTHENTICATION DEPENDENCY
# ===========================================

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Get current user from JWT token (placeholder)"""
    # This would validate JWT token and return user ID
    # For now, return a placeholder user ID
    return "user_123"

# ===========================================
# API ENDPOINTS
# ===========================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "trading-engine",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.post("/api/v1/orders", response_model=OrderResponse)
async def place_order(
    order_request: OrderRequest,
    user_id: str = Depends(get_current_user)
):
    """Place a new trading order"""
    return await trading_engine.place_order(order_request, user_id)

@app.delete("/api/v1/orders/{order_id}")
async def cancel_order(
    order_id: str,
    user_id: str = Depends(get_current_user)
):
    """Cancel an existing order"""
    success = await trading_engine.cancel_order(order_id, user_id)
    return {"success": success, "message": "Order cancelled successfully"}

@app.get("/api/v1/orders", response_model=List[OrderResponse])
async def get_orders(
    account_id: Optional[str] = Query(None),
    status: Optional[OrderStatus] = Query(None),
    user_id: str = Depends(get_current_user)
):
    """Get orders for the current user"""
    return await trading_engine.get_orders(user_id, account_id, status)

@app.get("/api/v1/positions", response_model=List[PositionResponse])
async def get_positions(
    account_id: str = Query(..., description="Trading account ID"),
    user_id: str = Depends(get_current_user)
):
    """Get positions for an account"""
    return await trading_engine.get_positions(user_id, account_id)

@app.websocket("/ws/orders")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time order updates"""
    await websocket.accept()
    trading_engine.websocket_connections.append(websocket)
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except:
        if websocket in trading_engine.websocket_connections:
            trading_engine.websocket_connections.remove(websocket)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Algorithmic Trading Engine",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "orders": "/api/v1/orders",
            "positions": "/api/v1/positions",
            "websocket": "/ws/orders",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8003,
        reload=True,
        log_level="info"
    )
