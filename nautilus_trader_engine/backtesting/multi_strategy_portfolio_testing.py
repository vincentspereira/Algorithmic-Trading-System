"""
Multi-Strategy Portfolio Testing Framework

This module provides comprehensive multi-strategy portfolio testing capabilities.
"""

import logging
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import statistics

# Try to import optional dependencies
try:
    import scipy.stats as stats
    import scipy.optimize as optimize
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


class AllocationMethod(Enum):
    """Portfolio allocation methods"""
    EQUAL_WEIGHT = "equal_weight"
    RISK_PARITY = "risk_parity"
    MEAN_VARIANCE = "mean_variance"
    MINIMUM_VARIANCE = "minimum_variance"
    MAXIMUM_DIVERSIFICATION = "maximum_diversification"
    RISK_BUDGETING = "risk_budgeting"


class RebalancingFrequency(Enum):
    """Portfolio rebalancing frequencies"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"


@dataclass
class Strategy:
    """Individual strategy definition"""
    name: str
    returns: pd.Series
    description: str = ""
    strategy_type: str = "generic"
    target_allocation: Optional[float] = None
    min_allocation: float = 0.0
    max_allocation: float = 1.0
    risk_budget: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PortfolioConstraints:
    """Portfolio construction constraints"""
    min_weight: float = 0.0
    max_weight: float = 1.0
    max_concentration: float = 0.5
    min_strategies: int = 1
    max_strategies: Optional[int] = None


@dataclass
class AllocationResult:
    """Portfolio allocation result"""
    weights: Dict[str, float]
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    diversification_ratio: float
    allocation_method: AllocationMethod
    optimization_success: bool
    constraints_satisfied: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PortfolioPerformance:
    """Portfolio performance metrics"""
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    var_95: float
    cvar_95: float
    skewness: float
    kurtosis: float
    win_rate: float
    best_month: float
    worst_month: float
    up_months: int
    down_months: int
    recovery_factor: float
    ulcer_index: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CorrelationAnalysis:
    """Strategy correlation analysis"""
    correlation_matrix: pd.DataFrame
    average_correlation: float
    max_correlation: float
    min_correlation: float
    diversification_ratio: float
    effective_strategies: float
    correlation_clusters: List[List[str]]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskAttribution:
    """Portfolio risk attribution"""
    strategy_risk_contributions: Dict[str, float]
    strategy_risk_percentages: Dict[str, float]
    marginal_risk_contributions: Dict[str, float]
    component_var: Dict[str, float]
    diversification_benefit: float
    concentration_risk: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PortfolioTestResult:
    """Complete portfolio test result"""
    portfolio_name: str
    test_period: Tuple[datetime, datetime]
    strategies: List[Strategy]
    allocation_result: AllocationResult
    portfolio_performance: PortfolioPerformance
    correlation_analysis: CorrelationAnalysis
    risk_attribution: RiskAttribution
    rebalancing_history: List[Dict[str, Any]]
    transaction_costs: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class CorrelationAnalyzer:
    """Analyzes correlations between strategies"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def analyze_correlations(self, strategies: List[Strategy],
                           lookback_window: int = 252) -> CorrelationAnalysis:
        """Analyze correlations between strategies"""
        try:
            if not strategies:
                return self._empty_correlation_analysis()
            
            # Align strategy returns
            returns_data = {}
            for strategy in strategies:
                returns_data[strategy.name] = strategy.returns
            
            returns_df = pd.DataFrame(returns_data).dropna()
            
            if len(returns_df) < 10:
                return self._empty_correlation_analysis()
            
            # Check for any remaining NaN or Inf values
            if returns_df.isnull().any().any() or np.isinf(returns_df.values).any():
                self.logger.warning("Found NaN or Inf values in returns data")
                return self._empty_correlation_analysis()
            
            # Calculate correlation matrix
            correlation_matrix = returns_df.corr()
            
            # Check correlation matrix validity
            if correlation_matrix.isnull().any().any() or np.isinf(correlation_matrix.values).any():
                self.logger.warning("Correlation matrix contains NaN or Inf values")
                return self._empty_correlation_analysis()
            
            # Calculate correlation statistics
            if len(strategies) == 1:
                # For single strategy, correlation with itself is 1.0
                avg_correlation = 0.0  # No cross-correlations
                max_correlation = 0.0
                min_correlation = 0.0
            else:
                correlations = correlation_matrix.values
                np.fill_diagonal(correlations, np.nan)
                
                # Handle NaN values
                valid_correlations = correlations[~np.isnan(correlations)]
                if len(valid_correlations) > 0:
                    avg_correlation = np.mean(valid_correlations)
                    max_correlation = np.max(valid_correlations)
                    min_correlation = np.min(valid_correlations)
                else:
                    avg_correlation = 0.0
                    max_correlation = 0.0
                    min_correlation = 0.0
            
            # Calculate diversification ratio
            try:
                if len(strategies) == 1:
                    diversification_ratio = 1.0  # Single strategy has no diversification
                else:
                    weights = np.ones(len(strategies)) / len(strategies)
                    portfolio_vol = np.sqrt(weights.T @ correlation_matrix.values @ weights)
                    avg_vol = np.mean([strategy.returns.std() for strategy in strategies])
                    diversification_ratio = avg_vol / portfolio_vol if portfolio_vol > 0 else 1.0
                    
                    # Check for invalid values
                    if not np.isfinite(diversification_ratio):
                        diversification_ratio = 1.0
            except:
                diversification_ratio = 1.0
            
            # Calculate effective number of strategies
            try:
                eigenvalues = np.linalg.eigvals(correlation_matrix.values)
                eigenvalues = eigenvalues[eigenvalues > 1e-8]
                if len(eigenvalues) > 0:
                    effective_strategies = (np.sum(eigenvalues) ** 2) / np.sum(eigenvalues ** 2)
                else:
                    effective_strategies = len(strategies)
            except:
                effective_strategies = len(strategies)
            
            # Find correlation clusters
            correlation_clusters = self._find_correlation_clusters(correlation_matrix, threshold=0.7)
            
            return CorrelationAnalysis(
                correlation_matrix=correlation_matrix,
                average_correlation=avg_correlation,
                max_correlation=max_correlation,
                min_correlation=min_correlation,
                diversification_ratio=diversification_ratio,
                effective_strategies=effective_strategies,
                correlation_clusters=correlation_clusters
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing correlations: {e}")
            return self._empty_correlation_analysis()
    
    def _find_correlation_clusters(self, correlation_matrix: pd.DataFrame,
                                 threshold: float = 0.7) -> List[List[str]]:
        """Find clusters of highly correlated strategies"""
        try:
            clusters = []
            strategies = list(correlation_matrix.index)
            visited = set()
            
            for strategy in strategies:
                if strategy in visited:
                    continue
                
                cluster = [strategy]
                visited.add(strategy)
                
                for other_strategy in strategies:
                    if (other_strategy != strategy and 
                        other_strategy not in visited and
                        abs(correlation_matrix.loc[strategy, other_strategy]) >= threshold):
                        cluster.append(other_strategy)
                        visited.add(other_strategy)
                
                if len(cluster) > 1:
                    clusters.append(cluster)
            
            return clusters
            
        except Exception as e:
            self.logger.error(f"Error finding correlation clusters: {e}")
            return []
    
    def _empty_correlation_analysis(self) -> CorrelationAnalysis:
        """Return empty correlation analysis"""
        return CorrelationAnalysis(
            correlation_matrix=pd.DataFrame(),
            average_correlation=0.0,
            max_correlation=0.0,
            min_correlation=0.0,
            diversification_ratio=1.0,
            effective_strategies=0.0,
            correlation_clusters=[]
        )


class PortfolioOptimizer:
    """Optimizes portfolio allocations using various methods"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def optimize_portfolio(self, strategies: List[Strategy],
                         method: AllocationMethod = AllocationMethod.RISK_PARITY,
                         constraints: Optional[PortfolioConstraints] = None,
                         lookback_window: int = 252) -> AllocationResult:
        """Optimize portfolio allocation"""
        try:
            if not strategies:
                return self._empty_allocation_result(method)
            
            constraints = constraints or PortfolioConstraints()
            
            # Align strategy returns
            returns_data = {}
            for strategy in strategies:
                returns_data[strategy.name] = strategy.returns
            
            returns_df = pd.DataFrame(returns_data).dropna()
            
            if len(returns_df) < 10:
                return self._empty_allocation_result(method)
            
            # Calculate expected returns and covariance
            expected_returns = returns_df.mean() * 252  # Annualized
            cov_matrix = returns_df.cov() * 252  # Annualized
            
            # Apply optimization method
            if method == AllocationMethod.EQUAL_WEIGHT:
                weights = self._equal_weight_allocation(strategies)
            elif method == AllocationMethod.RISK_PARITY:
                weights = self._risk_parity_allocation(strategies, cov_matrix)
            elif method == AllocationMethod.MINIMUM_VARIANCE:
                weights = self._minimum_variance_allocation(cov_matrix, constraints)
            else:
                weights = self._equal_weight_allocation(strategies)
            
            # Calculate portfolio metrics
            portfolio_return = np.sum([weights[s.name] * expected_returns[s.name] for s in strategies])
            portfolio_variance = np.sum([
                np.sum([weights[s1.name] * weights[s2.name] * cov_matrix.loc[s1.name, s2.name]
                       for s2 in strategies])
                for s1 in strategies
            ])
            portfolio_volatility = np.sqrt(portfolio_variance)
            
            sharpe_ratio = portfolio_return / portfolio_volatility if portfolio_volatility > 0 else 0
            
            # Calculate diversification ratio
            weighted_vol = np.sum([weights[s.name] * np.sqrt(cov_matrix.loc[s.name, s.name]) for s in strategies])
            diversification_ratio = weighted_vol / portfolio_volatility if portfolio_volatility > 0 else 1.0
            
            # Check constraints
            constraints_satisfied = self._check_constraints(weights, constraints)
            
            return AllocationResult(
                weights=weights,
                expected_return=portfolio_return,
                expected_volatility=portfolio_volatility,
                sharpe_ratio=sharpe_ratio,
                diversification_ratio=diversification_ratio,
                allocation_method=method,
                optimization_success=True,
                constraints_satisfied=constraints_satisfied,
                metadata={
                    "lookback_window": lookback_window,
                    "num_strategies": len(strategies),
                    "optimization_date": datetime.now()
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error optimizing portfolio: {e}")
            return self._empty_allocation_result(method)
    
    def _equal_weight_allocation(self, strategies: List[Strategy]) -> Dict[str, float]:
        """Equal weight allocation"""
        weight = 1.0 / len(strategies)
        return {strategy.name: weight for strategy in strategies}
    
    def _risk_parity_allocation(self, strategies: List[Strategy], 
                              cov_matrix: pd.DataFrame) -> Dict[str, float]:
        """Risk parity allocation"""
        try:
            if not SCIPY_AVAILABLE:
                return self._equal_weight_allocation(strategies)
            
            n = len(strategies)
            strategy_names = [s.name for s in strategies]
            
            # Simple risk parity approximation
            volatilities = np.sqrt(np.diag(cov_matrix.values))
            inv_vol = 1.0 / volatilities
            weights = inv_vol / np.sum(inv_vol)
            
            return dict(zip(strategy_names, weights))
                
        except Exception as e:
            self.logger.error(f"Error in risk parity allocation: {e}")
            return self._equal_weight_allocation(strategies)
    
    def _minimum_variance_allocation(self, cov_matrix: pd.DataFrame,
                                   constraints: PortfolioConstraints) -> Dict[str, float]:
        """Minimum variance allocation"""
        try:
            if not SCIPY_AVAILABLE:
                n = len(cov_matrix)
                return {name: 1.0/n for name in cov_matrix.index}
            
            # Simple minimum variance approximation
            inv_cov = np.linalg.inv(cov_matrix.values)
            ones = np.ones((len(cov_matrix), 1))
            weights = inv_cov @ ones
            weights = weights / np.sum(weights)
            
            return dict(zip(cov_matrix.index, weights.flatten()))
                
        except Exception as e:
            self.logger.error(f"Error in minimum variance allocation: {e}")
            n = len(cov_matrix)
            return {name: 1.0/n for name in cov_matrix.index}
    
    def _check_constraints(self, weights: Dict[str, float],
                         constraints: PortfolioConstraints) -> bool:
        """Check if allocation satisfies constraints"""
        try:
            if not weights:
                return False
                
            # Check weight bounds
            for weight in weights.values():
                if weight < constraints.min_weight or weight > constraints.max_weight:
                    return False
            
            # Check concentration limit
            max_weight = max(weights.values())
            if max_weight > constraints.max_concentration:
                return False
            
            # Check number of strategies
            active_strategies = sum(1 for w in weights.values() if w > 0.001)
            if active_strategies < constraints.min_strategies:
                return False
            
            if constraints.max_strategies and active_strategies > constraints.max_strategies:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking constraints: {e}")
            return False
    
    def _empty_allocation_result(self, method: AllocationMethod) -> AllocationResult:
        """Return empty allocation result"""
        return AllocationResult(
            weights={},
            expected_return=0.0,
            expected_volatility=0.0,
            sharpe_ratio=0.0,
            diversification_ratio=1.0,
            allocation_method=method,
            optimization_success=False,
            constraints_satisfied=False
        )


class PerformanceCalculator:
    """Calculates portfolio performance metrics"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def calculate_portfolio_performance(self, portfolio_returns: pd.Series) -> PortfolioPerformance:
        """Calculate comprehensive portfolio performance metrics"""
        try:
            if len(portfolio_returns) == 0:
                return self._empty_performance()
            
            # Basic return metrics
            total_return = (1 + portfolio_returns).prod() - 1
            periods_per_year = 252  # Assume daily data
            annualized_return = (1 + total_return) ** (periods_per_year / len(portfolio_returns)) - 1
            
            # Risk metrics
            volatility = portfolio_returns.std() * np.sqrt(periods_per_year)
            
            # Sharpe ratio (assuming 2% risk-free rate)
            risk_free_rate = 0.02
            sharpe_ratio = (annualized_return - risk_free_rate) / volatility if volatility > 0 else 0
            
            # Drawdown analysis
            cumulative_returns = (1 + portfolio_returns).cumprod()
            rolling_max = cumulative_returns.expanding().max()
            drawdowns = (cumulative_returns - rolling_max) / rolling_max
            max_drawdown = drawdowns.min()
            
            # Sortino ratio
            downside_returns = portfolio_returns[portfolio_returns < 0]
            downside_std = downside_returns.std() * np.sqrt(periods_per_year) if len(downside_returns) > 0 else volatility
            sortino_ratio = (annualized_return - risk_free_rate) / downside_std if downside_std > 0 else 0
            
            # Calmar ratio
            calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
            
            # VaR and CVaR
            var_95 = portfolio_returns.quantile(0.05)
            cvar_95 = portfolio_returns[portfolio_returns <= var_95].mean() if len(portfolio_returns[portfolio_returns <= var_95]) > 0 else var_95
            
            # Higher moments
            skewness = portfolio_returns.skew() if len(portfolio_returns) > 2 else 0
            kurtosis = portfolio_returns.kurtosis() if len(portfolio_returns) > 3 else 0
            
            # Win/Loss metrics
            win_rate = (portfolio_returns > 0).mean()
            
            # Monthly analysis
            if hasattr(portfolio_returns.index, 'to_period'):
                monthly_returns = portfolio_returns.resample('ME').apply(lambda x: (1 + x).prod() - 1)
            else:
                # For non-datetime index, create dummy monthly returns
                monthly_returns = pd.Series([total_return / 12] * 12)
            best_month = monthly_returns.max() if len(monthly_returns) > 0 else 0
            worst_month = monthly_returns.min() if len(monthly_returns) > 0 else 0
            up_months = (monthly_returns > 0).sum()
            down_months = (monthly_returns < 0).sum()
            
            # Recovery factor
            recovery_factor = total_return / abs(max_drawdown) if max_drawdown != 0 else 0
            
            # Ulcer Index
            ulcer_index = np.sqrt((drawdowns ** 2).mean()) if len(drawdowns) > 0 else 0
            
            return PortfolioPerformance(
                total_return=total_return,
                annualized_return=annualized_return,
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                calmar_ratio=calmar_ratio,
                max_drawdown=max_drawdown,
                var_95=var_95,
                cvar_95=cvar_95,
                skewness=skewness,
                kurtosis=kurtosis,
                win_rate=win_rate,
                best_month=best_month,
                worst_month=worst_month,
                up_months=up_months,
                down_months=down_months,
                recovery_factor=recovery_factor,
                ulcer_index=ulcer_index
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating portfolio performance: {e}")
            return self._empty_performance()
    
    def _empty_performance(self) -> PortfolioPerformance:
        """Return empty performance metrics"""
        return PortfolioPerformance(
            total_return=0.0, annualized_return=0.0, volatility=0.0,
            sharpe_ratio=0.0, sortino_ratio=0.0, calmar_ratio=0.0,
            max_drawdown=0.0, var_95=0.0, cvar_95=0.0,
            skewness=0.0, kurtosis=0.0, win_rate=0.0,
            best_month=0.0, worst_month=0.0, up_months=0, down_months=0,
            recovery_factor=0.0, ulcer_index=0.0
        )


class RiskAttributor:
    """Attributes portfolio risk to individual strategies"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def calculate_risk_attribution(self, strategies: List[Strategy],
                                 weights: Dict[str, float],
                                 lookback_window: int = 252) -> RiskAttribution:
        """Calculate risk attribution for portfolio"""
        try:
            # Align strategy returns
            returns_data = {}
            for strategy in strategies:
                if strategy.name in weights and weights[strategy.name] > 0:
                    returns_data[strategy.name] = strategy.returns
            
            if not returns_data:
                return self._empty_risk_attribution()
            
            returns_df = pd.DataFrame(returns_data).dropna()
            
            if len(returns_df) < 10:
                return self._empty_risk_attribution()
            
            # Calculate covariance matrix
            cov_matrix = returns_df.cov() * 252  # Annualized
            
            # Get weights vector
            strategy_names = list(returns_df.columns)
            weight_vector = np.array([weights.get(name, 0.0) for name in strategy_names])
            
            # Portfolio variance
            portfolio_variance = weight_vector.T @ cov_matrix.values @ weight_vector
            portfolio_volatility = np.sqrt(portfolio_variance)
            
            # Marginal risk contributions
            marginal_contrib = cov_matrix.values @ weight_vector
            
            # Component risk contributions
            risk_contributions = weight_vector * marginal_contrib
            
            # Risk percentages
            risk_percentages = risk_contributions / portfolio_variance if portfolio_variance > 0 else np.zeros_like(risk_contributions)
            
            # Component VaR (simplified)
            component_var = {}
            for i, name in enumerate(strategy_names):
                strategy_var = returns_df[name].quantile(0.05)
                component_var[name] = weights[name] * strategy_var
            
            # Diversification benefit
            individual_risk = np.sum([weights[name] * np.sqrt(cov_matrix.loc[name, name]) for name in strategy_names])
            diversification_benefit = individual_risk - portfolio_volatility
            
            # Concentration risk (Herfindahl index)
            concentration_risk = np.sum([weights[name] ** 2 for name in strategy_names])
            
            # Create result dictionaries
            strategy_risk_contributions = dict(zip(strategy_names, risk_contributions))
            strategy_risk_percentages = dict(zip(strategy_names, risk_percentages))
            marginal_risk_contributions = dict(zip(strategy_names, marginal_contrib))
            
            return RiskAttribution(
                strategy_risk_contributions=strategy_risk_contributions,
                strategy_risk_percentages=strategy_risk_percentages,
                marginal_risk_contributions=marginal_risk_contributions,
                component_var=component_var,
                diversification_benefit=diversification_benefit,
                concentration_risk=concentration_risk
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating risk attribution: {e}")
            return self._empty_risk_attribution()
    
    def _empty_risk_attribution(self) -> RiskAttribution:
        """Return empty risk attribution"""
        return RiskAttribution(
            strategy_risk_contributions={},
            strategy_risk_percentages={},
            marginal_risk_contributions={},
            component_var={},
            diversification_benefit=0.0,
            concentration_risk=0.0
        )


class MultiStrategyPortfolioTester:
    """Main multi-strategy portfolio testing framework"""
    
    def __init__(self):
        self.correlation_analyzer = CorrelationAnalyzer()
        self.portfolio_optimizer = PortfolioOptimizer()
        self.performance_calculator = PerformanceCalculator()
        self.risk_attributor = RiskAttributor()
        self.logger = logging.getLogger(__name__)
    
    async def test_portfolio(self,
                           portfolio_name: str,
                           strategies: List[Strategy],
                           allocation_method: AllocationMethod = AllocationMethod.RISK_PARITY,
                           constraints: Optional[PortfolioConstraints] = None,
                           rebalancing_frequency: RebalancingFrequency = RebalancingFrequency.MONTHLY,
                           transaction_cost_bps: float = 5.0,
                           lookback_window: int = 252) -> PortfolioTestResult:
        """Test multi-strategy portfolio"""
        try:
            if not strategies:
                raise ValueError("No strategies provided")
            
            # Determine test period
            all_dates = set()
            for strategy in strategies:
                all_dates.update(strategy.returns.index)
            
            if not all_dates:
                raise ValueError("No return data available")
            
            start_date = min(all_dates)
            end_date = max(all_dates)
            
            # Analyze correlations
            correlation_analysis = self.correlation_analyzer.analyze_correlations(
                strategies, lookback_window
            )
            
            # Optimize portfolio allocation
            allocation_result = self.portfolio_optimizer.optimize_portfolio(
                strategies, allocation_method, constraints, lookback_window
            )
            
            if not allocation_result.optimization_success:
                self.logger.warning(f"Portfolio optimization failed for {portfolio_name}")
            
            # Calculate portfolio returns
            portfolio_returns = self._calculate_portfolio_returns(
                strategies, allocation_result.weights
            )
            
            # Calculate portfolio performance
            portfolio_performance = self.performance_calculator.calculate_portfolio_performance(
                portfolio_returns
            )
            
            # Calculate risk attribution
            risk_attribution = self.risk_attributor.calculate_risk_attribution(
                strategies, allocation_result.weights, lookback_window
            )
            
            return PortfolioTestResult(
                portfolio_name=portfolio_name,
                test_period=(start_date, end_date),
                strategies=strategies,
                allocation_result=allocation_result,
                portfolio_performance=portfolio_performance,
                correlation_analysis=correlation_analysis,
                risk_attribution=risk_attribution,
                rebalancing_history=[],
                transaction_costs=0.0,
                metadata={
                    "allocation_method": allocation_method.value,
                    "rebalancing_frequency": rebalancing_frequency.value,
                    "transaction_cost_bps": transaction_cost_bps,
                    "lookback_window": lookback_window,
                    "test_date": datetime.now()
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error testing portfolio {portfolio_name}: {e}")
            return self._empty_portfolio_test_result(portfolio_name)
    
    def _calculate_portfolio_returns(self,
                                   strategies: List[Strategy],
                                   weights: Dict[str, float]) -> pd.Series:
        """Calculate portfolio returns"""
        try:
            # Align strategy returns
            returns_data = {}
            for strategy in strategies:
                if strategy.name in weights:
                    returns_data[strategy.name] = strategy.returns
            
            returns_df = pd.DataFrame(returns_data).dropna()
            
            if len(returns_df) == 0:
                return pd.Series(dtype=float)
            
            # Calculate weighted portfolio returns
            portfolio_returns = pd.Series(0.0, index=returns_df.index)
            for strategy_name, weight in weights.items():
                if strategy_name in returns_df.columns:
                    portfolio_returns += weight * returns_df[strategy_name]
            
            return portfolio_returns
            
        except Exception as e:
            self.logger.error(f"Error calculating portfolio returns: {e}")
            return pd.Series(dtype=float)
    
    def _empty_portfolio_test_result(self, portfolio_name: str) -> PortfolioTestResult:
        """Return empty portfolio test result"""
        return PortfolioTestResult(
            portfolio_name=portfolio_name,
            test_period=(datetime.now(), datetime.now()),
            strategies=[],
            allocation_result=self.portfolio_optimizer._empty_allocation_result(AllocationMethod.EQUAL_WEIGHT),
            portfolio_performance=self.performance_calculator._empty_performance(),
            correlation_analysis=self.correlation_analyzer._empty_correlation_analysis(),
            risk_attribution=self.risk_attributor._empty_risk_attribution(),
            rebalancing_history=[],
            transaction_costs=0.0,
            metadata={"error": "Failed to test portfolio"}
        )


# Example usage
async def example_usage():
    """Demonstrate multi-strategy portfolio testing"""
    print("=== Multi-Strategy Portfolio Testing Demo ===")
    
    # Create sample strategies
    np.random.seed(42)
    dates = pd.date_range(start='2022-01-01', end='2023-12-31', freq='D')
    
    # Strategy 1: Momentum strategy
    momentum_returns = np.random.normal(0.0008, 0.018, len(dates))
    momentum_strategy = Strategy(
        name="Momentum",
        returns=pd.Series(momentum_returns, index=dates),
        description="Momentum-based trading strategy",
        strategy_type="momentum",
        risk_budget=0.3
    )
    
    # Strategy 2: Mean reversion strategy
    mean_reversion_returns = np.random.normal(0.0006, 0.015, len(dates))
    mean_reversion_strategy = Strategy(
        name="MeanReversion",
        returns=pd.Series(mean_reversion_returns, index=dates),
        description="Mean reversion trading strategy",
        strategy_type="mean_reversion",
        risk_budget=0.25
    )
    
    strategies = [momentum_strategy, mean_reversion_strategy]
    
    print(f"Created {len(strategies)} strategies with {len(dates)} days of data")
    
    # Create portfolio tester
    tester = MultiStrategyPortfolioTester()
    
    # Test portfolio with risk parity allocation
    result = await tester.test_portfolio(
        portfolio_name="DiversifiedPortfolio",
        strategies=strategies,
        allocation_method=AllocationMethod.RISK_PARITY,
        rebalancing_frequency=RebalancingFrequency.MONTHLY,
        transaction_cost_bps=5.0
    )
    
    # Display results
    print(f"Portfolio: {result.portfolio_name}")
    print(f"Expected Return: {result.allocation_result.expected_return:.2%}")
    print(f"Expected Volatility: {result.allocation_result.expected_volatility:.2%}")
    print(f"Sharpe Ratio: {result.allocation_result.sharpe_ratio:.3f}")
    
    print("\\nStrategy Allocations:")
    for strategy_name, weight in result.allocation_result.weights.items():
        print(f"  {strategy_name}: {weight:.1%}")
    
    print("\\nMulti-strategy portfolio testing demo completed!")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run example
    asyncio.run(example_usage())