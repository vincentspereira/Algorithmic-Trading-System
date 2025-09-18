#!/usr/bin/env python3
"""Comprehensive Strategy Backtesting Framework

This module provides a comprehensive backtesting framework with advanced
performance analytics, risk analysis, and scenario testing capabilities.

Features:
- Event-driven backtesting engine with realistic execution simulation
- Comprehensive performance metrics and attribution analysis
- Advanced risk analytics including VaR, stress testing, and drawdown analysis
- Monte Carlo simulations and scenario analysis
- Multi-strategy backtesting with portfolio-level analytics
- Transaction cost modeling and slippage simulation
- Real-time performance monitoring and reporting

Architecture:
- BacktestEngine: Core event-driven backtesting engine
- PerformanceAnalyzer: Comprehensive performance metrics calculation
- RiskAnalyzer: Advanced risk analysis and VaR calculations
- ScenarioAnalyzer: Monte Carlo simulations and scenario testing
- Integration with 5-Pillar Architecture for seamless strategy testing

Components:
- Event-driven simulation with realistic market conditions
- Multi-asset class support (equities, futures, options, forex, crypto)
- Advanced order types and execution algorithms
- Portfolio optimization and rebalancing simulation
- Benchmark comparison and relative performance analysis
- Risk attribution and factor analysis
- Stress testing and scenario analysis
- Performance reporting and visualization

Integration:
- Seamless integration with strategy modules
- Real-time data feed integration
- Risk management system integration
- Portfolio management integration
- Web interface for interactive backtesting
"""

__version__ = "2.0.0"
__author__ = "Algorithmic Trading System"

# Core backtesting components
from .backtest_engine import (
    BacktestEngine,
    BacktestConfig,
    BacktestState,
    BacktestMode,
    BacktestResults
)

from .performance_analyzer import (
    PerformanceAnalyzer,
    PerformanceMetrics,
    RollingMetrics,
    BenchmarkComparison,
    PerformanceReport
)

from .risk_analyzer import (
    RiskAnalyzer,
    RiskMetrics,
    VaRAnalysis,
    StressTestResults,
    DrawdownAnalysis,
    RiskAttribution
)

from .scenario_analyzer import (
    ScenarioAnalyzer,
    ScenarioConfig,
    MonteCarloResults,
    HistoricalScenario,
    ScenarioAnalysisResults
)

# Legacy component for backward compatibility
# from .indicator_backtest import BacktestExecutor  # Commented out due to nautilus_trader dependency

# Export all components
__all__ = [
    # Core engine
    "BacktestEngine",
    "BacktestConfig",
    "BacktestState",
    "BacktestMode",
    "BacktestResults",
    
    # Performance analysis
    "PerformanceAnalyzer",
    "PerformanceMetrics",
    "RollingMetrics",
    "BenchmarkComparison",
    "PerformanceReport",
    
    # Risk analysis
    "RiskAnalyzer",
    "RiskMetrics",
    "VaRAnalysis",
    "StressTestResults",
    "DrawdownAnalysis",
    "RiskAttribution",
    
    # Scenario analysis
    "ScenarioAnalyzer",
    "ScenarioConfig",
    "MonteCarloResults",
    "HistoricalScenario",
    "ScenarioAnalysisResults",
    
    # Legacy
    # "BacktestExecutor"  # Commented out due to nautilus_trader dependency
]

# Default configuration
DEFAULT_BACKTEST_CONFIG = {
    'initial_capital': 100000,
    'commission': 0.001,
    'slippage': 0.0005,
    'benchmark': 'SPY',
    'risk_free_rate': 0.02,
    'confidence_levels': [0.95, 0.99],
    'monte_carlo_simulations': 10000
}

# Factory functions
def create_backtest_engine(config: dict = None) -> BacktestEngine:
    """Create a configured backtest engine
    
    Args:
        config: Backtest configuration dictionary
        
    Returns:
        Configured BacktestEngine instance
    """
    from .backtest_engine import BacktestConfig
    
    # Merge with defaults
    final_config = DEFAULT_BACKTEST_CONFIG.copy()
    if config:
        final_config.update(config)
    
    backtest_config = BacktestConfig(**final_config)
    return BacktestEngine(backtest_config)

def create_performance_analyzer(config: dict = None) -> PerformanceAnalyzer:
    """Create a configured performance analyzer
    
    Args:
        config: Performance analysis configuration
        
    Returns:
        Configured PerformanceAnalyzer instance
    """
    return PerformanceAnalyzer(config)

def create_risk_analyzer(config: dict = None) -> RiskAnalyzer:
    """Create a configured risk analyzer
    
    Args:
        config: Risk analysis configuration
        
    Returns:
        Configured RiskAnalyzer instance
    """
    return RiskAnalyzer(config)

def create_scenario_analyzer(config: dict = None) -> ScenarioAnalyzer:
    """Create a configured scenario analyzer
    
    Args:
        config: Scenario analysis configuration
        
    Returns:
        Configured ScenarioAnalyzer instance
    """
    from .scenario_analyzer import ScenarioConfig
    
    if config:
        scenario_config = ScenarioConfig(**config)
    else:
        scenario_config = ScenarioConfig()
    
    return ScenarioAnalyzer(scenario_config)

def run_comprehensive_backtest(
    strategy,
    data,
    config: dict = None,
    include_risk_analysis: bool = True,
    include_scenario_analysis: bool = True
) -> dict:
    """Run comprehensive backtest with all analytics
    
    Args:
        strategy: Trading strategy to backtest
        data: Market data for backtesting
        config: Backtest configuration
        include_risk_analysis: Whether to include risk analysis
        include_scenario_analysis: Whether to include scenario analysis
        
    Returns:
        Dictionary containing all backtest results
    """
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Create analyzers
        engine = create_backtest_engine(config)
        performance_analyzer = create_performance_analyzer(config)
        
        # Run backtest
        logger.info("Running backtest...")
        engine.add_strategy(strategy)
        engine.load_data(data)
        backtest_results = engine.run_backtest()
        
        # Analyze performance
        logger.info("Analyzing performance...")
        performance_results = performance_analyzer.analyze_performance(
            backtest_results.returns,
            backtest_results.positions,
            backtest_results.trades
        )
        
        results = {
            'backtest': backtest_results,
            'performance': performance_results
        }
        
        # Risk analysis
        if include_risk_analysis:
            logger.info("Analyzing risk...")
            risk_analyzer = create_risk_analyzer(config)
            risk_results = risk_analyzer.analyze_risk(
                backtest_results.returns,
                backtest_results.positions
            )
            results['risk'] = risk_results
        
        # Scenario analysis
        if include_scenario_analysis:
            logger.info("Running scenario analysis...")
            scenario_analyzer = create_scenario_analyzer(config)
            scenario_results = scenario_analyzer.analyze_scenarios(
                backtest_results.returns,
                backtest_results.positions
            )
            results['scenarios'] = scenario_results
        
        logger.info("Comprehensive backtest completed successfully")
        return results
        
    except Exception as e:
        logger.error(f"Error in comprehensive backtest: {e}")
        raise

# Initialize logging
import logging
logging.getLogger(__name__).info("Comprehensive backtesting framework initialized")