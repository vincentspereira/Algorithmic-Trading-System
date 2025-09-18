"""Volatility Breakout Strategy Example

This example demonstrates how to use the volatility breakout strategies
including range breakout and volatility expansion strategies.

Features demonstrated:
- Bollinger Band breakout strategy
- Donchian Channel breakout strategy  
- Keltner Channel breakout strategy
- Volatility expansion strategy
- Multi-strategy coordination
- Risk management integration
- Performance monitoring
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Import strategy components
from strategies.volatility_breakout import (
    BollingerBandBreakoutStrategy,
    DonchianChannelBreakoutStrategy,
    KeltnerChannelBreakoutStrategy,
    VolatilityExpansionStrategy,
    VolatilityAnalyzer,
    VolatilityAnalysisEngine,
    calculate_volatility_metrics
)

from strategies.pairs_trading_strategies import StrategyConfig
from strategies.strategy_manager import StrategyManager
from strategies.strategy_factory import StrategyFactory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_sample_data(days: int = 252) -> pd.DataFrame:
    """Generate sample market data for testing"""
    try:
        # Generate realistic price data with volatility clustering
        np.random.seed(42)
        
        dates = pd.date_range(start='2023-01-01', periods=days, freq='D')
        
        # Base price trend
        base_price = 100.0
        prices = [base_price]
        volumes = []
        
        # Volatility regimes
        low_vol_periods = [(50, 80), (150, 180)]  # Low volatility periods
        high_vol_periods = [(20, 40), (200, 230)]  # High volatility periods
        
        for i in range(1, days):
            # Determine volatility regime
            vol_multiplier = 1.0
            for start, end in low_vol_periods:
                if start <= i <= end:
                    vol_multiplier = 0.3
                    break
            for start, end in high_vol_periods:
                if start <= i <= end:
                    vol_multiplier = 2.5
                    break
            
            # Generate return with volatility clustering
            daily_return = np.random.normal(0.0005, 0.02 * vol_multiplier)
            new_price = prices[-1] * (1 + daily_return)
            prices.append(new_price)
            
            # Generate volume (higher during high volatility)
            base_volume = 1000000
            volume_multiplier = 1.0 + (vol_multiplier - 1.0) * 0.5
            volume = int(base_volume * volume_multiplier * np.random.uniform(0.5, 2.0))
            volumes.append(volume)
        
        # Create OHLC data
        df = pd.DataFrame({
            'date': dates,
            'close': prices[1:],  # Skip first price
            'volume': volumes
        })
        
        # Generate OHLC from close prices
        df['open'] = df['close'].shift(1).fillna(df['close'].iloc[0])
        df['high'] = df[['open', 'close']].max(axis=1) * np.random.uniform(1.0, 1.02, len(df))
        df['low'] = df[['open', 'close']].min(axis=1) * np.random.uniform(0.98, 1.0, len(df))
        
        # Ensure high >= close >= low and high >= open >= low
        df['high'] = df[['high', 'open', 'close']].max(axis=1)
        df['low'] = df[['low', 'open', 'close']].min(axis=1)
        
        return df
        
    except Exception as e:
        logger.error(f"Error generating sample data: {e}")
        return pd.DataFrame()

def demonstrate_range_breakout_strategies():
    """Demonstrate range breakout strategies"""
    logger.info("=== Range Breakout Strategies Demo ===")
    
    try:
        # Generate sample data
        df = generate_sample_data(100)
        if df.empty:
            logger.error("Failed to generate sample data")
            return
        
        logger.info(f"Generated {len(df)} days of sample data")
        
        # Create strategy configurations
        bollinger_config = StrategyConfig(
            strategy_id="bollinger_breakout",
            symbols=["AAPL"],
            parameters={
                'period': 20,
                'std_dev': 2.0,
                'volume_confirmation': True,
                'min_volume_ratio': 1.5
            }
        )
        
        donchian_config = StrategyConfig(
            strategy_id="donchian_breakout",
            symbols=["AAPL"],
            parameters={
                'period': 20,
                'volume_confirmation': True,
                'min_volume_ratio': 1.3
            }
        )
        
        keltner_config = StrategyConfig(
            strategy_id="keltner_breakout",
            symbols=["AAPL"],
            parameters={
                'period': 20,
                'multiplier': 2.0,
                'volume_confirmation': True
            }
        )
        
        # Create strategies
        bollinger_strategy = BollingerBandBreakoutStrategy(bollinger_config)
        donchian_strategy = DonchianChannelBreakoutStrategy(donchian_config)
        keltner_strategy = KeltnerChannelBreakoutStrategy(keltner_config)
        
        strategies = [
            ("Bollinger Band Breakout", bollinger_strategy),
            ("Donchian Channel Breakout", donchian_strategy),
            ("Keltner Channel Breakout", keltner_strategy)
        ]
        
        # Test each strategy
        for strategy_name, strategy in strategies:
            logger.info(f"\n--- Testing {strategy_name} ---")
            
            signals_generated = 0
            
            # Process data in chunks to simulate real-time
            for i in range(30, len(df)):  # Start after sufficient data
                market_data = df.iloc[:i+1].to_dict('records')
                
                # Generate signals
                signals = strategy.generate_signals(market_data)
                
                if signals:
                    signals_generated += len(signals)
                    for signal in signals:
                        logger.info(f"Signal: {signal.signal_type.value} at {signal.entry_price:.2f}")
                        logger.info(f"  Confidence: {signal.confidence:.2f}")
                        logger.info(f"  Stop Loss: {signal.stop_loss:.2f}")
                        logger.info(f"  Take Profit: {signal.take_profit:.2f}")
                        logger.info(f"  Metadata: {signal.metadata}")
            
            logger.info(f"Total signals generated: {signals_generated}")
        
    except Exception as e:
        logger.error(f"Error in range breakout demo: {e}")

def demonstrate_volatility_expansion_strategy():
    """Demonstrate volatility expansion strategy"""
    logger.info("\n=== Volatility Expansion Strategy Demo ===")
    
    try:
        # Generate sample data with volatility clustering
        df = generate_sample_data(150)
        if df.empty:
            logger.error("Failed to generate sample data")
            return
        
        logger.info(f"Generated {len(df)} days of sample data")
        
        # Create strategy configuration
        expansion_config = StrategyConfig(
            strategy_id="volatility_expansion",
            symbols=["AAPL"],
            parameters={
                'min_squeeze_duration': 5,
                'min_expansion_rate': 0.1,
                'volume_confirmation': True,
                'min_volume_ratio': 1.5,
                'volatility_position_sizing': True
            }
        )
        
        # Create strategy
        expansion_strategy = VolatilityExpansionStrategy(expansion_config)
        
        logger.info("--- Testing Volatility Expansion Strategy ---")
        
        signals_generated = 0
        volatility_metrics_logged = 0
        
        # Process data to simulate real-time analysis
        for i in range(50, len(df)):  # Start after sufficient data for volatility analysis
            market_data = df.iloc[:i+1].to_dict('records')
            
            # Analyze market data
            analysis = expansion_strategy.analyze_market_data(market_data)
            
            if analysis:
                # Log volatility metrics periodically
                if i % 20 == 0:
                    volatility_metrics_logged += 1
                    metrics = analysis.get('volatility_metrics')
                    if metrics:
                        logger.info(f"\nVolatility Analysis (Day {i}):")
                        logger.info(f"  ATR: {metrics.atr:.4f}")
                        logger.info(f"  ATR Percentile: {metrics.atr_percentile:.1f}")
                        logger.info(f"  Bollinger Width: {metrics.bollinger_width:.4f}")
                        logger.info(f"  Is Squeeze: {metrics.is_squeeze}")
                        logger.info(f"  Squeeze Duration: {metrics.squeeze_duration}")
                        logger.info(f"  Volatility Regime: {metrics.volatility_regime.value}")
                        logger.info(f"  Expansion Rate: {metrics.expansion_rate:.4f}")
                
                # Check for expansion signals
                expansion = analysis.get('volatility_expansion')
                if expansion:
                    logger.info(f"\nVolatility Expansion Detected (Day {i}):")
                    logger.info(f"  Phase: {expansion.expansion_phase.value}")
                    logger.info(f"  Direction: {expansion.direction.value}")
                    logger.info(f"  Magnitude: {expansion.magnitude:.4f}")
                    logger.info(f"  Rate: {expansion.rate:.4f}")
                    logger.info(f"  Volume Confirmation: {expansion.volume_confirmation}")
                    logger.info(f"  Volume Ratio: {expansion.volume_ratio:.2f}")
            
            # Generate trading signals
            signals = expansion_strategy.generate_signals(market_data)
            
            if signals:
                signals_generated += len(signals)
                for signal in signals:
                    logger.info(f"\nTrading Signal Generated:")
                    logger.info(f"  Type: {signal.signal_type.value}")
                    logger.info(f"  Strength: {signal.strength.value}")
                    logger.info(f"  Confidence: {signal.confidence:.2f}")
                    logger.info(f"  Entry: {signal.entry_price:.2f}")
                    logger.info(f"  Stop Loss: {signal.stop_loss:.2f}")
                    logger.info(f"  Take Profit: {signal.take_profit:.2f}")
                    
                    # Log strategy-specific metadata
                    metadata = signal.metadata
                    logger.info(f"  Expansion Phase: {metadata.get('expansion_phase')}")
                    logger.info(f"  Squeeze Duration: {metadata.get('squeeze_duration')}")
                    logger.info(f"  Position Size Multiplier: {metadata.get('position_size_multiplier', 1.0):.2f}")
        
        logger.info(f"\nSummary:")
        logger.info(f"Total signals generated: {signals_generated}")
        logger.info(f"Volatility metrics logged: {volatility_metrics_logged}")
        
    except Exception as e:
        logger.error(f"Error in volatility expansion demo: {e}")

def demonstrate_volatility_analysis():
    """Demonstrate volatility analysis capabilities"""
    logger.info("\n=== Volatility Analysis Demo ===")
    
    try:
        # Generate sample data
        df = generate_sample_data(100)
        if df.empty:
            logger.error("Failed to generate sample data")
            return
        
        # Create volatility analyzer
        analyzer = VolatilityAnalyzer()
        expansion_analyzer = VolatilityAnalysisEngine()
        
        logger.info("--- Volatility Range Analysis ---")
        
        # Test different range calculations
        close_prices = df['close']
        high_prices = df['high']
        low_prices = df['low']
        
        # Calculate Bollinger Bands
        bollinger_range = analyzer.calculate_bollinger_bands(close_prices, period=20, std_dev=2.0)
        logger.info(f"Bollinger Bands:")
        logger.info(f"  Upper: {bollinger_range.upper_band:.2f}")
        logger.info(f"  Middle: {bollinger_range.middle_line:.2f}")
        logger.info(f"  Lower: {bollinger_range.lower_band:.2f}")
        logger.info(f"  Width: {bollinger_range.range_width:.2f}")
        
        # Calculate Donchian Channels
        donchian_range = analyzer.calculate_donchian_channels(high_prices, low_prices, period=20)
        logger.info(f"\nDonchian Channels:")
        logger.info(f"  Upper: {donchian_range.upper_band:.2f}")
        logger.info(f"  Middle: {donchian_range.middle_line:.2f}")
        logger.info(f"  Lower: {donchian_range.lower_band:.2f}")
        logger.info(f"  Width: {donchian_range.range_width:.2f}")
        
        # Calculate Keltner Channels
        keltner_range = analyzer.calculate_keltner_channels(high_prices, low_prices, close_prices, period=20)
        logger.info(f"\nKeltner Channels:")
        logger.info(f"  Upper: {keltner_range.upper_band:.2f}")
        logger.info(f"  Middle: {keltner_range.middle_line:.2f}")
        logger.info(f"  Lower: {keltner_range.lower_band:.2f}")
        logger.info(f"  Width: {keltner_range.range_width:.2f}")
        
        logger.info("\n--- Comprehensive Volatility Analysis ---")
        
        # Calculate comprehensive volatility metrics
        volatility_metrics = expansion_analyzer.calculate_comprehensive_volatility(df)
        
        logger.info(f"Comprehensive Volatility Metrics:")
        logger.info(f"  ATR: {volatility_metrics.atr:.4f}")
        logger.info(f"  ATR Percentile: {volatility_metrics.atr_percentile:.1f}")
        logger.info(f"  Bollinger Width: {volatility_metrics.bollinger_width:.4f}")
        logger.info(f"  Bollinger Width Percentile: {volatility_metrics.bollinger_width_percentile:.1f}")
        logger.info(f"  Realized Volatility: {volatility_metrics.realized_volatility:.4f}")
        logger.info(f"  Parkinson Volatility: {volatility_metrics.parkinson_volatility:.4f}")
        logger.info(f"  Garman-Klass Volatility: {volatility_metrics.garman_klass_volatility:.4f}")
        logger.info(f"  Is Squeeze: {volatility_metrics.is_squeeze}")
        logger.info(f"  Squeeze Intensity: {volatility_metrics.squeeze_intensity:.2f}")
        logger.info(f"  Squeeze Duration: {volatility_metrics.squeeze_duration}")
        logger.info(f"  Volatility Regime: {volatility_metrics.volatility_regime.value}")
        logger.info(f"  Regime Confidence: {volatility_metrics.regime_confidence:.2f}")
        
    except Exception as e:
        logger.error(f"Error in volatility analysis demo: {e}")

def demonstrate_strategy_integration():
    """Demonstrate integration with strategy management system"""
    logger.info("\n=== Strategy Integration Demo ===")
    
    try:
        # Create strategy manager
        manager = StrategyManager()
        
        # Create strategy factory
        factory = StrategyFactory()
        
        # Register volatility breakout strategies
        logger.info("Registering volatility breakout strategies...")
        
        # Register Bollinger Band strategy
        bollinger_config = StrategyConfig(
            strategy_id="bollinger_breakout_integrated",
            symbols=["AAPL"],
            parameters={
                'period': 20,
                'std_dev': 2.0,
                'volume_confirmation': True
            }
        )
        
        bollinger_strategy = BollingerBandBreakoutStrategy(bollinger_config)
        manager.register_strategy(bollinger_strategy)
        
        # Register Volatility Expansion strategy
        expansion_config = StrategyConfig(
            strategy_id="volatility_expansion_integrated",
            symbols=["AAPL"],
            parameters={
                'min_squeeze_duration': 5,
                'min_expansion_rate': 0.1,
                'volume_confirmation': True
            }
        )
        
        expansion_strategy = VolatilityExpansionStrategy(expansion_config)
        manager.register_strategy(expansion_strategy)
        
        logger.info(f"Registered {len(manager.strategies)} strategies")
        
        # Generate sample data
        df = generate_sample_data(80)
        market_data = df.to_dict('records')
        
        # Execute strategies
        logger.info("Executing strategies...")
        results = manager.execute_strategies(market_data)
        
        # Display results
        for strategy_id, result in results.items():
            logger.info(f"\nStrategy: {strategy_id}")
            logger.info(f"  Status: {result.get('status', 'unknown')}")
            logger.info(f"  Signals: {len(result.get('signals', []))}")
            
            if result.get('signals'):
                for i, signal in enumerate(result['signals'][:2]):  # Show first 2 signals
                    logger.info(f"  Signal {i+1}: {signal.signal_type.value} at {signal.entry_price:.2f}")
        
        # Get performance summary
        performance = manager.get_performance_summary()
        logger.info(f"\nPerformance Summary:")
        logger.info(f"  Total Strategies: {performance.get('total_strategies', 0)}")
        logger.info(f"  Active Strategies: {performance.get('active_strategies', 0)}")
        logger.info(f"  Total Signals: {performance.get('total_signals', 0)}")
        
    except Exception as e:
        logger.error(f"Error in strategy integration demo: {e}")

def main():
    """Main demonstration function"""
    logger.info("Starting Volatility Breakout Strategy Demonstration")
    logger.info("=" * 60)
    
    try:
        # Run demonstrations
        demonstrate_range_breakout_strategies()
        demonstrate_volatility_expansion_strategy()
        demonstrate_volatility_analysis()
        demonstrate_strategy_integration()
        
        logger.info("\n" + "=" * 60)
        logger.info("Volatility Breakout Strategy Demonstration Complete")
        
    except Exception as e:
        logger.error(f"Error in main demonstration: {e}")

if __name__ == "__main__":
    main()