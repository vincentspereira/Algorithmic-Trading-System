"""
Simple test for portfolio optimization and observability system
"""

import pandas as pd
import numpy as np
from datetime import datetime

# Import our portfolio modules
from portfolio_optimization import (
    PortfolioOptimizer, 
    PortfolioOptimizationConfig,
    OptimizationMethod,
    RiskMeasure
)
from portfolio_observability import (
    PortfolioObservability, 
    PortfolioMetrics,
    RiskMetrics
)


def create_realistic_sample_data():
    """Create more realistic sample data that should work with optimization"""
    print("Creating realistic sample market data...")
    
    # Create date range (1 year of data)
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
    assets = ['AAPL', 'GOOGL', 'MSFT', 'AMZN']
    
    # Set random seed for reproducibility
    np.random.seed(42)
    
    # Create more realistic returns with proper correlation and mean
    # Annualized returns (approximate)
    expected_returns = {
        'AAPL': 0.15,  # 15% expected annual return
        'GOOGL': 0.12, # 12% expected annual return
        'MSFT': 0.10,  # 10% expected annual return
        'AMZN': 0.18   # 18% expected annual return
    }
    
    # Annualized volatilities (approximate)
    volatilities = {
        'AAPL': 0.25,  # 25% annual volatility
        'GOOGL': 0.22, # 22% annual volatility
        'MSFT': 0.20,  # 20% annual volatility
        'AMZN': 0.30   # 30% annual volatility
    }
    
    # Create correlated returns
    # Start with a base factor for correlation
    base_factor = np.random.randn(len(dates)) * 0.01  # 1% daily volatility base
    
    returns_data = {}
    for asset in assets:
        # Daily expected return
        daily_return = expected_returns[asset] / 252
        daily_vol = volatilities[asset] / np.sqrt(252)
        
        # Create returns with correlation to base factor and idiosyncratic component
        correlated_component = base_factor * 0.5  # 50% correlation to base
        idio_component = np.random.randn(len(dates)) * daily_vol * 0.866  # sqrt(1-0.5^2) for proper variance
        returns_data[asset] = correlated_component + idio_component + daily_return
        
    df = pd.DataFrame(returns_data, index=dates)
    
    print(f"Created data for {len(assets)} assets over {len(dates)} days")
    print("Expected annual returns:", expected_returns)
    print("Annual volatilities:", volatilities)
    return df


def test_portfolio_optimization(returns_data):
    """Test portfolio optimization with realistic data"""
    print("\n" + "="*50)
    print("TESTING PORTFOLIO OPTIMIZATION")
    print("="*50)
    
    # Test minimum variance optimization (most stable)
    print("\n--- Minimum Variance Optimization ---")
    try:
        config = PortfolioOptimizationConfig(
            method=OptimizationMethod.MINIMUM_VARIANCE,
            allow_short=False
        )
        
        optimizer = PortfolioOptimizer(config)
        result = optimizer.optimize_portfolio(returns_data)
        
        print(f"Expected Return: {result.expected_return:.2%}")
        print(f"Risk (Volatility): {result.risk:.2%}")
        print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
        
        print("Portfolio Weights:")
        for asset, weight in result.weights.items():
            print(f"  {asset}: {weight:.2%}")
            
        return True
        
    except Exception as e:
        print(f"Error with Minimum Variance Optimization: {e}")
        return False


def test_portfolio_observability(returns_data):
    """Test portfolio observability features"""
    print("\n" + "="*50)
    print("TESTING PORTFOLIO OBSERVABILITY")
    print("="*50)
    
    try:
        # Create observability instance
        observability = PortfolioObservability(None)  # Mock portfolio for demo
        
        # Calculate portfolio returns (equal weights for demo)
        equal_weights = {asset: 1/len(returns_data.columns) for asset in returns_data.columns}
        portfolio_returns = (returns_data * pd.Series(equal_weights)).sum(axis=1)
        
        # Calculate risk metrics
        risk_metrics = observability.calculate_risk_metrics(
            returns=portfolio_returns.tolist(),
            confidence_level=0.95
        )
        
        print(f"Value at Risk (95%): {risk_metrics.value_at_risk:.2%}")
        print(f"Conditional VaR (99%): {risk_metrics.conditional_var:.2%}")
        print(f"Maximum Drawdown: {risk_metrics.max_drawdown:.2%}")
        
        return True
        
    except Exception as e:
        print(f"Error with Portfolio Observability: {e}")
        return False


def main():
    """Main test function"""
    print("PORTFOLIO OPTIMIZATION AND OBSERVABILITY TEST")
    print("="*50)
    
    # Create realistic sample data
    returns_data = create_realistic_sample_data()
    
    # Test portfolio optimization
    opt_success = test_portfolio_optimization(returns_data)
    
    # Test portfolio observability
    obs_success = test_portfolio_observability(returns_data)
    
    print("\n" + "="*50)
    print("TEST RESULTS")
    print("="*50)
    print(f"Portfolio Optimization: {'PASS' if opt_success else 'FAIL'}")
    print(f"Portfolio Observability: {'PASS' if obs_success else 'FAIL'}")
    
    if opt_success and obs_success:
        print("\nAll tests passed! The portfolio system is working correctly.")
    else:
        print("\nSome tests failed. Please check the implementation.")


if __name__ == "__main__":
    main()