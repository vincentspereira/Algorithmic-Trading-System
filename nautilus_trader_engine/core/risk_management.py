"""
Mock Risk Manager for API Testing
"""

import asyncio
from typing import Dict, Optional, Any

class RiskManager:
    """Mock risk manager for testing the API"""
    
    def __init__(self):
        self.initialized = False
        self.max_position_size = 10000
        self.max_order_value = 50000
        
    async def initialize(self):
        """Initialize the risk manager"""
        self.initialized = True
        
    async def cleanup(self):
        """Cleanup resources"""
        self.initialized = False
        
    async def validate_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: Optional[float] = None,
        user_id: str = "demo"
    ) -> Dict[str, Any]:
        """Validate if an order meets risk requirements"""
        
        # Simple risk checks
        if quantity > self.max_position_size:
            return {
                "approved": False,
                "reason": f"Quantity {quantity} exceeds max position size {self.max_position_size}"
            }
        
        if price and (quantity * price) > self.max_order_value:
            return {
                "approved": False,
                "reason": f"Order value exceeds maximum allowed value {self.max_order_value}"
            }
        
        # Approve order
        return {
            "approved": True,
            "reason": "Order approved by risk management"
        }