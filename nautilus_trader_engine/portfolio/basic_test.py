"""
Basic test for portfolio optimization and observability system
"""

import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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


def test_basic_functionality():
    """Test basic functionality of the portfolio system"""
    print("Testing basic portfolio system functionality...")
    
    # Test optimizer initialization
    config = PortfolioOptimizationConfig()
    optimizer = PortfolioOptimizer(config)
    print("✓ PortfolioOptimizer initialized successfully")
    
    # Test observability initialization
    observability = PortfolioObservability(None)
    print("✓ PortfolioObservability initialized successfully")
    
    # Test configuration
    print(f"✓ Default optimization method: {config.method.value}")
    print(f"✓ Default risk measure: {config.risk_measure.value}")
    
    print("\nAll basic tests passed!")
    return True


if __name__ == "__main__":
    test_basic_functionality()