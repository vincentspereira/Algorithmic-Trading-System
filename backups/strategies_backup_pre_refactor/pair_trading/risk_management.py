#!/usr/bin/env python3
"""
Pairs Trading Risk Management

Comprehensive risk management system for pairs trading strategies including:
- Position sizing and exposure management
- Dynamic risk controls and limits
- Portfolio-level risk monitoring
- Stress testing and scenario analysis
- Real-time risk metrics calculation
- Correlation risk management

Key Features:
- Multi-level risk controls (position, pair, portfolio)
- Dynamic position sizing based on volatility and correlation
- Real-time exposure monitoring and alerts
- Stress testing with Monte Carlo simulations
- Correlation breakdown detection
- Maximum drawdown controls
- Sector and geographic exposure limits
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union, NamedTuple
from dataclasses import dataclass, field
from enum import Enum
import warnings
from datetime import datetime, timedelta
import logging
from abc import ABC, abstractmethod
from scipy import stats
from scipy.optimize import minimize

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk level classifications."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"


class AlertType(Enum):
    """Types of risk alerts."""
    EXPOSURE_LIMIT = "exposure_limit"
    CORRELATION_BREAKDOWN = "correlation_breakdown"
    VOLATILITY_SPIKE = "volatility_spike"
    DRAWDOWN_LIMIT = "drawdown_limit"
    CONCENTRATION_RISK = "concentration_risk"
    LIQUIDITY_RISK = "liquidity_risk"
    MARGIN_CALL = "margin_call"


@dataclass
class RiskMetrics:
    """Risk metrics for a position or portfolio."""
    var_95: float  # Value at Risk (95% confidence)
    var_99: float  # Value at Risk (99% confidence)
    expected_shortfall: float  # Conditional VaR
    max_drawdown: float
    volatility: float
    sharpe_ratio: float
    beta: float
    correlation: float
    exposure: float
    leverage: float
    liquidity_score: float
    concentration_score: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class RiskAlert:
    """Risk alert notification."""
    alert_type: AlertType
    severity: RiskLevel
    message: str
    current_value: float
    threshold: float
    pair_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)


@dataclass
class RiskLimits:
    """Risk limits configuration."""
    # Position limits
    max_position_size: float = 0.1  # 10% of portfolio per position
    max_pair_exposure: float = 0.2  # 20% of portfolio per pair
    max_sector_exposure: float = 0.3  # 30% per sector
    max_geographic_exposure: float = 0.4  # 40% per geography
    
    # Portfolio limits
    max_total_exposure: float = 1.0  # 100% total exposure
    max_leverage: float = 2.0  # 2:1 leverage
    max_correlation_exposure: float = 0.5  # 50% in correlated positions
    
    # Risk metrics limits
    max_portfolio_var: float = 0.05  # 5% daily VaR
    max_drawdown: float = 0.15  # 15% maximum drawdown
    min_liquidity_score: float = 0.6  # Minimum liquidity requirement
    max_concentration: float = 0.25  # 25% maximum concentration
    
    # Correlation limits
    min_correlation: float = 0.3  # Minimum correlation for pairs
    max_correlation: float = 0.95  # Maximum correlation (avoid perfect correlation)
    correlation_breakdown_threshold: float = 0.2  # Alert if correlation drops by 20%
    
    # Volatility limits
    max_volatility_ratio: float = 3.0  # Max 3x normal volatility
    volatility_lookback: int = 30  # Days for volatility calculation


class PositionSizer:
    """Dynamic position sizing based on risk metrics."""
    
    def __init__(self, risk_limits: RiskLimits):
        self.risk_limits = risk_limits
    
    def calculate_optimal_size(self,
                             expected_return: float,
                             volatility: float,
                             correlation: float,
                             portfolio_value: float,
                             current_exposure: float,
                             risk_free_rate: float = 0.02) -> float:
        """Calculate optimal position size using Kelly Criterion with risk adjustments.
        
        Args:
            expected_return: Expected return of the position
            volatility: Position volatility
            correlation: Correlation with existing positions
            portfolio_value: Total portfolio value
            current_exposure: Current portfolio exposure
            risk_free_rate: Risk-free rate
            
        Returns:
            Optimal position size as fraction of portfolio
        """
        try:
            if volatility <= 0:
                return 0.0
            
            # Kelly Criterion base calculation
            excess_return = expected_return - risk_free_rate
            kelly_fraction = excess_return / (volatility ** 2)
            
            # Apply risk adjustments
            
            # 1. Correlation adjustment (reduce size for high correlation)
            correlation_adjustment = 1.0 - min(abs(correlation) * 0.5, 0.5)
            
            # 2. Volatility adjustment (reduce size for high volatility)
            volatility_adjustment = min(1.0, 0.2 / volatility)  # Target 20% volatility
            
            # 3. Exposure adjustment (reduce size as exposure increases)
            exposure_adjustment = max(0.1, 1.0 - current_exposure / self.risk_limits.max_total_exposure)
            
            # 4. Apply maximum position limit
            adjusted_size = kelly_fraction * correlation_adjustment * volatility_adjustment * exposure_adjustment
            final_size = min(abs(adjusted_size), self.risk_limits.max_position_size)
            
            return final_size if adjusted_size >= 0 else -final_size
        
        except Exception as e:
            logger.warning(f"Error calculating optimal position size: {e}")
            return 0.0
    
    def calculate_risk_parity_size(self,
                                 volatilities: List[float],
                                 correlations: np.ndarray,
                                 target_risk: float = 0.1) -> List[float]:
        """Calculate risk parity position sizes.
        
        Args:
            volatilities: List of position volatilities
            correlations: Correlation matrix
            target_risk: Target portfolio risk
            
        Returns:
            List of position sizes
        """
        try:
            n_assets = len(volatilities)
            if n_assets == 0:
                return []
            
            # Equal risk contribution target
            target_contrib = target_risk / n_assets
            
            # Initial equal weights
            weights = np.ones(n_assets) / n_assets
            
            # Optimize for equal risk contribution
            def risk_contrib_objective(w):
                portfolio_vol = np.sqrt(np.dot(w, np.dot(correlations * np.outer(volatilities, volatilities), w)))
                risk_contribs = w * np.dot(correlations * np.outer(volatilities, volatilities), w) / portfolio_vol
                return np.sum((risk_contribs - target_contrib) ** 2)
            
            # Constraints
            constraints = [
                {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0},  # Weights sum to 1
                {'type': 'ineq', 'fun': lambda w: w}  # Non-negative weights
            ]
            
            # Bounds
            bounds = [(0, self.risk_limits.max_position_size) for _ in range(n_assets)]
            
            # Optimize
            result = minimize(risk_contrib_objective, weights, method='SLSQP', 
                            bounds=bounds, constraints=constraints)
            
            if result.success:
                return result.x.tolist()
            else:
                return [1.0 / n_assets] * n_assets
        
        except Exception as e:
            logger.warning(f"Error calculating risk parity sizes: {e}")
            return [1.0 / len(volatilities)] * len(volatilities)


class RiskMonitor:
    """Real-time risk monitoring and alerting system."""
    
    def __init__(self, risk_limits: RiskLimits):
        self.risk_limits = risk_limits
        self.alerts: List[RiskAlert] = []
        self.risk_history: List[RiskMetrics] = []
    
    def calculate_var(self,
                     returns: pd.Series,
                     confidence_levels: List[float] = [0.95, 0.99],
                     method: str = 'historical') -> Dict[str, float]:
        """Calculate Value at Risk using different methods.
        
        Args:
            returns: Return series
            confidence_levels: Confidence levels for VaR calculation
            method: Method to use ('historical', 'parametric', 'monte_carlo')
            
        Returns:
            Dictionary of VaR values
        """
        try:
            if len(returns) < 30:
                return {f'var_{int(cl*100)}': 0.0 for cl in confidence_levels}
            
            var_results = {}
            
            if method == 'historical':
                for cl in confidence_levels:
                    var_results[f'var_{int(cl*100)}'] = -np.percentile(returns, (1-cl)*100)
            
            elif method == 'parametric':
                mean_return = returns.mean()
                std_return = returns.std()
                for cl in confidence_levels:
                    z_score = stats.norm.ppf(1-cl)
                    var_results[f'var_{int(cl*100)}'] = -(mean_return + z_score * std_return)
            
            elif method == 'monte_carlo':
                # Monte Carlo simulation
                mean_return = returns.mean()
                std_return = returns.std()
                n_simulations = 10000
                
                simulated_returns = np.random.normal(mean_return, std_return, n_simulations)
                for cl in confidence_levels:
                    var_results[f'var_{int(cl*100)}'] = -np.percentile(simulated_returns, (1-cl)*100)
            
            return var_results
        
        except Exception as e:
            logger.warning(f"Error calculating VaR: {e}")
            return {f'var_{int(cl*100)}': 0.0 for cl in confidence_levels}
    
    def calculate_expected_shortfall(self,
                                   returns: pd.Series,
                                   confidence_level: float = 0.95) -> float:
        """Calculate Expected Shortfall (Conditional VaR).
        
        Args:
            returns: Return series
            confidence_level: Confidence level
            
        Returns:
            Expected Shortfall value
        """
        try:
            if len(returns) < 30:
                return 0.0
            
            var_threshold = -np.percentile(returns, (1-confidence_level)*100)
            tail_returns = returns[returns <= -var_threshold]
            
            if len(tail_returns) > 0:
                return -tail_returns.mean()
            else:
                return var_threshold
        
        except Exception as e:
            logger.warning(f"Error calculating Expected Shortfall: {e}")
            return 0.0
    
    def calculate_maximum_drawdown(self, prices: pd.Series) -> Tuple[float, datetime, datetime]:
        """Calculate maximum drawdown and its duration.
        
        Args:
            prices: Price series
            
        Returns:
            Tuple of (max_drawdown, start_date, end_date)
        """
        try:
            if len(prices) < 2:
                return 0.0, datetime.now(), datetime.now()
            
            # Calculate cumulative returns
            cumulative = (1 + prices.pct_change().fillna(0)).cumprod()
            
            # Calculate running maximum
            running_max = cumulative.expanding().max()
            
            # Calculate drawdown
            drawdown = (cumulative - running_max) / running_max
            
            # Find maximum drawdown
            max_dd_idx = drawdown.idxmin()
            max_drawdown = drawdown.min()
            
            # Find start of drawdown period
            start_idx = running_max[:max_dd_idx].idxmax()
            
            # Find end of drawdown period (recovery)
            recovery_mask = cumulative[max_dd_idx:] >= running_max.loc[max_dd_idx]
            if recovery_mask.any():
                end_idx = cumulative[max_dd_idx:][recovery_mask].index[0]
            else:
                end_idx = cumulative.index[-1]
            
            return abs(max_drawdown), start_idx, end_idx
        
        except Exception as e:
            logger.warning(f"Error calculating maximum drawdown: {e}")
            return 0.0, datetime.now(), datetime.now()
    
    def calculate_portfolio_metrics(self,
                                  positions: Dict,
                                  prices: Dict[str, pd.Series],
                                  benchmark: Optional[pd.Series] = None) -> RiskMetrics:
        """Calculate comprehensive portfolio risk metrics.
        
        Args:
            positions: Dictionary of positions {symbol: quantity}
            prices: Dictionary of price series {symbol: prices}
            benchmark: Optional benchmark series for beta calculation
            
        Returns:
            RiskMetrics object
        """
        try:
            if not positions or not prices:
                return RiskMetrics(
                    var_95=0.0, var_99=0.0, expected_shortfall=0.0,
                    max_drawdown=0.0, volatility=0.0, sharpe_ratio=0.0,
                    beta=0.0, correlation=0.0, exposure=0.0, leverage=0.0,
                    liquidity_score=1.0, concentration_score=0.0
                )
            
            # Calculate portfolio returns
            portfolio_values = []
            common_dates = None
            
            for symbol, quantity in positions.items():
                if symbol in prices and len(prices[symbol]) > 0:
                    if common_dates is None:
                        common_dates = prices[symbol].index
                    else:
                        common_dates = common_dates.intersection(prices[symbol].index)
            
            if common_dates is None or len(common_dates) < 30:
                return RiskMetrics(
                    var_95=0.0, var_99=0.0, expected_shortfall=0.0,
                    max_drawdown=0.0, volatility=0.0, sharpe_ratio=0.0,
                    beta=0.0, correlation=0.0, exposure=0.0, leverage=0.0,
                    liquidity_score=1.0, concentration_score=0.0
                )
            
            # Calculate portfolio value series
            portfolio_series = pd.Series(0.0, index=common_dates)
            total_abs_exposure = 0.0
            
            for symbol, quantity in positions.items():
                if symbol in prices:
                    aligned_prices = prices[symbol].reindex(common_dates).fillna(method='ffill')
                    portfolio_series += quantity * aligned_prices
                    total_abs_exposure += abs(quantity * aligned_prices.iloc[-1])
            
            # Calculate returns
            portfolio_returns = portfolio_series.pct_change().dropna()
            
            if len(portfolio_returns) < 30:
                return RiskMetrics(
                    var_95=0.0, var_99=0.0, expected_shortfall=0.0,
                    max_drawdown=0.0, volatility=0.0, sharpe_ratio=0.0,
                    beta=0.0, correlation=0.0, exposure=0.0, leverage=0.0,
                    liquidity_score=1.0, concentration_score=0.0
                )
            
            # Calculate VaR
            var_results = self.calculate_var(portfolio_returns)
            
            # Calculate Expected Shortfall
            expected_shortfall = self.calculate_expected_shortfall(portfolio_returns)
            
            # Calculate Maximum Drawdown
            max_drawdown, _, _ = self.calculate_maximum_drawdown(portfolio_series)
            
            # Calculate volatility (annualized)
            volatility = portfolio_returns.std() * np.sqrt(252)
            
            # Calculate Sharpe ratio
            excess_returns = portfolio_returns - 0.02/252  # Assume 2% risk-free rate
            sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252) if excess_returns.std() > 0 else 0.0
            
            # Calculate beta and correlation with benchmark
            beta = 0.0
            correlation = 0.0
            if benchmark is not None and len(benchmark) > 0:
                benchmark_aligned = benchmark.reindex(portfolio_returns.index).fillna(method='ffill')
                benchmark_returns = benchmark_aligned.pct_change().dropna()
                
                if len(benchmark_returns) > 0:
                    common_idx = portfolio_returns.index.intersection(benchmark_returns.index)
                    if len(common_idx) > 30:
                        port_ret_aligned = portfolio_returns.reindex(common_idx)
                        bench_ret_aligned = benchmark_returns.reindex(common_idx)
                        
                        correlation = port_ret_aligned.corr(bench_ret_aligned)
                        if bench_ret_aligned.var() > 0:
                            beta = port_ret_aligned.cov(bench_ret_aligned) / bench_ret_aligned.var()
            
            # Calculate exposure and leverage
            portfolio_value = portfolio_series.iloc[-1]
            exposure = total_abs_exposure / abs(portfolio_value) if portfolio_value != 0 else 0.0
            leverage = exposure  # Simplified leverage calculation
            
            # Calculate liquidity score (simplified)
            liquidity_score = 1.0  # Would need volume data for proper calculation
            
            # Calculate concentration score
            position_weights = []
            for symbol, quantity in positions.items():
                if symbol in prices:
                    position_value = abs(quantity * prices[symbol].iloc[-1])
                    weight = position_value / total_abs_exposure if total_abs_exposure > 0 else 0.0
                    position_weights.append(weight)
            
            # Herfindahl-Hirschman Index for concentration
            concentration_score = sum(w**2 for w in position_weights) if position_weights else 0.0
            
            return RiskMetrics(
                var_95=var_results.get('var_95', 0.0),
                var_99=var_results.get('var_99', 0.0),
                expected_shortfall=expected_shortfall,
                max_drawdown=max_drawdown,
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                beta=beta,
                correlation=correlation,
                exposure=exposure,
                leverage=leverage,
                liquidity_score=liquidity_score,
                concentration_score=concentration_score
            )
        
        except Exception as e:
            logger.warning(f"Error calculating portfolio metrics: {e}")
            return RiskMetrics(
                var_95=0.0, var_99=0.0, expected_shortfall=0.0,
                max_drawdown=0.0, volatility=0.0, sharpe_ratio=0.0,
                beta=0.0, correlation=0.0, exposure=0.0, leverage=0.0,
                liquidity_score=1.0, concentration_score=0.0
            )
    
    def check_risk_limits(self, metrics: RiskMetrics, positions: Dict) -> List[RiskAlert]:
        """Check risk metrics against limits and generate alerts.
        
        Args:
            metrics: Current risk metrics
            positions: Current positions
            
        Returns:
            List of risk alerts
        """
        alerts = []
        
        try:
            # Check VaR limits
            if metrics.var_95 > self.risk_limits.max_portfolio_var:
                alerts.append(RiskAlert(
                    alert_type=AlertType.EXPOSURE_LIMIT,
                    severity=RiskLevel.HIGH,
                    message=f"Portfolio VaR ({metrics.var_95:.2%}) exceeds limit ({self.risk_limits.max_portfolio_var:.2%})",
                    current_value=metrics.var_95,
                    threshold=self.risk_limits.max_portfolio_var
                ))
            
            # Check drawdown limits
            if metrics.max_drawdown > self.risk_limits.max_drawdown:
                alerts.append(RiskAlert(
                    alert_type=AlertType.DRAWDOWN_LIMIT,
                    severity=RiskLevel.EXTREME,
                    message=f"Maximum drawdown ({metrics.max_drawdown:.2%}) exceeds limit ({self.risk_limits.max_drawdown:.2%})",
                    current_value=metrics.max_drawdown,
                    threshold=self.risk_limits.max_drawdown
                ))
            
            # Check leverage limits
            if metrics.leverage > self.risk_limits.max_leverage:
                alerts.append(RiskAlert(
                    alert_type=AlertType.EXPOSURE_LIMIT,
                    severity=RiskLevel.HIGH,
                    message=f"Portfolio leverage ({metrics.leverage:.2f}) exceeds limit ({self.risk_limits.max_leverage:.2f})",
                    current_value=metrics.leverage,
                    threshold=self.risk_limits.max_leverage
                ))
            
            # Check concentration limits
            if metrics.concentration_score > self.risk_limits.max_concentration:
                alerts.append(RiskAlert(
                    alert_type=AlertType.CONCENTRATION_RISK,
                    severity=RiskLevel.MODERATE,
                    message=f"Portfolio concentration ({metrics.concentration_score:.2%}) exceeds limit ({self.risk_limits.max_concentration:.2%})",
                    current_value=metrics.concentration_score,
                    threshold=self.risk_limits.max_concentration
                ))
            
            # Check liquidity limits
            if metrics.liquidity_score < self.risk_limits.min_liquidity_score:
                alerts.append(RiskAlert(
                    alert_type=AlertType.LIQUIDITY_RISK,
                    severity=RiskLevel.MODERATE,
                    message=f"Portfolio liquidity score ({metrics.liquidity_score:.2f}) below minimum ({self.risk_limits.min_liquidity_score:.2f})",
                    current_value=metrics.liquidity_score,
                    threshold=self.risk_limits.min_liquidity_score
                ))
            
            self.alerts.extend(alerts)
            return alerts
        
        except Exception as e:
            logger.warning(f"Error checking risk limits: {e}")
            return []
    
    def stress_test(self,
                   positions: Dict,
                   prices: Dict[str, pd.Series],
                   scenarios: Dict[str, Dict[str, float]]) -> Dict[str, RiskMetrics]:
        """Perform stress testing under various scenarios.
        
        Args:
            positions: Current positions
            prices: Historical price data
            scenarios: Stress test scenarios {scenario_name: {symbol: shock_pct}}
            
        Returns:
            Dictionary of risk metrics for each scenario
        """
        try:
            stress_results = {}
            
            for scenario_name, shocks in scenarios.items():
                # Apply shocks to current prices
                shocked_prices = {}
                for symbol, price_series in prices.items():
                    if len(price_series) > 0:
                        shock = shocks.get(symbol, 0.0)
                        shocked_price = price_series.iloc[-1] * (1 + shock)
                        
                        # Create new series with shocked price
                        new_series = price_series.copy()
                        new_series.iloc[-1] = shocked_price
                        shocked_prices[symbol] = new_series
                
                # Calculate metrics under stress
                stress_metrics = self.calculate_portfolio_metrics(positions, shocked_prices)
                stress_results[scenario_name] = stress_metrics
            
            return stress_results
        
        except Exception as e:
            logger.warning(f"Error performing stress test: {e}")
            return {}


class PairsRiskManager:
    """Comprehensive risk management for pairs trading strategies."""
    
    def __init__(self, risk_limits: Optional[RiskLimits] = None):
        self.risk_limits = risk_limits or RiskLimits()
        self.position_sizer = PositionSizer(self.risk_limits)
        self.risk_monitor = RiskMonitor(self.risk_limits)
        
        # Tracking
        self.correlation_history: Dict[str, List[float]] = {}
        self.volatility_history: Dict[str, List[float]] = {}
        self.last_risk_check: Optional[datetime] = None
    
    def validate_new_position(self,
                            pair_id: str,
                            symbol1: str,
                            symbol2: str,
                            proposed_size: float,
                            current_positions: Dict,
                            prices: Dict[str, pd.Series]) -> Tuple[bool, List[RiskAlert]]:
        """Validate a new position against risk limits.
        
        Args:
            pair_id: Pair identifier
            symbol1: First symbol
            symbol2: Second symbol
            proposed_size: Proposed position size
            current_positions: Current portfolio positions
            prices: Price data
            
        Returns:
            Tuple of (is_valid, alerts)
        """
        try:
            alerts = []
            
            # Check individual position size limit
            if abs(proposed_size) > self.risk_limits.max_position_size:
                alerts.append(RiskAlert(
                    alert_type=AlertType.EXPOSURE_LIMIT,
                    severity=RiskLevel.HIGH,
                    message=f"Proposed position size ({abs(proposed_size):.2%}) exceeds limit ({self.risk_limits.max_position_size:.2%})",
                    current_value=abs(proposed_size),
                    threshold=self.risk_limits.max_position_size,
                    pair_id=pair_id
                ))
            
            # Calculate total exposure with new position
            current_exposure = sum(abs(pos) for pos in current_positions.values())
            new_total_exposure = current_exposure + abs(proposed_size)
            
            if new_total_exposure > self.risk_limits.max_total_exposure:
                alerts.append(RiskAlert(
                    alert_type=AlertType.EXPOSURE_LIMIT,
                    severity=RiskLevel.HIGH,
                    message=f"Total exposure with new position ({new_total_exposure:.2%}) would exceed limit ({self.risk_limits.max_total_exposure:.2%})",
                    current_value=new_total_exposure,
                    threshold=self.risk_limits.max_total_exposure,
                    pair_id=pair_id
                ))
            
            # Check correlation with existing positions
            if symbol1 in prices and symbol2 in prices:
                for existing_symbol in current_positions.keys():
                    if existing_symbol in prices:
                        # Check correlation between new symbols and existing positions
                        corr1 = self._calculate_correlation(prices[symbol1], prices[existing_symbol])
                        corr2 = self._calculate_correlation(prices[symbol2], prices[existing_symbol])
                        
                        if abs(corr1) > 0.8 or abs(corr2) > 0.8:
                            alerts.append(RiskAlert(
                                alert_type=AlertType.CONCENTRATION_RISK,
                                severity=RiskLevel.MODERATE,
                                message=f"High correlation detected between new pair and existing position {existing_symbol}",
                                current_value=max(abs(corr1), abs(corr2)),
                                threshold=0.8,
                                pair_id=pair_id
                            ))
            
            # Determine if position is valid (no HIGH or EXTREME severity alerts)
            is_valid = not any(alert.severity in [RiskLevel.HIGH, RiskLevel.EXTREME] for alert in alerts)
            
            return is_valid, alerts
        
        except Exception as e:
            logger.warning(f"Error validating new position: {e}")
            return False, [RiskAlert(
                alert_type=AlertType.EXPOSURE_LIMIT,
                severity=RiskLevel.HIGH,
                message=f"Error validating position: {e}",
                current_value=0.0,
                threshold=0.0,
                pair_id=pair_id
            )]
    
    def monitor_correlation_breakdown(self,
                                   pair_id: str,
                                   symbol1: str,
                                   symbol2: str,
                                   prices: Dict[str, pd.Series],
                                   lookback_periods: List[int] = [30, 60, 90]) -> List[RiskAlert]:
        """Monitor for correlation breakdown in existing pairs.
        
        Args:
            pair_id: Pair identifier
            symbol1: First symbol
            symbol2: Second symbol
            prices: Price data
            lookback_periods: Periods to check for correlation changes
            
        Returns:
            List of correlation breakdown alerts
        """
        try:
            alerts = []
            
            if symbol1 not in prices or symbol2 not in prices:
                return alerts
            
            # Calculate correlations for different periods
            correlations = {}
            for period in lookback_periods:
                if len(prices[symbol1]) >= period and len(prices[symbol2]) >= period:
                    recent_corr = self._calculate_correlation(
                        prices[symbol1].iloc[-period:],
                        prices[symbol2].iloc[-period:]
                    )
                    correlations[period] = recent_corr
            
            if not correlations:
                return alerts
            
            # Store correlation history
            if pair_id not in self.correlation_history:
                self.correlation_history[pair_id] = []
            
            current_corr = correlations[min(lookback_periods)]
            self.correlation_history[pair_id].append(current_corr)
            
            # Check for significant correlation breakdown
            if len(self.correlation_history[pair_id]) > 1:
                previous_corr = self.correlation_history[pair_id][-2]
                corr_change = abs(current_corr - previous_corr)
                
                if corr_change > self.risk_limits.correlation_breakdown_threshold:
                    severity = RiskLevel.HIGH if corr_change > 0.3 else RiskLevel.MODERATE
                    alerts.append(RiskAlert(
                        alert_type=AlertType.CORRELATION_BREAKDOWN,
                        severity=severity,
                        message=f"Correlation breakdown detected for pair {pair_id}: {previous_corr:.3f} -> {current_corr:.3f}",
                        current_value=corr_change,
                        threshold=self.risk_limits.correlation_breakdown_threshold,
                        pair_id=pair_id,
                        metadata={
                            'previous_correlation': previous_corr,
                            'current_correlation': current_corr,
                            'correlations_by_period': correlations
                        }
                    ))
            
            # Check if correlation falls below minimum threshold
            if abs(current_corr) < self.risk_limits.min_correlation:
                alerts.append(RiskAlert(
                    alert_type=AlertType.CORRELATION_BREAKDOWN,
                    severity=RiskLevel.HIGH,
                    message=f"Correlation for pair {pair_id} ({current_corr:.3f}) below minimum threshold ({self.risk_limits.min_correlation:.3f})",
                    current_value=abs(current_corr),
                    threshold=self.risk_limits.min_correlation,
                    pair_id=pair_id
                ))
            
            return alerts
        
        except Exception as e:
            logger.warning(f"Error monitoring correlation breakdown: {e}")
            return []
    
    def _calculate_correlation(self, series1: pd.Series, series2: pd.Series) -> float:
        """Calculate correlation between two price series."""
        try:
            # Align series
            aligned = pd.concat([series1, series2], axis=1).dropna()
            if len(aligned) < 10:
                return 0.0
            
            # Calculate returns
            returns1 = aligned.iloc[:, 0].pct_change().dropna()
            returns2 = aligned.iloc[:, 1].pct_change().dropna()
            
            if len(returns1) < 5 or len(returns2) < 5:
                return 0.0
            
            return returns1.corr(returns2)
        
        except Exception as e:
            logger.warning(f"Error calculating correlation: {e}")
            return 0.0
    
    def generate_risk_report(self,
                           positions: Dict,
                           prices: Dict[str, pd.Series],
                           benchmark: Optional[pd.Series] = None) -> Dict:
        """Generate comprehensive risk report.
        
        Args:
            positions: Current positions
            prices: Price data
            benchmark: Optional benchmark for comparison
            
        Returns:
            Comprehensive risk report dictionary
        """
        try:
            # Calculate current metrics
            current_metrics = self.risk_monitor.calculate_portfolio_metrics(
                positions, prices, benchmark
            )
            
            # Check risk limits
            alerts = self.risk_monitor.check_risk_limits(current_metrics, positions)
            
            # Stress test scenarios
            stress_scenarios = {
                'market_crash': {symbol: -0.20 for symbol in prices.keys()},  # 20% market crash
                'volatility_spike': {symbol: -0.10 for symbol in prices.keys()},  # 10% volatility spike
                'sector_rotation': {symbol: np.random.uniform(-0.15, 0.15) for symbol in prices.keys()},  # Random sector rotation
            }
            
            stress_results = self.risk_monitor.stress_test(positions, prices, stress_scenarios)
            
            # Compile report
            report = {
                'timestamp': datetime.now(),
                'current_metrics': current_metrics,
                'risk_alerts': alerts,
                'stress_test_results': stress_results,
                'risk_limits': self.risk_limits,
                'position_count': len(positions),
                'total_exposure': sum(abs(pos) for pos in positions.values()),
                'correlation_history': self.correlation_history,
                'recommendations': self._generate_recommendations(current_metrics, alerts)
            }
            
            return report
        
        except Exception as e:
            logger.warning(f"Error generating risk report: {e}")
            return {'error': str(e), 'timestamp': datetime.now()}
    
    def _generate_recommendations(self, metrics: RiskMetrics, alerts: List[RiskAlert]) -> List[str]:
        """Generate risk management recommendations."""
        recommendations = []
        
        try:
            # High VaR recommendations
            if metrics.var_95 > self.risk_limits.max_portfolio_var * 0.8:
                recommendations.append("Consider reducing position sizes to lower portfolio VaR")
            
            # High concentration recommendations
            if metrics.concentration_score > self.risk_limits.max_concentration * 0.8:
                recommendations.append("Diversify portfolio to reduce concentration risk")
            
            # Low Sharpe ratio recommendations
            if metrics.sharpe_ratio < 1.0:
                recommendations.append("Review strategy performance - consider optimizing entry/exit criteria")
            
            # High drawdown recommendations
            if metrics.max_drawdown > self.risk_limits.max_drawdown * 0.7:
                recommendations.append("Implement tighter stop-loss controls to limit drawdowns")
            
            # Alert-based recommendations
            for alert in alerts:
                if alert.alert_type == AlertType.CORRELATION_BREAKDOWN:
                    recommendations.append(f"Review pair {alert.pair_id} - correlation may have broken down")
                elif alert.alert_type == AlertType.EXPOSURE_LIMIT:
                    recommendations.append("Reduce position sizes to comply with exposure limits")
                elif alert.alert_type == AlertType.CONCENTRATION_RISK:
                    recommendations.append("Increase diversification to reduce concentration risk")
            
            return recommendations
        
        except Exception as e:
            logger.warning(f"Error generating recommendations: {e}")
            return ["Unable to generate recommendations due to error"]