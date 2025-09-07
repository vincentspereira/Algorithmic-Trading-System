"""
Database utilities for the Algorithmic Trading System.

This module provides consolidated database connection and operation utilities
that were previously duplicated across multiple components. Provides consistent
database handling for PostgreSQL, ClickHouse, DuckDB, and Redis.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncGenerator, Dict, Generator, Optional, Union

# Optional database imports
try:
    import psycopg2
except ImportError:
    psycopg2 = None

try:
    import redis
except ImportError:
    redis = None

try:
    import duckdb
except ImportError:
    duckdb = None
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from .error_handling import DatabaseError, handle_error, retry


logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration helper"""
    
    @staticmethod
    def get_postgres_config() -> Dict[str, Any]:
        """Get PostgreSQL configuration with environment variable support"""
        return {
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": int(os.getenv("POSTGRES_PORT", "5432")),
            "user": os.getenv("POSTGRES_USER", "postgres"),
            "password": os.getenv("POSTGRES_PASSWORD", "password"),
            "database": os.getenv("POSTGRES_DB", "trading_system"),
            "pool_size": int(os.getenv("POSTGRES_POOL_SIZE", "5")),
            "max_overflow": int(os.getenv("POSTGRES_MAX_OVERFLOW", "10")),
            "timeout": int(os.getenv("POSTGRES_TIMEOUT", "30")),
        }
    
    @staticmethod
    def get_clickhouse_config() -> Dict[str, Any]:
        """Get ClickHouse configuration with environment variable support"""
        return {
            "host": os.getenv("CLICKHOUSE_HOST", "localhost"),
            "port": int(os.getenv("CLICKHOUSE_PORT", "8123")),
            "user": os.getenv("CLICKHOUSE_USER", "default"),
            "password": os.getenv("CLICKHOUSE_PASSWORD", ""),
            "database": os.getenv("CLICKHOUSE_DB", "default"),
        }
    
    @staticmethod
    def get_redis_config() -> Dict[str, Any]:
        """Get Redis configuration with environment variable support"""
        return {
            "host": os.getenv("REDIS_HOST", "localhost"),
            "port": int(os.getenv("REDIS_PORT", "6379")),
            "db": int(os.getenv("REDIS_DB", "0")),
            "password": os.getenv("REDIS_PASSWORD"),
            "max_connections": int(os.getenv("REDIS_MAX_CONNECTIONS", "20")),
        }
    
    @staticmethod
    def get_duckdb_config() -> Dict[str, str]:
        """Get DuckDB configuration with environment variable support"""
        return {
            "path": os.getenv("DUCKDB_DATABASE_PATH", ":memory:")
        }


class PostgreSQLConnectionManager:
    """PostgreSQL connection manager with pooling and error handling"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize PostgreSQL connection manager
        
        Args:
            config: Database configuration dictionary
        """
        self.config = config or DatabaseConfig.get_postgres_config()
        self.engine = None
        self.session_factory = None
        self.async_engine = None
        self.async_session_factory = None
    
    def initialize_sync_engine(self):
        """Initialize synchronous SQLAlchemy engine"""
        connection_string = (
            f"postgresql://{self.config['user']}:{self.config['password']}"
            f"@{self.config['host']}:{self.config['port']}/{self.config['database']}"
        )
        
        self.engine = create_engine(
            connection_string,
            pool_size=self.config["pool_size"],
            max_overflow=self.config["max_overflow"],
            pool_timeout=self.config["timeout"]
        )
        
        self.session_factory = sessionmaker(bind=self.engine)
        logger.info(f"PostgreSQL sync engine initialized: {self.config['host']}:{self.config['port']}")
    
    async def initialize_async_engine(self):
        """Initialize asynchronous SQLAlchemy engine"""
        connection_string = (
            f"postgresql+asyncpg://{self.config['user']}:{self.config['password']}"
            f"@{self.config['host']}:{self.config['port']}/{self.config['database']}"
        )
        
        self.async_engine = create_async_engine(
            connection_string,
            pool_size=self.config["pool_size"],
            max_overflow=self.config["max_overflow"]
        )
        
        self.async_session_factory = async_sessionmaker(bind=self.async_engine)
        logger.info(f"PostgreSQL async engine initialized: {self.config['host']}:{self.config['port']}")
    
    @contextmanager
    def get_session(self) -> Generator:
        """
        Get synchronous database session with automatic cleanup
        
        Yields:
            Database session
            
        Example:
            with db_manager.get_session() as session:
                result = session.execute("SELECT 1")
        """
        if not self.session_factory:
            self.initialize_sync_engine()
        
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise DatabaseError(f"Database operation failed: {e}")
        finally:
            session.close()
    
    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get asynchronous database session with automatic cleanup
        
        Yields:
            Async database session
            
        Example:
            async with db_manager.get_async_session() as session:
                result = await session.execute("SELECT 1")
        """
        if not self.async_session_factory:
            await self.initialize_async_engine()
        
        session = self.async_session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Async database session error: {e}")
            raise DatabaseError(f"Async database operation failed: {e}")
        finally:
            await session.close()
    
    @retry(max_attempts=3, retry_exceptions=(psycopg2.OperationalError,) if psycopg2 else (Exception,))
    def test_connection(self) -> bool:
        """
        Test database connection
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self.get_session() as session:
                session.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"PostgreSQL connection test failed: {e}")
            return False


class RedisConnectionManager:
    """Redis connection manager with connection pooling"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Redis connection manager
        
        Args:
            config: Redis configuration dictionary
        """
        self.config = config or DatabaseConfig.get_redis_config()
        self.pool = None
        self.client = None
    
    def initialize_pool(self):
        """Initialize Redis connection pool"""
        self.pool = redis.ConnectionPool(
            host=self.config["host"],
            port=self.config["port"],
            db=self.config["db"],
            password=self.config["password"],
            max_connections=self.config["max_connections"]
        )
        
        self.client = redis.Redis(connection_pool=self.pool)
        logger.info(f"Redis pool initialized: {self.config['host']}:{self.config['port']}")
    
    def get_client(self) -> redis.Redis:
        """
        Get Redis client
        
        Returns:
            Redis client instance
        """
        if not self.client:
            self.initialize_pool()
        return self.client
    
    @retry(max_attempts=3, retry_exceptions=(redis.ConnectionError,))
    def test_connection(self) -> bool:
        """
        Test Redis connection
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            client = self.get_client()
            client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis connection test failed: {e}")
            return False


class DuckDBConnectionManager:
    """DuckDB connection manager"""
    
    def __init__(self, config: Optional[Dict[str, str]] = None):
        """
        Initialize DuckDB connection manager
        
        Args:
            config: DuckDB configuration dictionary
        """
        self.config = config or DatabaseConfig.get_duckdb_config()
        self.connection = None
    
    @contextmanager
    def get_connection(self) -> Generator:
        """
        Get DuckDB connection with automatic cleanup
        
        Yields:
            DuckDB connection
            
        Example:
            with duckdb_manager.get_connection() as conn:
                result = conn.execute("SELECT 1").fetchall()
        """
        conn = duckdb.connect(self.config["path"])
        try:
            yield conn
        except Exception as e:
            logger.error(f"DuckDB connection error: {e}")
            raise DatabaseError(f"DuckDB operation failed: {e}")
        finally:
            conn.close()
    
    @retry(max_attempts=3)
    def test_connection(self) -> bool:
        """
        Test DuckDB connection
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"DuckDB connection test failed: {e}")
            return False


# Global connection managers (lazy initialization)
_postgres_manager = None
_redis_manager = None
_duckdb_manager = None


def get_postgres_manager() -> PostgreSQLConnectionManager:
    """Get global PostgreSQL connection manager"""
    global _postgres_manager
    if _postgres_manager is None:
        _postgres_manager = PostgreSQLConnectionManager()
    return _postgres_manager


def get_redis_manager() -> RedisConnectionManager:
    """Get global Redis connection manager"""
    global _redis_manager
    if _redis_manager is None:
        _redis_manager = RedisConnectionManager()
    return _redis_manager


def get_duckdb_manager() -> DuckDBConnectionManager:
    """Get global DuckDB connection manager"""
    global _duckdb_manager
    if _duckdb_manager is None:
        _duckdb_manager = DuckDBConnectionManager()
    return _duckdb_manager


# Utility functions for common database operations
async def test_all_connections() -> Dict[str, bool]:
    """
    Test all database connections
    
    Returns:
        Dictionary with connection test results
    """
    results = {}
    
    # Test PostgreSQL
    try:
        pg_manager = get_postgres_manager()
        results["postgresql"] = pg_manager.test_connection()
    except Exception as e:
        logger.error(f"PostgreSQL test failed: {e}")
        results["postgresql"] = False
    
    # Test Redis
    try:
        redis_manager = get_redis_manager()
        results["redis"] = redis_manager.test_connection()
    except Exception as e:
        logger.error(f"Redis test failed: {e}")
        results["redis"] = False
    
    # Test DuckDB
    try:
        duckdb_manager = get_duckdb_manager()
        results["duckdb"] = duckdb_manager.test_connection()
    except Exception as e:
        logger.error(f"DuckDB test failed: {e}")
        results["duckdb"] = False
    
    return results


def create_connection_string(
    host: str,
    port: int,
    database: str,
    username: str,
    password: str,
    driver: str = "postgresql"
) -> str:
    """
    Create database connection string
    
    Args:
        host: Database host
        port: Database port
        database: Database name
        username: Username
        password: Password
        driver: Database driver
        
    Returns:
        Connection string
    """
    return f"{driver}://{username}:{password}@{host}:{port}/{database}"