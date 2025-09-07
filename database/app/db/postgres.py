
import asyncio
import logging

import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from database.app.core.config import db_settings
from database.app.models import Base

logger = logging.getLogger(__name__)

class PostgreSQLManager:
    def __init__(self):
        self.engine = None
        self.session_factory = None
        self.is_healthy = False

    async def initialize(self):
        try:
            connection_string = (
                f"postgresql+asyncpg://{db_settings.POSTGRES_USER}:"
                f"{db_settings.POSTGRES_PASSWORD}@{db_settings.POSTGRES_HOST}:"
                f"{db_settings.POSTGRES_PORT}/{db_settings.POSTGRES_DATABASE}"
            )

            self.engine = create_async_engine(
                connection_string,
                pool_size=db_settings.POSTGRES_POOL_SIZE,
                max_overflow=db_settings.POSTGRES_MAX_OVERFLOW,
                pool_timeout=db_settings.CONNECTION_TIMEOUT,
                echo=False
            )

            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )

            async with self.engine.begin() as conn:
                await conn.execute("SELECT 1")

            self.is_healthy = True
            logger.info("PostgreSQL connection established")

        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL: {e}")
            self.is_healthy = False

    async def get_session(self) -> AsyncSession:
        if not self.session_factory:
            raise RuntimeError("PostgreSQL not initialized")
        return self.session_factory()

    async def create_tables(self):
        if not self.engine:
            raise RuntimeError("PostgreSQL not initialized")

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("PostgreSQL tables created")

    async def cleanup(self):
        if self.engine:
            await self.engine.dispose()
