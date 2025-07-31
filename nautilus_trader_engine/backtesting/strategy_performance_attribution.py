"""
Strategy Performance Attribution Framework

This module provides comprehensive performance attribution capabilities including:
- Factor-based attribution analysis
- Risk-adjusted performance metrics
- Benchmark comparison and tracking error
- Performance decomposition tools
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
import warnings

# Try to import optional dependencies
try:
    import scipy.stats as stats
    import scipy.optimize as optimize
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

try:
    import sklearn.linear_model as linear_model
    import sklearn.decomposition as decomposition
    import sklearn.preprocessing as preprocessing
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


class AttributionMethod(Enum):
    """Attribution analysis methods"""
    BRINSON = "brinson"
    FACTOR_MODEL = "factor_model"
    RISK_MODEL = "risk_model"
    HOLDINGS_BASED = "holdings_based"
    RETURNS_BASED = "returns_based"


class PerformanceMetric(Enum):
    """Performance metrics for attribution"""
    TOTAL_RETURN = "total_return"
    EXCESS_RETURN = "excess_return"
    SHARPE_RATIO = "sharpe_ratio"
    INFORMATION_RATIO = "information_ratio"
    ALPHA = "alpha"
    BETA = "beta"
    TRACKING_ERROR = "tracking_error"
    MAX_DRAWDOWN = "max_drawdown"


@dataclass
class Factor:
    """Factor definition for attribution analysis"""
    name: str
    description: str
    factor_type: str  # "market", "style", "sector", "custom"
    data: pd.Series
    benchmark_exposure: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AttributionResult:
    """Single attribution analysis result"""
    period_start: datetime
    period_end: datetime
    total_return: float
    benchmark_return: float
    excess_return: float
    factor_contributions: Dict[str, float]
    selection_effect: float
    allocation_effect: float
    interaction_effect: float
    specific_return: float
    attribution_method: AttributionMethod
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics"""
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    calmar_ratio: float
    sortino_ratio: float
    win_rate: float
    average_win: float
    average_loss: float
    profit_factor: float
    recovery_factor: float
    var_95: float
    cvar_95: float
    skewness: float
    kurtosis: float
    beta: float
    alpha: float
    information_ratio: float
    tracking_error: float
    up_capture: float
    down_capture: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkComparison:
    """Benchmark comparison results"""
    benchmark_name: str
    correlation: float
    beta: float
    alpha: float
    r_squared: float
    tracking_error: float
    information_ratio: float
    up_capture_ratio: float
    down_capture_ratio: float
    excess_return_periods: int
    outperformance_ratio: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceAttribution:
    """Complete performance attribution analysis"""
    strategy_name: str
    analysis_period: Tuple[datetime, datetime]
    attribution_results: List[AttributionResult]
    performance_metrics: PerformanceMetrics
    benchmark_comparisons: List[BenchmarkComparison]
    factor_exposures: Dict[str, float]
    risk_decomposition: Dict[str, float]
    performance_summary: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


class FactorModelBuilder:
    """Builds factor models for attribution analysis"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def build_factor_model(self, returns: pd.Series, factors: List[Factor],
                          method: str = "ols") -> Dict[str, Any]:
        """Build factor model using specified method"""
        try:
            if not SKLEARN_AVAILABLE:
                self.logger.warning("sklearn not available, using simple linear regression")
                return self._simple_factor_model(returns, factors)
            
            # Prepare factor data
            factor_data = pd.DataFrame()
            for factor in factors:
                factor_data[factor.name] = factor.data
            
            # Align data
            aligned_data = pd.concat([returns, factor_data], axis=1).dropna()
            
            if len(aligned_data) < 10:
                raise ValueError("Insufficient data for factor model")
            
            y = aligned_data.iloc[:, 0].values  # Returns
            X = aligned_data.iloc[:, 1:].values  # Factors
            
            # Fit model
            if method == "ols":
                model = linear_model.LinearRegression()
            elif method == "ridge":
                model = linear_model.Ridge(alpha=0.1)
            elif method == "lasso":
                model = linear_model.Lasso(alpha=0.01)
            else:
                model = linear_model.LinearRegression()
            
            model.fit(X, y)
            
            # Calculate model statistics
            y_pred = model.predict(X)
            residuals = y - y_pred
            
            # R-squared
            ss_res = np.sum(residuals ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            # Factor loadings
            factor_loadings = dict(zip([f.name for f in factors], model.coef_))
            
            # Specific risk (residual volatility)
            specific_risk = np.std(residuals) * np.sqrt(252)  # Annualized
            
            return {
                "model": model,
                "factor_loadings": factor_loadings,
                "alpha": model.intercept_,
                "r_squared": r_squared,
                "specific_risk": specific_risk,
                "residuals": residuals,
                "fitted_values": y_pred
            }
            
        except Exception as e:
            self.logger.error(f"Error building factor model: {e}")
            return self._simple_factor_model(returns, factors)
    
    def _simple_factor_model(self, returns: pd.Series, factors: List[Factor]) -> Dict[str, Any]:
        """Simple factor model using basic linear regression"""
        try:
            if not factors:
                return {
                    "factor_loadings": {},
                    "alpha": returns.mean(),
                    "r_squared": 0.0,
                    "specific_risk": returns.std() * np.sqrt(252)
                }
            
            # Use first factor as market factor
            market_factor = factors[0]
            
            # Align data
            aligned_data = pd.concat([returns, market_factor.data], axis=1).dropna()
            
            if len(aligned_data) < 2:
                return {
                    "factor_loadings": {market_factor.name: 0.0},
                    "alpha": returns.mean(),
                    "r_squared": 0.0,
                    "specific_risk": returns.std() * np.sqrt(252)
                }
            
            y = aligned_data.iloc[:, 0].values
            x = aligned_data.iloc[:, 1].values
            
            # Simple linear regression
            if np.std(x) > 0:
                correlation = np.corrcoef(x, y)[0, 1]
                beta = correlation * (np.std(y) / np.std(x))
                alpha = np.mean(y) - beta * np.mean(x)
                r_squared = correlation ** 2
            else:
                beta = 0.0
                alpha = np.mean(y)
                r_squared = 0.0
            
            # Residuals
            y_pred = alpha + beta * x
            residuals = y - y_pred
            specific_risk = np.std(residuals) * np.sqrt(252)
            
            return {
                "factor_loadings": {market_factor.name: beta},
                "alpha": alpha,
                "r_squared": r_squared,
                "specific_risk": specific_risk,
                "residuals": residuals
            }
            
        except Exception as e:
            self.logger.error(f"Error in simple factor model: {e}")
            return {
                "factor_loadings": {},
                "alpha": 0.0,
                "r_squared": 0.0,
                "specific_risk": 0.2
            }


class PerformanceCalculator:
    """Calculates comprehensive performance metrics"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def calculate_performance_metrics(self, returns: pd.Series,
                                    benchmark_returns: Optional[pd.Series] = None,
                                    risk_free_rate: float = 0.02) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics"""
        try:
            if len(returns) == 0:
                return self._empty_metrics()
            
            # Basic return metrics
            total_return = (1 + returns).prod() - 1
            periods_per_year = self._infer_frequency(returns)
            annualized_return = (1 + total_return) ** (periods_per_year / len(returns)) - 1
            
            # Risk metrics
            volatility = returns.std() * np.sqrt(periods_per_year)
            
            # Sharpe ratio
            excess_returns = returns - risk_free_rate / periods_per_year
            sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(periods_per_year) if excess_returns.std() > 0 else 0
            
            # Drawdown analysis
            cumulative_returns = (1 + returns).cumprod()
            rolling_max = cumulative_returns.expanding().max()
            drawdowns = (cumulative_returns - rolling_max) / rolling_max
            max_drawdown = drawdowns.min()
            
            # Calmar ratio
            calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
            
            # Sortino ratio
            downside_returns = returns[returns < 0]
            downside_std = downside_returns.std() * np.sqrt(periods_per_year) if len(downside_returns) > 0 else volatility
            sortino_ratio = (annualized_return - risk_free_rate) / downside_std if downside_std > 0 else 0
            
            # Win/Loss metrics
            winning_returns = returns[returns > 0]
            losing_returns = returns[returns < 0]
            
            win_rate = len(winning_returns) / len(returns) if len(returns) > 0 else 0
            average_win = winning_returns.mean() if len(winning_returns) > 0 else 0
            average_loss = losing_returns.mean() if len(losing_returns) > 0 else 0
            
            profit_factor = abs(winning_returns.sum() / losing_returns.sum()) if losing_returns.sum() != 0 else float('inf')
            
            # Recovery factor
            recovery_factor = total_return / abs(max_drawdown) if max_drawdown != 0 else 0
            
            # VaR and CVaR
            var_95 = returns.quantile(0.05)
            cvar_95 = returns[returns <= var_95].mean() if len(returns[returns <= var_95]) > 0 else var_95
            
            # Higher moments
            skewness = returns.skew() if len(returns) > 2 else 0
            kurtosis = returns.kurtosis() if len(returns) > 3 else 0
            
            # Benchmark-relative metrics
            beta = 1.0
            alpha = 0.0
            information_ratio = 0.0
            tracking_error = 0.0
            up_capture = 1.0
            down_capture = 1.0
            
            if benchmark_returns is not None and len(benchmark_returns) > 0:
                # Align returns
                aligned_data = pd.concat([returns, benchmark_returns], axis=1).dropna()
                if len(aligned_data) > 1:
                    strategy_ret = aligned_data.iloc[:, 0]
                    benchmark_ret = aligned_data.iloc[:, 1]
                    
                    # Beta and alpha
                    if benchmark_ret.std() > 0:
                        beta = np.cov(strategy_ret, benchmark_ret)[0, 1] / benchmark_ret.var()
                        alpha = strategy_ret.mean() - beta * benchmark_ret.mean()
                    
                    # Tracking error and information ratio
                    excess_ret = strategy_ret - benchmark_ret
                    tracking_error = excess_ret.std() * np.sqrt(periods_per_year)
                    information_ratio = excess_ret.mean() / excess_ret.std() * np.sqrt(periods_per_year) if excess_ret.std() > 0 else 0
                    
                    # Capture ratios
                    up_periods = benchmark_ret > 0
                    down_periods = benchmark_ret < 0
                    
                    if up_periods.sum() > 0:
                        up_capture = strategy_ret[up_periods].mean() / benchmark_ret[up_periods].mean()
                    
                    if down_periods.sum() > 0:
                        down_capture = strategy_ret[down_periods].mean() / benchmark_ret[down_periods].mean()
            
            return PerformanceMetrics(
                total_return=total_return,
                annualized_return=annualized_return,
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                calmar_ratio=calmar_ratio,
                sortino_ratio=sortino_ratio,
                win_rate=win_rate,
                average_win=average_win,
                average_loss=average_loss,
                profit_factor=profit_factor,
                recovery_factor=recovery_factor,
                var_95=var_95,
                cvar_95=cvar_95,
                skewness=skewness,
                kurtosis=kurtosis,
                beta=beta,
                alpha=alpha,
                information_ratio=information_ratio,
                tracking_error=tracking_error,
                up_capture=up_capture,
                down_capture=down_capture
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating performance metrics: {e}")
            return self._empty_metrics()
    
    def _empty_metrics(self) -> PerformanceMetrics:
        """Return empty performance metrics"""
        return PerformanceMetrics(
            total_return=0.0, annualized_return=0.0, volatility=0.0,
            sharpe_ratio=0.0, max_drawdown=0.0, calmar_ratio=0.0,
            sortino_ratio=0.0, win_rate=0.0, average_win=0.0,
            average_loss=0.0, profit_factor=0.0, recovery_factor=0.0,
            var_95=0.0, cvar_95=0.0, skewness=0.0, kurtosis=0.0,
            beta=1.0, alpha=0.0, information_ratio=0.0,
            tracking_error=0.0, up_capture=1.0, down_capture=1.0
        )
    
    def _infer_frequency(self, returns: pd.Series) -> int:
        """Infer the frequency of returns data"""
        if hasattr(returns.index, 'freq') and returns.index.freq:
            freq = returns.index.freq
            if 'D' in str(freq):
                return 252
            elif 'W' in str(freq):
                return 52
            elif 'M' in str(freq):
                return 12
            elif 'Q' in str(freq):
                return 4
            elif 'Y' in str(freq):
                return 1
        
        # Default to daily
        return 252


class BenchmarkAnalyzer:
    """Analyzes performance relative to benchmarks"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def compare_to_benchmark(self, strategy_returns: pd.Series,
                           benchmark_returns: pd.Series,
                           benchmark_name: str = "Benchmark") -> BenchmarkComparison:
        """Compare strategy performance to benchmark"""
        try:
            # Align returns
            aligned_data = pd.concat([strategy_returns, benchmark_returns], axis=1).dropna()
            
            if len(aligned_data) < 2:
                return self._empty_comparison(benchmark_name)
            
            strategy_ret = aligned_data.iloc[:, 0]
            benchmark_ret = aligned_data.iloc[:, 1]
            
            # Basic statistics
            correlation = strategy_ret.corr(benchmark_ret)
            
            # Regression analysis
            if benchmark_ret.std() > 0:
                beta = np.cov(strategy_ret, benchmark_ret)[0, 1] / benchmark_ret.var()
                alpha = strategy_ret.mean() - beta * benchmark_ret.mean()
                
                # R-squared
                predicted_returns = alpha + beta * benchmark_ret
                ss_res = ((strategy_ret - predicted_returns) ** 2).sum()
                ss_tot = ((strategy_ret - strategy_ret.mean()) ** 2).sum()
                r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            else:
                beta = 0.0
                alpha = strategy_ret.mean()
                r_squared = 0.0
            
            # Tracking error and information ratio
            excess_returns = strategy_ret - benchmark_ret
            tracking_error = excess_returns.std() * np.sqrt(252)
            information_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252) if excess_returns.std() > 0 else 0
            
            # Capture ratios
            up_periods = benchmark_ret > 0
            down_periods = benchmark_ret < 0
            
            up_capture_ratio = 1.0
            down_capture_ratio = 1.0
            
            if up_periods.sum() > 0 and benchmark_ret[up_periods].mean() != 0:
                up_capture_ratio = strategy_ret[up_periods].mean() / benchmark_ret[up_periods].mean()
            
            if down_periods.sum() > 0 and benchmark_ret[down_periods].mean() != 0:
                down_capture_ratio = strategy_ret[down_periods].mean() / benchmark_ret[down_periods].mean()
            
            # Outperformance statistics
            excess_return_periods = (excess_returns > 0).sum()
            outperformance_ratio = excess_return_periods / len(excess_returns) if len(excess_returns) > 0 else 0
            
            return BenchmarkComparison(
                benchmark_name=benchmark_name,
                correlation=correlation,
                beta=beta,
                alpha=alpha,
                r_squared=r_squared,
                tracking_error=tracking_error,
                information_ratio=information_ratio,
                up_capture_ratio=up_capture_ratio,
                down_capture_ratio=down_capture_ratio,
                excess_return_periods=excess_return_periods,
                outperformance_ratio=outperformance_ratio
            )
            
        except Exception as e:
            self.logger.error(f"Error comparing to benchmark {benchmark_name}: {e}")
            return self._empty_comparison(benchmark_name)
    
    def _empty_comparison(self, benchmark_name: str) -> BenchmarkComparison:
        """Return empty benchmark comparison"""
        return BenchmarkComparison(
            benchmark_name=benchmark_name,
            correlation=0.0, beta=1.0, alpha=0.0, r_squared=0.0,
            tracking_error=0.0, information_ratio=0.0,
            up_capture_ratio=1.0, down_capture_ratio=1.0,
            excess_return_periods=0, outperformance_ratio=0.0
        )


class AttributionAnalyzer:
    """Performs attribution analysis"""
    
    def __init__(self):
        self.factor_model_builder = FactorModelBuilder()
        self.logger = logging.getLogger(__name__)
    
    def perform_attribution_analysis(self, strategy_returns: pd.Series,
                                   benchmark_returns: pd.Series,
                                   factors: List[Factor],
                                   method: AttributionMethod = AttributionMethod.FACTOR_MODEL) -> List[AttributionResult]:
        """Perform attribution analysis"""
        try:
            if method == AttributionMethod.FACTOR_MODEL:
                return self._factor_based_attribution(strategy_returns, benchmark_returns, factors)
            elif method == AttributionMethod.BRINSON:
                return self._brinson_attribution(strategy_returns, benchmark_returns, factors)
            else:
                return self._returns_based_attribution(strategy_returns, benchmark_returns)
                
        except Exception as e:
            self.logger.error(f"Error in attribution analysis: {e}")
            return []
    
    def _factor_based_attribution(self, strategy_returns: pd.Series,
                                benchmark_returns: pd.Series,
                                factors: List[Factor]) -> List[AttributionResult]:
        """Factor-based attribution analysis"""
        try:
            # Build factor model for strategy
            strategy_model = self.factor_model_builder.build_factor_model(strategy_returns, factors)
            
            # Build factor model for benchmark
            benchmark_model = self.factor_model_builder.build_factor_model(benchmark_returns, factors)
            
            # Calculate factor contributions
            factor_contributions = {}
            
            for factor in factors:
                strategy_loading = strategy_model["factor_loadings"].get(factor.name, 0.0)
                benchmark_loading = benchmark_model["factor_loadings"].get(factor.name, 0.0)
                
                # Factor contribution = (strategy loading - benchmark loading) * factor return
                factor_return = factor.data.mean()
                contribution = (strategy_loading - benchmark_loading) * factor_return
                factor_contributions[factor.name] = contribution
            
            # Selection effect (alpha difference)
            selection_effect = strategy_model["alpha"] - benchmark_model["alpha"]
            
            # Allocation effect (sum of factor contributions)
            allocation_effect = sum(factor_contributions.values())
            
            # Interaction effect (residual)
            total_excess = strategy_returns.mean() - benchmark_returns.mean()
            interaction_effect = total_excess - selection_effect - allocation_effect
            
            # Specific return (idiosyncratic)
            specific_return = strategy_model.get("specific_risk", 0.0) - benchmark_model.get("specific_risk", 0.0)
            
            result = AttributionResult(
                period_start=strategy_returns.index[0] if len(strategy_returns) > 0 else datetime.now(),
                period_end=strategy_returns.index[-1] if len(strategy_returns) > 0 else datetime.now(),
                total_return=strategy_returns.sum(),
                benchmark_return=benchmark_returns.sum(),
                excess_return=strategy_returns.sum() - benchmark_returns.sum(),
                factor_contributions=factor_contributions,
                selection_effect=selection_effect,
                allocation_effect=allocation_effect,
                interaction_effect=interaction_effect,
                specific_return=specific_return,
                attribution_method=AttributionMethod.FACTOR_MODEL,
                metadata={
                    "strategy_model": strategy_model,
                    "benchmark_model": benchmark_model
                }
            )
            
            return [result]
            
        except Exception as e:
            self.logger.error(f"Error in factor-based attribution: {e}")
            return []
    
    def _brinson_attribution(self, strategy_returns: pd.Series,
                           benchmark_returns: pd.Series,
                           factors: List[Factor]) -> List[AttributionResult]:
        """Brinson attribution analysis"""
        try:
            # Simplified Brinson attribution
            # In practice, this would require holdings data
            
            total_return = strategy_returns.sum()
            benchmark_return = benchmark_returns.sum()
            excess_return = total_return - benchmark_return
            
            # Simplified allocation: assume equal factor contributions
            allocation_effect = excess_return * 0.6  # 60% allocation
            selection_effect = excess_return * 0.4   # 40% selection
            interaction_effect = 0.0
            
            factor_contributions = {}
            if factors:
                contribution_per_factor = allocation_effect / len(factors)
                for factor in factors:
                    factor_contributions[factor.name] = contribution_per_factor
            
            result = AttributionResult(
                period_start=strategy_returns.index[0] if len(strategy_returns) > 0 else datetime.now(),
                period_end=strategy_returns.index[-1] if len(strategy_returns) > 0 else datetime.now(),
                total_return=total_return,
                benchmark_return=benchmark_return,
                excess_return=excess_return,
                factor_contributions=factor_contributions,
                selection_effect=selection_effect,
                allocation_effect=allocation_effect,
                interaction_effect=interaction_effect,
                specific_return=0.0,
                attribution_method=AttributionMethod.BRINSON
            )
            
            return [result]
            
        except Exception as e:
            self.logger.error(f"Error in Brinson attribution: {e}")
            return []
    
    def _returns_based_attribution(self, strategy_returns: pd.Series,
                                 benchmark_returns: pd.Series) -> List[AttributionResult]:
        """Simple returns-based attribution"""
        try:
            total_return = strategy_returns.sum()
            benchmark_return = benchmark_returns.sum()
            excess_return = total_return - benchmark_return
            
            result = AttributionResult(
                period_start=strategy_returns.index[0] if len(strategy_returns) > 0 else datetime.now(),
                period_end=strategy_returns.index[-1] if len(strategy_returns) > 0 else datetime.now(),
                total_return=total_return,
                benchmark_return=benchmark_return,
                excess_return=excess_return,
                factor_contributions={},
                selection_effect=excess_return,
                allocation_effect=0.0,
                interaction_effect=0.0,
                specific_return=0.0,
                attribution_method=AttributionMethod.RETURNS_BASED
            )
            
            return [result]
            
        except Exception as e:
            self.logger.error(f"Error in returns-based attribution: {e}")
            return []


class StrategyPerformanceAttributor:
    """Main strategy performance attribution system"""
    
    def __init__(self):
        self.performance_calculator = PerformanceCalculator()
        self.benchmark_analyzer = BenchmarkAnalyzer()
        self.attribution_analyzer = AttributionAnalyzer()
        self.logger = logging.getLogger(__name__)
    
    async def analyze_strategy_performance(self,
                                         strategy_name: str,
                                         strategy_returns: pd.Series,
                                         benchmark_returns: Optional[pd.Series] = None,
                                         factors: Optional[List[Factor]] = None,
                                         benchmark_names: Optional[List[str]] = None,
                                         attribution_method: AttributionMethod = AttributionMethod.FACTOR_MODEL) -> PerformanceAttribution:
        """Perform comprehensive strategy performance attribution"""
        try:
            analysis_start = strategy_returns.index[0] if len(strategy_returns) > 0 else datetime.now()
            analysis_end = strategy_returns.index[-1] if len(strategy_returns) > 0 else datetime.now()
            
            # Calculate performance metrics
            performance_metrics = self.performance_calculator.calculate_performance_metrics(
                strategy_returns, benchmark_returns
            )
            
            # Benchmark comparisons
            benchmark_comparisons = []
            if benchmark_returns is not None:
                comparison = self.benchmark_analyzer.compare_to_benchmark(
                    strategy_returns, benchmark_returns,
                    benchmark_names[0] if benchmark_names else "Benchmark"
                )
                benchmark_comparisons.append(comparison)
            
            # Attribution analysis
            attribution_results = []
            if benchmark_returns is not None and factors:
                attribution_results = self.attribution_analyzer.perform_attribution_analysis(
                    strategy_returns, benchmark_returns, factors, attribution_method
                )
            
            # Factor exposures
            factor_exposures = {}
            if factors:
                factor_model = self.attribution_analyzer.factor_model_builder.build_factor_model(
                    strategy_returns, factors
                )
                factor_exposures = factor_model.get("factor_loadings", {})
            
            # Risk decomposition
            risk_decomposition = self._calculate_risk_decomposition(
                strategy_returns, factors, factor_exposures
            )
            
            # Performance summary
            performance_summary = self._create_performance_summary(
                performance_metrics, benchmark_comparisons, attribution_results
            )
            
            return PerformanceAttribution(
                strategy_name=strategy_name,
                analysis_period=(analysis_start, analysis_end),
                attribution_results=attribution_results,
                performance_metrics=performance_metrics,
                benchmark_comparisons=benchmark_comparisons,
                factor_exposures=factor_exposures,
                risk_decomposition=risk_decomposition,
                performance_summary=performance_summary,
                metadata={
                    "attribution_method": attribution_method.value,
                    "num_factors": len(factors) if factors else 0,
                    "analysis_date": datetime.now()
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error in strategy performance attribution: {e}")
            return self._empty_attribution(strategy_name)
    
    def _calculate_risk_decomposition(self, returns: pd.Series,
                                    factors: Optional[List[Factor]],
                                    factor_exposures: Dict[str, float]) -> Dict[str, float]:
        """Calculate risk decomposition"""
        try:
            total_risk = returns.std() * np.sqrt(252)  # Annualized volatility
            
            if not factors or not factor_exposures:
                return {
                    "total_risk": total_risk,
                    "systematic_risk": 0.0,
                    "specific_risk": total_risk
                }
            
            # Estimate systematic risk from factor exposures
            systematic_risk_squared = 0.0
            
            for factor in factors:
                if factor.name in factor_exposures:
                    factor_vol = factor.data.std() * np.sqrt(252)
                    exposure = factor_exposures[factor.name]
                    systematic_risk_squared += (exposure * factor_vol) ** 2
            
            systematic_risk = np.sqrt(systematic_risk_squared)
            specific_risk = np.sqrt(max(0, total_risk ** 2 - systematic_risk ** 2))
            
            # Calculate percentages properly (they should sum to 1)
            if total_risk > 0:
                systematic_risk_pct = (systematic_risk ** 2) / (total_risk ** 2)
                specific_risk_pct = (specific_risk ** 2) / (total_risk ** 2)
            else:
                systematic_risk_pct = 0
                specific_risk_pct = 1
            
            return {
                "total_risk": total_risk,
                "systematic_risk": systematic_risk,
                "specific_risk": specific_risk,
                "systematic_risk_pct": systematic_risk_pct,
                "specific_risk_pct": specific_risk_pct
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating risk decomposition: {e}")
            return {"total_risk": 0.0, "systematic_risk": 0.0, "specific_risk": 0.0}
    
    def _create_performance_summary(self, metrics: PerformanceMetrics,
                                  benchmarks: List[BenchmarkComparison],
                                  attributions: List[AttributionResult]) -> Dict[str, Any]:
        """Create performance summary"""
        try:
            summary = {
                "total_return": metrics.total_return,
                "annualized_return": metrics.annualized_return,
                "volatility": metrics.volatility,
                "sharpe_ratio": metrics.sharpe_ratio,
                "max_drawdown": metrics.max_drawdown,
                "win_rate": metrics.win_rate
            }
            
            if benchmarks:
                benchmark = benchmarks[0]
                summary.update({
                    "alpha": benchmark.alpha,
                    "beta": benchmark.beta,
                    "information_ratio": benchmark.information_ratio,
                    "tracking_error": benchmark.tracking_error,
                    "correlation": benchmark.correlation
                })
            
            if attributions:
                attribution = attributions[0]
                summary.update({
                    "excess_return": attribution.excess_return,
                    "selection_effect": attribution.selection_effect,
                    "allocation_effect": attribution.allocation_effect,
                    "top_factor_contribution": max(attribution.factor_contributions.values()) if attribution.factor_contributions else 0
                })
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error creating performance summary: {e}")
            return {}
    
    def _empty_attribution(self, strategy_name: str) -> PerformanceAttribution:
        """Return empty performance attribution"""
        return PerformanceAttribution(
            strategy_name=strategy_name,
            analysis_period=(datetime.now(), datetime.now()),
            attribution_results=[],
            performance_metrics=self.performance_calculator._empty_metrics(),
            benchmark_comparisons=[],
            factor_exposures={},
            risk_decomposition={},
            performance_summary={},
            metadata={"error": "Failed to perform attribution analysis"}
        )


# Example usage and testing
async def example_usage():
    """Demonstrate strategy performance attribution"""
    print("=== Strategy Performance Attribution Demo ===")
    
    # Create sample data
    np.random.seed(42)
    dates = pd.date_range(start='2022-01-01', end='2023-12-31', freq='D')
    
    # Generate synthetic strategy returns with some alpha
    market_returns = np.random.normal(0.0008, 0.015, len(dates))
    strategy_returns = 0.0002 + 1.2 * market_returns + np.random.normal(0, 0.01, len(dates))
    
    # Create benchmark returns (market)
    benchmark_returns = market_returns
    
    # Create factor data
    value_factor = np.random.normal(0.0003, 0.012, len(dates))
    momentum_factor = np.random.normal(0.0001, 0.010, len(dates))
    size_factor = np.random.normal(-0.0001, 0.008, len(dates))
    
    # Create pandas series
    strategy_series = pd.Series(strategy_returns, index=dates, name='Strategy')
    benchmark_series = pd.Series(benchmark_returns, index=dates, name='Market')
    
    # Define factors
    factors = [
        Factor(
            name="Market",
            description="Market factor (broad market exposure)",
            factor_type="market",
            data=pd.Series(market_returns, index=dates),
            benchmark_exposure=1.0
        ),
        Factor(
            name="Value",
            description="Value factor (value vs growth)",
            factor_type="style",
            data=pd.Series(value_factor, index=dates),
            benchmark_exposure=0.0
        ),
        Factor(
            name="Momentum",
            description="Momentum factor (price momentum)",
            factor_type="style",
            data=pd.Series(momentum_factor, index=dates),
            benchmark_exposure=0.0
        ),
        Factor(
            name="Size",
            description="Size factor (small vs large cap)",
            factor_type="style",
            data=pd.Series(size_factor, index=dates),
            benchmark_exposure=0.0
        )
    ]
    
    print(f"Generated {len(dates)} days of synthetic data")
    print(f"Strategy total return: {(1 + strategy_series).prod() - 1:.2%}")
    print(f"Benchmark total return: {(1 + benchmark_series).prod() - 1:.2%}")
    
    # Perform attribution analysis
    print("\\nPerforming attribution analysis...")
    
    attributor = StrategyPerformanceAttributor()
    
    attribution = await attributor.analyze_strategy_performance(
        strategy_name="Demo Strategy",
        strategy_returns=strategy_series,
        benchmark_returns=benchmark_series,
        factors=factors,
        benchmark_names=["Market Index"],
        attribution_method=AttributionMethod.FACTOR_MODEL
    )
    
    # Display results
    print("\\n=== Performance Metrics ===")
    metrics = attribution.performance_metrics
    print(f"Total Return: {metrics.total_return:.2%}")
    print(f"Annualized Return: {metrics.annualized_return:.2%}")
    print(f"Volatility: {metrics.volatility:.2%}")
    print(f"Sharpe Ratio: {metrics.sharpe_ratio:.3f}")
    print(f"Max Drawdown: {metrics.max_drawdown:.2%}")
    print(f"Win Rate: {metrics.win_rate:.2%}")
    print(f"Alpha: {metrics.alpha:.4f}")
    print(f"Beta: {metrics.beta:.3f}")
    print(f"Information Ratio: {metrics.information_ratio:.3f}")
    
    print("\\n=== Benchmark Comparison ===")
    if attribution.benchmark_comparisons:
        benchmark = attribution.benchmark_comparisons[0]
        print(f"Benchmark: {benchmark.benchmark_name}")
        print(f"Correlation: {benchmark.correlation:.3f}")
        print(f"Beta: {benchmark.beta:.3f}")
        print(f"Alpha: {benchmark.alpha:.4f}")
        print(f"R-squared: {benchmark.r_squared:.3f}")
        print(f"Tracking Error: {benchmark.tracking_error:.2%}")
        print(f"Information Ratio: {benchmark.information_ratio:.3f}")
        print(f"Up Capture: {benchmark.up_capture_ratio:.3f}")
        print(f"Down Capture: {benchmark.down_capture_ratio:.3f}")
        print(f"Outperformance Ratio: {benchmark.outperformance_ratio:.2%}")
    
    print("\\n=== Factor Exposures ===")
    for factor_name, exposure in attribution.factor_exposures.items():
        print(f"{factor_name}: {exposure:.3f}")
    
    print("\\n=== Risk Decomposition ===")
    for risk_type, value in attribution.risk_decomposition.items():
        if "pct" in risk_type:
            print(f"{risk_type}: {value:.1%}")
        else:
            print(f"{risk_type}: {value:.2%}")
    
    print("\\n=== Attribution Analysis ===")
    if attribution.attribution_results:
        attr_result = attribution.attribution_results[0]
        print(f"Total Return: {attr_result.total_return:.2%}")
        print(f"Benchmark Return: {attr_result.benchmark_return:.2%}")
        print(f"Excess Return: {attr_result.excess_return:.2%}")
        print(f"Selection Effect: {attr_result.selection_effect:.4f}")
        print(f"Allocation Effect: {attr_result.allocation_effect:.4f}")
        print(f"Interaction Effect: {attr_result.interaction_effect:.4f}")
        
        print("\\nFactor Contributions:")
        for factor_name, contribution in attr_result.factor_contributions.items():
            print(f"  {factor_name}: {contribution:.4f}")
    
    print("\\n=== Performance Summary ===")
    for key, value in attribution.performance_summary.items():
        if isinstance(value, float):
            if abs(value) < 0.01:
                print(f"{key}: {value:.4f}")
            else:
                print(f"{key}: {value:.3f}")
        else:
            print(f"{key}: {value}")
    
    print("\\nStrategy performance attribution demo completed!")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run example
    asyncio.run(example_usage())