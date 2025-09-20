"""Unified Strategy Architecture for Algorithmic Trading System

This module provides a comprehensive, organized structure for all trading strategies,
indicators, execution frameworks, and supporting components. The architecture follows
a modular design with clear separation of concerns and consistent naming conventions.

Directory Structure:
==================

strategies/
├── core/                    # Core strategy implementations by category
│   ├── mean_reversion/      # Mean reversion strategies (RSI, Bollinger, etc.)
│   ├── trend_following/     # Trend following strategies (MA crossover, momentum)
│   ├── volatility/          # Volatility-based strategies (breakout, VIX)
│   ├── multi_asset/         # Multi-asset and cross-asset strategies
│   └── machine_learning/    # ML/AI-powered strategies
├── templates/               # Strategy templates and base classes
├── execution/               # Strategy execution framework
│   ├── backtesting/         # Backtesting engine and analysis
│   ├── live_trading/        # Live trading execution
│   └── validation/          # Strategy validation and compliance
├── architecture/            # 5-Pillar Architecture framework
│   ├── pillars/             # Individual pillar implementations
│   ├── coordinator/         # Pillar coordination and orchestration
│   └── framework/           # Base framework and factory classes
├── indicators/              # Technical analysis library
│   ├── traditional/         # Traditional technical indicators
│   ├── volume_weighted/     # Volume-weighted indicators
│   ├── patterns/            # Pattern recognition (candlestick, chart)
│   └── custom/              # Proprietary and composite indicators
├── research/                # Strategy research and development
│   ├── backtests/           # Historical backtesting results
│   ├── analysis/            # Performance and statistical analysis
│   ├── optimization/        # Parameter optimization studies
│   └── experiments/         # Experimental strategies and ideas
├── integration/             # External system integrations
│   ├── brokers/             # Broker-specific integrations
│   ├── data_feeds/          # Data feed integrations
│   └── ai_assistant/        # AI assistant integrations
└── documentation/           # Comprehensive documentation
    ├── performance_reports/ # Strategy performance reports
    └── api_documentation/   # API and usage documentation

Key Features:
=============

1. **5-Pillar Architecture**: Advanced strategy framework with:
   - Signal Generation: Multi-timeframe technical analysis
   - Market Regime Detection: ML-powered market state classification
   - Risk Management: Dynamic position sizing and portfolio risk
   - Execution Intent: Smart order execution algorithms
   - Performance Analytics: Comprehensive performance measurement

2. **Modular Design**: Clear separation of concerns with:
   - Strategy categorization by trading approach
   - Reusable components and templates
   - Pluggable execution frameworks
   - Extensible indicator library

3. **Enterprise Features**:
   - Multi-asset class support (stocks, futures, options, forex, crypto)
   - Real-time and historical backtesting
   - Advanced risk management and compliance
   - Performance attribution and analytics
   - AI-powered strategy generation and optimization

4. **Integration Ready**:
   - NautilusTrader engine compatibility
   - Interactive Brokers integration
   - Multiple data feed support with fallback
   - Kafka event streaming for real-time execution

Usage Examples:
===============

# Import core strategy categories
from nautilus_trader_engine.strategies.core.mean_reversion import RSI2MeanReversionStrategy
from nautilus_trader_engine.strategies.core.trend_following import MovingAverageCrossoverStrategy
from nautilus_trader_engine.strategies.core.machine_learning import RLStrategy

# Import 5-Pillar Architecture
from nautilus_trader_engine.strategies.architecture.coordinator import PillarCoordinator
from nautilus_trader_engine.strategies.architecture.pillars import (
    SignalGenerator,
    MarketRegimeDetector,
    RiskManager,
    ExecutionIntentManager,
    PerformanceAnalyticsManager
)

# Import technical indicators
from nautilus_trader_engine.indicators.traditional import (
    MomentumIndicators,
    TrendIndicators,
    VolatilityIndicators
)
from nautilus_trader_engine.indicators.volume_weighted import VolumeWeightedIndicators
from nautilus_trader_engine.indicators.patterns import CandlestickPatterns

# Import execution framework
from nautilus_trader_engine.strategies.execution.backtesting import BacktestingEngine
from nautilus_trader_engine.strategies.execution.live_trading import RuntimeEngine
from nautilus_trader_engine.strategies.execution.validation import StrategyValidator

# Import templates for custom development
from nautilus_trader_engine.strategies.templates import BaseStrategyTemplate
from nautilus_trader_engine.strategies.architecture.framework import StrategyFactory

Development Guidelines:
======================

1. **Strategy Development**:
   - Use appropriate category directory (mean_reversion, trend_following, etc.)
   - Follow naming convention: {StrategyName}Strategy
   - Implement comprehensive docstrings and type hints
   - Include unit tests and validation

2. **Indicator Development**:
   - Place in appropriate subcategory (traditional, volume_weighted, etc.)
   - Follow naming convention: {IndicatorName}Indicator
   - Implement both single-value and vectorized calculations
   - Include performance benchmarks

3. **Integration Development**:
   - Use integration directory for external system connections
   - Implement proper error handling and fallback mechanisms
   - Follow async/await patterns for non-blocking operations
   - Include comprehensive logging and monitoring

4. **Research and Experimentation**:
   - Use research directory for experimental work
   - Document all assumptions and methodologies
   - Include statistical significance testing
   - Maintain reproducible results with seed management

Performance Considerations:
==========================

- All indicators support vectorized operations using NumPy
- Strategies implement efficient data structures for real-time execution
- Backtesting engine supports parallel processing for parameter optimization
- Memory-efficient data handling for large historical datasets
- Optimized execution paths for low-latency trading

Compliance and Risk Management:
==============================

- Built-in risk management with position sizing and exposure limits
- Compliance checking for regulatory requirements
- Audit trails for all trading decisions and executions
- Performance monitoring and alerting
- Comprehensive logging for debugging and analysis

For detailed documentation, see strategies/documentation/
For API reference, see strategies/documentation/api_documentation/
For performance reports, see strategies/documentation/performance_reports/
"""

# Version information
__version__ = "1.0.0"
__author__ = "Algorithmic Trading System Team"
__email__ = "support@algo-trading-system.com"
__status__ = "Production"

# Import key components for easy access
try:
    # Import base strategy components
    from .core.base_strategy import (
        BaseStrategy,
        StrategyConfig,
        Signal,
        SignalType,
        Position,
        PositionSide,
        OrderType
    )
    
    from .core.base_institutional_strategy import (
        BaseInstitutionalStrategy
    )
    from .core.base_strategy import (
        create_signal,
        validate_ohlcv_data
    )
    
    from .core.base_strategy import (
        StrategyManager,
        SimpleMovingAverageStrategy
    )
    
    # Import strategy management components
    from .core.strategy_manager import (
        StrategyManager as UnifiedStrategyManager,
        StrategyStatus,
        StrategyCategory,
        AlertLevel,
        StrategyMetrics,
        StrategyAlert,
        StrategyRegistration,
        strategy_manager,
        register_strategy,
        start_strategy,
        execute_strategy,
        get_strategy_status,
        get_all_strategies
    )

    # Import only what exists from strategy_factory
    try:
        from .core.strategy_factory import (
            StrategyFactory,
            BaseStrategyFactory,
            strategy_factory,
            create_strategy
        )
    except ImportError:
        pass
    
    # Core strategy categories - only import what exists
    # Note: Removed imports from non-existent modules
    
    # Strategy categories that exist
    from .momentum import *
    from .mean_reversion import *
    from .pairs_trading import *
    from .arbitrage import *
    from .machine_learning import *
    from .volatility_breakout import *
    
    # Execution framework
    from .execution import *
    
    # Templates
    from .templates import *
    
    # Utils
    from .utils import *
    
except ImportError as e:
    # Graceful handling during initial setup
    import warnings
    warnings.warn(f"Some strategy components not yet available: {e}")

# Export main components
__all__ = [
    # Base strategy components
    'BaseStrategy',
    'StrategyConfig',
    'Signal',
    'SignalType',
    'Position',
    'PositionSide',
    'OrderType',
    'StrategyManager',
    'SimpleMovingAverageStrategy',
    'BaseInstitutionalStrategy',
    'AugmentedMomentumStrategy',
    'create_signal',
    'validate_ohlcv_data',
    
    # Strategy Management
    'UnifiedStrategyManager',
    'StrategyStatus',
    'StrategyCategory',
    'AlertLevel',
    'StrategyMetrics',
    'StrategyAlert',
    'StrategyRegistration',
    'strategy_manager',
    'register_strategy',
    'start_strategy',
    'execute_strategy',
    'get_strategy_status',
    'get_all_strategies',
    
    # Strategy Factory
    'StrategyFactory',
    'BaseStrategyFactory',
    'PairsStrategyFactory',
    'MLStrategyFactory',
    'StrategyTemplate',
    'StrategyBlueprint',
    'strategy_factory',
    'create_strategy',
    'create_from_template',
    'list_available_strategies',
    'get_strategy_info',
    
    # Core categories
    'mean_reversion',
    'trend_following', 
    'volatility',
    'multi_asset',
    'machine_learning',
    
    # Architecture components
    'PillarCoordinator',
    'SignalGenerator',
    'MarketRegimeDetector',
    'RiskManager', 
    'ExecutionIntentManager',
    'PerformanceAnalyticsManager',
    
    # Execution framework
    'backtesting',
    'live_trading',
    'validation',
    
    # Technical analysis
    'indicators',
    'patterns',
    
    # Development tools
    'templates',
    'framework',
    'research',
    'integration'
]

# Configuration
STRATEGY_CONFIG = {
    'default_timeframe': '1m',
    'max_lookback_periods': 1000,
    'default_risk_per_trade': 0.02,
    'max_portfolio_risk': 0.20,
    'enable_ml_features': True,
    'enable_volume_weighting': True,
    'enable_pattern_recognition': True,
    'performance_update_frequency': '1s',
    'logging_level': 'INFO'
}

# Utility functions
def get_strategy_categories():
    """Get list of available strategy categories."""
    return ['mean_reversion', 'trend_following', 'volatility', 'multi_asset', 'machine_learning']

def get_indicator_categories():
    """Get list of available indicator categories."""
    return ['traditional', 'volume_weighted', 'patterns', 'custom']

def get_execution_modes():
    """Get list of available execution modes."""
    return ['backtesting', 'live_trading', 'paper_trading', 'validation']

def validate_strategy_config(config):
    """Validate strategy configuration parameters."""
    required_keys = ['timeframe', 'lookback_periods', 'risk_per_trade']
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required configuration key: {key}")
    return True

# Initialize logging
import logging
logging.getLogger(__name__).addHandler(logging.NullHandler())