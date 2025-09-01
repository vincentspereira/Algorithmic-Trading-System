
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app

client = TestClient(app)

@patch("app.api.market_data.data_feed_manager")
def test_get_market_data(mock_data_feed_manager):
    mock_data_feed_manager.get_historical_data.return_value = {"AAPL": {"close": 150.0}}
    response = client.post("/api/v1/market-data", json={
        "symbols": [
            {
                "symbol": "AAPL",
                "exchange": "NASDAQ",
                "asset_class": "STK"
            }
        ]
    })
    assert response.status_code == 200
    assert response.json()["data"]["AAPL"]["close"] == 150.0
