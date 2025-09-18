import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from enum import Enum

# PyPortfolioOpt imports
try:
    from pypfopt import EfficientFrontier, risk_models, expected_returns
    from pypfopt.hierarchical_portfolio import HRPOpt
    from pypfopt.black_litterman import BlackLittermanModel
    from pypfopt.risk_models import CovarianceShrinkage
    from pypfopt.expected_returns import mean_historical_return
    from pypfopt.discrete_allocation import DiscreteAllocation, get_latest_prices
    PYPFOPT_AVAILABLE = True
except ImportError:
    PYPFOPT_AVAILABLE = False
    logging.warning("PyPortfolioOpt not available. Portfolio optimization features will be limited.")

# Riskfolio-Lib imports
try:
    import riskfolio as rp
    RISKFOLIO_AVAILABLE = True
except ImportError:
    RISKFOLIO_AVAILABLE = False
    logging.warning("Riskfolio-Lib not available. Advanced risk analysis features will be limited.")

# Additional imports for advanced features
try:
    import cvxpy as cp
    CVXPY_AVAILABLE = True
except ImportError:
    CVXPY_AVAILABLE = False

try:
    import scipy.optimize as sco
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

logger = logging.getLogger(__name__)

class OptimizationMethod(Enum):
    """Portfolio optimization methods"""
    MEAN_VARIANCE = "mean_variance"
    HIERARCHICAL_RISK_PARITY = "hrp"
    BLACK_LITTERMAN = "black_litterman"
    RISK_PARITY = "risk_parity"
    MINIMUM_VARIANCE = "min_variance"
    MAXIMUM_SHARPE = "max_sharpe"
    MAXIMUM_QUADRATIC_UTILITY = "max_quad_utility"
    CVAR_OPTIMIZATION = "cvar"
    WORST_CASE_OPTIMIZATION = "worst_case"
    HIERARCHICAL_CLUSTERING = "hierarchical_clustering"

class RiskMeasure(Enum):
    """Risk measures for optimization"""
    VARIANCE = "MV"  # Mean Variance
    CVAR = "CVaR"  # Conditional Value at Risk
    WORST_REALIZATION = "WR"  # Worst Realization
    MAXIMUM_DRAWDOWN = "MDD"  # Maximum Drawdown
    LOWER_PARTIAL_MOMENT = "LPM"  # Lower Partial Moment
    ENTROPIC_VALUE_AT_RISK = "EVaR"  # Entropic Value at Risk

@dataclass
class OptimizationConfig:
    """Configuration for portfolio optimization"""
    method: OptimizationMethod
    risk_measure: RiskMeasure = RiskMeasure.VARIANCE
    target_return: Optional[float] = None
    risk_free_rate: float = 0.02
    gamma: float = 1.0  # Risk aversion parameter
    alpha: float = 0.05  # Confidence level for VaR/CVaR
    max_weight: float = 1.0  # Maximum weight per asset
    min_weight: float = 0.0  # Minimum weight per asset
    turnover_constraint: Optional[float] = None
    sector_constraints: Optional[Dict[str, Tuple[float, float]]] = None
    black_litterman_views: Optional[Dict[str, float]] = None
    black_litterman_confidence: Optional[Dict[str, float]] = None

@dataclass
class PortfolioMetrics:
    """Portfolio performance and risk metrics"""
    expected_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    var_95: float
    var_99: float
    cvar_95: float
    cvar_99: float
    beta: float
    alpha: float
    information_ratio: float
    tracking_error: float
    treynor_ratio: float

@dataclass
class AttributionAnalysis:
    """Performance attribution analysis"""
    total_return: float
    asset_allocation_effect: Dict[str, float]
    security_selection_effect: Dict[str, float]
    interaction_effect: Dict[str, float]
    sector_attribution: Dict[str, Dict[str, float]]
    factor_attribution: Dict[str, float]
    currency_attribution: Optional[Dict[str, float]] = None

class PortfolioManager:
    """Advanced Portfolio Management System with PyPortfolioOpt and Riskfolio-Lib integration"""
    
    def __init__(self, 
                 risk_free_rate: float = 0.02,
                 benchmark_ticker: str = "SPY",
                 rebalancing_frequency: str = "monthly"):
        """
        Initialize Portfolio Manager
        
        Args:
            risk_free_rate: Risk-free rate for calculations
            benchmark_ticker: Benchmark for performance comparison
            rebalancing_frequency: Frequency for portfolio rebalancing
        """
        self.risk_free_rate = risk_free_rate
        self.benchmark_ticker = benchmark_ticker
        self.rebalancing_frequency = rebalancing_frequency
        
        # Initialize optimization engines
        self.pypfopt_engine = PyPortfolioOptEngine() if PYPFOPT_AVAILABLE else None
        self.riskfolio_engine = RiskfolioEngine() if RISKFOLIO_AVAILABLE else None
        
        # Portfolio state
        self.current_weights: Optional[pd.Series] = None
        self.price_data: Optional[pd.DataFrame] = None
        self.returns_data: Optional[pd.DataFrame] = None
        self.benchmark_data: Optional[pd.Series] = None
        
        logger.info(f"Portfolio Manager initialized with engines: "
                   f"PyPortfolioOpt={'Available' if PYPFOPT_AVAILABLE else 'Not Available'}, "
                   f"Riskfolio={'Available' if RISKFOLIO_AVAILABLE else 'Not Available'}")
    
    def load_data(self, 
                  price_data: pd.DataFrame, 
                  benchmark_data: Optional[pd.Series] = None) -> None:
        """
        Load price data for optimization
        
        Args:
            price_data: DataFrame with asset prices (columns: assets, index: dates)
            benchmark_data: Series with benchmark prices
        """
        self.price_data = price_data.copy()
        self.returns_data = price_data.pct_change().dropna()
        
        if benchmark_data is not None:
            self.benchmark_data = benchmark_data.copy()
        
        logger.info(f"Loaded data for {len(price_data.columns)} assets over {len(price_data)} periods")
    
    def optimize(self, 
                 config: OptimizationConfig,
                 assets: Optional[List[str]] = None) -> Dict[str, Union[pd.Series, Dict]]:
        """
        Optimize portfolio using specified method and configuration
        
        Args:
            config: Optimization configuration
            assets: List of assets to include (if None, use all available)
            
        Returns:
            Dictionary containing optimized weights and metrics
        """
        if self.returns_data is None:
            raise ValueError("No data loaded. Call load_data() first.")
        
        # Select assets
        if assets is not None:
            available_assets = [asset for asset in assets if asset in self.returns_data.columns]
            if not available_assets:
                raise ValueError("None of the specified assets are available in the data")
            returns_subset = self.returns_data[available_assets]
        else:
            returns_subset = self.returns_data
        
        # Route to appropriate optimization engine
        if config.method in [OptimizationMethod.MEAN_VARIANCE, 
                           OptimizationMethod.BLACK_LITTERMAN,
                           OptimizationMethod.HIERARCHICAL_RISK_PARITY,
                           OptimizationMethod.MINIMUM_VARIANCE,
                           OptimizationMethod.MAXIMUM_SHARPE] and self.pypfopt_engine:
            
            result = self.pypfopt_engine.optimize(returns_subset, config)
            
        elif config.method in [OptimizationMethod.CVAR_OPTIMIZATION,
                             OptimizationMethod.WORST_CASE_OPTIMIZATION,
                             OptimizationMethod.HIERARCHICAL_CLUSTERING] and self.riskfolio_engine:
            
            result = self.riskfolio_engine.optimize(returns_subset, config)
            
        else:
            # Fallback to basic optimization
            result = self._basic_optimization(returns_subset, config)
        
        # Store current weights
        if 'weights' in result:
            self.current_weights = result['weights']
        
        # Calculate comprehensive metrics
        if 'weights' in result:
            metrics = self.calculate_portfolio_metrics(result['weights'], returns_subset)
            result['metrics'] = metrics
        
        return result
    
    def rebalance(self, 
                  current_portfolio: Dict[str, float], 
                  target_allocations: Dict[str, float],
                  transaction_costs: float = 0.001,
                  min_trade_size: float = 100) -> Dict[str, Union[Dict, float]]:
        """
        Calculate rebalancing trades with transaction cost optimization
        
        Args:
            current_portfolio: Current portfolio positions {asset: value}
            target_allocations: Target weight allocations {asset: weight}
            transaction_costs: Transaction cost rate
            min_trade_size: Minimum trade size to execute
            
        Returns:
            Dictionary with rebalancing instructions and costs
        """
        total_value = sum(current_portfolio.values())
        current_weights = {asset: value/total_value for asset, value in current_portfolio.items()}
        
        # Calculate required trades
        trades = {}
        total_transaction_cost = 0.0
        
        all_assets = set(list(current_weights.keys()) + list(target_allocations.keys()))
        
        for asset in all_assets:
            current_weight = current_weights.get(asset, 0.0)
            target_weight = target_allocations.get(asset, 0.0)
            
            weight_diff = target_weight - current_weight
            trade_value = weight_diff * total_value
            
            if abs(trade_value) >= min_trade_size:
                trades[asset] = {
                    'current_weight': current_weight,
                    'target_weight': target_weight,
                    'trade_value': trade_value,
                    'trade_direction': 'buy' if trade_value > 0 else 'sell'
                }
                total_transaction_cost += abs(trade_value) * transaction_costs
        
        # Calculate turnover
        turnover = sum(abs(trade['trade_value']) for trade in trades.values()) / total_value
        
        return {
            'trades': trades,
            'total_transaction_cost': total_transaction_cost,
            'turnover': turnover,
            'net_rebalancing_cost': total_transaction_cost / total_value,
            'rebalancing_summary': {
                'total_trades': len(trades),
                'total_value_traded': sum(abs(trade['trade_value']) for trade in trades.values()),
                'estimated_execution_time': len(trades) * 2  # Assume 2 minutes per trade
            }
        }
    
    def calculate_portfolio_metrics(self, 
                                  weights: pd.Series, 
                                  returns_data: pd.DataFrame) -> PortfolioMetrics:
        """
        Calculate comprehensive portfolio metrics
        
        Args:
            weights: Portfolio weights
            returns_data: Historical returns data
            
        Returns:
            PortfolioMetrics object with all calculated metrics
        """
        # Align weights with returns data
        aligned_weights = weights.reindex(returns_data.columns, fill_value=0.0)
        
        # Portfolio returns
        portfolio_returns = (returns_data * aligned_weights).sum(axis=1)
        
        # Basic metrics
        expected_return = portfolio_returns.mean() * 252  # Annualized
        volatility = portfolio_returns.std() * np.sqrt(252)  # Annualized
        
        # Risk-adjusted metrics
        sharpe_ratio = (expected_return - self.risk_free_rate) / volatility if volatility > 0 else 0.0
        
        # Downside metrics
        downside_returns = portfolio_returns[portfolio_returns < 0]
        downside_deviation = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0.0
        sortino_ratio = (expected_return - self.risk_free_rate) / downside_deviation if downside_deviation > 0 else 0.0
        
        # Maximum drawdown
        cumulative_returns = (1 + portfolio_returns).cumprod()
        rolling_max = cumulative_returns.expanding().max()
        drawdowns = (cumulative_returns - rolling_max) / rolling_max
        max_drawdown = abs(drawdowns.min())
        
        # Calmar ratio
        calmar_ratio = expected_return / max_drawdown if max_drawdown > 0 else 0.0
        
        # VaR and CVaR
        var_95 = np.percentile(portfolio_returns, 5)
        var_99 = np.percentile(portfolio_returns, 1)
        cvar_95 = portfolio_returns[portfolio_returns <= var_95].mean()
        cvar_99 = portfolio_returns[portfolio_returns <= var_99].mean()
        
        # Beta and alpha (if benchmark available)
        beta, alpha = 0.0, 0.0
        information_ratio, tracking_error = 0.0, 0.0
        
        if self.benchmark_data is not None:
            benchmark_returns = self.benchmark_data.pct_change().dropna()
            
            # Align dates
            common_dates = portfolio_returns.index.intersection(benchmark_returns.index)
            if len(common_dates) > 1:
                port_aligned = portfolio_returns.loc[common_dates]
                bench_aligned = benchmark_returns.loc[common_dates]
                
                # Beta calculation
                covariance = np.cov(port_aligned, bench_aligned)[0, 1]
                benchmark_variance = np.var(bench_aligned)
                beta = covariance / benchmark_variance if benchmark_variance > 0 else 0.0
                
                # Alpha calculation
                benchmark_return = bench_aligned.mean() * 252
                alpha = expected_return - (self.risk_free_rate + beta * (benchmark_return - self.risk_free_rate))
                
                # Information ratio and tracking error
                excess_returns = port_aligned - bench_aligned
                tracking_error = excess_returns.std() * np.sqrt(252)
                information_ratio = excess_returns.mean() * 252 / tracking_error if tracking_error > 0 else 0.0
        
        # Treynor ratio
        treynor_ratio = (expected_return - self.risk_free_rate) / beta if beta > 0 else 0.0
        
        return PortfolioMetrics(
            expected_return=expected_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            max_drawdown=max_drawdown,
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            cvar_99=cvar_99,
            beta=beta,
            alpha=alpha,
            information_ratio=information_ratio,
            tracking_error=tracking_error,
            treynor_ratio=treynor_ratio
        )
    
    def performance_attribution(self, 
                              portfolio_weights: pd.Series,
                              benchmark_weights: pd.Series,
                              returns_data: pd.DataFrame,
                              sector_mapping: Optional[Dict[str, str]] = None) -> AttributionAnalysis:
        """
        Perform comprehensive performance attribution analysis
        
        Args:
            portfolio_weights: Portfolio weights
            benchmark_weights: Benchmark weights
            returns_data: Historical returns data
            sector_mapping: Mapping of assets to sectors
            
        Returns:
            AttributionAnalysis object with detailed attribution
        """
        # Align weights with returns
        assets = returns_data.columns
        port_weights = portfolio_weights.reindex(assets, fill_value=0.0)
        bench_weights = benchmark_weights.reindex(assets, fill_value=0.0)
        
        # Calculate returns
        portfolio_return = (returns_data * port_weights).sum(axis=1).mean() * 252
        benchmark_return = (returns_data * bench_weights).sum(axis=1).mean() * 252
        total_return = portfolio_return - benchmark_return
        
        # Asset allocation effect (Brinson attribution)
        asset_returns = returns_data.mean() * 252
        weight_diff = port_weights - bench_weights
        
        asset_allocation_effect = {}
        security_selection_effect = {}
        interaction_effect = {}
        
        for asset in assets:
            # Asset allocation effect: (wp - wb) * rb
            aa_effect = weight_diff[asset] * asset_returns[asset]
            asset_allocation_effect[asset] = aa_effect
            
            # Security selection effect: wb * (rp - rb)
            # For individual assets, this is typically 0 unless we have active views
            ss_effect = bench_weights[asset] * (asset_returns[asset] - asset_returns[asset])
            security_selection_effect[asset] = ss_effect
            
            # Interaction effect: (wp - wb) * (rp - rb)
            int_effect = weight_diff[asset] * (asset_returns[asset] - asset_returns[asset])
            interaction_effect[asset] = int_effect
        
        # Sector attribution (if sector mapping provided)
        sector_attribution = {}
        if sector_mapping:
            sectors = set(sector_mapping.values())
            for sector in sectors:
                sector_assets = [asset for asset, sec in sector_mapping.items() if sec == sector]
                sector_port_weight = sum(port_weights[asset] for asset in sector_assets if asset in port_weights.index)
                sector_bench_weight = sum(bench_weights[asset] for asset in sector_assets if asset in bench_weights.index)
                sector_return = sum(asset_returns[asset] * port_weights[asset] for asset in sector_assets if asset in asset_returns.index)
                
                sector_attribution[sector] = {
                    'allocation_effect': (sector_port_weight - sector_bench_weight) * sector_return,
                    'selection_effect': 0.0,  # Simplified for now
                    'total_effect': (sector_port_weight - sector_bench_weight) * sector_return
                }
        
        # Factor attribution (simplified - would need factor model for full implementation)
        factor_attribution = {
            'market_factor': total_return * 0.8,  # Simplified assumption
            'size_factor': total_return * 0.1,
            'value_factor': total_return * 0.05,
            'momentum_factor': total_return * 0.05
        }
        
        return AttributionAnalysis(
            total_return=total_return,
            asset_allocation_effect=asset_allocation_effect,
            security_selection_effect=security_selection_effect,
            interaction_effect=interaction_effect,
            sector_attribution=sector_attribution,
            factor_attribution=factor_attribution
        )
    
    def _basic_optimization(self, 
                          returns_data: pd.DataFrame, 
                          config: OptimizationConfig) -> Dict[str, Union[pd.Series, Dict]]:
        """
        Basic optimization fallback when advanced libraries are not available
        
        Args:
            returns_data: Historical returns data
            config: Optimization configuration
            
        Returns:
            Dictionary with optimization results
        """
        n_assets = len(returns_data.columns)
        
        if config.method == OptimizationMethod.MINIMUM_VARIANCE:
            # Equal weight as simple fallback
            weights = pd.Series(1.0/n_assets, index=returns_data.columns)
        elif config.method == OptimizationMethod.RISK_PARITY:
            # Inverse volatility weighting
            volatilities = returns_data.std()
            inv_vol = 1.0 / volatilities
            weights = inv_vol / inv_vol.sum()
        else:
            # Default to equal weight
            weights = pd.Series(1.0/n_assets, index=returns_data.columns)
        
        return {
            'weights': weights,
            'method': config.method.value,
            'optimization_status': 'completed_basic',
            'message': 'Used basic optimization due to missing advanced libraries'
        }