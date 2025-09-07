
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from contextlib import asynccontextmanager

from database.app.db.postgres import PostgreSQLManager
from database.app.models import Base

@pytest.fixture
def postgres_manager():
    with patch('database.app.db.postgres.create_async_engine') as mock_create_engine:
        with patch('database.app.db.postgres.async_sessionmaker') as mock_sessionmaker:
            # Create a proper async context manager mock
            mock_conn = AsyncMock()
            
            @asynccontextmanager
            async def mock_begin():
                yield mock_conn
            
            mock_engine = AsyncMock()
            mock_engine.begin = mock_begin
            mock_engine.dispose = AsyncMock()
            
            # Mock the create_async_engine to return our mock engine
            mock_create_engine.return_value = mock_engine
            mock_sessionmaker.return_value = AsyncMock()
            
            manager = PostgreSQLManager()
            manager._mock_conn = mock_conn  # Store reference for tests
            yield manager

@pytest.mark.asyncio
async def test_postgres_initialize_success(postgres_manager):
    # Mock successful execution
    postgres_manager._mock_conn.execute.return_value = None
    
    await postgres_manager.initialize()
    assert postgres_manager.is_healthy is True

@pytest.mark.asyncio
async def test_postgres_initialize_failure(postgres_manager):
    # Mock failed execution
    postgres_manager._mock_conn.execute.side_effect = Exception("Connection error")
    
    await postgres_manager.initialize()
    assert postgres_manager.is_healthy is False

@pytest.mark.asyncio
async def test_postgres_create_tables(postgres_manager):
    # Initialize first to set up the engine
    postgres_manager._mock_conn.execute.return_value = None
    await postgres_manager.initialize()
    
    # Mock successful table creation
    postgres_manager._mock_conn.run_sync.return_value = None
    
    await postgres_manager.create_tables()
    postgres_manager._mock_conn.run_sync.assert_called_once_with(Base.metadata.create_all)
