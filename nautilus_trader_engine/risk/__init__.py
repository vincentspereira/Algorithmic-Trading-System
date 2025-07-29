"""
Risk Management Module
Comprehensive risk management tools including VaR calculation, portfolio optimization,
stress testing, and dynamic hedging strategies
"""

from .var_engine import (
    VaREngine, VaRMethod, ConfidenceLevel, TimeHorizon,
    VaRResult, VaRBacktestResult, PortfolioPosition, GARCHParameters,
    VaRCalculator, HistoricalVaRCalculator, ParametricVaRCalculator,
    MonteCarloVaRCalculator, GARCHVaRCalculator, VaRBacktester,
    initialize_var_engine, start_var_engine, get_var_engine, stop_var_engine
)

from .portfolio_optimizer import (
    PortfolioOptimizationEngine, OptimizationMethod, ObjectiveFunction, RiskModel,
    Asset, OptimizationConstraints, BlackLittermanInputs, OptimizationResult,
    PortfolioOptimizer, MeanVarianceOptimizer, BlackLittermanOptimizer, RiskParityOptimizer, EqualWeightOptimizer,
    initialize_optimization_engine, start_optimization_engine, get_optimization_engine, stop_optimization_engine
)

__all__ = [
    # VaR Engine
    'VaREngine',
    'VaRMethod',
    'ConfidenceLevel',
    'TimeHorizon',
    'VaRResult',
    'VaRBacktestResult',
    'PortfolioPosition',
    'GARCHParameters',
    'VaRCalculator',
    'HistoricalVaRCalculator',
    'ParametricVaRCalculator',
    'MonteCarloVaRCalculator',
    'GARCHVaRCalculator',
    'VaRBacktester',
    'initialize_var_engine',
    'start_var_engine',
    'get_var_engine',
    'stop_var_engine',
    
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
    'stop_optimization_engine'
]