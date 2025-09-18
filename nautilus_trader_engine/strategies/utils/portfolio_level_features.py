#!/usr/bin/env python3
"""
Portfolio-Level Features for Pairs Trading

This module implements advanced portfolio-level features including:
- Multi-pair Optimization: Portfolio-level risk and return optimization
- Sector Diversification: Balanced exposure management
- Currency Hedging: International pairs currency risk management
- Leverage Optimization: Dynamic leverage based on market conditions

Author: Algorithmic Trading System
Version: 1.0.0
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Portfolio optimization libraries
try:
    import cvxpy as cp
    from scipy.optimize import minimize, differential_evolution
    from scipy import linalg
    OPTIMIZATION_AVAILABLE = True
except ImportError:
    OPTIMIZATION_AVAILABLE = False
    logging.warning("Portfolio optimization libraries not available")

# Risk management libraries
try:
    from sklearn.covariance import LedoitWolf, OAS
    from sklearn.decomposition import PCA
    RISK_LIBRARIES_AVAILABLE = True
except ImportError:
    RISK_LIBRARIES_AVAILABLE = False
    logging.warning("Risk management libraries not available")

# Currency and FX libraries
try:
    import yfinance as yf
    FX_DATA_AVAILABLE = True
except ImportError:
    FX_DATA_AVAILABLE = False
    logging.warning("FX data libraries not available")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OptimizationObjective(Enum):
    """Portfolio optimization objectives"""
    MAX_SHARPE = "max_sharpe"
    MIN_VARIANCE = "min_variance"
    MAX_RETURN = "max_return"
    RISK_PARITY = "risk_parity"
    MAX_DIVERSIFICATION = "max_diversification"
    BLACK_LITTERMAN = "black_litterman"

class SectorClassification(Enum):
    """Sector classifications"""
    TECHNOLOGY = "technology"
    FINANCIALS = "financials"
    HEALTHCARE = "healthcare"
    CONSUMER_DISCRETIONARY = "consumer_discretionary"
    CONSUMER_STAPLES = "consumer_staples"
    INDUSTRIALS = "industrials"
    ENERGY = "energy"
    UTILITIES = "utilities"
    MATERIALS = "materials"
    REAL_ESTATE = "real_estate"
    TELECOMMUNICATIONS = "telecommunications"

class CurrencyCode(Enum):
    """Major currency codes"""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CHF = "CHF"
    CAD = "CAD"
    AUD = "AUD"
    NZD = "NZD"
    CNY = "CNY"
    HKD = "HKD"

class LeverageStrategy(Enum):
    """Leverage strategies"""
    FIXED = "fixed"
    VOLATILITY_TARGETING = "volatility_targeting"
    KELLY_CRITERION = "kelly_criterion"
    RISK_BUDGETING = "risk_budgeting"
    ADAPTIVE = "adaptive"

@dataclass
class PairInfo:
    """Information about a trading pair"""
    symbol1: str
    symbol2: str
    sector1: SectorClassification
    sector2: SectorClassification
    currency1: CurrencyCode
    currency2: CurrencyCode
    correlation: float
    volatility: float
    expected_return: float
    beta: float = 1.0
    market_cap1: float = 0.0
    market_cap2: float = 0.0

@dataclass
class PortfolioConstraints:
    """Portfolio optimization constraints"""
    max_weight_per_pair: float = 0.2
    max_sector_exposure: float = 0.4
    max_currency_exposure: float = 0.6
    min_diversification_ratio: float = 0.5
    max_leverage: float = 2.0
    min_liquidity: float = 1000000.0  # Minimum daily volume
    max_correlation: float = 0.8
    target_volatility: float = 0.15
    max_drawdown: float = 0.1

@dataclass
class RiskMetrics:
    """Portfolio risk metrics"""
    portfolio_volatility: float
    var_95: float
    cvar_95: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    diversification_ratio: float
    concentration_risk: float
    sector_concentration: Dict[str, float]
    currency_exposure: Dict[str, float]

class MultiPairOptimizer:
    """Multi-pair portfolio optimization engine"""
    
    def __init__(self, pairs: List[PairInfo], constraints: PortfolioConstraints):
        self.pairs = pairs
        self.constraints = constraints
        self.n_pairs = len(pairs)
        self.returns_data = None
        self.covariance_matrix = None
        self.expected_returns = None
        
    def set_historical_data(self, returns_data: pd.DataFrame):
        """Set historical returns data for optimization"""
        self.returns_data = returns_data
        self.expected_returns = returns_data.mean().values
        
        # Robust covariance estimation
        if RISK_LIBRARIES_AVAILABLE:
            # Use Ledoit-Wolf shrinkage estimator
            lw = LedoitWolf()
            self.covariance_matrix = lw.fit(returns_data).covariance_
        else:
            self.covariance_matrix = returns_data.cov().values
    
    def optimize_portfolio(self, objective: OptimizationObjective = OptimizationObjective.MAX_SHARPE) -> Dict[str, Any]:
        """Optimize portfolio allocation"""
        
        if self.returns_data is None:
            raise ValueError("Historical data must be set before optimization")
        
        if not OPTIMIZATION_AVAILABLE:
            logger.warning("Optimization libraries not available. Using equal weights.")
            return self._equal_weight_fallback()
        
        if objective == OptimizationObjective.MAX_SHARPE:
            return self._maximize_sharpe_ratio()
        elif objective == OptimizationObjective.MIN_VARIANCE:
            return self._minimize_variance()
        elif objective == OptimizationObjective.RISK_PARITY:
            return self._risk_parity_optimization()
        elif objective == OptimizationObjective.MAX_DIVERSIFICATION:
            return self._maximize_diversification()
        elif objective == OptimizationObjective.BLACK_LITTERMAN:
            return self._black_litterman_optimization()
        else:
            return self._maximize_sharpe_ratio()
    
    def _maximize_sharpe_ratio(self) -> Dict[str, Any]:
        """Maximize Sharpe ratio optimization"""
        try:
            # Define optimization variables
            w = cp.Variable(self.n_pairs)
            
            # Objective: maximize Sharpe ratio (equivalent to maximizing return/risk)
            portfolio_return = self.expected_returns @ w
            portfolio_variance = cp.quad_form(w, self.covariance_matrix)
            
            # Constraints
            constraints = [
                cp.sum(w) == 1,  # Weights sum to 1
                w >= 0,  # Long-only (can be modified for long-short)
                w <= self.constraints.max_weight_per_pair  # Maximum weight per pair
            ]
            
            # Add sector constraints
            sector_constraints = self._build_sector_constraints(w)
            constraints.extend(sector_constraints)
            
            # Add currency constraints
            currency_constraints = self._build_currency_constraints(w)
            constraints.extend(currency_constraints)
            
            # Solve optimization (maximize return for given risk)
            target_return = cp.Parameter(value=np.mean(self.expected_returns))
            constraints.append(portfolio_return >= target_return)
            
            objective = cp.Minimize(portfolio_variance)
            problem = cp.Problem(objective, constraints)
            
            # Solve for different target returns to find efficient frontier
            returns_range = np.linspace(
                np.min(self.expected_returns),
                np.max(self.expected_returns),
                20
            )
            
            efficient_portfolios = []
            for target_ret in returns_range:
                target_return.value = target_ret
                try:
                    problem.solve(solver=cp.ECOS)
                    if problem.status == cp.OPTIMAL:
                        portfolio_vol = np.sqrt(portfolio_variance.value)
                        sharpe = target_ret / portfolio_vol if portfolio_vol > 0 else 0
                        efficient_portfolios.append({
                            'return': target_ret,
                            'volatility': portfolio_vol,
                            'sharpe': sharpe,
                            'weights': w.value.copy()
                        })
                except:
                    continue
            
            # Select portfolio with maximum Sharpe ratio
            if efficient_portfolios:
                best_portfolio = max(efficient_portfolios, key=lambda x: x['sharpe'])
                optimal_weights = best_portfolio['weights']
            else:
                # Fallback to minimum variance
                return self._minimize_variance()
            
            return {
                'weights': optimal_weights,
                'expected_return': best_portfolio['return'],
                'volatility': best_portfolio['volatility'],
                'sharpe_ratio': best_portfolio['sharpe'],
                'optimization_status': 'success',
                'efficient_frontier': efficient_portfolios
            }
            
        except Exception as e:
            logger.error(f"Sharpe ratio optimization failed: {e}")
            return self._equal_weight_fallback()
    
    def _minimize_variance(self) -> Dict[str, Any]:
        """Minimum variance optimization"""
        try:
            w = cp.Variable(self.n_pairs)
            
            # Objective: minimize portfolio variance
            portfolio_variance = cp.quad_form(w, self.covariance_matrix)
            
            # Constraints
            constraints = [
                cp.sum(w) == 1,
                w >= 0,
                w <= self.constraints.max_weight_per_pair
            ]
            
            # Add sector and currency constraints
            constraints.extend(self._build_sector_constraints(w))
            constraints.extend(self._build_currency_constraints(w))
            
            # Solve
            objective = cp.Minimize(portfolio_variance)
            problem = cp.Problem(objective, constraints)
            problem.solve(solver=cp.ECOS)
            
            if problem.status == cp.OPTIMAL:
                optimal_weights = w.value
                portfolio_return = self.expected_returns @ optimal_weights
                portfolio_vol = np.sqrt(portfolio_variance.value)
                sharpe = portfolio_return / portfolio_vol if portfolio_vol > 0 else 0
                
                return {
                    'weights': optimal_weights,
                    'expected_return': portfolio_return,
                    'volatility': portfolio_vol,
                    'sharpe_ratio': sharpe,
                    'optimization_status': 'success'
                }
            else:
                return self._equal_weight_fallback()
                
        except Exception as e:
            logger.error(f"Minimum variance optimization failed: {e}")
            return self._equal_weight_fallback()
    
    def _risk_parity_optimization(self) -> Dict[str, Any]:
        """Risk parity optimization"""
        try:
            def risk_parity_objective(weights):
                """Risk parity objective function"""
                portfolio_vol = np.sqrt(weights @ self.covariance_matrix @ weights)
                marginal_contrib = self.covariance_matrix @ weights / portfolio_vol
                contrib = weights * marginal_contrib
                target_contrib = portfolio_vol / self.n_pairs
                return np.sum((contrib - target_contrib) ** 2)
            
            # Constraints
            constraints = [
                {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},  # Weights sum to 1
            ]
            
            bounds = [(0, self.constraints.max_weight_per_pair) for _ in range(self.n_pairs)]
            
            # Initial guess
            x0 = np.ones(self.n_pairs) / self.n_pairs
            
            # Optimize
            result = minimize(
                risk_parity_objective,
                x0,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints
            )
            
            if result.success:
                optimal_weights = result.x
                portfolio_return = self.expected_returns @ optimal_weights
                portfolio_vol = np.sqrt(optimal_weights @ self.covariance_matrix @ optimal_weights)
                sharpe = portfolio_return / portfolio_vol if portfolio_vol > 0 else 0
                
                return {
                    'weights': optimal_weights,
                    'expected_return': portfolio_return,
                    'volatility': portfolio_vol,
                    'sharpe_ratio': sharpe,
                    'optimization_status': 'success'
                }
            else:
                return self._equal_weight_fallback()
                
        except Exception as e:
            logger.error(f"Risk parity optimization failed: {e}")
            return self._equal_weight_fallback()
    
    def _maximize_diversification(self) -> Dict[str, Any]:
        """Maximize diversification ratio"""
        try:
            def diversification_ratio(weights):
                """Calculate diversification ratio"""
                individual_vols = np.sqrt(np.diag(self.covariance_matrix))
                weighted_avg_vol = weights @ individual_vols
                portfolio_vol = np.sqrt(weights @ self.covariance_matrix @ weights)
                return -(weighted_avg_vol / portfolio_vol)  # Negative for maximization
            
            constraints = [
                {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},
            ]
            
            bounds = [(0, self.constraints.max_weight_per_pair) for _ in range(self.n_pairs)]
            x0 = np.ones(self.n_pairs) / self.n_pairs
            
            result = minimize(
                diversification_ratio,
                x0,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints
            )
            
            if result.success:
                optimal_weights = result.x
                portfolio_return = self.expected_returns @ optimal_weights
                portfolio_vol = np.sqrt(optimal_weights @ self.covariance_matrix @ optimal_weights)
                sharpe = portfolio_return / portfolio_vol if portfolio_vol > 0 else 0
                
                return {
                    'weights': optimal_weights,
                    'expected_return': portfolio_return,
                    'volatility': portfolio_vol,
                    'sharpe_ratio': sharpe,
                    'diversification_ratio': -result.fun,
                    'optimization_status': 'success'
                }
            else:
                return self._equal_weight_fallback()
                
        except Exception as e:
            logger.error(f"Diversification optimization failed: {e}")
            return self._equal_weight_fallback()
    
    def _black_litterman_optimization(self) -> Dict[str, Any]:
        """Black-Litterman optimization"""
        try:
            # Market capitalization weights as prior
            market_caps = np.array([pair.market_cap1 + pair.market_cap2 for pair in self.pairs])
            if np.sum(market_caps) > 0:
                market_weights = market_caps / np.sum(market_caps)
            else:
                market_weights = np.ones(self.n_pairs) / self.n_pairs
            
            # Risk aversion parameter
            risk_aversion = 3.0
            
            # Implied equilibrium returns
            pi = risk_aversion * self.covariance_matrix @ market_weights
            
            # Uncertainty in prior (tau)
            tau = 1.0 / len(self.returns_data)
            
            # Views and confidence (simplified - no views for now)
            # In practice, you would incorporate analyst views here
            P = np.eye(self.n_pairs)  # Identity matrix (views on all assets)
            Q = self.expected_returns  # View returns (using historical as proxy)
            omega = tau * np.diag(np.diag(self.covariance_matrix))  # View uncertainty
            
            # Black-Litterman formula
            M1 = linalg.inv(tau * self.covariance_matrix)
            M2 = P.T @ linalg.inv(omega) @ P
            M3 = linalg.inv(tau * self.covariance_matrix) @ pi
            M4 = P.T @ linalg.inv(omega) @ Q
            
            # New expected returns
            mu_bl = linalg.inv(M1 + M2) @ (M3 + M4)
            
            # New covariance matrix
            cov_bl = linalg.inv(M1 + M2)
            
            # Optimize with Black-Litterman inputs
            w = cp.Variable(self.n_pairs)
            portfolio_return = mu_bl @ w
            portfolio_variance = cp.quad_form(w, cov_bl)
            
            constraints = [
                cp.sum(w) == 1,
                w >= 0,
                w <= self.constraints.max_weight_per_pair
            ]
            
            # Maximize utility (return - risk penalty)
            utility = portfolio_return - 0.5 * risk_aversion * portfolio_variance
            objective = cp.Maximize(utility)
            
            problem = cp.Problem(objective, constraints)
            problem.solve(solver=cp.ECOS)
            
            if problem.status == cp.OPTIMAL:
                optimal_weights = w.value
                portfolio_return_val = mu_bl @ optimal_weights
                portfolio_vol = np.sqrt(optimal_weights @ cov_bl @ optimal_weights)
                sharpe = portfolio_return_val / portfolio_vol if portfolio_vol > 0 else 0
                
                return {
                    'weights': optimal_weights,
                    'expected_return': portfolio_return_val,
                    'volatility': portfolio_vol,
                    'sharpe_ratio': sharpe,
                    'bl_returns': mu_bl,
                    'bl_covariance': cov_bl,
                    'optimization_status': 'success'
                }
            else:
                return self._equal_weight_fallback()
                
        except Exception as e:
            logger.error(f"Black-Litterman optimization failed: {e}")
            return self._equal_weight_fallback()
    
    def _build_sector_constraints(self, w) -> List:
        """Build sector exposure constraints"""
        constraints = []
        
        # Group pairs by sector combinations
        sector_groups = {}
        for i, pair in enumerate(self.pairs):
            sector_key = f"{pair.sector1.value}_{pair.sector2.value}"
            if sector_key not in sector_groups:
                sector_groups[sector_key] = []
            sector_groups[sector_key].append(i)
        
        # Add constraints for each sector group
        for sector_key, indices in sector_groups.items():
            if len(indices) > 1:  # Only add constraint if multiple pairs in sector
                sector_weight = cp.sum([w[i] for i in indices])
                constraints.append(sector_weight <= self.constraints.max_sector_exposure)
        
        return constraints
    
    def _build_currency_constraints(self, w) -> List:
        """Build currency exposure constraints"""
        constraints = []
        
        # Group pairs by currency
        currency_groups = {}
        for i, pair in enumerate(self.pairs):
            for currency in [pair.currency1, pair.currency2]:
                if currency not in currency_groups:
                    currency_groups[currency] = []
                currency_groups[currency].append(i)
        
        # Add constraints for each currency
        for currency, indices in currency_groups.items():
            if len(indices) > 1:
                currency_weight = cp.sum([w[i] for i in indices])
                constraints.append(currency_weight <= self.constraints.max_currency_exposure)
        
        return constraints
    
    def _equal_weight_fallback(self) -> Dict[str, Any]:
        """Fallback to equal weights"""
        weights = np.ones(self.n_pairs) / self.n_pairs
        portfolio_return = self.expected_returns @ weights
        portfolio_vol = np.sqrt(weights @ self.covariance_matrix @ weights)
        sharpe = portfolio_return / portfolio_vol if portfolio_vol > 0 else 0
        
        return {
            'weights': weights,
            'expected_return': portfolio_return,
            'volatility': portfolio_vol,
            'sharpe_ratio': sharpe,
            'optimization_status': 'fallback_equal_weight'
        }

class SectorDiversificationManager:
    """Manage sector diversification and exposure"""
    
    def __init__(self, pairs: List[PairInfo]):
        self.pairs = pairs
        self.sector_mapping = self._build_sector_mapping()
    
    def _build_sector_mapping(self) -> Dict[str, List[int]]:
        """Build mapping of sectors to pair indices"""
        mapping = {}
        
        for i, pair in enumerate(self.pairs):
            # Add to both sectors
            for sector in [pair.sector1, pair.sector2]:
                sector_name = sector.value
                if sector_name not in mapping:
                    mapping[sector_name] = []
                mapping[sector_name].append(i)
        
        return mapping
    
    def calculate_sector_exposure(self, weights: np.ndarray) -> Dict[str, float]:
        """Calculate current sector exposure"""
        exposure = {}
        
        for sector, indices in self.sector_mapping.items():
            sector_weight = sum(weights[i] for i in indices)
            exposure[sector] = sector_weight
        
        return exposure
    
    def get_diversification_score(self, weights: np.ndarray) -> float:
        """Calculate diversification score (0-1, higher is better)"""
        sector_exposures = self.calculate_sector_exposure(weights)
        
        # Calculate Herfindahl-Hirschman Index (HHI)
        hhi = sum(exposure ** 2 for exposure in sector_exposures.values())
        
        # Convert to diversification score (1 - normalized HHI)
        max_hhi = 1.0  # Maximum HHI when all weight in one sector
        min_hhi = 1.0 / len(sector_exposures)  # Minimum HHI with equal distribution
        
        if max_hhi > min_hhi:
            diversification_score = 1 - (hhi - min_hhi) / (max_hhi - min_hhi)
        else:
            diversification_score = 1.0
        
        return max(0, min(1, diversification_score))
    
    def suggest_rebalancing(self, current_weights: np.ndarray, target_diversification: float = 0.8) -> Dict[str, Any]:
        """Suggest rebalancing to improve diversification"""
        current_score = self.get_diversification_score(current_weights)
        
        if current_score >= target_diversification:
            return {
                'rebalancing_needed': False,
                'current_score': current_score,
                'message': 'Portfolio is sufficiently diversified'
            }
        
        # Identify overweight sectors
        sector_exposures = self.calculate_sector_exposure(current_weights)
        avg_exposure = 1.0 / len(sector_exposures)
        overweight_sectors = {k: v for k, v in sector_exposures.items() if v > avg_exposure * 1.5}
        
        # Suggest reducing overweight positions
        suggestions = []
        for sector, exposure in overweight_sectors.items():
            reduction_needed = exposure - avg_exposure
            suggestions.append({
                'sector': sector,
                'current_exposure': exposure,
                'target_exposure': avg_exposure,
                'reduction_needed': reduction_needed,
                'affected_pairs': [self.pairs[i].symbol1 + '-' + self.pairs[i].symbol2 
                                 for i in self.sector_mapping[sector]]
            })
        
        return {
            'rebalancing_needed': True,
            'current_score': current_score,
            'target_score': target_diversification,
            'overweight_sectors': overweight_sectors,
            'suggestions': suggestions
        }

class CurrencyHedgingManager:
    """Manage currency hedging for international pairs"""
    
    def __init__(self, base_currency: CurrencyCode = CurrencyCode.USD):
        self.base_currency = base_currency
        self.fx_rates = {}
        self.fx_volatilities = {}
        self.hedge_ratios = {}
    
    def update_fx_rates(self, fx_data: Dict[str, float]):
        """Update current FX rates"""
        self.fx_rates.update(fx_data)
    
    def calculate_currency_exposure(self, pairs: List[PairInfo], weights: np.ndarray) -> Dict[str, float]:
        """Calculate portfolio currency exposure"""
        exposure = {currency.value: 0.0 for currency in CurrencyCode}
        
        for i, (pair, weight) in enumerate(zip(pairs, weights)):
            # Assume equal exposure to both currencies in the pair
            exposure[pair.currency1.value] += weight * 0.5
            exposure[pair.currency2.value] += weight * 0.5
        
        # Remove zero exposures
        return {k: v for k, v in exposure.items() if v > 0.001}
    
    def calculate_optimal_hedge_ratios(self, pairs: List[PairInfo], weights: np.ndarray, 
                                     target_fx_exposure: float = 0.1) -> Dict[str, float]:
        """Calculate optimal currency hedge ratios"""
        currency_exposure = self.calculate_currency_exposure(pairs, weights)
        hedge_ratios = {}
        
        for currency, exposure in currency_exposure.items():
            if currency != self.base_currency.value and exposure > target_fx_exposure:
                # Calculate hedge ratio based on exposure and volatility
                fx_vol = self.fx_volatilities.get(f"{currency}{self.base_currency.value}", 0.1)
                
                # Simple hedge ratio: reduce exposure to target level
                excess_exposure = exposure - target_fx_exposure
                hedge_ratio = min(1.0, excess_exposure / exposure)
                
                # Adjust for volatility (higher vol = higher hedge ratio)
                vol_adjustment = min(1.5, fx_vol / 0.1)  # Normalize to 10% vol
                hedge_ratio *= vol_adjustment
                
                hedge_ratios[currency] = min(1.0, hedge_ratio)
        
        return hedge_ratios
    
    def estimate_hedging_cost(self, hedge_ratios: Dict[str, float], 
                            notional_amounts: Dict[str, float]) -> Dict[str, float]:
        """Estimate cost of currency hedging"""
        hedging_costs = {}
        
        for currency, hedge_ratio in hedge_ratios.items():
            notional = notional_amounts.get(currency, 0)
            
            # Estimate hedging cost (bid-ask spread + roll cost)
            # Typical FX forward spread: 0.1-0.5 bps for majors, 1-5 bps for minors
            if currency in ['EUR', 'GBP', 'JPY', 'CHF']:
                spread_cost = 0.0002  # 2 bps
            else:
                spread_cost = 0.0010  # 10 bps
            
            # Roll cost (interest rate differential)
            roll_cost = 0.0005  # 5 bps (simplified)
            
            total_cost = (spread_cost + roll_cost) * hedge_ratio * notional
            hedging_costs[currency] = total_cost
        
        return hedging_costs
    
    def get_fx_data(self, currency_pairs: List[str]) -> Dict[str, Dict[str, float]]:
        """Fetch FX data (rates and volatilities)"""
        fx_data = {}
        
        if not FX_DATA_AVAILABLE:
            # Return mock data
            for pair in currency_pairs:
                fx_data[pair] = {
                    'rate': 1.0 + np.random.normal(0, 0.1),
                    'volatility': 0.1 + np.random.uniform(0, 0.05)
                }
            return fx_data
        
        try:
            for pair in currency_pairs:
                # Format for yfinance (e.g., EURUSD=X)
                yf_symbol = f"{pair}=X"
                
                # Fetch data
                ticker = yf.Ticker(yf_symbol)
                hist = ticker.history(period="1y")
                
                if not hist.empty:
                    current_rate = hist['Close'].iloc[-1]
                    returns = hist['Close'].pct_change().dropna()
                    volatility = returns.std() * np.sqrt(252)  # Annualized
                    
                    fx_data[pair] = {
                        'rate': current_rate,
                        'volatility': volatility
                    }
                else:
                    # Fallback to mock data
                    fx_data[pair] = {
                        'rate': 1.0,
                        'volatility': 0.1
                    }
        
        except Exception as e:
            logger.error(f"Failed to fetch FX data: {e}")
            # Return mock data
            for pair in currency_pairs:
                fx_data[pair] = {
                    'rate': 1.0 + np.random.normal(0, 0.1),
                    'volatility': 0.1 + np.random.uniform(0, 0.05)
                }
        
        return fx_data

class LeverageOptimizer:
    """Dynamic leverage optimization based on market conditions"""
    
    def __init__(self, strategy: LeverageStrategy = LeverageStrategy.VOLATILITY_TARGETING):
        self.strategy = strategy
        self.target_volatility = 0.15  # 15% target volatility
        self.max_leverage = 3.0
        self.min_leverage = 0.5
        self.lookback_period = 252  # 1 year
    
    def calculate_optimal_leverage(self, returns_data: pd.DataFrame, 
                                 current_volatility: float) -> Dict[str, float]:
        """Calculate optimal leverage based on strategy"""
        
        if self.strategy == LeverageStrategy.VOLATILITY_TARGETING:
            return self._volatility_targeting_leverage(current_volatility)
        elif self.strategy == LeverageStrategy.KELLY_CRITERION:
            return self._kelly_criterion_leverage(returns_data)
        elif self.strategy == LeverageStrategy.RISK_BUDGETING:
            return self._risk_budgeting_leverage(returns_data)
        elif self.strategy == LeverageStrategy.ADAPTIVE:
            return self._adaptive_leverage(returns_data, current_volatility)
        else:
            return {'leverage': 1.0, 'confidence': 0.5}
    
    def _volatility_targeting_leverage(self, current_volatility: float) -> Dict[str, float]:
        """Volatility targeting leverage"""
        if current_volatility <= 0:
            return {'leverage': 1.0, 'confidence': 0.0}
        
        # Target leverage = target_vol / current_vol
        target_leverage = self.target_volatility / current_volatility
        
        # Apply bounds
        leverage = np.clip(target_leverage, self.min_leverage, self.max_leverage)
        
        # Confidence based on volatility stability
        vol_stability = min(1.0, self.target_volatility / max(current_volatility, 0.01))
        confidence = vol_stability * 0.8  # Max 80% confidence
        
        return {
            'leverage': leverage,
            'confidence': confidence,
            'target_volatility': self.target_volatility,
            'current_volatility': current_volatility
        }
    
    def _kelly_criterion_leverage(self, returns_data: pd.DataFrame) -> Dict[str, float]:
        """Kelly criterion leverage calculation"""
        if returns_data.empty:
            return {'leverage': 1.0, 'confidence': 0.0}
        
        # Calculate Kelly fraction for each asset
        kelly_fractions = []
        
        for column in returns_data.columns:
            returns = returns_data[column].dropna()
            
            if len(returns) < 30:  # Need sufficient data
                kelly_fractions.append(0.1)
                continue
            
            # Kelly formula: f = (bp - q) / b
            # where b = odds, p = win probability, q = loss probability
            
            # Estimate win probability and average win/loss
            wins = returns[returns > 0]
            losses = returns[returns < 0]
            
            if len(wins) == 0 or len(losses) == 0:
                kelly_fractions.append(0.1)
                continue
            
            win_prob = len(wins) / len(returns)
            loss_prob = 1 - win_prob
            avg_win = wins.mean()
            avg_loss = abs(losses.mean())
            
            if avg_loss == 0:
                kelly_fractions.append(0.1)
                continue
            
            # Kelly fraction
            kelly_f = (win_prob * avg_win - loss_prob * avg_loss) / avg_win
            kelly_f = max(0, min(0.25, kelly_f))  # Cap at 25%
            
            kelly_fractions.append(kelly_f)
        
        # Portfolio Kelly fraction (simplified as average)
        portfolio_kelly = np.mean(kelly_fractions)
        
        # Convert to leverage (Kelly fraction is optimal allocation)
        leverage = portfolio_kelly * 4  # Scale up (Kelly is conservative)
        leverage = np.clip(leverage, self.min_leverage, self.max_leverage)
        
        # Confidence based on data quality
        confidence = min(0.8, len(returns_data) / 252)  # More data = higher confidence
        
        return {
            'leverage': leverage,
            'confidence': confidence,
            'kelly_fraction': portfolio_kelly,
            'individual_kelly': kelly_fractions
        }
    
    def _risk_budgeting_leverage(self, returns_data: pd.DataFrame) -> Dict[str, float]:
        """Risk budgeting approach to leverage"""
        if returns_data.empty:
            return {'leverage': 1.0, 'confidence': 0.0}
        
        # Calculate portfolio volatility
        portfolio_returns = returns_data.mean(axis=1)  # Equal weight portfolio
        portfolio_vol = portfolio_returns.std() * np.sqrt(252)
        
        if portfolio_vol <= 0:
            return {'leverage': 1.0, 'confidence': 0.0}
        
        # Risk budget approach: allocate risk budget across time
        # Higher recent volatility = lower leverage
        recent_vol = portfolio_returns.tail(63).std() * np.sqrt(252)  # Last quarter
        vol_ratio = recent_vol / portfolio_vol
        
        # Base leverage on risk budget
        base_leverage = self.target_volatility / portfolio_vol
        
        # Adjust for recent volatility regime
        if vol_ratio > 1.2:  # High volatility regime
            leverage_adjustment = 0.8
        elif vol_ratio < 0.8:  # Low volatility regime
            leverage_adjustment = 1.2
        else:
            leverage_adjustment = 1.0
        
        leverage = base_leverage * leverage_adjustment
        leverage = np.clip(leverage, self.min_leverage, self.max_leverage)
        
        confidence = min(0.8, 1.0 / vol_ratio)  # Lower confidence in high vol regimes
        
        return {
            'leverage': leverage,
            'confidence': confidence,
            'portfolio_volatility': portfolio_vol,
            'recent_volatility': recent_vol,
            'volatility_ratio': vol_ratio
        }
    
    def _adaptive_leverage(self, returns_data: pd.DataFrame, current_volatility: float) -> Dict[str, float]:
        """Adaptive leverage combining multiple approaches"""
        # Get leverage from different methods
        vol_targeting = self._volatility_targeting_leverage(current_volatility)
        kelly_result = self._kelly_criterion_leverage(returns_data)
        risk_budgeting = self._risk_budgeting_leverage(returns_data)
        
        # Weighted combination based on confidence
        leverages = [vol_targeting['leverage'], kelly_result['leverage'], risk_budgeting['leverage']]
        confidences = [vol_targeting['confidence'], kelly_result['confidence'], risk_budgeting['confidence']]
        
        # Weighted average
        total_confidence = sum(confidences)
        if total_confidence > 0:
            weights = [c / total_confidence for c in confidences]
            combined_leverage = sum(l * w for l, w in zip(leverages, weights))
        else:
            combined_leverage = np.mean(leverages)
        
        # Final bounds check
        final_leverage = np.clip(combined_leverage, self.min_leverage, self.max_leverage)
        
        return {
            'leverage': final_leverage,
            'confidence': np.mean(confidences),
            'component_leverages': {
                'volatility_targeting': vol_targeting['leverage'],
                'kelly_criterion': kelly_result['leverage'],
                'risk_budgeting': risk_budgeting['leverage']
            },
            'component_confidences': {
                'volatility_targeting': vol_targeting['confidence'],
                'kelly_criterion': kelly_result['confidence'],
                'risk_budgeting': risk_budgeting['confidence']
            }
        }
    
    def calculate_leverage_metrics(self, returns_data: pd.DataFrame, leverage: float) -> Dict[str, float]:
        """Calculate leverage-related risk metrics"""
        if returns_data.empty:
            return {}
        
        # Leveraged returns
        leveraged_returns = returns_data.mean(axis=1) * leverage
        
        # Risk metrics
        volatility = leveraged_returns.std() * np.sqrt(252)
        sharpe_ratio = leveraged_returns.mean() / leveraged_returns.std() * np.sqrt(252)
        
        # Drawdown calculation
        cumulative = (1 + leveraged_returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # VaR calculation
        var_95 = np.percentile(leveraged_returns, 5)
        var_99 = np.percentile(leveraged_returns, 1)
        
        return {
            'leveraged_volatility': volatility,
            'leveraged_sharpe': sharpe_ratio,
            'max_drawdown': abs(max_drawdown),
            'var_95': var_95,
            'var_99': var_99,
            'leverage_ratio': leverage
        }

# Example usage and testing
def test_portfolio_level_features():
    """Test the portfolio-level features"""
    print("Testing Portfolio-Level Features")
    print("=" * 50)
    
    # Create sample pairs
    sample_pairs = [
        PairInfo(
            symbol1="AAPL", symbol2="MSFT",
            sector1=SectorClassification.TECHNOLOGY, sector2=SectorClassification.TECHNOLOGY,
            currency1=CurrencyCode.USD, currency2=CurrencyCode.USD,
            correlation=0.75, volatility=0.25, expected_return=0.12,
            market_cap1=2500000000000, market_cap2=2000000000000
        ),
        PairInfo(
            symbol1="JPM", symbol2="BAC",
            sector1=SectorClassification.FINANCIALS, sector2=SectorClassification.FINANCIALS,
            currency1=CurrencyCode.USD, currency2=CurrencyCode.USD,
            correlation=0.80, volatility=0.30, expected_return=0.10,
            market_cap1=400000000000, market_cap2=300000000000
        ),
        PairInfo(
            symbol1="JNJ", symbol2="PFE",
            sector1=SectorClassification.HEALTHCARE, sector2=SectorClassification.HEALTHCARE,
            currency1=CurrencyCode.USD, currency2=CurrencyCode.USD,
            correlation=0.65, volatility=0.20, expected_return=0.08,
            market_cap1=450000000000, market_cap2=250000000000
        )
    ]
    
    # Generate sample returns data
    np.random.seed(42)
    n_days = 252
    returns_data = pd.DataFrame({
        'AAPL-MSFT': np.random.normal(0.12/252, 0.25/np.sqrt(252), n_days),
        'JPM-BAC': np.random.normal(0.10/252, 0.30/np.sqrt(252), n_days),
        'JNJ-PFE': np.random.normal(0.08/252, 0.20/np.sqrt(252), n_days)
    })
    
    # 1. Test Multi-Pair Optimizer
    print("\n1. Testing Multi-Pair Optimizer:")
    constraints = PortfolioConstraints(
        max_weight_per_pair=0.4,
        max_sector_exposure=0.6,
        target_volatility=0.15
    )
    
    optimizer = MultiPairOptimizer(sample_pairs, constraints)
    optimizer.set_historical_data(returns_data)
    
    # Test different optimization objectives
    objectives = [OptimizationObjective.MAX_SHARPE, OptimizationObjective.MIN_VARIANCE, 
                 OptimizationObjective.RISK_PARITY]
    
    for objective in objectives:
        result = optimizer.optimize_portfolio(objective)
        print(f"\n{objective.value.upper()} Optimization:")
        print(f"  Status: {result['optimization_status']}")
        print(f"  Expected Return: {result['expected_return']:.4f}")
        print(f"  Volatility: {result['volatility']:.4f}")
        print(f"  Sharpe Ratio: {result['sharpe_ratio']:.4f}")
        print(f"  Weights: {[f'{w:.3f}' for w in result['weights']]}")
    
    # 2. Test Sector Diversification Manager
    print("\n2. Testing Sector Diversification Manager:")
    sector_manager = SectorDiversificationManager(sample_pairs)
    
    # Test with concentrated weights
    concentrated_weights = np.array([0.7, 0.2, 0.1])
    sector_exposure = sector_manager.calculate_sector_exposure(concentrated_weights)
    diversification_score = sector_manager.get_diversification_score(concentrated_weights)
    
    print(f"Sector Exposure: {sector_exposure}")
    print(f"Diversification Score: {diversification_score:.3f}")
    
    rebalancing_suggestion = sector_manager.suggest_rebalancing(concentrated_weights)
    print(f"Rebalancing Needed: {rebalancing_suggestion['rebalancing_needed']}")
    if rebalancing_suggestion['rebalancing_needed']:
        print(f"Suggestions: {len(rebalancing_suggestion['suggestions'])} sector adjustments")
    
    # 3. Test Currency Hedging Manager
    print("\n3. Testing Currency Hedging Manager:")
    hedging_manager = CurrencyHedgingManager(CurrencyCode.USD)
    
    # Add some international pairs
    international_pairs = sample_pairs + [
        PairInfo(
            symbol1="ASML", symbol2="SAP",
            sector1=SectorClassification.TECHNOLOGY, sector2=SectorClassification.TECHNOLOGY,
            currency1=CurrencyCode.EUR, currency2=CurrencyCode.EUR,
            correlation=0.60, volatility=0.35, expected_return=0.15
        )
    ]
    
    weights_with_fx = np.array([0.3, 0.3, 0.2, 0.2])
    currency_exposure = hedging_manager.calculate_currency_exposure(international_pairs, weights_with_fx)
    print(f"Currency Exposure: {currency_exposure}")
    
    hedge_ratios = hedging_manager.calculate_optimal_hedge_ratios(international_pairs, weights_with_fx)
    print(f"Optimal Hedge Ratios: {hedge_ratios}")
    
    # 4. Test Leverage Optimizer
    print("\n4. Testing Leverage Optimizer:")
    
    strategies = [LeverageStrategy.VOLATILITY_TARGETING, LeverageStrategy.KELLY_CRITERION, 
                 LeverageStrategy.ADAPTIVE]
    
    for strategy in strategies:
        leverage_optimizer = LeverageOptimizer(strategy)
        current_vol = returns_data.std().mean() * np.sqrt(252)
        
        leverage_result = leverage_optimizer.calculate_optimal_leverage(returns_data, current_vol)
        print(f"\n{strategy.value.upper()} Strategy:")
        print(f"  Optimal Leverage: {leverage_result['leverage']:.2f}")
        print(f"  Confidence: {leverage_result['confidence']:.3f}")
        
        # Calculate leverage metrics
        leverage_metrics = leverage_optimizer.calculate_leverage_metrics(
            returns_data, leverage_result['leverage']
        )
        if leverage_metrics:
            print(f"  Leveraged Volatility: {leverage_metrics['leveraged_volatility']:.3f}")
            print(f"  Leveraged Sharpe: {leverage_metrics['leveraged_sharpe']:.3f}")
            print(f"  Max Drawdown: {leverage_metrics['max_drawdown']:.3f}")
    
    print("\nPortfolio-Level Features testing completed!")

if __name__ == "__main__":
    test_portfolio_level_features()