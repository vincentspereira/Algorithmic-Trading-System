"""Events Module for Nautilus Trader Engine
Handles event-driven architecture and real-time event processing.
"""

from .event_bus import RealtimeEventBus

__all__ = [
    'RealtimeEventBus'
]