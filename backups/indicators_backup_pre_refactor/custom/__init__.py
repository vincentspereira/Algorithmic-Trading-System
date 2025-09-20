"""Custom and Proprietary Technical Indicators

This module contains proprietary and composite technical indicators developed
specifically for the algorithmic trading system. These indicators combine
multiple traditional indicators or implement novel analysis methods.

Components:
===========
- comprehensive_indicators: Complete suite of traditional and custom indicators
- smart_money_analysis: Institutional money flow and smart money detection
- cross_asset_correlation_engine: Cross-asset correlation and signal propagation
- multi_timeframe_engine: Multi-timeframe analysis and signal aggregation
- fused_rsi_bb_vwap: Composite indicator combining RSI, Bollinger Bands, and VWAP

Key Features:
=============
- Proprietary indicator formulations
- Multi-asset correlation analysis
- Smart money flow detection
- Composite signal generation
- Cross-timeframe analysis
- Advanced pattern recognition
- Institutional-grade analytics

Custom Indicators:
==================
- Comprehensive Technical Suite: 80+ indicators with volume weighting
- Smart Money Index: Institutional flow detection
- Cross-Asset Momentum: Inter-market signal propagation
- Multi-Timeframe Confluence: Signal confirmation across timeframes
- Fused Momentum Oscillator: RSI + Bollinger Bands + VWAP composite
- Market Regime Classifier: ML-based market state detection
- Volume-Weighted Sentiment: Volume-adjusted sentiment analysis

Usage:
======
from nautilus_trader_engine.indicators.custom import (
    comprehensive_indicators,
    smart_money_analysis,
    cross_asset_correlation_engine,
    multi_timeframe_engine,
    fused_rsi_bb_vwap
)

# Calculate comprehensive indicators
all_indicators = comprehensive_indicators.calculate_all_indicators(
    ohlcv_data, 
    volume_weighted=True
)

# Detect smart money flows
smart_money = smart_money_analysis.detect_smart_money_flow(
    price_data, 
    volume_data, 
    order_flow_data
)

# Analyze cross-asset correlations
correlations = cross_asset_correlation_engine.analyze_correlations(
    asset_data_dict
)

# Multi-timeframe analysis
mtf_signals = multi_timeframe_engine.generate_mtf_signals(
    price_data, 
    timeframes=['1m', '5m', '15m', '1h']
)

# Fused indicator signals
fused_signals = fused_rsi_bb_vwap.calculate_fused_signals(
    ohlcv_data
)
"""

try:
    from . import comprehensive_indicators
    from . import smart_money_analysis
    from . import cross_asset_correlation_engine
    from . import multi_timeframe_engine
    from . import fused_rsi_bb_vwap
except ImportError:
    # Handle missing dependencies gracefully
    pass

__all__ = [
    'comprehensive_indicators',
    'smart_money_analysis',
    'cross_asset_correlation_engine',
    'multi_timeframe_engine',
    'fused_rsi_bb_vwap'
]