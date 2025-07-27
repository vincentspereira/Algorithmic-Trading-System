# nautilus_trader_engine/api/routers/trading.py

"""
API endpoints for handling trading operations such as placing, modifying, and canceling orders.
This router integrates with the TradingGateway to execute trades and manage order lifecycle.
"""

from fastapi import APIRouter, Depends, HTTPException
from nautilus_trader.model.enums import OrderSide, OrderType
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.objects import Price
from nautilus_trader_engine.services.trading_gateway import TradingGateway
from nautilus_trader_engine.services.risk_management_service import RiskManagementService

router = APIRouter()

# In a real application, you would use a dependency injection system
# to provide these services. For simplicity, we instantiate them here.
risk_management_service = RiskManagementService()
trading_gateway = TradingGateway(risk_management_service=risk_management_service)

@router.on_event("startup")
async def startup_event():
    """
    Connect to the trading gateway on application startup.
    """
    await trading_gateway.connect()

@router.on_event("shutdown")
async def shutdown_event():
    """
    Disconnect from the trading gateway on application shutdown.
    """
    await trading_gateway.disconnect()

@router.post("/orders/place", status_code=201)
async def place_order(
    instrument_id: str,
    side: OrderSide,
    quantity: float,
    price: float,
    order_type: OrderType,
):
    """
    Places a new trading order.

    Args:
        instrument_id (str): The ID of the instrument to trade (e.g., "EUR/USD.FX.IDEALPRO").
        side (OrderSide): 'BUY' or 'SELL'.
        quantity (float): The amount of the instrument to trade.
        price (float): The price at which to place the order.
        order_type (OrderType): The type of order (e.g., 'LIMIT').

    Returns:
        A confirmation message with the order details.
    """
    instrument = InstrumentId.from_str(instrument_id)
    order_price = Price(price)

    order_result = await trading_gateway.place_order(
        instrument_id=instrument,
        side=side,
        quantity=quantity,
        price=order_price,
        order_type=order_type,
    )

    if order_result:
        return {"message": "Order placed successfully", "order": order_result}
    else:
        raise HTTPException(status_code=400, detail="Order placement failed risk validation or other error.")

@router.post("/orders/cancel/{order_id}", status_code=200)
async def cancel_order(order_id: str):
    """
    Cancels an existing order.

    Args:
        order_id (str): The ID of the order to cancel.
    """
    await trading_gateway.cancel_order(order_id)
    return {"message": f"Cancellation request for order {order_id} sent."}

@router.get("/orders/status/{order_id}", status_code=200)
async def get_order_status(order_id: str):
    """
    Retrieves the status of a specific order.

    Args:
        order_id (str): The ID of the order to check.
    """
    status = await trading_gateway.get_order_status(order_id)
    return status

@router.get("/orders/updates", status_code=200)
async def get_trade_updates():
    """
    Retrieves all trade updates.
    """
    updates = await trading_gateway.get_trade_updates()
    return {"updates": updates}

@router.get("/orders/book/{instrument_id}", status_code=200)
async def get_order_book(instrument_id: str):
    """
    Retrieves the order book for a given instrument.

    Args:
        instrument_id (str): The ID of the instrument to check.
    """
    order_book = await trading_gateway.get_order_book(instrument_id)
    return {"instrument_id": instrument_id, "order_book": order_book}

@router.get("/positions", status_code=200)
async def get_positions():
    """
    Retrieves the current positions.
    """
    positions = await trading_gateway.get_positions()
    return {"positions": positions}

# Further endpoints for modifying orders would be added here.