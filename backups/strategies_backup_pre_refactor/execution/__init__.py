"""Strategy Execution Framework

This module provides comprehensive strategy execution capabilities for both
backtesting and live trading environments. It includes performance monitoring,
validation, and execution engines optimized for different trading scenarios.

Components:
===========
- backtesting: Historical strategy testing and analysis
- live_trading: Real-time strategy execution and monitoring
- validation: Strategy validation and compliance checking

Key Features:
=============
- Unified execution interface for backtesting and live trading
- Real-time performance monitoring and risk management
- Comprehensive validation framework
- Event-driven architecture with Kafka integration
- Microsecond-level latency optimization
- Enterprise-grade logging and audit trails

Usage:
======
# Backtesting
from nautilus_trader_engine.strategies.execution.backtesting import BacktestingEngine

backtest_engine = BacktestingEngine()
results = backtest_engine.run_backtest(strategy, data, config)

# Live Trading
from nautilus_trader_engine.strategies.execution.live_trading import RuntimeEngine, PerformanceMonitor

runtime_engine = RuntimeEngine()
performance_monitor = PerformanceMonitor()

# Strategy Validation
from nautilus_trader_engine.strategies.execution.validation import StrategyValidator

validator = StrategyValidator()
validation_result = validator.validate_strategy(strategy)

# Execution Pipeline
from nautilus_trader_engine.strategies.execution import ExecutionPipeline

pipeline = ExecutionPipeline(
    backtesting_engine=backtest_engine,
    runtime_engine=runtime_engine,
    performance_monitor=performance_monitor,
    validator=validator
)
"""

try:
    from . import backtesting
    from . import live_trading
    from . import validation
except ImportError:
    # Handle missing dependencies gracefully
    pass

__all__ = [
    'backtesting',
    'live_trading',
    'validation'
]