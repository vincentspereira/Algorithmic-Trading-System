
from typing import Dict, Any

from database.app.core.config import db_settings

# This file centralizes all database configurations for the trading system,
# including connection pooling and performance settings.

# Database URL for SQLAlchemy
DATABASE_URL = (
    f"postgresql://{db_settings.POSTGRES_USER}:"
    f"{db_settings.POSTGRES_PASSWORD}@{db_settings.POSTGRES_HOST}:"
    f"{db_settings.POSTGRES_PORT}/{db_settings.POSTGRES_DATABASE}"
)

def get_postgres_config() -> Dict[str, Any]:
    """Get PostgreSQL configuration, including connection pooling."""
    return {
        "host": db_settings.POSTGRES_HOST,
        "port": db_settings.POSTGRES_PORT,
        "user": db_settings.POSTGRES_USER,
        "password": db_settings.POSTGRES_PASSWORD,
        "db": db_settings.POSTGRES_DATABASE,
        # Connection pooling settings
        "pool_size": db_settings.POSTGRES_POOL_SIZE,
        "max_overflow": db_settings.POSTGRES_MAX_OVERFLOW,
        "timeout": db_settings.CONNECTION_TIMEOUT,
    }

def get_clickhouse_config() -> Dict[str, Any]:
    """Get ClickHouse configuration."""
    return {
        "host": db_settings.CLICKHOUSE_HOST,
        "port": db_settings.CLICKHOUSE_PORT,
        "user": db_settings.CLICKHOUSE_USER,
        "password": db_settings.CLICKHOUSE_PASSWORD,
        "database": db_settings.CLICKHOUSE_DATABASE,
    }

def get_duckdb_config() -> Dict[str, str]:
    """Get DuckDB configuration."""
    return {
        "path": db_settings.DUCKDB_DATABASE_PATH
    }
