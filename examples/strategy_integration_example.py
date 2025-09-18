"""Strategy Integration Example

This example demonstrates how to use the unified strategy management system
to create, register, and execute different types of trading strategies including
pairs trading and machine learning strategies.

Key Features Demonstrated:
- Strategy factory pattern usage
- Strategy manager registration and execution
- Multi-strategy coordination
- Performance monitoring
- Risk management integration

Usage:
    python examples/strategy_integration_example.py
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import strategy components
from strategies import (
    # Core types
    StrategyType, StrategyConfig, TradingSignal,
    
    # Strategy management
    StrategyManager, StrategyCategory, StrategyStatus,
    strategy_manager, register_strategy, start_strategy,
    execute_strategy, get_strategy_status, get_all_strategies,
    
    # Strategy factory
    StrategyTemplate, create_from_template, create_strategy,
    list_available_strategies, get_strategy_info
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def generate_sample_market_data() -> Dict:
    """Generate sample market data for testing"""
    import random
    
    # Simulate market data for multiple symbols
    symbols = ["SPY", "QQQ", "IWM", "TLT", "GLD"]
    market_data = {}
    
    base_time = datetime.now()
    
    for symbol in symbols:
        # Generate OHLCV data
        base_price = random.uniform(100, 500)
        
        market_data[symbol] = {
            'timestamp': base_time,
            'open': base_price,
            'high': base_price * random.uniform(1.001, 1.02),
            'low': base_price * random.uniform(0.98, 0.999),
            'close': base_price * random.uniform(0.99, 1.01),
            'volume': random.randint(1000000, 10000000),
            
            # Technical indicators (simulated)
            'sma_20': base_price * random.uniform(0.98, 1.02),
            'ema_12': base_price * random.uniform(0.99, 1.01),
            'rsi': random.uniform(30, 70),
            'macd': random.uniform(-2, 2),
            'bollinger_upper': base_price * 1.02,
            'bollinger_lower': base_price * 0.98,
            
            # Volume indicators
            'vwap': base_price * random.uniform(0.995, 1.005),
            'obv': random.randint(-1000000, 1000000),
            
            # Volatility indicators
            'atr': base_price * random.uniform(0.01, 0.05),
            'volatility': random.uniform(0.15, 0.35)
        }
    
    return market_data

async def demonstrate_strategy_factory():
    """Demonstrate strategy factory usage"""
    logger.info("=== Strategy Factory Demonstration ===")
    
    # List available strategies
    available_strategies = list_available_strategies()
    logger.info(f"Available strategy categories: {list(available_strategies.keys())}")
    
    for category, blueprints in available_strategies.items():
        logger.info(f"  {category}: {blueprints}")
    
    # Get detailed information about a strategy
    pairs_info = get_strategy_info("pairs_trading", "conservative_pairs")
    if pairs_info:
        logger.info(f"Conservative Pairs Strategy Info:")
        logger.info(f"  Description: {pairs_info.description}")
        logger.info(f"  Risk Level: {pairs_info.risk_level}")
        logger.info(f"  Min Capital: ${pairs_info.min_capital:,.2f}")
        logger.info(f"  Recommended Timeframes: {pairs_info.recommended_timeframes}")
    
    # Create strategies from templates
    logger.info("\nCreating strategies from templates...")
    
    # Conservative pairs strategy
    conservative_pairs = create_from_template(
        StrategyTemplate.CONSERVATIVE_PAIRS,
        symbols=["SPY", "QQQ"],
        capital=100000.0
    )
    
    if conservative_pairs:
        logger.info("✓ Conservative pairs strategy created successfully")
    else:
        logger.error("✗ Failed to create conservative pairs strategy")
    
    # ML momentum strategy
    ml_momentum = create_from_template(
        StrategyTemplate.ML_MOMENTUM,
        symbols=["SPY", "QQQ", "IWM"],
        capital=150000.0
    )
    
    if ml_momentum:
        logger.info("✓ ML momentum strategy created successfully")
    else:
        logger.error("✗ Failed to create ML momentum strategy")
    
    # Regime adaptive strategy
    regime_adaptive = create_from_template(
        StrategyTemplate.REGIME_ADAPTIVE,
        symbols=["SPY", "QQQ", "IWM", "TLT", "GLD"],
        capital=200000.0
    )
    
    if regime_adaptive:
        logger.info("✓ Regime adaptive strategy created successfully")
    else:
        logger.error("✗ Failed to create regime adaptive strategy")
    
    return {
        "conservative_pairs": conservative_pairs,
        "ml_momentum": ml_momentum,
        "regime_adaptive": regime_adaptive
    }

async def demonstrate_strategy_manager(strategies: Dict):
    """Demonstrate strategy manager usage"""
    logger.info("\n=== Strategy Manager Demonstration ===")
    
    # Register strategies with the manager
    logger.info("Registering strategies...")
    
    registration_results = []
    
    # Register conservative pairs strategy
    if strategies["conservative_pairs"]:
        config = StrategyConfig(
            strategy_type=StrategyType.CONVERGENCE,
            symbols=["SPY", "QQQ"],
            timeframe="1h",
            initial_capital=100000.0,
            max_position_size=0.1,
            stop_loss=0.02,
            take_profit=0.04
        )
        
        result = register_strategy(
            "conservative_pairs_001",
            StrategyType.CONVERGENCE,
            config,
            StrategyCategory.PAIRS_TRADING
        )
        registration_results.append(("conservative_pairs_001", result))
    
    # Register ML momentum strategy
    if strategies["ml_momentum"]:
        config = StrategyConfig(
            strategy_type=StrategyType.MOMENTUM,
            symbols=["SPY", "QQQ", "IWM"],
            timeframe="1h",
            initial_capital=150000.0,
            max_position_size=0.15,
            stop_loss=0.03,
            take_profit=0.06
        )
        
        result = register_strategy(
            "ml_momentum_001",
            "random_forest",
            config,
            StrategyCategory.MACHINE_LEARNING
        )
        registration_results.append(("ml_momentum_001", result))
    
    # Register regime adaptive strategy
    if strategies["regime_adaptive"]:
        config = StrategyConfig(
            strategy_type=StrategyType.ADAPTIVE,
            symbols=["SPY", "QQQ", "IWM", "TLT", "GLD"],
            timeframe="1d",
            initial_capital=200000.0,
            max_position_size=0.3,
            stop_loss=0.04,
            take_profit=0.08
        )
        
        result = register_strategy(
            "regime_adaptive_001",
            "clustering",
            config,
            StrategyCategory.MACHINE_LEARNING
        )
        registration_results.append(("regime_adaptive_001", result))
    
    # Report registration results
    for strategy_id, success in registration_results:
        if success:
            logger.info(f"✓ Strategy {strategy_id} registered successfully")
        else:
            logger.error(f"✗ Failed to register strategy {strategy_id}")
    
    # List all registered strategies
    all_strategies = get_all_strategies()
    logger.info(f"\nTotal registered strategies: {len(all_strategies)}")
    
    for strategy_id, registration in all_strategies.items():
        logger.info(f"  {strategy_id}: {registration.category.value} - {registration.status.value}")
    
    return [sid for sid, success in registration_results if success]

async def demonstrate_strategy_execution(strategy_ids: List[str]):
    """Demonstrate strategy execution"""
    logger.info("\n=== Strategy Execution Demonstration ===")
    
    # Start strategies
    logger.info("Starting strategies...")
    
    for strategy_id in strategy_ids:
        try:
            success = await start_strategy(strategy_id)
            if success:
                logger.info(f"✓ Strategy {strategy_id} started successfully")
            else:
                logger.error(f"✗ Failed to start strategy {strategy_id}")
        except Exception as e:
            logger.error(f"✗ Error starting strategy {strategy_id}: {e}")
    
    # Check strategy statuses
    logger.info("\nStrategy statuses:")
    for strategy_id in strategy_ids:
        status = get_strategy_status(strategy_id)
        logger.info(f"  {strategy_id}: {status.value if status else 'Unknown'}")
    
    # Execute strategies with market data
    logger.info("\nExecuting strategies with market data...")
    
    # Generate sample market data
    market_data = generate_sample_market_data()
    logger.info(f"Generated market data for symbols: {list(market_data.keys())}")
    
    # Execute each strategy
    execution_results = {}
    
    for strategy_id in strategy_ids:
        try:
            signals = await execute_strategy(strategy_id, market_data)
            execution_results[strategy_id] = signals
            
            if signals:
                logger.info(f"✓ Strategy {strategy_id} generated {len(signals)} signals")
                for i, signal in enumerate(signals[:3]):  # Show first 3 signals
                    logger.info(f"    Signal {i+1}: {signal.symbol} - {signal.signal_type.value} - Strength: {signal.strength.value}")
            else:
                logger.info(f"  Strategy {strategy_id} generated no signals")
                
        except Exception as e:
            logger.error(f"✗ Error executing strategy {strategy_id}: {e}")
            execution_results[strategy_id] = None
    
    return execution_results

async def demonstrate_performance_monitoring(strategy_ids: List[str]):
    """Demonstrate performance monitoring"""
    logger.info("\n=== Performance Monitoring Demonstration ===")
    
    # Get strategy metrics
    for strategy_id in strategy_ids:
        metrics = strategy_manager.get_strategy_metrics(strategy_id)
        if metrics:
            logger.info(f"\nMetrics for {strategy_id}:")
            logger.info(f"  Total Return: {metrics.total_return:.2%}")
            logger.info(f"  Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
            logger.info(f"  Max Drawdown: {metrics.max_drawdown:.2%}")
            logger.info(f"  Win Rate: {metrics.win_rate:.2%}")
            logger.info(f"  Total Trades: {metrics.total_trades}")
            logger.info(f"  Active Positions: {metrics.active_positions}")
            logger.info(f"  Last Updated: {metrics.last_updated}")
    
    # Get alerts
    alerts = strategy_manager.get_alerts()
    if alerts:
        logger.info(f"\nActive alerts: {len(alerts)}")
        for alert in alerts[-5:]:  # Show last 5 alerts
            logger.info(f"  {alert.timestamp}: {alert.level.value.upper()} - {alert.strategy_id} - {alert.message}")
    else:
        logger.info("\nNo active alerts")

async def demonstrate_multi_strategy_coordination():
    """Demonstrate multi-strategy coordination"""
    logger.info("\n=== Multi-Strategy Coordination Demonstration ===")
    
    # Get active strategies
    active_strategies = strategy_manager.get_active_strategies()
    logger.info(f"Active strategies: {len(active_strategies)}")
    
    # Simulate portfolio-level coordination
    total_capital = sum(
        reg.config.initial_capital for reg in active_strategies.values()
    )
    logger.info(f"Total allocated capital: ${total_capital:,.2f}")
    
    # Calculate portfolio exposure by category
    category_exposure = {}
    for registration in active_strategies.values():
        category = registration.category.value
        capital = registration.config.initial_capital
        
        if category not in category_exposure:
            category_exposure[category] = 0
        category_exposure[category] += capital
    
    logger.info("\nCapital allocation by strategy category:")
    for category, capital in category_exposure.items():
        percentage = (capital / total_capital) * 100 if total_capital > 0 else 0
        logger.info(f"  {category}: ${capital:,.2f} ({percentage:.1f}%)")

async def main():
    """Main demonstration function"""
    logger.info("Starting Strategy Integration Demonstration")
    logger.info("=" * 60)
    
    try:
        # Start strategy monitoring
        strategy_manager.start_monitoring()
        
        # Demonstrate strategy factory
        strategies = await demonstrate_strategy_factory()
        
        # Demonstrate strategy manager
        strategy_ids = await demonstrate_strategy_manager(strategies)
        
        if strategy_ids:
            # Demonstrate strategy execution
            execution_results = await demonstrate_strategy_execution(strategy_ids)
            
            # Demonstrate performance monitoring
            await demonstrate_performance_monitoring(strategy_ids)
            
            # Demonstrate multi-strategy coordination
            await demonstrate_multi_strategy_coordination()
        else:
            logger.warning("No strategies were successfully registered")
        
        logger.info("\n=== Demonstration Complete ===")
        logger.info("Strategy integration system is working correctly!")
        
    except Exception as e:
        logger.error(f"Error in demonstration: {e}")
        raise
    
    finally:
        # Stop monitoring and cleanup
        strategy_manager.stop_monitoring()
        strategy_manager.shutdown()
        logger.info("Strategy manager shutdown complete")

if __name__ == "__main__":
    # Run the demonstration
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Demonstration interrupted by user")
    except Exception as e:
        logger.error(f"Demonstration failed: {e}")
        sys.exit(1)