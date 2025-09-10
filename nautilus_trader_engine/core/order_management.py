"""
Mock Order Manager for API Testing
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from nautilus_trader_engine.brokers.ibapi import IBClient
from nautilus_trader_engine.config.ib_config import IBPaperConfig, IBLiveConfig


class OrderType(Enum):
    """Order type enumeration"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"

class OrderManager:
    """Mock order manager for testing the API"""
    
    def __init__(self, use_ibkr: bool = False, ib_config: Optional[Any] = None):
        self.orders = {}
        self.positions = {}
        self.initialized = False
        self.use_ibkr = use_ibkr
        self.ib_client = None
        self.ib_config = ib_config
        
    async def initialize(self):
        """Initialize the order manager"""
        if self.use_ibkr:
            if self.ib_config is None:
                raise ValueError("IBKR configuration must be provided when use_ibkr is True")
            self.ib_client = IBClient(
                host=self.ib_config.HOST,
                port=self.ib_config.PORT,
                client_id=self.ib_config.CLIENT_ID,
                account_id=self.ib_config.ACCOUNT_ID
            )
            await self.ib_client.connect()
        self.initialized = True
        
    async def cleanup(self):
        """Cleanup resources"""
        self.initialized = False
        
    async def submit_order(
        self,
        symbol: str,
        order_type: str,
        side: str,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "DAY",
        user_id: str = "demo"
    ) -> Dict[str, Any]:
        """Submit a trading order"""
        order_id = str(uuid.uuid4())
        
        order = {
            "order_id": order_id,
            "symbol": symbol,
            "order_type": order_type,
            "side": side,
            "quantity": quantity,
            "price": price,
            "stop_price": stop_price,
            "time_in_force": time_in_force,
            "user_id": user_id,
            "status": "SUBMITTED",
            "created_at": datetime.now(),
            "filled_quantity": 0.0
        }
        
        self.orders[order_id] = order
        
        return {
            "success": True,
            "order_id": order_id,
            "status": "SUBMITTED",
            "message": f"Order {order_id} submitted successfully"
        }
    
    async def cancel_order(self, order_id: str, user_id: str) -> Dict[str, Any]:
        """Cancel an order"""
        if order_id in self.orders:
            order = self.orders[order_id]
            if order["user_id"] == user_id:
                order["status"] = "CANCELLED"
                return {"success": True, "message": f"Order {order_id} cancelled"}
        
        return {"success": False, "message": f"Order {order_id} not found"}
    
    async def get_orders(
        self,
        user_id: str,
        status: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get user orders"""
        user_orders = []
        for order in self.orders.values():
            if order["user_id"] == user_id:
                if status and order["status"] != status:
                    continue
                if symbol and order["symbol"] != symbol:
                    continue
                user_orders.append(order)
        
        return user_orders[:limit]
    
    async def get_positions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user positions"""
        # Mock positions
        return [
            {
                "symbol": "AAPL",
                "quantity": 100.0,
                "avg_cost": 150.0,
                "market_value": 15500.0,
                "unrealized_pnl": 500.0,
                "realized_pnl": 0.0,
                "last_updated": datetime.now()
            }
        ]
    
    async def get_portfolio_performance(
        self, 
        user_id: str, 
        period: str = "1d"
    ) -> Dict[str, Any]:
        """Get portfolio performance"""
        return {
            "period": period,
            "total_return": 0.05,
            "total_return_pct": 5.0,
            "total_value": 100000.0,
            "day_pnl": 500.0,
            "day_pnl_pct": 0.5
        }