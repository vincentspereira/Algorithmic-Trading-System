import os
from typing import Dict, Any

# This file centralizes all database configurations for the trading system,
# including connection pooling and performance settings.

def get_postgres_config() -> Dict[str, Any]:
    """Get PostgreSQL configuration, including connection pooling."""
    return {
        "host": os.getenv("POSTGRES_HOST", "postgres"),
        "port": int(os.getenv("POSTGRES_PORT", 5432)),
        "user": os.getenv("POSTGRES_USER", "user"),
        "password": os.getenv("POSTGRES_PASSWORD", "password"),
        "db": os.getenv("POSTGRES_DB", "trading_system"),
        # Connection pooling settings
        "pool_size": int(os.getenv("POSTGRES_POOL_SIZE", 5)),
        "max_overflow": int(os.getenv("POSTGRES_MAX_OVERFLOW", 10)),
        "timeout": int(os.getenv("POSTGRES_TIMEOUT", 30)),
    }

def get_clickhouse_config() -> Dict[str, Any]:
    """Get ClickHouse configuration."""
    return {
        "host": os.getenv("CLICKHOUSE_HOST", "clickhouse"),
        "port": int(os.getenv("CLICKHOUSE_PORT", 8123)),
        "user": os.getenv("CLICKHOUSE_USER", "default"),
        "password": os.getenv("CLICKHOUSE_PASSWORD", ""),
        "database": os.getenv("CLICKHOUSE_DB", "default"),
    }

def get_duckdb_config() -> Dict[str, str]:
    """Get DuckDB configuration."""
    return {
        "path": os.getenv("DUCKDB_DATABASE_PATH", "/app/data/duckdb/trading_research.duckdb")
    }