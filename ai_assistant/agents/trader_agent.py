"""
Trader Agent for Trade Execution and Order Management

This agent specializes in trade execution, order management, and interfacing
with broker APIs to execute trading decisions.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from enum import Enum

from ..utils.agent_utils import AgentBase, AgentMessage, AgentResponse
from shared.utils import format_currency, get_logger


logger = get_logger(__name__)


class OrderType(Enum):
    """Order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    """Order sides"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """Order status"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class TraderAgent(AgentBase):
    """
    Trader Agent for trade execution and order management
    
    Capabilities:
    - Order placement and management
    - Trade execution monitoring
    - Broker API integration
    - Order routing and optimization
    - Fill reporting and reconciliation
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Trader Agent
        
        Args:
            config: Agent configuration
        """
        super().__init__(name="trader", config=config)
        
        # Trading configuration
        self.broker_config = config.get("broker", {}) if config else {}
        self.paper_trading = config.get("paper_trading", True) if config else True
        self.max_retry_attempts = config.get("max_retry_attempts", 3) if config else 3
        
        # Order tracking
        self._active_orders = {}
        self._completed_orders = {}
        
        logger.info(f"Trader Agent initialized (paper_trading: {self.paper_trading})")
    
    async def execute_trade(
        self,
        symbol: str,
        trade_decision: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute trade based on trade decision
        
        Args:
            symbol: Trading symbol
            trade_decision: Trade decision from workflow
            
        Returns:
            Trade execution result
        """
        logger.info(f"Executing trade for {symbol}: {trade_decision.get('action')}")
        
        try:
            # Validate trade decision
            validation_result = self._validate_trade_decision(symbol, trade_decision)
            if not validation_result["valid"]:
                return {
                    "status": "rejected",
                    "reason": validation_result["reason"],
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            # Create order from trade decision
            order = self._create_order_from_decision(symbol, trade_decision)
            
            # Execute order
            execution_result = await self._execute_order(order)
            
            # Set up monitoring for fills
            if execution_result["status"] in ["submitted", "partially_filled"]:
                asyncio.create_task(self._monitor_order_fills(order["order_id"]))
            
            logger.info(f"Trade execution completed for {symbol}: {execution_result['status']}")
            
            return execution_result
        
        except Exception as e:
            logger.error(f"Trade execution failed for {symbol}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel an active order
        
        Args:
            order_id: Order identifier
            
        Returns:
            Cancellation result
        """
        logger.info(f"Cancelling order {order_id}")
        
        try:
            if order_id not in self._active_orders:
                return {
                    "status": "error",
                    "reason": "Order not found or not active",
                    "order_id": order_id
                }
            
            order = self._active_orders[order_id]
            
            # Send cancellation request to broker
            cancel_result = await self._send_cancel_request(order)
            
            if cancel_result["success"]:
                order["status"] = OrderStatus.CANCELLED
                order["cancelled_time"] = datetime.now(timezone.utc)
                
                # Move to completed orders
                self._completed_orders[order_id] = order
                del self._active_orders[order_id]
                
                logger.info(f"Order {order_id} cancelled successfully")
                
                return {
                    "status": "cancelled",
                    "order_id": order_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            else:
                logger.error(f"Failed to cancel order {order_id}: {cancel_result.get('reason')}")
                return {
                    "status": "error",
                    "reason": cancel_result.get("reason"),
                    "order_id": order_id
                }
        
        except Exception as e:
            logger.error(f"Order cancellation failed for {order_id}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "order_id": order_id
            }
    
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Get current order status
        
        Args:
            order_id: Order identifier
            
        Returns:
            Order status information
        """
        # Check active orders first
        if order_id in self._active_orders:
            order = self._active_orders[order_id]
            # Refresh status from broker
            await self._refresh_order_status(order)
            return self._format_order_status(order)
        
        # Check completed orders
        if order_id in self._completed_orders:
            order = self._completed_orders[order_id]
            return self._format_order_status(order)
        
        return {
            "status": "not_found",
            "order_id": order_id,
            "message": "Order not found"
        }
    
    async def get_portfolio_positions(self) -> Dict[str, Any]:
        """
        Get current portfolio positions
        
        Returns:
            Portfolio positions
        """
        try:
            # In real implementation, this would query the broker API
            # For now, return mock positions
            
            positions = await self._fetch_positions_from_broker()
            
            return {
                "status": "success",
                "positions": positions,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        except Exception as e:
            logger.error(f"Failed to fetch portfolio positions: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def _validate_trade_decision(
        self,
        symbol: str,
        trade_decision: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate trade decision parameters
        
        Args:
            symbol: Trading symbol
            trade_decision: Trade decision to validate
            
        Returns:
            Validation result
        """
        errors = []
        
        # Check required fields
        required_fields = ["action", "quantity"]
        for field in required_fields:
            if field not in trade_decision:
                errors.append(f"Missing required field: {field}")
        
        # Validate action
        valid_actions = ["BUY", "SELL"]
        if trade_decision.get("action") not in valid_actions:
            errors.append(f"Invalid action: {trade_decision.get('action')}")
        
        # Validate quantity
        quantity = trade_decision.get("quantity", 0)
        if not isinstance(quantity, (int, float)) or quantity <= 0:
            errors.append("Quantity must be a positive number")
        
        # Validate order type
        order_type = trade_decision.get("order_type", "MARKET")
        if order_type not in [ot.value.upper() for ot in OrderType]:
            errors.append(f"Invalid order type: {order_type}")
        
        # Validate limit price for limit orders
        if order_type == "LIMIT" and "limit_price" not in trade_decision:
            errors.append("Limit price required for limit orders")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "reason": "; ".join(errors) if errors else None
        }
    
    def _create_order_from_decision(
        self,
        symbol: str,
        trade_decision: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create order from trade decision
        
        Args:
            symbol: Trading symbol
            trade_decision: Trade decision
            
        Returns:
            Order object
        """
        order_id = str(uuid.uuid4())
        
        order = {
            "order_id": order_id,
            "symbol": symbol,
            "action": trade_decision["action"],
            "quantity": trade_decision["quantity"],
            "order_type": trade_decision.get("order_type", "MARKET"),
            "limit_price": trade_decision.get("limit_price"),
            "stop_price": trade_decision.get("stop_price"),
            "time_in_force": trade_decision.get("time_in_force", "DAY"),
            "status": OrderStatus.PENDING,
            "created_time": datetime.now(timezone.utc),
            "filled_quantity": 0,
            "average_fill_price": 0,
            "fills": [],
            "stop_loss": trade_decision.get("stop_loss"),
            "take_profit": trade_decision.get("take_profit")
        }
        
        return order
    
    async def _execute_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute order with broker
        
        Args:
            order: Order to execute
            
        Returns:
            Execution result
        """
        order_id = order["order_id"]
        symbol = order["symbol"]
        
        logger.info(f"Sending order to broker: {order_id} ({symbol})")
        
        try:
            # Simulate order submission
            if self.paper_trading:
                execution_result = await self._simulate_order_execution(order)
            else:
                execution_result = await self._send_order_to_broker(order)
            
            # Update order status
            if execution_result["success"]:
                order["status"] = OrderStatus.SUBMITTED
                order["broker_order_id"] = execution_result.get("broker_order_id")
                order["submitted_time"] = datetime.now(timezone.utc)
                
                # Add to active orders
                self._active_orders[order_id] = order
                
                # For market orders in simulation, immediately fill
                if self.paper_trading and order["order_type"] == "MARKET":
                    await self._simulate_immediate_fill(order)
                
                logger.info(f"Order {order_id} submitted successfully")
                
                return {
                    "status": "submitted",
                    "order_id": order_id,
                    "broker_order_id": execution_result.get("broker_order_id"),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            else:
                order["status"] = OrderStatus.REJECTED
                order["rejection_reason"] = execution_result.get("reason")
                
                # Add to completed orders
                self._completed_orders[order_id] = order
                
                logger.error(f"Order {order_id} rejected: {execution_result.get('reason')}")
                
                return {
                    "status": "rejected",
                    "reason": execution_result.get("reason"),
                    "order_id": order_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
        
        except Exception as e:
            logger.error(f"Order execution failed for {order_id}: {e}")
            order["status"] = OrderStatus.REJECTED
            order["rejection_reason"] = str(e)
            self._completed_orders[order_id] = order
            
            return {
                "status": "error",
                "error": str(e),
                "order_id": order_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def _simulate_order_execution(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate order execution for paper trading
        
        Args:
            order: Order to simulate
            
        Returns:
            Simulation result
        """
        # Simulate latency
        await asyncio.sleep(0.1)
        
        # Mock validation (99% success rate)
        import random
        if random.random() < 0.99:
            return {
                "success": True,
                "broker_order_id": f"SIM_{order['order_id'][:8]}",
                "message": "Order submitted to simulation"
            }
        else:
            return {
                "success": False,
                "reason": "Simulated rejection - insufficient buying power"
            }
    
    async def _simulate_immediate_fill(self, order: Dict[str, Any]) -> None:
        """
        Simulate immediate fill for market orders in paper trading
        
        Args:
            order: Order to fill
        """
        # Simulate market price with slight slippage
        import random
        base_price = 150.0  # Mock current market price
        slippage = random.uniform(-0.002, 0.002)  # +/- 0.2% slippage
        fill_price = base_price * (1 + slippage)
        
        # Create fill
        fill = {
            "fill_id": str(uuid.uuid4()),
            "quantity": order["quantity"],
            "price": fill_price,
            "timestamp": datetime.now(timezone.utc),
            "commission": order["quantity"] * 0.01  # $0.01 per share
        }
        
        # Update order
        order["fills"].append(fill)
        order["filled_quantity"] = order["quantity"]
        order["average_fill_price"] = fill_price
        order["status"] = OrderStatus.FILLED
        order["completed_time"] = datetime.now(timezone.utc)
        
        # Move to completed orders
        order_id = order["order_id"]
        self._completed_orders[order_id] = order
        if order_id in self._active_orders:
            del self._active_orders[order_id]
        
        logger.info(f"Order {order_id} filled: {order['quantity']} @ {format_currency(fill_price)}")
    
    async def _send_order_to_broker(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send order to real broker (placeholder for actual implementation)
        
        Args:
            order: Order to send
            
        Returns:
            Broker response
        """
        # TODO: Implement actual broker integration
        # This would use Interactive Brokers API, Alpaca API, etc.
        
        # Placeholder implementation
        logger.warning("Real broker integration not implemented - using simulation")
        return await self._simulate_order_execution(order)
    
    async def _send_cancel_request(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send cancellation request to broker
        
        Args:
            order: Order to cancel
            
        Returns:
            Cancellation result
        """
        if self.paper_trading:
            # Simulate cancellation
            await asyncio.sleep(0.05)
            return {"success": True, "message": "Order cancelled in simulation"}
        else:
            # TODO: Implement actual broker cancellation
            logger.warning("Real broker integration not implemented")
            return {"success": True, "message": "Placeholder cancellation"}
    
    async def _monitor_order_fills(self, order_id: str) -> None:
        """
        Monitor order for fills and updates
        
        Args:
            order_id: Order to monitor
        """
        logger.info(f"Starting fill monitoring for order {order_id}")
        
        try:
            while order_id in self._active_orders:
                order = self._active_orders[order_id]
                
                # Check for fills
                await self._refresh_order_status(order)
                
                # If order is complete, stop monitoring
                if order["status"] in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
                    logger.info(f"Order {order_id} completed with status: {order['status'].value}")
                    
                    # Move to completed orders
                    self._completed_orders[order_id] = order
                    del self._active_orders[order_id]
                    break
                
                # Wait before next check
                await asyncio.sleep(1.0)
        
        except Exception as e:
            logger.error(f"Error monitoring order {order_id}: {e}")
    
    async def _refresh_order_status(self, order: Dict[str, Any]) -> None:
        """
        Refresh order status from broker
        
        Args:
            order: Order to refresh
        """
        if self.paper_trading:
            # In simulation, randomly simulate partial fills for limit orders
            import random
            if (order["order_type"] == "LIMIT" and 
                order["status"] == OrderStatus.SUBMITTED and 
                random.random() < 0.1):  # 10% chance of fill per check
                
                # Simulate partial fill
                remaining_quantity = order["quantity"] - order["filled_quantity"]
                fill_quantity = min(remaining_quantity, random.randint(1, int(remaining_quantity)))
                
                fill = {
                    "fill_id": str(uuid.uuid4()),
                    "quantity": fill_quantity,
                    "price": order.get("limit_price", 150.0),
                    "timestamp": datetime.now(timezone.utc),
                    "commission": fill_quantity * 0.01
                }
                
                order["fills"].append(fill)
                order["filled_quantity"] += fill_quantity
                
                # Update average fill price
                total_value = sum(f["quantity"] * f["price"] for f in order["fills"])
                order["average_fill_price"] = total_value / order["filled_quantity"]
                
                if order["filled_quantity"] >= order["quantity"]:
                    order["status"] = OrderStatus.FILLED
                    order["completed_time"] = datetime.now(timezone.utc)
                else:
                    order["status"] = OrderStatus.PARTIALLY_FILLED
                
                logger.info(f"Order {order['order_id']} filled: {fill_quantity} @ {format_currency(fill['price'])}")
        else:
            # TODO: Implement actual broker status refresh
            pass
    
    async def _fetch_positions_from_broker(self) -> List[Dict[str, Any]]:
        """
        Fetch current positions from broker
        
        Returns:
            List of positions
        """
        if self.paper_trading:
            # Return mock positions for simulation
            return [
                {
                    "symbol": "AAPL",
                    "quantity": 100,
                    "average_cost": 145.50,
                    "market_value": 15000.0,
                    "unrealized_pnl": 450.0,
                    "sector": "Technology"
                },
                {
                    "symbol": "MSFT",
                    "quantity": 75,
                    "average_cost": 280.00,
                    "market_value": 21000.0,
                    "unrealized_pnl": 0.0,
                    "sector": "Technology"
                }
            ]
        else:
            # TODO: Implement actual broker position fetching
            return []
    
    def _format_order_status(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format order for status response
        
        Args:
            order: Order to format
            
        Returns:
            Formatted order status
        """
        return {
            "order_id": order["order_id"],
            "symbol": order["symbol"],
            "action": order["action"],
            "quantity": order["quantity"],
            "order_type": order["order_type"],
            "status": order["status"].value,
            "filled_quantity": order["filled_quantity"],
            "remaining_quantity": order["quantity"] - order["filled_quantity"],
            "average_fill_price": order["average_fill_price"],
            "created_time": order["created_time"].isoformat(),
            "fills": len(order["fills"]),
            "limit_price": order.get("limit_price"),
            "stop_loss": order.get("stop_loss"),
            "take_profit": order.get("take_profit")
        }