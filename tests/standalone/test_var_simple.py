"""
Simple test for VaR Engine
"""

import asyncio
import numpy as np
import sys
import os
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.abspath('.'))

# Test the VaR engine
async def test_var_engine():
    """Test basic VaR engine functionality"""
    print("Testing VaR Engine...")
    
    try:
        # Import the VaR engine components
        from nautilus_trader_engine.risk.var_engine import (
            VaREngine, VaRMethod, TimeHorizon, PortfolioPosition
        )
        print("✓ Successfully imported VaR engine classes")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return
    
    # Initialize VaR engine
    try:
        engine = VaREngine(enable_real_time=False, enable_backtesting=True)
        await engine.start()
        print("✓ VaR engine started successfully")
    except Exception as e:
        print(f"❌ Failed to start VaR engine: {e}")
        return
    
    try:
        # Create sample portfolio positions
        np.random.seed(42)  # For reproducible results
        
        positions = [
            PortfolioPosition(
                symbol="AAPL",
                quantity=100,
                current_price=150.0,
                market_value=15000.0,
                weight=0.6,
                volatility=0.02,
                returns=np.random.normal(0.001, 0.02, 252)  # 1 year of daily returns
            ),
            PortfolioPosition(
                symbol="MSFT",
                quantity=50,
                current_price=200.0,
                market_value=10000.0,
                weight=0.4,
                volatility=0.018,
                returns=np.random.normal(0.0008, 0.018, 252)
            )
        ]
        
        print(f"Created portfolio with {len(positions)} positions")
        print(f"Total portfolio value: ${sum(pos.market_value for pos in positions):,.2f}")
        
        # Calculate VaR using Historical method
        print("\nCalculating Historical VaR...")
        historical_var = await engine.calculate_var(
            portfolio_id="test_portfolio",
            positions=positions,
            method=VaRMethod.HISTORICAL,
            confidence_level=0.95,
            time_horizon=TimeHorizon.DAILY
        )
        
        print(f"✓ Historical VaR (95%, 1-day): ${historical_var.var_value:,.2f}")
        print(f"  Expected Shortfall: ${historical_var.expected_shortfall:,.2f}")
        print(f"  VaR as % of portfolio: {historical_var.var_percentage:.2%}")
        
        # Calculate VaR using Parametric method
        print("\nCalculating Parametric VaR...")
        parametric_var = await engine.calculate_var(
            portfolio_id="test_portfolio",
            positions=positions,
            method=VaRMethod.PARAMETRIC,
            confidence_level=0.95,
            time_horizon=TimeHorizon.DAILY
        )
        
        print(f"✓ Parametric VaR (95%, 1-day): ${parametric_var.var_value:,.2f}")
        print(f"  Expected Shortfall: ${parametric_var.expected_shortfall:,.2f}")
        print(f"  VaR as % of portfolio: {parametric_var.var_percentage:.2%}")
        
        # Calculate VaR using Monte Carlo method
        print("\nCalculating Monte Carlo VaR...")
        mc_var = await engine.calculate_var(
            portfolio_id="test_portfolio",
            positions=positions,
            method=VaRMethod.MONTE_CARLO,
            confidence_level=0.95,
            time_horizon=TimeHorizon.DAILY
        )
        
        print(f"✓ Monte Carlo VaR (95%, 1-day): ${mc_var.var_value:,.2f}")
        print(f"  Expected Shortfall: ${mc_var.expected_shortfall:,.2f}")
        print(f"  VaR as % of portfolio: {mc_var.var_percentage:.2%}")
        
        # Calculate VaR for different confidence levels
        print("\nCalculating VaR for different confidence levels...")
        for confidence in [0.90, 0.95, 0.99]:
            var_result = await engine.calculate_var(
                portfolio_id="test_portfolio",
                positions=positions,
                method=VaRMethod.PARAMETRIC,
                confidence_level=confidence,
                time_horizon=TimeHorizon.DAILY
            )
            print(f"  {confidence:.0%} VaR: ${var_result.var_value:,.2f}")
        
        # Calculate VaR for different time horizons
        print("\nCalculating VaR for different time horizons...")
        for horizon in [TimeHorizon.DAILY, TimeHorizon.WEEKLY, TimeHorizon.MONTHLY]:
            var_result = await engine.calculate_var(
                portfolio_id="test_portfolio",
                positions=positions,
                method=VaRMethod.PARAMETRIC,
                confidence_level=0.95,
                time_horizon=horizon
            )
            print(f"  {horizon.value.title()} VaR: ${var_result.var_value:,.2f}")
        
        # Get VaR history
        history = engine.get_var_history("test_portfolio")
        print(f"\nVaR calculation history: {len(history)} calculations")
        
        # Get engine metrics
        metrics = engine.get_metrics()
        print(f"\nEngine metrics:")
        print(f"  Calculations completed: {metrics['calculations_completed']}")
        print(f"  Calculations failed: {metrics['calculations_failed']}")
        print(f"  Active portfolios: {metrics['active_portfolios']}")
        print(f"  Average calculation time: {metrics['avg_calculation_time_ms']:.2f}ms")
        
        print("\n✅ VaR Engine test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        try:
            await engine.stop()
            print("✓ VaR engine stopped")
        except Exception as e:
            print(f"❌ Failed to stop VaR engine: {e}")


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_var_engine())