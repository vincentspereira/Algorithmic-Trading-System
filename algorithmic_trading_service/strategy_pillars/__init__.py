"""5-Pillar Strategy Architecture

This module implements the institutional-grade 5-Pillar Strategy Architecture:
1. Signal Generation - Multi-timeframe technical analysis and pattern recognition
2. Market Regime Detection - ML-powered market state classification
3. Risk Management - Dynamic position sizing and risk controls
4. Execution Intent - Decoupled execution logic with smart order routing
5. Performance Analytics - Real-time strategy performance monitoring

Author: Vincent S. Pereira
Version: 1.0.0
"""

from .signal_generation import SignalGenerator, SignalStrength, MultiTimeframeSignal
from .market_regime_detection import MarketRegimeDetector, MarketRegime, RegimeFeatures
from .risk_management import RiskManager, PositionSizer, RiskMetrics
from .execution_intent import ExecutionIntent, ExecutionManager, OrderIntent
from .performance_analytics import PerformanceAnalyzer, StrategyMetrics, RealTimeAnalytics
from .pillar_coordinator import PillarCoordinator, StrategyDecision

__all__ = [
    # Signal Generation
    'SignalGenerator',
    'SignalStrength', 
    'MultiTimeframeSignal',
    
    # Market Regime Detection
    'MarketRegimeDetector',
    'MarketRegime',
    'RegimeFeatures',
    
    # Risk Management
    'RiskManager',
    'PositionSizer',
    'RiskMetrics',
    
    # Execution Intent
    'ExecutionIntent',
    'ExecutionManager',
    'OrderIntent',
    
    # Performance Analytics
    'PerformanceAnalyzer',
    'StrategyMetrics',
    'RealTimeAnalytics',
    
    # Coordination
    'PillarCoordinator',
    'StrategyDecision'
]