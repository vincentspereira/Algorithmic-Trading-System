"""
Trading API Router for Nautilus Trader Engine

This module provides API endpoints for trading functionality including
order management, account information, and trading mode switching.

Author: Vincent S. Pereira
Version: 1.0.0
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging

from nautilus_trader.model.orders import MarketOrder, LimitOrder
from nautilus_trader.model.identifiers import InstrumentId, VenueOrderId
from nautilus_trader.model.objects import Quantity, Price

from nautilus_trader_engine.adapters.ibkr_adapter import (
    get_ibkr_adapter, 
    initialize_ibkr_adapter
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/trading", tags=["trading"])


class OrderRequest(BaseModel):
    """Request model for submitting orders."""
    instrument_id: str
    order_type: str  # "market" or "limit"
    quantity: float
    price: Optional[float] = None
    side: str  # "buy" or "sell"
    
    
class OrderResponse(BaseModel):
    """Response model for order submissions."""
    venue_order_id: str
    status: str
    message: str


class AccountInfoResponse(BaseModel):
    """Response model for account information."""
    account_id: str
    balance: float
    available_funds: float
    equity: float
    currency: str
    mode: str


class TradingModeRequest(BaseModel):
    """Request model for switching trading modes."""
    paper_trading: bool


@router.post("/orders", response_model=OrderResponse)
async def submit_order(order_request: OrderRequest):
    """
    Submit an order to the trading system.
    
    Args:
        order_request: Order details
        
    Returns:
        OrderResponse: Order submission result
    """
    try:
        # Get the IBKR adapter
        adapter = get_ibkr_adapter()
        
        if not adapter.is_connected():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not connected to trading system"
            )
        
        # Create instrument ID
        instrument_id = InstrumentId.from_str(order_request.instrument_id)
        
        # Create order based on type
        if order_request.order_type == "market":
            order = MarketOrder(
                trader_id="TRADER_001",
                strategy_id="STRATEGY_001",
                instrument_id=instrument_id,
                order_side=order_request.side.upper(),
                quantity=Quantity.from_str(str(order_request.quantity)),
            )
        elif order_request.order_type == "limit":
            if order_request.price is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Price is required for limit orders"
                )
            order = LimitOrder(
                trader_id="TRADER_001",
                strategy_id="STRATEGY_001",
                instrument_id=instrument_id,
                order_side=order_request.side.upper(),
                quantity=Quantity.from_str(str(order_request.quantity)),
                price=Price.from_str(str(order_request.price)),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported order type: {order_request.order_type}"
            )
        
        # Submit order
        venue_order_id = await adapter.submit_order(order, instrument_id)
        
        return OrderResponse(
            venue_order_id=venue_order_id.value,
            status="submitted",
            message=f"Order {venue_order_id.value} submitted successfully"
        )
        
    except Exception as e:
        logger.error(f"Error submitting order: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error submitting order: {str(e)}"
        )


@router.get("/account", response_model=AccountInfoResponse)
async def get_account_info():
    """
    Get account information.
    
    Returns:
        AccountInfoResponse: Account information
    """
    try:
        # Get the IBKR adapter
        adapter = get_ibkr_adapter()
        
        if not adapter.is_connected():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not connected to trading system"
            )
        
        # Get account info
        account_info = await adapter.get_account_info()
        
        return AccountInfoResponse(**account_info)
        
    except Exception as e:
        logger.error(f"Error getting account info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting account info: {str(e)}"
        )


@router.post("/connect")
async def connect_to_trading_system(paper_trading: bool = True):
    """
    Connect to the trading system (IBKR).
    
    Args:
        paper_trading: Whether to use paper trading mode (default: True)
        
    Returns:
        Dict: Connection status
    """
    try:
        # Get the IBKR adapter
        adapter = get_ibkr_adapter()
        
        # Connect to IBKR
        success = await adapter.connect()
        
        if success:
            return {
                "status": "connected",
                "message": f"Successfully connected to {'paper' if paper_trading else 'live'} trading system",
                "paper_trading": paper_trading
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to connect to trading system"
            )
            
    except Exception as e:
        logger.error(f"Error connecting to trading system: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error connecting to trading system: {str(e)}"
        )


@router.post("/disconnect")
async def disconnect_from_trading_system():
    """
    Disconnect from the trading system.
    
    Returns:
        Dict: Disconnection status
    """
    try:
        # Get the IBKR adapter
        adapter = get_ibkr_adapter()
        
        # Disconnect from IBKR
        await adapter.disconnect()
        
        return {
            "status": "disconnected",
            "message": "Successfully disconnected from trading system"
        }
        
    except Exception as e:
        logger.error(f"Error disconnecting from trading system: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error disconnecting from trading system: {str(e)}"
        )


@router.post("/mode")
async def switch_trading_mode(mode_request: TradingModeRequest):
    """
    Switch between paper and live trading modes.
    
    Args:
        mode_request: Trading mode request
        
    Returns:
        Dict: Mode switch status
    """
    try:
        # Get the IBKR adapter
        adapter = get_ibkr_adapter()
        
        # Switch trading mode
        success = adapter.switch_trading_mode(mode_request.paper_trading)
        
        if success:
            return {
                "status": "mode_switched",
                "message": f"Trading mode switched to {'paper' if mode_request.paper_trading else 'live'}",
                "paper_trading": mode_request.paper_trading
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to switch trading mode. Disconnect first if currently connected."
            )
            
    except Exception as e:
        logger.error(f"Error switching trading mode: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error switching trading mode: {str(e)}"
        )


@router.get("/orders/{venue_order_id}/status")
async def get_order_status(venue_order_id: str):
    """
    Get the status of an order.
    
    Args:
        venue_order_id: The order ID assigned by the venue
        
    Returns:
        Dict: Order status
    """
    try:
        # Get the IBKR adapter
        adapter = get_ibkr_adapter()
        
        if not adapter.is_connected():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not connected to trading system"
            )
        
        # Get order status
        status = await adapter.get_order_status(VenueOrderId(venue_order_id))
        
        return {
            "venue_order_id": venue_order_id,
            "status": status
        }
        
    except Exception as e:
        logger.error(f"Error getting order status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting order status: {str(e)}"
        )