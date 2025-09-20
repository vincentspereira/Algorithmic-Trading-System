"""5-Pillar Strategy Architecture - Individual Pillars

This module contains the individual pillar implementations of the 5-Pillar Architecture.
Each pillar represents a specialized component of the comprehensive trading framework.

Pillars:
========
1. Signal Generation: Multi-timeframe technical analysis and signal generation
2. Market Regime Detection: ML-powered market state classification
3. Risk Management: Dynamic position sizing and portfolio risk management
4. Execution Intent: Smart order execution algorithms (TWAP, VWAP, etc.)
5. Performance Analytics: Comprehensive performance measurement and attribution

Architecture Benefits:
=====================
- Modular design with clear separation of concerns
- Independent pillar development and testing
- Coordinated decision-making through PillarCoordinator
- Scalable and maintainable codebase
- Enterprise-grade strategy development framework

Usage:
======
from nautilus_trader_engine.strategies.architecture.pillars import (
    SignalGenerator,
    MarketRegimeDetector,
    RiskManager,
    ExecutionIntentManager,
    PerformanceAnalyticsManager
)

# Initialize individual pillars
signal_gen = SignalGenerator()
regime_detector = MarketRegimeDetector()
risk_manager = RiskManager()
execution_manager = ExecutionIntentManager()
performance_manager = PerformanceAnalyticsManager()

# Use with PillarCoordinator for full integration
from nautilus_trader_engine.strategies.architecture.coordinator import PillarCoordinator
coordinator = PillarCoordinator(
    signal_generator=signal_gen,
    regime_detector=regime_detector,
    risk_manager=risk_manager,
    execution_manager=execution_manager,
    performance_manager=performance_manager
)
"""

try:
    from .signal_generation import SignalGenerator
    from .market_regime_detection import MarketRegimeDetector
    from .risk_management import RiskManager
    from .execution_intent import ExecutionIntentManager
    from .performance_analytics import PerformanceAnalyticsManager
except ImportError:
    # Handle missing dependencies gracefully during development
    pass

__all__ = [
    'SignalGenerator',
    'MarketRegimeDetector',
    'RiskManager',
    'ExecutionIntentManager',
    'PerformanceAnalyticsManager'
]