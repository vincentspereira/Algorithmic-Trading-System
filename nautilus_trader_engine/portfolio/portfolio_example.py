"""
Portfolio Optimization and Observability Example
Demonstrates the usage of the portfolio optimization and observability system.
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns

from nautilus_trader.model.identifiers import InstrumentId

# Import our portfolio modules
try:
    from portfolio_optimization import (
        PortfolioOptimizer, 
        NautilusPortfolioOptimizer, 
        PortfolioOptimizationConfig,
        OptimizationMethod,
        RiskMeasure
    )
    from portfolio_observability import (
        PortfolioObservability, 
        PortfolioMetrics,
        RiskMetrics
    )
    from portfolio_integration import IntegratedPortfolioSystem
except ImportError as e:
    print(f"Import error: {e}")
    # Try alternative import paths
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from portfolio_optimization import (
        PortfolioOptimizer, 
        NautilusPortfolioOptimizer, 
        PortfolioOptimizationConfig,
        OptimizationMethod,
        RiskMeasure
    )
    from portfolio_observability import (
        PortfolioObservability, 
        PortfolioMetrics,
        RiskMetrics
    )
    from portfolio_integration import IntegratedPortfolioSystem


def generate_sample_data():
    """Generate sample market data for demonstration"""
    print("Generating sample market data...")
    
    # Create date range
    dates = pd.date_range(start='2020-01-01', end='2023-12-31', freq='D')
    assets = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX']
    
    # Generate correlated returns
    np.random.seed(42)
    
    # Base factor for correlation
    base_factor = np.random.randn(len(dates)) * 0.01
    
    # Generate asset returns with some correlation
    returns_data = {}
    for i, asset in enumerate(assets):
        # Each asset has a mix of base factor and idiosyncratic returns
        base_component = base_factor * (0.3 + i * 0.05)  # Different correlations
        idio_component = np.random.randn(len(dates)) * 0.015  # Idiosyncratic
        returns_data[asset] = base_component + idio_component
        
    df = pd.DataFrame(returns_data, index=dates)
    
    print(f"Generated data for {len(assets)} assets over {len(dates)} days")
    return df


def demonstrate_portfolio_optimization(returns_data):
    """Demonstrate portfolio optimization capabilities"""
    print("\n" + "="*60)
    print("PORTFOLIO OPTIMIZATION DEMONSTRATION")
    print("="*60)
    
    # Test different optimization methods
    methods = [
        (OptimizationMethod.MAXIMUM_SHARPE, "Maximum Sharpe Ratio"),
        (OptimizationMethod.MINIMUM_VARIANCE, "Minimum Variance"),
        (OptimizationMethod.MEAN_VARIANCE, "Mean-Variance Optimization"),
        (OptimizationMethod.RISK_PARITY, "Risk Parity")
    ]
    
    results = []
    
    for method, method_name in methods:
        print(f"\n--- {method_name} ---")
        
        try:
            # Configure optimizer
            config = PortfolioOptimizationConfig(
                method=method,
                risk_free_rate=0.02,  # 2% risk-free rate
                allow_short=False,
                l2_regularization=0.1 if method == OptimizationMethod.MAXIMUM_SHARPE else 0.0
            )
            
            optimizer = PortfolioOptimizer(config)
            
            # Optimize portfolio
            result = optimizer.optimize_portfolio(returns_data)
            
            # Store results
            results.append({
                'method': method_name,
                'expected_return': result.expected_return,
                'risk': result.risk,
                'sharpe_ratio': result.sharpe_ratio,
                'weights': result.weights,
                'turnover': result.turnover or 0
            })
            
            print(f"Expected Return: {result.expected_return:.2%}")
            print(f"Risk (Volatility): {result.risk:.2%}")
            print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
            print(f"Turnover: {result.turnover:.2%}" if result.turnover else "Turnover: N/A")
            
            # Show top 5 weights
            sorted_weights = sorted(result.weights.items(), key=lambda x: abs(x[1]), reverse=True)
            print("Top 5 Portfolio Weights:")
            for asset, weight in sorted_weights[:5]:
                if abs(weight) > 0.001:  # Only show significant weights
                    print(f"  {asset}: {weight:.2%}")
                    
        except Exception as e:
            print(f"Error with {method_name}: {e}")
            results.append({
                'method': method_name,
                'error': str(e)
            })
    
    return results


def demonstrate_risk_analysis(returns_data):
    """Demonstrate risk analysis capabilities"""
    print("\n" + "="*60)
    print("RISK ANALYSIS DEMONSTRATION")
    print("="*60)
    
    # Calculate various risk metrics
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
    
    # Calculate rolling volatility
    rolling_vol = portfolio_returns.rolling(window=30).std() * np.sqrt(252)  # Annualized
    print(f"Current 30-day Volatility: {rolling_vol.iloc[-1]:.2%}")
    print(f"Average Volatility: {rolling_vol.mean():.2%}")
    
    return risk_metrics, rolling_vol


def demonstrate_performance_attribution(returns_data):
    """Demonstrate performance attribution"""
    print("\n" + "="*60)
    print("PERFORMANCE ATTRIBUTION DEMONSTRATION")
    print("="*60)
    
    observability = PortfolioObservability(None)  # Mock portfolio for demo
    
    # Calculate attribution (mock implementation)
    attribution = observability.calculate_performance_attribution()
    
    print("Asset Contributions to Performance:")
    for asset, contribution in list(attribution.asset_contributions.items())[:5]:
        print(f"  {asset}: {contribution:.2%}")
        
    print("\nSector Contributions to Performance:")
    for sector, contribution in attribution.sector_contributions.items():
        print(f"  {sector}: {contribution:.2%}")
        
    return attribution


def create_visualizations(returns_data, optimization_results, rolling_vol):
    """Create visualizations of portfolio analysis"""
    print("\n" + "="*60)
    print("CREATING VISUALIZATIONS")
    print("="*60)
    
    # Set up the plotting style
    plt.style.use('seaborn-v0_8')
    fig = plt.figure(figsize=(15, 12))
    
    # 1. Efficient Frontier Plot (conceptual)
    ax1 = plt.subplot(2, 3, 1)
    methods_data = [r for r in optimization_results if 'error' not in r]
    
    if methods_data:
        risks = [r['risk'] for r in methods_data]
        returns = [r['expected_return'] for r in methods_data]
        sharpe_ratios = [r['sharpe_ratio'] for r in methods_data]
        methods = [r['method'] for r in methods_data]
        
        scatter = ax1.scatter(risks, returns, c=sharpe_ratios, cmap='viridis', s=100)
        ax1.set_xlabel('Risk (Volatility)')
        ax1.set_ylabel('Expected Return')
        ax1.set_title('Portfolio Optimization Methods')
        plt.colorbar(scatter, ax=ax1, label='Sharpe Ratio')
        
        # Annotate points
        for i, method in enumerate(methods):
            ax1.annotate(method.split()[0], (risks[i], returns[i]), 
                        xytext=(5, 5), textcoords='offset points', fontsize=8)
    
    # 2. Asset Correlation Heatmap
    ax2 = plt.subplot(2, 3, 2)
    correlation_matrix = returns_data.corr()
    sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0,
                square=True, ax=ax2, fmt='.2f')
    ax2.set_title('Asset Correlation Matrix')
    
    # 3. Rolling Volatility
    ax3 = plt.subplot(2, 3, 3)
    ax3.plot(rolling_vol.index, rolling_vol.values)
    ax3.set_title('30-Day Rolling Volatility')
    ax3.set_ylabel('Annualized Volatility')
    ax3.tick_params(axis='x', rotation=45)
    
    # 4. Portfolio Weights Comparison
    ax4 = plt.subplot(2, 3, 4)
    methods_with_weights = [r for r in optimization_results if 'weights' in r and 'error' not in r]
    
    if methods_with_weights:
        # Get top 5 assets by average weight
        all_weights = {}
        for result in methods_with_weights:
            for asset, weight in result['weights'].items():
                if asset not in all_weights:
                    all_weights[asset] = []
                all_weights[asset].append(abs(weight))
        
        avg_weights = {asset: np.mean(weights) for asset, weights in all_weights.items()}
        top_assets = sorted(avg_weights.items(), key=lambda x: x[1], reverse=True)[:5]
        
        assets = [item[0] for item in top_assets]
        x_pos = np.arange(len(assets))
        
        # Plot bars for each method
        width = 0.8 / len(methods_with_weights)
        for i, result in enumerate(methods_with_weights):
            weights = [result['weights'].get(asset, 0) for asset in assets]
            ax4.bar(x_pos + i*width, weights, width, label=result['method'].split()[0])
            
        ax4.set_xlabel('Assets')
        ax4.set_ylabel('Portfolio Weight')
        ax4.set_title('Portfolio Weights by Method')
        ax4.set_xticks(x_pos + width * (len(methods_with_weights)-1) / 2)
        ax4.set_xticklabels(assets, rotation=45)
        ax4.legend()
    
    # 5. Risk-Return Scatter
    ax5 = plt.subplot(2, 3, 5)
    asset_returns = returns_data.mean() * 252  # Annualized
    asset_vol = returns_data.std() * np.sqrt(252)  # Annualized
    
    scatter = ax5.scatter(asset_vol, asset_returns, s=100)
    ax5.set_xlabel('Annualized Volatility')
    ax5.set_ylabel('Annualized Return')
    ax5.set_title('Asset Risk-Return Profile')
    
    # Annotate assets
    for i, asset in enumerate(returns_data.columns):
        ax5.annotate(asset, (asset_vol.iloc[i], asset_returns.iloc[i]),
                    xytext=(5, 5), textcoords='offset points', fontsize=8)
    
    # Add Sharpe ratio lines
    risk_free_rate = 0.02
    sharpe_ratios = (asset_returns - risk_free_rate) / asset_vol
    max_sharpe_idx = sharpe_ratios.idxmax()
    tangent_slope = sharpe_ratios[max_sharpe_idx]
    
    # Tangency line
    max_vol = asset_vol.max()
    ax5.plot([0, max_vol], [risk_free_rate, risk_free_rate + tangent_slope * max_vol], 
             'r--', alpha=0.7, label='Tangency Line')
    ax5.axhline(y=risk_free_rate, color='g', linestyle='-', alpha=0.7, label='Risk-Free Rate')
    ax5.legend()
    
    # 6. Drawdown Analysis
    ax6 = plt.subplot(2, 3, 6)
    # Calculate cumulative returns for equal weight portfolio
    equal_weights = {asset: 1/len(returns_data.columns) for asset in returns_data.columns}
    portfolio_returns = (returns_data * pd.Series(equal_weights)).sum(axis=1)
    cumulative_returns = (1 + portfolio_returns).cumprod()
    
    # Calculate running maximum
    running_max = cumulative_returns.expanding().max()
    drawdown = (cumulative_returns - running_max) / running_max
    
    ax6.fill_between(drawdown.index, drawdown.values, 0, alpha=0.3)
    ax6.plot(drawdown.index, drawdown.values, linewidth=1)
    ax6.set_title('Portfolio Drawdown')
    ax6.set_ylabel('Drawdown')
    ax6.tick_params(axis='x', rotation=45)
    ax6.axhline(y=0, color='k', linestyle='-', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('portfolio_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    print("Visualizations saved as 'portfolio_analysis.png'")


async def demonstrate_integration():
    """Demonstrate the integrated portfolio system"""
    print("\n" + "="*60)
    print("INTEGRATED PORTFOLIO SYSTEM DEMONSTRATION")
    print("="*60)
    
    # This would normally use real Nautilus Trader components
    class MockPortfolio:
        pass
        
    class MockCache:
        pass
        
    # Create integrated system
    integrated_system = IntegratedPortfolioSystem(
        portfolio=MockPortfolio(),
        cache=MockCache()
    )
    
    # Start system
    await integrated_system.start()
    print("Integrated portfolio system started")
    
    # Generate sample report
    report = await integrated_system.generate_portfolio_report()
    print(f"Portfolio Report Generated: {report['timestamp']}")
    print(f"Total Portfolio Value: ${report.get('portfolio_summary', {}).get('total_value', 0):,.2f}")
    
    # Get portfolio summary
    summary = integrated_system.get_portfolio_summary()
    print(f"Current Sharpe Ratio: {summary.get('performance', {}).get('sharpe_ratio', 0):.2f}")
    
    # Stop system
    await integrated_system.stop()
    print("Integrated portfolio system stopped")


def main():
    """Main demonstration function"""
    print("PORTFOLIO OPTIMIZATION AND OBSERVABILITY SYSTEM")
    print("="*60)
    print("This demonstration shows the capabilities of the portfolio")
    print("optimization and observability system.")
    print("="*60)
    
    # Generate sample data
    returns_data = generate_sample_data()
    
    # Demonstrate portfolio optimization
    optimization_results = demonstrate_portfolio_optimization(returns_data)
    
    # Demonstrate risk analysis
    risk_metrics, rolling_vol = demonstrate_risk_analysis(returns_data)
    
    # Demonstrate performance attribution
    attribution = demonstrate_performance_attribution(returns_data)
    
    # Create visualizations
    create_visualizations(returns_data, optimization_results, rolling_vol)
    
    # Demonstrate integration (async)
    asyncio.run(demonstrate_integration())
    
    print("\n" + "="*60)
    print("DEMONSTRATION COMPLETE")
    print("="*60)
    print("The portfolio optimization and observability system provides:")
    print("• Multiple optimization methods (Mean-Variance, Risk Parity, etc.)")
    print("• Comprehensive risk analysis (VaR, CVaR, Drawdown, etc.)")
    print("• Performance attribution and contribution analysis")
    print("• Real-time monitoring and alerting capabilities")
    print("• Integration with Nautilus Trader portfolio system")
    print("• Visualization and reporting tools")


if __name__ == "__main__":
    main()