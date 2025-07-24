"""
VectorBT Integration Example for Nautilus Trader Engine

This module demonstrates VectorBT integration with the existing trading system,
showcasing high-performance backtesting capabilities and comparison with traditional methods.

Features:
- Simple VectorBT backtest implementation
- Integration with existing data feeds
- Performance comparison with traditional backtesting
- GPU acceleration support (when available)

Author: Kilo Code
Version: 1.0.0
"""

import os
import sys
import logging
import time
import warnings
from typing import Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np

# Suppress VectorBT warnings for cleaner output
warnings.filterwarnings('ignore', category=UserWarning, module='vectorbt')

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import vectorbt as vbt
    from vectorbt.portfolio import Portfolio
    from vectorbt.signals import STEX
    VECTORBT_AVAILABLE = True
    print("✓ VectorBT loaded successfully")
except ImportError as e:
    VECTORBT_AVAILABLE = False
    print(f"✗ VectorBT not available: {e}")

from data_feeds import DataFeedManager, AssetClass
from run_initial_backtest import BacktestRunner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VectorBTBacktester:
    """VectorBT-based backtesting engine for high-performance analysis"""
    
    def __init__(self, symbol: str = "AAPL", year: int = 2023, initial_capital: float = 100000.0):
        self.symbol = symbol
        self.year = year
        self.initial_capital = initial_capital
        self.data = None
        
        # Strategy parameters
        self.fast_period = 10
        self.slow_period = 30
        
        # VectorBT settings
        self.freq = 'D'  # Daily frequency
        
        logger.info(f"VectorBT Backtester initialized for {symbol} ({year}) with ${initial_capital:,.2f}")
    
    def fetch_data(self) -> bool:
        """Fetch market data using the existing data feed system"""
        try:
            logger.info(f"Fetching {self.symbol} data for {self.year}...")
            
            # Define date range
            start_date = f"{self.year}-01-01"
            end_date = f"{self.year}-12-31"
            
            # Use the existing data feed manager
            data_manager = DataFeedManager()
            response = data_manager.get_data(
                ticker=self.symbol,
                asset_class=AssetClass.STOCK,
                start_date=start_date,
                end_date=end_date,
                interval='1d'
            )
            
            if response.success and not response.data.empty:
                self.data = response.data
                # Ensure proper column names for VectorBT
                self.data.columns = [col.lower().replace(' ', '_') for col in self.data.columns]
                logger.info(f"Data fetched successfully: {len(self.data)} bars")
                return True
            else:
                logger.error("Failed to fetch data via DataFeedManager")
                return False
                
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            return False
    
    def generate_signals(self) -> Tuple[pd.Series, pd.Series]:
        """Generate buy/sell signals using moving average crossover strategy"""
        try:
            # Calculate moving averages
            close_prices = self.data['close']
            fast_ma = close_prices.rolling(window=self.fast_period).mean()
            slow_ma = close_prices.rolling(window=self.slow_period).mean()
            
            # Generate signals
            # Buy when fast MA crosses above slow MA
            buy_signals = (fast_ma > slow_ma) & (fast_ma.shift(1) <= slow_ma.shift(1))
            
            # Sell when fast MA crosses below slow MA
            sell_signals = (fast_ma < slow_ma) & (fast_ma.shift(1) >= slow_ma.shift(1))
            
            logger.info(f"Generated {buy_signals.sum()} buy signals and {sell_signals.sum()} sell signals")
            
            return buy_signals, sell_signals
            
        except Exception as e:
            logger.error(f"Error generating signals: {e}")
            return pd.Series(dtype=bool), pd.Series(dtype=bool)
    
    def run_vectorbt_backtest(self) -> Optional[Dict[str, Any]]:
        """Run backtest using VectorBT for high-performance analysis"""
        try:
            if not VECTORBT_AVAILABLE:
                logger.error("VectorBT not available")
                return None
            
            logger.info("=" * 60)
            logger.info("RUNNING VECTORBT BACKTEST")
            logger.info("=" * 60)
            
            start_time = time.time()
            
            # Generate trading signals
            buy_signals, sell_signals = self.generate_signals()
            
            if buy_signals.empty or sell_signals.empty:
                logger.error("No valid signals generated")
                return None
            
            # Get close prices
            close_prices = self.data['close']
            
            # Create VectorBT portfolio
            portfolio = vbt.Portfolio.from_signals(
                close=close_prices,
                entries=buy_signals,
                exits=sell_signals,
                init_cash=self.initial_capital,
                freq=self.freq
            )
            
            # Calculate performance metrics
            total_return = portfolio.total_return()
            annual_return = portfolio.annualized_return()
            sharpe_ratio = portfolio.sharpe_ratio()
            max_drawdown = portfolio.max_drawdown()
            volatility = portfolio.annualized_volatility()
            
            # Calculate additional metrics
            calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
            sortino_ratio = portfolio.sortino_ratio()
            
            # Trade statistics
            trades = portfolio.trades
            total_trades = trades.count()
            winning_trades = trades.winning.count()
            losing_trades = trades.losing.count()
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            avg_win = trades.winning.pnl.mean() if winning_trades > 0 else 0
            avg_loss = trades.losing.pnl.mean() if losing_trades > 0 else 0
            profit_factor = abs(trades.winning.pnl.sum() / trades.losing.pnl.sum()) if trades.losing.pnl.sum() != 0 else 0
            
            # Capital metrics
            final_capital = portfolio.final_value()
            
            execution_time = time.time() - start_time
            
            # Create result dictionary
            result = {
                'total_return': total_return,
                'annual_return': annual_return,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'volatility': volatility,
                'calmar_ratio': calmar_ratio,
                'sortino_ratio': sortino_ratio,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor,
                'initial_capital': self.initial_capital,
                'final_capital': final_capital,
                'execution_time': execution_time
            }
            
            # Print results
            self._print_vectorbt_results(result)
            
            logger.info(f"VectorBT backtest completed in {execution_time:.2f} seconds")
            return result
            
        except Exception as e:
            logger.error(f"VectorBT backtest failed: {e}")
            return None
    
    def _print_vectorbt_results(self, result: Dict[str, Any]):
        """Print formatted VectorBT backtest results"""
        print(f"\nVECTORBT BACKTEST RESULTS")
        print("=" * 50)
        print(f"Strategy: Moving Average Crossover ({self.fast_period}/{self.slow_period})")
        print(f"Symbol: {self.symbol}")
        print(f"Period: {self.year}")
        print(f"Initial Capital: ${result['initial_capital']:,.2f}")
        print(f"Final Capital: ${result['final_capital']:,.2f}")
        print(f"Execution Time: {result['execution_time']:.2f} seconds")
        print()
        
        print("PERFORMANCE METRICS:")
        print(f"  Total Return: {result['total_return']:.2%}")
        print(f"  Annual Return: {result['annual_return']:.2%}")
        print(f"  Sharpe Ratio: {result['sharpe_ratio']:.2f}")
        print(f"  Max Drawdown: {result['max_drawdown']:.2%}")
        print(f"  Volatility: {result['volatility']:.2%}")
        print(f"  Calmar Ratio: {result['calmar_ratio']:.2f}")
        print(f"  Sortino Ratio: {result['sortino_ratio']:.2f}")
        print()
        
        print("TRADE STATISTICS:")
        print(f"  Total Trades: {result['total_trades']}")
        print(f"  Winning Trades: {result['winning_trades']}")
        print(f"  Losing Trades: {result['losing_trades']}")
        print(f"  Win Rate: {result['win_rate']:.1%}")
        print(f"  Average Win: ${result['avg_win']:.2f}")
        print(f"  Average Loss: ${result['avg_loss']:.2f}")
        print(f"  Profit Factor: {result['profit_factor']:.2f}")
        print()
    
    def compare_with_traditional(self) -> Dict[str, Any]:
        """Compare VectorBT performance with traditional backtesting"""
        try:
            logger.info("=" * 60)
            logger.info("PERFORMANCE COMPARISON")
            logger.info("=" * 60)
            
            # Run VectorBT backtest
            vectorbt_result = self.run_vectorbt_backtest()
            if not vectorbt_result:
                logger.error("VectorBT backtest failed")
                return {}
            
            # Run traditional backtest using existing BacktestRunner
            traditional_runner = BacktestRunner(
                symbol=self.symbol,
                year=self.year,
                initial_capital=self.initial_capital
            )
            traditional_runner.fast_period = self.fast_period
            traditional_runner.slow_period = self.slow_period
            
            if not traditional_runner.fetch_data():
                logger.error("Failed to fetch data for traditional backtest")
                return {}
            
            traditional_start = time.time()
            traditional_result = traditional_runner.run_backtrader_backtest()
            traditional_time = time.time() - traditional_start
            
            if not traditional_result:
                logger.error("Traditional backtest failed")
                return {}
            
            # Compare results
            comparison = {
                'vectorbt': vectorbt_result,
                'traditional': traditional_result,
                'performance_improvement': {
                    'speed_improvement': traditional_time / vectorbt_result['execution_time'],
                    'vectorbt_time': vectorbt_result['execution_time'],
                    'traditional_time': traditional_time
                }
            }
            
            # Print comparison
            self._print_comparison(comparison)
            
            return comparison
            
        except Exception as e:
            logger.error(f"Comparison failed: {e}")
            return {}
    
    def _print_comparison(self, comparison: Dict[str, Any]):
        """Print performance comparison results"""
        vbt_result = comparison['vectorbt']
        trad_result = comparison['traditional']
        perf = comparison['performance_improvement']
        
        print("\n" + "=" * 60)
        print("VECTORBT vs TRADITIONAL BACKTESTING COMPARISON")
        print("=" * 60)
        
        print(f"{'Metric':<20} {'VectorBT':<15} {'Traditional':<15} {'Difference':<15}")
        print("-" * 65)
        
        metrics = [
            ('Total Return', 'total_return', '%'),
            ('Sharpe Ratio', 'sharpe_ratio', ''),
            ('Max Drawdown', 'max_drawdown', '%'),
            ('Total Trades', 'total_trades', ''),
            ('Win Rate', 'win_rate', '%')
        ]
        
        for metric_name, metric_key, unit in metrics:
            vbt_value = vbt_result.get(metric_key, 0)
            trad_value = trad_result.get(metric_key, 0)
            diff = vbt_value - trad_value
            
            if unit == '%':
                vbt_str = f"{vbt_value:.2%}"
                trad_str = f"{trad_value:.2%}"
                diff_str = f"{diff:.2%}"
            elif metric_key in ['total_trades']:
                vbt_str = f"{vbt_value:.0f}"
                trad_str = f"{trad_value:.0f}"
                diff_str = f"{diff:.0f}"
            else:
                vbt_str = f"{vbt_value:.2f}"
                trad_str = f"{trad_value:.2f}"
                diff_str = f"{diff:.2f}"
            
            print(f"{metric_name:<20} {vbt_str:<15} {trad_str:<15} {diff_str:<15}")
        
        print("\nPERFORMANCE METRICS:")
        print(f"VectorBT Execution Time: {perf['vectorbt_time']:.2f} seconds")
        print(f"Traditional Execution Time: {perf['traditional_time']:.2f} seconds")
        print(f"Speed Improvement: {perf['speed_improvement']:.1f}x faster")


def main():
    """Main function to demonstrate VectorBT integration"""
    print("=" * 80)
    print("VECTORBT INTEGRATION EXAMPLE")
    print("High-Performance Backtesting with Nautilus Trader Engine")
    print("=" * 80)
    
    if not VECTORBT_AVAILABLE:
        print("❌ VectorBT is not available. Please install it using:")
        print("   pip install vectorbt[numba]")
        return
    
    try:
        # Initialize VectorBT backtester
        backtester = VectorBTBacktester(
            symbol="AAPL",
            year=2023,
            initial_capital=100000.0
        )
        
        # Fetch data
        if not backtester.fetch_data():
            logger.error("Failed to fetch data. Aborting.")
            return
        
        # Run comparison with traditional backtesting
        comparison_result = backtester.compare_with_traditional()
        
        if comparison_result:
            print("\n✅ VectorBT integration demonstration completed successfully!")
            print(f"Speed improvement: {comparison_result['performance_improvement']['speed_improvement']:.1f}x")
        else:
            print("❌ Comparison failed")
        
    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()