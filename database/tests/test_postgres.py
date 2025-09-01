
import pytest
from unittest.mock import AsyncMock, patch

from app.db.postgres import PostgreSQLManager
from app.models import Base

@pytest.fixture
def postgres_manager():
    with patch('sqlalchemy.ext.asyncio.create_async_engine') as mock_create_engine:
        with patch('sqlalchemy.orm.async_sessionmaker') as mock_sessionmaker:
            manager = PostgreSQLManager()
            manager.engine = AsyncMock()
            manager.session_factory = AsyncMock()
            yield manager

@pytest.mark.asyncio
async def test_postgres_initialize_success(postgres_manager):
    postgres_manager.engine.begin.return_value.__aenter__.return_value.execute.return_value = None
    await postgres_manager.initialize()
    assert postgres_manager.is_healthy is True

@pytest.mark.asyncio
async def test_postgres_initialize_failure(postgres_manager):
    postgres_manager.engine.begin.return_value.__aenter__.return_value.execute.side_effect = Exception("Connection error")
    await postgres_manager.initialize()
    assert postgres_manager.is_healthy is False

@pytest.mark.asyncio
async def test_postgres_create_tables(postgres_manager):
    postgres_manager.engine.begin.return_value.__aenter__.return_value.run_sync.return_value = None
    await postgres_manager.create_tables()
    postgres_manager.engine.begin.return_value.__aenter__.return_value.run_sync.assert_called_once_with(Base.metadata.create_all)
