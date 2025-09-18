#!/usr/bin/env python3
"""
Advanced Portfolio Optimization Demo

This script demonstrates the comprehensive portfolio optimization capabilities
integrating PyPortfolioOpt and Riskfolio-Lib with advanced attribution features.

Features demonstrated:
- Multiple optimization methods (Mean-Variance, Black-Litterman, HRP, CVaR, etc.)
- Advanced risk measures and constraints
- Performance attribution analysis
- Transaction cost optimization
- Comprehensive portfolio metrics

Author: Algorithmic Trading System
Date: 2024
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Import our portfolio management system
from algorithmic_trading_service.portfolio_management import (
    PortfolioManager, OptimizationConfig, OptimizationMethod, RiskMeasure
)

# Set up logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_sample_data(n_assets=10, n_periods=252*3, start_date='2021-01-01'):
    """
    Generate sample price data for demonstration
    
    Args:
        n_assets: Number of assets
        n_periods: Number of time periods
        start_date: Start date for the data
        
    Returns:
        DataFrame with price data
    """
    np.random.seed(42)  # For reproducible results
    
    # Generate asset names
    assets = [f'ASSET_{i+1}' for i in range(n_assets)]
    
    # Generate dates
    dates = pd.date_range(start=start_date, periods=n_periods, freq='D')
    
    # Generate correlated returns
    # Create a correlation matrix
    correlation_matrix = np.random.uniform(0.1, 0.7, (n_assets, n_assets))
    correlation_matrix = (correlation_matrix + correlation_matrix.T) / 2
    np.fill_diagonal(correlation_matrix, 1.0)
    
    # Generate returns with different volatilities and expected returns
    expected_returns = np.random.uniform(0.05, 0.15, n_assets) / 252  # Daily returns
    volatilities = np.random.uniform(0.15, 0.35, n_assets) / np.sqrt(252)  # Daily volatilities
    
    # Generate correlated random returns
    random_returns = np.random.multivariate_normal(
        mean=expected_returns,
        cov=np.outer(volatilities, volatilities) * correlation_matrix,
        size=n_periods
    )
    
    # Convert to prices (starting at 100)
    prices = pd.DataFrame(index=dates, columns=assets)
    prices.iloc[0] = 100.0
    
    for i in range(1, n_periods):
        prices.iloc[i] = prices.iloc[i-1] * (1 + random_returns[i])
    
    return prices

def generate_benchmark_data(price_data):
    """
    Generate benchmark data (market index)
    
    Args:
        price_data: Asset price data
        
    Returns:
        Series with benchmark prices
    """
    # Create a market-cap weighted benchmark (simplified)
    returns = price_data.pct_change().dropna()
    equal_weight_returns = returns.mean(axis=1)
    
    benchmark = pd.Series(index=price_data.index, name='BENCHMARK')
    benchmark.iloc[0] = 100.0
    
    for i in range(1, len(benchmark)):
        benchmark.iloc[i] = benchmark.iloc[i-1] * (1 + equal_weight_returns.iloc[i-1])
    
    return benchmark

def demonstrate_optimization_methods(portfolio_manager, price_data):
    """
    Demonstrate different optimization methods
    
    Args:
        portfolio_manager: PortfolioManager instance
        price_data: Price data for optimization
        
    Returns:
        Dictionary with optimization results
    """
    results = {}
    
    # Define optimization configurations
    configs = {
        'Mean Variance': OptimizationConfig(
            method=OptimizationMethod.MEAN_VARIANCE,
            risk_measure=RiskMeasure.VARIANCE,
            risk_free_rate=0.02,
            max_weight=0.3,
            min_weight=0.01
        ),
        'Maximum Sharpe': OptimizationConfig(
            method=OptimizationMethod.MAXIMUM_SHARPE,
            risk_free_rate=0.02,
            max_weight=0.4,
            min_weight=0.0
        ),
        'Minimum Variance': OptimizationConfig(
            method=OptimizationMethod.MINIMUM_VARIANCE,
            max_weight=0.5,
            min_weight=0.0
        ),
        'Risk Parity': OptimizationConfig(
            method=OptimizationMethod.RISK_PARITY,
            risk_free_rate=0.02
        ),
        'Hierarchical Risk Parity': OptimizationConfig(
            method=OptimizationMethod.HIERARCHICAL_RISK_PARITY,
            risk_free_rate=0.02
        ),
        'CVaR Optimization': OptimizationConfig(
            method=OptimizationMethod.CVAR_OPTIMIZATION,
            risk_measure=RiskMeasure.CVAR,
            alpha=0.05,
            target_return=0.10
        )
    }
    
    print("\n" + "="*60)
    print("PORTFOLIO OPTIMIZATION METHODS COMPARISON")
    print("="*60)
    
    for name, config in configs.items():
        try:
            print(f"\nOptimizing using {name}...")
            result = portfolio_manager.optimize(config)
            results[name] = result
            
            if 'weights' in result:
                weights = result['weights']
                print(f"  Status: {result.get('optimization_status', 'Unknown')}")
                print(f"  Top 5 holdings:")
                top_holdings = weights.nlargest(5)
                for asset, weight in top_holdings.items():
                    print(f"    {asset}: {weight:.3f} ({weight*100:.1f}%)")
                
                if 'metrics' in result:
                    metrics = result['metrics']
                    print(f"  Expected Return: {metrics.expected_return:.3f} ({metrics.expected_return*100:.1f}%)")
                    print(f"  Volatility: {metrics.volatility:.3f} ({metrics.volatility*100:.1f}%)")
                    print(f"  Sharpe Ratio: {metrics.sharpe_ratio:.3f}")
                    print(f"  Max Drawdown: {metrics.max_drawdown:.3f} ({metrics.max_drawdown*100:.1f}%)")
            else:
                print(f"  Optimization failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"  Error in {name}: {str(e)}")
            results[name] = {'error': str(e)}
    
    return results

def demonstrate_black_litterman(portfolio_manager, price_data):
    """
    Demonstrate Black-Litterman optimization with views
    
    Args:
        portfolio_manager: PortfolioManager instance
        price_data: Price data for optimization
        
    Returns:
        Optimization result
    """
    print("\n" + "="*60)
    print("BLACK-LITTERMAN OPTIMIZATION WITH VIEWS")
    print("="*60)
    
    # Define some market views
    assets = price_data.columns.tolist()
    views = {
        assets[0]: 0.12,  # Expect 12% return for first asset
        assets[1]: 0.08,  # Expect 8% return for second asset
        assets[2]: 0.15   # Expect 15% return for third asset
    }
    
    confidence = {
        assets[0]: 0.8,   # High confidence
        assets[1]: 0.6,   # Medium confidence
        assets[2]: 0.9    # Very high confidence
    }
    
    config = OptimizationConfig(
        method=OptimizationMethod.BLACK_LITTERMAN,
        risk_free_rate=0.02,
        max_weight=0.4,
        min_weight=0.0,
        black_litterman_views=views,
        black_litterman_confidence=confidence
    )
    
    print("Market Views:")
    for asset, view in views.items():
        conf = confidence[asset]
        print(f"  {asset}: {view*100:.1f}% expected return (confidence: {conf*100:.0f}%)")
    
    try:
        result = portfolio_manager.optimize(config)
        
        if 'weights' in result:
            weights = result['weights']
            print(f"\nOptimization Status: {result.get('optimization_status', 'Unknown')}")
            print(f"Views Applied: {result.get('views_applied', 0)}")
            
            print("\nOptimal Portfolio Weights:")
            for asset, weight in weights.items():
                if weight > 0.001:  # Only show significant weights
                    view_indicator = " (VIEW)" if asset in views else ""
                    print(f"  {asset}: {weight:.3f} ({weight*100:.1f}%){view_indicator}")
            
            if 'metrics' in result:
                metrics = result['metrics']
                print(f"\nPortfolio Metrics:")
                print(f"  Expected Return: {metrics.expected_return:.3f} ({metrics.expected_return*100:.1f}%)")
                print(f"  Volatility: {metrics.volatility:.3f} ({metrics.volatility*100:.1f}%)")
                print(f"  Sharpe Ratio: {metrics.sharpe_ratio:.3f}")
        
        return result
        
    except Exception as e:
        print(f"Black-Litterman optimization failed: {str(e)}")
        return {'error': str(e)}

def demonstrate_performance_attribution(portfolio_manager, price_data, benchmark_data):
    """
    Demonstrate performance attribution analysis
    
    Args:
        portfolio_manager: PortfolioManager instance
        price_data: Price data
        benchmark_data: Benchmark price data
        
    Returns:
        Attribution analysis result
    """
    print("\n" + "="*60)
    print("PERFORMANCE ATTRIBUTION ANALYSIS")
    print("="*60)
    
    # Create a sample portfolio (equal weight)
    assets = price_data.columns
    portfolio_weights = pd.Series(1.0/len(assets), index=assets)
    
    # Create benchmark weights (also equal weight for simplicity)
    benchmark_weights = pd.Series(1.0/len(assets), index=assets)
    
    # Add some sector mapping for demonstration
    sector_mapping = {}
    n_assets = len(assets)
    sectors = ['Technology', 'Healthcare', 'Finance', 'Energy', 'Consumer']
    
    for i, asset in enumerate(assets):
        sector_mapping[asset] = sectors[i % len(sectors)]
    
    print("Sector Mapping:")
    for sector in sectors:
        sector_assets = [asset for asset, sec in sector_mapping.items() if sec == sector]
        print(f"  {sector}: {', '.join(sector_assets)}")
    
    try:
        returns_data = price_data.pct_change().dropna()
        attribution = portfolio_manager.performance_attribution(
            portfolio_weights=portfolio_weights,
            benchmark_weights=benchmark_weights,
            returns_data=returns_data,
            sector_mapping=sector_mapping
        )
        
        print(f"\nTotal Excess Return: {attribution.total_return:.4f} ({attribution.total_return*100:.2f}%)")
        
        print("\nAsset Allocation Effects:")
        for asset, effect in attribution.asset_allocation_effect.items():
            if abs(effect) > 0.0001:  # Only show significant effects
                print(f"  {asset}: {effect:.4f} ({effect*100:.2f}%)")
        
        print("\nSector Attribution:")
        for sector, effects in attribution.sector_attribution.items():
            total_effect = effects['total_effect']
            if abs(total_effect) > 0.0001:
                print(f"  {sector}: {total_effect:.4f} ({total_effect*100:.2f}%)")
        
        print("\nFactor Attribution:")
        for factor, effect in attribution.factor_attribution.items():
            print(f"  {factor}: {effect:.4f} ({effect*100:.2f}%)")
        
        return attribution
        
    except Exception as e:
        print(f"Performance attribution failed: {str(e)}")
        return None

def demonstrate_rebalancing(portfolio_manager):
    """
    Demonstrate portfolio rebalancing with transaction costs
    
    Args:
        portfolio_manager: PortfolioManager instance
        
    Returns:
        Rebalancing result
    """
    print("\n" + "="*60)
    print("PORTFOLIO REBALANCING WITH TRANSACTION COSTS")
    print("="*60)
    
    # Current portfolio (in dollar values)
    current_portfolio = {
        'ASSET_1': 25000,
        'ASSET_2': 30000,
        'ASSET_3': 20000,
        'ASSET_4': 15000,
        'ASSET_5': 10000
    }
    
    # Target allocations (weights)
    target_allocations = {
        'ASSET_1': 0.30,
        'ASSET_2': 0.25,
        'ASSET_3': 0.20,
        'ASSET_4': 0.15,
        'ASSET_5': 0.10
    }
    
    total_value = sum(current_portfolio.values())
    print(f"Current Portfolio Value: ${total_value:,.2f}")
    
    print("\nCurrent Weights vs Target Weights:")
    for asset in current_portfolio.keys():
        current_weight = current_portfolio[asset] / total_value
        target_weight = target_allocations[asset]
        diff = target_weight - current_weight
        print(f"  {asset}: {current_weight:.3f} → {target_weight:.3f} (Δ {diff:+.3f})")
    
    try:
        rebalancing_result = portfolio_manager.rebalance(
            current_portfolio=current_portfolio,
            target_allocations=target_allocations,
            transaction_costs=0.001,  # 0.1% transaction cost
            min_trade_size=500  # Minimum $500 trade
        )
        
        print(f"\nRebalancing Analysis:")
        print(f"  Total Transaction Cost: ${rebalancing_result['total_transaction_cost']:,.2f}")
        print(f"  Portfolio Turnover: {rebalancing_result['turnover']:.3f} ({rebalancing_result['turnover']*100:.1f}%)")
        print(f"  Net Rebalancing Cost: {rebalancing_result['net_rebalancing_cost']:.4f} ({rebalancing_result['net_rebalancing_cost']*100:.2f}%)")
        
        summary = rebalancing_result['rebalancing_summary']
        print(f"  Total Trades Required: {summary['total_trades']}")
        print(f"  Total Value Traded: ${summary['total_value_traded']:,.2f}")
        print(f"  Estimated Execution Time: {summary['estimated_execution_time']} minutes")
        
        print("\nRequired Trades:")
        for asset, trade_info in rebalancing_result['trades'].items():
            direction = trade_info['trade_direction']
            value = abs(trade_info['trade_value'])
            print(f"  {asset}: {direction.upper()} ${value:,.2f}")
        
        return rebalancing_result
        
    except Exception as e:
        print(f"Rebalancing analysis failed: {str(e)}")
        return None

def create_visualization(optimization_results):
    """
    Create visualizations of optimization results
    
    Args:
        optimization_results: Dictionary of optimization results
    """
    print("\n" + "="*60)
    print("CREATING VISUALIZATIONS")
    print("="*60)
    
    try:
        # Extract metrics for comparison
        methods = []
        returns = []
        volatilities = []
        sharpe_ratios = []
        
        for method, result in optimization_results.items():
            if 'metrics' in result and result['metrics'] is not None:
                methods.append(method)
                metrics = result['metrics']
                returns.append(metrics.expected_return)
                volatilities.append(metrics.volatility)
                sharpe_ratios.append(metrics.sharpe_ratio)
        
        if len(methods) > 0:
            # Create subplots
            fig, axes = plt.subplots(2, 2, figsize=(15, 12))
            fig.suptitle('Portfolio Optimization Results Comparison', fontsize=16, fontweight='bold')
            
            # Risk-Return scatter plot
            axes[0, 0].scatter(volatilities, returns, s=100, alpha=0.7)
            for i, method in enumerate(methods):
                axes[0, 0].annotate(method, (volatilities[i], returns[i]), 
                                  xytext=(5, 5), textcoords='offset points', fontsize=8)
            axes[0, 0].set_xlabel('Volatility (Risk)')
            axes[0, 0].set_ylabel('Expected Return')
            axes[0, 0].set_title('Risk-Return Profile')
            axes[0, 0].grid(True, alpha=0.3)
            
            # Sharpe ratio comparison
            bars = axes[0, 1].bar(range(len(methods)), sharpe_ratios, alpha=0.7)
            axes[0, 1].set_xlabel('Optimization Method')
            axes[0, 1].set_ylabel('Sharpe Ratio')
            axes[0, 1].set_title('Sharpe Ratio Comparison')
            axes[0, 1].set_xticks(range(len(methods)))
            axes[0, 1].set_xticklabels(methods, rotation=45, ha='right')
            axes[0, 1].grid(True, alpha=0.3)
            
            # Add value labels on bars
            for bar, value in zip(bars, sharpe_ratios):
                height = bar.get_height()
                axes[0, 1].text(bar.get_x() + bar.get_width()/2., height + 0.01,
                               f'{value:.3f}', ha='center', va='bottom', fontsize=8)
            
            # Portfolio weights heatmap (for first few methods)
            weights_data = []
            weight_methods = []
            
            for method, result in list(optimization_results.items())[:4]:  # First 4 methods
                if 'weights' in result and result['weights'] is not None:
                    weights_data.append(result['weights'].values)
                    weight_methods.append(method)
            
            if weights_data:
                weights_df = pd.DataFrame(weights_data, 
                                        index=weight_methods,
                                        columns=optimization_results[weight_methods[0]]['weights'].index)
                
                sns.heatmap(weights_df, annot=True, fmt='.3f', cmap='RdYlBu_r', 
                           ax=axes[1, 0], cbar_kws={'label': 'Weight'})
                axes[1, 0].set_title('Portfolio Weights Heatmap')
                axes[1, 0].set_xlabel('Assets')
                axes[1, 0].set_ylabel('Optimization Methods')
            
            # Risk metrics comparison
            if len(methods) > 0:
                first_result = optimization_results[methods[0]]
                if 'metrics' in first_result and first_result['metrics'] is not None:
                    metrics_names = ['Max Drawdown', 'VaR 95%', 'CVaR 95%']
                    metrics_values = [
                        first_result['metrics'].max_drawdown,
                        abs(first_result['metrics'].var_95),
                        abs(first_result['metrics'].cvar_95)
                    ]
                    
                    axes[1, 1].bar(metrics_names, metrics_values, alpha=0.7, color=['red', 'orange', 'darkred'])
                    axes[1, 1].set_title(f'Risk Metrics - {methods[0]}')
                    axes[1, 1].set_ylabel('Risk Value')
                    axes[1, 1].tick_params(axis='x', rotation=45)
                    axes[1, 1].grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # Save the plot
            output_path = 'portfolio_optimization_results.png'
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"Visualization saved as: {output_path}")
            
            # Show the plot
            plt.show()
        
    except Exception as e:
        print(f"Visualization creation failed: {str(e)}")

def main():
    """
    Main demonstration function
    """
    print("\n" + "="*80)
    print("ADVANCED PORTFOLIO OPTIMIZATION SYSTEM DEMONSTRATION")
    print("Integrating PyPortfolioOpt and Riskfolio-Lib with Attribution Analysis")
    print("="*80)
    
    try:
        # Generate sample data
        print("\nGenerating sample market data...")
        price_data = generate_sample_data(n_assets=8, n_periods=252*2)  # 2 years of daily data
        benchmark_data = generate_benchmark_data(price_data)
        
        print(f"Generated data for {len(price_data.columns)} assets over {len(price_data)} periods")
        print(f"Date range: {price_data.index[0].strftime('%Y-%m-%d')} to {price_data.index[-1].strftime('%Y-%m-%d')}")
        
        # Initialize portfolio manager
        print("\nInitializing Portfolio Manager...")
        portfolio_manager = PortfolioManager(
            risk_free_rate=0.02,
            benchmark_ticker="BENCHMARK",
            rebalancing_frequency="monthly"
        )
        
        # Load data
        portfolio_manager.load_data(price_data, benchmark_data)
        
        # Demonstrate optimization methods
        optimization_results = demonstrate_optimization_methods(portfolio_manager, price_data)
        
        # Demonstrate Black-Litterman with views
        bl_result = demonstrate_black_litterman(portfolio_manager, price_data)
        if bl_result and 'error' not in bl_result:
            optimization_results['Black-Litterman'] = bl_result
        
        # Demonstrate performance attribution
        attribution_result = demonstrate_performance_attribution(
            portfolio_manager, price_data, benchmark_data
        )
        
        # Demonstrate rebalancing
        rebalancing_result = demonstrate_rebalancing(portfolio_manager)
        
        # Create visualizations
        create_visualization(optimization_results)
        
        print("\n" + "="*80)
        print("DEMONSTRATION COMPLETED SUCCESSFULLY")
        print("="*80)
        
        # Summary statistics
        successful_optimizations = sum(1 for result in optimization_results.values() 
                                     if 'error' not in result)
        total_optimizations = len(optimization_results)
        
        print(f"\nSummary:")
        print(f"  Successful Optimizations: {successful_optimizations}/{total_optimizations}")
        print(f"  Performance Attribution: {'✓' if attribution_result else '✗'}")
        print(f"  Rebalancing Analysis: {'✓' if rebalancing_result else '✗'}")
        
        if successful_optimizations > 0:
            best_sharpe = max(
                (result['metrics'].sharpe_ratio for result in optimization_results.values() 
                 if 'metrics' in result and result['metrics'] is not None),
                default=0
            )
            print(f"  Best Sharpe Ratio Achieved: {best_sharpe:.3f}")
        
    except Exception as e:
        logger.error(f"Demonstration failed: {str(e)}")
        print(f"\nERROR: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)