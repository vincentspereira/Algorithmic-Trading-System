"""
GraphQL Schema for Algorithmic Trading System
Complex data relationships and queries

Author: Vincent S. Pereira
Version: 1.0.0
"""

import strawberry
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio

@strawberry.type
class TradingSymbol:
    symbol: str
    exchange: str
    asset_class: str

@strawberry.type
class MarketData:
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    
@strawberry.type
class TechnicalIndicator:
    name: str
    category: str
    signal: str
    strength: float
    confidence: float
    volume_weighted: bool
    metadata: strawberry.scalars.JSON

@strawberry.type
class Order:
    order_id: str
    symbol: str
    side: str
    quantity: float
    price: Optional[float]
    status: str
    created_at: datetime
    filled_at: Optional[datetime]

@strawberry.type
class Position:
    symbol: str
    quantity: float
    avg_cost: float
    market_value: float
    unrealized_pnl: float

@strawberry.type
class Portfolio:
    positions: List[Position]
    total_value: float
    total_pnl: float
    cash_balance: float

@strawberry.input
class MarketDataFilter:
    symbols: List[str]
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    interval: str = "1d"

@strawberry.input
class IndicatorFilter:
    symbol: str
    types: List[str]
    include_volume_weighted: bool = True

@strawberry.type
class Query:
    @strawberry.field
    async def market_data(self, filter: MarketDataFilter) -> List[MarketData]:
        """Get market data with flexible filtering"""
        # Implementation would connect to data services
        return []
    
    @strawberry.field
    async def indicators(self, filter: IndicatorFilter) -> List[TechnicalIndicator]:
        """Get technical indicators for symbol"""
        return []
    
    @strawberry.field
    async def portfolio(self, user_id: str) -> Portfolio:
        """Get user portfolio"""
        return Portfolio(positions=[], total_value=0.0, total_pnl=0.0, cash_balance=0.0)

schema = strawberry.Schema(query=Query)