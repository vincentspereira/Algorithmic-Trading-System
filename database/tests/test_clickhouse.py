
import pytest
from unittest.mock import MagicMock, patch

from app.db.clickhouse import ClickHouseManager

@pytest.fixture
def clickhouse_manager():
    with patch('clickhouse_driver.Client') as mock_client:
        manager = ClickHouseManager()
        manager.client = mock_client.return_value
        yield manager

@pytest.mark.asyncio
async def test_clickhouse_initialize_success(clickhouse_manager):
    clickhouse_manager.client.execute.return_value = [[1]]
    await clickhouse_manager.initialize()
    assert clickhouse_manager.is_healthy is True

@pytest.mark.asyncio
async def test_clickhouse_initialize_failure(clickhouse_manager):
    clickhouse_manager.client.execute.side_effect = Exception("Connection error")
    await clickhouse_manager.initialize()
    assert clickhouse_manager.is_healthy is False

@pytest.mark.asyncio
async def test_clickhouse_create_tables(clickhouse_manager):
    clickhouse_manager.client.execute.return_value = None
    await clickhouse_manager.create_tables()
    assert clickhouse_manager.client.execute.call_count == 3
