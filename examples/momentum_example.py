"""Momentum Strategies Example

This example demonstrates how to use the momentum strategy module,
including trend following and momentum breakout strategies.

Features demonstrated:
- Trend following strategies (MA, MACD, ADX)
- Momentum breakout strategies (Price, Volume, Volatility)
- Strategy configuration and parameter tuning
- Signal generation and analysis
- Performance monitoring and evaluation
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Import momentum strategies
from strategies.momentum import (
    TrendFollowingStrategy,
    MovingAverageTrendStrategy,
    MACDTrendStrategy,
    ADXTrendStrategy,
    PriceMomentumBreakoutStrategy,
    VolumeMomentumBreakoutStrategy,
    VolatilityMomentumBreakoutStrategy,
    TrendAnalyzer,
    MomentumAnalyzer,
    create_momentum_strategy
)

# Import base components
from strategies.base_strategy import StrategyConfig
from strategies.signal_generator import SignalType, SignalStrength

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_sample_data(symbol: str = "AAPL", days: int = 100) -> List[Dict]:
    """Generate sample market data for testing"""
    np.random.seed(42)
    
    # Generate realistic price data
    base_price = 150.0
    dates = pd.date_range(start=datetime.now() - timedelta(days=days), periods=days, freq='D')
    
    data = []
    current_price = base_price
    
    for i, date in enumerate(dates):
        # Add trend and noise
        trend = 0.001 * np.sin(i / 20) + 0.0005  # Slight upward trend with cycles
        noise = np.random.normal(0, 0.02)
        
        # Calculate price change
        price_change = current_price * (trend + noise)
        current_price += price_change
        
        # Generate OHLC data
        high = current_price * (1 + abs(np.random.normal(0, 0.01)))
        low = current_price * (1 - abs(np.random.normal(0, 0.01)))
        open_price = current_price + np.random.normal(0, current_price * 0.005)
        close = current_price
        
        # Generate volume data
        base_volume = 1000000
        volume_noise = np.random.normal(1, 0.3)
        volume = int(base_volume * max(0.1, volume_noise))
        
        data.append({
            'symbol': symbol,
            'timestamp': date,
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close, 2),
            'volume': volume
        })
    
    return data

def test_trend_following_strategies():
    """Test trend following strategies"""
    logger.info("Testing Trend Following Strategies")
    logger.info("=" * 50)
    
    # Generate sample data
    market_data = generate_sample_data("AAPL", 100)
    
    # Test Moving Average Trend Strategy
    logger.info("\n1. Moving Average Trend Strategy")
    ma_config = StrategyConfig(
        name="MA_Trend_Strategy",
        symbols=["AAPL"],
        parameters={
            'short_period': 10,
            'long_period': 20,
            'trend_threshold': 0.02,
            'volume_confirmation': True,
            'risk_reward_ratio': 2.0
        }
    )
    
    ma_strategy = MovingAverageTrendStrategy(ma_config)
    ma_signals = ma_strategy.generate_signals(market_data)
    
    logger.info(f"Generated {len(ma_signals)} MA trend signals")
    for signal in ma_signals[:3]:  # Show first 3 signals
        logger.info(f"  Signal: {signal.signal_type.value} at ${signal.entry_price:.2f}, "
                   f"Strength: {signal.strength.value}, Confidence: {signal.confidence:.2f}")
    
    # Test MACD Trend Strategy
    logger.info("\n2. MACD Trend Strategy")
    macd_config = StrategyConfig(
        name="MACD_Trend_Strategy",
        symbols=["AAPL"],
        parameters={
            'fast_period': 12,
            'slow_period': 26,
            'signal_period': 9,
            'trend_threshold': 0.5,
            'volume_confirmation': True,
            'risk_reward_ratio': 2.5
        }
    )
    
    macd_strategy = MACDTrendStrategy(macd_config)
    macd_signals = macd_strategy.generate_signals(market_data)
    
    logger.info(f"Generated {len(macd_signals)} MACD trend signals")
    for signal in macd_signals[:3]:
        logger.info(f"  Signal: {signal.signal_type.value} at ${signal.entry_price:.2f}, "
                   f"Strength: {signal.strength.value}, Confidence: {signal.confidence:.2f}")
    
    # Test ADX Trend Strategy
    logger.info("\n3. ADX Trend Strategy")
    adx_config = StrategyConfig(
        name="ADX_Trend_Strategy",
        symbols=["AAPL"],
        parameters={
            'adx_period': 14,
            'adx_threshold': 25,
            'trend_strength_threshold': 30,
            'volume_confirmation': False,
            'risk_reward_ratio': 2.0
        }
    )
    
    adx_strategy = ADXTrendStrategy(adx_config)
    adx_signals = adx_strategy.generate_signals(market_data)
    
    logger.info(f"Generated {len(adx_signals)} ADX trend signals")
    for signal in adx_signals[:3]:
        logger.info(f"  Signal: {signal.signal_type.value} at ${signal.entry_price:.2f}, "
                   f"Strength: {signal.strength.value}, Confidence: {signal.confidence:.2f}")

def test_momentum_breakout_strategies():
    """Test momentum breakout strategies"""
    logger.info("\n\nTesting Momentum Breakout Strategies")
    logger.info("=" * 50)
    
    # Generate sample data with more volatility for breakouts
    market_data = generate_sample_data("TSLA", 80)
    
    # Test Price Momentum Breakout Strategy
    logger.info("\n1. Price Momentum Breakout Strategy")
    price_config = StrategyConfig(
        name="Price_Momentum_Breakout",
        symbols=["TSLA"],
        parameters={
            'momentum_period': 14,
            'breakout_threshold': 2.0,
            'momentum_threshold': 0.3,
            'min_persistence': 0.2,
            'volume_confirmation': True,
            'risk_reward_ratio': 2.0
        }
    )
    
    price_strategy = PriceMomentumBreakoutStrategy(price_config)
    price_signals = price_strategy.generate_signals(market_data)
    
    logger.info(f"Generated {len(price_signals)} price momentum signals")
    for signal in price_signals[:3]:
        logger.info(f"  Signal: {signal.signal_type.value} at ${signal.entry_price:.2f}, "
                   f"Strength: {signal.strength.value}, Confidence: {signal.confidence:.2f}")
        if signal.metadata:
            logger.info(f"    Price Momentum: {signal.metadata.get('price_momentum', 0):.2f}%")
            logger.info(f"    Momentum Score: {signal.metadata.get('momentum_score', 0):.3f}")
    
    # Test Volume Momentum Breakout Strategy
    logger.info("\n2. Volume Momentum Breakout Strategy")
    volume_config = StrategyConfig(
        name="Volume_Momentum_Breakout",
        symbols=["TSLA"],
        parameters={
            'volume_momentum_threshold': 50.0,
            'min_volume_spike': 2.0,
            'price_confirmation': True,
            'risk_reward_ratio': 2.5
        }
    )
    
    volume_strategy = VolumeMomentumBreakoutStrategy(volume_config)
    volume_signals = volume_strategy.generate_signals(market_data)
    
    logger.info(f"Generated {len(volume_signals)} volume momentum signals")
    for signal in volume_signals[:3]:
        logger.info(f"  Signal: {signal.signal_type.value} at ${signal.entry_price:.2f}, "
                   f"Strength: {signal.strength.value}, Confidence: {signal.confidence:.2f}")
        if signal.metadata:
            logger.info(f"    Volume Ratio: {signal.metadata.get('volume_ratio', 0):.2f}x")
            logger.info(f"    Volume Momentum: {signal.metadata.get('volume_momentum', 0):.2f}%")
    
    # Test Volatility Momentum Breakout Strategy
    logger.info("\n3. Volatility Momentum Breakout Strategy")
    volatility_config = StrategyConfig(
        name="Volatility_Momentum_Breakout",
        symbols=["TSLA"],
        parameters={
            'volatility_threshold': 10.0,
            'volatility_expansion_ratio': 1.5,
            'trend_confirmation': True,
            'risk_reward_ratio': 2.0
        }
    )
    
    volatility_strategy = VolatilityMomentumBreakoutStrategy(volatility_config)
    volatility_signals = volatility_strategy.generate_signals(market_data)
    
    logger.info(f"Generated {len(volatility_signals)} volatility momentum signals")
    for signal in volatility_signals[:3]:
        logger.info(f"  Signal: {signal.signal_type.value} at ${signal.entry_price:.2f}, "
                   f"Strength: {signal.strength.value}, Confidence: {signal.confidence:.2f}")
        if signal.metadata:
            logger.info(f"    Volatility Momentum: {signal.metadata.get('volatility_momentum', 0):.2f}%")
            logger.info(f"    Direction: {signal.metadata.get('direction', 'neutral')}")

def test_momentum_analyzers():
    """Test momentum analysis engines"""
    logger.info("\n\nTesting Momentum Analyzers")
    logger.info("=" * 50)
    
    # Generate sample data
    market_data = generate_sample_data("NVDA", 60)
    df = pd.DataFrame(market_data)
    
    # Test Trend Analyzer
    logger.info("\n1. Trend Analyzer")
    trend_analyzer = TrendAnalyzer()
    trend_metrics = trend_analyzer.analyze_comprehensive_trend(df)
    
    logger.info(f"Trend Direction: {trend_metrics.direction.value}")
    logger.info(f"Trend Strength: {trend_metrics.strength.value}")
    logger.info(f"Trend Confidence: {trend_metrics.confidence:.3f}")
    logger.info(f"Trend Persistence: {trend_metrics.persistence:.3f}")
    logger.info(f"MA Trend Score: {trend_metrics.ma_trend_score:.3f}")
    logger.info(f"MACD Signal: {trend_metrics.macd_signal:.3f}")
    logger.info(f"ADX Value: {trend_metrics.adx_value:.2f}")
    
    # Test Momentum Analyzer
    logger.info("\n2. Momentum Analyzer")
    momentum_analyzer = MomentumAnalyzer()
    momentum_metrics = momentum_analyzer.analyze_comprehensive_momentum(df)
    
    logger.info(f"Momentum Direction: {momentum_metrics.direction.value}")
    logger.info(f"Momentum Strength: {momentum_metrics.strength.value}")
    logger.info(f"Momentum Score: {momentum_metrics.momentum_score:.3f}")
    logger.info(f"Price Momentum: {momentum_metrics.price_momentum:.2f}%")
    logger.info(f"Volume Momentum: {momentum_metrics.volume_momentum:.2f}%")
    logger.info(f"Volatility Momentum: {momentum_metrics.volatility_momentum:.2f}%")
    logger.info(f"Persistence: {momentum_metrics.persistence:.3f}")
    logger.info(f"Volume Confirmation: {momentum_metrics.volume_confirmation}")
    logger.info(f"Volume Ratio: {momentum_metrics.volume_ratio:.2f}x")

def test_strategy_factory():
    """Test momentum strategy factory function"""
    logger.info("\n\nTesting Strategy Factory")
    logger.info("=" * 50)
    
    # Test creating different strategies via factory
    strategies_to_test = [
        ("trend_following", {"short_period": 10, "long_period": 20}),
        ("macd_trend", {"fast_period": 12, "slow_period": 26}),
        ("adx_trend", {"adx_period": 14, "adx_threshold": 25}),
        ("price_momentum", {"momentum_period": 14, "breakout_threshold": 2.0}),
        ("volume_momentum", {"volume_momentum_threshold": 50.0}),
        ("volatility_momentum", {"volatility_threshold": 10.0})
    ]
    
    for strategy_type, params in strategies_to_test:
        try:
            config = StrategyConfig(
                name=f"Factory_{strategy_type}",
                symbols=["TEST"],
                parameters=params
            )
            
            strategy = create_momentum_strategy(strategy_type, config)
            logger.info(f"✓ Successfully created {strategy_type} strategy: {strategy.__class__.__name__}")
            
        except Exception as e:
            logger.error(f"✗ Failed to create {strategy_type} strategy: {e}")

def analyze_strategy_performance():
    """Analyze strategy performance metrics"""
    logger.info("\n\nStrategy Performance Analysis")
    logger.info("=" * 50)
    
    # Generate longer dataset for performance analysis
    market_data = generate_sample_data("SPY", 200)
    
    strategies = [
        ("MA Trend", MovingAverageTrendStrategy(StrategyConfig(
            name="MA_Performance_Test",
            symbols=["SPY"],
            parameters={'short_period': 10, 'long_period': 20}
        ))),
        ("MACD Trend", MACDTrendStrategy(StrategyConfig(
            name="MACD_Performance_Test",
            symbols=["SPY"],
            parameters={'fast_period': 12, 'slow_period': 26, 'signal_period': 9}
        ))),
        ("Price Momentum", PriceMomentumBreakoutStrategy(StrategyConfig(
            name="Price_Momentum_Performance_Test",
            symbols=["SPY"],
            parameters={'momentum_period': 14, 'breakout_threshold': 1.5}
        )))
    ]
    
    for strategy_name, strategy in strategies:
        try:
            signals = strategy.generate_signals(market_data)
            
            # Calculate basic performance metrics
            total_signals = len(signals)
            buy_signals = len([s for s in signals if s.signal_type == SignalType.BUY])
            sell_signals = len([s for s in signals if s.signal_type == SignalType.SELL])
            
            avg_confidence = np.mean([s.confidence for s in signals]) if signals else 0
            strong_signals = len([s for s in signals if s.strength == SignalStrength.STRONG])
            
            logger.info(f"\n{strategy_name} Performance:")
            logger.info(f"  Total Signals: {total_signals}")
            logger.info(f"  Buy Signals: {buy_signals}")
            logger.info(f"  Sell Signals: {sell_signals}")
            logger.info(f"  Average Confidence: {avg_confidence:.3f}")
            logger.info(f"  Strong Signals: {strong_signals} ({strong_signals/total_signals*100:.1f}%)" if total_signals > 0 else "  Strong Signals: 0 (0.0%)")
            
        except Exception as e:
            logger.error(f"Error analyzing {strategy_name}: {e}")

def main():
    """Main example execution"""
    logger.info("Momentum Strategies Example")
    logger.info("=" * 60)
    
    try:
        # Test trend following strategies
        test_trend_following_strategies()
        
        # Test momentum breakout strategies
        test_momentum_breakout_strategies()
        
        # Test analyzers
        test_momentum_analyzers()
        
        # Test factory function
        test_strategy_factory()
        
        # Analyze performance
        analyze_strategy_performance()
        
        logger.info("\n" + "=" * 60)
        logger.info("Momentum Strategies Example Completed Successfully!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Error in momentum strategies example: {e}")
        raise

if __name__ == "__main__":
    main()