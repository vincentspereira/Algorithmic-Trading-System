# Algorithmic Trading System - Phase 2

Phase 2 introduces a feature queries endpoint, a comprehensive Streamlit research dashboard, and an enhanced gRPC streaming server.

## 1. Feature Queries Endpoint

The feature queries endpoint provides a flexible way to retrieve historical and real-time features for various financial instruments.

**Endpoint:** `GET /api/v1/features/{symbol}`

**Authentication:** Requires a valid JWT token.

**Query Parameters:**

*   `symbol` (str, required): The trading symbol (e.g., AAPL, GOOGL).
*   `start_date` (datetime, required): The start of the time range.
*   `end_date` (datetime, required): The end of the time range.
*   `feature_types` (List[str], required): A list of feature types to retrieve. Supported types: `market_data`, `indicators`, `volume_analysis`.
*   `aggregation` (str, optional, default: "1d"): The time aggregation level (e.g., `1m`, `5m`, `1h`, `1d`).

**Example Usage (Python):**

```python
import requests
from datetime import datetime, timedelta

# Obtain a JWT token from the /api/v1/auth/login endpoint
token = "your_jwt_token"
headers = {"Authorization": f"Bearer {token}"}

symbol = "AAPL"
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

params = {
    "start_date": start_date.isoformat(),
    "end_date": end_date.isoformat(),
    "feature_types": ["market_data", "indicators"],
    "aggregation": "1d",
}

response = requests.get(
    f"http://localhost:8001/api/v1/features/{symbol}",
    headers=headers,
    params=params
)

if response.status_code == 200:
    print(response.json())
else:
    print(f"Error: {response.status_code}", response.text)
```

## 2. Streamlit Research Dashboard

The Streamlit dashboard provides a powerful interface for trading research, visualization, and analysis.

**Location:** `nautilus_trader_engine/research/streamlit_app.py`

**How to Run:**

1.  Make sure the main FastAPI application is running.
2.  Navigate to the `nautilus_trader_engine` directory.
3.  Run the following command:
    ```bash
    streamlit run research/streamlit_app.py
    ```

**Features:**

*   **Authentication:** Connect to the API using your credentials.
*   **Data Fetching:** Retrieve feature data using the new endpoint.
*   **Visualizations:**
    *   Candlestick charts for price action analysis.
    *   Plots for technical indicators.
    *   Feature correlation heatmaps.
*   **Real-time Streaming:** Connect to the gRPC server to stream live market data.

## 3. Enhanced gRPC Server

The gRPC server has been updated for improved performance, reliability, and flexibility.

**Location:** `nautilus_trader_engine/api/streaming.py`

**Key Enhancements:**

*   **Dynamic Topic Subscription:** Clients can subscribe to specific `raw.ticks.{symbol}` topics.
*   **Connection Pooling:** Efficiently manages multiple concurrent client connections.
*   **Error Recovery:** Includes reconnection logic to handle transient network issues.
*   **High Performance:** Optimized for microsecond-level latency.

**Example gRPC Client (Python):**

```python
import grpc
import asyncio
from nautilus_trader_engine.api.generated import market_data_pb2, market_data_pb2_grpc

async def run_client():
    async with grpc.aio.insecure_channel('localhost:50051') as channel:
        stub = market_data_pb2_grpc.MarketDataStub(channel)
        
        # Subscribe to AAPL and GOOGL ticks
        request = market_data_pb2.SubscriptionRequest(symbols=["AAPL", "GOOGL"])
        
        try:
            async for tick in stub.StreamMarketData(request):
                print(f"Received tick: {tick.symbol} - {tick.price} @ {tick.timestamp}")
        except grpc.aio.AioRpcError as e:
            print(f"gRPC error: {e}")

if __name__ == '__main__':
    asyncio.run(run_client())
```

This completes the core features of Phase 2. The system is now equipped with powerful tools for feature engineering, research, and real-time data consumption.