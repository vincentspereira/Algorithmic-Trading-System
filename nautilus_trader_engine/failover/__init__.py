"""Failover Module for Nautilus Trader Engine
Handles system failover and recovery mechanisms for high availability.
"""

from .failover_manager import FailoverManager

__all__ = [
    'FailoverManager'
]