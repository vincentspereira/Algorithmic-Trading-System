"""
Compatibility shim for tests expecting `from database.session import get_db_session`.
This re-exports the async context manager and helpers from the engine's database config.
"""
from nautilus_trader_engine.database.database_config import (
    get_db_session,
    init_databases,
    get_performance_report,
    database_manager,
)

__all__ = [
    "get_db_session",
    "init_databases",
    "get_performance_report",
    "database_manager",
]