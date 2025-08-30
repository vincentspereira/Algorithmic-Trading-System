"""
Data Access Layer (DAL)
Clean abstraction layer for database operations

Provides:
- Repository pattern for each entity
- Transaction management
- Query optimization
- Caching integration
- Error handling

Author: Vincent S. Pereira
Version: 1.0.0
"""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid
import logging

from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from database.database_manager import (
    DatabaseManager, User, TradingAccount, Order, Position, Strategy
)

logger = logging.getLogger(__name__)

class BaseRepository:
    """Base repository with common operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    async def get_session(self) -> AsyncSession:
        """Get database session"""
        return await self.db_manager.get_postgres_session()

class UserRepository(BaseRepository):
    """User data access operations"""
    
    async def create_user(self, username: str, email: str, password_hash: str, 
                         permissions: List[str] = None) -> User:
        """Create a new user"""
        async with await self.get_session() as session:
            user = User(
                username=username,
                email=email,
                password_hash=password_hash,
                permissions=permissions or [],
                is_active=True,
                is_verified=False
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user
    
    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Get user by ID"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            return result.scalar_one_or_none()
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(User).where(User.username == username)
            )
            return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(User).where(User.email == email)
            )
            return result.scalar_one_or_none()
    
    async def update_last_login(self, user_id: uuid.UUID):
        """Update user's last login timestamp"""
        async with await self.get_session() as session:
            await session.execute(
                update(User)
                .where(User.id == user_id)
                .values(last_login=datetime.utcnow())
            )
            await session.commit()
    
    async def update_user_permissions(self, user_id: uuid.UUID, permissions: List[str]):
        """Update user permissions"""
        async with await self.get_session() as session:
            await session.execute(
                update(User)
                .where(User.id == user_id)
                .values(permissions=permissions)
            )
            await session.commit()

class TradingAccountRepository(BaseRepository):
    """Trading account data access operations"""
    
    async def create_account(self, user_id: uuid.UUID, account_name: str, 
                           broker: str, account_number: str, account_type: str,
                           api_credentials: Dict = None) -> TradingAccount:
        """Create a new trading account"""
        async with await self.get_session() as session:
            account = TradingAccount(
                user_id=user_id,
                account_name=account_name,
                broker=broker,
                account_number=account_number,
                account_type=account_type,
                api_credentials=api_credentials or {},
                is_active=True
            )
            session.add(account)
            await session.commit()
            await session.refresh(account)
            return account
    
    async def get_accounts_by_user(self, user_id: uuid.UUID) -> List[TradingAccount]:
        """Get all accounts for a user"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(TradingAccount)
                .where(and_(TradingAccount.user_id == user_id, TradingAccount.is_active == True))
                .order_by(TradingAccount.created_at.desc())
            )
            return list(result.scalars().all())
    
    async def get_account_by_id(self, account_id: uuid.UUID) -> Optional[TradingAccount]:
        """Get account by ID"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(TradingAccount).where(TradingAccount.id == account_id)
            )
            return result.scalar_one_or_none()
    
    async def deactivate_account(self, account_id: uuid.UUID):
        """Deactivate a trading account"""
        async with await self.get_session() as session:
            await session.execute(
                update(TradingAccount)
                .where(TradingAccount.id == account_id)
                .values(is_active=False)
            )
            await session.commit()

class OrderRepository(BaseRepository):
    """Order data access operations"""
    
    async def create_order(self, user_id: uuid.UUID, account_id: uuid.UUID,
                          order_id: str, symbol: str, side: str, order_type: str,
                          quantity: float, price: float = None, stop_price: float = None,
                          time_in_force: str = "DAY", metadata: Dict = None) -> Order:
        """Create a new order"""
        async with await self.get_session() as session:
            order = Order(
                user_id=user_id,
                account_id=account_id,
                order_id=order_id,
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
                stop_price=stop_price,
                time_in_force=time_in_force,
                status="PENDING",
                order_metadata=metadata or {}
            )
            session.add(order)
            await session.commit()
            await session.refresh(order)
            return order
    
    async def get_orders_by_user(self, user_id: uuid.UUID, status: str = None,
                               limit: int = 100, offset: int = 0) -> List[Order]:
        """Get orders for a user"""
        async with await self.get_session() as session:
            query = select(Order).where(Order.user_id == user_id)
            
            if status:
                query = query.where(Order.status == status)
            
            query = query.order_by(Order.created_at.desc()).limit(limit).offset(offset)
            
            result = await session.execute(query)
            return list(result.scalars().all())
    
    async def get_order_by_id(self, order_id: str, user_id: uuid.UUID = None) -> Optional[Order]:
        """Get order by order ID"""
        async with await self.get_session() as session:
            query = select(Order).where(Order.order_id == order_id)
            
            if user_id:
                query = query.where(Order.user_id == user_id)
            
            result = await session.execute(query)
            return result.scalar_one_or_none()
    
    async def update_order_status(self, order_id: str, status: str, 
                                filled_quantity: float = None, avg_fill_price: float = None):
        """Update order status and fill information"""
        async with await self.get_session() as session:
            update_values = {"status": status, "updated_at": datetime.utcnow()}
            
            if filled_quantity is not None:
                update_values["filled_quantity"] = filled_quantity
            
            if avg_fill_price is not None:
                update_values["avg_fill_price"] = avg_fill_price
            
            if status in ["FILLED", "PARTIALLY_FILLED"]:
                update_values["filled_at"] = datetime.utcnow()
            
            await session.execute(
                update(Order)
                .where(Order.order_id == order_id)
                .values(**update_values)
            )
            await session.commit()
    
    async def get_orders_by_symbol(self, symbol: str, start_date: datetime = None,
                                 end_date: datetime = None) -> List[Order]:
        """Get orders for a specific symbol"""
        async with await self.get_session() as session:
            query = select(Order).where(Order.symbol == symbol)
            
            if start_date:
                query = query.where(Order.created_at >= start_date)
            
            if end_date:
                query = query.where(Order.created_at <= end_date)
            
            query = query.order_by(Order.created_at.desc())
            
            result = await session.execute(query)
            return list(result.scalars().all())

class PositionRepository(BaseRepository):
    """Position data access operations"""
    
    async def create_or_update_position(self, user_id: uuid.UUID, account_id: uuid.UUID,
                                      symbol: str, quantity: float, avg_cost: float,
                                      market_value: float = None, unrealized_pnl: float = None) -> Position:
        """Create or update a position"""
        async with await self.get_session() as session:
            # Check if position exists
            result = await session.execute(
                select(Position).where(
                    and_(
                        Position.user_id == user_id,
                        Position.account_id == account_id,
                        Position.symbol == symbol
                    )
                )
            )
            
            position = result.scalar_one_or_none()
            
            if position:
                # Update existing position
                position.quantity = quantity
                position.avg_cost = avg_cost
                position.market_value = market_value
                position.unrealized_pnl = unrealized_pnl
                position.last_updated = datetime.utcnow()
            else:
                # Create new position
                position = Position(
                    user_id=user_id,
                    account_id=account_id,
                    symbol=symbol,
                    quantity=quantity,
                    avg_cost=avg_cost,
                    market_value=market_value,
                    unrealized_pnl=unrealized_pnl
                )
                session.add(position)
            
            await session.commit()
            await session.refresh(position)
            return position
    
    async def get_positions_by_user(self, user_id: uuid.UUID, account_id: uuid.UUID = None) -> List[Position]:
        """Get positions for a user"""
        async with await self.get_session() as session:
            query = select(Position).where(Position.user_id == user_id)
            
            if account_id:
                query = query.where(Position.account_id == account_id)
            
            # Only return positions with non-zero quantity
            query = query.where(Position.quantity != 0)
            query = query.order_by(Position.last_updated.desc())
            
            result = await session.execute(query)
            return list(result.scalars().all())
    
    async def get_position_by_symbol(self, user_id: uuid.UUID, account_id: uuid.UUID,
                                   symbol: str) -> Optional[Position]:
        """Get position for a specific symbol"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(Position).where(
                    and_(
                        Position.user_id == user_id,
                        Position.account_id == account_id,
                        Position.symbol == symbol
                    )
                )
            )
            return result.scalar_one_or_none()
    
    async def close_position(self, user_id: uuid.UUID, account_id: uuid.UUID, symbol: str):
        """Close a position (set quantity to 0)"""
        async with await self.get_session() as session:
            await session.execute(
                update(Position)
                .where(
                    and_(
                        Position.user_id == user_id,
                        Position.account_id == account_id,
                        Position.symbol == symbol
                    )
                )
                .values(quantity=0, last_updated=datetime.utcnow())
            )
            await session.commit()

class StrategyRepository(BaseRepository):
    """Strategy data access operations"""
    
    async def create_strategy(self, user_id: uuid.UUID, name: str, description: str,
                            strategy_type: str, parameters: Dict) -> Strategy:
        """Create a new strategy"""
        async with await self.get_session() as session:
            strategy = Strategy(
                user_id=user_id,
                name=name,
                description=description,
                strategy_type=strategy_type,
                parameters=parameters,
                is_active=False
            )
            session.add(strategy)
            await session.commit()
            await session.refresh(strategy)
            return strategy
    
    async def get_strategies_by_user(self, user_id: uuid.UUID) -> List[Strategy]:
        """Get strategies for a user"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(Strategy)
                .where(Strategy.user_id == user_id)
                .order_by(Strategy.created_at.desc())
            )
            return list(result.scalars().all())
    
    async def get_strategy_by_id(self, strategy_id: uuid.UUID, user_id: uuid.UUID = None) -> Optional[Strategy]:
        """Get strategy by ID"""
        async with await self.get_session() as session:
            query = select(Strategy).where(Strategy.id == strategy_id)
            
            if user_id:
                query = query.where(Strategy.user_id == user_id)
            
            result = await session.execute(query)
            return result.scalar_one_or_none()
    
    async def update_strategy_status(self, strategy_id: uuid.UUID, is_active: bool):
        """Update strategy active status"""
        async with await self.get_session() as session:
            await session.execute(
                update(Strategy)
                .where(Strategy.id == strategy_id)
                .values(is_active=is_active, updated_at=datetime.utcnow())
            )
            await session.commit()
    
    async def update_strategy_parameters(self, strategy_id: uuid.UUID, parameters: Dict):
        """Update strategy parameters"""
        async with await self.get_session() as session:
            await session.execute(
                update(Strategy)
                .where(Strategy.id == strategy_id)
                .values(parameters=parameters, updated_at=datetime.utcnow())
            )
            await session.commit()

class MarketDataRepository:
    """Market data operations for ClickHouse"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    async def store_market_data(self, symbol: str, timestamp: datetime, 
                              open_price: float, high: float, low: float, 
                              close: float, volume: int, interval: str = "1m",
                              source: str = "api"):
        """Store market data in ClickHouse"""
        if not self.db_manager.clickhouse_client:
            return
        
        try:
            data = [{
                'timestamp': timestamp,
                'symbol': symbol,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume,
                'interval': interval,
                'source': source
            }]
            
            await self.db_manager.insert_market_data(data)
            
        except Exception as e:
            logger.error(f"Failed to store market data: {e}")
    
    async def get_market_data(self, symbol: str, start_time: datetime, 
                            end_time: datetime, interval: str = "1m") -> List[Dict]:
        """Get market data from ClickHouse"""
        if not self.db_manager.clickhouse_client:
            return []
        
        try:
            query = """
            SELECT timestamp, open, high, low, close, volume
            FROM market_data
            WHERE symbol = %(symbol)s
            AND interval = %(interval)s
            AND timestamp >= %(start_time)s
            AND timestamp <= %(end_time)s
            ORDER BY timestamp
            """
            
            result = self.db_manager.clickhouse_client.execute(query, {
                'symbol': symbol,
                'interval': interval,
                'start_time': start_time,
                'end_time': end_time
            })
            
            return [dict(zip(['timestamp', 'open', 'high', 'low', 'close', 'volume'], row)) 
                   for row in result]
            
        except Exception as e:
            logger.error(f"Failed to get market data: {e}")
            return []
    
    async def store_indicator_data(self, symbol: str, timestamp: datetime,
                                 indicator_name: str, value: float, 
                                 signal: str, strength: float, metadata: Dict = None):
        """Store indicator data in ClickHouse"""
        if not self.db_manager.clickhouse_client:
            return
        
        try:
            data = [{
                'timestamp': timestamp,
                'symbol': symbol,
                'indicator_name': indicator_name,
                'value': value,
                'signal': signal,
                'strength': strength,
                'metadata': json.dumps(metadata or {})
            }]
            
            self.db_manager.clickhouse_client.execute(
                "INSERT INTO indicator_data VALUES", data
            )
            
        except Exception as e:
            logger.error(f"Failed to store indicator data: {e}")

# ===========================================
# DATA ACCESS LAYER FACTORY
# ===========================================

class DataAccessLayer:
    """Complete data access layer with all repositories"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.users = UserRepository(db_manager)
        self.trading_accounts = TradingAccountRepository(db_manager)
        self.orders = OrderRepository(db_manager)
        self.positions = PositionRepository(db_manager)
        self.strategies = StrategyRepository(db_manager)
        self.market_data = MarketDataRepository(db_manager)
    
    async def begin_transaction(self):
        """Begin a database transaction"""
        session = await self.db_manager.get_postgres_session()
        return session
    
    def get_health_status(self) -> Dict[str, bool]:
        """Get database health status"""
        return self.db_manager.get_health_status()

async def create_data_access_layer(db_manager: DatabaseManager) -> DataAccessLayer:
    """Create data access layer instance"""
    return DataAccessLayer(db_manager)