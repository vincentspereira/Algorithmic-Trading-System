"""Arbitrage & Statistical Strategies Example

This example demonstrates the usage of arbitrage and statistical strategies
including index arbitrage, volatility arbitrage, and multi-factor models.

Features demonstrated:
- Index arbitrage strategy configuration and execution
- Volatility arbitrage with implied vs realized volatility
- Multi-factor models (Fama-French, momentum, quality)
- Strategy backtesting and performance analysis
- Risk management and position sizing
- Integration with strategy management system
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Core imports
from core.data_types import MarketData, Signal, Position
from core.events import SignalEvent, OrderEvent
from core.risk_management import RiskManager, RiskConfig
from core.portfolio_management import PortfolioManager, PortfolioConfig
from core.signal_generator import SignalGenerator
from core.strategy_manager import StrategyManager

# Strategy imports
from strategies.arbitrage import (
    IndexArbitrageStrategy,
    VolatilityArbitrageStrategy,
    MultiFactorStrategy,
    FamaFrenchStrategy,
    MomentumFactorStrategy,
    QualityFactorStrategy,
    create_arbitrage_strategy
)
from strategies.base_strategy import StrategyConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_sample_data(symbols: List[str], days: int = 252) -> Dict[str, pd.DataFrame]:
    """Generate sample market data for testing
    
    Args:
        symbols: List of symbols to generate data for
        days: Number of days of data
        
    Returns:
        Dictionary of DataFrames with OHLCV data
    """
    np.random.seed(42)  # For reproducible results
    
    data = {}
    base_date = datetime.now() - timedelta(days=days)
    
    for symbol in symbols:
        dates = pd.date_range(start=base_date, periods=days, freq='D')
        
        # Generate realistic price data with different characteristics
        if 'SPY' in symbol:  # ETF - lower volatility
            returns = np.random.normal(0.0005, 0.012, days)  # ~12% annual vol
            initial_price = 400.0
        elif 'QQQ' in symbol:  # Tech ETF - higher volatility
            returns = np.random.normal(0.0008, 0.018, days)  # ~18% annual vol
            initial_price = 350.0
        elif symbol.startswith('AAPL'):  # Individual stock
            returns = np.random.normal(0.001, 0.025, days)   # ~25% annual vol
            initial_price = 150.0
        else:  # Other stocks
            returns = np.random.normal(0.0006, 0.02, days)   # ~20% annual vol
            initial_price = 100.0
        
        # Calculate prices
        prices = [initial_price]
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        # Generate OHLCV data
        df = pd.DataFrame(index=dates)
        df['close'] = prices
        
        # Generate realistic OHLC from close prices
        daily_range = np.random.uniform(0.005, 0.03, days)  # 0.5% to 3% daily range
        
        df['high'] = df['close'] * (1 + daily_range * np.random.uniform(0.3, 1.0, days))
        df['low'] = df['close'] * (1 - daily_range * np.random.uniform(0.3, 1.0, days))
        df['open'] = df['close'].shift(1) * (1 + np.random.normal(0, 0.005, days))
        df['open'].iloc[0] = initial_price
        
        # Generate volume (higher volume on higher volatility days)
        base_volume = 1000000 if 'SPY' in symbol or 'QQQ' in symbol else 500000
        volume_multiplier = 1 + abs(returns) * 10  # Higher volume on big moves
        df['volume'] = (base_volume * volume_multiplier * np.random.uniform(0.5, 2.0, days)).astype(int)
        
        data[symbol] = df
    
    return data

def generate_fundamental_data(symbols: List[str]) -> Dict[str, Dict[str, float]]:
    """Generate sample fundamental data for factor analysis
    
    Args:
        symbols: List of symbols
        
    Returns:
        Dictionary of fundamental metrics by symbol
    """
    np.random.seed(42)
    
    fundamental_data = {}
    
    for symbol in symbols:
        if symbol in ['SPY', 'QQQ']:  # Skip ETFs
            continue
            
        # Generate realistic fundamental metrics
        data = {
            # Valuation metrics
            'pe_ratio': np.random.uniform(8, 35),
            'pb_ratio': np.random.uniform(0.5, 5.0),
            'ps_ratio': np.random.uniform(0.5, 8.0),
            'ev_ebitda': np.random.uniform(5, 25),
            
            # Profitability metrics
            'roe': np.random.uniform(0.05, 0.25),
            'roa': np.random.uniform(0.02, 0.15),
            'roic': np.random.uniform(0.08, 0.30),
            'gross_margin': np.random.uniform(0.20, 0.70),
            'operating_margin': np.random.uniform(0.05, 0.30),
            'net_margin': np.random.uniform(0.02, 0.20),
            
            # Growth metrics
            'revenue_growth': np.random.uniform(-0.10, 0.30),
            'earnings_growth': np.random.uniform(-0.20, 0.50),
            'book_value_growth': np.random.uniform(-0.05, 0.25),
            
            # Quality metrics
            'debt_to_equity': np.random.uniform(0.1, 2.0),
            'interest_coverage': np.random.uniform(2, 20),
            'earnings_volatility': np.random.uniform(0.1, 0.8),
            
            # Size metric
            'market_cap': np.random.uniform(1e9, 500e9)  # $1B to $500B
        }
        
        fundamental_data[symbol] = data
    
    return fundamental_data

def create_market_data_objects(data: Dict[str, pd.DataFrame]) -> Dict[str, List[MarketData]]:
    """Convert DataFrame data to MarketData objects
    
    Args:
        data: Dictionary of DataFrames
        
    Returns:
        Dictionary of MarketData lists
    """
    market_data = {}
    
    for symbol, df in data.items():
        market_data[symbol] = []
        
        for timestamp, row in df.iterrows():
            md = MarketData(
                timestamp=timestamp,
                symbol=symbol,
                open=row['open'],
                high=row['high'],
                low=row['low'],
                close=row['close'],
                volume=int(row['volume'])
            )
            market_data[symbol].append(md)
    
    return market_data

def test_index_arbitrage_strategy():
    """Test index arbitrage strategy"""
    logger.info("\n=== Testing Index Arbitrage Strategy ===")
    
    # Create strategy configuration
    config = StrategyConfig(
        name="IndexArbitrageTest",
        strategy_type="index_arbitrage",
        parameters={
            'index_symbol': 'SPY',
            'basket_symbols': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'],
            'basket_weights': [0.25, 0.20, 0.20, 0.20, 0.15],
            'min_arbitrage_threshold': 0.002,  # 0.2% minimum spread
            'max_position_size': 0.10,
            'rebalance_frequency': 1,  # Daily
            'transaction_costs': 0.001  # 0.1% transaction costs
        }
    )
    
    # Create strategy
    strategy = IndexArbitrageStrategy(config)
    
    # Generate sample data
    symbols = ['SPY', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
    sample_data = generate_sample_data(symbols, days=100)
    
    # Test strategy with recent data
    recent_data = {}
    for symbol in symbols:
        recent_row = sample_data[symbol].iloc[-1]
        recent_data[symbol] = MarketData(
            timestamp=recent_row.name,
            symbol=symbol,
            open=recent_row['open'],
            high=recent_row['high'],
            low=recent_row['low'],
            close=recent_row['close'],
            volume=int(recent_row['volume'])
        )
    
    # Generate signals
    signals = strategy.generate_signals(recent_data)
    
    logger.info(f"Generated {len(signals)} index arbitrage signals")
    for signal in signals:
        logger.info(f"Signal: {signal.signal_type} {signal.symbol} - "
                   f"Strength: {signal.strength:.3f}, Confidence: {signal.confidence:.3f}")

def test_volatility_arbitrage_strategy():
    """Test volatility arbitrage strategy"""
    logger.info("\n=== Testing Volatility Arbitrage Strategy ===")
    
    # Create strategy configuration
    config = StrategyConfig(
        name="VolatilityArbitrageTest",
        strategy_type="volatility_arbitrage",
        parameters={
            'underlying_symbols': ['SPY', 'QQQ', 'AAPL'],
            'volatility_lookback': 30,
            'min_vol_spread': 0.02,  # 2% minimum volatility spread
            'max_position_size': 0.05,
            'hedge_ratio': 0.8,
            'rebalance_frequency': 5  # Weekly
        }
    )
    
    # Create strategy
    strategy = VolatilityArbitrageStrategy(config)
    
    # Generate sample data
    symbols = ['SPY', 'QQQ', 'AAPL']
    sample_data = generate_sample_data(symbols, days=100)
    
    # Update strategy with historical data for volatility calculation
    for symbol in symbols:
        df = sample_data[symbol]
        for timestamp, row in df.iterrows():
            md = MarketData(
                timestamp=timestamp,
                symbol=symbol,
                open=row['open'],
                high=row['high'],
                low=row['low'],
                close=row['close'],
                volume=int(row['volume'])
            )
            strategy.update_price_data(symbol, md)
    
    # Test with recent data
    recent_data = {}
    for symbol in symbols:
        recent_row = sample_data[symbol].iloc[-1]
        recent_data[symbol] = MarketData(
            timestamp=recent_row.name,
            symbol=symbol,
            open=recent_row['open'],
            high=recent_row['high'],
            low=recent_row['low'],
            close=recent_row['close'],
            volume=int(recent_row['volume'])
        )
    
    # Generate signals
    signals = strategy.generate_signals(recent_data)
    
    logger.info(f"Generated {len(signals)} volatility arbitrage signals")
    for signal in signals:
        logger.info(f"Signal: {signal.signal_type} {signal.symbol} - "
                   f"Strength: {signal.strength:.3f}, Expected Return: {signal.expected_return:.3f}")

def test_multi_factor_strategy():
    """Test multi-factor strategy"""
    logger.info("\n=== Testing Multi-Factor Strategy ===")
    
    # Create strategy configuration
    config = StrategyConfig(
        name="MultiFactorTest",
        strategy_type="multi_factor",
        parameters={
            'factors': ['value', 'momentum', 'quality'],
            'rebalance_frequency': 21,  # Monthly
            'long_pct': 0.2,
            'short_pct': 0.2,
            'max_position_size': 0.05,
            'lookback_period': 252
        }
    )
    
    # Create strategy
    strategy = MultiFactorStrategy(config)
    
    # Generate sample data
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX', 'CRM', 'ADBE']
    sample_data = generate_sample_data(symbols, days=100)
    fundamental_data = generate_fundamental_data(symbols)
    
    # Update fundamental data
    for symbol, data in fundamental_data.items():
        strategy.update_fundamental_data(symbol, data)
    
    # Update price data
    for symbol in symbols:
        df = sample_data[symbol]
        for timestamp, row in df.iterrows():
            strategy.analyzer.price_data[symbol] = df['close']
    
    # Test with recent data
    recent_data = {}
    for symbol in symbols:
        recent_row = sample_data[symbol].iloc[-1]
        recent_data[symbol] = MarketData(
            timestamp=recent_row.name,
            symbol=symbol,
            open=recent_row['open'],
            high=recent_row['high'],
            low=recent_row['low'],
            close=recent_row['close'],
            volume=int(recent_row['volume'])
        )
    
    # Generate signals
    signals = strategy.generate_signals(recent_data)
    
    logger.info(f"Generated {len(signals)} multi-factor signals")
    for signal in signals:
        logger.info(f"Signal: {signal.signal_type} {signal.symbol} - "
                   f"Strength: {signal.strength:.3f}, Composite Score: {signal.metadata.get('composite_score', 0):.3f}")

def test_fama_french_strategy():
    """Test Fama-French factor strategy"""
    logger.info("\n=== Testing Fama-French Strategy ===")
    
    # Create strategy configuration
    config = StrategyConfig(
        name="FamaFrenchTest",
        strategy_type="fama_french",
        parameters={
            'model_type': '3_factor',  # or '5_factor'
            'rebalance_frequency': 21,
            'long_pct': 0.3,
            'short_pct': 0.3,
            'max_position_size': 0.04
        }
    )
    
    # Create strategy
    strategy = FamaFrenchStrategy(config)
    
    # Generate sample data
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX']
    sample_data = generate_sample_data(symbols, days=100)
    fundamental_data = generate_fundamental_data(symbols)
    
    # Update fundamental data
    for symbol, data in fundamental_data.items():
        strategy.update_fundamental_data(symbol, data)
    
    # Update price data
    for symbol in symbols:
        df = sample_data[symbol]
        strategy.analyzer.price_data[symbol] = df['close']
    
    # Test with recent data
    recent_data = {}
    for symbol in symbols:
        recent_row = sample_data[symbol].iloc[-1]
        recent_data[symbol] = MarketData(
            timestamp=recent_row.name,
            symbol=symbol,
            open=recent_row['open'],
            high=recent_row['high'],
            low=recent_row['low'],
            close=recent_row['close'],
            volume=int(recent_row['volume'])
        )
    
    # Generate signals
    signals = strategy.generate_signals(recent_data)
    
    logger.info(f"Generated {len(signals)} Fama-French signals")
    for signal in signals:
        factors = signal.metadata.get('factors', [])
        logger.info(f"Signal: {signal.signal_type} {signal.symbol} - "
                   f"Factors: {factors}, Strength: {signal.strength:.3f}")

def test_strategy_integration():
    """Test integration with strategy management system"""
    logger.info("\n=== Testing Strategy Integration ===")
    
    # Create risk manager
    risk_config = RiskConfig(
        max_portfolio_risk=0.15,
        max_position_size=0.10,
        max_sector_exposure=0.30,
        var_confidence=0.95,
        var_horizon=1
    )
    risk_manager = RiskManager(risk_config)
    
    # Create portfolio manager
    portfolio_config = PortfolioConfig(
        initial_capital=1000000,
        max_positions=20,
        rebalance_frequency=21
    )
    portfolio_manager = PortfolioManager(portfolio_config)
    
    # Create signal generator
    signal_generator = SignalGenerator()
    
    # Create strategy manager
    strategy_manager = StrategyManager(
        risk_manager=risk_manager,
        portfolio_manager=portfolio_manager,
        signal_generator=signal_generator
    )
    
    # Create multiple strategies
    strategies = [
        create_arbitrage_strategy({
            'name': 'IndexArb',
            'type': 'index_arbitrage',
            'index_symbol': 'SPY',
            'basket_symbols': ['AAPL', 'MSFT', 'GOOGL'],
            'basket_weights': [0.4, 0.3, 0.3]
        }),
        create_arbitrage_strategy({
            'name': 'VolArb',
            'type': 'volatility_arbitrage',
            'underlying_symbols': ['QQQ', 'AAPL']
        }),
        create_arbitrage_strategy({
            'name': 'MultiFactorMomentum',
            'type': 'momentum_factor',
            'factors': ['momentum']
        })
    ]
    
    # Add strategies to manager
    for strategy in strategies:
        if strategy:
            strategy_manager.add_strategy(strategy)
    
    logger.info(f"Added {len(strategies)} strategies to manager")
    logger.info("Strategy integration test completed successfully")

def run_performance_analysis(signals: List[Signal]):
    """Run basic performance analysis on generated signals
    
    Args:
        signals: List of signals to analyze
    """
    if not signals:
        logger.info("No signals to analyze")
        return
    
    logger.info("\n=== Performance Analysis ===")
    
    # Signal statistics
    buy_signals = [s for s in signals if s.signal_type == 'BUY']
    sell_signals = [s for s in signals if s.signal_type == 'SELL']
    
    logger.info(f"Total signals: {len(signals)}")
    logger.info(f"Buy signals: {len(buy_signals)} ({len(buy_signals)/len(signals)*100:.1f}%)")
    logger.info(f"Sell signals: {len(sell_signals)} ({len(sell_signals)/len(signals)*100:.1f}%)")
    
    # Strength and confidence analysis
    strengths = [s.strength for s in signals]
    confidences = [s.confidence for s in signals]
    expected_returns = [s.expected_return for s in signals if s.expected_return is not None]
    
    if strengths:
        logger.info(f"Average signal strength: {np.mean(strengths):.3f} (±{np.std(strengths):.3f})")
    if confidences:
        logger.info(f"Average confidence: {np.mean(confidences):.3f} (±{np.std(confidences):.3f})")
    if expected_returns:
        logger.info(f"Average expected return: {np.mean(expected_returns):.3f} (±{np.std(expected_returns):.3f})")
    
    # Symbol distribution
    symbol_counts = {}
    for signal in signals:
        symbol_counts[signal.symbol] = symbol_counts.get(signal.symbol, 0) + 1
    
    logger.info("\nSignal distribution by symbol:")
    for symbol, count in sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {symbol}: {count} signals")

def main():
    """Main function to run all arbitrage strategy examples"""
    logger.info("Starting Arbitrage & Statistical Strategies Example")
    logger.info("=" * 60)
    
    try:
        # Test individual strategies
        test_index_arbitrage_strategy()
        test_volatility_arbitrage_strategy()
        test_multi_factor_strategy()
        test_fama_french_strategy()
        
        # Test integration
        test_strategy_integration()
        
        logger.info("\n" + "=" * 60)
        logger.info("All arbitrage strategy tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in arbitrage strategy example: {e}")
        raise

if __name__ == "__main__":
    main()