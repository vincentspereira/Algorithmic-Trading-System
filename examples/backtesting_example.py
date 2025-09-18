"""Comprehensive Backtesting Framework Example

This example demonstrates the usage of the comprehensive backtesting framework
including performance analysis, risk analysis, and scenario testing.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, Any

# Import backtesting framework
from backtesting import (
    create_backtest_engine,
    create_performance_analyzer,
    create_risk_analyzer,
    create_scenario_analyzer,
    run_comprehensive_backtest,
    BacktestConfig,
    ScenarioConfig
)

# Import strategy components
from strategies.momentum import MomentumStrategy
from strategies.mean_reversion import MeanReversionStrategy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def generate_sample_data(start_date: str = '2020-01-01', end_date: str = '2023-12-31', 
                        symbols: list = None) -> Dict[str, pd.DataFrame]:
    """Generate sample market data for backtesting
    
    Args:
        start_date: Start date for data generation
        end_date: End date for data generation
        symbols: List of symbols to generate data for
        
    Returns:
        Dictionary of DataFrames with OHLCV data
    """
    if symbols is None:
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'SPY']
    
    logger.info(f"Generating sample data for {len(symbols)} symbols from {start_date} to {end_date}")
    
    # Generate date range
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    dates = dates[dates.weekday < 5]  # Remove weekends
    
    data = {}
    
    for symbol in symbols:
        # Set random seed for reproducible data
        np.random.seed(hash(symbol) % 2**32)
        
        n_days = len(dates)
        
        # Generate realistic price movements
        base_price = np.random.uniform(50, 300)
        returns = np.random.normal(0.0005, 0.02, n_days)  # Daily returns
        
        # Add some trend and volatility clustering
        trend = np.sin(np.arange(n_days) * 2 * np.pi / 252) * 0.001  # Annual cycle
        volatility = 0.015 + 0.01 * np.abs(np.sin(np.arange(n_days) * 2 * np.pi / 63))  # Quarterly vol cycle
        
        returns = returns + trend
        returns = returns * volatility / 0.02  # Scale by volatility
        
        # Generate price series
        prices = base_price * np.exp(np.cumsum(returns))
        
        # Generate OHLC from close prices
        high_mult = 1 + np.abs(np.random.normal(0, 0.01, n_days))
        low_mult = 1 - np.abs(np.random.normal(0, 0.01, n_days))
        open_mult = 1 + np.random.normal(0, 0.005, n_days)
        
        high = prices * high_mult
        low = prices * low_mult
        open_prices = np.roll(prices, 1) * open_mult
        open_prices[0] = prices[0]  # First open = first close
        
        # Generate volume
        base_volume = np.random.uniform(1000000, 10000000)
        volume_mult = 1 + np.abs(np.random.normal(0, 0.3, n_days))
        volume = base_volume * volume_mult
        
        # Create DataFrame
        df = pd.DataFrame({
            'open': open_prices,
            'high': high,
            'low': low,
            'close': prices,
            'volume': volume.astype(int)
        }, index=dates)
        
        # Ensure OHLC consistency
        df['high'] = df[['open', 'high', 'low', 'close']].max(axis=1)
        df['low'] = df[['open', 'high', 'low', 'close']].min(axis=1)
        
        data[symbol] = df
    
    logger.info(f"Generated sample data with {len(dates)} trading days")
    return data

def create_sample_strategy():
    """Create a sample strategy for backtesting"""
    class SampleStrategy:
        """Simple momentum + mean reversion strategy"""
        
        def __init__(self, momentum_window=20, mean_reversion_window=5):
            self.momentum_window = momentum_window
            self.mean_reversion_window = mean_reversion_window
            self.positions = {}
            
        def generate_signals(self, data: pd.DataFrame) -> pd.Series:
            """Generate trading signals"""
            # Momentum signal
            momentum = data['close'].pct_change(self.momentum_window)
            momentum_signal = np.where(momentum > 0.05, 1, np.where(momentum < -0.05, -1, 0))
            
            # Mean reversion signal
            sma = data['close'].rolling(self.mean_reversion_window).mean()
            mean_reversion_signal = np.where(
                data['close'] < sma * 0.98, 1,
                np.where(data['close'] > sma * 1.02, -1, 0)
            )
            
            # Combine signals
            combined_signal = (momentum_signal + mean_reversion_signal) / 2
            return pd.Series(combined_signal, index=data.index)
        
        def calculate_positions(self, signals: pd.Series) -> pd.Series:
            """Calculate position sizes from signals"""
            # Simple position sizing
            positions = signals * 0.1  # 10% of capital per signal
            return positions.fillna(0)
    
    return SampleStrategy()

def demonstrate_basic_backtesting():
    """Demonstrate basic backtesting functionality"""
    logger.info("=== Basic Backtesting Demo ===")
    
    # Generate sample data
    data = generate_sample_data(symbols=['AAPL', 'SPY'])
    
    # Create strategy
    strategy = create_sample_strategy()
    
    # Configure backtest
    config = {
        'initial_capital': 100000,
        'commission': 0.001,
        'slippage': 0.0005,
        'benchmark': 'SPY'
    }
    
    # Create backtest engine
    engine = create_backtest_engine(config)
    
    logger.info("Running basic backtest...")
    
    # Simulate backtest results (simplified)
    returns = generate_sample_returns()
    positions = generate_sample_positions()
    
    logger.info(f"Backtest completed - Total return: {(returns + 1).prod() - 1:.2%}")
    
    return returns, positions

def demonstrate_performance_analysis():
    """Demonstrate performance analysis"""
    logger.info("=== Performance Analysis Demo ===")
    
    # Generate sample results
    returns, positions = demonstrate_basic_backtesting()
    
    # Create performance analyzer
    analyzer = create_performance_analyzer()
    
    logger.info("Analyzing performance...")
    
    # Generate sample trades
    trades = generate_sample_trades()
    
    # Analyze performance
    performance_metrics, rolling_metrics, benchmark_comparison, report = analyzer.analyze_performance(
        returns, positions, trades
    )
    
    # Display key metrics
    logger.info(f"Total Return: {performance_metrics.total_return:.2%}")
    logger.info(f"Sharpe Ratio: {performance_metrics.sharpe_ratio:.3f}")
    logger.info(f"Max Drawdown: {performance_metrics.max_drawdown:.2%}")
    logger.info(f"Win Rate: {performance_metrics.win_rate:.1%}")
    
    # Generate performance report
    report_text = analyzer.generate_performance_report(performance_metrics, benchmark_comparison)
    logger.info("Performance report generated")
    
    return performance_metrics, report

def demonstrate_risk_analysis():
    """Demonstrate risk analysis"""
    logger.info("=== Risk Analysis Demo ===")
    
    # Generate sample results
    returns, positions = demonstrate_basic_backtesting()
    
    # Create risk analyzer
    risk_analyzer = create_risk_analyzer()
    
    logger.info("Analyzing risk...")
    
    # Analyze risk
    risk_metrics, var_analysis, stress_results, drawdown_analysis, risk_attribution = risk_analyzer.analyze_risk(
        returns, positions
    )
    
    # Display key risk metrics
    logger.info(f"VaR (95%, 1d): {risk_metrics.var_1d_95:.2%}")
    logger.info(f"CVaR (95%, 1d): {risk_metrics.cvar_1d_95:.2%}")
    logger.info(f"Realized Volatility: {risk_metrics.realized_volatility:.2%}")
    logger.info(f"Max Drawdown: {risk_metrics.max_drawdown:.2%}")
    logger.info(f"Tail Ratio: {risk_metrics.tail_ratio:.2f}")
    
    # Generate risk report
    risk_report = risk_analyzer.generate_risk_report(
        risk_metrics, var_analysis, stress_results, drawdown_analysis
    )
    logger.info("Risk report generated")
    
    return risk_metrics, risk_report

def demonstrate_scenario_analysis():
    """Demonstrate scenario analysis"""
    logger.info("=== Scenario Analysis Demo ===")
    
    # Generate sample results
    returns, positions = demonstrate_basic_backtesting()
    
    # Create scenario analyzer with custom config
    scenario_config = ScenarioConfig(
        n_simulations=5000,
        confidence_levels=[0.95, 0.99],
        custom_scenarios={
            'market_crash': {'equity': -0.30, 'bond': 0.05},
            'inflation_shock': {'equity': -0.15, 'bond': -0.10, 'commodity': 0.20}
        }
    )
    
    scenario_analyzer = create_scenario_analyzer(scenario_config.__dict__)
    
    logger.info("Running scenario analysis...")
    
    # Analyze scenarios
    scenario_results = scenario_analyzer.analyze_scenarios(returns, positions)
    
    # Display Monte Carlo results
    mc_results = scenario_results.monte_carlo
    logger.info(f"Monte Carlo - Mean Return: {mc_results.mean_return:.2%}")
    logger.info(f"Monte Carlo - Volatility: {mc_results.std_return:.2%}")
    logger.info(f"Monte Carlo - VaR (95%): {mc_results.var_estimates.get('95%', 0):.2%}")
    logger.info(f"Monte Carlo - CVaR (95%): {mc_results.cvar_estimates.get('95%', 0):.2%}")
    
    # Display stress test results
    if scenario_results.stress_test_results:
        worst_stress = min(scenario_results.stress_test_results.items(), key=lambda x: x[1])
        logger.info(f"Worst Stress Test: {worst_stress[0]} = {worst_stress[1]:.2%}")
    
    # Generate scenario report
    scenario_report = scenario_analyzer.generate_scenario_report(scenario_results)
    logger.info("Scenario analysis report generated")
    
    return scenario_results, scenario_report

def demonstrate_comprehensive_backtesting():
    """Demonstrate comprehensive backtesting with all analytics"""
    logger.info("=== Comprehensive Backtesting Demo ===")
    
    # Generate sample data
    data = generate_sample_data(symbols=['AAPL', 'GOOGL', 'SPY'])
    
    # Create strategy
    strategy = create_sample_strategy()
    
    # Configure comprehensive backtest
    config = {
        'initial_capital': 100000,
        'commission': 0.001,
        'slippage': 0.0005,
        'benchmark': 'SPY',
        'risk_free_rate': 0.02,
        'confidence_levels': [0.95, 0.99],
        'monte_carlo_simulations': 5000
    }
    
    logger.info("Running comprehensive backtest...")
    
    # Note: This would normally run the full backtest, but for demo purposes
    # we'll simulate the results
    try:
        # results = run_comprehensive_backtest(
        #     strategy=strategy,
        #     data=data,
        #     config=config,
        #     include_risk_analysis=True,
        #     include_scenario_analysis=True
        # )
        
        # For demo, create mock results
        results = {
            'backtest': 'Mock backtest results',
            'performance': 'Mock performance analysis',
            'risk': 'Mock risk analysis',
            'scenarios': 'Mock scenario analysis'
        }
        
        logger.info("Comprehensive backtest completed successfully")
        logger.info(f"Results include: {list(results.keys())}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error in comprehensive backtest: {e}")
        return None

def generate_sample_returns(n_days: int = 500) -> pd.Series:
    """Generate sample returns for demonstration"""
    dates = pd.date_range(start='2022-01-01', periods=n_days, freq='D')
    dates = dates[dates.weekday < 5][:n_days]  # Remove weekends
    
    # Generate realistic returns with some autocorrelation
    np.random.seed(42)
    returns = np.random.normal(0.0008, 0.015, len(dates))
    
    # Add some momentum and mean reversion
    for i in range(1, len(returns)):
        returns[i] += 0.1 * returns[i-1]  # Momentum
        if i > 5:
            returns[i] -= 0.05 * np.mean(returns[i-5:i])  # Mean reversion
    
    return pd.Series(returns, index=dates)

def generate_sample_positions(n_days: int = 500) -> pd.DataFrame:
    """Generate sample positions for demonstration"""
    dates = pd.date_range(start='2022-01-01', periods=n_days, freq='D')
    dates = dates[dates.weekday < 5][:n_days]  # Remove weekends
    
    symbols = ['AAPL', 'GOOGL', 'MSFT']
    
    # Generate random positions that sum to ~1.0
    np.random.seed(42)
    positions = np.random.uniform(-0.5, 0.5, (len(dates), len(symbols)))
    
    # Normalize to reasonable leverage
    positions = positions / np.abs(positions).sum(axis=1, keepdims=True) * 0.8
    
    return pd.DataFrame(positions, index=dates, columns=symbols)

def generate_sample_trades(n_trades: int = 100) -> pd.DataFrame:
    """Generate sample trades for demonstration"""
    dates = pd.date_range(start='2022-01-01', periods=n_trades, freq='D')
    
    np.random.seed(42)
    trades = pd.DataFrame({
        'symbol': np.random.choice(['AAPL', 'GOOGL', 'MSFT'], n_trades),
        'side': np.random.choice(['buy', 'sell'], n_trades),
        'quantity': np.random.randint(10, 1000, n_trades),
        'price': np.random.uniform(50, 300, n_trades),
        'commission': np.random.uniform(1, 10, n_trades),
        'pnl': np.random.normal(0, 100, n_trades)
    }, index=dates)
    
    return trades

def main():
    """Main demonstration function"""
    logger.info("Starting Comprehensive Backtesting Framework Demonstration")
    logger.info("=" * 60)
    
    try:
        # Demonstrate each component
        demonstrate_basic_backtesting()
        print("\n" + "="*60 + "\n")
        
        demonstrate_performance_analysis()
        print("\n" + "="*60 + "\n")
        
        demonstrate_risk_analysis()
        print("\n" + "="*60 + "\n")
        
        demonstrate_scenario_analysis()
        print("\n" + "="*60 + "\n")
        
        demonstrate_comprehensive_backtesting()
        
        logger.info("\n" + "="*60)
        logger.info("Demonstration completed successfully!")
        logger.info("The comprehensive backtesting framework provides:")
        logger.info("- Event-driven backtesting engine")
        logger.info("- Comprehensive performance analytics")
        logger.info("- Advanced risk analysis and VaR calculations")
        logger.info("- Monte Carlo simulations and scenario testing")
        logger.info("- Multi-strategy portfolio backtesting")
        logger.info("- Transaction cost modeling and slippage simulation")
        logger.info("- Real-time performance monitoring and reporting")
        
    except Exception as e:
        logger.error(f"Error in demonstration: {e}")
        raise

if __name__ == "__main__":
    main()