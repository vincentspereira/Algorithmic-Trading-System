"""Volatility Breakout Strategies Module

This module implements advanced volatility breakout trading strategies including:
- Range Breakout Strategies (Bollinger Bands, Donchian Channels, Keltner Channels)
- Volatility Expansion Strategies (ATR-based, Volume-weighted volatility)
- Volatility Contraction Strategies (Squeeze patterns, Low volatility breakouts)
- Adaptive Volatility Strategies (Dynamic threshold adjustment)
- Multi-timeframe Volatility Analysis
- Volume-confirmed Breakout Strategies

Key Features:
- Real-time volatility measurement and analysis
- Dynamic breakout threshold calculation
- Volume confirmation for breakout validation
- False breakout filtering mechanisms
- Multi-asset class volatility analysis
- Risk-adjusted position sizing based on volatility
- Volatility regime detection and adaptation

Architecture:
Follows the 5-Pillar Architecture with sophisticated volatility measurement
engines, breakout detection systems, and adaptive threshold mechanisms.

Components:
- Range Breakout Strategies: Traditional range-based breakout detection
- Volatility Expansion Strategies: Momentum-based volatility breakouts
- Volatility Contraction Strategies: Mean reversion after low volatility
- Adaptive Volatility Strategies: Dynamic parameter adjustment
- Volume Confirmation Systems: Enhanced breakout validation
- Multi-timeframe Analysis: Cross-timeframe volatility confirmation
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

# Import core components
from .range_breakout_strategies import (
    RangeBreakoutStrategy, BollingerBandBreakoutStrategy,
    DonchianChannelBreakoutStrategy, KeltnerChannelBreakoutStrategy,
    VolatilityAnalyzer, VolatilityRange, BreakoutSignal,
    VolatilityMeasure, BreakoutDirection, BreakoutType, VolumeConfirmation,
    calculate_bollinger_bands, calculate_donchian_channels, calculate_keltner_channels
)
from .volatility_expansion_strategies import (
    VolatilityExpansionStrategy, VolatilityAnalysisEngine,
    VolatilityMetrics, VolatilitySqueeze, VolatilityExpansion,
    VolatilityRegime, SqueezeType, ExpansionPhase, ExpansionDirection,
    calculate_volatility_metrics, detect_volatility_squeeze, classify_volatility_regime
)

from .volatility_contraction_strategies import (
    ContractionType, SqueezeType, ContractionState,
    VolatilityContraction, ContractionSignal, VolatilityContractionAnalyzer,
    VolatilityContractionStrategy, VolatilitySqueezeStrategy, LowVolatilityBreakoutStrategy,
    calculate_volatility_squeeze, detect_low_volatility_periods
)

from .multi_timeframe_volatility import (
    TimeframeVolatility, VolatilityAlignment, TimeframeSignal,
    MultiTimeframeVolatilityAnalyzer, MultiTimeframeVolatilityStrategy,
    calculate_multi_timeframe_volatility, align_volatility_signals
)

# Module metadata
__version__ = "1.0.0"
__author__ = "Algorithmic Trading System"
__description__ = "Advanced volatility breakout trading strategies"

# Configure logging
logger = logging.getLogger(__name__)

# Export all components
__all__ = [
    # Enums and Data Classes
    'VolatilityMeasure', 'BreakoutDirection', 'BreakoutType', 'VolumeConfirmation',
    'VolatilityRegime', 'SqueezeType', 'ExpansionPhase', 'ExpansionDirection',
    'ContractionType', 'ContractionState',
    'TimeframeVolatility', 'VolatilityAlignment',
    
    # Data Structures
    'VolatilityRange', 'BreakoutSignal', 'VolatilityMetrics', 'VolatilitySqueeze', 'VolatilityExpansion',
    'VolatilityContraction', 'ContractionSignal', 'TimeframeSignal',
    
    # Analyzers
    'VolatilityAnalyzer', 'VolatilityAnalysisEngine', 
    'VolatilityContractionAnalyzer', 'MultiTimeframeVolatilityAnalyzer',
    
    # Range Breakout Strategies
    'RangeBreakoutStrategy', 'BollingerBandBreakoutStrategy',
    'DonchianChannelBreakoutStrategy', 'KeltnerChannelBreakoutStrategy',
    
    # Volatility Expansion Strategies
    'VolatilityExpansionStrategy', 'ATRBreakoutStrategy', 
    'VolumeWeightedVolatilityStrategy', 'AdaptiveVolatilityStrategy',
    
    # Volatility Contraction Strategies
    'VolatilityContractionStrategy', 'VolatilitySqueezeStrategy', 
    'LowVolatilityBreakoutStrategy',
    
    # Multi-timeframe Strategies
    'MultiTimeframeVolatilityStrategy',
    
    # Utility Functions
    'calculate_bollinger_bands', 'calculate_donchian_channels', 'calculate_keltner_channels',
    'calculate_volatility_metrics', 'detect_volatility_squeeze', 'classify_volatility_regime',
    'calculate_volatility_squeeze', 'detect_low_volatility_periods',
    'calculate_multi_timeframe_volatility', 'align_volatility_signals'
]

# Default configuration for volatility breakout strategies
DEFAULT_VOLATILITY_CONFIG = {
    'range_breakout': {
        'bollinger_period': 20,
        'bollinger_std_dev': 2.0,
        'donchian_period': 20,
        'keltner_period': 20,
        'keltner_multiplier': 2.0,
        'volume_confirmation': True,
        'min_volume_ratio': 1.5
    },
    'volatility_expansion': {
        'atr_period': 14,
        'atr_multiplier': 2.0,
        'expansion_threshold': 1.5,
        'volume_weight': True,
        'adaptive_threshold': True,
        'lookback_period': 50
    },
    'volatility_contraction': {
        'squeeze_period': 20,
        'squeeze_threshold': 0.5,
        'low_vol_percentile': 20,
        'breakout_multiplier': 1.5,
        'confirmation_period': 3
    },
    'multi_timeframe': {
        'timeframes': ['1m', '5m', '15m', '1h', '4h', '1d'],
        'alignment_threshold': 0.7,
        'weight_distribution': [0.1, 0.15, 0.2, 0.25, 0.2, 0.1]
    }
}

def get_default_config() -> Dict[str, Any]:
    """Get default configuration for volatility breakout strategies"""
    return DEFAULT_VOLATILITY_CONFIG.copy()

def create_volatility_strategy(strategy_type: str, config: Optional[Dict] = None) -> Any:
    """Factory function to create volatility breakout strategies
    
    Args:
        strategy_type: Type of strategy ('range_breakout', 'volatility_expansion', etc.)
        config: Optional configuration dictionary
        
    Returns:
        Configured volatility strategy instance
    """
    if config is None:
        config = get_default_config()
    
    strategy_map = {
        'bollinger_breakout': BollingerBandBreakoutStrategy,
        'donchian_breakout': DonchianChannelBreakoutStrategy,
        'keltner_breakout': KeltnerChannelBreakoutStrategy,
        'atr_breakout': ATRBreakoutStrategy,
        'volume_weighted_volatility': VolumeWeightedVolatilityStrategy,
        'adaptive_volatility': AdaptiveVolatilityStrategy,
        'volatility_squeeze': VolatilitySqueezeStrategy,
        'low_volatility_breakout': LowVolatilityBreakoutStrategy,
        'multi_timeframe_volatility': MultiTimeframeVolatilityStrategy
    }
    
    if strategy_type not in strategy_map:
        raise ValueError(f"Unknown strategy type: {strategy_type}")
    
    strategy_class = strategy_map[strategy_type]
    
    # Create strategy config based on type
    from ..pairs_trading_strategies import StrategyConfig, StrategyType
    
    strategy_config = StrategyConfig(
        strategy_id=f"{strategy_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        strategy_type=StrategyType.VOLATILITY_BREAKOUT,
        symbols=config.get('symbols', ['SPY']),
        parameters=config.get(strategy_type.split('_')[0], {}),
        risk_parameters=config.get('risk_parameters', {
            'max_position_size': 0.1,
            'stop_loss_pct': 0.02,
            'take_profit_pct': 0.04
        })
    )
    
    return strategy_class(strategy_config)

# Module initialization
logger.info(f"Volatility Breakout Strategies Module v{__version__} initialized")
logger.info(f"Available strategies: {list(DEFAULT_VOLATILITY_CONFIG.keys())}")