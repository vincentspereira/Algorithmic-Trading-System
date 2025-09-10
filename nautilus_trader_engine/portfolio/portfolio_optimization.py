"""
Portfolio Optimization System
Advanced portfolio optimization with multiple risk measures, 
constraints, and integration with Nautilus Trader portfolio system.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

# Import PyPortfolioOpt and Riskfolio-Lib
try:
    from pypfopt import EfficientFrontier, risk_models, expected_returns
    from pypfopt.discrete_allocation import DiscreteAllocation
    from pypfopt.black_litterman import BlackLittermanModel
    from pypfopt.hierarchical_portfolio import HRPOpt
    PYPFOPT_AVAILABLE = True
except ImportError:
    PYPFOPT_AVAILABLE = False
    logging.warning("PyPortfolioOpt not available, some optimization features will be limited")

try:
    import riskfolio as rp
    RISKFOLIO_AVAILABLE = True
except ImportError:
    RISKFOLIO_AVAILABLE = False
    logging.warning("Riskfolio-Lib not available, some advanced optimization features will be limited")

# Nautilus Trader imports
from nautilus_trader.portfolio.portfolio import Portfolio
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.objects import Money
from nautilus_trader.cache.cache import Cache
from nautilus_trader.common.component import Logger


class OptimizationMethod(Enum):
    """Portfolio optimization methods"""
    MEAN_VARIANCE = "mean_variance"
    BLACK_LITTERMAN = "black_litterman"
    HIERARCHICAL_RISK_PARITY = "hrp"
    RISK_PARITY = "risk_parity"
    MINIMUM_VARIANCE = "min_variance"
    MAXIMUM_SHARPE = "max_sharpe"
    MAXIMUM_UTILITY = "max_utility"
    MAXIMUM_RETURN = "max_return"
    CVAR = "cvar"
    SEMIVARIANCE = "semivariance"


class RiskMeasure(Enum):
    """Risk measures for portfolio optimization"""
    STANDARD_DEVIATION = "std"
    VARIANCE = "var"
    SEMI_DEVIATION = "semi_dev"
    CVAR = "cvar"
    MAD = "mad"  # Mean Absolute Deviation
    GMD = "gmd"  # Gini Mean Difference
    MAX_DRAWDOWN = "max_drawdown"
    AVERAGE_DRAWDOWN = "avg_drawdown"
    CDAR = "cdar"  # Conditional Drawdown at Risk
    VALUE_AT_RISK = "var"


@dataclass
class PortfolioOptimizationConfig:
    """Configuration for portfolio optimization"""
    method: OptimizationMethod = OptimizationMethod.MEAN_VARIANCE
    risk_measure: RiskMeasure = RiskMeasure.STANDARD_DEVIATION
    target_return: Optional[float] = None
    target_risk: Optional[float] = None
    risk_free_rate: float = 0.02
    risk_aversion: float = 1.0
    allow_short: bool = False
    max_short_weight: float = 0.3
    max_long_weight: float = 1.0
    min_positions: Optional[int] = None
    max_positions: Optional[int] = None
    transaction_cost: float = 0.001
    l2_regularization: float = 0.0
    use_black_litterman: bool = False
    use_hierarchical: bool = False
    confidence_level: float = 0.95
    rebalance_frequency: str = "daily"  # daily, weekly, monthly
    optimization_window: int = 252  # trading days
    use_robust_estimates: bool = False
    shrinkage: Optional[float] = None
    market_neutral: bool = False
    constraints: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizationResult:
    """Result of portfolio optimization"""
    weights: Dict[str, float]
    expected_return: float
    risk: float
    sharpe_ratio: float
    risk_contribution: Optional[Dict[str, float]] = None
    turnover: Optional[float] = None
    transaction_cost: Optional[float] = None
    effective_assets: Optional[float] = None
    diversification_ratio: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    method: str = ""
    risk_measure: str = ""


class PortfolioOptimizer:
    """Advanced portfolio optimizer with multiple methods and risk measures"""
    
    def __init__(self, config: PortfolioOptimizationConfig = None):
        self.config = config or PortfolioOptimizationConfig()
        self.logger = Logger(name=type(self).__name__)
        self._previous_weights = {}
        self._optimization_history = []
        
    def optimize_portfolio(self, 
                          returns_data: pd.DataFrame,
                          market_caps: Optional[pd.Series] = None,
                          views: Optional[Dict[str, float]] = None,
                          confidence: Optional[pd.DataFrame] = None) -> OptimizationResult:
        """
        Optimize portfolio using the configured method and parameters.
        
        Parameters
        ----------
        returns_data : pd.DataFrame
            Historical returns data for assets (columns are assets, rows are dates)
        market_caps : pd.Series, optional
            Market capitalization for assets (for market-cap weighted priors)
        views : Dict[str, float], optional
            Investor views for Black-Litterman model
        confidence : pd.DataFrame, optional
            Confidence matrix for Black-Litterman views
            
        Returns
        -------
        OptimizationResult
            The optimized portfolio weights and performance metrics
        """
        try:
            if self.config.use_hierarchical and PYPFOPT_AVAILABLE:
                return self._optimize_hierarchical(returns_data)
            elif self.config.use_black_litterman and PYPFOPT_AVAILABLE:
                return self._optimize_black_litterman(returns_data, market_caps, views, confidence)
            elif PYPFOPT_AVAILABLE:
                return self._optimize_pypfopt(returns_data)
            elif RISKFOLIO_AVAILABLE:
                return self._optimize_riskfolio(returns_data)
            else:
                raise RuntimeError("No portfolio optimization library available")
                
        except Exception as e:
            self.logger.error(f"Portfolio optimization failed: {e}")
            raise
            
    def _optimize_pypfopt(self, returns_data: pd.DataFrame) -> OptimizationResult:
        """Optimize using PyPortfolioOpt library"""
        if not PYPFOPT_AVAILABLE:
            raise RuntimeError("PyPortfolioOpt not available")
            
        # Calculate expected returns and covariance matrix
        mu = expected_returns.mean_historical_return(returns_data)
        S = risk_models.sample_cov(returns_data)
        
        # Apply shrinkage if specified
        if self.config.shrinkage is not None:
            S = risk_models.CovarianceShrinkage(returns_data).shrunk_covariance(
                method='ledoit-wolf', delta=self.config.shrinkage
            )
        
        # Set weight bounds
        if self.config.allow_short:
            weight_bounds = (-self.config.max_short_weight, self.config.max_long_weight)
        else:
            weight_bounds = (0, self.config.max_long_weight)
            
        # Initialize optimizer
        ef = EfficientFrontier(mu, S, weight_bounds=weight_bounds)
        
        # Add L2 regularization if specified
        if self.config.l2_regularization > 0:
            try:
                from pypfopt import objective_functions
                ef.add_objective(objective_functions.L2_reg, gamma=self.config.l2_regularization)
            except ImportError:
                self.logger.warning("Could not add L2 regularization")
        
        # Apply market neutrality if specified
        if self.config.market_neutral and self.config.allow_short:
            ef.add_constraint(lambda w: np.sum(w) == 0)
            
        # Apply position limits if specified
        if self.config.max_positions:
            # This is a simplified approach - in practice, integer programming would be needed
            pass
            
        # Optimize based on method
        weights = None
        if self.config.method == OptimizationMethod.MINIMUM_VARIANCE:
            weights = ef.min_volatility()
        elif self.config.method == OptimizationMethod.MAXIMUM_RETURN:
            if self.config.target_risk:
                weights = ef.efficient_risk(self.config.target_risk)
            else:
                weights = ef.max_quadratic_utility(risk_aversion=self.config.risk_aversion)
        elif self.config.method == OptimizationMethod.MAXIMUM_SHARPE:
            weights = ef.max_sharpe(risk_free_rate=self.config.risk_free_rate)
        elif self.config.method == OptimizationMethod.MEAN_VARIANCE:
            if self.config.target_return:
                weights = ef.efficient_return(self.config.target_return)
            elif self.config.target_risk:
                weights = ef.efficient_risk(self.config.target_risk)
            else:
                weights = ef.max_sharpe(risk_free_rate=self.config.risk_free_rate)
        else:
            # Default to maximum Sharpe ratio
            weights = ef.max_sharpe(risk_free_rate=self.config.risk_free_rate)
            
        # Clean weights
        cleaned_weights = ef.clean_weights()
        weights_dict = dict(cleaned_weights)
        
        # Calculate performance metrics
        perf = ef.portfolio_performance(verbose=False)
        expected_return = perf[0]
        risk = perf[1]
        sharpe_ratio = perf[2]
        
        # Calculate risk contribution if available
        risk_contribution = None
        try:
            rc = ef.risk_contribution()
            risk_contribution = dict(zip(returns_data.columns, rc))
        except:
            pass
            
        # Calculate turnover from previous weights
        turnover = self._calculate_turnover(weights_dict)
        self._previous_weights = weights_dict.copy()
        
        # Calculate transaction costs
        transaction_cost = turnover * self.config.transaction_cost if turnover else 0
        
        # Calculate diversification metrics
        effective_assets = self._calculate_effective_assets(weights_dict)
        diversification_ratio = self._calculate_diversification_ratio(weights_dict, risk, S)
        
        result = OptimizationResult(
            weights=weights_dict,
            expected_return=expected_return,
            risk=risk,
            sharpe_ratio=sharpe_ratio,
            risk_contribution=risk_contribution,
            turnover=turnover,
            transaction_cost=transaction_cost,
            effective_assets=effective_assets,
            diversification_ratio=diversification_ratio,
            method=self.config.method.value,
            risk_measure=self.config.risk_measure.value
        )
        
        self._optimization_history.append(result)
        return result
        
    def _optimize_black_litterman(self, returns_data: pd.DataFrame,
                                 market_caps: pd.Series,
                                 views: Dict[str, float],
                                 confidence: pd.DataFrame) -> OptimizationResult:
        """Optimize using Black-Litterman model"""
        if not PYPFOPT_AVAILABLE:
            raise RuntimeError("PyPortfolioOpt not available")
            
        # Calculate market-implied returns
        S = risk_models.sample_cov(returns_data)
        delta = 2.5  # Risk aversion parameter
        market_prior = implied_market_returns.implied_market_returns(
            delta, self.config.risk_free_rate, S, market_caps
        )
        
        # Create Black-Litterman model
        if views:
            bl = BlackLittermanModel(
                S, 
                pi=market_prior, 
                absolute_views=views,
                omega=confidence if confidence is not None else "default"
            )
            rets = bl.bl_returns()
        else:
            rets = market_prior
            
        # Optimize portfolio with Black-Litterman returns
        ef = EfficientFrontier(rets, S)
        weights = ef.max_sharpe(risk_free_rate=self.config.risk_free_rate)
        cleaned_weights = ef.clean_weights()
        weights_dict = dict(cleaned_weights)
        
        # Calculate performance metrics
        perf = ef.portfolio_performance(verbose=False)
        expected_return = perf[0]
        risk = perf[1]
        sharpe_ratio = perf[2]
        
        result = OptimizationResult(
            weights=weights_dict,
            expected_return=expected_return,
            risk=risk,
            sharpe_ratio=sharpe_ratio,
            method="black_litterman",
            risk_measure=self.config.risk_measure.value
        )
        
        self._optimization_history.append(result)
        return result
        
    def _optimize_hierarchical(self, returns_data: pd.DataFrame) -> OptimizationResult:
        """Optimize using Hierarchical Risk Parity"""
        if not PYPFOPT_AVAILABLE:
            raise RuntimeError("PyPortfolioOpt not available")
            
        hrp = HRPOpt(returns_data)
        weights_dict = hrp.optimize(linkage_method='single')
        
        # Calculate performance metrics
        perf = hrp.portfolio_performance(verbose=False)
        expected_return = perf[0]
        risk = perf[1]
        sharpe_ratio = perf[2]
        
        result = OptimizationResult(
            weights=weights_dict,
            expected_return=expected_return,
            risk=risk,
            sharpe_ratio=sharpe_ratio,
            method="hierarchical_risk_parity",
            risk_measure=self.config.risk_measure.value
        )
        
        self._optimization_history.append(result)
        return result
        
    def _optimize_riskfolio(self, returns_data: pd.DataFrame) -> OptimizationResult:
        """Optimize using Riskfolio-Lib"""
        if not RISKFOLIO_AVAILABLE:
            raise RuntimeError("Riskfolio-Lib not available")
            
        # Create portfolio object
        port = rp.HCPortfolio(returns_data)
        
        # Set optimization parameters
        model = "Classic"  # Classic, BL, FM, BLFM
        rm = self.config.risk_measure.value  # Risk measure
        obj = "Sharpe"    # Objective function
        hist = True       # Use historical scenarios
        rf = self.config.risk_free_rate  # Risk free rate
        l = self.config.risk_aversion   # Risk aversion factor
        
        # Optimize
        weights_dict = port.optimization(
            model=model, 
            rm=rm, 
            obj=obj, 
            rf=rf, 
            l=l, 
            method_mu='hist' if hist else 'classic', 
            method_cov='hist' if hist else 'classic'
        )
        weights_dict = weights_dict.to_dict()['weights']
        
        # Calculate portfolio performance
        if rm == "MV":
            risk = np.sqrt(np.dot(list(weights_dict.values()), np.dot(returns_data.cov(), list(weights_dict.values()))))
        else:
            # For other risk measures, we'll use a simplified approach
            risk = np.std(np.dot(returns_data, list(weights_dict.values()))) * np.sqrt(252)
            
        expected_return = np.dot(list(weights_dict.values()), returns_data.mean()) * 252  # Annualized
        sharpe_ratio = (expected_return - rf) / risk if risk > 0 else 0
        
        result = OptimizationResult(
            weights=weights_dict,
            expected_return=expected_return,
            risk=risk,
            sharpe_ratio=sharpe_ratio,
            method=self.config.method.value,
            risk_measure=rm
        )
        
        self._optimization_history.append(result)
        return result
        
    def _calculate_turnover(self, new_weights: Dict[str, float]) -> float:
        """Calculate portfolio turnover from previous weights"""
        if not self._previous_weights:
            return 0.0
            
        turnover = 0.0
        all_assets = set(new_weights.keys()) | set(self._previous_weights.keys())
        
        for asset in all_assets:
            new_w = new_weights.get(asset, 0.0)
            old_w = self._previous_weights.get(asset, 0.0)
            turnover += abs(new_w - old_w)
            
        return turnover / 2.0  # Divide by 2 as we count both buys and sells
        
    def _calculate_effective_assets(self, weights: Dict[str, float]) -> float:
        """Calculate effective number of assets (inverse of Herfindahl index)"""
        sum_sq_weights = sum(w * w for w in weights.values())
        if sum_sq_weights > 0:
            return 1.0 / sum_sq_weights
        return float(len(weights))
        
    def _calculate_diversification_ratio(self, weights: Dict[str, float], 
                                       portfolio_risk: float, 
                                       cov_matrix: pd.DataFrame) -> float:
        """Calculate diversification ratio"""
        if portfolio_risk <= 0:
            return 0.0
            
        weighted_asset_risks = 0.0
        for asset, weight in weights.items():
            if asset in cov_matrix.columns:
                asset_risk = np.sqrt(cov_matrix.loc[asset, asset])
                weighted_asset_risks += abs(weight) * asset_risk
                
        if weighted_asset_risks > 0:
            return weighted_asset_risks / portfolio_risk
        return 0.0
        
    def get_optimization_history(self) -> List[OptimizationResult]:
        """Get history of all optimizations performed"""
        return self._optimization_history.copy()
        
    def generate_discrete_allocation(self, 
                                   weights: Dict[str, float],
                                   latest_prices: pd.Series,
                                   total_portfolio_value: float = 100000.0) -> Dict[str, int]:
        """
        Convert continuous weights to discrete share allocations.
        
        Parameters
        ----------
        weights : Dict[str, float]
            Continuous portfolio weights
        latest_prices : pd.Series
            Latest prices for each asset
        total_portfolio_value : float
            Total value of the portfolio
            
        Returns
        -------
        Dict[str, int]
            Discrete share allocations
        """
        if not PYPFOPT_AVAILABLE:
            raise RuntimeError("PyPortfolioOpt not available for discrete allocation")
            
        da = DiscreteAllocation(weights, latest_prices, total_portfolio_value=total_portfolio_value)
        allocation, leftover = da.lp_portfolio()
        return allocation


class NautilusPortfolioOptimizer:
    """Integration between portfolio optimization and Nautilus Trader portfolio system"""
    
    def __init__(self, portfolio: Portfolio, cache: Cache, config: PortfolioOptimizationConfig = None):
        self.portfolio = portfolio
        self.cache = cache
        self.config = config or PortfolioOptimizationConfig()
        self.optimizer = PortfolioOptimizer(self.config)
        self.logger = Logger(name=type(self).__name__)
        
    def optimize_current_portfolio(self, 
                                 historical_data: pd.DataFrame,
                                 market_caps: Optional[pd.Series] = None,
                                 views: Optional[Dict[str, float]] = None,
                                 confidence: Optional[pd.DataFrame] = None) -> OptimizationResult:
        """
        Optimize the current portfolio based on historical data and market conditions.
        
        Parameters
        ----------
        historical_data : pd.DataFrame
            Historical price or return data for assets in the portfolio
        market_caps : pd.Series, optional
            Market capitalization data for Black-Litterman model
        views : Dict[str, float], optional
            Investor views for Black-Litterman model
        confidence : pd.DataFrame, optional
            Confidence matrix for views
            
        Returns
        -------
        OptimizationResult
            The optimized portfolio weights and performance metrics
        """
        try:
            # Optimize portfolio
            result = self.optimizer.optimize_portfolio(
                returns_data=historical_data,
                market_caps=market_caps,
                views=views,
                confidence=confidence
            )
            
            self.logger.info(f"Portfolio optimization completed: {result.method}")
            self.logger.info(f"Expected return: {result.expected_return:.2%}")
            self.logger.info(f"Risk: {result.risk:.2%}")
            self.logger.info(f"Sharpe ratio: {result.sharpe_ratio:.2f}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to optimize portfolio: {e}")
            raise
            
    def get_current_portfolio_metrics(self) -> Dict[str, Any]:
        """
        Get current portfolio metrics from Nautilus Trader portfolio system.
        
        Returns
        -------
        Dict[str, Any]
            Current portfolio metrics
        """
        try:
            metrics = {}
            
            # Get portfolio positions and values
            # This would need to be implemented based on the actual Nautilus Trader API
            # For now, we'll return a placeholder
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to get portfolio metrics: {e}")
            return {}
            
    def generate_rebalancing_signals(self, 
                                   optimization_result: OptimizationResult,
                                   threshold: float = 0.05) -> List[Dict[str, Any]]:
        """
        Generate rebalancing signals based on optimization results.
        
        Parameters
        ----------
        optimization_result : OptimizationResult
            The optimized portfolio weights
        threshold : float
            Minimum weight change to trigger rebalancing
            
        Returns
        -------
        List[Dict[str, Any]]
            List of rebalancing signals
        """
        signals = []
        current_weights = self.get_current_portfolio_metrics().get('weights', {})
        
        for asset, target_weight in optimization_result.weights.items():
            current_weight = current_weights.get(asset, 0.0)
            weight_diff = abs(target_weight - current_weight)
            
            if weight_diff > threshold:
                signals.append({
                    'asset': asset,
                    'current_weight': current_weight,
                    'target_weight': target_weight,
                    'weight_difference': weight_diff,
                    'action': 'BUY' if target_weight > current_weight else 'SELL',
                    'timestamp': datetime.now()
                })
                
        return signals


# Example usage and testing
def example_usage():
    """Example usage of the portfolio optimization system"""
    import numpy as np
    import pandas as pd
    from datetime import datetime, timedelta
    
    # Create sample data
    dates = pd.date_range(start='2020-01-01', end='2023-12-31', freq='D')
    assets = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
    
    # Generate random returns
    np.random.seed(42)
    returns_data = pd.DataFrame(
        np.random.randn(len(dates), len(assets)) * 0.02,
        index=dates,
        columns=assets
    )
    
    # Add some correlation
    returns_data['GOOGL'] = returns_data['AAPL'] * 0.7 + np.random.randn(len(dates)) * 0.01
    returns_data['MSFT'] = returns_data['AAPL'] * 0.5 + np.random.randn(len(dates)) * 0.015
    
    # Create optimizer
    config = PortfolioOptimizationConfig(
        method=OptimizationMethod.MAXIMUM_SHARPE,
        risk_free_rate=0.02,
        allow_short=False,
        l2_regularization=0.1
    )
    
    optimizer = PortfolioOptimizer(config)
    
    # Optimize portfolio
    print("Optimizing portfolio...")
    result = optimizer.optimize_portfolio(returns_data)
    
    print(f"Optimization Method: {result.method}")
    print(f"Expected Return: {result.expected_return:.2%}")
    print(f"Risk: {result.risk:.2%}")
    print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
    print("\nOptimal Weights:")
    for asset, weight in result.weights.items():
        print(f"  {asset}: {weight:.2%}")
        
    # Generate discrete allocation
    latest_prices = pd.Series({
        'AAPL': 150.0,
        'GOOGL': 2500.0,
        'MSFT': 300.0,
        'AMZN': 3200.0,
        'TSLA': 250.0
    })
    
    try:
        allocation = optimizer.generate_discrete_allocation(
            result.weights, 
            latest_prices, 
            total_portfolio_value=100000.0
        )
        print("\nDiscrete Allocation ($100,000 portfolio):")
        for asset, shares in allocation.items():
            value = shares * latest_prices[asset]
            print(f"  {asset}: {shares} shares (${value:,.2f})")
    except Exception as e:
        print(f"Could not generate discrete allocation: {e}")


if __name__ == "__main__":
    example_usage()