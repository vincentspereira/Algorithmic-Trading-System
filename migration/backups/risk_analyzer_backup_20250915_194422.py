"""Risk Analyzer

Comprehensive risk analysis and monitoring system with real-time risk metrics,
stress testing, and regulatory compliance features.
"""

from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
import logging
from scipy import stats
from scipy.optimize import minimize
import warnings
warnings.filterwarnings('ignore')

from .results import BacktestResults, Trade, PortfolioSnapshot
from .config import RiskLimits

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class VaRResult:
    """Value at Risk calculation result"""
    var_95: float
    var_99: float
    cvar_95: float  # Conditional VaR (Expected Shortfall)
    cvar_99: float
    method: str
    confidence_interval: Tuple[float, float]
    

@dataclass
class StressTestResult:
    """Stress test result"""
    scenario_name: str
    portfolio_pnl: float
    portfolio_return: float
    max_drawdown: float
    var_breach: bool
    risk_limit_breach: Dict[str, bool]
    component_pnl: Dict[str, float]
    

@dataclass
class RiskMetrics:
    """Comprehensive risk metrics"""
    # Market Risk
    portfolio_var: VaRResult
    component_var: Dict[str, VaRResult]
    correlation_risk: float
    concentration_risk: float
    
    # Credit Risk
    counterparty_exposure: Dict[str, float]
    credit_var: float
    
    # Liquidity Risk
    liquidity_score: float
    funding_risk: float
    market_impact_cost: float
    
    # Operational Risk
    model_risk: float
    execution_risk: float
    
    # Regulatory Metrics
    leverage_ratio: float
    capital_adequacy: float
    
    # Dynamic Risk
    risk_attribution: Dict[str, float]
    marginal_var: Dict[str, float]
    component_var_contribution: Dict[str, float]
    

@dataclass
class RiskAlert:
    """Risk alert/warning"""
    timestamp: datetime
    alert_type: str  # 'limit_breach', 'var_breach', 'concentration', 'liquidity'
    severity: str  # 'low', 'medium', 'high', 'critical'
    message: str
    current_value: float
    limit_value: float
    recommended_action: str
    

class RiskAnalyzer:
    """Advanced risk analysis and monitoring system"""
    
    def __init__(self, results: BacktestResults, risk_limits: Optional[RiskLimits] = None):
        self.results = results
        self.risk_limits = risk_limits or RiskLimits()
        self.returns = results.returns_series
        self.portfolio_history = results.portfolio_history
        self.trades = results.trades
        
        # Risk calculation cache
        self._var_cache: Dict[str, VaRResult] = {}
        self._stress_test_cache: Dict[str, List[StressTestResult]] = {}
        
        # Alert system
        self.alerts: List[RiskAlert] = []
        
        logger.info(f"Initialized risk analyzer with {len(self.returns)} return observations")
    
    def calculate_var(self, confidence_levels: List[float] = [0.95, 0.99], 
                     method: str = 'historical', 
                     lookback_window: int = 252) -> VaRResult:
        """Calculate Value at Risk using multiple methods
        
        Args:
            confidence_levels: Confidence levels for VaR calculation
            method: VaR method ('historical', 'parametric', 'monte_carlo')
            lookback_window: Lookback window for calculation
        
        Returns:
            VaRResult with VaR and CVaR estimates
        """
        cache_key = f"{method}_{lookback_window}_{'-'.join(map(str, confidence_levels))}"
        if cache_key in self._var_cache:
            return self._var_cache[cache_key]
        
        logger.info(f"Calculating VaR using {method} method")
        
        # Get recent returns
        recent_returns = self.returns.tail(lookback_window)
        
        if len(recent_returns) == 0:
            return VaRResult(0.0, 0.0, 0.0, 0.0, method, (0.0, 0.0))
        
        if method == 'historical':
            var_result = self._calculate_historical_var(recent_returns, confidence_levels)
        elif method == 'parametric':
            var_result = self._calculate_parametric_var(recent_returns, confidence_levels)
        elif method == 'monte_carlo':
            var_result = self._calculate_monte_carlo_var(recent_returns, confidence_levels)
        else:
            raise ValueError(f"Unknown VaR method: {method}")
        
        self._var_cache[cache_key] = var_result
        return var_result
    
    def _calculate_historical_var(self, returns: pd.Series, confidence_levels: List[float]) -> VaRResult:
        """Calculate historical VaR"""
        sorted_returns = returns.sort_values()
        
        var_95 = np.percentile(sorted_returns, (1 - 0.95) * 100)
        var_99 = np.percentile(sorted_returns, (1 - 0.99) * 100)
        
        # Conditional VaR (Expected Shortfall)
        cvar_95 = sorted_returns[sorted_returns <= var_95].mean()
        cvar_99 = sorted_returns[sorted_returns <= var_99].mean()
        
        # Bootstrap confidence interval for VaR
        n_bootstrap = 1000
        bootstrap_vars = []
        
        for _ in range(n_bootstrap):
            bootstrap_sample = returns.sample(n=len(returns), replace=True)
            bootstrap_var = np.percentile(bootstrap_sample, (1 - 0.95) * 100)
            bootstrap_vars.append(bootstrap_var)
        
        confidence_interval = (np.percentile(bootstrap_vars, 2.5), np.percentile(bootstrap_vars, 97.5))
        
        return VaRResult(
            var_95=abs(var_95),
            var_99=abs(var_99),
            cvar_95=abs(cvar_95),
            cvar_99=abs(cvar_99),
            method='historical',
            confidence_interval=confidence_interval
        )
    
    def _calculate_parametric_var(self, returns: pd.Series, confidence_levels: List[float]) -> VaRResult:
        """Calculate parametric VaR assuming normal distribution"""
        mean_return = returns.mean()
        std_return = returns.std()
        
        # Z-scores for confidence levels
        z_95 = stats.norm.ppf(0.05)  # 5th percentile
        z_99 = stats.norm.ppf(0.01)  # 1st percentile
        
        var_95 = abs(mean_return + z_95 * std_return)
        var_99 = abs(mean_return + z_99 * std_return)
        
        # Conditional VaR for normal distribution
        cvar_95 = abs(mean_return - std_return * stats.norm.pdf(z_95) / 0.05)
        cvar_99 = abs(mean_return - std_return * stats.norm.pdf(z_99) / 0.01)
        
        # Confidence interval using standard error
        se_var = std_return / np.sqrt(len(returns))
        confidence_interval = (var_95 - 1.96 * se_var, var_95 + 1.96 * se_var)
        
        return VaRResult(
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            cvar_99=cvar_99,
            method='parametric',
            confidence_interval=confidence_interval
        )
    
    def _calculate_monte_carlo_var(self, returns: pd.Series, confidence_levels: List[float], 
                                  n_simulations: int = 10000) -> VaRResult:
        """Calculate Monte Carlo VaR"""
        # Fit distribution to returns
        mean_return = returns.mean()
        std_return = returns.std()
        
        # Generate random scenarios
        np.random.seed(42)  # For reproducibility
        simulated_returns = np.random.normal(mean_return, std_return, n_simulations)
        
        # Calculate VaR from simulations
        var_95 = abs(np.percentile(simulated_returns, 5))
        var_99 = abs(np.percentile(simulated_returns, 1))
        
        # Conditional VaR
        cvar_95 = abs(simulated_returns[simulated_returns <= -var_95].mean())
        cvar_99 = abs(simulated_returns[simulated_returns <= -var_99].mean())
        
        # Confidence interval from simulation
        confidence_interval = (np.percentile(simulated_returns, 2.5), np.percentile(simulated_returns, 97.5))
        
        return VaRResult(
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            cvar_99=cvar_99,
            method='monte_carlo',
            confidence_interval=confidence_interval
        )
    
    def run_stress_tests(self, scenarios: Optional[Dict[str, Dict[str, float]]] = None) -> List[StressTestResult]:
        """Run comprehensive stress tests
        
        Args:
            scenarios: Custom stress scenarios {scenario_name: {factor: shock}}
        
        Returns:
            List of stress test results
        """
        if scenarios is None:
            scenarios = self._get_default_stress_scenarios()
        
        logger.info(f"Running {len(scenarios)} stress test scenarios")
        
        stress_results = []
        
        for scenario_name, shocks in scenarios.items():
            result = self._run_single_stress_test(scenario_name, shocks)
            stress_results.append(result)
        
        self._stress_test_cache['latest'] = stress_results
        return stress_results
    
    def run_stress_test(self, scenario_name: str = "Market Crash", **kwargs) -> StressTestResult:
        """Run a single stress test scenario (singular method for compatibility)
        
        Args:
            scenario_name: Name of the stress test scenario
            **kwargs: Additional parameters
        
        Returns:
            Single stress test result
        """
        scenarios = self._get_default_stress_scenarios()
        if scenario_name in scenarios:
            return self._run_single_stress_test(scenario_name, scenarios[scenario_name])
        else:
            # Default to market crash scenario
            return self._run_single_stress_test("Market Crash", scenarios["Market Crash"])
    
    def _get_default_stress_scenarios(self) -> Dict[str, Dict[str, float]]:
        """Get default stress test scenarios"""
        return {
            'Market Crash': {
                'equity_shock': -0.20,  # 20% equity decline
                'volatility_shock': 2.0,  # Volatility doubles
                'correlation_shock': 0.8   # Correlations increase to 0.8
            },
            'Interest Rate Shock': {
                'rate_shock': 0.02,  # 200 bps rate increase
                'curve_steepening': 0.01,  # Curve steepens by 100 bps
                'credit_spread_widening': 0.005  # Credit spreads widen by 50 bps
            },
            'Liquidity Crisis': {
                'bid_ask_widening': 3.0,  # Bid-ask spreads triple
                'market_impact_increase': 2.0,  # Market impact doubles
                'funding_cost_increase': 0.01  # Funding costs increase by 100 bps
            },
            'Currency Crisis': {
                'fx_shock': -0.15,  # 15% currency depreciation
                'fx_volatility_shock': 2.5,  # FX volatility increases 2.5x
                'emerging_market_shock': -0.25  # 25% EM decline
            },
            'Credit Crisis': {
                'credit_spread_shock': 0.02,  # Credit spreads widen by 200 bps
                'default_rate_increase': 3.0,  # Default rates triple
                'recovery_rate_decline': -0.20  # Recovery rates decline by 20%
            },
            'Operational Risk': {
                'execution_error_rate': 0.05,  # 5% execution error rate
                'system_downtime': 0.02,  # 2% system downtime
                'model_error': 0.10  # 10% model error
            }
        }
    
    def _run_single_stress_test(self, scenario_name: str, shocks: Dict[str, float]) -> StressTestResult:
        """Run a single stress test scenario"""
        # Get current portfolio value
        current_value = self.portfolio_history['portfolio_value'].iloc[-1] if len(self.portfolio_history) > 0 else 0
        
        # Apply shocks to calculate stressed portfolio value
        stressed_pnl = 0.0
        component_pnl = {}
        
        # Market shock impact
        if 'equity_shock' in shocks:
            equity_exposure = current_value * 0.8  # Assume 80% equity exposure
            equity_pnl = equity_exposure * shocks['equity_shock']
            stressed_pnl += equity_pnl
            component_pnl['equity'] = equity_pnl
        
        # Volatility shock impact (affects options positions)
        if 'volatility_shock' in shocks:
            # Simplified: assume 10% of portfolio in volatility-sensitive instruments
            vol_exposure = current_value * 0.1
            vol_pnl = vol_exposure * (shocks['volatility_shock'] - 1) * 0.5  # Simplified vega impact
            stressed_pnl += vol_pnl
            component_pnl['volatility'] = vol_pnl
        
        # Interest rate shock impact
        if 'rate_shock' in shocks:
            # Simplified duration impact
            duration = 5.0  # Assume average duration of 5 years
            rate_exposure = current_value * 0.2  # Assume 20% fixed income exposure
            rate_pnl = -rate_exposure * duration * shocks['rate_shock']
            stressed_pnl += rate_pnl
            component_pnl['interest_rate'] = rate_pnl
        
        # Currency shock impact
        if 'fx_shock' in shocks:
            fx_exposure = current_value * 0.3  # Assume 30% foreign exposure
            fx_pnl = fx_exposure * shocks['fx_shock']
            stressed_pnl += fx_pnl
            component_pnl['currency'] = fx_pnl
        
        # Credit shock impact
        if 'credit_spread_shock' in shocks:
            credit_exposure = current_value * 0.15  # Assume 15% credit exposure
            credit_duration = 3.0  # Assume average credit duration of 3 years
            credit_pnl = -credit_exposure * credit_duration * shocks['credit_spread_shock']
            stressed_pnl += credit_pnl
            component_pnl['credit'] = credit_pnl
        
        # Liquidity shock impact
        if 'bid_ask_widening' in shocks:
            liquidity_cost = current_value * 0.001 * shocks['bid_ask_widening']  # Increased transaction costs
            stressed_pnl -= liquidity_cost
            component_pnl['liquidity'] = -liquidity_cost
        
        # Calculate stressed portfolio metrics
        stressed_value = current_value + stressed_pnl
        portfolio_return = stressed_pnl / current_value if current_value > 0 else 0
        
        # Calculate stressed drawdown (simplified)
        max_drawdown = abs(min(0, portfolio_return))
        
        # Check for VaR breach
        current_var = self.calculate_var()
        var_breach = abs(portfolio_return) > current_var.var_95
        
        # Check risk limit breaches
        risk_limit_breach = {
            'max_loss': abs(stressed_pnl) > self.risk_limits.max_portfolio_loss,
            'max_drawdown': max_drawdown > self.risk_limits.max_drawdown,
            'var_limit': abs(portfolio_return) > self.risk_limits.var_limit,
            'concentration': False  # Simplified
        }
        
        return StressTestResult(
            scenario_name=scenario_name,
            portfolio_pnl=stressed_pnl,
            portfolio_return=portfolio_return,
            max_drawdown=max_drawdown,
            var_breach=var_breach,
            risk_limit_breach=risk_limit_breach,
            component_pnl=component_pnl
        )
    
    def calculate_comprehensive_risk_metrics(self) -> RiskMetrics:
        """Calculate comprehensive risk metrics"""
        logger.info("Calculating comprehensive risk metrics")
        
        # Market Risk
        portfolio_var = self.calculate_var()
        component_var = self._calculate_component_var()
        correlation_risk = self._calculate_correlation_risk()
        concentration_risk = self._calculate_concentration_risk()
        
        # Credit Risk
        counterparty_exposure = self._calculate_counterparty_exposure()
        credit_var = self._calculate_credit_var()
        
        # Liquidity Risk
        liquidity_score = self._calculate_liquidity_score()
        funding_risk = self._calculate_funding_risk()
        market_impact_cost = self._calculate_market_impact_cost()
        
        # Operational Risk
        model_risk = self._calculate_model_risk()
        execution_risk = self._calculate_execution_risk()
        
        # Regulatory Metrics
        leverage_ratio = self._calculate_leverage_ratio()
        capital_adequacy = self._calculate_capital_adequacy()
        
        # Dynamic Risk
        risk_attribution = self._calculate_risk_attribution()
        marginal_var = self._calculate_marginal_var()
        component_var_contribution = self._calculate_component_var_contribution()
        
        return RiskMetrics(
            portfolio_var=portfolio_var,
            component_var=component_var,
            correlation_risk=correlation_risk,
            concentration_risk=concentration_risk,
            counterparty_exposure=counterparty_exposure,
            credit_var=credit_var,
            liquidity_score=liquidity_score,
            funding_risk=funding_risk,
            market_impact_cost=market_impact_cost,
            model_risk=model_risk,
            execution_risk=execution_risk,
            leverage_ratio=leverage_ratio,
            capital_adequacy=capital_adequacy,
            risk_attribution=risk_attribution,
            marginal_var=marginal_var,
            component_var_contribution=component_var_contribution
        )
    
    def _calculate_component_var(self) -> Dict[str, VaRResult]:
        """Calculate VaR for individual components"""
        # Simplified: assume single component (portfolio)
        return {'portfolio': self.calculate_var()}
    
    def _calculate_correlation_risk(self) -> float:
        """Calculate correlation risk"""
        if len(self.returns) < 63:
            return 0.0
        
        # Calculate rolling correlation with benchmark
        if self.results.benchmark_returns is not None and len(self.results.benchmark_returns) > 0:
            rolling_corr = self.returns.rolling(63).corr(self.results.benchmark_returns)
            correlation_volatility = rolling_corr.std()
            return correlation_volatility
        
        return 0.0
    
    def _calculate_concentration_risk(self) -> float:
        """Calculate concentration risk using Herfindahl index"""
        if not self.results.positions_history:
            return 0.0
        
        latest_positions = self.results.positions_history[-1].positions
        if not latest_positions:
            return 0.0
        
        # Calculate position weights
        total_value = sum(abs(pos.market_value) for pos in latest_positions)
        if total_value == 0:
            return 0.0
        
        weights = [abs(pos.market_value) / total_value for pos in latest_positions]
        herfindahl_index = sum(w**2 for w in weights)
        
        return herfindahl_index
    
    def _calculate_counterparty_exposure(self) -> Dict[str, float]:
        """Calculate counterparty exposure"""
        # Simplified: return empty dict
        return {}
    
    def _calculate_credit_var(self) -> float:
        """Calculate credit VaR"""
        # Simplified: assume no credit risk
        return 0.0
    
    def _calculate_liquidity_score(self) -> float:
        """Calculate liquidity score (0-1, higher is more liquid)"""
        if not self.trades:
            return 1.0
        
        # Calculate average market impact
        market_impacts = [trade.market_impact for trade in self.trades if trade.market_impact > 0]
        if not market_impacts:
            return 1.0
        
        avg_market_impact = np.mean(market_impacts)
        # Convert to liquidity score (inverse relationship)
        liquidity_score = max(0, 1 - avg_market_impact * 100)
        
        return liquidity_score
    
    def _calculate_funding_risk(self) -> float:
        """Calculate funding risk"""
        # Simplified: based on leverage
        leverage = self._calculate_leverage_ratio()
        return max(0, leverage - 1) * 0.1  # 10% funding risk per unit of excess leverage
    
    def _calculate_market_impact_cost(self) -> float:
        """Calculate average market impact cost"""
        if not self.trades:
            return 0.0
        
        market_impacts = [trade.market_impact for trade in self.trades]
        return np.mean(market_impacts) if market_impacts else 0.0
    
    def _calculate_model_risk(self) -> float:
        """Calculate model risk"""
        # Simplified: based on strategy complexity
        return 0.05  # Assume 5% model risk
    
    def _calculate_execution_risk(self) -> float:
        """Calculate execution risk based on slippage"""
        if not self.trades:
            return 0.0
        
        slippages = [trade.slippage for trade in self.trades]
        return np.std(slippages) if slippages else 0.0
    
    def _calculate_leverage_ratio(self) -> float:
        """Calculate leverage ratio"""
        if not self.results.positions_history:
            return 0.0
        
        latest_snapshot = self.results.positions_history[-1]
        return latest_snapshot.leverage
    
    def _calculate_capital_adequacy(self) -> float:
        """Calculate capital adequacy ratio"""
        # Simplified: ratio of cash to total value
        if len(self.portfolio_history) == 0:
            return 1.0
        
        latest_cash = self.portfolio_history['cash'].iloc[-1]
        latest_total = self.portfolio_history['portfolio_value'].iloc[-1]
        
        return latest_cash / latest_total if latest_total > 0 else 1.0
    
    def _calculate_risk_attribution(self) -> Dict[str, float]:
        """Calculate risk attribution by factor"""
        # Simplified risk attribution
        total_var = self.calculate_var().var_95
        
        return {
            'market_risk': total_var * 0.7,
            'specific_risk': total_var * 0.2,
            'operational_risk': total_var * 0.1
        }
    
    def _calculate_marginal_var(self) -> Dict[str, float]:
        """Calculate marginal VaR for each position"""
        # Simplified: return empty dict
        return {}
    
    def _calculate_component_var_contribution(self) -> Dict[str, float]:
        """Calculate component VaR contributions"""
        # Simplified: return empty dict
        return {}
    
    def monitor_risk_limits(self) -> List[RiskAlert]:
        """Monitor risk limits and generate alerts"""
        alerts = []
        current_time = datetime.now()
        
        # Calculate current metrics
        current_var = self.calculate_var()
        current_metrics = self.calculate_comprehensive_risk_metrics()
        
        # Check VaR limit
        if current_var.var_95 > self.risk_limits.var_limit:
            alerts.append(RiskAlert(
                timestamp=current_time,
                alert_type='var_breach',
                severity='high',
                message=f'VaR limit breached: {current_var.var_95:.4f} > {self.risk_limits.var_limit:.4f}',
                current_value=current_var.var_95,
                limit_value=self.risk_limits.var_limit,
                recommended_action='Reduce position sizes or hedge exposure'
            ))
        
        # Check concentration limit
        if current_metrics.concentration_risk > self.risk_limits.max_position_size:
            alerts.append(RiskAlert(
                timestamp=current_time,
                alert_type='concentration',
                severity='medium',
                message=f'Concentration risk high: {current_metrics.concentration_risk:.4f}',
                current_value=current_metrics.concentration_risk,
                limit_value=self.risk_limits.max_position_size,
                recommended_action='Diversify portfolio holdings'
            ))
        
        # Check leverage limit
        if current_metrics.leverage_ratio > self.risk_limits.max_leverage:
            alerts.append(RiskAlert(
                timestamp=current_time,
                alert_type='leverage',
                severity='high',
                message=f'Leverage limit breached: {current_metrics.leverage_ratio:.2f}x > {self.risk_limits.max_leverage:.2f}x',
                current_value=current_metrics.leverage_ratio,
                limit_value=self.risk_limits.max_leverage,
                recommended_action='Reduce leverage by closing positions or adding capital'
            ))
        
        # Check drawdown limit
        if len(self.portfolio_history) > 0:
            current_value = self.portfolio_history['portfolio_value'].iloc[-1]
            peak_value = self.portfolio_history['portfolio_value'].max()
            current_drawdown = (peak_value - current_value) / peak_value
            
            if current_drawdown > self.risk_limits.max_drawdown:
                alerts.append(RiskAlert(
                    timestamp=current_time,
                    alert_type='drawdown',
                    severity='critical',
                    message=f'Drawdown limit breached: {current_drawdown:.4f} > {self.risk_limits.max_drawdown:.4f}',
                    current_value=current_drawdown,
                    limit_value=self.risk_limits.max_drawdown,
                    recommended_action='Consider stopping strategy or reducing risk'
                ))
        
        # Store alerts
        self.alerts.extend(alerts)
        
        return alerts
    
    def generate_risk_report(self) -> Dict[str, Any]:
        """Generate comprehensive risk report"""
        logger.info("Generating comprehensive risk report")
        
        # Calculate all risk metrics
        risk_metrics = self.calculate_comprehensive_risk_metrics()
        
        # Run stress tests
        stress_results = self.run_stress_tests()
        
        # Monitor risk limits
        current_alerts = self.monitor_risk_limits()
        
        # VaR backtesting
        var_backtest = self._backtest_var()
        
        report = {
            'risk_summary': {
                'portfolio_var_95': risk_metrics.portfolio_var.var_95,
                'portfolio_var_99': risk_metrics.portfolio_var.var_99,
                'concentration_risk': risk_metrics.concentration_risk,
                'leverage_ratio': risk_metrics.leverage_ratio,
                'liquidity_score': risk_metrics.liquidity_score
            },
            'detailed_metrics': {
                'market_risk': {
                    'var_95': risk_metrics.portfolio_var.var_95,
                    'var_99': risk_metrics.portfolio_var.var_99,
                    'cvar_95': risk_metrics.portfolio_var.cvar_95,
                    'cvar_99': risk_metrics.portfolio_var.cvar_99,
                    'correlation_risk': risk_metrics.correlation_risk
                },
                'liquidity_risk': {
                    'liquidity_score': risk_metrics.liquidity_score,
                    'funding_risk': risk_metrics.funding_risk,
                    'market_impact_cost': risk_metrics.market_impact_cost
                },
                'operational_risk': {
                    'model_risk': risk_metrics.model_risk,
                    'execution_risk': risk_metrics.execution_risk
                }
            },
            'stress_tests': {
                'scenarios': [{
                    'name': result.scenario_name,
                    'portfolio_pnl': result.portfolio_pnl,
                    'portfolio_return': result.portfolio_return,
                    'var_breach': result.var_breach,
                    'component_pnl': result.component_pnl
                } for result in stress_results]
            },
            'risk_alerts': {
                'current_alerts': len(current_alerts),
                'alert_details': [{
                    'type': alert.alert_type,
                    'severity': alert.severity,
                    'message': alert.message,
                    'recommended_action': alert.recommended_action
                } for alert in current_alerts]
            },
            'var_backtesting': var_backtest,
            'risk_attribution': risk_metrics.risk_attribution
        }
        
        return report
    
    def _backtest_var(self, confidence_level: float = 0.95) -> Dict[str, Any]:
        """Backtest VaR model accuracy"""
        if len(self.returns) < 252:
            return {'status': 'insufficient_data'}
        
        # Rolling VaR calculation
        lookback_window = 252
        var_estimates = []
        actual_returns = []
        
        for i in range(lookback_window, len(self.returns)):
            # Calculate VaR using historical data up to this point
            historical_data = self.returns.iloc[i-lookback_window:i]
            var_estimate = np.percentile(historical_data, (1 - confidence_level) * 100)
            
            # Get actual return for next period
            actual_return = self.returns.iloc[i]
            
            var_estimates.append(abs(var_estimate))
            actual_returns.append(actual_return)
        
        var_estimates = np.array(var_estimates)
        actual_returns = np.array(actual_returns)
        
        # Count VaR breaches
        breaches = np.sum(actual_returns < -var_estimates)
        total_observations = len(actual_returns)
        breach_rate = breaches / total_observations
        expected_breach_rate = 1 - confidence_level
        
        # Kupiec test for VaR accuracy
        from scipy.stats import chi2
        
        if breach_rate > 0 and breach_rate < 1:
            lr_stat = -2 * np.log(
                (expected_breach_rate ** breaches) * ((1 - expected_breach_rate) ** (total_observations - breaches))
            ) + 2 * np.log(
                (breach_rate ** breaches) * ((1 - breach_rate) ** (total_observations - breaches))
            )
            p_value = 1 - chi2.cdf(lr_stat, df=1)
        else:
            lr_stat = np.nan
            p_value = np.nan
        
        return {
            'total_observations': total_observations,
            'breaches': int(breaches),
            'breach_rate': breach_rate,
            'expected_breach_rate': expected_breach_rate,
            'kupiec_lr_stat': lr_stat,
            'kupiec_p_value': p_value,
            'model_accurate': p_value > 0.05 if not np.isnan(p_value) else None
        }
    
    def export_risk_report(self, filepath: str, format: str = 'json'):
        """Export risk report to file
        
        Args:
            filepath: Output file path
            format: Export format ('json', 'excel', 'html')
        """
        report = self.generate_risk_report()
        
        if format == 'json':
            import json
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2, default=str)
        
        elif format == 'excel':
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # Risk summary
                summary_df = pd.DataFrame([report['risk_summary']]).T
                summary_df.to_excel(writer, sheet_name='Risk Summary')
                
                # Stress test results
                if 'stress_tests' in report and 'scenarios' in report['stress_tests']:
                    stress_df = pd.DataFrame(report['stress_tests']['scenarios'])
                    stress_df.to_excel(writer, sheet_name='Stress Tests', index=False)
                
                # Risk alerts
                if 'risk_alerts' in report and 'alert_details' in report['risk_alerts']:
                    alerts_df = pd.DataFrame(report['risk_alerts']['alert_details'])
                    alerts_df.to_excel(writer, sheet_name='Risk Alerts', index=False)
        
        elif format == 'html':
            html_content = self._generate_risk_html_report(report)
            with open(filepath, 'w') as f:
                f.write(html_content)
        
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Risk report exported to {filepath}")
    
    def _generate_risk_html_report(self, report: Dict[str, Any]) -> str:
        """Generate HTML risk report"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Risk Analysis Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .alert-high {{ background-color: #ffebee; }}
                .alert-critical {{ background-color: #ffcdd2; }}
                .section {{ margin: 30px 0; }}
            </style>
        </head>
        <body>
            <h1>Risk Analysis Report</h1>
            
            <div class="section">
                <h2>Risk Summary</h2>
                <table>
        """
        
        # Add risk summary
        for key, value in report['risk_summary'].items():
            if isinstance(value, (int, float)):
                formatted_value = f"{value:.4f}"
            else:
                formatted_value = str(value)
            html += f"<tr><td>{key}</td><td>{formatted_value}</td></tr>"
        
        html += """
                </table>
            </div>
        """
        
        # Add stress test results
        if 'stress_tests' in report and 'scenarios' in report['stress_tests']:
            html += """
            <div class="section">
                <h2>Stress Test Results</h2>
                <table>
                    <tr><th>Scenario</th><th>Portfolio P&L</th><th>Portfolio Return</th><th>VaR Breach</th></tr>
            """
            
            for scenario in report['stress_tests']['scenarios']:
                breach_class = 'alert-high' if scenario['var_breach'] else ''
                html += f"""
                    <tr class="{breach_class}">
                        <td>{scenario['name']}</td>
                        <td>{scenario['portfolio_pnl']:,.2f}</td>
                        <td>{scenario['portfolio_return']:.2%}</td>
                        <td>{'Yes' if scenario['var_breach'] else 'No'}</td>
                    </tr>
                """
            
            html += """
                </table>
            </div>
            """
        
        html += """
        </body>
        </html>
        """
        
        return html