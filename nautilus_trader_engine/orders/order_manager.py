"""Order Manager for Multi-Asset Trading
Handles order submission, execution, and management across different asset classes.
"""

import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class OrderResult:
    """Result of order execution."""
    order_id: str
    symbol: str
    status: str
    fill_price: float
    fill_quantity: float
    timestamp: str
    commission: float
    error_message: Optional[str] = None


class MultiAssetOrderManager:
    """Manages orders across multiple asset classes."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the order manager.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.orders: Dict[str, OrderResult] = {}
        
    async def submit_order(self, order: Dict[str, Any]) -> OrderResult:
        """Submit an order for execution.
        
        Args:
            order: Order details dictionary
            
        Returns:
            OrderResult with execution details
        """
        try:
            # Generate order ID
            order_id = f"ORD_{len(self.orders) + 1:06d}"
            
            # For testing purposes, we'll return a mock result
            # In a real implementation, this would connect to actual trading venues
            result = OrderResult(
                order_id=order_id,
                symbol=order.get('symbol', ''),
                status='FILLED',
                fill_price=self._get_mock_fill_price(order),
                fill_quantity=order.get('quantity', 0),
                timestamp=datetime.now(timezone.utc).isoformat(),
                commission=self._calculate_mock_commission(order)
            )
            
            # Store the order result
            self.orders[order_id] = result
            
            return result
            
        except Exception as e:
            return OrderResult(
                order_id=f"ORD_ERR_{len(self.orders) + 1:06d}",
                symbol=order.get('symbol', ''),
                status='REJECTED',
                fill_price=0.0,
                fill_quantity=0.0,
                timestamp=datetime.now(timezone.utc).isoformat(),
                commission=0.0,
                error_message=str(e)
            )
    
    def _get_mock_fill_price(self, order: Dict[str, Any]) -> float:
        """Generate mock fill price based on order details."""
        # Make sure prices are aligned with their respective tick sizes
        mock_prices = {
            'EURUSD': 1.08650,  # Aligned to 0.00001 tick size
            'AAPL': 175.25,     # Aligned to 0.01 tick size
            'BTCUSD': 45250.00  # Aligned to 0.01 tick size
        }
        price = mock_prices.get(order['symbol'], 100.0)
        
        # Align price to tick size to avoid floating point precision issues
        asset_class = order.get('asset_class', 'forex')
        tick_sizes = {
            'forex': 0.00001,
            'stocks': 0.01,
            'commodities': 0.01,
            'crypto': 0.01,
            'indices': 0.1
        }
        tick_size = tick_sizes.get(asset_class, 0.00001)
        
        # Round to nearest tick
        aligned_price = round(price / tick_size) * tick_size
        return aligned_price
    
    def _calculate_mock_commission(self, order: Dict[str, Any]) -> float:
        """Calculate mock commission based on asset class."""
        commission_rates = {
            'forex': 0.0,  # Spread-based
            'stocks': 0.005,  # $0.005 per share
            'crypto': 0.001,  # 0.1% of notional
            'commodities': 2.50,  # Fixed per contract
            'indices': 1.00  # Fixed per contract
        }
        
        asset_class = order['asset_class']
        rate = commission_rates.get(asset_class, 0.0)
        
        if asset_class == 'stocks':
            return order['quantity'] * rate
        elif asset_class == 'crypto':
            notional = order['quantity'] * self._get_mock_fill_price(order)
            return notional * rate
        else:
            return rate


class OrderManager:
    """Simple order manager for single asset class trading."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the order manager.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.multi_asset_manager = MultiAssetOrderManager(config)
        
    async def submit_order(self, order: Dict[str, Any]) -> OrderResult:
        """Submit an order for execution.
        
        Args:
            order: Order details dictionary
            
        Returns:
            OrderResult with execution details
        """
        return await self.multi_asset_manager.submit_order(order)