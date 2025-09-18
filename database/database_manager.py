"""
Database and Data Layer Configuration
Enterprise-grade database architecture for Algorithmic Trading System

Architecture:
- PostgreSQL: Transactional data (users, orders, portfolios, configurations)
- ClickHouse: Time-series data (market data, ticks, bars, analytics)
- Redis: Caching layer (real-time data, sessions, rate limiting)
- Connection pooling, failover, and monitoring

Author: Vincent S. Pereira
Version: 1.0.0
"""

import asyncio
import logging
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json

import asyncpg
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

# ClickHouse client (asyncio compatible)
try:
    from clickhouse_driver import Client as ClickHouseClient
    from clickhouse_driver.errors import Error as ClickHouseError
    CLICKHOUSE_AVAILABLE = True
except ImportError:
    ClickHouseClient = None
    ClickHouseError = None
    CLICKHOUSE_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """Database configuration settings"""
    # PostgreSQL settings
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "trading_user"
    postgres_password: str = "trading_password"
    postgres_database: str = "algorithmic_trading"
    postgres_pool_size: int = 20
    postgres_max_overflow: int = 30
    
    # ClickHouse settings
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 9000
    clickhouse_user: str = "default"
    clickhouse_password: str = ""
    clickhouse_database: str = "trading_analytics"
    
    # Redis settings
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0
    redis_pool_size: int = 50
    
    # General settings
    enable_ssl: bool = False
    connection_timeout: int = 30
    query_timeout: int = 60
    health_check_interval: int = 30

# SQLAlchemy Base
Base = declarative_base()

# ===========================================
# POSTGRESQL SCHEMA DEFINITIONS
# ===========================================

class User(Base):
    """User accounts and authentication"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    permissions = Column(JSONB, default=list)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime)
    
    __table_args__ = (
        Index('idx_users_username', 'username'),
        Index('idx_users_email', 'email'),
    )

class TradingAccount(Base):
    """Trading account configurations"""
    __tablename__ = "trading_accounts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    account_name = Column(String(100), nullable=False)
    broker = Column(String(50), nullable=False)  # IBKR, Alpaca, etc.
    account_number = Column(String(50), nullable=False)
    account_type = Column(String(20), nullable=False)  # PAPER, LIVE
    api_credentials = Column(JSONB)  # Encrypted credentials
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index('idx_trading_accounts_user_id', 'user_id'),
        Index('idx_trading_accounts_broker', 'broker'),
    )

class Order(Base):
    """Trading orders"""
    __tablename__ = "orders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    account_id = Column(UUID(as_uuid=True), nullable=False)
    order_id = Column(String(100), unique=True, nullable=False)  # Broker order ID
    symbol = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)  # BUY, SELL
    order_type = Column(String(20), nullable=False)  # MARKET, LIMIT, STOP
    quantity = Column(Float, nullable=False)
    price = Column(Float)
    stop_price = Column(Float)
    filled_quantity = Column(Float, default=0.0)
    avg_fill_price = Column(Float)
    status = Column(String(20), nullable=False)  # PENDING, FILLED, CANCELLED
    time_in_force = Column(String(10), default="DAY")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    filled_at = Column(DateTime)
    order_metadata = Column(JSONB)
    
    __table_args__ = (
        Index('idx_orders_user_id', 'user_id'),
        Index('idx_orders_symbol', 'symbol'),
        Index('idx_orders_status', 'status'),
        Index('idx_orders_created_at', 'created_at'),
    )

class Position(Base):
    """Current positions"""
    __tablename__ = "positions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    account_id = Column(UUID(as_uuid=True), nullable=False)
    symbol = Column(String(20), nullable=False)
    quantity = Column(Float, nullable=False)
    avg_cost = Column(Float, nullable=False)
    market_value = Column(Float)
    unrealized_pnl = Column(Float)
    realized_pnl = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index('idx_positions_user_id', 'user_id'),
        Index('idx_positions_symbol', 'symbol'),
    )

class Strategy(Base):
    """Trading strategies"""
    __tablename__ = "strategies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    strategy_type = Column(String(50), nullable=False)
    parameters = Column(JSONB)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index('idx_strategies_user_id', 'user_id'),
        Index('idx_strategies_type', 'strategy_type'),
    )

# ===========================================
# DATABASE CONNECTION MANAGER
# ===========================================

class DatabaseManager:
    """Comprehensive database management system"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.postgres_engine = None
        self.postgres_session_factory = None
        self.clickhouse_client = None
        self.redis_pool = None
        self.health_status = {
            "postgres": False,
            "clickhouse": False,
            "redis": False
        }
    
    async def initialize(self):
        """Initialize all database connections"""
        logger.info("Initializing database connections...")
        
        # Initialize PostgreSQL
        await self._init_postgresql()
        
        # Initialize ClickHouse
        await self._init_clickhouse()
        
        # Initialize Redis
        await self._init_redis()
        
        # Start health monitoring
        asyncio.create_task(self._health_monitor())
        
        logger.info("Database initialization completed", extra={
            "postgres": self.health_status["postgres"],
            "clickhouse": self.health_status["clickhouse"],
            "redis": self.health_status["redis"]
        })
    
    async def _init_postgresql(self):
        """Initialize PostgreSQL connection"""
        try:
            # Create connection string
            connection_string = (
                f"postgresql+asyncpg://{self.config.postgres_user}:"
                f"{self.config.postgres_password}@{self.config.postgres_host}:"
                f"{self.config.postgres_port}/{self.config.postgres_database}"
            )
            
            # Create engine
            self.postgres_engine = create_async_engine(
                connection_string,
                pool_size=self.config.postgres_pool_size,
                max_overflow=self.config.postgres_max_overflow,
                pool_timeout=self.config.connection_timeout,
                echo=False  # Set to True for SQL debugging
            )
            
            # Create session factory
            self.postgres_session_factory = async_sessionmaker(
                self.postgres_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Test connection
            async with self.postgres_engine.begin() as conn:
                await conn.execute("SELECT 1")
            
            self.health_status["postgres"] = True
            logger.info("PostgreSQL connection established")
            
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL: {e}")
            self.health_status["postgres"] = False
    
    async def _init_clickhouse(self):
        """Initialize ClickHouse connection"""
        try:
            if not CLICKHOUSE_AVAILABLE:
                logger.warning("ClickHouse driver not available")
                return
            
            # Create ClickHouse client
            self.clickhouse_client = ClickHouseClient(
                host=self.config.clickhouse_host,
                port=self.config.clickhouse_port,
                user=self.config.clickhouse_user,
                password=self.config.clickhouse_password,
                database=self.config.clickhouse_database,
                connect_timeout=self.config.connection_timeout,
                send_receive_timeout=self.config.query_timeout
            )
            
            # Test connection
            result = self.clickhouse_client.execute("SELECT 1")
            if result:
                self.health_status["clickhouse"] = True
                logger.info("ClickHouse connection established")
            
        except Exception as e:
            logger.error(f"Failed to initialize ClickHouse: {e}")
            self.health_status["clickhouse"] = False
    
    async def _init_redis(self):
        """Initialize Redis connection"""
        try:
            # Create Redis connection pool
            self.redis_pool = aioredis.ConnectionPool(
                host=self.config.redis_host,
                port=self.config.redis_port,
                password=self.config.redis_password if self.config.redis_password else None,
                db=self.config.redis_db,
                max_connections=self.config.redis_pool_size,
                retry_on_timeout=True,
                socket_timeout=self.config.connection_timeout
            )
            
            # Test connection
            redis_client = aioredis.Redis(connection_pool=self.redis_pool)
            await redis_client.ping()
            await redis_client.close()
            
            self.health_status["redis"] = True
            logger.info("Redis connection established")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            self.health_status["redis"] = False
    
    async def _health_monitor(self):
        """Monitor database health"""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                
                # Check PostgreSQL
                if self.postgres_engine:
                    try:
                        async with self.postgres_engine.begin() as conn:
                            await conn.execute("SELECT 1")
                        self.health_status["postgres"] = True
                    except Exception:
                        self.health_status["postgres"] = False
                
                # Check ClickHouse
                if self.clickhouse_client:
                    try:
                        self.clickhouse_client.execute("SELECT 1")
                        self.health_status["clickhouse"] = True
                    except Exception:
                        self.health_status["clickhouse"] = False
                
                # Check Redis
                if self.redis_pool:
                    try:
                        redis_client = aioredis.Redis(connection_pool=self.redis_pool)
                        await redis_client.ping()
                        await redis_client.close()
                        self.health_status["redis"] = True
                    except Exception:
                        self.health_status["redis"] = False
                        
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
    
    # ===========================================
    # POSTGRESQL OPERATIONS
    # ===========================================
    
    async def get_postgres_session(self) -> AsyncSession:
        """Get PostgreSQL session"""
        if not self.postgres_session_factory:
            raise RuntimeError("PostgreSQL not initialized")
        return self.postgres_session_factory()
    
    async def create_tables(self):
        """Create all PostgreSQL tables"""
        if not self.postgres_engine:
            raise RuntimeError("PostgreSQL not initialized")
        
        async with self.postgres_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("PostgreSQL tables created")
    
    async def execute_query(self, query: str, params: Dict = None) -> List[Dict]:
        """Execute raw SQL query"""
        async with self.get_postgres_session() as session:
            result = await session.execute(query, params or {})
            return [dict(row) for row in result.fetchall()]
    
    # ===========================================
    # CLICKHOUSE OPERATIONS
    # ===========================================
    
    async def create_clickhouse_tables(self):
        """Create ClickHouse tables for time-series data"""
        if not self.clickhouse_client:
            logger.warning("ClickHouse not available, skipping table creation")
            return
        
        # Market data table
        market_data_ddl = """
        CREATE TABLE IF NOT EXISTS market_data (
            timestamp DateTime64(3),
            symbol String,
            open Float64,
            high Float64,
            low Float64,
            close Float64,
            volume UInt64,
            interval String,
            source String
        ) ENGINE = MergeTree()
        ORDER BY (symbol, timestamp)
        PARTITION BY toYYYYMM(timestamp)
        """
        
        # Tick data table
        tick_data_ddl = """
        CREATE TABLE IF NOT EXISTS tick_data (
            timestamp DateTime64(6),
            symbol String,
            price Float64,
            size UInt32,
            bid Float64,
            ask Float64,
            bid_size UInt32,
            ask_size UInt32,
            exchange String
        ) ENGINE = MergeTree()
        ORDER BY (symbol, timestamp)
        PARTITION BY toYYYYMMDD(timestamp)
        """
        
        # Indicator data table
        indicator_data_ddl = """
        CREATE TABLE IF NOT EXISTS indicator_data (
            timestamp DateTime64(3),
            symbol String,
            indicator_name String,
            value Float64,
            signal String,
            strength Float64,
            metadata String
        ) ENGINE = MergeTree()
        ORDER BY (symbol, indicator_name, timestamp)
        PARTITION BY toYYYYMM(timestamp)
        """
        
        try:
            self.clickhouse_client.execute(market_data_ddl)
            self.clickhouse_client.execute(tick_data_ddl)
            self.clickhouse_client.execute(indicator_data_ddl)
            logger.info("ClickHouse tables created")
        except Exception as e:
            logger.error(f"Failed to create ClickHouse tables: {e}")
    
    async def insert_market_data(self, data: List[Dict]):
        """Insert market data into ClickHouse"""
        if not self.clickhouse_client:
            return
        
        try:
            self.clickhouse_client.execute(
                "INSERT INTO market_data VALUES",
                data
            )
        except Exception as e:
            logger.error(f"Failed to insert market data: {e}")
    
    async def query_market_data(self, symbol: str, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Query market data from ClickHouse"""
        if not self.clickhouse_client:
            return []
        
        query = """
        SELECT timestamp, open, high, low, close, volume
        FROM market_data
        WHERE symbol = %(symbol)s
        AND timestamp >= %(start_time)s
        AND timestamp <= %(end_time)s
        ORDER BY timestamp
        """
        
        try:
            result = self.clickhouse_client.execute(query, {
                'symbol': symbol,
                'start_time': start_time,
                'end_time': end_time
            })
            return [dict(zip(['timestamp', 'open', 'high', 'low', 'close', 'volume'], row)) for row in result]
        except Exception as e:
            logger.error(f"Failed to query market data: {e}")
            return []
    
    # ===========================================
    # REDIS OPERATIONS
    # ===========================================
    
    async def get_redis_client(self) -> aioredis.Redis:
        """Get Redis client"""
        if not self.redis_pool:
            raise RuntimeError("Redis not initialized")
        return aioredis.Redis(connection_pool=self.redis_pool)
    
    async def cache_set(self, key: str, value: Any, ttl: int = 300):
        """Set cache value with TTL"""
        async with self.get_redis_client() as redis:
            await redis.setex(key, ttl, json.dumps(value, default=str))
    
    async def cache_get(self, key: str) -> Optional[Any]:
        """Get cache value"""
        async with self.get_redis_client() as redis:
            value = await redis.get(key)
            return json.loads(value) if value else None
    
    async def cache_delete(self, key: str):
        """Delete cache key"""
        async with self.get_redis_client() as redis:
            await redis.delete(key)
    
    # ===========================================
    # CLEANUP AND SHUTDOWN
    # ===========================================
    
    async def cleanup(self):
        """Cleanup all database connections"""
        logger.info("Cleaning up database connections...")
        
        if self.postgres_engine:
            await self.postgres_engine.dispose()
        
        if self.clickhouse_client:
            self.clickhouse_client.disconnect()
        
        if self.redis_pool:
            await self.redis_pool.disconnect()
        
        logger.info("Database cleanup completed")
    
    def get_health_status(self) -> Dict[str, bool]:
        """Get current health status of all databases"""
        return self.health_status.copy()

# ===========================================
# FACTORY FUNCTIONS
# ===========================================

def create_database_config() -> DatabaseConfig:
    """Create database configuration from environment variables"""
    return DatabaseConfig(
        # PostgreSQL
        postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
        postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
        postgres_user=os.getenv("POSTGRES_USER", "trading_user"),
        postgres_password=os.getenv("POSTGRES_PASSWORD", "trading_password"),
        postgres_database=os.getenv("POSTGRES_DATABASE", "algorithmic_trading"),
        
        # ClickHouse
        clickhouse_host=os.getenv("CLICKHOUSE_HOST", "localhost"),
        clickhouse_port=int(os.getenv("CLICKHOUSE_PORT", "9000")),
        clickhouse_user=os.getenv("CLICKHOUSE_USER", "default"),
        clickhouse_password=os.getenv("CLICKHOUSE_PASSWORD", ""),
        clickhouse_database=os.getenv("CLICKHOUSE_DATABASE", "trading_analytics"),
        
        # Redis
        redis_host=os.getenv("REDIS_HOST", "localhost"),
        redis_port=int(os.getenv("REDIS_PORT", "6379")),
        redis_password=os.getenv("REDIS_PASSWORD", ""),
        redis_db=int(os.getenv("REDIS_DB", "0")),
    )

async def create_database_manager() -> DatabaseManager:
    """Create and initialize database manager"""
    config = create_database_config()
    manager = DatabaseManager(config)
    await manager.initialize()
    return manager

# Global database manager instance
_db_manager: Optional[DatabaseManager] = None

async def get_database_manager() -> DatabaseManager:
    """Get global database manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = await create_database_manager()
    return _db_manager