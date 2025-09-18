#!/usr/bin/env python3
"""
Pairs Trading Module

A comprehensive market-neutral pairs trading system designed for algorithmic trading
with spread/ratio-based technical indicators, statistical analysis, and advanced
strategy implementations.

This module provides:
- Pair selection and screening algorithms
- Correlation and cointegration analysis
- Spread/ratio calculations and indicators
- Mean reversion and momentum strategies
- Risk management and position sizing
- Performance analytics and reporting

Components:
- pair_selection: Statistical pair selection and screening
- correlation_analysis: Correlation and cointegration testing
- spread_indicators: Technical indicators for spread/ratio data
- convergence_strategy: Mean reversion on spread/ratio
- divergence_strategy: Momentum breakout on spread/ratio
- risk_management: Pairs-specific risk controls
- performance_analytics: Strategy performance analysis
"""

from typing import Dict, List, Tuple, Optional, Any
import warnings

# Core pair selection and analysis
try:
    from .pair_selection import (
        PairSelectionEngine,
        PairScreener,
        StatisticalPairAnalyzer,
        PairRanking,
        PairMetrics
    )
except ImportError:
    warnings.warn("Pair selection module not available")
    PairSelectionEngine = None
    PairScreener = None
    StatisticalPairAnalyzer = None
    PairRanking = None
    PairMetrics = None

# Correlation and cointegration analysis
try:
    from .correlation_analysis import (
        CorrelationAnalyzer,
        CointegrationTester,
        StationarityTester,
        SpreadAnalyzer,
        TimeSeriesAnalyzer
    )
except ImportError:
    warnings.warn("Correlation analysis module not available")
    CorrelationAnalyzer = None
    CointegrationTester = None
    StationarityTester = None
    SpreadAnalyzer = None
    TimeSeriesAnalyzer = None

# Spread and ratio indicators
try:
    from .spread_indicators import (
        SpreadCalculator,
        RatioCalculator,
        PairsTechnicalIndicators,
        VolumeWeightedSpread,
        SpreadVolatility
    )
except ImportError:
    warnings.warn("Spread indicators module not available")
    SpreadCalculator = None
    RatioCalculator = None
    PairsTechnicalIndicators = None
    VolumeWeightedSpread = None
    SpreadVolatility = None

# Trading strategies
try:
    from .convergence_strategy import (
        PairsConvergenceStrategy,
        MeanReversionSignalGenerator,
        SpreadMeanReversion
    )
except ImportError:
    warnings.warn("Convergence strategy module not available")
    PairsConvergenceStrategy = None
    MeanReversionSignalGenerator = None
    SpreadMeanReversion = None

try:
    from .divergence_strategy import (
        PairsDivergenceStrategy,
        MomentumBreakoutGenerator,
        SpreadMomentum
    )
except ImportError:
    warnings.warn("Divergence strategy module not available")
    PairsDivergenceStrategy = None
    MomentumBreakoutGenerator = None
    SpreadMomentum = None

# Risk management
try:
    from .risk_management import (
        PairsRiskManager,
        PositionSizer,
        HedgeRatioCalculator,
        DrawdownController
    )
except ImportError:
    warnings.warn("Risk management module not available")
    PairsRiskManager = None
    PositionSizer = None
    HedgeRatioCalculator = None
    DrawdownController = None

# Performance analytics
try:
    from .performance_analytics import (
        PairsPerformanceAnalyzer,
        SpreadPerformanceMetrics,
        PairwiseAnalytics,
        PortfolioAnalytics
    )
except ImportError:
    warnings.warn("Performance analytics module not available")
    PairsPerformanceAnalyzer = None
    SpreadPerformanceMetrics = None
    PairwiseAnalytics = None
    PortfolioAnalytics = None

# Export all available components
__all__ = [
    # Pair selection
    'PairSelectionEngine',
    'PairScreener', 
    'StatisticalPairAnalyzer',
    'PairRanking',
    'PairMetrics',
    
    # Correlation analysis
    'CorrelationAnalyzer',
    'CointegrationTester',
    'StationarityTester',
    'SpreadAnalyzer',
    'TimeSeriesAnalyzer',
    
    # Spread indicators
    'SpreadCalculator',
    'RatioCalculator',
    'PairsTechnicalIndicators',
    'VolumeWeightedSpread',
    'SpreadVolatility',
    
    # Trading strategies
    'PairsConvergenceStrategy',
    'MeanReversionSignalGenerator',
    'SpreadMeanReversion',
    'PairsDivergenceStrategy',
    'MomentumBreakoutGenerator',
    'SpreadMomentum',
    
    # Risk management
    'PairsRiskManager',
    'PositionSizer',
    'HedgeRatioCalculator',
    'DrawdownController',
    
    # Performance analytics
    'PairsPerformanceAnalyzer',
    'SpreadPerformanceMetrics',
    'PairwiseAnalytics',
    'PortfolioAnalytics'
]

# Module metadata
__version__ = '1.0.0'
__author__ = 'Algorithmic Trading System'
__description__ = 'Comprehensive pairs trading module with statistical analysis and strategy implementation'