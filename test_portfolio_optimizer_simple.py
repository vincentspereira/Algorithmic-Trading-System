"""
Simple test for Portfolio Optimization Engine
"""

import asyncio
import numpy as np
import sys
import os
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.abspath('.'))

# Test the portfolio optimizer
async def test_portfolio_optimizer():
    """Test basic portfolio optimization functionality"""
    print("Testing Portfolio Optimization Engine...")
    
    try:
        # Import the portfolio optimizer components
        from nautilus_trader_engine.risk.portfolio_optimizer import (
            PortfolioOptimizationEngine, Asset, OptimizationConstraints,
            OptimizationMethod, ObjectiveFunction, RiskModel
        )
        print("✓ Successfully imported portfolio optimizer classes")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return
    
    # Initialize portfolio optimizer
    try:
        engine = PortfolioOptimizationEngine(enable_real_time=False)
        await engine.start()
        print("✓ Portfolio optimizer started successfully")
    except Exception as e:
        print(f"❌ Failed to start portfolio optimizer: {e}")
        return
    
    try:
        # Create sample assets
        np.random.seed(42)  # For reproducible results
        
        assets = [
            Asset(
                symbol="AAPL",
                name="Apple Inc.",
                expected_return=0.12,  # 12% annual return
                volatility=0.20,       # 20% annual volatility
                current_price=150.0,
                market_cap=2500000000000,  # $2.5T
                returns=np.random.normal(0.12/252, 0.20/np.sqrt(252), 252),
                sector="Technology",
                min_weight=0.0,
                max_weight=0.4
            ),
            Asset(
                symbol="MSFT",
                name="Microsoft Corp.",
                expected_return=0.11,
                volatility=0.18,
                current_price=300.0,
                market_cap=2200000000000,  # $2.2T
                returns=np.random.normal(0.11/252, 0.18/np.sqrt(252), 252),
                sector="Technology",
                min_weight=0.0,
                max_weight=0.4
            ),
            Asset(
                symbol="JPM",
                name="JPMorgan Chase",
                expected_return=0.10,
                volatility=0.25,
                current_price=140.0,
                market_cap=400000000000,  # $400B
                returns=np.random.normal(0.10/252, 0.25/np.sqrt(252), 252),
                sector="Financial",
                min_weight=0.0,
                max_weight=0.3
            ),
            Asset(
                symbol="JNJ",
                name="Johnson & Johnson",
                expected_return=0.08,
                volatility=0.15,
                current_price=160.0,
                market_cap=450000000000,  # $450B
                returns=np.random.normal(0.08/252, 0.15/np.sqrt(252), 252),
                sector="Healthcare",
                min_weight=0.0,
                max_weight=0.3
            )
        ]
        
        print(f"Created portfolio with {len(assets)} assets:")
        for asset in assets:
            print(f"  {asset.symbol}: Expected Return {asset.expected_return:.1%}, "
                  f"Volatility {asset.volatility:.1%}")
        
        # Create optimization constraints
        constraints = OptimizationConstraints(
            long_only=True,
            max_leverage=1.0,
            sector_max_weights={"Technology": 0.6, "Financial": 0.3, "Healthcare": 0.3}
        )
        
        # Test Mean-Variance Optimization (Maximum Sharpe Ratio)
        print("\n=== Mean-Variance Optimization (Maximum Sharpe) ===")
        mv_result = await engine.optimize_portfolio(
            portfolio_id="test_mv_portfolio",
            assets=assets,
            method=OptimizationMethod.MEAN_VARIANCE,
            objective=ObjectiveFunction.MAXIMIZE_SHARPE,
            constraints=constraints,
            risk_free_rate=0.02
        )
        
        print(f"✓ Optimization completed successfully")
        print(f"  Expected Return: {mv_result.expected_return:.2%}")
        print(f"  Expected Risk: {mv_result.expected_risk:.2%}")
        print(f"  Sharpe Ratio: {mv_result.sharpe_ratio:.3f}")
        print(f"  Convergence: {mv_result.convergence}")
        
        print(f"  Optimal Weights:")
        for symbol, weight in mv_result.weights.items():
            print(f"    {symbol}: {weight:.1%}")
        
        # Test Minimum Variance Optimization
        print("\n=== Minimum Variance Optimization ===")
        min_var_result = await engine.optimize_portfolio(
            portfolio_id="test_minvar_portfolio",
            assets=assets,
            method=OptimizationMethod.MINIMUM_VARIANCE,
            constraints=constraints
        )
        
        print(f"✓ Minimum variance optimization completed")
        print(f"  Expected Return: {min_var_result.expected_return:.2%}")
        print(f"  Expected Risk: {min_var_result.expected_risk:.2%}")
        print(f"  Sharpe Ratio: {min_var_result.sharpe_ratio:.3f}")
        
        print(f"  Optimal Weights:")
        for symbol, weight in min_var_result.weights.items():
            print(f"    {symbol}: {weight:.1%}")
        
        # Test Risk Parity Optimization
        print("\n=== Risk Parity Optimization ===")
        rp_result = await engine.optimize_portfolio(
            portfolio_id="test_rp_portfolio",
            assets=assets,
            method=OptimizationMethod.RISK_PARITY,
            constraints=constraints
        )
        
        print(f"✓ Risk parity optimization completed")
        print(f"  Expected Return: {rp_result.expected_return:.2%}")
        print(f"  Expected Risk: {rp_result.expected_risk:.2%}")
        print(f"  Sharpe Ratio: {rp_result.sharpe_ratio:.3f}")
        
        print(f"  Optimal Weights:")
        for symbol, weight in rp_result.weights.items():
            print(f"    {symbol}: {weight:.1%}")
        
        print(f"  Risk Contributions:")
        for symbol, contrib in rp_result.risk_contributions.items():
            print(f"    {symbol}: {contrib:.1%}")
        
        # Test Equal Weight Portfolio
        print("\n=== Equal Weight Portfolio ===")
        eq_result = await engine.optimize_portfolio(
            portfolio_id="test_eq_portfolio",
            assets=assets,
            method=OptimizationMethod.EQUAL_WEIGHT,
            constraints=constraints
        )
        
        print(f"✓ Equal weight optimization completed")
        print(f"  Expected Return: {eq_result.expected_return:.2%}")
        print(f"  Expected Risk: {eq_result.expected_risk:.2%}")
        print(f"  Sharpe Ratio: {eq_result.sharpe_ratio:.3f}")
        
        print(f"  Optimal Weights:")
        for symbol, weight in eq_result.weights.items():
            print(f"    {symbol}: {weight:.1%}")
        
        # Compare all methods
        print("\n=== Method Comparison ===")
        methods = [
            ("Mean-Variance (Max Sharpe)", mv_result),
            ("Minimum Variance", min_var_result),
            ("Risk Parity", rp_result),
            ("Equal Weight", eq_result)
        ]
        
        print(f"{'Method':<25} {'Return':<8} {'Risk':<8} {'Sharpe':<8}")
        print("-" * 50)
        for name, result in methods:
            print(f"{name:<25} {result.expected_return:>7.1%} {result.expected_risk:>7.1%} {result.sharpe_ratio:>7.3f}")
        
        # Get engine metrics
        metrics = engine.get_metrics()
        print(f"\nEngine metrics:")
        print(f"  Optimizations completed: {metrics['optimizations_completed']}")
        print(f"  Optimizations failed: {metrics['optimizations_failed']}")
        print(f"  Active portfolios: {metrics['active_portfolios']}")
        print(f"  Average optimization time: {metrics['avg_optimization_time_ms']:.2f}ms")
        
        print("\n✅ Portfolio Optimization Engine test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        try:
            await engine.stop()
            print("✓ Portfolio optimizer stopped")
        except Exception as e:
            print(f"❌ Failed to stop portfolio optimizer: {e}")


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_portfolio_optimizer())