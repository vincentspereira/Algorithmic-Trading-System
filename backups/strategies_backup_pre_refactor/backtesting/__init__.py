"""Backtesting Framework

Comprehensive backtesting and performance analytics framework with institutional-grade
metrics, risk analysis, and reporting capabilities.

Components:
- BacktestEngine: Core backtesting engine with event-driven simulation
- PerformanceAnalyzer: Institutional-grade performance metrics calculation
- RiskAnalyzer: Comprehensive risk analysis and VaR calculations
- ReportGenerator: Professional reporting with visualizations
- DataManager: Historical data management and preprocessing
- PortfolioSimulator: Portfolio-level backtesting with multiple strategies

Key Features:
- Event-driven backtesting simulation
- Transaction cost modeling
- Slippage and market impact simulation
- Multi-asset class support
- Regime-aware performance analysis
- Monte Carlo simulation
- Walk-forward analysis
- Out-of-sample testing
- Benchmark comparison
- Drawdown analysis
- Risk-adjusted returns
- Factor attribution
- Stress testing
- Scenario analysis

Usage:
    from nautilus_trader_engine.strategies.backtesting import BacktestEngine, PerformanceAnalyzer
    
    engine = BacktestEngine()
    results = engine.run_backtest(strategy, data, config)
    analyzer = PerformanceAnalyzer(results)
    metrics = analyzer.calculate_metrics()
"""

from .backtest_engine import BacktestEngine
from .performance_analyzer import PerformanceAnalyzer
from .risk_analyzer import RiskAnalyzer
from .report_generator import ReportGenerator, ReportConfig, create_report_generator
from .data_manager import DataManager, DataConfig, MarketData as DataMarketData, create_data_manager
from .portfolio_simulator import PortfolioSimulator, Position, TransactionCosts, create_portfolio_simulator
from .results import BacktestResults, Trade, Position as ResultsPosition, PortfolioSnapshot
from .integration import KafkaEventStreamer, EventMessage
from .metrics import (
    PerformanceMetrics,
    RiskMetrics,
    TradeMetrics,
    DrawdownMetrics,
    BenchmarkMetrics
)
from .config import BacktestConfig
from .results import BacktestResults
from .visualization import VisualizationEngine

__all__ = [
    'BacktestEngine',
    'PerformanceAnalyzer',
    'RiskAnalyzer',
    'ReportGenerator',
    'ReportConfig',
    'DataManager',
    'PortfolioSimulator',
    'PerformanceMetrics',
    'RiskMetrics',
    'TradeMetrics',
    'DrawdownMetrics',
    'BenchmarkMetrics',
    'BacktestConfig',
    'BacktestResults',
    'create_report_generator',
    'DataConfig',
    'DataMarketData',
    'create_data_manager',
    'Position',
    'TransactionCosts',
    'create_portfolio_simulator',
    'Trade',
    'ResultsPosition',
    'PortfolioSnapshot',
    'KafkaEventStreamer',
    'EventMessage',
    'VisualizationEngine'
]