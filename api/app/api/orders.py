
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from api.app.models import APIResponse, OrderRequest
from api.app.websockets import ConnectionManager
from nautilus_trader_engine.core.order_management import OrderManager
from app.core.security import verify_token
from app.services.kafka_service import KafkaService

router = APIRouter()
order_manager = OrderManager()
connection_manager = ConnectionManager()
kafka_service = KafkaService()

@router.post("/orders", response_model=APIResponse)
async def submit_order(
    request: OrderRequest,
    user: dict = Depends(verify_token)
):
    """Submit a new trading order by sending it to Kafka for processing"""
    try:
        # Check user permissions
        if "trade" not in user.get("permissions", []):
            raise HTTPException(status_code=403, detail="Trading permission required")

        # Prepare the order event for Kafka
        order_event = request.dict()
        order_event["user_id"] = user["user_id"]
        order_event["timestamp"] = datetime.now(timezone.utc).isoformat()
        order_event["request_id"] = str(uuid4()) # Add a unique request ID for traceability

        # Send the order request to a Kafka topic for asynchronous processing
        await kafka_service.send_message('order_requests', order_event)

        return APIResponse(
            success=True,
            data={"request_id": order_event["request_id"]},
            message="Order request sent to Kafka for asynchronous processing."
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send order request to Kafka: {str(e)}")

@router.get("/orders")
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
        raise HTTPException(status_code=500, detail=f"Failed to retrieve orders: {str(e)}")

@router.delete("/orders/{order_id}")
async def cancel_order(order_id: str, user: dict = Depends(verify_token)):
    """Cancel an existing order"""
    try:
        result = await order_manager.cancel_order(order_id, user["user_id"])

        # Broadcast cancellation via WebSocket
        await connection_manager.broadcast_all({
            "type": "order_cancelled",
            "data": {"order_id": order_id, "result": result},
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return APIResponse(
            success=result["success"],
            data=result,
            message=f"Order {order_id} {'cancelled' if result['success'] else 'cancellation failed'}"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Order cancellation failed: {str(e)}")
