"""Broker Integration Module

Integrates with live brokers (Alpaca, Interactive Brokers) for real-time trading,
account data synchronization, and order execution.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import asyncio
import json
import aiohttp
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass, field
import logging
from decimal import Decimal

from pydantic import BaseModel, Field, validator
import websockets
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.database_manager import DatabaseManager, Order, Position, TradingAccount
from shared.utils.logging_utils import get_logger
from shared.config import Settings

logger = get_logger(__name__)

# ===========================================
# ENUMS AND CONSTANTS
# ===========================================

class BrokerType(str, Enum):
    ALPACA = "ALPACA"
    INTERACTIVE_BROKERS = "INTERACTIVE_BROKERS"
    PAPER_TRADING = "PAPER_TRADING"

class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"

class OrderStatus(str, Enum):
    NEW = "new"
    PENDING_NEW = "pending_new"
    ACCEPTED = "accepted"
    PENDING_CANCEL = "pending_cancel"
    PENDING_REPLACE = "pending_replace"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    DONE_FOR_DAY = "done_for_day"
    CANCELED = "canceled"
    EXPIRED = "expired"
    REPLACED = "replaced"
    REJECTED = "rejected"
    SUSPENDED = "suspended"
    CALCULATED = "calculated"

class TimeInForce(str, Enum):
    DAY = "day"
    GTC = "gtc"  # Good Till Canceled
    IOC = "ioc"  # Immediate or Cancel
    FOK = "fok"  # Fill or Kill
    GTD = "gtd"  # Good Till Date

class AssetClass(str, Enum):
    US_EQUITY = "us_equity"
    CRYPTO = "crypto"
    FOREX = "forex"
    OPTION = "option"

# ===========================================
# DATA MODELS
# ===========================================

@dataclass
class BrokerCredentials:
    """Broker API credentials"""
    api_key: str
    secret_key: str
    base_url: str
    paper_trading: bool = True
    additional_params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BrokerAccount:
    """Broker account information"""
    account_id: str
    broker_type: BrokerType
    account_number: str
    buying_power: Decimal
    cash: Decimal
    portfolio_value: Decimal
    day_trade_count: int
    pattern_day_trader: bool
    trading_blocked: bool
    transfers_blocked: bool
    account_blocked: bool
    created_at: datetime
    currency: str = "USD"
    status: str = "ACTIVE"

@dataclass
class BrokerPosition:
    """Broker position information"""
    symbol: str
    quantity: Decimal
    market_value: Decimal
    cost_basis: Decimal
    unrealized_pl: Decimal
    unrealized_plpc: Decimal
    unrealized_intraday_pl: Decimal
    unrealized_intraday_plpc: Decimal
    current_price: Decimal
    lastday_price: Decimal
    change_today: Decimal
    asset_class: AssetClass
    avg_entry_price: Decimal
    side: str  # long/short
    exchange: Optional[str] = None

class BrokerOrderRequest(BaseModel):
    """Broker order request"""
    symbol: str
    qty: Union[int, float, str]
    side: OrderSide
    type: OrderType
    time_in_force: TimeInForce = TimeInForce.DAY
    limit_price: Optional[Union[float, str]] = None
    stop_price: Optional[Union[float, str]] = None
    trail_price: Optional[Union[float, str]] = None
    trail_percent: Optional[Union[float, str]] = None
    extended_hours: bool = False
    client_order_id: Optional[str] = None
    order_class: Optional[str] = None  # simple, bracket, oco, oto
    take_profit: Optional[Dict[str, Any]] = None
    stop_loss: Optional[Dict[str, Any]] = None
    
class BrokerOrderResponse(BaseModel):
    """Broker order response"""
    id: str
    client_order_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    replaced_at: Optional[datetime] = None
    replaced_by: Optional[str] = None
    replaces: Optional[str] = None
    asset_id: str
    symbol: str
    asset_class: AssetClass
    notional: Optional[Decimal] = None
    qty: Optional[Decimal] = None
    filled_qty: Decimal = Decimal('0')
    filled_avg_price: Optional[Decimal] = None
    order_class: str
    order_type: OrderType
    type: OrderType  # Alias for order_type
    side: OrderSide
    time_in_force: TimeInForce
    limit_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    status: OrderStatus
    extended_hours: bool = False
    legs: Optional[List[Dict[str, Any]]] = None
    trail_percent: Optional[Decimal] = None
    trail_price: Optional[Decimal] = None
    hwm: Optional[Decimal] = None

class MarketDataUpdate(BaseModel):
    """Real-time market data update"""
    symbol: str
    price: float
    size: int
    timestamp: datetime
    exchange: Optional[str] = None
    conditions: Optional[List[str]] = None
    
class AccountUpdate(BaseModel):
    """Account update from broker"""
    account_id: str
    buying_power: Decimal
    cash: Decimal
    portfolio_value: Decimal
    timestamp: datetime
    
class PositionUpdate(BaseModel):
    """Position update from broker"""
    symbol: str
    quantity: Decimal
    market_value: Decimal
    unrealized_pl: Decimal
    timestamp: datetime

# ===========================================
# ABSTRACT BROKER INTERFACE
# ===========================================

class BaseBroker(ABC):
    """Abstract base class for broker integrations"""
    
    def __init__(self, credentials: BrokerCredentials, db_manager: DatabaseManager):
        self.credentials = credentials
        self.db_manager = db_manager
        self.session: Optional[aiohttp.ClientSession] = None
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.is_connected = False
        self.account_info: Optional[BrokerAccount] = None
        self.positions: Dict[str, BrokerPosition] = {}
        self.orders: Dict[str, BrokerOrderResponse] = {}
        
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to broker API"""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """Disconnect from broker API"""
        pass
    
    @abstractmethod
    async def get_account(self) -> BrokerAccount:
        """Get account information"""
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[BrokerPosition]:
        """Get all positions"""
        pass
    
    @abstractmethod
    async def get_orders(self, status: Optional[str] = None) -> List[BrokerOrderResponse]:
        """Get orders"""
        pass
    
    @abstractmethod
    async def place_order(self, order_request: BrokerOrderRequest) -> BrokerOrderResponse:
        """Place an order"""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        pass
    
    @abstractmethod
    async def get_order(self, order_id: str) -> BrokerOrderResponse:
        """Get specific order"""
        pass
    
    @abstractmethod
    async def start_streaming(self, symbols: List[str]):
        """Start real-time data streaming"""
        pass
    
    @abstractmethod
    async def stop_streaming(self):
        """Stop real-time data streaming"""
        pass
    
    async def sync_with_database(self, user_id: str, account_id: str):
        """Sync broker data with local database"""
        try:
            # Sync account information
            account = await self.get_account()
            await self._update_account_in_db(account, user_id, account_id)
            
            # Sync positions
            positions = await self.get_positions()
            await self._update_positions_in_db(positions, user_id, account_id)
            
            # Sync orders
            orders = await self.get_orders()
            await self._update_orders_in_db(orders, user_id, account_id)
            
            logger.info(f"Successfully synced broker data for account {account_id}")
            
        except Exception as e:
            logger.error(f"Error syncing broker data: {e}")
            raise
    
    async def _update_account_in_db(self, account: BrokerAccount, user_id: str, account_id: str):
        """Update account information in database"""
        try:
            async with self.db_manager.get_postgres_session() as session:
                # Update or create trading account
                stmt = select(TradingAccount).where(
                    and_(TradingAccount.account_id == account_id, TradingAccount.user_id == user_id)
                )
                result = await session.execute(stmt)
                existing_account = result.scalar_one_or_none()
                
                if existing_account:
                    # Update existing account
                    update_stmt = update(TradingAccount).where(
                        and_(TradingAccount.account_id == account_id, TradingAccount.user_id == user_id)
                    ).values(
                        balance=float(account.portfolio_value),
                        buying_power=float(account.buying_power),
                        cash_balance=float(account.cash),
                        updated_at=datetime.utcnow()
                    )
                    await session.execute(update_stmt)
                else:
                    # Create new account
                    new_account = TradingAccount(
                        account_id=account_id,
                        user_id=user_id,
                        broker_name=account.broker_type.value,
                        account_type="LIVE" if not self.credentials.paper_trading else "PAPER",
                        balance=float(account.portfolio_value),
                        buying_power=float(account.buying_power),
                        cash_balance=float(account.cash),
                        is_active=True,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    session.add(new_account)
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error updating account in database: {e}")
            raise
    
    async def _update_positions_in_db(self, positions: List[BrokerPosition], user_id: str, account_id: str):
        """Update positions in database"""
        try:
            async with self.db_manager.get_postgres_session() as session:
                for pos in positions:
                    # Update or create position
                    stmt = select(Position).where(
                        and_(
                            Position.account_id == account_id,
                            Position.user_id == user_id,
                            Position.symbol == pos.symbol
                        )
                    )
                    result = await session.execute(stmt)
                    existing_position = result.scalar_one_or_none()
                    
                    if existing_position:
                        # Update existing position
                        update_stmt = update(Position).where(
                            and_(
                                Position.account_id == account_id,
                                Position.user_id == user_id,
                                Position.symbol == pos.symbol
                            )
                        ).values(
                            quantity=float(pos.quantity),
                            avg_cost=float(pos.avg_entry_price),
                            market_value=float(pos.market_value),
                            unrealized_pnl=float(pos.unrealized_pl),
                            updated_at=datetime.utcnow()
                        )
                        await session.execute(update_stmt)
                    else:
                        # Create new position
                        new_position = Position(
                            account_id=account_id,
                            user_id=user_id,
                            symbol=pos.symbol,
                            quantity=float(pos.quantity),
                            avg_cost=float(pos.avg_entry_price),
                            market_value=float(pos.market_value),
                            unrealized_pnl=float(pos.unrealized_pl),
                            realized_pnl=0.0,
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow()
                        )
                        session.add(new_position)
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error updating positions in database: {e}")
            raise
    
    async def _update_orders_in_db(self, orders: List[BrokerOrderResponse], user_id: str, account_id: str):
        """Update orders in database"""
        try:
            async with self.db_manager.get_postgres_session() as session:
                for order in orders:
                    # Update or create order
                    stmt = select(Order).where(
                        and_(
                            Order.account_id == account_id,
                            Order.user_id == user_id,
                            Order.broker_order_id == order.id
                        )
                    )
                    result = await session.execute(stmt)
                    existing_order = result.scalar_one_or_none()
                    
                    if existing_order:
                        # Update existing order
                        update_stmt = update(Order).where(
                            and_(
                                Order.account_id == account_id,
                                Order.user_id == user_id,
                                Order.broker_order_id == order.id
                            )
                        ).values(
                            status=order.status.value.upper(),
                            filled_quantity=float(order.filled_qty),
                            filled_price=float(order.filled_avg_price) if order.filled_avg_price else None,
                            updated_at=datetime.utcnow()
                        )
                        await session.execute(update_stmt)
                    else:
                        # Create new order
                        new_order = Order(
                            account_id=account_id,
                            user_id=user_id,
                            symbol=order.symbol,
                            side=order.side.value.upper(),
                            quantity=float(order.qty) if order.qty else 0,
                            price=float(order.limit_price) if order.limit_price else None,
                            order_type=order.type.value.upper(),
                            status=order.status.value.upper(),
                            broker_order_id=order.id,
                            filled_quantity=float(order.filled_qty),
                            filled_price=float(order.filled_avg_price) if order.filled_avg_price else None,
                            created_at=order.created_at,
                            updated_at=datetime.utcnow()
                        )
                        session.add(new_order)
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error updating orders in database: {e}")
            raise

# ===========================================
# ALPACA BROKER IMPLEMENTATION
# ===========================================

class AlpacaBroker(BaseBroker):
    """Alpaca broker integration"""
    
    def __init__(self, credentials: BrokerCredentials, db_manager: DatabaseManager):
        super().__init__(credentials, db_manager)
        self.base_url = credentials.base_url or (
            "https://paper-api.alpaca.markets" if credentials.paper_trading 
            else "https://api.alpaca.markets"
        )
        self.data_url = "https://data.alpaca.markets"
        self.ws_url = "wss://stream.data.alpaca.markets/v2/iex" if credentials.paper_trading else "wss://stream.data.alpaca.markets/v2/sip"
        
    async def connect(self) -> bool:
        """Connect to Alpaca API"""
        try:
            headers = {
                "APCA-API-KEY-ID": self.credentials.api_key,
                "APCA-API-SECRET-KEY": self.credentials.secret_key,
                "Content-Type": "application/json"
            }
            
            self.session = aiohttp.ClientSession(headers=headers)
            
            # Test connection by getting account info
            account = await self.get_account()
            if account:
                self.is_connected = True
                self.account_info = account
                logger.info(f"Successfully connected to Alpaca API (Paper: {self.credentials.paper_trading})")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error connecting to Alpaca API: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from Alpaca API"""
        try:
            if self.websocket:
                await self.websocket.close()
                self.websocket = None
            
            if self.session:
                await self.session.close()
                self.session = None
            
            self.is_connected = False
            logger.info("Disconnected from Alpaca API")
            
        except Exception as e:
            logger.error(f"Error disconnecting from Alpaca API: {e}")
    
    async def get_account(self) -> BrokerAccount:
        """Get Alpaca account information"""
        try:
            if not self.session:
                raise Exception("Not connected to Alpaca API")
            
            async with self.session.get(f"{self.base_url}/v2/account") as response:
                if response.status == 200:
                    data = await response.json()
                    
                    account = BrokerAccount(
                        account_id=data["id"],
                        broker_type=BrokerType.ALPACA,
                        account_number=data["account_number"],
                        buying_power=Decimal(data["buying_power"]),
                        cash=Decimal(data["cash"]),
                        portfolio_value=Decimal(data["portfolio_value"]),
                        day_trade_count=int(data["daytrade_count"]),
                        pattern_day_trader=data["pattern_day_trader"],
                        trading_blocked=data["trading_blocked"],
                        transfers_blocked=data["transfers_blocked"],
                        account_blocked=data["account_blocked"],
                        created_at=datetime.fromisoformat(data["created_at"].replace('Z', '+00:00')),
                        currency=data["currency"],
                        status=data["status"]
                    )
                    
                    return account
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to get account info: {response.status} - {error_text}")
                    
        except Exception as e:
            logger.error(f"Error getting Alpaca account info: {e}")
            raise
    
    async def get_positions(self) -> List[BrokerPosition]:
        """Get all Alpaca positions"""
        try:
            if not self.session:
                raise Exception("Not connected to Alpaca API")
            
            async with self.session.get(f"{self.base_url}/v2/positions") as response:
                if response.status == 200:
                    data = await response.json()
                    positions = []
                    
                    for pos_data in data:
                        position = BrokerPosition(
                            symbol=pos_data["symbol"],
                            quantity=Decimal(pos_data["qty"]),
                            market_value=Decimal(pos_data["market_value"]),
                            cost_basis=Decimal(pos_data["cost_basis"]),
                            unrealized_pl=Decimal(pos_data["unrealized_pl"]),
                            unrealized_plpc=Decimal(pos_data["unrealized_plpc"]),
                            unrealized_intraday_pl=Decimal(pos_data["unrealized_intraday_pl"]),
                            unrealized_intraday_plpc=Decimal(pos_data["unrealized_intraday_plpc"]),
                            current_price=Decimal(pos_data["current_price"]),
                            lastday_price=Decimal(pos_data["lastday_price"]),
                            change_today=Decimal(pos_data["change_today"]),
                            asset_class=AssetClass.US_EQUITY,
                            avg_entry_price=Decimal(pos_data["avg_entry_price"]),
                            side=pos_data["side"],
                            exchange=pos_data.get("exchange")
                        )
                        positions.append(position)
                    
                    return positions
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to get positions: {response.status} - {error_text}")
                    
        except Exception as e:
            logger.error(f"Error getting Alpaca positions: {e}")
            raise
    
    async def get_orders(self, status: Optional[str] = None) -> List[BrokerOrderResponse]:
        """Get Alpaca orders"""
        try:
            if not self.session:
                raise Exception("Not connected to Alpaca API")
            
            params = {}
            if status:
                params["status"] = status
            
            async with self.session.get(f"{self.base_url}/v2/orders", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    orders = []
                    
                    for order_data in data:
                        order = BrokerOrderResponse(
                            id=order_data["id"],
                            client_order_id=order_data.get("client_order_id"),
                            created_at=datetime.fromisoformat(order_data["created_at"].replace('Z', '+00:00')),
                            updated_at=datetime.fromisoformat(order_data["updated_at"].replace('Z', '+00:00')),
                            submitted_at=datetime.fromisoformat(order_data["submitted_at"].replace('Z', '+00:00')) if order_data.get("submitted_at") else None,
                            filled_at=datetime.fromisoformat(order_data["filled_at"].replace('Z', '+00:00')) if order_data.get("filled_at") else None,
                            expired_at=datetime.fromisoformat(order_data["expired_at"].replace('Z', '+00:00')) if order_data.get("expired_at") else None,
                            canceled_at=datetime.fromisoformat(order_data["canceled_at"].replace('Z', '+00:00')) if order_data.get("canceled_at") else None,
                            failed_at=datetime.fromisoformat(order_data["failed_at"].replace('Z', '+00:00')) if order_data.get("failed_at") else None,
                            asset_id=order_data["asset_id"],
                            symbol=order_data["symbol"],
                            asset_class=AssetClass.US_EQUITY,
                            qty=Decimal(order_data["qty"]) if order_data.get("qty") else None,
                            filled_qty=Decimal(order_data["filled_qty"]),
                            filled_avg_price=Decimal(order_data["filled_avg_price"]) if order_data.get("filled_avg_price") else None,
                            order_class=order_data["order_class"],
                            order_type=OrderType(order_data["order_type"]),
                            type=OrderType(order_data["type"]),
                            side=OrderSide(order_data["side"]),
                            time_in_force=TimeInForce(order_data["time_in_force"]),
                            limit_price=Decimal(order_data["limit_price"]) if order_data.get("limit_price") else None,
                            stop_price=Decimal(order_data["stop_price"]) if order_data.get("stop_price") else None,
                            status=OrderStatus(order_data["status"]),
                            extended_hours=order_data.get("extended_hours", False)
                        )
                        orders.append(order)
                    
                    return orders
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to get orders: {response.status} - {error_text}")
                    
        except Exception as e:
            logger.error(f"Error getting Alpaca orders: {e}")
            raise
    
    async def place_order(self, order_request: BrokerOrderRequest) -> BrokerOrderResponse:
        """Place order with Alpaca"""
        try:
            if not self.session:
                raise Exception("Not connected to Alpaca API")
            
            # Prepare order data
            order_data = {
                "symbol": order_request.symbol,
                "qty": str(order_request.qty),
                "side": order_request.side.value,
                "type": order_request.type.value,
                "time_in_force": order_request.time_in_force.value
            }
            
            if order_request.limit_price:
                order_data["limit_price"] = str(order_request.limit_price)
            
            if order_request.stop_price:
                order_data["stop_price"] = str(order_request.stop_price)
            
            if order_request.client_order_id:
                order_data["client_order_id"] = order_request.client_order_id
            
            if order_request.extended_hours:
                order_data["extended_hours"] = order_request.extended_hours
            
            # Add bracket order parameters if specified
            if order_request.take_profit:
                order_data["order_class"] = "bracket"
                order_data["take_profit"] = order_request.take_profit
            
            if order_request.stop_loss:
                if "order_class" not in order_data:
                    order_data["order_class"] = "bracket"
                order_data["stop_loss"] = order_request.stop_loss
            
            async with self.session.post(f"{self.base_url}/v2/orders", json=order_data) as response:
                if response.status == 201:
                    data = await response.json()
                    
                    order = BrokerOrderResponse(
                        id=data["id"],
                        client_order_id=data.get("client_order_id"),
                        created_at=datetime.fromisoformat(data["created_at"].replace('Z', '+00:00')),
                        updated_at=datetime.fromisoformat(data["updated_at"].replace('Z', '+00:00')),
                        submitted_at=datetime.fromisoformat(data["submitted_at"].replace('Z', '+00:00')) if data.get("submitted_at") else None,
                        asset_id=data["asset_id"],
                        symbol=data["symbol"],
                        asset_class=AssetClass.US_EQUITY,
                        qty=Decimal(data["qty"]) if data.get("qty") else None,
                        filled_qty=Decimal(data["filled_qty"]),
                        order_class=data["order_class"],
                        order_type=OrderType(data["order_type"]),
                        type=OrderType(data["type"]),
                        side=OrderSide(data["side"]),
                        time_in_force=TimeInForce(data["time_in_force"]),
                        limit_price=Decimal(data["limit_price"]) if data.get("limit_price") else None,
                        stop_price=Decimal(data["stop_price"]) if data.get("stop_price") else None,
                        status=OrderStatus(data["status"]),
                        extended_hours=data.get("extended_hours", False)
                    )
                    
                    logger.info(f"Successfully placed Alpaca order: {order.id} for {order.symbol}")
                    return order
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to place order: {response.status} - {error_text}")
                    
        except Exception as e:
            logger.error(f"Error placing Alpaca order: {e}")
            raise
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel Alpaca order"""
        try:
            if not self.session:
                raise Exception("Not connected to Alpaca API")
            
            async with self.session.delete(f"{self.base_url}/v2/orders/{order_id}") as response:
                if response.status == 204:
                    logger.info(f"Successfully canceled Alpaca order: {order_id}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to cancel order {order_id}: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error canceling Alpaca order {order_id}: {e}")
            return False
    
    async def get_order(self, order_id: str) -> BrokerOrderResponse:
        """Get specific Alpaca order"""
        try:
            if not self.session:
                raise Exception("Not connected to Alpaca API")
            
            async with self.session.get(f"{self.base_url}/v2/orders/{order_id}") as response:
                if response.status == 200:
                    data = await response.json()
                    
                    order = BrokerOrderResponse(
                        id=data["id"],
                        client_order_id=data.get("client_order_id"),
                        created_at=datetime.fromisoformat(data["created_at"].replace('Z', '+00:00')),
                        updated_at=datetime.fromisoformat(data["updated_at"].replace('Z', '+00:00')),
                        submitted_at=datetime.fromisoformat(data["submitted_at"].replace('Z', '+00:00')) if data.get("submitted_at") else None,
                        filled_at=datetime.fromisoformat(data["filled_at"].replace('Z', '+00:00')) if data.get("filled_at") else None,
                        asset_id=data["asset_id"],
                        symbol=data["symbol"],
                        asset_class=AssetClass.US_EQUITY,
                        qty=Decimal(data["qty"]) if data.get("qty") else None,
                        filled_qty=Decimal(data["filled_qty"]),
                        filled_avg_price=Decimal(data["filled_avg_price"]) if data.get("filled_avg_price") else None,
                        order_class=data["order_class"],
                        order_type=OrderType(data["order_type"]),
                        type=OrderType(data["type"]),
                        side=OrderSide(data["side"]),
                        time_in_force=TimeInForce(data["time_in_force"]),
                        limit_price=Decimal(data["limit_price"]) if data.get("limit_price") else None,
                        stop_price=Decimal(data["stop_price"]) if data.get("stop_price") else None,
                        status=OrderStatus(data["status"]),
                        extended_hours=data.get("extended_hours", False)
                    )
                    
                    return order
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to get order {order_id}: {response.status} - {error_text}")
                    
        except Exception as e:
            logger.error(f"Error getting Alpaca order {order_id}: {e}")
            raise
    
    async def start_streaming(self, symbols: List[str]):
        """Start Alpaca real-time data streaming"""
        try:
            # This would implement WebSocket streaming for real-time data
            # For now, just log the intent
            logger.info(f"Starting Alpaca streaming for symbols: {symbols}")
            
            # WebSocket implementation would go here
            # self.websocket = await websockets.connect(self.ws_url)
            # await self._handle_streaming_data()
            
        except Exception as e:
            logger.error(f"Error starting Alpaca streaming: {e}")
            raise
    
    async def stop_streaming(self):
        """Stop Alpaca real-time data streaming"""
        try:
            if self.websocket:
                await self.websocket.close()
                self.websocket = None
                logger.info("Stopped Alpaca streaming")
                
        except Exception as e:
            logger.error(f"Error stopping Alpaca streaming: {e}")

# ===========================================
# INTERACTIVE BROKERS IMPLEMENTATION
# ===========================================

class InteractiveBrokersBroker(BaseBroker):
    """Interactive Brokers integration (placeholder)"""
    
    def __init__(self, credentials: BrokerCredentials, db_manager: DatabaseManager):
        super().__init__(credentials, db_manager)
        # IBKR would use different connection parameters
        self.host = credentials.additional_params.get('host', '127.0.0.1')
        self.port = credentials.additional_params.get('port', 7497)  # Paper trading port
        self.client_id = credentials.additional_params.get('client_id', 1)
    
    async def connect(self) -> bool:
        """Connect to Interactive Brokers API"""
        # This would implement IBKR TWS API connection
        logger.info("Interactive Brokers integration not yet implemented")
        return False
    
    async def disconnect(self):
        """Disconnect from Interactive Brokers API"""
        pass
    
    async def get_account(self) -> BrokerAccount:
        """Get IBKR account information"""
        raise NotImplementedError("Interactive Brokers integration not yet implemented")
    
    async def get_positions(self) -> List[BrokerPosition]:
        """Get IBKR positions"""
        raise NotImplementedError("Interactive Brokers integration not yet implemented")
    
    async def get_orders(self, status: Optional[str] = None) -> List[BrokerOrderResponse]:
        """Get IBKR orders"""
        raise NotImplementedError("Interactive Brokers integration not yet implemented")
    
    async def place_order(self, order_request: BrokerOrderRequest) -> BrokerOrderResponse:
        """Place IBKR order"""
        raise NotImplementedError("Interactive Brokers integration not yet implemented")
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel IBKR order"""
        raise NotImplementedError("Interactive Brokers integration not yet implemented")
    
    async def get_order(self, order_id: str) -> BrokerOrderResponse:
        """Get specific IBKR order"""
        raise NotImplementedError("Interactive Brokers integration not yet implemented")
    
    async def start_streaming(self, symbols: List[str]):
        """Start IBKR streaming"""
        raise NotImplementedError("Interactive Brokers integration not yet implemented")
    
    async def stop_streaming(self):
        """Stop IBKR streaming"""
        raise NotImplementedError("Interactive Brokers integration not yet implemented")

# ===========================================
# BROKER FACTORY
# ===========================================

class BrokerFactory:
    """Factory for creating broker instances"""
    
    @staticmethod
    def create_broker(broker_type: BrokerType, credentials: BrokerCredentials, db_manager: DatabaseManager) -> BaseBroker:
        """Create broker instance based on type"""
        if broker_type == BrokerType.ALPACA:
            return AlpacaBroker(credentials, db_manager)
        elif broker_type == BrokerType.INTERACTIVE_BROKERS:
            return InteractiveBrokersBroker(credentials, db_manager)
        else:
            raise ValueError(f"Unsupported broker type: {broker_type}")

# ===========================================
# BROKER MANAGER
# ===========================================

class BrokerManager:
    """Manages multiple broker connections"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.brokers: Dict[str, BaseBroker] = {}
        self.active_connections: Dict[str, bool] = {}
    
    async def add_broker(self, broker_id: str, broker_type: BrokerType, credentials: BrokerCredentials) -> bool:
        """Add and connect to a broker"""
        try:
            broker = BrokerFactory.create_broker(broker_type, credentials, self.db_manager)
            
            if await broker.connect():
                self.brokers[broker_id] = broker
                self.active_connections[broker_id] = True
                logger.info(f"Successfully added broker {broker_id} ({broker_type.value})")
                return True
            else:
                logger.error(f"Failed to connect to broker {broker_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error adding broker {broker_id}: {e}")
            return False
    
    async def remove_broker(self, broker_id: str) -> bool:
        """Remove and disconnect from a broker"""
        try:
            if broker_id in self.brokers:
                await self.brokers[broker_id].disconnect()
                del self.brokers[broker_id]
                del self.active_connections[broker_id]
                logger.info(f"Successfully removed broker {broker_id}")
                return True
            else:
                logger.warning(f"Broker {broker_id} not found")
                return False
                
        except Exception as e:
            logger.error(f"Error removing broker {broker_id}: {e}")
            return False
    
    def get_broker(self, broker_id: str) -> Optional[BaseBroker]:
        """Get broker instance"""
        return self.brokers.get(broker_id)
    
    async def sync_all_brokers(self, user_id: str):
        """Sync all broker data with database"""
        for broker_id, broker in self.brokers.items():
            try:
                if self.active_connections.get(broker_id, False):
                    await broker.sync_with_database(user_id, broker_id)
                    logger.info(f"Synced broker {broker_id}")
            except Exception as e:
                logger.error(f"Error syncing broker {broker_id}: {e}")
    
    def get_active_brokers(self) -> List[str]:
        """Get list of active broker IDs"""
        return [broker_id for broker_id, active in self.active_connections.items() if active]
    
    async def place_order_with_broker(self, broker_id: str, order_request: BrokerOrderRequest) -> Optional[BrokerOrderResponse]:
        """Place order with specific broker"""
        try:
            broker = self.get_broker(broker_id)
            if broker and self.active_connections.get(broker_id, False):
                return await broker.place_order(order_request)
            else:
                logger.error(f"Broker {broker_id} not available")
                return None
                
        except Exception as e:
            logger.error(f"Error placing order with broker {broker_id}: {e}")
            return None
    
    async def cancel_order_with_broker(self, broker_id: str, order_id: str) -> bool:
        """Cancel order with specific broker"""
        try:
            broker = self.get_broker(broker_id)
            if broker and self.active_connections.get(broker_id, False):
                return await broker.cancel_order(order_id)
            else:
                logger.error(f"Broker {broker_id} not available")
                return False
                
        except Exception as e:
            logger.error(f"Error canceling order with broker {broker_id}: {e}")
            return False

# ===========================================
# FACTORY FUNCTIONS
# ===========================================

async def create_broker_manager(db_manager: DatabaseManager) -> BrokerManager:
    """Factory function to create BrokerManager instance"""
    return BrokerManager(db_manager)

async def create_alpaca_broker(api_key: str, secret_key: str, paper_trading: bool, db_manager: DatabaseManager) -> AlpacaBroker:
    """Factory function to create Alpaca broker"""
    credentials = BrokerCredentials(
        api_key=api_key,
        secret_key=secret_key,
        base_url="https://paper-api.alpaca.markets" if paper_trading else "https://api.alpaca.markets",
        paper_trading=paper_trading
    )
    
    broker = AlpacaBroker(credentials, db_manager)
    await broker.connect()
    return broker