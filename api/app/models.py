
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

from pydantic import BaseModel, Field, validator

class TradingSymbol(BaseModel):
    """Trading symbol model"""
    symbol: str = Field(..., example="AAPL")
    exchange: str = Field(..., example="NASDAQ")
    asset_class: str = Field(..., example="STK")

    @validator('symbol')
    def symbol_must_be_uppercase(cls, v):
        return v.upper()

class MarketDataRequest(BaseModel):
    """Market data request model"""
    symbols: List[TradingSymbol]
    period: str = Field(default="1d", example="1d")
    interval: str = Field(default="1m", example="1m")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class IndicatorRequest(BaseModel):
    """Technical indicator request model"""
    symbol: TradingSymbol
    indicator_types: List[str] = Field(..., example=["rsi", "macd", "bollinger_bands"])
    include_volume_weighted: bool = Field(default=True)
    include_patterns: bool = Field(default=True)
    period_override: Optional[Dict[str, int]] = None

class OrderRequest(BaseModel):
    """Order submission request model"""
    symbol: TradingSymbol
    order_type: str = Field(..., example="MARKET")  # MARKET, LIMIT, STOP
    side: str = Field(..., example="BUY")  # BUY, SELL
    quantity: float = Field(..., gt=0, example=100.0)
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = Field(default="DAY", example="DAY")

    @validator('side')
    def side_must_be_valid(cls, v):
        if v.upper() not in ['BUY', 'SELL']:
            raise ValueError('Side must be BUY or SELL')
        return v.upper()

class PortfolioPosition(BaseModel):
    """Portfolio position model"""
    symbol: TradingSymbol
    quantity: float
    avg_cost: float
    market_value: float
    unrealized_pnl: float
    realized_pnl: float
    last_updated: datetime

class APIResponse(BaseModel):
    """Standard API response model"""
    success: bool
    data: Optional[Any] = None
    message: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)
    request_id: str = Field(default_factory=lambda: str(uuid4()))
