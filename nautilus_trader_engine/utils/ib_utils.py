"""
ib_utils.py

Utility functions for the Interactive Brokers adapter.

This module provides helper functions for:
- Converting between NautilusTrader and IB `ib_insync` object models.
- Handling of contract creation and symbol mapping.
- Parsing and formatting data for the IB API.
- Time zone conversions and commission calculations.
"""

from datetime import datetime, timezone
from typing import Dict, Optional

from ib_insync import Contract, Ticker as IBTicker, BarData as IBBar
from nautilus_trader.model.data import Bar, QuoteTick
from nautilus_trader.model.enums import OrderStatus, PriceType
from nautilus_trader.model.identifiers import InstrumentId, Venue
from nautilus_trader.model.objects import Price, Quantity

def to_ib_contract(instrument_id: InstrumentId, symbol_map: Dict[str, str]) -> Contract:
    """
    Converts a NautilusTrader InstrumentId to an `ib_insync` Contract.

    :param instrument_id: The NautilusTrader instrument ID.
    :param symbol_map: A dictionary mapping NautilusTrader symbols to IB symbols.
    :return: An `ib_insync` Contract object.
    """
    symbol_str = str(instrument_id.symbol)
    ib_symbol = symbol_map.get(symbol_str, symbol_str)
    
    # Example for creating a stock contract, can be expanded for other asset classes
    return Contract(
        symbol=ib_symbol,
        secType="STK",
        exchange="SMART",
        currency="USD"
    )

def to_nautilus_bar(bar_data: IBBar, venue: Venue) -> Bar:
    """
    Converts an `ib_insync` BarData object to a NautilusTrader Bar.

    :param bar_data: The `ib_insync` bar data.
    :param venue: The venue identifier.
    :return: A NautilusTrader Bar object.
    """
    instrument_id = InstrumentId(bar_data.contract.symbol, venue)
    ts_init = int(datetime.strptime(bar_data.date, "%Y%m%d  %H:%M:%S").replace(tzinfo=timezone.utc).timestamp() * 1e9)
    
    return Bar(
        instrument_id=instrument_id,
        open=Price(bar_data.open_, 6),
        high=Price(bar_data.high, 6),
        low=Price(bar_data.low, 6),
        close=Price(bar_data.close, 6),
        volume=Quantity(bar_data.volume, 0),
        ts_init=ts_init,
        ts_event=ts_init, # Or use a more precise event time if available
    )

def to_nautilus_quote_tick(ticker: IBTicker, venue: Venue) -> Optional[QuoteTick]:
    """
    Converts an `ib_insync` Ticker object to a NautilusTrader QuoteTick.
    
    :param ticker: The `ib_insync` ticker data.
    :param venue: The venue identifier.
    :return: A NautilusTrader QuoteTick object, or None if data is incomplete.
    """
    if ticker.bid is None or ticker.ask is None or ticker.bidSize is None or ticker.askSize is None:
        return None
        
    instrument_id = InstrumentId(ticker.contract.symbol, venue)
    ts_event = int(ticker.time.replace(tzinfo=timezone.utc).timestamp() * 1e9)

    return QuoteTick(
        instrument_id=instrument_id,
        bid_price=Price(ticker.bid, 6),
        ask_price=Price(ticker.ask, 6),
        bid_size=Quantity(ticker.bidSize, 0),
        ask_size=Quantity(ticker.askSize, 0),
        ts_event=ts_event,
        ts_init=ts_event,
    )

def from_ib_order_status(ib_status: str) -> Optional[OrderStatus]:
    """
    Maps an Interactive Brokers order status string to a NautilusTrader OrderStatus enum.

    :param ib_status: The status string from IB (e.g., 'Filled', 'Cancelled').
    :return: A NautilusTrader OrderStatus enum member, or None if no direct mapping.
    """
    status_map = {
        "ApiPending": OrderStatus.ACCEPTED,
        "PendingSubmit": OrderStatus.ACCEPTED,
        "PendingCancel": OrderStatus.PENDING_CANCEL,
        "PreSubmitted": OrderStatus.ACCEPTED,
        "Submitted": OrderStatus.SUBMITTED,
        "ApiCancelled": OrderStatus.CANCELED,
        "Cancelled": OrderStatus.CANCELED,
        "Filled": OrderStatus.FILLED,
        "Inactive": OrderStatus.REJECTED,
    }
    return status_map.get(ib_status)

def calculate_ib_commission(quantity: float, price: float) -> float:
    """
    A simplified commission calculation for IB.
    This should be replaced with a more accurate model based on the IB commission structure.
    
    :param quantity: The quantity of the trade.
    :param price: The execution price.
    :return: The estimated commission.
    """
    # Example: $0.005 per share, with a minimum of $1.00
    commission = max(1.00, 0.005 * abs(quantity))
    return commission