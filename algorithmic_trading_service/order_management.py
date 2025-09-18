"""Order Management System

Comprehensive order management with CRUD operations, status tracking,
validation, and lifecycle management.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import logging

from pydantic import BaseModel, Field, validator
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from database.database_manager import DatabaseManager, Order, Position, TradingAccount
from shared.utils.logging_utils import get_logger

logger = get_logger(__name__)

# ===========================================
# ENUMS AND CONSTANTS
# ===========================================

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"
    TRAILING_STOP = "TRAILING_STOP"

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    REPLACED = "REPLACED"

class TimeInForce(str, Enum):
    DAY = "DAY"
    GTC = "GTC"  # Good Till Cancelled
    IOC = "IOC"  # Immediate or Cancel
    FOK = "FOK"  # Fill or Kill
    GTD = "GTD"  # Good Till Date

class OrderValidationError(Exception):
    """Custom exception for order validation errors"""
    pass

class OrderNotFoundError(Exception):
    """Custom exception for order not found errors"""
    pass

# ===========================================
# PYDANTIC MODELS
# ===========================================

class OrderCreateRequest(BaseModel):
    """Order creation request model"""
    symbol: str = Field(..., min_length=1, max_length=20, description="Trading symbol")
    side: OrderSide = Field(..., description="Order side (BUY/SELL)")
    order_type: OrderType = Field(..., description="Order type")
    quantity: float = Field(..., gt=0, description="Order quantity")
    price: Optional[float] = Field(None, gt=0, description="Limit price")
    stop_price: Optional[float] = Field(None, gt=0, description="Stop price")
    trail_amount: Optional[float] = Field(None, gt=0, description="Trailing stop amount")
    trail_percent: Optional[float] = Field(None, gt=0, le=100, description="Trailing stop percentage")
    time_in_force: TimeInForce = Field(TimeInForce.DAY, description="Time in force")
    good_till_date: Optional[datetime] = Field(None, description="Good till date for GTD orders")
    account_id: str = Field(..., description="Trading account ID")
    strategy_id: Optional[str] = Field(None, description="Associated strategy ID")
    client_order_id: Optional[str] = Field(None, description="Client-provided order ID")
    notes: Optional[str] = Field(None, max_length=500, description="Order notes")
    
    @validator('symbol')
    def validate_symbol(cls, v):
        return v.upper().strip()
    
    @validator('price', 'stop_price', 'trail_amount')
    def validate_prices(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Prices must be positive")
        return v
    
    @validator('good_till_date')
    def validate_gtd_date(cls, v, values):
        if v and values.get('time_in_force') != TimeInForce.GTD:
            raise ValueError("good_till_date only valid for GTD orders")
        if values.get('time_in_force') == TimeInForce.GTD and not v:
            raise ValueError("good_till_date required for GTD orders")
        if v and v <= datetime.now(timezone.utc):
            raise ValueError("Good till date must be in the future.")
        return v

class OrderUpdateRequest(BaseModel):
    """Order update request model"""
    quantity: Optional[float] = Field(None, gt=0, description="New quantity")
    price: Optional[float] = Field(None, gt=0, description="New price")
    stop_price: Optional[float] = Field(None, gt=0, description="New stop price")
    time_in_force: Optional[TimeInForce] = Field(None, description="New time in force")
    good_till_date: Optional[datetime] = Field(None, description="New good till date")
    notes: Optional[str] = Field(None, max_length=500, description="Updated notes")

class OrderResponse(BaseModel):
    """Order response model"""
    id: str
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float]
    stop_price: Optional[float]
    trail_amount: Optional[float]
    trail_percent: Optional[float]
    filled_quantity: float
    remaining_quantity: float
    avg_fill_price: Optional[float]
    status: OrderStatus
    time_in_force: TimeInForce
    good_till_date: Optional[datetime]
    account_id: str
    strategy_id: Optional[str]
    client_order_id: Optional[str]
    broker_order_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    filled_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    notes: Optional[str]
    rejection_reason: Optional[str]
    fills: List[Dict[str, Any]] = Field(default_factory=list)
    
    class Config:
        from_attributes = True

class OrderFill(BaseModel):
    """Order fill model"""
    fill_id: str
    order_id: str
    quantity: float
    price: float
    timestamp: datetime
    execution_id: str
    commission: Optional[float] = None
    
class OrderSearchFilters(BaseModel):
    """Order search filters"""
    symbols: Optional[List[str]] = None
    sides: Optional[List[OrderSide]] = None
    statuses: Optional[List[OrderStatus]] = None
    order_types: Optional[List[OrderType]] = None
    account_ids: Optional[List[str]] = None
    strategy_ids: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    min_quantity: Optional[float] = None
    max_quantity: Optional[float] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None

# ===========================================
# ORDER MANAGEMENT SERVICE
# ===========================================

class OrderManager:
    """Comprehensive order management system"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.order_cache: Dict[str, Dict] = {}  # In-memory cache for active orders
        self.validation_rules: Dict[str, Any] = self._load_validation_rules()
        
    def _load_validation_rules(self) -> Dict[str, Any]:
        """Load order validation rules"""
        return {
            "max_order_size": 10000,  # Maximum shares per order
            "max_order_value": 1000000,  # Maximum dollar value per order
            "min_price_increment": 0.01,  # Minimum price increment
            "max_orders_per_minute": 60,  # Rate limiting
            "allowed_symbols": None,  # None means all symbols allowed
            "blocked_symbols": ["RESTRICTED"],  # Blocked symbols
            "market_hours_only": False,  # Allow after-hours trading
        }
    
    async def create_order(self, request: OrderCreateRequest, user_id: str) -> OrderResponse:
        """Create a new order with comprehensive validation"""
        try:
            # Validate the order request
            await self._validate_order_request(request, user_id)
            
            # Generate unique order ID
            order_id = str(uuid.uuid4())
            client_order_id = request.client_order_id or f"CLT_{order_id[:8]}"
            
            # Create order data
            order_data = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "account_id": request.account_id,
                "order_id": order_id,
                "symbol": request.symbol,
                "side": request.side.value,
                "order_type": request.order_type.value,
                "quantity": request.quantity,
                "price": request.price,
                "stop_price": request.stop_price,
                "filled_quantity": 0.0,
                "avg_fill_price": None,
                "status": OrderStatus.PENDING.value,
                "time_in_force": request.time_in_force.value,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "order_metadata": {
                    "strategy_id": request.strategy_id,
                    "client_order_id": client_order_id,
                    "trail_amount": request.trail_amount,
                    "trail_percent": request.trail_percent,
                    "good_till_date": request.good_till_date.isoformat() if request.good_till_date else None,
                    "notes": request.notes,
                    "source": "api",
                    "validation_passed": True
                }
            }
            
            # Store in database
            async with self.db_manager.get_postgres_session() as session:
                # Create Order instance
                order = Order(**order_data)
                session.add(order)
                await session.commit()
                await session.refresh(order)
            
            # Add to cache
            self.order_cache[order_id] = order_data
            
            logger.info(f"Order created successfully: {order_id} for user {user_id}")
            
            return await self._build_order_response(order_data)
            
        except OrderValidationError as e:
            logger.warning(f"Order validation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            raise Exception(f"Failed to create order: {str(e)}")
    
    async def update_order(self, order_id: str, request: OrderUpdateRequest, user_id: str) -> OrderResponse:
        """Update an existing order"""
        try:
            # Get existing order
            order_data = await self._get_order_data(order_id, user_id)
            
            if not order_data:
                raise OrderNotFoundError(f"Order {order_id} not found")
            
            # Check if order can be updated
            if order_data["status"] not in [OrderStatus.PENDING.value, OrderStatus.SUBMITTED.value]:
                raise OrderValidationError(f"Cannot update order in status: {order_data['status']}")
            
            # Prepare update data
            update_data = {"updated_at": datetime.now(timezone.utc)}
            metadata_updates = {}
            
            if request.quantity is not None:
                update_data["quantity"] = request.quantity
            if request.price is not None:
                update_data["price"] = request.price
            if request.stop_price is not None:
                update_data["stop_price"] = request.stop_price
            if request.time_in_force is not None:
                update_data["time_in_force"] = request.time_in_force.value
            if request.good_till_date is not None:
                metadata_updates["good_till_date"] = request.good_till_date.isoformat()
            if request.notes is not None:
                metadata_updates["notes"] = request.notes
            
            # Update metadata if needed
            if metadata_updates:
                current_metadata = order_data.get("order_metadata", {})
                current_metadata.update(metadata_updates)
                update_data["order_metadata"] = current_metadata
            
            # Update in database
            async with self.db_manager.get_postgres_session() as session:
                stmt = update(Order).where(
                    and_(Order.order_id == order_id, Order.user_id == user_id)
                ).values(**update_data)
                await session.execute(stmt)
                await session.commit()
            
            # Update cache
            if order_id in self.order_cache:
                self.order_cache[order_id].update(update_data)
            
            # Get updated order
            updated_order = await self._get_order_data(order_id, user_id)
            
            logger.info(f"Order updated successfully: {order_id}")
            
            return await self._build_order_response(updated_order)
            
        except (OrderNotFoundError, OrderValidationError):
            raise
        except Exception as e:
            logger.error(f"Error updating order: {e}")
            raise Exception(f"Failed to update order: {str(e)}")
    
    async def cancel_order(self, order_id: str, user_id: str, reason: str = "User requested") -> bool:
        """Cancel an existing order"""
        try:
            # Get existing order
            order_data = await self._get_order_data(order_id, user_id)
            
            if not order_data:
                raise OrderNotFoundError(f"Order {order_id} not found")
            
            # Check if order can be cancelled
            if order_data["status"] in [OrderStatus.FILLED.value, OrderStatus.CANCELLED.value, OrderStatus.REJECTED.value]:
                raise OrderValidationError(f"Cannot cancel order in status: {order_data['status']}")
            
            # Update order status
            update_data = {
                "status": OrderStatus.CANCELLED.value,
                "updated_at": datetime.now(timezone.utc),
                "order_metadata": {
                    **order_data.get("order_metadata", {}),
                    "cancellation_reason": reason,
                    "cancelled_at": datetime.now(timezone.utc).isoformat()
                }
            }
            
            # Update in database
            async with self.db_manager.get_postgres_session() as session:
                stmt = update(Order).where(
                    and_(Order.order_id == order_id, Order.user_id == user_id)
                ).values(**update_data)
                result = await session.execute(stmt)
                await session.commit()
            
            # Remove from cache
            if order_id in self.order_cache:
                del self.order_cache[order_id]
            
            logger.info(f"Order cancelled successfully: {order_id}, reason: {reason}")
            
            return result.rowcount > 0
            
        except (OrderNotFoundError, OrderValidationError):
            raise
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            raise Exception(f"Failed to cancel order: {str(e)}")
    
    async def get_order(self, order_id: str, user_id: str) -> Optional[OrderResponse]:
        """Get a specific order by ID"""
        try:
            order_data = await self._get_order_data(order_id, user_id)
            
            if not order_data:
                return None
            
            return await self._build_order_response(order_data)
            
        except Exception as e:
            logger.error(f"Error getting order: {e}")
            raise Exception(f"Failed to get order: {str(e)}")
    
    async def search_orders(
        self, 
        user_id: str, 
        filters: OrderSearchFilters, 
        limit: int = 100, 
        offset: int = 0
    ) -> Tuple[List[OrderResponse], int]:
        """Search orders with filters and pagination"""
        try:
            # Build query conditions
            conditions = [Order.user_id == user_id]
            
            if filters.symbols:
                conditions.append(Order.symbol.in_(filters.symbols))
            if filters.sides:
                conditions.append(Order.side.in_([s.value for s in filters.sides]))
            if filters.statuses:
                conditions.append(Order.status.in_([s.value for s in filters.statuses]))
            if filters.order_types:
                conditions.append(Order.order_type.in_([t.value for t in filters.order_types]))
            if filters.account_ids:
                conditions.append(Order.account_id.in_(filters.account_ids))
            if filters.start_date:
                conditions.append(Order.created_at >= filters.start_date)
            if filters.end_date:
                conditions.append(Order.created_at <= filters.end_date)
            if filters.min_quantity:
                conditions.append(Order.quantity >= filters.min_quantity)
            if filters.max_quantity:
                conditions.append(Order.quantity <= filters.max_quantity)
            if filters.min_price:
                conditions.append(Order.price >= filters.min_price)
            if filters.max_price:
                conditions.append(Order.price <= filters.max_price)
            
            # Execute query
            async with self.db_manager.get_postgres_session() as session:
                # Count total
                count_stmt = select(Order).where(and_(*conditions))
                count_result = await session.execute(count_stmt)
                total_count = len(count_result.fetchall())
                
                # Get orders with pagination
                stmt = select(Order).where(and_(*conditions)).order_by(
                    Order.created_at.desc()
                ).limit(limit).offset(offset)
                
                result = await session.execute(stmt)
                orders = result.fetchall()
            
            # Convert to response models
            order_responses = []
            for order in orders:
                order_dict = {
                    "id": str(order.Order.id),
                    "order_id": order.Order.order_id,
                    "symbol": order.Order.symbol,
                    "side": order.Order.side,
                    "order_type": order.Order.order_type,
                    "quantity": order.Order.quantity,
                    "price": order.Order.price,
                    "stop_price": order.Order.stop_price,
                    "filled_quantity": order.Order.filled_quantity or 0.0,
                    "avg_fill_price": order.Order.avg_fill_price,
                    "status": order.Order.status,
                    "time_in_force": order.Order.time_in_force,
                    "account_id": str(order.Order.account_id),
                    "created_at": order.Order.created_at,
                    "updated_at": order.Order.updated_at,
                    "filled_at": order.Order.filled_at,
                    "order_metadata": order.Order.order_metadata or {}
                }
                order_responses.append(await self._build_order_response(order_dict))
            
            return order_responses, total_count
            
        except Exception as e:
            logger.error(f"Error searching orders: {e}")
            raise Exception(f"Failed to search orders: {str(e)}")
    
    async def update_order_status(
        self, 
        order_id: str, 
        new_status: OrderStatus, 
        fill_data: Optional[OrderFill] = None,
        rejection_reason: Optional[str] = None
    ) -> bool:
        """Update order status (typically called by execution engine)"""
        try:
            update_data = {
                "status": new_status.value,
                "updated_at": datetime.now(timezone.utc)
            }
            
            # Handle fill data
            if fill_data:
                update_data["filled_quantity"] = fill_data.quantity
                update_data["avg_fill_price"] = fill_data.price
                if new_status == OrderStatus.FILLED:
                    update_data["filled_at"] = fill_data.timestamp
            
            # Handle rejection
            if rejection_reason:
                metadata_update = {"rejection_reason": rejection_reason}
                update_data["order_metadata"] = metadata_update
            
            # Update in database
            async with self.db_manager.get_postgres_session() as session:
                stmt = update(Order).where(Order.order_id == order_id).values(**update_data)
                result = await session.execute(stmt)
                await session.commit()
            
            # Update cache
            if order_id in self.order_cache:
                self.order_cache[order_id].update(update_data)
            
            logger.info(f"Order status updated: {order_id} -> {new_status.value}")
            
            return result.rowcount > 0
            
        except Exception as e:
            logger.error(f"Error updating order status: {e}")
            raise Exception(f"Failed to update order status: {str(e)}")
    
    async def _validate_order_request(self, request: OrderCreateRequest, user_id: str):
        """Comprehensive order validation"""
        # Check account ownership
        async with self.db_manager.get_postgres_session() as session:
            stmt = select(TradingAccount).where(
                and_(TradingAccount.id == request.account_id, TradingAccount.user_id == user_id)
            )
            result = await session.execute(stmt)
            account = result.fetchone()
            
            if not account:
                raise OrderValidationError("Account not found or unauthorized")
        
        # Validate order parameters based on type
        if request.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT] and not request.price:
            raise OrderValidationError("Price required for limit orders")
        
        if request.order_type in [OrderType.STOP, OrderType.STOP_LIMIT] and not request.stop_price:
            raise OrderValidationError("Stop price required for stop orders")
        
        if request.order_type == OrderType.TRAILING_STOP:
            if not request.trail_amount and not request.trail_percent:
                raise OrderValidationError("Trail amount or trail percent required for trailing stop orders")
        
        # Validate against business rules
        if request.quantity > self.validation_rules["max_order_size"]:
            raise OrderValidationError(f"Order size exceeds maximum: {self.validation_rules['max_order_size']}")
        
        if request.price and request.quantity * request.price > self.validation_rules["max_order_value"]:
            raise OrderValidationError(f"Order value exceeds maximum: {self.validation_rules['max_order_value']}")
        
        if request.symbol in self.validation_rules["blocked_symbols"]:
            raise OrderValidationError(f"Symbol {request.symbol} is blocked")
    
    async def _get_order_data(self, order_id: str, user_id: str) -> Optional[Dict]:
        """Get order data from cache or database"""
        # Check cache first
        if order_id in self.order_cache:
            cached_order = self.order_cache[order_id]
            if cached_order["user_id"] == user_id:
                return cached_order
        
        # Query database
        async with self.db_manager.get_postgres_session() as session:
            stmt = select(Order).where(
                and_(Order.order_id == order_id, Order.user_id == user_id)
            )
            result = await session.execute(stmt)
            order = result.fetchone()
            
            if order:
                order_dict = {
                    "id": str(order.Order.id),
                    "user_id": str(order.Order.user_id),
                    "account_id": str(order.Order.account_id),
                    "order_id": order.Order.order_id,
                    "symbol": order.Order.symbol,
                    "side": order.Order.side,
                    "order_type": order.Order.order_type,
                    "quantity": order.Order.quantity,
                    "price": order.Order.price,
                    "stop_price": order.Order.stop_price,
                    "filled_quantity": order.Order.filled_quantity or 0.0,
                    "avg_fill_price": order.Order.avg_fill_price,
                    "status": order.Order.status,
                    "time_in_force": order.Order.time_in_force,
                    "created_at": order.Order.created_at,
                    "updated_at": order.Order.updated_at,
                    "filled_at": order.Order.filled_at,
                    "order_metadata": order.Order.order_metadata or {}
                }
                return order_dict
        
        return None
    
    async def _build_order_response(self, order_data: Dict) -> OrderResponse:
        """Build OrderResponse from order data"""
        metadata = order_data.get("order_metadata", {})
        
        return OrderResponse(
            id=order_data["id"],
            order_id=order_data["order_id"],
            symbol=order_data["symbol"],
            side=OrderSide(order_data["side"]),
            order_type=OrderType(order_data["order_type"]),
            quantity=order_data["quantity"],
            price=order_data.get("price"),
            stop_price=order_data.get("stop_price"),
            trail_amount=metadata.get("trail_amount"),
            trail_percent=metadata.get("trail_percent"),
            filled_quantity=order_data.get("filled_quantity", 0.0),
            remaining_quantity=order_data["quantity"] - order_data.get("filled_quantity", 0.0),
            avg_fill_price=order_data.get("avg_fill_price"),
            status=OrderStatus(order_data["status"]),
            time_in_force=TimeInForce(order_data["time_in_force"]),
            good_till_date=datetime.fromisoformat(metadata["good_till_date"]) if metadata.get("good_till_date") else None,
            account_id=order_data["account_id"],
            strategy_id=metadata.get("strategy_id"),
            client_order_id=metadata.get("client_order_id"),
            broker_order_id=metadata.get("broker_order_id"),
            created_at=order_data["created_at"],
            updated_at=order_data["updated_at"],
            filled_at=order_data.get("filled_at"),
            cancelled_at=datetime.fromisoformat(metadata["cancelled_at"]) if metadata.get("cancelled_at") else None,
            notes=metadata.get("notes"),
            rejection_reason=metadata.get("rejection_reason"),
            fills=metadata.get("fills", [])
        )

# ===========================================
# FACTORY FUNCTION
# ===========================================

async def create_order_manager(db_manager: DatabaseManager) -> OrderManager:
    """Factory function to create OrderManager instance"""
    return OrderManager(db_manager)