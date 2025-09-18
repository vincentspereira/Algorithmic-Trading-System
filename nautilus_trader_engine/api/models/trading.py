from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone
import uuid

class PortfolioPosition(BaseModel):
    symbol: str
    quantity: float
    average_price: float
    market_value: float

class PortfolioResponse(BaseModel):
    cash: float = Field(..., description="Current cash balance")
    positions: List[PortfolioPosition] = Field(..., description="List of current positions")
    total_value: float = Field(..., description="Total portfolio value (cash + positions)")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class OrderRequest(BaseModel):
    symbol: str = Field(..., description="Symbol of the asset to trade")
    quantity: float = Field(..., gt=0, description="Quantity to trade (must be positive)")
    order_type: str = Field("MARKET", description="Type of order (e.g., MARKET, LIMIT)")
    price: Optional[float] = Field(None, description="Price for LIMIT orders")
    side: str = Field(..., description="Order side (e.g., BUY, SELL)")

class OrderResponse(BaseModel):
    order_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique order identifier")
    symbol: str
    quantity: float
    order_type: str
    price: Optional[float]
    side: str
    status: str = "PENDING"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PositionGreeks(BaseModel):
    symbol: str
    delta: float
    gamma: float
    theta: float
    vega: float

class RiskSnapshot(BaseModel):
    portfolio_var: float = Field(..., description="Portfolio Value at Risk (VaR)")
    position_greeks: List[PositionGreeks] = Field(..., description="Greeks for each position")
    concentration_metrics: dict = Field(..., description="Concentration metrics by asset class or sector")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))