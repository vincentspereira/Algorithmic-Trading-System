import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Dict, Any

from nautilus_trader.model.enums import OrderSide, OrderType, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId, ClientOrderId
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.model.orders.market import MarketOrder
from nautilus_trader.model.orders.limit import LimitOrder

from nautilus_trader_engine.services.trading_gateway import TradingGateway
from nautilus_trader_engine.services.risk_management_service import RiskManagementService
from nautilus_trader_engine.config.ib_config import get_ib_config

router = APIRouter()

# Dependency to get TradingGateway instance
async def get_trading_gateway():
    loop = asyncio.get_event_loop()
    ib_config = get_ib_config()
    risk_service = RiskManagementService()
    gateway = TradingGateway(loop=loop, risk_management_service=risk_service, config=ib_config)
    await gateway.connect()
    try:
        yield gateway
    finally:
        await gateway.disconnect()

class PlaceOrderRequest(BaseModel):
    instrument_id: str
    order_side: OrderSide
    quantity: float
    order_type: OrderType
    price: Optional[float] = None
    client_order_id: Optional[str] = None
    time_in_force: Optional[TimeInForce] = TimeInForce.DAY

class OrderResponse(BaseModel):
    client_order_id: str
    status: str
    ib_order_id: Optional[int] = None
    message: Optional[str] = None

class CancelOrderResponse(BaseModel):
    client_order_id: str
    success: bool
    message: Optional[str] = None

class OrderStatusResponse(BaseModel):
    client_order_id: str
    status: str
    ib_order_id: Optional[int] = None

class PortfolioResponse(BaseModel):
    account_values: Dict[str, Any]
    positions: list

@router.post("/orders/place", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def place_order(request: PlaceOrderRequest, gateway: TradingGateway = Depends(get_trading_gateway)):
    instrument_id = InstrumentId.from_str(request.instrument_id)
    quantity = Quantity(request.quantity)
    client_order_id = ClientOrderId(request.client_order_id) if request.client_order_id else ClientOrderId.random()

    if request.order_type == OrderType.MARKET:
        order = MarketOrder(
            instrument_id=instrument_id,
            order_side=request.order_side,
            quantity=quantity,
            client_order_id=client_order_id,
            time_in_force=request.time_in_force
        )
    elif request.order_type == OrderType.LIMIT:
        if request.price is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Limit orders require a price.")
        order = LimitOrder(
            instrument_id=instrument_id,
            order_side=request.order_side,
            quantity=quantity,
            price=Price(request.price),
            client_order_id=client_order_id,
            time_in_force=request.time_in_force
        )
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Order type {request.order_type} not supported.")

    trade = await gateway.place_order(order)
    if trade:
        return OrderResponse(
            client_order_id=str(client_order_id),
            status="PENDING",
            ib_order_id=trade.order.orderId,
            message="Order placed successfully."
        )
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to place order.")

@router.post("/orders/cancel", response_model=CancelOrderResponse)
async def cancel_order(client_order_id: str, gateway: TradingGateway = Depends(get_trading_gateway)):
    success = await gateway.cancel_order(client_order_id)
    if success:
        return CancelOrderResponse(client_order_id=client_order_id, success=True, message="Order cancellation requested.")
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to cancel order.")

@router.get("/orders/status/{client_order_id}", response_model=OrderStatusResponse)
async def get_order_status(client_order_id: str, gateway: TradingGateway = Depends(get_trading_gateway)):
    status_info = await gateway.get_order_status(client_order_id)
    if status_info:
        return OrderStatusResponse(
            client_order_id=status_info["client_order_id"],
            status=status_info["status"],
            ib_order_id=status_info["ib_order_id"]
        )
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found or status unavailable.")

@router.get("/portfolio", response_model=PortfolioResponse)
async def get_portfolio(gateway: TradingGateway = Depends(get_trading_gateway)):
    portfolio = await gateway.get_portfolio()
    if portfolio:
        return PortfolioResponse(
            account_values=portfolio.get("account_values", {}),
            positions=portfolio.get("positions", [])
        )
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve portfolio.")