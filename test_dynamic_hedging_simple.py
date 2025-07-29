#!/usr/bin/env python3
"""
Simple test for Dynamic Hedging System
"""

import asyncio
import numpy as np
import sys
import os
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.abspath('.'))


async def test_dynamic_hedging_system():
    """Test basic dynamic hedging functionality"""
    print("Testing Dynamic Hedging System...")
    
    try:
        # Import the dynamic hedging components
        from nautilus_trader_engine.risk.dynamic_hedging import (
            DynamicHedgingSystem, HedgeType, HedgeInstrument,
            create_correlation_hedge, create_delta_neutral_hedge, create_currency_hedge
        )
        print("✓ Successfully imported dynamic hedging classes")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return
    
    # Initialize dynamic hedging system
    try:
        hedging_system = DynamicHedgingSystem(enable_real_time=False)
        await hedging_system.start()
        print("✓ Dynamic hedging system started successfully")
    except Exception as e:
        print(f"❌ Failed to start dynamic hedging system: {e}")
        return
    
    try:
        # Create sample portfolio positions
        class MockPosition:
            def __init__(self, symbol, market_value, beta=1.0, currency="USD", sector="Technology", delta=None):
                self.symbol = symbol
                self.market_value = market_value
                self.quantity = 100
                self.beta = beta
                self.currency = currency
                self.sector = sector
                self.delta = delta if delta is not None else (1.0 if "option" not in symbol.lower() else 0.5)
        
        # Create a sample portfolio
        portfolio = [
            MockPosition("AAPL", 100000, beta=1.2, sector="Technology"),
            MockPosition("MSFT", 80000, beta=1.1, sector="Technology"),
            MockPosition("JPM", 60000, beta=1.5, sector="Financial"),
            MockPosition("GOOGL", 70000, beta=1.3, sector="Technology"),
            MockPosition("TSLA", 50000, beta=2.0, sector="Automotive")
        ]
        
        portfolio_value = sum(pos.market_value for pos in portfolio)
        print(f"Created portfolio with {len(portfolio)} positions, total value: ${portfolio_value:,.2f}")
        
        # Test 1: Correlation-based hedging
        print("\n=== Correlation-Based Hedging ===")
        
        correlation_hedge = await create_correlation_hedge(
            strategy_id="correlation_hedge_test",
            target_portfolio=portfolio,
            hedge_symbols=["SPY", "QQQ"]
        )
        
        print(f"✓ Created correlation hedge strategy:")
        print(f"  Strategy ID: {correlation_hedge.strategy_id}")
        print(f"  Hedge Type: {correlation_hedge.hedge_type.value}")
        print(f"  Status: {correlation_hedge.status.value}")
        print(f"  Effectiveness Score: {correlation_hedge.effectiveness_score:.3f}")
        print(f"  Hedge Instruments:")
        for instrument in correlation_hedge.hedge_instruments:
            print(f"    {instrument.symbol}: ratio={instrument.hedge_ratio:.3f}, target=${instrument.target_position:,.2f}")
        
        # Test 2: Delta-neutral hedging
        print("\n=== Delta-Neutral Hedging ===")
        
        # Create options portfolio
        options_portfolio = [
            MockPosition("AAPL_CALL_150", 25000, delta=0.6),
            MockPosition("AAPL_PUT_140", -15000, delta=-0.4),
            MockPosition("MSFT_CALL_300", 30000, delta=0.7)
        ]
        
        delta_neutral_hedge = await create_delta_neutral_hedge(
            strategy_id="delta_neutral_test",
            options_portfolio=options_portfolio,
            underlying_symbol="AAPL"
        )
        
        print(f"✓ Created delta-neutral hedge strategy:")
        print(f"  Strategy ID: {delta_neutral_hedge.strategy_id}")
        print(f"  Hedge Type: {delta_neutral_hedge.hedge_type.value}")
        print(f"  Status: {delta_neutral_hedge.status.value}")
        print(f"  Effectiveness Score: {delta_neutral_hedge.effectiveness_score:.3f}")
        print(f"  Hedge Instruments:")
        for instrument in delta_neutral_hedge.hedge_instruments:
            print(f"    {instrument.symbol}: ratio={instrument.hedge_ratio:.3f}, target=${instrument.target_position:,.2f}")
        
        # Test 3: Currency hedging
        print("\n=== Currency Hedging ===")
        
        # Create portfolio with foreign currency exposure
        fx_portfolio = [
            MockPosition("ASML", 50000, currency="EUR"),
            MockPosition("NESN", 40000, currency="CHF"),
            MockPosition("TSM", 60000, currency="TWD"),
            MockPosition("AAPL", 100000, currency="USD")
        ]
        
        currency_hedge = await create_currency_hedge(
            strategy_id="currency_hedge_test",
            portfolio=fx_portfolio,
            currency_pairs=["EURUSD", "CHFUSD", "TWDUSD"]
        )
        
        print(f"✓ Created currency hedge strategy:")
        print(f"  Strategy ID: {currency_hedge.strategy_id}")
        print(f"  Hedge Type: {currency_hedge.hedge_type.value}")
        print(f"  Status: {currency_hedge.status.value}")
        print(f"  Effectiveness Score: {currency_hedge.effectiveness_score:.3f}")
        print(f"  Hedge Instruments:")
        for instrument in currency_hedge.hedge_instruments:
            print(f"    {instrument.symbol}: ratio={instrument.hedge_ratio:.3f}, target=${instrument.target_position:,.2f}")
        
        # Test 4: Hedge recommendations
        print("\n=== Hedge Recommendations ===")
        
        recommendations = await hedging_system.generate_hedge_recommendations(
            portfolio=portfolio,
            risk_tolerance="medium"
        )
        
        print(f"✓ Generated {len(recommendations)} hedge recommendations:")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec.action.upper()} - {rec.strategy_id}")
            print(f"     Expected Effectiveness: {rec.expected_effectiveness:.3f}")
            print(f"     Cost Estimate: {rec.cost_estimate:.4f}")
            print(f"     Risk Reduction: {rec.risk_reduction:.3f}")
            print(f"     Rationale: {rec.rationale}")
            print(f"     Confidence: {rec.confidence:.3f}")
            print(f"     Priority: {rec.execution_priority}")
        
        # Test 5: Hedge rebalancing
        print("\n=== Hedge Rebalancing ===")
        
        # Simulate portfolio changes
        updated_portfolio = portfolio.copy()
        updated_portfolio[0].market_value = 120000  # AAPL increased
        updated_portfolio[1].market_value = 70000   # MSFT decreased
        
        rebalance_needed = await hedging_system.rebalance_hedge_strategy(
            strategy_id="correlation_hedge_test",
            current_portfolio=updated_portfolio
        )
        
        print(f"✓ Rebalancing check completed:")
        print(f"  Rebalance needed: {rebalance_needed}")
        
        if rebalance_needed:
            updated_strategy = hedging_system.active_strategies["correlation_hedge_test"]
            print(f"  Updated hedge ratios:")
            for instrument in updated_strategy.hedge_instruments:
                print(f"    {instrument.symbol}: {instrument.hedge_ratio:.3f}")
        
        # Test 6: Performance measurement
        print("\n=== Performance Measurement ===")
        
        performance_metrics = await hedging_system.measure_hedge_effectiveness(
            strategy_id="correlation_hedge_test",
            measurement_period_days=30
        )
        
        print(f"✓ Performance metrics calculated:")
        print(f"  Hedge Effectiveness: {performance_metrics.hedge_effectiveness:.3f}")
        print(f"  Tracking Error: {performance_metrics.tracking_error:.4f}")
        print(f"  Hedge P&L: ${performance_metrics.hedge_pnl:,.2f}")
        print(f"  Hedge Cost: ${performance_metrics.hedge_cost:,.2f}")
        print(f"  Net Benefit: ${performance_metrics.net_hedge_benefit:,.2f}")
        print(f"  Risk Reduction: {performance_metrics.risk_reduction_achieved:.3f}")
        
        # Test 7: System metrics
        print("\n=== System Metrics ===")
        
        system_metrics = hedging_system.get_system_metrics()
        print(f"✓ System metrics:")
        print(f"  Active Strategies: {system_metrics['active_strategies']}")
        print(f"  Total Hedge P&L: ${system_metrics['total_hedge_pnl']:,.2f}")
        print(f"  Average Effectiveness: {system_metrics['avg_hedge_effectiveness']:.3f}")
        print(f"  Rebalances Completed: {system_metrics['rebalances_completed']}")
        print(f"  Rebalances Failed: {system_metrics['rebalances_failed']}")
        
        # Test 8: Active strategies overview
        print("\n=== Active Strategies Overview ===")
        
        active_strategies = hedging_system.get_active_strategies()
        print(f"✓ Active strategies ({len(active_strategies)}):")
        
        for strategy_id, strategy in active_strategies.items():
            print(f"  {strategy_id}:")
            print(f"    Type: {strategy.hedge_type.value}")
            print(f"    Status: {strategy.status.value}")
            print(f"    Effectiveness: {strategy.effectiveness_score:.3f}")
            print(f"    Last Rebalance: {strategy.last_rebalance}")
            print(f"    Instruments: {len(strategy.hedge_instruments)}")
        
        print("\n✅ Dynamic Hedging System test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        try:
            await hedging_system.stop()
            print("✓ Dynamic hedging system stopped")
        except Exception as e:
            print(f"❌ Failed to stop dynamic hedging system: {e}")


async def test_hedge_calculators():
    """Test individual hedge calculators"""
    print("\n=== Testing Hedge Calculators ===")
    
    try:
        from nautilus_trader_engine.risk.dynamic_hedging import (
            CorrelationBasedHedgeCalculator, DeltaNeutralHedgeCalculator, 
            CurrencyHedgeCalculator, HedgeInstrument
        )
        
        # Test correlation-based calculator
        print("\n--- Correlation-Based Calculator ---")
        correlation_calc = CorrelationBasedHedgeCalculator(lookback_days=252)
        
        # Mock portfolio
        class MockPosition:
            def __init__(self, symbol, market_value):
                self.symbol = symbol
                self.market_value = market_value
        
        portfolio = [MockPosition("AAPL", 100000), MockPosition("MSFT", 80000)]
        hedge_instruments = [
            HedgeInstrument("SPY", "etf", 0.0, 0.0, 0.0),
            HedgeInstrument("QQQ", "etf", 0.0, 0.0, 0.0)
        ]
        
        hedge_ratios = await correlation_calc.calculate_hedge_ratio(
            portfolio, hedge_instruments
        )
        
        print(f"✓ Correlation hedge ratios calculated:")
        for symbol, ratio in hedge_ratios.items():
            print(f"  {symbol}: {ratio:.3f}")
        
        # Test effectiveness estimation
        effectiveness = correlation_calc.estimate_hedge_effectiveness(
            hedge_ratio=0.8, correlation=0.7
        )
        print(f"  Estimated effectiveness: {effectiveness:.3f}")
        
        # Test delta-neutral calculator
        print("\n--- Delta-Neutral Calculator ---")
        delta_calc = DeltaNeutralHedgeCalculator()
        
        # Mock options portfolio
        class MockOptionPosition:
            def __init__(self, symbol, quantity, delta):
                self.symbol = symbol
                self.quantity = quantity
                self.delta = delta
        
        options_portfolio = [
            MockOptionPosition("AAPL_CALL", 10, 0.6),
            MockOptionPosition("AAPL_PUT", -5, -0.4)
        ]
        
        hedge_instrument = HedgeInstrument("AAPL", "stock", 0.0, 0.0, 0.0, delta=1.0)
        
        delta_ratios = await delta_calc.calculate_hedge_ratio(
            options_portfolio, [hedge_instrument]
        )
        
        print(f"✓ Delta-neutral hedge ratios calculated:")
        for symbol, ratio in delta_ratios.items():
            print(f"  {symbol}: {ratio:.3f}")
        
        # Test currency calculator
        print("\n--- Currency Calculator ---")
        currency_calc = CurrencyHedgeCalculator()
        
        # Mock FX portfolio
        class MockFXPosition:
            def __init__(self, symbol, market_value, currency):
                self.symbol = symbol
                self.market_value = market_value
                self.currency = currency
        
        fx_portfolio = [
            MockFXPosition("ASML", 50000, "EUR"),
            MockFXPosition("NESN", 40000, "CHF")
        ]
        
        fx_hedge_instruments = [
            HedgeInstrument("EURUSD", "currency", 0.0, 0.0, 0.0, 
                          base_currency="EUR", quote_currency="USD"),
            HedgeInstrument("CHFUSD", "currency", 0.0, 0.0, 0.0,
                          base_currency="CHF", quote_currency="USD")
        ]
        
        fx_ratios = await currency_calc.calculate_hedge_ratio(
            fx_portfolio, fx_hedge_instruments, base_currency="USD"
        )
        
        print(f"✓ Currency hedge ratios calculated:")
        for symbol, ratio in fx_ratios.items():
            print(f"  {symbol}: {ratio:.3f}")
        
        print("✅ Hedge calculators test completed successfully!")
        
    except Exception as e:
        print(f"❌ Hedge calculators test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the tests
    asyncio.run(test_dynamic_hedging_system())
    asyncio.run(test_hedge_calculators())