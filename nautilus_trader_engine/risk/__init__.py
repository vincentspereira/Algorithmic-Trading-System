"""
Risk Management Module
Comprehensive risk management tools including VaR calculation, portfolio optimization,
stress testing, and dynamic hedging strategies
"""

from .var_engine import (
    VaREngine, VaRMethod, ConfidenceLevel,
    VaRResult, BacktestResult,
    create_var_engine as initialize_var_engine
)

from .portfolio_optimizer import (
    PortfolioOptimizationEngine, OptimizationMethod, ObjectiveFunction, RiskModel,
    Asset, OptimizationConstraints, BlackLittermanInputs, OptimizationResult,
    PortfolioOptimizer, MeanVarianceOptimizer, BlackLittermanOptimizer, RiskParityOptimizer, EqualWeightOptimizer,
    initialize_optimization_engine, start_optimization_engine, get_optimization_engine, stop_optimization_engine
)

from .multi_asset_risk_manager import (
    MultiAssetRiskManager, VaRResult, ExposureResult, LimitCheckResult
)

from .realtime_monitor import RealtimeRiskMonitor

__all__ = [
    # VaR Engine
    'VaREngine',
    'VaRMethod',
    'ConfidenceLevel',
    'VaRResult',
    
    'initialize_var_engine',
    
    # Portfolio Optimization Engine
    'PortfolioOptimizationEngine',
    'OptimizationMethod',
    'ObjectiveFunction',
    'RiskModel',
    'Asset',
    'OptimizationConstraints',
    'BlackLittermanInputs',
    'OptimizationResult',
    'PortfolioOptimizer',
    'MeanVarianceOptimizer',
    'BlackLittermanOptimizer',
    'RiskParityOptimizer',
    'EqualWeightOptimizer',
    'initialize_optimization_engine',
    'start_optimization_engine',
    'get_optimization_engine',
    'stop_optimization_engine',
    
    # Multi-Asset Risk Management
    'MultiAssetRiskManager',
    'VaRResult',
    'ExposureResult',
    'LimitCheckResult',
    
    # Real-time Risk Monitoring
    'RealtimeRiskMonitor'
]