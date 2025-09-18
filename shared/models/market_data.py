"""Market data models for the algorithmic trading system.

This module provides data structures for market data including quotes,
trades, order books, and market data aggregation.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

logger = logging.getLogger(__name__)


class MarketDataType(Enum):
    """Types of market data."""
    QUOTE = "quote"
    TRADE = "trade"
    ORDER_BOOK = "order_book"
    BAR = "bar"
    TICK = "tick"


class QuoteType(Enum):
    """Types of quotes."""
    BID = "bid"
    ASK = "ask"
    MID = "mid"


@dataclass
class Quote:
    """Represents a market quote (bid/ask)."""
    symbol: str
    bid_price: Decimal
    ask_price: Decimal
    bid_size: Decimal
    ask_size: Decimal
    timestamp: datetime = field(default_factory=datetime.utcnow)
    exchange: Optional[str] = None
    quote_id: Optional[str] = None
    
    @property
    def mid_price(self) -> Decimal:
        """Calculate mid price."""
        return (self.bid_price + self.ask_price) / 2
    
    @property
    def spread(self) -> Decimal:
        """Calculate bid-ask spread."""
        return self.ask_price - self.bid_price
    
    @property
    def spread_bps(self) -> Decimal:
        """Calculate spread in basis points."""
        return (self.spread / self.mid_price) * 10000
    
    def is_valid(self) -> bool:
        """Check if quote is valid."""
        return (
            self.bid_price > 0 and
            self.ask_price > 0 and
            self.bid_size > 0 and
            self.ask_size > 0 and
            self.ask_price >= self.bid_price
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "symbol": self.symbol,
            "bid_price": float(self.bid_price),
            "ask_price": float(self.ask_price),
            "bid_size": float(self.bid_size),
            "ask_size": float(self.ask_size),
            "timestamp": self.timestamp.isoformat(),
            "exchange": self.exchange,
            "quote_id": self.quote_id,
            "mid_price": float(self.mid_price),
            "spread": float(self.spread),
            "spread_bps": float(self.spread_bps)
        }


@dataclass
class Trade:
    """Represents a market trade."""
    symbol: str
    price: Decimal
    size: Decimal
    timestamp: datetime = field(default_factory=datetime.utcnow)
    trade_id: Optional[str] = None
    exchange: Optional[str] = None
    side: Optional[str] = None  # "buy" or "sell"
    conditions: Optional[List[str]] = None
    
    @property
    def value(self) -> Decimal:
        """Calculate trade value."""
        return self.price * self.size
    
    def is_valid(self) -> bool:
        """Check if trade is valid."""
        return self.price > 0 and self.size > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "symbol": self.symbol,
            "price": float(self.price),
            "size": float(self.size),
            "timestamp": self.timestamp.isoformat(),
            "trade_id": self.trade_id,
            "exchange": self.exchange,
            "side": self.side,
            "conditions": self.conditions,
            "value": float(self.value)
        }


@dataclass
class OrderBookLevel:
    """Represents a single level in the order book."""
    price: Decimal
    size: Decimal
    orders: int = 1
    
    @property
    def value(self) -> Decimal:
        """Calculate total value at this level."""
        return self.price * self.size
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "price": float(self.price),
            "size": float(self.size),
            "orders": self.orders,
            "value": float(self.value)
        }


@dataclass
class OrderBook:
    """Represents a market order book."""
    symbol: str
    bids: List[OrderBookLevel] = field(default_factory=list)
    asks: List[OrderBookLevel] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    exchange: Optional[str] = None
    sequence: Optional[int] = None
    
    @property
    def best_bid(self) -> Optional[OrderBookLevel]:
        """Get best bid level."""
        return self.bids[0] if self.bids else None
    
    @property
    def best_ask(self) -> Optional[OrderBookLevel]:
        """Get best ask level."""
        return self.asks[0] if self.asks else None
    
    @property
    def mid_price(self) -> Optional[Decimal]:
        """Calculate mid price."""
        if self.best_bid and self.best_ask:
            return (self.best_bid.price + self.best_ask.price) / 2
        return None
    
    @property
    def spread(self) -> Optional[Decimal]:
        """Calculate bid-ask spread."""
        if self.best_bid and self.best_ask:
            return self.best_ask.price - self.best_bid.price
        return None
    
    def get_bid_depth(self, levels: int = 5) -> List[OrderBookLevel]:
        """Get bid depth up to specified levels."""
        return self.bids[:levels]
    
    def get_ask_depth(self, levels: int = 5) -> List[OrderBookLevel]:
        """Get ask depth up to specified levels."""
        return self.asks[:levels]
    
    def get_total_bid_size(self, levels: int = 5) -> Decimal:
        """Get total bid size for specified levels."""
        return sum(level.size for level in self.get_bid_depth(levels))
    
    def get_total_ask_size(self, levels: int = 5) -> Decimal:
        """Get total ask size for specified levels."""
        return sum(level.size for level in self.get_ask_depth(levels))
    
    def is_valid(self) -> bool:
        """Check if order book is valid."""
        if not self.bids or not self.asks:
            return False
        
        # Check bid ordering (descending)
        for i in range(len(self.bids) - 1):
            if self.bids[i].price < self.bids[i + 1].price:
                return False
        
        # Check ask ordering (ascending)
        for i in range(len(self.asks) - 1):
            if self.asks[i].price > self.asks[i + 1].price:
                return False
        
        # Check no crossed market
        if self.best_bid and self.best_ask:
            if self.best_bid.price >= self.best_ask.price:
                return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "symbol": self.symbol,
            "bids": [level.to_dict() for level in self.bids],
            "asks": [level.to_dict() for level in self.asks],
            "timestamp": self.timestamp.isoformat(),
            "exchange": self.exchange,
            "sequence": self.sequence,
            "best_bid": self.best_bid.to_dict() if self.best_bid else None,
            "best_ask": self.best_ask.to_dict() if self.best_ask else None,
            "mid_price": float(self.mid_price) if self.mid_price else None,
            "spread": float(self.spread) if self.spread else None
        }


@dataclass
class MarketData:
    """Aggregated market data container."""
    symbol: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    quote: Optional[Quote] = None
    trade: Optional[Trade] = None
    order_book: Optional[OrderBook] = None
    data_type: MarketDataType = MarketDataType.QUOTE
    exchange: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def price(self) -> Optional[Decimal]:
        """Get current price from available data."""
        if self.trade:
            return self.trade.price
        elif self.quote:
            return self.quote.mid_price
        elif self.order_book and self.order_book.mid_price:
            return self.order_book.mid_price
        return None
    
    @property
    def volume(self) -> Optional[Decimal]:
        """Get current volume from available data."""
        if self.trade:
            return self.trade.size
        elif self.quote:
            return (self.quote.bid_size + self.quote.ask_size) / 2
        return None
    
    def is_valid(self) -> bool:
        """Check if market data is valid."""
        if self.quote and not self.quote.is_valid():
            return False
        if self.trade and not self.trade.is_valid():
            return False
        if self.order_book and not self.order_book.is_valid():
            return False
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "data_type": self.data_type.value,
            "exchange": self.exchange,
            "price": float(self.price) if self.price else None,
            "volume": float(self.volume) if self.volume else None,
            "quote": self.quote.to_dict() if self.quote else None,
            "trade": self.trade.to_dict() if self.trade else None,
            "order_book": self.order_book.to_dict() if self.order_book else None,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_quote(cls, quote: Quote) -> "MarketData":
        """Create MarketData from Quote."""
        return cls(
            symbol=quote.symbol,
            timestamp=quote.timestamp,
            quote=quote,
            data_type=MarketDataType.QUOTE,
            exchange=quote.exchange
        )
    
    @classmethod
    def from_trade(cls, trade: Trade) -> "MarketData":
        """Create MarketData from Trade."""
        return cls(
            symbol=trade.symbol,
            timestamp=trade.timestamp,
            trade=trade,
            data_type=MarketDataType.TRADE,
            exchange=trade.exchange
        )
    
    @classmethod
    def from_order_book(cls, order_book: OrderBook) -> "MarketData":
        """Create MarketData from OrderBook."""
        return cls(
            symbol=order_book.symbol,
            timestamp=order_book.timestamp,
            order_book=order_book,
            data_type=MarketDataType.ORDER_BOOK,
            exchange=order_book.exchange
        )


class MarketDataAggregator:
    """Aggregates and manages market data streams."""
    
    def __init__(self):
        self.data_cache: Dict[str, MarketData] = {}
        self.subscribers: Dict[str, List[callable]] = {}
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def add_data(self, market_data: MarketData) -> None:
        """Add market data to cache and notify subscribers."""
        if not market_data.is_valid():
            self.logger.warning(f"Invalid market data for {market_data.symbol}")
            return
        
        self.data_cache[market_data.symbol] = market_data
        
        # Notify subscribers
        if market_data.symbol in self.subscribers:
            for callback in self.subscribers[market_data.symbol]:
                try:
                    callback(market_data)
                except Exception as e:
                    self.logger.error(f"Error notifying subscriber: {e}")
    
    def get_latest(self, symbol: str) -> Optional[MarketData]:
        """Get latest market data for symbol."""
        return self.data_cache.get(symbol)
    
    def subscribe(self, symbol: str, callback: callable) -> None:
        """Subscribe to market data updates for symbol."""
        if symbol not in self.subscribers:
            self.subscribers[symbol] = []
        self.subscribers[symbol].append(callback)
    
    def unsubscribe(self, symbol: str, callback: callable) -> None:
        """Unsubscribe from market data updates."""
        if symbol in self.subscribers:
            try:
                self.subscribers[symbol].remove(callback)
            except ValueError:
                pass
    
    def get_symbols(self) -> List[str]:
        """Get all symbols with cached data."""
        return list(self.data_cache.keys())
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self.data_cache.clear()
        self.logger.info("Market data cache cleared")