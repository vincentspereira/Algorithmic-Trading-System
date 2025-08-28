"""
Order Management Service

Main entry point for the order management microservice.
Handles order lifecycle, execution, and settlement.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

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


# Initialize logger
logger = configure_trading_logger("order_management_service")

# Global service instances
order_manager: OrderManager = None
event_producer: OrderEventProducer = None
event_consumer: OrderEventConsumer = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global order_manager, event_producer, event_consumer
    
    try:
        logger.info("Starting Order Management Service...")
        
        # Load configuration
        config = OrderServiceConfig.from_env()
        
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
    description="Microservice for managing trading order lifecycle",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "order_management_service",
        "timestamp": asyncio.get_event_loop().time()
    }


# Order management endpoints
@app.post("/orders", response_model=OrderResponse)
async def place_order(order_request: OrderRequest):
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
async def get_order(order_id: str):
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
async def modify_order(order_id: str, modifications: Dict[str, Any]):
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
async def cancel_order(order_id: str):
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
async def get_user_orders(user_id: str, status: Optional[str] = None, limit: int = 100):
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
async def get_metrics():
    """
    Get service metrics
    
    Returns:
        Service performance metrics
    """
    try:
        metrics = await order_manager.get_metrics()
        return metrics
        
    except Exception as e:
        logger.error(f"Error retrieving metrics: {e}")
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