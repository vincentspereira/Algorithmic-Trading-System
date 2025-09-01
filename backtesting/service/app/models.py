
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

class TimeFrame(str, Enum):
    """Trading timeframes"""
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1d"

class MAStrategy(BaseModel):
    """Moving Average Strategy Parameters"""
    symbol: str
    start_date: datetime
    end_date: datetime
    timeframe: TimeFrame
    fast_ma: int = Field(default=20, gt=0)
    slow_ma: int = Field(default=50, gt=0)
    initial_capital: float = Field(default=100000.0, gt=0)

class BacktestStatus(str, Enum):
    """Backtest execution status"""
    PENDING = "pending"
    FETCHING_DATA = "fetching_data"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class BacktestRequest(BaseModel):
    """Backtest request model"""
    strategy: MAStrategy
    request_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class BacktestResult(BaseModel):
    """Backtest result model"""
    request_id: UUID
    status: BacktestStatus
    metrics: Optional[Dict] = None
    trades: Optional[List[Dict]] = None
    equity_curve: Optional[List[Dict]] = None
    error: Optional[str] = None

class MarketData(BaseModel):
    """Market data model"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

class DataRequest(BaseModel):
    """Data request model"""
    symbol: str
    start_date: datetime
    end_date: datetime
    timeframe: str
