#!/usr/bin/env python3
"""
RSI(2) Mean Reversion Strategy Backtesting Example

This example demonstrates how to use the comprehensive backtesting framework
with the RSI(2) mean reversion strategy and NautilusTrader integration.

Features:
- Complete strategy backtesting with regime detection
- Performance analytics and risk analysis
- Visualization and reporting
- Kafka event streaming integration
- Multi-timeframe analysis
"""

import asyncio
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import logging

# Strategy imports
from strategies.mean_reversion.rsi2_mean_reversion_strategy import (
    RSI2MeanReversionStrategy,
    create_rsi2_strategy
)

# Backtesting framework imports
from strategies.backtesting import (
    BacktestEngine,
    BacktestConfig,
    BacktestMode,
    RebalanceFrequency,
    BenchmarkType,
    TransactionCosts,
    RiskLimits,
    PerformanceAnalyzer,
    RiskAnalyzer,
    VisualizationEngine,
    IntegratedBacktestEngine
)

# Data and utilities
import yfinance as yf
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RSI2BacktestExample:
    """
    Comprehensive example demonstrating RSI(2) strategy backtesting
    with the full analytics framework.
    """
    
    def __init__(self):
        self.results_dir = Path("backtest_results")
        self.results_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.backtest_engine = None
        self.performance_analyzer = None
        self.risk_analyzer = None
        self.visualization_engine = None
        self.integrated_engine = None
    
    def create_sample_data(self, symbol: str = "SPY", 
                          start_date: str = "2020-01-01",
                          end_date: str = "2023-12-31") -> pd.DataFrame:
        """
        Download sample market data for backtesting.
        
        Args:
            symbol: Stock symbol to download
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            DataFrame with OHLCV data
        """
        logger.info(f"Downloading data for {symbol} from {start_date} to {end_date}")
        
        try:
            # Download data using yfinance
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date)
            
            # Ensure we have the required columns
            required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in data.columns for col in required_columns):
                raise ValueError(f"Missing required columns: {required_columns}")
            
            # Reset index to make Date a column
            data = data.reset_index()
            data['Symbol'] = symbol
            
            logger.info(f"Downloaded {len(data)} rows of data for {symbol}")
            return data
            
        except Exception as e:
            logger.error(f"Error downloading data for {symbol}: {e}")
            # Create synthetic data as fallback
            return self._create_synthetic_data(symbol, start_date, end_date)
    
    def _create_synthetic_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Create synthetic market data for testing when real data is unavailable.
        """
        logger.info(f"Creating synthetic data for {symbol}")
        
        # Generate date range
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        dates = dates[dates.weekday < 5]  # Remove weekends
        
        n_days = len(dates)
        np.random.seed(42)  # For reproducible results
        
        # Generate realistic price movements
        returns = np.random.normal(0.0005, 0.02, n_days)  # Daily returns
        prices = 100 * np.exp(np.cumsum(returns))  # Geometric Brownian motion
        
        # Generate OHLC from close prices
        high_factor = 1 + np.abs(np.random.normal(0, 0.01, n_days))
        low_factor = 1 - np.abs(np.random.normal(0, 0.01, n_days))
        
        data = pd.DataFrame({
            'Date': dates,
            'Open': prices * np.random.uniform(0.99, 1.01, n_days),
            'High': prices * high_factor,
            'Low': prices * low_factor,
            'Close': prices,
            'Volume': np.random.randint(1000000, 10000000, n_days),
            'Symbol': symbol
        })
        
        return data
    
    def setup_backtest_config(self) -> BacktestConfig:
        """
        Create a comprehensive backtest configuration.
        """
        transaction_costs = TransactionCosts(
            commission_per_trade=1.0,
            commission_percent=0.001,
            bid_ask_spread=0.01,
            slippage_percent=0.001,
            borrowing_rate=0.02
        )
        
        risk_limits = RiskLimits(
            max_position_size=0.1,
            max_portfolio_leverage=2.0,
            max_sector_exposure=0.3,
            max_single_position=0.05,
            var_limit=0.02,
            max_drawdown=0.15
        )
        
        config = BacktestConfig(
            start_date=datetime(2020, 1, 1),
            end_date=datetime(2023, 12, 31),
            initial_capital=100000.0,
            mode=BacktestMode.VECTORIZED,
            rebalance_frequency=RebalanceFrequency.DAILY,
            benchmark=BenchmarkType.SPY,
            transaction_costs=transaction_costs,
            risk_limits=risk_limits,
            enable_short_selling=True,
            margin_requirement=0.5,
            risk_free_rate=0.02
        )
        
        return config
    
    def create_strategy_config(self) -> dict:
        """
        Create RSI(2) strategy configuration.
        """
        return {
            'rsi_period': 2,
            'rsi_oversold': 10,
            'rsi_overbought': 90,
            'position_size': 0.05,
            'stop_loss_pct': 0.02,
            'take_profit_pct': 0.04,
            'max_holding_period': 10,
            'regime_lookback': 252,
            'volatility_threshold': 0.02,
            'trend_threshold': 0.1,
            'enable_regime_filter': True,
            'enable_volume_filter': True,
            'min_volume_ratio': 1.5,
            'confidence_threshold': 0.6
        }
    
    async def run_basic_backtest(self):
        """
        Run a basic backtest using the BacktestEngine.
        """
        logger.info("Running basic backtest...")
        
        # Get sample data
        data = self.create_sample_data("SPY")
        
        # Setup configuration
        config = self.setup_backtest_config()
        strategy_config = self.create_strategy_config()
        
        # Create strategy
        strategy = create_rsi2_strategy(**strategy_config)
        
        # Initialize backtest engine
        self.backtest_engine = BacktestEngine(config)
        
        # Run backtest
        results = await self.backtest_engine.run_backtest(
            strategy=strategy,
            data=data,
            symbols=["SPY"]
        )
        
        # Print basic results
        logger.info(f"Backtest completed. Total return: {results.total_return:.2%}")
        logger.info(f"Sharpe ratio: {results.sharpe_ratio:.2f}")
        logger.info(f"Max drawdown: {results.max_drawdown:.2%}")
        logger.info(f"Number of trades: {len(results.trades)}")
        
        return results
    
    async def run_comprehensive_analysis(self):
        """
        Run comprehensive backtesting with full analytics.
        """
        logger.info("Running comprehensive analysis...")
        
        # Get sample data for multiple symbols
        symbols = ["SPY", "QQQ", "IWM"]
        data_dict = {}
        
        for symbol in symbols:
            data_dict[symbol] = self.create_sample_data(symbol)
        
        # Setup configuration
        config = self.setup_backtest_config()
        strategy_config = self.create_strategy_config()
        
        # Initialize integrated engine
        self.integrated_engine = IntegratedBacktestEngine(
            backtest_config=config,
            kafka_config=None  # Disable Kafka for this example
        )
        
        # Run comprehensive backtest
        results = await self.integrated_engine.run_backtest(
            strategy_class=RSI2MeanReversionStrategy,
            strategy_config=strategy_config,
            data=data_dict,
            symbols=symbols
        )
        
        # Analyze performance
        performance_analysis = await self.integrated_engine.analyze_performance(
            results, 
            benchmark_data=data_dict["SPY"]
        )
        
        # Generate reports
        report_path = self.results_dir / "comprehensive_report.html"
        await self.integrated_engine.generate_report(
            results=results,
            analysis=performance_analysis,
            output_path=str(report_path)
        )
        
        logger.info(f"Comprehensive analysis completed. Report saved to {report_path}")
        return results, performance_analysis
    
    async def run_risk_analysis(self, results):
        """
        Run detailed risk analysis on backtest results.
        """
        logger.info("Running risk analysis...")
        
        # Initialize risk analyzer
        self.risk_analyzer = RiskAnalyzer()
        
        # Calculate VaR
        returns = pd.Series([t.pnl for t in results.trades])
        var_result = self.risk_analyzer.calculate_var(
            returns=returns,
            confidence_level=0.95,
            method='historical'
        )
        
        logger.info(f"Value at Risk (95%): ${var_result.var:.2f}")
        logger.info(f"Expected Shortfall: ${var_result.expected_shortfall:.2f}")
        
        # Run stress tests
        stress_scenarios = {
            'market_crash': {'market_shock': -0.20, 'volatility_shock': 2.0},
            'high_volatility': {'volatility_shock': 3.0},
            'interest_rate_shock': {'rate_shock': 0.02}
        }
        
        stress_results = {}
        for scenario_name, scenario in stress_scenarios.items():
            stress_result = self.risk_analyzer.run_stress_test(
                portfolio_value=results.final_portfolio_value,
                positions=results.positions,
                scenario=scenario
            )
            stress_results[scenario_name] = stress_result
            logger.info(f"Stress test '{scenario_name}': {stress_result.portfolio_impact:.2%}")
        
        return var_result, stress_results
    
    async def create_visualizations(self, results, analysis):
        """
        Create comprehensive visualizations.
        """
        logger.info("Creating visualizations...")
        
        # Initialize visualization engine
        self.visualization_engine = VisualizationEngine()
        
        # Create performance dashboard
        performance_fig = self.visualization_engine.create_performance_dashboard(
            results=results,
            benchmark_data=None,  # Would use actual benchmark data
            title="RSI(2) Strategy Performance"
        )
        
        # Save performance chart
        performance_path = self.results_dir / "performance_dashboard.html"
        performance_fig.write_html(str(performance_path))
        
        # Create trade analysis
        trade_fig = self.visualization_engine.create_trade_analysis(
            trades=results.trades,
            title="Trade Analysis"
        )
        
        # Save trade analysis
        trade_path = self.results_dir / "trade_analysis.html"
        trade_fig.write_html(str(trade_path))
        
        # Create risk dashboard
        risk_fig = self.visualization_engine.create_risk_dashboard(
            results=results,
            risk_metrics=analysis.risk_metrics if analysis else None,
            title="Risk Analysis"
        )
        
        # Save risk dashboard
        risk_path = self.results_dir / "risk_dashboard.html"
        risk_fig.write_html(str(risk_path))
        
        logger.info(f"Visualizations saved to {self.results_dir}")
        
        return {
            'performance': str(performance_path),
            'trades': str(trade_path),
            'risk': str(risk_path)
        }
    
    async def run_parameter_optimization(self):
        """
        Run parameter optimization for the RSI(2) strategy.
        """
        logger.info("Running parameter optimization...")
        
        # Get sample data
        data = self.create_sample_data("SPY")
        
        # Define parameter ranges
        param_ranges = {
            'rsi_period': [2, 3, 4, 5],
            'rsi_oversold': [5, 10, 15, 20],
            'rsi_overbought': [80, 85, 90, 95],
            'position_size': [0.02, 0.05, 0.1],
            'stop_loss_pct': [0.01, 0.02, 0.03]
        }
        
        best_params = None
        best_sharpe = -np.inf
        optimization_results = []
        
        # Grid search optimization
        import itertools
        
        param_combinations = list(itertools.product(*param_ranges.values()))
        logger.info(f"Testing {len(param_combinations)} parameter combinations")
        
        for i, params in enumerate(param_combinations[:20]):  # Limit for example
            param_dict = dict(zip(param_ranges.keys(), params))
            
            # Add default parameters
            strategy_config = self.create_strategy_config()
            strategy_config.update(param_dict)
            
            try:
                # Create and test strategy
                strategy = create_rsi2_strategy(**strategy_config)
                config = self.setup_backtest_config()
                
                engine = BacktestEngine(config)
                results = await engine.run_backtest(
                    strategy=strategy,
                    data=data,
                    symbols=["SPY"]
                )
                
                # Track results
                optimization_results.append({
                    'params': param_dict,
                    'total_return': results.total_return,
                    'sharpe_ratio': results.sharpe_ratio,
                    'max_drawdown': results.max_drawdown,
                    'num_trades': len(results.trades)
                })
                
                # Update best parameters
                if results.sharpe_ratio > best_sharpe:
                    best_sharpe = results.sharpe_ratio
                    best_params = param_dict.copy()
                
                if (i + 1) % 5 == 0:
                    logger.info(f"Completed {i + 1}/{len(param_combinations[:20])} optimizations")
                    
            except Exception as e:
                logger.warning(f"Optimization failed for params {param_dict}: {e}")
        
        logger.info(f"Optimization completed. Best Sharpe ratio: {best_sharpe:.2f}")
        logger.info(f"Best parameters: {best_params}")
        
        # Save optimization results
        results_df = pd.DataFrame(optimization_results)
        results_path = self.results_dir / "optimization_results.csv"
        results_df.to_csv(results_path, index=False)
        
        return best_params, optimization_results


async def main():
    """
    Main function to run the RSI(2) backtesting example.
    """
    logger.info("Starting RSI(2) Backtesting Example")
    
    # Initialize example
    example = RSI2BacktestExample()
    
    try:
        # Run basic backtest
        logger.info("=== Running Basic Backtest ===")
        basic_results = await example.run_basic_backtest()
        
        # Run comprehensive analysis
        logger.info("=== Running Comprehensive Analysis ===")
        comp_results, analysis = await example.run_comprehensive_analysis()
        
        # Run risk analysis
        logger.info("=== Running Risk Analysis ===")
        var_result, stress_results = await example.run_risk_analysis(comp_results)
        
        # Create visualizations
        logger.info("=== Creating Visualizations ===")
        viz_paths = await example.create_visualizations(comp_results, analysis)
        
        # Run parameter optimization
        logger.info("=== Running Parameter Optimization ===")
        best_params, opt_results = await example.run_parameter_optimization()
        
        # Summary
        logger.info("=== Summary ===")
        logger.info(f"Basic backtest Sharpe ratio: {basic_results.sharpe_ratio:.2f}")
        logger.info(f"Comprehensive backtest Sharpe ratio: {comp_results.sharpe_ratio:.2f}")
        logger.info(f"Optimized parameters: {best_params}")
        logger.info(f"Visualizations created: {list(viz_paths.values())}")
        
        logger.info("RSI(2) Backtesting Example completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in backtesting example: {e}")
        raise


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())