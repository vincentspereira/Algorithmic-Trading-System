"""Arbitrage & Statistical Strategies Module

This module implements sophisticated arbitrage and statistical trading strategies
that exploit market inefficiencies and statistical relationships between assets.

Features:
- Index Arbitrage: ETF vs underlying basket arbitrage
- Volatility Arbitrage: Implied vs realized volatility strategies
- Multi-Factor Models: Statistical factor-based strategies
- Pairs Trading: Statistical arbitrage between correlated assets
- Mean Reversion: Statistical mean reversion strategies
- Cointegration Analysis: Long-term statistical relationships
- Risk-neutral pricing and hedging strategies

Architecture:
- Follows the 5-Pillar Architecture principles
- Event-driven signal generation
- Real-time statistical analysis
- Multi-asset correlation monitoring
- Advanced risk management integration

Components:
- Index arbitrage strategies and basket tracking
- Volatility surface analysis and arbitrage detection
- Multi-factor model construction and signal generation
- Statistical relationship monitoring and exploitation
- Risk-neutral hedging and position management
"""

import logging
from typing import Dict, List, Optional, Any

# Import from index_arbitrage.py
from .index_arbitrage import (
    IndexArbitrageType,
    ArbitrageOpportunity,
    BasketComponent,
    IndexArbitrageAnalyzer,
    IndexArbitrageStrategy,
    ETFArbitrageStrategy,
    BasketArbitrageStrategy,
    calculate_tracking_error,
    detect_arbitrage_opportunity,
    calculate_basket_value
)

# Import from volatility_arbitrage.py
from .volatility_arbitrage import (
    VolatilityArbitrageType,
    VolatilitySurface,
    VolatilityOpportunity,
    VolatilityAnalyzer,
    VolatilityArbitrageStrategy,
    ImpliedRealizedArbitrageStrategy,
    VolatilitySurfaceArbitrageStrategy,
    calculate_implied_volatility,
    calculate_realized_volatility,
    detect_volatility_mispricing
)

# Import from multi_factor_models.py
from .multi_factor_models import (
    # Enums
    FactorType,
    
    # Data structures
    FactorExposure,
    FactorModel,
    
    # Analyzers
    FactorAnalyzer,
    
    # Strategies
    MultiFactorStrategy,
    FamaFrenchStrategy,
    MomentumFactorStrategy,
    QualityFactorStrategy,
    
    # Utility functions
    calculate_factor_loadings,
    construct_factor_portfolio,
    calculate_factor_returns
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Module metadata
__version__ = "1.0.0"
__author__ = "Algorithmic Trading System"
__description__ = "Arbitrage & Statistical Strategies Module"

# Default configuration
DEFAULT_CONFIG = {
    'index_arbitrage': {
        'min_arbitrage_threshold': 0.005,  # 0.5% minimum arbitrage opportunity
        'max_tracking_error': 0.02,       # 2% maximum tracking error
        'rebalance_frequency': '1H',       # Hourly rebalancing
        'transaction_costs': 0.001,        # 0.1% transaction costs
        'risk_limit': 0.1                  # 10% maximum position size
    },
    'volatility_arbitrage': {
        'min_vol_spread': 0.05,           # 5% minimum volatility spread
        'lookback_period': 30,            # 30-day realized volatility
        'hedge_ratio': 0.8,               # 80% hedge ratio
        'rebalance_frequency': '1D',       # Daily rebalancing
        'risk_limit': 0.05                # 5% maximum position size
    },
    'multi_factor': {
        'rebalance_frequency': '1M',       # Monthly rebalancing
        'min_factor_exposure': 0.1,       # 10% minimum factor exposure
        'max_factor_exposure': 0.3,       # 30% maximum factor exposure
        'risk_budget': 0.15,              # 15% risk budget
        'transaction_costs': 0.002        # 0.2% transaction costs
    }
}

# Export all components
__all__ = [
    # Enums
    'ArbitrageType',
    'IndexType',
    'VolatilityRegime',
    'FactorType',
    
    # Data structures
    'ArbitrageOpportunity',
    'IndexBasket',
    'VolatilitySurface',
    'FactorExposure',
    'FactorModel',
    
    # Analyzers
    'IndexArbitrageAnalyzer',
    'VolatilityAnalyzer',
    'FactorAnalyzer',
    
    # Strategies
    'IndexArbitrageStrategy',
    'VolatilityArbitrageStrategy',
    'MultiFactorStrategy',
    'FamaFrenchStrategy',
    'MomentumFactorStrategy',
    'QualityFactorStrategy',
    
    # Utility functions
    'calculate_tracking_error',
    'construct_replication_basket',
    'calculate_arbitrage_profit',
    'calculate_implied_volatility',
    'calculate_realized_volatility',
    'detect_volatility_arbitrage',
    'calculate_factor_loadings',
    'construct_factor_portfolio',
    'calculate_factor_returns',
    
    # Factory function
    'create_arbitrage_strategy'
]

def create_arbitrage_strategy(strategy_type: str, config: Dict[str, Any]) -> Any:
    """Factory function to create arbitrage strategies
    
    Args:
        strategy_type: Type of strategy to create
        config: Strategy configuration
        
    Returns:
        Configured strategy instance
        
    Raises:
        ValueError: If strategy type is not supported
    """
    try:
        from ..base_strategy import StrategyConfig
        
        # Convert dict config to StrategyConfig if needed
        if isinstance(config, dict):
            strategy_config = StrategyConfig(
                name=config.get('name', f'{strategy_type}_strategy'),
                symbols=config.get('symbols', []),
                parameters=config.get('parameters', {})
            )
        else:
            strategy_config = config
        
        # Create strategy based on type
        if strategy_type.lower() in ['index_arbitrage', 'index']:
            return IndexArbitrageStrategy(strategy_config)
        elif strategy_type.lower() in ['etf_arbitrage', 'etf']:
            return ETFArbitrageStrategy(strategy_config)
        elif strategy_type.lower() in ['basket_arbitrage', 'basket']:
            return BasketArbitrageStrategy(strategy_config)
        elif strategy_type.lower() in ['volatility_arbitrage', 'vol_arb']:
            return VolatilityArbitrageStrategy(strategy_config)
        elif strategy_type.lower() in ['implied_realized', 'iv_rv']:
            return ImpliedRealizedArbitrageStrategy(strategy_config)
        elif strategy_type.lower() in ['volatility_surface', 'vol_surface']:
            return VolatilitySurfaceArbitrageStrategy(strategy_config)
        elif strategy_type.lower() in ['multi_factor', 'factor']:
            return MultiFactorStrategy(strategy_config)
        elif strategy_type.lower() in ['fama_french', 'ff']:
            return FamaFrenchStrategy(strategy_config)
        elif strategy_type.lower() in ['momentum_factor', 'momentum']:
            return MomentumFactorStrategy(strategy_config)
        elif strategy_type.lower() in ['quality_factor', 'quality']:
            return QualityFactorStrategy(strategy_config)
        else:
            raise ValueError(f"Unsupported arbitrage strategy type: {strategy_type}")
            
    except Exception as e:
        logger.error(f"Error creating arbitrage strategy {strategy_type}: {e}")
        raise

# Initialize module
logger.info(f"Arbitrage & Statistical Strategies Module v{__version__} initialized")
logger.info(f"Available strategies: {len(__all__)} components")
logger.info("Module supports: Index Arbitrage, Volatility Arbitrage, Multi-Factor Models")