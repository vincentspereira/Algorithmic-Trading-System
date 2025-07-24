#!/usr/bin/env python3
"""
Portfolio Value Test Script for Nautilus Trader Engine

This script demonstrates the backtesting functionality by running a simple
Moving Average Crossover strategy and displaying portfolio performance metrics.

Security Features:
- Input validation and sanitization
- Comprehensive error handling
- Secure logging practices
- Resource management with proper cleanup

Best Practices Implemented:
- Clear separation of concerns
- Comprehensive documentation
- Type hints for better code clarity
- Defensive programming patterns
- Performance monitoring

Author: Kilo Code
Version: 1.0.0
Date: 2025-01-24
"""

import os
import sys
import logging
import traceback
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
import warnings

# Suppress pandas warnings for cleaner output
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

# Add the current directory to Python path for secure imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    from run_initial_backtest import BacktestRunner
    from data_feeds import DataFeedManager, AssetClass
except ImportError as e:
    print(f"❌ Error importing required modules: {e}")
    print("Please ensure you're running this script from the nautilus_trader_engine directory")
    sys.exit(1)

# Configure secure logging
def setup_logging() -> logging.Logger:
    """
    Set up secure logging configuration
    
    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    # Create formatter with timestamp and security context
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [PID:%(process)d] - %(message)s'
    )
    
    # Console handler for immediate feedback
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler for audit trail (secure file permissions)
    try:
        log_file = os.path.join(current_dir, 'portfolio_test.log')
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Set secure file permissions (owner read/write only)
        os.chmod(log_file, 0o600)
        
    except (OSError, PermissionError) as e:
        logger.warning(f"Could not create log file: {e}")
    
    return logger


class PortfolioValueTester:
    """
    Secure portfolio value testing class with comprehensive validation
    
    This class demonstrates best practices for:
    - Input validation and sanitization
    - Resource management
    - Error handling and recovery
    - Security-conscious design
    """
    
    def __init__(self, symbol: str = "AAPL", year: int = 2023, initial_capital: float = 100000.0):
        """
        Initialize the portfolio tester with validated parameters
        
        Args:
            symbol: Stock symbol to test (validated for security)
            year: Year for backtesting (validated range)
            initial_capital: Starting capital amount (validated positive)
            
        Raises:
            ValueError: If parameters are invalid or potentially unsafe
        """
        self.logger = setup_logging()
        
        # Input validation and sanitization
        self.symbol = self._validate_symbol(symbol)
        self.year = self._validate_year(year)
        self.initial_capital = self._validate_capital(initial_capital)
        
        # Initialize runner with validated parameters
        self.runner = None
        self.results = {}
        
        self.logger.info(f"PortfolioValueTester initialized - Symbol: {self.symbol}, "
                        f"Year: {self.year}, Capital: ${self.initial_capital:,.2f}")
    
    def _validate_symbol(self, symbol: str) -> str:
        """
        Validate and sanitize stock symbol
        
        Args:
            symbol: Raw symbol input
            
        Returns:
            str: Validated and sanitized symbol
            
        Raises:
            ValueError: If symbol is invalid or potentially unsafe
        """
        if not isinstance(symbol, str):
            raise ValueError("Symbol must be a string")
        
        # Remove any potentially dangerous characters
        symbol = symbol.strip().upper()
        
        # Validate symbol format (alphanumeric only, reasonable length)
        if not symbol.isalnum() or len(symbol) > 10 or len(symbol) < 1:
            raise ValueError(f"Invalid symbol format: {symbol}")
        
        return symbol
    
    def _validate_year(self, year: int) -> int:
        """
        Validate year parameter for reasonable range
        
        Args:
            year: Year to validate
            
        Returns:
            int: Validated year
            
        Raises:
            ValueError: If year is outside reasonable range
        """
        if not isinstance(year, int):
            raise ValueError("Year must be an integer")
        
        current_year = datetime.now().year
        if year < 2000 or year > current_year:
            raise ValueError(f"Year must be between 2000 and {current_year}")
        
        return year
    
    def _validate_capital(self, capital: float) -> float:
        """
        Validate initial capital amount
        
        Args:
            capital: Capital amount to validate
            
        Returns:
            float: Validated capital amount
            
        Raises:
            ValueError: If capital is invalid
        """
        if not isinstance(capital, (int, float)):
            raise ValueError("Capital must be a number")
        
        if capital <= 0 or capital > 10_000_000:  # Reasonable upper limit
            raise ValueError("Capital must be positive and reasonable (≤ $10M)")
        
        return float(capital)
    
    def run_portfolio_test(self) -> bool:
        """
        Execute the portfolio value test with comprehensive error handling
        
        Returns:
            bool: True if test completed successfully, False otherwise
        """
        try:
            self.logger.info("=" * 60)
            self.logger.info("STARTING PORTFOLIO VALUE TEST")
            self.logger.info("=" * 60)
            
            # Initialize BacktestRunner with validated parameters
            self.runner = BacktestRunner(
                symbol=self.symbol,
                year=self.year,
                initial_capital=self.initial_capital
            )
            
            # Fetch data with timeout and validation
            self.logger.info(f"Fetching market data for {self.symbol} ({self.year})...")
            if not self.runner.fetch_data():
                self.logger.error("Failed to fetch market data")
                return False
            
            # Validate data integrity
            if not self._validate_data():
                self.logger.error("Data validation failed")
                return False
            
            # Run backtest using backtrader engine (more stable for demo)
            self.logger.info("Running backtest with Moving Average Crossover strategy...")
            result = self.runner.run_backtrader_backtest()
            
            if result is None:
                self.logger.error("Backtest execution failed")
                return False
            
            # Store results for analysis
            self.results = result
            
            # Display comprehensive results
            self._display_portfolio_results()
            
            self.logger.info("Portfolio value test completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Portfolio test failed: {e}")
            self.logger.error(traceback.format_exc())
            return False
    
    def _validate_data(self) -> bool:
        """
        Validate the integrity of fetched market data
        
        Returns:
            bool: True if data is valid, False otherwise
        """
        if self.runner.data is None or self.runner.data.empty:
            self.logger.error("No data available for validation")
            return False
        
        # Check for minimum required data points
        min_required_days = 50  # Minimum for meaningful backtest
        if len(self.runner.data) < min_required_days:
            self.logger.error(f"Insufficient data: {len(self.runner.data)} days "
                            f"(minimum required: {min_required_days})")
            return False
        
        # Check for required columns
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns 
                          if col not in self.runner.data.columns]
        
        if missing_columns:
            self.logger.error(f"Missing required data columns: {missing_columns}")
            return False
        
        # Check for data quality issues
        data = self.runner.data
        
        # Check for null values
        null_counts = data.isnull().sum()
        if null_counts.any():
            self.logger.warning(f"Found null values in data: {null_counts[null_counts > 0].to_dict()}")
        
        # Check for unrealistic price values
        if (data['close'] <= 0).any():
            self.logger.error("Found non-positive closing prices")
            return False
        
        self.logger.info(f"Data validation passed: {len(data)} trading days")
        return True
    
    def _display_portfolio_results(self) -> None:
        """
        Display comprehensive portfolio performance results
        """
        if not self.results:
            self.logger.error("No results available to display")
            return
        
        print("\n" + "=" * 70)
        print("🏦 PORTFOLIO VALUE TEST RESULTS")
        print("=" * 70)
        
        # Basic Information
        print(f"📊 Test Configuration:")
        print(f"   Symbol: {self.symbol}")
        print(f"   Period: {self.year}")
        print(f"   Strategy: Moving Average Crossover (10/30 SMA)")
        print(f"   Data Points: {len(self.runner.data) if self.runner.data is not None else 'N/A'}")
        print()
        
        # Portfolio Values
        initial_value = self.results.get('initial_capital', 0)
        final_value = self.results.get('final_capital', 0)
        total_return = self.results.get('total_return', 0)
        
        print(f"💰 Portfolio Performance:")
        print(f"   Initial Portfolio Value: ${initial_value:,.2f}")
        print(f"   Final Portfolio Value:   ${final_value:,.2f}")
        print(f"   Absolute Gain/Loss:      ${final_value - initial_value:,.2f}")
        print(f"   Total Return (ROI):      {total_return:.2%}")
        print()
        
        # Performance Metrics
        print(f"📈 Risk & Return Metrics:")
        print(f"   Annual Return:           {self.results.get('annual_return', 0):.2%}")
        print(f"   Sharpe Ratio:            {self.results.get('sharpe_ratio', 0):.2f}")
        print(f"   Maximum Drawdown:        {self.results.get('max_drawdown', 0):.2%}")
        print(f"   Volatility:              {self.results.get('volatility', 0):.2%}")
        print(f"   Calmar Ratio:            {self.results.get('calmar_ratio', 0):.2f}")
        print(f"   Sortino Ratio:           {self.results.get('sortino_ratio', 0):.2f}")
        print()
        
        # Trading Statistics
        total_trades = self.results.get('total_trades', 0)
        winning_trades = self.results.get('winning_trades', 0)
        losing_trades = self.results.get('losing_trades', 0)
        win_rate = self.results.get('win_rate', 0)
        
        print(f"📊 Trading Activity:")
        print(f"   Total Trades Executed:   {total_trades}")
        print(f"   Winning Trades:          {winning_trades}")
        print(f"   Losing Trades:           {losing_trades}")
        print(f"   Win Rate:                {win_rate:.1%}")
        print(f"   Average Win:             ${self.results.get('avg_win', 0):.2f}")
        print(f"   Average Loss:            ${self.results.get('avg_loss', 0):.2f}")
        print(f"   Profit Factor:           {self.results.get('profit_factor', 0):.2f}")
        print()
        
        # Performance Summary
        self._display_performance_summary(total_return, total_trades)
        
        print("=" * 70)
        print("✅ Test completed successfully!")
        print("📝 Detailed logs saved to: portfolio_test.log")
        print("=" * 70)
    
    def _display_performance_summary(self, total_return: float, total_trades: int) -> None:
        """
        Display a performance summary with interpretation
        
        Args:
            total_return: Total return percentage
            total_trades: Number of trades executed
        """
        print(f"🎯 Performance Summary:")
        
        # Return interpretation
        if total_return > 0.15:  # 15%+
            performance_rating = "Excellent"
            emoji = "🚀"
        elif total_return > 0.05:  # 5-15%
            performance_rating = "Good"
            emoji = "📈"
        elif total_return > -0.05:  # -5% to 5%
            performance_rating = "Neutral"
            emoji = "➡️"
        else:  # < -5%
            performance_rating = "Poor"
            emoji = "📉"
        
        print(f"   Strategy Performance:    {performance_rating} {emoji}")
        
        # Trading activity assessment
        if total_trades == 0:
            activity_rating = "No trades executed"
        elif total_trades < 5:
            activity_rating = "Low activity"
        elif total_trades < 20:
            activity_rating = "Moderate activity"
        else:
            activity_rating = "High activity"
        
        print(f"   Trading Activity:        {activity_rating}")
        
        # Risk assessment
        max_drawdown = abs(self.results.get('max_drawdown', 0))
        if max_drawdown < 0.05:  # < 5%
            risk_rating = "Low risk"
        elif max_drawdown < 0.15:  # 5-15%
            risk_rating = "Moderate risk"
        else:  # > 15%
            risk_rating = "High risk"
        
        print(f"   Risk Level:              {risk_rating}")
        print()


def main():
    """
    Main function to execute the portfolio value test
    
    Implements comprehensive error handling and security best practices
    """
    print("🔧 Nautilus Trader Engine - Portfolio Value Test")
    print("=" * 50)
    
    # Test configuration (easily modifiable for different scenarios)
    test_configs = [
        {
            'symbol': 'AAPL',
            'year': 2023,
            'initial_capital': 100000.0,
            'description': 'Apple Inc. - Standard Test'
        }
    ]
    
    successful_tests = 0
    total_tests = len(test_configs)
    
    for i, config in enumerate(test_configs, 1):
        print(f"\n🧪 Running Test {i}/{total_tests}: {config['description']}")
        print("-" * 50)
        
        try:
            # Create tester instance with validated parameters
            tester = PortfolioValueTester(
                symbol=config['symbol'],
                year=config['year'],
                initial_capital=config['initial_capital']
            )
            
            # Execute test
            if tester.run_portfolio_test():
                successful_tests += 1
                print(f"✅ Test {i} completed successfully")
            else:
                print(f"❌ Test {i} failed")
                
        except ValueError as e:
            print(f"❌ Test {i} failed due to invalid parameters: {e}")
        except Exception as e:
            print(f"❌ Test {i} failed due to unexpected error: {e}")
            logging.error(f"Unexpected error in test {i}: {e}")
            logging.error(traceback.format_exc())
    
    # Final summary
    print(f"\n📊 Test Summary:")
    print(f"   Tests Completed: {successful_tests}/{total_tests}")
    print(f"   Success Rate: {(successful_tests/total_tests)*100:.1f}%")
    
    if successful_tests == total_tests:
        print("🎉 All tests passed successfully!")
        return 0
    else:
        print("⚠️  Some tests failed. Check logs for details.")
        return 1


if __name__ == "__main__":
    """
    Entry point with proper error handling and exit codes
    """
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        logging.error(f"Fatal error: {e}")
        logging.error(traceback.format_exc())
        sys.exit(1)