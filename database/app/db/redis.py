
import logging

import redis.asyncio as aioredis

from database.app.core.config import db_settings

logger = logging.getLogger(__name__)

class RedisManager:
    def __init__(self):
        self.pool = None
        self.is_healthy = False

    async def initialize(self):
        try:
            self.pool = aioredis.ConnectionPool(
                host=db_settings.REDIS_HOST,
                port=db_settings.REDIS_PORT,
                password=db_settings.REDIS_PASSWORD if db_settings.REDIS_PASSWORD else None,
                db=db_settings.REDIS_DB,
                max_connections=db_settings.REDIS_POOL_SIZE,
                retry_on_timeout=True,
                socket_timeout=db_settings.CONNECTION_TIMEOUT
            )

            redis_client = aioredis.Redis(connection_pool=self.pool)
            await redis_client.ping()
            await redis_client.close()

            self.is_healthy = True
            logger.info("Redis connection established")

        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            self.is_healthy = False

    async def get_client(self) -> aioredis.Redis:
        if not self.pool:
            raise RuntimeError("Redis not initialized")
        return aioredis.Redis(connection_pool=self.pool)

    async def cleanup(self):
        if self.pool:
            await self.pool.disconnect()
