from dataclasses import dataclass

@dataclass
class MarketData:
    symbol: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int

@dataclass
class Quote:
    symbol: str
    bid: float
    ask: float
    timestamp: str

@dataclass
class Trade:
    symbol: str
    price: float
    volume: int
    timestamp: str

@dataclass
class Bar:
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: str