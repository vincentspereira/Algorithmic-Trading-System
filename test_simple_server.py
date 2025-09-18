#!/usr/bin/env python3
"""
Simple FastAPI server for testing integration tests
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.websockets import WebSocket
import uvicorn
import json
from typing import Dict, List

# In-memory storage for test data
strategies_db: List[Dict] = []
orders_db: List[Dict] = []
backtests_db: Dict[str, Dict] = {}

app = FastAPI(
    title="Test Trading API",
    description="Simple API for integration testing",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Test Trading API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "test-api"}

@app.get("/api/v1/status")
async def api_status():
    return {"api_version": "v1", "status": "operational"}

# Authentication endpoints
@app.post("/auth/login")
async def login(credentials: dict):
    # Simulate authentication failure for error handling tests
    if credentials.get("username") == "invalid_user":
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {
        "access_token": "test-token-123",
        "token_type": "bearer",
        "user_id": "test-user"
    }

@app.get("/market-data/quotes/{symbol}")
async def get_market_data(symbol: str):
    from datetime import datetime
    return {
        "symbol": symbol,
        "price": 150.25,
        "bid": 150.20,
        "ask": 150.30,
        "volume": 1000000,
        "timestamp": datetime.now().isoformat()
    }

# Strategy endpoints
@app.get("/strategies")
async def get_strategies():
    return {
        "strategies": strategies_db if strategies_db else [
            {"id": "strategy-1", "name": "Test Strategy", "status": "active"}
        ]
    }

@app.delete("/strategies/{strategy_id}")
async def delete_strategy(strategy_id: str):
    from fastapi import Response
    if strategy_id in strategies_db:
        del strategies_db[strategy_id]
        return Response(status_code=204)
    else:
        raise HTTPException(status_code=404, detail="Strategy not found")

@app.post("/strategies", status_code=201)
async def create_strategy(strategy_data: dict):
    strategy = {
        "id": f"strategy-{len(strategies_db) + 1}",
        "name": strategy_data.get("name", "New Strategy"),
        "description": strategy_data.get("description", ""),
        "asset_class": strategy_data.get("asset_class", "stocks"),
        "strategy_type": strategy_data.get("strategy_type", "momentum"),
        "parameters": strategy_data.get("parameters", {}),
        "status": "created"
    }
    strategies_db.append(strategy)
    return strategy

@app.get("/strategies/{strategy_id}")
async def get_strategy(strategy_id: str):
    return {
        "id": strategy_id,
        "name": "Test Strategy",
        "status": "active"
    }

# Market data endpoints
@app.get("/market-data/quotes/{symbol}")
async def get_quote(symbol: str):
    return {
        "symbol": symbol,
        "price": 150.25,
        "timestamp": "2024-01-01T12:00:00Z"
    }

# Backtesting endpoints
@app.post("/backtesting/run", status_code=202)
async def run_backtest(backtest_data: dict):
    backtest_id = f"backtest-{len(backtests_db) + 1}"
    backtest = {
        "backtest_id": backtest_id,
        "strategy_id": backtest_data.get("strategy_id"),
        "start_date": backtest_data.get("start_date"),
        "end_date": backtest_data.get("end_date"),
        "initial_capital": backtest_data.get("initial_capital"),
        "status": "running",
        "message": "Backtest started"
    }
    backtests_db[backtest_id] = backtest
    return backtest

@app.get("/backtesting/{backtest_id}")
async def get_backtest_results(backtest_id: str):
    if backtest_id in backtests_db:
        backtest = backtests_db[backtest_id].copy()
        backtest["status"] = "completed"
        backtest["results"] = {
            "total_return": 0.15,
            "sharpe_ratio": 1.2,
            "max_drawdown": -0.08,
            "trades": 25,
            "win_rate": 0.68
        }
        return backtest
    else:
        raise HTTPException(status_code=404, detail="Backtest not found")

# Portfolio endpoints
@app.get("/portfolio")
async def get_portfolio():
    return {
        "total_value": 100000.0,
        "cash": 50000.0,
        "positions": [
            {"symbol": "AAPL", "quantity": 100, "value": 15000.0},
            {"symbol": "GOOGL", "quantity": 50, "value": 35000.0}
        ],
        "daily_pnl": 1250.0,
        "total_pnl": 5000.0
    }

@app.get("/portfolio/performance")
async def get_portfolio_performance(period: str = "1m"):
    return {
        "period": period,
        "total_return": 0.05,
        "sharpe_ratio": 1.2,
        "max_drawdown": -0.03,
        "volatility": 0.15,
        "alpha": 0.02,
        "beta": 1.1
    }

# Orders endpoints
@app.post("/orders", status_code=201)
async def create_order(order_data: dict):
    order = {
        "id": f"order-{len(orders_db) + 1}",
        "status": "submitted",
        "symbol": order_data.get("symbol", "AAPL"),
        "side": order_data.get("side", "buy"),
        "order_type": order_data.get("order_type", "market"),
        "quantity": order_data.get("quantity", 100),
        "price": order_data.get("price")
    }
    orders_db.append(order)
    return order

@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    return {
        "id": order_id,
        "status": "filled",
        "symbol": "AAPL",
        "quantity": 100
    }

# Risk management endpoints
@app.get("/risk/limits")
async def get_risk_limits():
    return {
        "daily_loss_limit": 0.02,
        "position_size_limit": 0.05,
        "max_positions": 10,
        "leverage_limit": 2.0
    }

@app.post("/risk/limits")
async def update_risk_limits(limits: dict):
    from datetime import datetime
    return {
        "message": "Risk limits updated successfully",
        "limits": limits,
        "updated_at": datetime.now().isoformat()
    }

# WebSocket endpoint for real-time data
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        # Send initial status message
        status_msg = {
            "status": "connected",
            "message": "WebSocket connection established"
        }
        await websocket.send_text(json.dumps(status_msg))
        
        while True:
            # Send mock real-time data
            data = {
                "type": "market_data",
                "symbol": "AAPL",
                "price": 150.25,
                "timestamp": "2024-01-01T12:00:00Z",
                "status": "active"
            }
            await websocket.send_text(json.dumps(data))
            await asyncio.sleep(1)
    except Exception:
        pass

if __name__ == "__main__":
    import asyncio
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False
    )