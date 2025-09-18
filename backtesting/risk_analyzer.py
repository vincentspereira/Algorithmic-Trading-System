"""Risk Analysis Module

This module provides comprehensive risk analysis for backtesting results
including VaR, stress testing, risk attribution, and scenario analysis.
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from scipy import stats
from sklearn.decomposition import PCA
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

@dataclass
class RiskMetrics:
    """Container for risk metrics"""
    # Value at Risk metrics
    var_1d_95: float = 0.0
    var_1d_99: float = 0.0
    var_10d_95: float = 0.0
    var_10d_99: float = 0.0
    
    # Conditional Value at Risk
    cvar_1d_95: float = 0.0
    cvar_1d_99: float = 0.0
    cvar_10d_95: float = 0.0
    cvar_10d_99: float = 0.0
    
    # Volatility metrics
    realized_volatility: float = 0.0
    garch_volatility: float = 0.0
    ewma_volatility: float = 0.0
    
    # Drawdown metrics
    max_drawdown: float = 0.0
    avg_drawdown: float = 0.0
    drawdown_duration: int = 0
    recovery_time: int = 0
    
    # Tail risk metrics
    skewness: float = 0.0
    kurtosis: float = 0.0
    tail_ratio: float = 0.0
    
    # Concentration risk
    concentration_index: float = 0.0
    effective_positions: int = 0
    
    # Correlation risk
    avg_correlation: float = 0.0
    max_correlation: float = 0.0
    
    # Leverage metrics
    gross_leverage: float = 0.0
    net_leverage: float = 0.0
    
    # Risk-adjusted metrics
    risk_adjusted_return: float = 0.0
    ulcer_index: float = 0.0
    pain_index: float = 0.0

@dataclass
class VaRAnalysis:
    """Value at Risk analysis results"""
    historical_var: Dict[str, float] = field(default_factory=dict)
    parametric_var: Dict[str, float] = field(default_factory=dict)
    monte_carlo_var: Dict[str, float] = field(default_factory=dict)
    
    # Backtesting results
    var_exceptions: int = 0
    exception_rate: float = 0.0
    kupiec_test_pvalue: float = 0.0
    
    # Component VaR
    component_var: Dict[str, float] = field(default_factory=dict)
    marginal_var: Dict[str, float] = field(default_factory=dict)

@dataclass
class StressTestResults:
    """Stress testing results"""
    scenario_results: Dict[str, float] = field(default_factory=dict)
    worst_case_scenario: str = ""
    worst_case_loss: float = 0.0
    
    # Historical scenarios
    historical_scenarios: Dict[str, float] = field(default_factory=dict)
    
    # Factor stress tests
    factor_stress: Dict[str, float] = field(default_factory=dict)
    
    # Correlation breakdown
    correlation_stress: Dict[str, float] = field(default_factory=dict)

@dataclass
class DrawdownAnalysis:
    """Detailed drawdown analysis"""
    drawdown_periods: List[Dict[str, Any]] = field(default_factory=list)
    max_drawdown: float = 0.0
    avg_drawdown: float = 0.0
    max_duration: int = 0
    avg_duration: int = 0
    recovery_factor: float = 0.0
    
    # Underwater curve
    underwater_curve: pd.Series = field(default_factory=pd.Series)
    
    # Drawdown distribution
    drawdown_distribution: Dict[str, float] = field(default_factory=dict)

@dataclass
class RiskAttribution:
    """Risk attribution analysis"""
    factor_contributions: Dict[str, float] = field(default_factory=dict)
    sector_contributions: Dict[str, float] = field(default_factory=dict)
    asset_contributions: Dict[str, float] = field(default_factory=dict)
    
    # Risk decomposition
    systematic_risk: float = 0.0
    idiosyncratic_risk: float = 0.0
    
    # Factor loadings
    factor_loadings: Dict[str, float] = field(default_factory=dict)
    
    # Risk budget
    risk_budget: Dict[str, float] = field(default_factory=dict)

class RiskAnalyzer:
    """Comprehensive risk analyzer
    
    Provides detailed risk analysis including VaR, stress testing,
    risk attribution, and scenario analysis.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize risk analyzer
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.var_confidence = self.config.get('var_confidence', 0.95)
        self.var_horizon = self.config.get('var_horizon', 1)
        self.cvar_confidence = self.config.get('cvar_confidence', 0.95)
        self.volatility_window = self.config.get('volatility_window', 252)
        
        # Stress test scenarios
        self.stress_scenarios = {
            '2008_crisis': {'equity': -0.37, 'bond': 0.05, 'commodity': -0.36},
            '2020_covid': {'equity': -0.34, 'bond': 0.08, 'commodity': -0.21},
            'dot_com_crash': {'equity': -0.49, 'bond': 0.16, 'commodity': -0.12},
            'inflation_shock': {'equity': -0.15, 'bond': -0.10, 'commodity': 0.25},
            'interest_rate_shock': {'equity': -0.10, 'bond': -0.15, 'commodity': 0.05}
        }
        
        logger.info("Initialized risk analyzer")
    
    def analyze_risk(
        self,
        returns: pd.Series,
        positions: Optional[pd.DataFrame] = None,
        market_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> Tuple[RiskMetrics, VaRAnalysis, StressTestResults, DrawdownAnalysis, RiskAttribution]:
        """Comprehensive risk analysis
        
        Args:
            returns: Portfolio returns time series
            positions: Position weights over time
            market_data: Market data for factor analysis
            
        Returns:
            Tuple of risk analysis results
        """
        try:
            # Calculate risk metrics
            risk_metrics = self._calculate_risk_metrics(returns, positions)
            
            # VaR analysis
            var_analysis = self._calculate_var_analysis(returns)
            
            # Stress testing
            stress_results = self._perform_stress_tests(returns, positions)
            
            # Drawdown analysis
            drawdown_analysis = self._analyze_drawdowns(returns)
            
            # Risk attribution
            risk_attribution = self._calculate_risk_attribution(returns, positions, market_data)
            
            logger.info(f"Risk analysis completed - VaR(95%): {risk_metrics.var_1d_95:.2%}, Max DD: {risk_metrics.max_drawdown:.2%}")
            
            return risk_metrics, var_analysis, stress_results, drawdown_analysis, risk_attribution
            
        except Exception as e:
            logger.error(f"Error analyzing risk: {e}")
            raise
    
    def _calculate_risk_metrics(self, returns: pd.Series, positions: Optional[pd.DataFrame] = None) -> RiskMetrics:
        """Calculate comprehensive risk metrics"""
        try:
            metrics = RiskMetrics()
            
            if returns.empty:
                return metrics
            
            # VaR calculations
            metrics.var_1d_95 = returns.quantile(1 - 0.95)
            metrics.var_1d_99 = returns.quantile(1 - 0.99)
            metrics.var_10d_95 = returns.quantile(1 - 0.95) * np.sqrt(10)
            metrics.var_10d_99 = returns.quantile(1 - 0.99) * np.sqrt(10)
            
            # CVaR calculations
            tail_95 = returns[returns <= metrics.var_1d_95]
            tail_99 = returns[returns <= metrics.var_1d_99]
            
            metrics.cvar_1d_95 = tail_95.mean() if len(tail_95) > 0 else 0
            metrics.cvar_1d_99 = tail_99.mean() if len(tail_99) > 0 else 0
            metrics.cvar_10d_95 = metrics.cvar_1d_95 * np.sqrt(10)
            metrics.cvar_10d_99 = metrics.cvar_1d_99 * np.sqrt(10)
            
            # Volatility metrics
            metrics.realized_volatility = returns.std() * np.sqrt(252)
            metrics.ewma_volatility = self._calculate_ewma_volatility(returns)
            
            # Drawdown metrics
            cumulative = (1 + returns).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            
            metrics.max_drawdown = drawdown.min()
            metrics.avg_drawdown = drawdown[drawdown < 0].mean() if (drawdown < 0).any() else 0
            
            # Tail risk metrics
            metrics.skewness = returns.skew()
            metrics.kurtosis = returns.kurtosis()
            
            # Tail ratio (95th percentile / 5th percentile)
            p95 = returns.quantile(0.95)
            p5 = returns.quantile(0.05)
            metrics.tail_ratio = abs(p95 / p5) if p5 != 0 else 0
            
            # Position-based metrics
            if positions is not None:
                metrics = self._calculate_position_risk_metrics(metrics, positions)
            
            # Risk-adjusted metrics
            metrics.risk_adjusted_return = returns.mean() / returns.std() if returns.std() > 0 else 0
            metrics.ulcer_index = self._calculate_ulcer_index(returns)
            metrics.pain_index = self._calculate_pain_index(returns)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {e}")
            return RiskMetrics()
    
    def _calculate_var_analysis(self, returns: pd.Series) -> VaRAnalysis:
        """Calculate comprehensive VaR analysis"""
        try:
            analysis = VaRAnalysis()
            
            if returns.empty:
                return analysis
            
            # Historical VaR
            analysis.historical_var = {
                '95%_1d': returns.quantile(0.05),
                '99%_1d': returns.quantile(0.01),
                '95%_10d': returns.quantile(0.05) * np.sqrt(10),
                '99%_10d': returns.quantile(0.01) * np.sqrt(10)
            }
            
            # Parametric VaR (assuming normal distribution)
            mean_return = returns.mean()
            std_return = returns.std()
            
            analysis.parametric_var = {
                '95%_1d': mean_return - 1.645 * std_return,
                '99%_1d': mean_return - 2.326 * std_return,
                '95%_10d': mean_return * 10 - 1.645 * std_return * np.sqrt(10),
                '99%_10d': mean_return * 10 - 2.326 * std_return * np.sqrt(10)
            }
            
            # Monte Carlo VaR
            analysis.monte_carlo_var = self._calculate_monte_carlo_var(returns)
            
            # VaR backtesting
            var_95 = analysis.historical_var['95%_1d']
            exceptions = (returns < var_95).sum()
            analysis.var_exceptions = exceptions
            analysis.exception_rate = exceptions / len(returns)
            
            # Kupiec test for VaR model validation
            expected_exceptions = len(returns) * 0.05
            if expected_exceptions > 0:
                lr_stat = 2 * (exceptions * np.log(analysis.exception_rate / 0.05) + 
                              (len(returns) - exceptions) * np.log((1 - analysis.exception_rate) / 0.95))
                analysis.kupiec_test_pvalue = 1 - stats.chi2.cdf(lr_stat, 1)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error calculating VaR analysis: {e}")
            return VaRAnalysis()
    
    def _perform_stress_tests(self, returns: pd.Series, positions: Optional[pd.DataFrame] = None) -> StressTestResults:
        """Perform comprehensive stress tests"""
        try:
            results = StressTestResults()
            
            if returns.empty:
                return results
            
            # Historical scenario stress tests
            for scenario_name, shocks in self.stress_scenarios.items():
                # Simple stress test assuming portfolio behaves like equity
                stressed_return = shocks.get('equity', 0)
                results.scenario_results[scenario_name] = stressed_return
            
            # Find worst case scenario
            if results.scenario_results:
                worst_scenario = min(results.scenario_results.items(), key=lambda x: x[1])
                results.worst_case_scenario = worst_scenario[0]
                results.worst_case_loss = worst_scenario[1]
            
            # Historical scenarios (worst periods)
            rolling_returns = returns.rolling(21).sum()  # 1-month periods
            worst_periods = rolling_returns.nsmallest(5)
            
            for i, (date, ret) in enumerate(worst_periods.items()):
                results.historical_scenarios[f'worst_period_{i+1}'] = ret
            
            # Factor stress tests
            results.factor_stress = {
                'volatility_shock_2x': self._stress_test_volatility(returns, 2.0),
                'volatility_shock_3x': self._stress_test_volatility(returns, 3.0),
                'correlation_shock': self._stress_test_correlation(returns),
                'liquidity_shock': self._stress_test_liquidity(returns)
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error performing stress tests: {e}")
            return StressTestResults()
    
    def _analyze_drawdowns(self, returns: pd.Series) -> DrawdownAnalysis:
        """Analyze drawdown characteristics"""
        try:
            analysis = DrawdownAnalysis()
            
            if returns.empty:
                return analysis
            
            # Calculate drawdown series
            cumulative = (1 + returns).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            
            analysis.underwater_curve = drawdown
            analysis.max_drawdown = drawdown.min()
            
            # Find drawdown periods
            in_drawdown = drawdown < 0
            drawdown_periods = []
            
            start_idx = None
            for i, is_dd in enumerate(in_drawdown):
                if is_dd and start_idx is None:
                    start_idx = i
                elif not is_dd and start_idx is not None:
                    end_idx = i - 1
                    period_drawdown = drawdown.iloc[start_idx:end_idx+1]
                    
                    drawdown_periods.append({
                        'start_date': drawdown.index[start_idx],
                        'end_date': drawdown.index[end_idx],
                        'duration': end_idx - start_idx + 1,
                        'max_drawdown': period_drawdown.min(),
                        'recovery_date': drawdown.index[i] if i < len(drawdown) else None
                    })
                    
                    start_idx = None
            
            analysis.drawdown_periods = drawdown_periods
            
            # Calculate statistics
            if drawdown_periods:
                drawdowns = [period['max_drawdown'] for period in drawdown_periods]
                durations = [period['duration'] for period in drawdown_periods]
                
                analysis.avg_drawdown = np.mean(drawdowns)
                analysis.max_duration = max(durations)
                analysis.avg_duration = np.mean(durations)
                
                # Recovery factor
                total_return = cumulative.iloc[-1] - 1
                analysis.recovery_factor = total_return / abs(analysis.max_drawdown) if analysis.max_drawdown != 0 else 0
            
            # Drawdown distribution
            analysis.drawdown_distribution = {
                'mean': drawdown[drawdown < 0].mean() if (drawdown < 0).any() else 0,
                'std': drawdown[drawdown < 0].std() if (drawdown < 0).any() else 0,
                '5th_percentile': drawdown.quantile(0.05),
                '25th_percentile': drawdown.quantile(0.25),
                '75th_percentile': drawdown.quantile(0.75),
                '95th_percentile': drawdown.quantile(0.95)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing drawdowns: {e}")
            return DrawdownAnalysis()
    
    def _calculate_risk_attribution(self, returns: pd.Series, positions: Optional[pd.DataFrame] = None, 
                                  market_data: Optional[Dict[str, pd.DataFrame]] = None) -> RiskAttribution:
        """Calculate risk attribution"""
        try:
            attribution = RiskAttribution()
            
            if returns.empty:
                return attribution
            
            # Simple factor model if market data available
            if market_data:
                attribution = self._factor_risk_attribution(returns, market_data)
            
            # Position-based attribution if positions available
            if positions is not None:
                attribution = self._position_risk_attribution(attribution, positions)
            
            return attribution
            
        except Exception as e:
            logger.error(f"Error calculating risk attribution: {e}")
            return RiskAttribution()
    
    def _calculate_ewma_volatility(self, returns: pd.Series, lambda_param: float = 0.94) -> float:
        """Calculate EWMA volatility"""
        try:
            if len(returns) < 2:
                return 0.0
            
            # Initialize with first return squared
            ewma_var = returns.iloc[0] ** 2
            
            # Calculate EWMA variance
            for ret in returns.iloc[1:]:
                ewma_var = lambda_param * ewma_var + (1 - lambda_param) * ret ** 2
            
            return np.sqrt(ewma_var * 252)  # Annualized
            
        except Exception as e:
            logger.error(f"Error calculating EWMA volatility: {e}")
            return 0.0
    
    def _calculate_position_risk_metrics(self, metrics: RiskMetrics, positions: pd.DataFrame) -> RiskMetrics:
        """Calculate position-based risk metrics"""
        try:
            if positions.empty:
                return metrics
            
            # Concentration metrics
            latest_positions = positions.iloc[-1].abs()
            
            # Herfindahl index for concentration
            weights_squared = (latest_positions ** 2).sum()
            metrics.concentration_index = weights_squared
            metrics.effective_positions = 1 / weights_squared if weights_squared > 0 else 0
            
            # Leverage metrics
            metrics.gross_leverage = latest_positions.sum()
            metrics.net_leverage = positions.iloc[-1].sum()
            
            # Correlation analysis (if multiple positions)
            if len(latest_positions) > 1:
                position_returns = positions.pct_change().dropna()
                if not position_returns.empty:
                    corr_matrix = position_returns.corr()
                    
                    # Average correlation (excluding diagonal)
                    mask = ~np.eye(corr_matrix.shape[0], dtype=bool)
                    metrics.avg_correlation = corr_matrix.values[mask].mean()
                    metrics.max_correlation = corr_matrix.values[mask].max()
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating position risk metrics: {e}")
            return metrics
    
    def _calculate_monte_carlo_var(self, returns: pd.Series, n_simulations: int = 10000) -> Dict[str, float]:
        """Calculate Monte Carlo VaR"""
        try:
            if len(returns) < 30:  # Need sufficient data
                return {}
            
            # Fit distribution to returns
            mean_return = returns.mean()
            std_return = returns.std()
            
            # Generate random scenarios
            np.random.seed(42)  # For reproducibility
            simulated_returns = np.random.normal(mean_return, std_return, n_simulations)
            
            return {
                '95%_1d': np.percentile(simulated_returns, 5),
                '99%_1d': np.percentile(simulated_returns, 1),
                '95%_10d': np.percentile(simulated_returns, 5) * np.sqrt(10),
                '99%_10d': np.percentile(simulated_returns, 1) * np.sqrt(10)
            }
            
        except Exception as e:
            logger.error(f"Error calculating Monte Carlo VaR: {e}")
            return {}
    
    def _stress_test_volatility(self, returns: pd.Series, shock_factor: float) -> float:
        """Stress test with volatility shock"""
        try:
            current_vol = returns.std()
            shocked_vol = current_vol * shock_factor
            
            # Assume worst case scenario with high volatility
            return -2.33 * shocked_vol  # 99% VaR with shocked volatility
            
        except Exception as e:
            logger.error(f"Error in volatility stress test: {e}")
            return 0.0
    
    def _stress_test_correlation(self, returns: pd.Series) -> float:
        """Stress test with correlation shock"""
        try:
            # Assume correlations go to 1 in crisis
            current_vol = returns.std()
            return -3.0 * current_vol  # Severe correlation shock scenario
            
        except Exception as e:
            logger.error(f"Error in correlation stress test: {e}")
            return 0.0
    
    def _stress_test_liquidity(self, returns: pd.Series) -> float:
        """Stress test with liquidity shock"""
        try:
            # Assume liquidity dries up, increasing transaction costs
            worst_return = returns.min()
            liquidity_cost = 0.05  # 5% liquidity cost
            return worst_return - liquidity_cost
            
        except Exception as e:
            logger.error(f"Error in liquidity stress test: {e}")
            return 0.0
    
    def _factor_risk_attribution(self, returns: pd.Series, market_data: Dict[str, pd.DataFrame]) -> RiskAttribution:
        """Calculate factor-based risk attribution"""
        try:
            attribution = RiskAttribution()
            
            # Simple factor model with market factor
            if 'market' in market_data:
                market_returns = market_data['market']['close'].pct_change().dropna()
                aligned_returns, aligned_market = returns.align(market_returns, join='inner')
                
                if len(aligned_returns) > 1:
                    # Calculate beta
                    covariance = np.cov(aligned_returns, aligned_market)[0, 1]
                    market_variance = np.var(aligned_market)
                    beta = covariance / market_variance if market_variance > 0 else 0
                    
                    # Risk decomposition
                    systematic_variance = (beta ** 2) * market_variance
                    total_variance = np.var(aligned_returns)
                    idiosyncratic_variance = total_variance - systematic_variance
                    
                    attribution.systematic_risk = np.sqrt(systematic_variance * 252)
                    attribution.idiosyncratic_risk = np.sqrt(max(0, idiosyncratic_variance) * 252)
                    
                    attribution.factor_loadings['market'] = beta
                    attribution.factor_contributions['market'] = systematic_variance / total_variance if total_variance > 0 else 0
                    attribution.factor_contributions['idiosyncratic'] = idiosyncratic_variance / total_variance if total_variance > 0 else 0
            
            return attribution
            
        except Exception as e:
            logger.error(f"Error in factor risk attribution: {e}")
            return RiskAttribution()
    
    def _position_risk_attribution(self, attribution: RiskAttribution, positions: pd.DataFrame) -> RiskAttribution:
        """Calculate position-based risk attribution"""
        try:
            if positions.empty:
                return attribution
            
            # Calculate position contributions to risk
            position_returns = positions.pct_change().dropna()
            
            if not position_returns.empty:
                # Calculate covariance matrix
                cov_matrix = position_returns.cov() * 252  # Annualized
                
                # Latest weights
                weights = positions.iloc[-1]
                
                # Portfolio variance
                portfolio_variance = np.dot(weights, np.dot(cov_matrix, weights))
                
                # Marginal contributions to risk
                marginal_contrib = np.dot(cov_matrix, weights)
                
                # Component contributions
                component_contrib = weights * marginal_contrib
                
                # Normalize to percentages
                if portfolio_variance > 0:
                    for asset in weights.index:
                        attribution.asset_contributions[asset] = component_contrib[asset] / portfolio_variance
            
            return attribution
            
        except Exception as e:
            logger.error(f"Error in position risk attribution: {e}")
            return attribution
    
    def _calculate_ulcer_index(self, returns: pd.Series) -> float:
        """Calculate Ulcer Index"""
        try:
            cumulative = (1 + returns).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            
            # Ulcer Index is RMS of drawdowns
            return np.sqrt((drawdown ** 2).mean())
            
        except Exception as e:
            logger.error(f"Error calculating Ulcer Index: {e}")
            return 0.0
    
    def _calculate_pain_index(self, returns: pd.Series) -> float:
        """Calculate Pain Index"""
        try:
            cumulative = (1 + returns).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            
            # Pain Index is average of absolute drawdowns
            return abs(drawdown).mean()
            
        except Exception as e:
            logger.error(f"Error calculating Pain Index: {e}")
            return 0.0
    
    def generate_risk_report(self, risk_metrics: RiskMetrics, var_analysis: VaRAnalysis, 
                           stress_results: StressTestResults, drawdown_analysis: DrawdownAnalysis) -> str:
        """Generate comprehensive risk report"""
        try:
            report = f"""
RISK ANALYSIS REPORT
===================

Value at Risk:
- VaR (95%, 1d): {risk_metrics.var_1d_95:.2%}
- VaR (99%, 1d): {risk_metrics.var_1d_99:.2%}
- CVaR (95%, 1d): {risk_metrics.cvar_1d_95:.2%}
- CVaR (99%, 1d): {risk_metrics.cvar_1d_99:.2%}

Volatility Metrics:
- Realized Volatility: {risk_metrics.realized_volatility:.2%}
- EWMA Volatility: {risk_metrics.ewma_volatility:.2%}

Drawdown Analysis:
- Maximum Drawdown: {risk_metrics.max_drawdown:.2%}
- Average Drawdown: {risk_metrics.avg_drawdown:.2%}
- Max DD Duration: {risk_metrics.drawdown_duration} days
- Recovery Factor: {drawdown_analysis.recovery_factor:.2f}

Tail Risk:
- Skewness: {risk_metrics.skewness:.3f}
- Kurtosis: {risk_metrics.kurtosis:.3f}
- Tail Ratio: {risk_metrics.tail_ratio:.2f}

Stress Test Results:
- Worst Case Scenario: {stress_results.worst_case_scenario}
- Worst Case Loss: {stress_results.worst_case_loss:.2%}

Risk-Adjusted Metrics:
- Ulcer Index: {risk_metrics.ulcer_index:.3f}
- Pain Index: {risk_metrics.pain_index:.3f}
"""
            
            if var_analysis.var_exceptions > 0:
                report += f"""
VaR Model Validation:
- VaR Exceptions: {var_analysis.var_exceptions}
- Exception Rate: {var_analysis.exception_rate:.2%}
- Kupiec Test p-value: {var_analysis.kupiec_test_pvalue:.4f}
"""
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating risk report: {e}")
            return "Error generating risk report"