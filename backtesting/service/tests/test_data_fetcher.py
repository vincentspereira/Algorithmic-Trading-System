
import asyncio
from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from data.data_fetcher import DataFetcher
from app.models import DataRequest

@pytest.fixture
def data_fetcher():
    with patch('redis.Redis') as mock_redis:
        with patch('kafka.KafkaConsumer'), patch('kafka.KafkaProducer'):
            fetcher = DataFetcher()
            fetcher.redis = mock_redis.return_value
            return fetcher

@pytest.mark.asyncio
async def test_fetch_data_from_cache(data_fetcher):
    # Arrange
    request = DataRequest(
        symbol="AAPL",
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 1, 2),
        timeframe="1d"
    )
    cached_data = pd.DataFrame({'close': [150.0]})
    data_fetcher.redis.get.return_value = cached_data.to_json()

    # Act
    result = await data_fetcher.fetch_data(request)

    # Assert
    assert not result.empty
    assert result['close'][0] == 150.0
    data_fetcher.redis.get.assert_called_once()

@pytest.mark.asyncio
@patch('yfinance.download')
async def test_fetch_data_from_yfinance(mock_yf_download, data_fetcher):
    # Arrange
    request = DataRequest(
        symbol="AAPL",
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 1, 2),
        timeframe="1d"
    )
    data_fetcher.redis.get.return_value = None
    mock_yf_download.return_value = pd.DataFrame({
        'Date': [datetime(2023, 1, 1)],
        'Open': [140.0],
        'High': [145.0],
        'Low': [135.0],
        'Close': [142.0],
        'Adj Close': [141.0],
        'Volume': [1000000]
    })

    # Act
    result = await data_fetcher.fetch_data(request)

    # Assert
    assert not result.empty
    assert result['close'][0] == 142.0
    data_fetcher.redis.get.assert_called_once()
    mock_yf_download.assert_called_once()
