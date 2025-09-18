"""Momentum Strategy Module

This module implements comprehensive momentum-based trading strategies that capitalize
on the tendency of assets to continue moving in their current direction.

Features:
- Trend Following Strategies (Moving Average, MACD, ADX-based)
- Momentum Breakout Strategies (Price, Volume, Volatility breakouts)
- Multi-timeframe momentum analysis
- Momentum oscillator strategies (RSI, Stochastic)
- Adaptive momentum strategies with regime detection
- Volume-weighted momentum indicators
- Risk-adjusted momentum scoring
- Momentum persistence analysis

Architecture:
- Follows the 5-Pillar Architecture (Data, Signals, Risk, Execution, Monitoring)
- Event-driven design with real-time processing capabilities
- Modular components for easy customization and extension
- Integration with unified strategy management system

Components:
- TrendFollowingStrategy: Base class for trend-following strategies
- MomentumBreakoutStrategy: Base class for momentum breakout strategies
- MovingAverageTrendStrategy: Multiple MA crossover strategies
- MACDTrendStrategy: MACD-based trend following
- ADXTrendStrategy: ADX-based trend strength analysis
- RSIMomentumStrategy: RSI-based momentum oscillator strategy
- StochasticMomentumStrategy: Stochastic oscillator momentum strategy
- MomentumAnalyzer: Core momentum calculation engine
- TrendAnalyzer: Trend identification and strength analysis
- MomentumScorer: Risk-adjusted momentum scoring system
"""

from typing import Dict, List, Optional, Any
import logging

# Import core components
from .trend_following_strategies import (
    TrendFollowingStrategy,
    MovingAverageTrendStrategy,
    MACDTrendStrategy,
    ADXTrendStrategy,
    TrendAnalyzer,
    TrendDirection,
    TrendStrength,
    TrendSignal,
    calculate_trend_strength,
    detect_trend_change,
    calculate_ma_crossover
)

from .momentum_breakout_strategies import (
    MomentumDirection,
    MomentumStrength,
    MomentumMetrics,
    MomentumSignal,
    MomentumAnalyzer,
    MomentumBreakoutStrategy,
    PriceMomentumBreakoutStrategy,
    VolumeMomentumBreakoutStrategy,
    VolatilityMomentumBreakoutStrategy,
    calculate_momentum_score,
    detect_momentum_breakout,
    calculate_momentum_persistence
)

from .momentum_oscillator_strategies import (
    MomentumOscillatorStrategy,
    RSIMomentumStrategy,
    StochasticMomentumStrategy,
    MomentumOscillatorAnalyzer,
    OscillatorSignal,
    calculate_rsi_momentum,
    calculate_stochastic_momentum,
    detect_oscillator_divergence
)

# Export all components
__all__ = [
    # Enums
    'TrendDirection',
    'TrendStrength',
    'MomentumDirection',
    'MomentumStrength',
    
    # Data structures
    'TrendMetrics',
    'TrendSignal',
    'MomentumMetrics',
    'MomentumSignal',
    
    # Analyzers
    'TrendAnalyzer',
    'MomentumAnalyzer',
    
    # Strategies
    'TrendFollowingStrategy',
    'MovingAverageTrendStrategy',
    'MACDTrendStrategy',
    'ADXTrendStrategy',
    'MomentumBreakoutStrategy',
    'PriceMomentumBreakoutStrategy',
    'VolumeMomentumBreakoutStrategy',
    'VolatilityMomentumBreakoutStrategy',
    
    # Utility functions
    'calculate_trend_strength',
    'detect_trend_change',
    'calculate_trend_persistence',
    'calculate_momentum_score',
    'detect_momentum_breakout',
    'calculate_momentum_persistence',
    
    # Factory function
    'create_momentum_strategy'
]

# Module metadata
__version__ = "1.0.0"
__author__ = "Algorithmic Trading System"
__description__ = "Comprehensive momentum-based trading strategies"

# Default configurations
DEFAULT_TREND_CONFIG = {
    'short_ma_period': 10,
    'long_ma_period': 20,
    'macd_fast': 12,
    'macd_slow': 26,
    'macd_signal': 9,
    'adx_period': 14,
    'adx_threshold': 25,
    'trend_confirmation_periods': 3
}

DEFAULT_MOMENTUM_CONFIG = {
    'momentum_period': 14,
    'breakout_threshold': 2.0,
    'volume_confirmation': True,
    'min_volume_ratio': 1.5,
    'persistence_threshold': 0.6,
    'risk_adjustment': True
}

DEFAULT_OSCILLATOR_CONFIG = {
    'rsi_period': 14,
    'rsi_overbought': 70,
    'rsi_oversold': 30,
    'stoch_k_period': 14,
    'stoch_d_period': 3,
    'stoch_overbought': 80,
    'stoch_oversold': 20,
    'divergence_lookback': 20
}

# Factory function for creating momentum strategies
def create_momentum_strategy(strategy_type: str, config: Dict[str, Any]) -> Optional[Any]:
    """Factory function to create momentum strategies
    
    Args:
        strategy_type: Type of momentum strategy to create
        config: Strategy configuration parameters
        
    Returns:
        Momentum strategy instance or None if type not found
    """
    strategy_map = {
        'ma_trend': MovingAverageTrendStrategy,
        'macd_trend': MACDTrendStrategy,
        'adx_trend': ADXTrendStrategy,
        'price_momentum': PriceMomentumBreakoutStrategy,
        'volume_momentum': VolumeMomentumBreakoutStrategy,
        'volatility_momentum': VolatilityMomentumBreakoutStrategy,
        'rsi_momentum': RSIMomentumStrategy,
        'stochastic_momentum': StochasticMomentumStrategy
    }
    
    strategy_class = strategy_map.get(strategy_type)
    if strategy_class:
        return strategy_class(config)
    
    return None

# Initialize logging
logger = logging.getLogger(__name__)
logger.info("Momentum Strategy Module initialized")
logger.info(f"Available strategies: {list(create_momentum_strategy.__annotations__.keys()) if hasattr(create_momentum_strategy, '__annotations__') else 'Multiple types available'}")