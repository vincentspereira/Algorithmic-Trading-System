"""
Stub classes for missing nautilus_trader imports
"""

from enum import Enum
from typing import Any


class BarType:
    """Stub for BarType"""
    pass


class PriceType(Enum):
    """Stub for PriceType"""
    BID = "bid"
    ASK = "ask"
    MID = "mid"


class Bar:
    """Stub for Bar"""
    def __init__(self, **kwargs):
        pass


class BarEvent:
    """Stub for BarEvent"""
    def __init__(self, **kwargs):
        pass


class InstrumentId:
    """Stub for InstrumentId"""
    def __init__(self, symbol: str):
        self.symbol = symbol


class Price:
    """Stub for Price"""
    def __init__(self, value: float):
        self.value = value


class BarGenerator:
    """Stub for BarGenerator"""
    pass


def dt_to_unix_nanos(dt):
    """Stub for dt_to_unix_nanos"""
    return 0


class Event:
    """Stub for Event"""
    pass


class BarData:
    """Stub for BarData"""
    def __init__(self, **kwargs):
        pass