"""
Order Flow Analysis Module

This module provides institutional-grade order flow analysis tools including:
- Order Book Imbalance: Real-time analysis of buy/sell order imbalances
- Large Order Detection: Identification of significant market orders
- Iceberg Order Detection: Pattern recognition for hidden large orders
- Market Maker Absorption: Detection of order absorption by market makers
- Volume Profile Analysis: Time and price-based volume analysis
- Smart Money Tracking: Detection of institutional order flow patterns

All implementations include volume-weighting, smart money confirmation,
multi-timeframe analysis, adaptive confidence scoring, and integrated risk management.
"""

from .order_flow_analyzer import (
    InstitutionalOrderFlowAnalyzer, OrderFlowAnalysis, OrderFlowTradingSignal,
    OrderFlowSignal, OrderFlowStrength, OrderBookSnapshot,
    create_order_flow_analyzer, calculate_order_book_imbalance, detect_large_orders
)

__all__ = [
    "InstitutionalOrderFlowAnalyzer",
    "OrderFlowAnalysis",
    "OrderFlowTradingSignal",
    "OrderFlowSignal",
    "OrderFlowStrength",
    "OrderBookSnapshot",
    "create_order_flow_analyzer",
    "calculate_order_book_imbalance",
    "detect_large_orders"
]