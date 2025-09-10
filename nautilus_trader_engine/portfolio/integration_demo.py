"""
Integration Demo for Portfolio Optimization and Observability System
Demonstrates integration with Nautilus Trader portfolio system
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our portfolio modules
from portfolio_optimization import (
    PortfolioOptimizer, 
    NautilusPortfolioOptimizer,
    PortfolioOptimizationConfig,
    OptimizationMethod,
    RiskMeasure,
    OptimizationResult
)
from portfolio_observability import (
    PortfolioObservability, 
    PortfolioMetrics,
    RiskMetrics
)
from portfolio_integration import IntegratedPortfolioSystem


def create_sample_market_data():
    """Create sample market data for demonstration"""
    print("Creating sample market data...")
    
    # Create date range (6 months of data)
    dates = pd.date_range(start='2023-01-01', end='2023-06-30', freq='D')
    assets = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
    
    # Set random seed for reproducibility
    np.random.seed(42)
    
    # Create realistic returns with proper correlation and mean
    expected_returns = {
        'AAPL': 0.12,   # 12% expected annual return
        'GOOGL': 0.10,  # 10% expected annual return
        'MSFT': 0.08,   # 8% expected annual return
        'AMZN': 0.15,   # 15% expected annual return
        'TSLA': 0.20    # 20% expected annual return
    }
    
    volatilities = {
        'AAPL': 0.22,   # 22% annual volatility
        'GOOGL': 0.20,  # 20% annual volatility
        'MSFT': 0.18,   # 18% annual volatility
        'AMZN': 0.25,   # 25% annual volatility
        'TSLA': 0.35    # 35% annual volatility
    }
    
    # Create correlated returns
    base_factor = np.random.randn(len(dates)) * 0.01
    
    returns_data = {}
    for asset in assets:
        # Daily expected return
        daily_return = expected_returns[asset] / 252
        daily_vol = volatilities[asset] / np.sqrt(252)
        
        # Create returns with correlation to base factor and idiosyncratic component
        correlated_component = base_factor * 0.4  # 40% correlation to base
        idio_component = np.random.randn(len(dates)) * daily_vol * 0.916  # sqrt(1-0.4^2)
        returns_data[asset] = correlated_component + idio_component + daily_return
        
    df = pd.DataFrame(returns_data, index=dates)
    
    print(f"Created data for {len(assets)} assets over {len(dates)} days")
    return df


class MockPortfolio:
    """Mock Nautilus Trader portfolio for demonstration"""
    def __init__(self):
        self.id = "MOCK_PORTFOLIO_001"
        self.value = 1000000.0  # $1M portfolio
        
    def net_exposure(self, instrument_id):
        # Mock implementation
        return {"instrument_id": instrument_id, "exposure": 100000.0}
        
    def unrealized_pnl(self, instrument_id):
        # Mock implementation
        return {"instrument_id": instrument_id, "pnl": 5000.0}


class MockCache:
    """Mock Nautilus Trader cache for demonstration"""
    def __init__(self):
        self.data = {}
        
    def get(self, key):
        return self.data.get(key)
        
    def set(self, key, value):
        self.data[key] = value


def demonstrate_integration():
    """Demonstrate the complete integrated portfolio system"""
    print("\n" + "="*60)
    print("INTEGRATED PORTFOLIO SYSTEM DEMONSTRATION")
    print("="*60)
    
    # Create sample market data
    market_data = create_sample_market_data()
    
    # Create mock Nautilus Trader components
    mock_portfolio = MockPortfolio()
    mock_cache = MockCache()
    
    print(f"\nMock Portfolio Value: ${mock_portfolio.value:,.2f}")
    
    # 1. Demonstrate Portfolio Optimization
    print("\n1. PORTFOLIO OPTIMIZATION")
    print("-" * 30)
    
    # Configure optimizer
    config = PortfolioOptimizationConfig(
        method=OptimizationMethod.MINIMUM_VARIANCE,
        risk_free_rate=0.02,  # 2% risk-free rate
        allow_short=False
    )
    
    optimizer = PortfolioOptimizer(config)
    
    try:
        # Optimize portfolio
        result = optimizer.optimize_portfolio(market_data)
        
        print(f"Optimization Method: {config.method.value}")
        print(f"Expected Return: {result.expected_return:.2%}")
        print(f"Risk (Volatility): {result.risk:.2%}")
        print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
        
        print("\nOptimal Portfolio Weights:")
        for asset, weight in sorted(result.weights.items(), key=lambda x: x[1], reverse=True):
            if abs(weight) > 0.001:  # Only show significant weights
                print(f"  {asset}: {weight:.2%}")
                
    except Exception as e:
        print(f"Optimization failed: {e}")
        return False
    
    # 2. Demonstrate Portfolio Observability
    print("\n2. PORTFOLIO OBSERVABILITY")
    print("-" * 30)
    
    observability = PortfolioObservability(mock_portfolio)
    
    # Calculate portfolio returns (using optimized weights)
    portfolio_returns = (market_data * pd.Series(result.weights)).sum(axis=1)
    
    # Calculate risk metrics
    risk_metrics = observability.calculate_risk_metrics(
        returns=portfolio_returns.tolist(),
        confidence_level=0.95
    )
    
    print(f"Value at Risk (95%): {risk_metrics.value_at_risk:.2%}")
    print(f"Conditional VaR (99%): {risk_metrics.conditional_var:.2%}")
    print(f"Maximum Drawdown: {risk_metrics.max_drawdown:.2%}")
    
    # 3. Demonstrate Integrated System
    print("\n3. INTEGRATED SYSTEM")
    print("-" * 30)
    
    # Create integrated system
    integrated_system = IntegratedPortfolioSystem(
        portfolio=mock_portfolio,
        cache=mock_cache,
        optimization_config=config
    )
    
    print("Integrated portfolio system created successfully")
    
    # Get portfolio summary
    summary = integrated_system.get_portfolio_summary()
    print(f"Portfolio Summary Timestamp: {summary['timestamp']}")
    print(f"Total Portfolio Value: ${summary['portfolio_value']:,.2f}")
    
    # Get instrument exposure
    exposure = integrated_system.get_instrument_exposure("AAPL.NASDAQ")
    if isinstance(exposure, dict) and "exposure" in exposure:
        print(f"AAPL Exposure: ${exposure['exposure']:,.2f}")
    else:
        print("AAPL Exposure: Data not available in mock implementation")
    
    print("\n" + "="*60)
    print("INTEGRATION DEMONSTRATION COMPLETE")
    print("="*60)
    print("The integrated portfolio system successfully demonstrates:")
    print("• Portfolio optimization with realistic market data")
    print("• Risk analysis and observability metrics")
    print("• Integration with Nautilus Trader portfolio components")
    print("• Complete portfolio management workflow")
    
    return True


def main():
    """Main demonstration function"""
    print("PORTFOLIO OPTIMIZATION AND OBSERVABILITY INTEGRATION DEMO")
    print("="*60)
    print("This demo shows the complete integration of the portfolio")
    print("optimization and observability system with Nautilus Trader.")
    print("="*60)
    
    success = demonstrate_integration()
    
    if success:
        print("\n✓ Integration demo completed successfully!")
    else:
        print("\n✗ Integration demo failed!")


if __name__ == "__main__":
    main()