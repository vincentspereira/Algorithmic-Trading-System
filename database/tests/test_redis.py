
import pytest
from unittest.mock import AsyncMock, patch

from app.db.redis import RedisManager

@pytest.fixture
def redis_manager():
    with patch('redis.asyncio.ConnectionPool') as mock_pool:
        with patch('redis.asyncio.Redis') as mock_redis:
            manager = RedisManager()
            manager.pool = mock_pool.return_value
            mock_redis.return_value.ping.return_value = True
            yield manager

@pytest.mark.asyncio
async def test_redis_initialize_success(redis_manager):
    await redis_manager.initialize()
    assert redis_manager.is_healthy is True

@pytest.mark.asyncio
async def test_redis_initialize_failure(redis_manager):
    redis_manager.pool.side_effect = Exception("Connection error")
    await redis_manager.initialize()
    assert redis_manager.is_healthy is False
