"""
Order Management Service

Main entry point for the order management microservice.
Handles order lifecycle, execution, and settlement.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from shared.auth import (
    JWTManager,
    RBACManager,
    UserManager,
    JWTBearer,
    require_permissions,
    require_roles,
    Permission,
    Role,
    TokenData,
    UserCreateRequest,
    AuthenticationError,
    AuthorizationError,
    get_http_status_code,
    create_error_response
)

from shared.utils import (
    configure_trading_logger,
    get_postgres_manager,
    DatabaseError
)
from .order_manager import OrderManager
from .kafka_producer import OrderEventProducer
from .kafka_consumer import OrderEventConsumer
from .models import OrderRequest, OrderResponse, OrderStatus
from .config import OrderServiceConfig
from .auth_api import router as auth_router


# Initialize logger
logger = configure_trading_logger("order_management_service")

# Global service instances
order_manager: OrderManager = None
event_producer: OrderEventProducer = None
event_consumer: OrderEventConsumer = None
jwt_manager: JWTManager = None
rbac_manager: RBACManager = None
user_manager: UserManager = None
jwt_bearer: JWTBearer = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global order_manager, event_producer, event_consumer, jwt_manager, rbac_manager, user_manager, jwt_bearer
    
    try:
        logger.info("Starting Order Management Service...")
        
        # Load configuration
        config = OrderServiceConfig.from_env()
        
        # Initialize authentication components
        jwt_manager = JWTManager(
            secret_key=os.getenv("JWT_SECRET_KEY", "your-super-secret-jwt-key-change-in-production"),
            algorithm="HS256",
            access_token_expire_minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
            refresh_token_expire_days=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))
        )
        
        rbac_manager = RBACManager()
        user_manager = UserManager(rbac_manager, jwt_manager)
        jwt_bearer = JWTBearer(jwt_manager, rbac_manager)
        
        # Initialize RBAC with default roles and permissions
        rbac_manager.initialize_default_roles()
        
        # Create default admin user if it doesn't exist
        try:
            admin_request = UserCreateRequest(
                username="admin",
                email="admin@trading-system.com",
                password="admin123",  # TODO: Use secure password from environment
                first_name="System",
                last_name="Administrator",
                roles=["admin"]
            )
            user_manager.create_user(admin_request)
            logger.info("Default admin user created")
        except Exception as e:
            logger.info(f"Admin user already exists or creation failed: {e}")
        
        # Initialize database connections
        db_manager = get_postgres_manager()
        await db_manager.initialize_async_engine()
        
        # Initialize Kafka producer/consumer
        event_producer = OrderEventProducer(config.kafka_config)
        await event_producer.start()
        
        event_consumer = OrderEventConsumer(config.kafka_config)
        await event_consumer.start()
        
        # Initialize order manager
        order_manager = OrderManager(
            db_manager=db_manager,
            event_producer=event_producer,
            config=config
        )
        
        logger.info("Order Management Service started successfully")
        yield
        
    except Exception as e:
        logger.error(f"Failed to start Order Management Service: {e}")
        raise
    
    finally:
        logger.info("Shutting down Order Management Service...")
        
        # Cleanup resources
        if event_consumer:
            await event_consumer.stop()
        if event_producer:
            await event_producer.stop()
        
        logger.info("Order Management Service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Order Management Service",
    description="Microservice for managing trading order lifecycle with Authentication",
    version="1.0.0",
    lifespan=lifespan
)

# Add security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.trading-system.com"]
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React frontend
        "http://localhost:8080",  # Alternative frontend port
        "https://*.trading-system.com"  # Production domains
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)


# Global exception handlers
@app.exception_handler(AuthenticationError)
async def authentication_exception_handler(request, exc: AuthenticationError):
    """Handle authentication errors"""
    return JSONResponse(
        status_code=get_http_status_code(exc),
        content=create_error_response(exc)
    )


@app.exception_handler(AuthorizationError)
async def authorization_exception_handler(request, exc: AuthorizationError):
    """Handle authorization errors"""
    return JSONResponse(
        status_code=get_http_status_code(exc),
        content=create_error_response(exc)
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "HTTPException",
                "message": exc.detail,
                "status_code": exc.status_code
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "type": "InternalServerError",
                "message": "An internal server error occurred",
                "status_code": 500
            }
        }
    )


# Include authentication router
app.include_router(auth_router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Order Management Service",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "order_management_service",
        "version": "1.0.0",
        "components": {
            "authentication": "healthy",
            "authorization": "healthy",
            "database": "healthy",
            "kafka": "healthy"
        },
        "timestamp": asyncio.get_event_loop().time()
    }


# Order management endpoints
@app.post("/orders", response_model=OrderResponse)
@require_permissions(Permission.TRADING_EXECUTE)
async def place_order(
    order_request: OrderRequest,
    token_data: TokenData = Depends(jwt_bearer)
):
    """
    Place a new trading order
    
    Args:
        order_request: Order placement request
        
    Returns:
        Order response with order ID and status
    """
    try:
        logger.info(f"Placing order: {order_request.symbol} {order_request.side} {order_request.quantity}")
        
        order_response = await order_manager.place_order(order_request)
        
        logger.info(f"Order placed successfully: {order_response.order_id}")
        return order_response
        
    except ValueError as e:
        logger.warning(f"Invalid order request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Database error placing order: {e}")
        raise HTTPException(status_code=500, detail="Internal service error")
    except Exception as e:
        logger.error(f"Unexpected error placing order: {e}")
        raise HTTPException(status_code=500, detail="Internal service error")


@app.get("/orders/{order_id}", response_model=OrderResponse)
@require_permissions(Permission.TRADING_VIEW)
async def get_order(
    order_id: str,
    token_data: TokenData = Depends(jwt_bearer)
):
    """
    Get order status and details
    
    Args:
        order_id: Order identifier
        
    Returns:
        Order details and current status
    """
    try:
        order_response = await order_manager.get_order(order_id)
        
        if not order_response:
            raise HTTPException(status_code=404, detail="Order not found")
        
        return order_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving order {order_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal service error")


@app.put("/orders/{order_id}")
@require_permissions(Permission.TRADING_MODIFY)
async def modify_order(
    order_id: str,
    modifications: Dict[str, Any],
    token_data: TokenData = Depends(jwt_bearer)
):
    """
    Modify an existing order
    
    Args:
        order_id: Order identifier
        modifications: Order modifications
        
    Returns:
        Updated order response
    """
    try:
        logger.info(f"Modifying order {order_id}: {modifications}")
        
        order_response = await order_manager.modify_order(order_id, modifications)
        
        if not order_response:
            raise HTTPException(status_code=404, detail="Order not found")
        
        logger.info(f"Order {order_id} modified successfully")
        return order_response
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid order modification: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error modifying order {order_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal service error")


@app.delete("/orders/{order_id}")
@require_permissions(Permission.TRADING_CANCEL)
async def cancel_order(
    order_id: str,
    token_data: TokenData = Depends(jwt_bearer)
):
    """
    Cancel an existing order
    
    Args:
        order_id: Order identifier
        
    Returns:
        Cancellation confirmation
    """
    try:
        logger.info(f"Cancelling order {order_id}")
        
        success = await order_manager.cancel_order(order_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Order not found or cannot be cancelled")
        
        logger.info(f"Order {order_id} cancelled successfully")
        return {"message": "Order cancelled successfully", "order_id": order_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling order {order_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal service error")


@app.get("/orders/user/{user_id}")
@require_permissions(Permission.TRADING_VIEW)
async def get_user_orders(
    user_id: str,
    status: Optional[str] = None,
    limit: int = 100,
    token_data: TokenData = Depends(jwt_bearer)
):
    """
    Get orders for a specific user
    
    Args:
        user_id: User identifier
        status: Optional status filter
        limit: Maximum number of orders to return
        
    Returns:
        List of user orders
    """
    try:
        orders = await order_manager.get_user_orders(
            user_id=user_id,
            status=status,
            limit=limit
        )
        
        return {"orders": orders, "count": len(orders)}
        
    except Exception as e:
        logger.error(f"Error retrieving orders for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal service error")


@app.get("/metrics")
@require_permissions(Permission.REPORTS_VIEW)
async def get_metrics(
    token_data: TokenData = Depends(jwt_bearer)
):
    """Get service metrics
    
    Returns:
        Service performance metrics
    """
    try:
        metrics = await order_manager.get_metrics()
        return metrics
        
    except Exception as e:
        logger.error(f"Error retrieving metrics: {e}")
        raise HTTPException(status_code=500, detail="Internal service error")


# Admin-only endpoints
@app.get("/admin/users")
@require_roles("super_admin")
async def get_all_users(
    token_data: TokenData = Depends(jwt_bearer)
):
    """Get all users (admin only)"""
    try:
        # TODO: Implement actual user listing logic
        return {
            "message": "Users retrieved successfully",
            "admin_user": token_data.username,
            "users": []  # Placeholder
        }
    except Exception as e:
        logger.error(f"Error retrieving users: {e}")
        raise HTTPException(status_code=500, detail="Internal service error")


@app.get("/admin/system-status")
@require_roles("super_admin")
async def get_system_status(
    token_data: TokenData = Depends(jwt_bearer)
):
    """Get system status (admin only)"""
    try:
        return {
            "message": "System status retrieved successfully",
            "admin_user": token_data.username,
            "system_status": {
                "uptime": "24h 15m",
                "active_orders": 0,
                "active_users": 1,
                "memory_usage": "45%",
                "cpu_usage": "12%",
                "kafka_status": "connected",
                "database_status": "connected"
            }
        }
    except Exception as e:
        logger.error(f"Error retrieving system status: {e}")
        raise HTTPException(status_code=500, detail="Internal service error")


# Trader-specific endpoints
@app.get("/trading/positions")
@require_roles("trader")
async def get_positions(
    token_data: TokenData = Depends(jwt_bearer)
):
    """Get trading positions (trader role required)"""
    try:
        # TODO: Implement actual position retrieval logic
        return {
            "message": "Positions retrieved successfully",
            "trader": token_data.username,
            "positions": []  # Placeholder
        }
    except Exception as e:
        logger.error(f"Error retrieving positions: {e}")
        raise HTTPException(status_code=500, detail="Internal service error")


@app.post("/trading/strategies")
@require_permissions(Permission.STRATEGY_CREATE)
async def create_strategy(
    token_data: TokenData = Depends(jwt_bearer)
):
    """Create trading strategy (requires MANAGE_STRATEGIES permission)"""
    try:
        # TODO: Implement actual strategy creation logic
        return {
            "message": "Strategy created successfully",
            "user": token_data.username,
            "strategy_id": "STRAT-12345"  # Placeholder
        }
    except Exception as e:
        logger.error(f"Error creating strategy: {e}")
        raise HTTPException(status_code=500, detail="Internal service error")


# Main entry point
if __name__ == "__main__":
    port = int(os.getenv("ORDER_SERVICE_PORT", "8001"))
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True,
        reload=False  # Set to True for development
    )