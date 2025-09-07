
import asyncio
import logging
from typing import Dict, Any

from database.app.core.config import db_settings
from database.app.db.postgres import PostgreSQLManager
from database.app.db.clickhouse import ClickHouseManager
from database.app.db.redis import RedisManager

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.postgres = PostgreSQLManager()
        self.clickhouse = ClickHouseManager()
        self.redis = RedisManager()
        self.health_status = {
            "postgres": False,
            "clickhouse": False,
            "redis": False
        }

    async def initialize(self):
        logger.info("Initializing database connections...")

        await self.postgres.initialize()
        await self.clickhouse.initialize()
        await self.redis.initialize()

        self.health_status["postgres"] = self.postgres.is_healthy
        self.health_status["clickhouse"] = self.clickhouse.is_healthy
        self.health_status["redis"] = self.redis.is_healthy

        asyncio.create_task(self._health_monitor())

        logger.info("Database initialization completed", extra={
            "postgres": self.health_status["postgres"],
            "clickhouse": self.health_status["clickhouse"],
            "redis": self.health_status["redis"]
        })

    async def _health_monitor(self):
        while True:
            try:
                await asyncio.sleep(db_settings.HEALTH_CHECK_INTERVAL)

                self.health_status["postgres"] = self.postgres.is_healthy
                self.health_status["clickhouse"] = self.clickhouse.is_healthy
                self.health_status["redis"] = self.redis.is_healthy

            except Exception as e:
                logger.error(f"Health monitor error: {e}")

    async def cleanup(self):
        logger.info("Cleaning up database connections...")

        await self.postgres.cleanup()
        await self.clickhouse.cleanup()
        await self.redis.cleanup()

        logger.info("Database cleanup completed")

    def get_health_status(self) -> Dict[str, bool]:
        return self.health_status.copy()

# Global database manager instance
_db_manager: DatabaseManager = None

async def get_database_manager() -> DatabaseManager:
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
        await _db_manager.initialize()
    return _db_manager
