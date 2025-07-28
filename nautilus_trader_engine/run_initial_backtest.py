"""
Initial Backtesting Script for Nautilus Trader Engine

This script demonstrates the backtesting capabilities by running a Moving Average
Crossover strategy on AAPL data for 2023 using both backtrader and TradingGym engines.

Features:
- Fetches AAPL data for 2023 using yfinance
- Implements Moving Average Crossover strategy (SMA 10 vs SMA 30)
- Runs backtests using both backtrader and TradingGym
- Outputs comprehensive performance metrics
- Includes proper error handling and logging

Author: Vincent S. Pereira
Version: 1.0.0
"""

import os
import sys
import logging
import traceback
from datetime import datetime, date
from typing import Dict, Any, Optional
import pandas as pd
import yfinance as yf

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_feeds import DataFeedManager, AssetClass
from backtesting.backtrader_engine import BacktraderEngine
from backtesting.trading_gym_engine import TradingGymEngine
from strategies.moving_average_crossover import MovingAverageCrossover, MovingAverageCrossoverGym

# Import indicators with fallback support
try:
    from indicators_fallback import get_available_indicators, test_indicators
    INDICATORS_AVAILABLE = True
    print("Technical indicators module loaded successfully")
except ImportError as e:
    INDICATORS_AVAILABLE = False
    print(f"Warning: Could not load indicators module: {e}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backtest.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BacktestRunner:
    """Main class for running backtests with multiple engines"""
    
    def __init__(self, symbol: str = "AAPL", year: int = 2023, initial_capital: float = 100000.0):
        self.symbol = symbol
        self.year = year
        self.initial_capital = initial_capital
        self.data = None
        
        # Strategy parameters
        self.fast_period = 10
        self.slow_period = 30
        
        logger.info(f"BacktestRunner initialized for {symbol} ({year}) with ${initial_capital:,.2f}")
    
    def fetch_data(self) -> bool:
        """Fetch market data for the specified symbol and year"""
        try:
            logger.info(f"Fetching {self.symbol} data for {self.year}...")
            
            # Define date range
            start_date = f"{self.year}-01-01"
            end_date = f"{self.year}-12-31"
            
            # Try using the data feed manager first
            try:
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
                    logger.info(f"Data fetched via DataFeedManager: {len(self.data)} bars")
                    return True
                else:
                    logger.warning("DataFeedManager failed, trying direct yfinance...")
            
            except Exception as e:
                logger.warning(f"DataFeedManager error: {e}, trying direct yfinance...")
            
            # Fallback to direct yfinance
            ticker = yf.Ticker(self.symbol)
            self.data = ticker.history(start=start_date, end=end_date, interval='1d')
            
            if self.data.empty:
                logger.error(f"No data retrieved for {self.symbol}")
                return False
            
            # Standardize column names
            self.data.columns = [col.lower().replace(' ', '_') for col in self.data.columns]
            
            logger.info(f"Data fetched successfully: {len(self.data)} bars from {self.data.index[0].date()} to {self.data.index[-1].date()}")
            logger.info(f"Data columns: {list(self.data.columns)}")
            logger.info(f"Sample data:\n{self.data.head()}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def run_backtrader_backtest(self) -> Optional[Dict[str, Any]]:
        """Run backtest using backtrader engine"""
        try:
            logger.info("=" * 60)
            logger.info("RUNNING BACKTRADER BACKTEST")
            logger.info("=" * 60)
            
            # Initialize engine
            engine = BacktraderEngine(initial_capital=self.initial_capital)
            
            # Add strategy
            engine.add_strategy(
                MovingAverageCrossover,
                fast_period=self.fast_period,
                slow_period=self.slow_period,
                printlog=True
            )
            
            # Add data
            engine.add_data(self.data, self.symbol)
            
            # Run backtest
            result = engine.run()
            
            # Print results
            self._print_results("BACKTRADER", result)
            
            return result.to_dict()
            
        except Exception as e:
            logger.error(f"Backtrader backtest failed: {e}")
            logger.error(traceback.format_exc())
            return None
    
    def run_trading_gym_backtest(self) -> Optional[Dict[str, Any]]:
        """Run backtest using TradingGym engine"""
        try:
            logger.info("=" * 60)
            logger.info("RUNNING TRADING GYM BACKTEST")
            logger.info("=" * 60)
            
            # Initialize engine
            engine = TradingGymEngine(initial_capital=self.initial_capital)
            
            # Create strategy instance
            strategy = MovingAverageCrossoverGym(
                fast_period=self.fast_period,
                slow_period=self.slow_period
            )
            
            # Add strategy and data
            engine.add_strategy(strategy)
            engine.add_data(self.data, self.symbol)
            
            # Run backtest
            result = engine.run()
            
            # Print results
            self._print_results("TRADING GYM", result)
            
            return result.to_dict()
            
        except Exception as e:
            logger.error(f"TradingGym backtest failed: {e}")
            logger.error(traceback.format_exc())
            return None
    
    def _print_results(self, engine_name: str, result):
        """Print formatted backtest results"""
        print(f"\n{engine_name} BACKTEST RESULTS")
        print("=" * 50)
        print(f"Strategy: Moving Average Crossover ({self.fast_period}/{self.slow_period})")
        print(f"Symbol: {self.symbol}")
        print(f"Period: {self.year}")
        print(f"Initial Capital: ${result.initial_capital:,.2f}")
        print(f"Final Capital: ${result.final_capital:,.2f}")
        print()
        
        print("PERFORMANCE METRICS:")
        print(f"  Total Return: {result.total_return:.2%}")
        print(f"  Annual Return: {result.annual_return:.2%}")
        print(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}")
        print(f"  Max Drawdown: {result.max_drawdown:.2%}")
        print(f"  Volatility: {result.volatility:.2%}")
        print(f"  Calmar Ratio: {result.calmar_ratio:.2f}")
        print(f"  Sortino Ratio: {result.sortino_ratio:.2f}")
        print()
        
        print("TRADE STATISTICS:")
        print(f"  Total Trades: {result.total_trades}")
        print(f"  Winning Trades: {result.winning_trades}")
        print(f"  Losing Trades: {result.losing_trades}")
        print(f"  Win Rate: {result.win_rate:.1%}")
        print(f"  Average Win: ${result.avg_win:.2f}")
        print(f"  Average Loss: ${result.avg_loss:.2f}")
        print(f"  Profit Factor: {result.profit_factor:.2f}")
        print()
    
    def compare_results(self, backtrader_result: Dict, trading_gym_result: Dict):
        """Compare results from both engines"""
        print("\n" + "=" * 60)
        print("COMPARISON OF RESULTS")
        print("=" * 60)
        
        metrics = [
            ('Total Return', 'total_return', '%'),
            ('Annual Return', 'annual_return', '%'),
            ('Sharpe Ratio', 'sharpe_ratio', ''),
            ('Max Drawdown', 'max_drawdown', '%'),
            ('Volatility', 'volatility', '%'),
            ('Total Trades', 'total_trades', ''),
            ('Win Rate', 'win_rate', '%')
        ]
        
        print(f"{'Metric':<20} {'Backtrader':<15} {'TradingGym':<15} {'Difference':<15}")
        print("-" * 65)
        
        for metric_name, metric_key, unit in metrics:
            bt_value = backtrader_result.get(metric_key, 0)
            tg_value = trading_gym_result.get(metric_key, 0)
            diff = bt_value - tg_value
            
            if unit == '%':
                bt_str = f"{bt_value:.2%}"
                tg_str = f"{tg_value:.2%}"
                diff_str = f"{diff:.2%}"
            elif metric_key in ['total_trades']:
                bt_str = f"{bt_value:.0f}"
                tg_str = f"{tg_value:.0f}"
                diff_str = f"{diff:.0f}"
            else:
                bt_str = f"{bt_value:.2f}"
                tg_str = f"{tg_value:.2f}"
                diff_str = f"{diff:.2f}"
            
            print(f"{metric_name:<20} {bt_str:<15} {tg_str:<15} {diff_str:<15}")
    
    def run_all_backtests(self):
        """Run backtests with both engines and compare results"""
        logger.info(f"Starting comprehensive backtest for {self.symbol} ({self.year})")
        
        # Fetch data
        if not self.fetch_data():
            logger.error("Failed to fetch data. Aborting backtests.")
            return
        
        # Run backtests
        backtrader_result = self.run_backtrader_backtest()
        trading_gym_result = self.run_trading_gym_backtest()
        
        # Compare results if both succeeded
        if backtrader_result and trading_gym_result:
            self.compare_results(backtrader_result, trading_gym_result)
        
        # Summary
        print("\n" + "=" * 60)
        print("BACKTEST SUMMARY")
        print("=" * 60)
        print(f"Symbol: {self.symbol}")
        print(f"Year: {self.year}")
        print(f"Strategy: Moving Average Crossover ({self.fast_period}/{self.slow_period})")
        print(f"Data Points: {len(self.data) if self.data is not None else 0}")
        print(f"Backtrader: {'OK' if backtrader_result else 'FAIL'}")
        print(f"TradingGym: {'OK' if trading_gym_result else 'FAIL'}")
        
        if backtrader_result:
            print(f"Best Return: {backtrader_result['total_return']:.2%} (Backtrader)")
        
        logger.info("Backtest completed successfully")


def display_system_info():
    """Display system and indicator availability information"""
    print("\nSYSTEM INFORMATION:")
    print("-" * 40)
    
    if INDICATORS_AVAILABLE:
        try:
            indicator_info = get_available_indicators()
            print(f"TA-Lib Available: {'Yes' if indicator_info['talib_available'] else 'No'}")
            print(f"'ta' Library Available: {'Yes' if indicator_info['ta_available'] else 'No'}")
            print(f"Fallback Method: {indicator_info['fallback_method']}")
            print(f"Available Indicators: {len(indicator_info['indicators'])}")
            
            if not indicator_info['talib_available']:
                print("\n[!] TA-Lib not installed. Using fallback implementations.")
                print("   See TALIB_INSTALLATION.md for installation instructions.")
                
        except Exception as e:
            print(f"Error getting indicator info: {e}")
    else:
        print("[!] Indicators module not available")
    
    print()


def main():
    """Main function to run the backtesting script"""
    print("=" * 80)
    print("NAUTILUS TRADER ENGINE - INITIAL BACKTEST")
    print("Moving Average Crossover Strategy (SMA 10 vs SMA 30)")
    print("=" * 80)
    
    # Display system information
    display_system_info()
    
    try:
        # Test indicators if available
        if INDICATORS_AVAILABLE:
            print("Testing technical indicators...")
            try:
                test_indicators()
                print("OK: All indicators working correctly\n")
            except Exception as e:
                print(f"[!] Indicator test failed: {e}")
                print("Proceeding with basic backtest...\n")
        
        # Initialize and run backtests
        runner = BacktestRunner(
            symbol="AAPL",
            year=2023,
            initial_capital=100000.0
        )
        
        runner.run_all_backtests()
        
    except KeyboardInterrupt:
        logger.info("Backtest interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(traceback.format_exc())
    
    print("\nBacktest completed. Check 'backtest.log' for detailed logs.")
    
    if not INDICATORS_AVAILABLE:
        print("\n" + "=" * 60)
        print("INSTALLATION NOTES:")
        print("=" * 60)
        print("For full technical analysis capabilities, install TA-Lib:")
        print("1. See nautilus_trader_engine/TALIB_INSTALLATION.md")
        print("2. Or use Docker: docker-compose up --build")
        print("3. Current fallback uses 'ta' library and manual calculations")


if __name__ == "__main__":
    main()