
import time
import requests
import pytest
from uuid import UUID

BASE_URL = "http://localhost:8000/api"

@pytest.mark.e2e
def test_backtesting_workflow():
    # Step 1: Create a new backtest
    create_payload = {
        "strategy": {
            "symbol": "AAPL",
            "start_date": "2023-01-01T00:00:00",
            "end_date": "2023-01-31T00:00:00",
            "timeframe": "1d",
            "fast_ma": 10,
            "slow_ma": 20,
            "initial_capital": 100000
        }
    }
    create_response = requests.post(f"{BASE_URL}/backtest", json=create_payload)
    assert create_response.status_code == 200
    result = create_response.json()
    assert "request_id" in result
    request_id = result["request_id"]

    # Step 2: Poll for backtest completion
    status_url = f"{BASE_URL}/backtest/{request_id}"
    for _ in range(60):  # Poll for up to 60 seconds
        status_response = requests.get(status_url)
        assert status_response.status_code == 200
        status_result = status_response.json()
        if status_result["status"] == "completed":
            break
        time.sleep(1)
    else:
        pytest.fail("Backtest did not complete in time")

    # Step 3: Verify the results
    assert status_result["status"] == "completed"
    assert "metrics" in status_result
    assert "trades" in status_result
    assert "equity_curve" in status_result
    assert status_result["error"] is None
