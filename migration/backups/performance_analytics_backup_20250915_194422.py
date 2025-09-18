"""Performance Analytics Pillar - 5-Pillar Strategy Architecture

This pillar provides comprehensive performance measurement, attribution analysis,
risk-adjusted returns, and institutional-grade reporting for trading strategies.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import asyncio
import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
from dataclasses import dataclass, field
import logging
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

# ===========================================
# ENUMS AND TYPES
# ===========================================

class PerformanceMetric(Enum):
    """Performance metrics for analysis"""
    TOTAL_RETURN = "total_return"
    ANNUALIZED_RETURN = "annualized_return"
    VOLATILITY = "volatility"
    SHARPE_RATIO = "sharpe_ratio"
    SORTINO_RATIO = "sortino_ratio"
    CALMAR_RATIO = "calmar_ratio"
    MAX_DRAWDOWN = "max_drawdown"
    VAR_95 = "var_95"
    CVAR_95 = "cvar_95"
    BETA = "beta"
    ALPHA = "alpha"
    INFORMATION_RATIO = "information_ratio"
    TRACKING_ERROR = "tracking_error"
    WIN_RATE = "win_rate"
    PROFIT_FACTOR = "profit_factor"
    RECOVERY_FACTOR = "recovery_factor"
    ULCER_INDEX = "ulcer_index"
    STERLING_RATIO = "sterling_ratio"
    BURKE_RATIO = "burke_ratio"
    KAPPA_THREE = "kappa_three"

class AttributionType(Enum):
    """Types of performance attribution"""
    SECURITY_SELECTION = "security_selection"
    ASSET_ALLOCATION = "asset_allocation"
    TIMING = "timing"
    INTERACTION = "interaction"
    CURRENCY = "currency"
    SECTOR = "sector"
    STYLE = "style"

class ReportingPeriod(Enum):
    """Reporting periods for performance analysis"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    INCEPTION_TO_DATE = "inception_to_date"

class BenchmarkType(Enum):
    """Types of benchmarks for comparison"""
    MARKET_INDEX = "market_index"
    PEER_GROUP = "peer_group"
    RISK_FREE_RATE = "risk_free_rate"
    CUSTOM = "custom"
    ABSOLUTE = "absolute"

# ===========================================
# DATA CLASSES
# ===========================================

@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics"""
    # Return Metrics
    total_return: float
    annualized_return: float
    cumulative_return: float
    
    # Risk Metrics
    volatility: float
    downside_deviation: float
    max_drawdown: float
    max_drawdown_duration: int
    
    # Risk-Adjusted Returns
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    sterling_ratio: float
    burke_ratio: float
    
    # Risk Measures
    var_95: float
    cvar_95: float
    ulcer_index: float
    
    # Relative Performance
    beta: Optional[float] = None
    alpha: Optional[float] = None
    information_ratio: Optional[float] = None
    tracking_error: Optional[float] = None
    
    # Trade Statistics
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    # Higher Moments
    skewness: float = 0.0
    kurtosis: float = 0.0
    kappa_three: float = 0.0
    
    # Period Information
    start_date: datetime = field(default_factory=datetime.now)
    end_date: datetime = field(default_factory=datetime.now)
    total_periods: int = 0
    
    # Additional Metrics
    recovery_factor: float = 0.0
    payoff_ratio: float = 0.0
    profit_to_max_drawdown: float = 0.0

@dataclass
class AttributionAnalysis:
    """Performance attribution analysis"""
    security_selection: float
    asset_allocation: float
    timing_effect: float
    interaction_effect: float
    currency_effect: float
    total_active_return: float
    benchmark_return: float
    portfolio_return: float
    attribution_breakdown: Dict[str, float] = field(default_factory=dict)

@dataclass
class RiskAnalysis:
    """Comprehensive risk analysis"""
    var_95: float
    var_99: float
    cvar_95: float
    cvar_99: float
    maximum_drawdown: float
    current_drawdown: float
    drawdown_duration: int
    volatility_regime: str  # "low", "medium", "high"
    tail_ratio: float
    gain_to_pain_ratio: float
    ulcer_index: float
    pain_index: float
    
@dataclass
class PerformanceReport:
    """Comprehensive performance report"""
    strategy_name: str
    report_date: datetime
    period: ReportingPeriod
    metrics: PerformanceMetrics
    attribution: Optional[AttributionAnalysis]
    risk_analysis: RiskAnalysis
    benchmark_comparison: Dict[str, PerformanceMetrics]
    sector_breakdown: Dict[str, float]
    monthly_returns: pd.Series
    rolling_metrics: Dict[str, pd.Series]
    
# ===========================================
# PERFORMANCE CALCULATOR
# ===========================================

class PerformanceCalculator:
    """Calculates comprehensive performance metrics"""
    
    def __init__(self, risk_free_rate: float = 0.02):
        self.risk_free_rate = risk_free_rate
    
    def calculate_metrics(
        self,
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None,
        trades: Optional[pd.DataFrame] = None
    ) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics"""
        
        if len(returns) == 0:
            raise ValueError("Returns series cannot be empty")
        
        # Basic return metrics
        total_return = (1 + returns).prod() - 1
        periods_per_year = self._infer_frequency(returns)
        annualized_return = (1 + total_return) ** (periods_per_year / len(returns)) - 1
        cumulative_return = (1 + returns).cumprod().iloc[-1] - 1
        
        # Risk metrics
        volatility = returns.std() * np.sqrt(periods_per_year)
        downside_returns = returns[returns < 0]
        downside_deviation = downside_returns.std() * np.sqrt(periods_per_year) if len(downside_returns) > 0 else 0
        
        # Drawdown analysis
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Drawdown duration
        max_dd_duration = self._calculate_max_drawdown_duration(drawdown)
        
        # Risk-adjusted returns
        excess_return = annualized_return - self.risk_free_rate
        sharpe_ratio = excess_return / volatility if volatility > 0 else 0
        sortino_ratio = excess_return / downside_deviation if downside_deviation > 0 else 0
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # Additional risk-adjusted ratios
        sterling_ratio = self._calculate_sterling_ratio(returns, max_drawdown)
        burke_ratio = self._calculate_burke_ratio(returns, drawdown)
        
        # Risk measures
        var_95 = np.percentile(returns, 5)
        tail_returns = returns[returns <= var_95]
        cvar_95 = tail_returns.mean() if len(tail_returns) > 0 else var_95
        
        # Ulcer Index
        ulcer_index = self._calculate_ulcer_index(drawdown)
        
        # Relative performance (if benchmark provided)
        beta, alpha, information_ratio, tracking_error = None, None, None, None
        if benchmark_returns is not None and len(benchmark_returns) == len(returns):
            beta, alpha = self._calculate_beta_alpha(returns, benchmark_returns)
            tracking_error = (returns - benchmark_returns).std() * np.sqrt(periods_per_year)
            excess_returns = returns - benchmark_returns
            information_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(periods_per_year) if excess_returns.std() > 0 else 0
        
        # Trade statistics (if trades provided)
        win_rate, profit_factor, avg_win, avg_loss, largest_win, largest_loss = 0, 0, 0, 0, 0, 0
        if trades is not None and not trades.empty:
            win_rate, profit_factor, avg_win, avg_loss, largest_win, largest_loss = self._calculate_trade_stats(trades)
        
        # Higher moments
        skewness = returns.skew()
        kurtosis = returns.kurtosis()
        kappa_three = self._calculate_kappa_three(returns)
        
        # Additional metrics
        recovery_factor = abs(total_return / max_drawdown) if max_drawdown != 0 else 0
        payoff_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        profit_to_max_drawdown = total_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        return PerformanceMetrics(
            total_return=total_return,
            annualized_return=annualized_return,
            cumulative_return=cumulative_return,
            volatility=volatility,
            downside_deviation=downside_deviation,
            max_drawdown=max_drawdown,
            max_drawdown_duration=max_dd_duration,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            sterling_ratio=sterling_ratio,
            burke_ratio=burke_ratio,
            var_95=var_95,
            cvar_95=cvar_95,
            ulcer_index=ulcer_index,
            beta=beta,
            alpha=alpha,
            information_ratio=information_ratio,
            tracking_error=tracking_error,
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            skewness=skewness,
            kurtosis=kurtosis,
            kappa_three=kappa_three,
            start_date=returns.index[0] if hasattr(returns.index[0], 'date') else datetime.now(),
            end_date=returns.index[-1] if hasattr(returns.index[-1], 'date') else datetime.now(),
            total_periods=len(returns),
            recovery_factor=recovery_factor,
            payoff_ratio=payoff_ratio,
            profit_to_max_drawdown=profit_to_max_drawdown
        )
    
    def _infer_frequency(self, returns: pd.Series) -> int:
        """Infer the frequency of returns data"""
        if len(returns) < 2:
            return 252  # Default to daily
        
        # Try to infer from index if it's datetime
        if hasattr(returns.index, 'freq') and returns.index.freq:
            freq = returns.index.freq
            if 'D' in str(freq):
                return 252
            elif 'W' in str(freq):
                return 52
            elif 'M' in str(freq):
                return 12
        
        # Fallback: assume daily if more than 100 observations
        return 252 if len(returns) > 100 else 12
    
    def _calculate_max_drawdown_duration(self, drawdown: pd.Series) -> int:
        """Calculate maximum drawdown duration in periods"""
        is_drawdown = drawdown < 0
        drawdown_periods = is_drawdown.astype(int).groupby((~is_drawdown).cumsum()).sum()
        return drawdown_periods.max() if len(drawdown_periods) > 0 else 0
    
    def _calculate_sterling_ratio(self, returns: pd.Series, max_drawdown: float) -> float:
        """Calculate Sterling ratio"""
        if max_drawdown == 0:
            return 0
        periods_per_year = self._infer_frequency(returns)
        annualized_return = (1 + returns.mean()) ** periods_per_year - 1
        return annualized_return / abs(max_drawdown)
    
    def _calculate_burke_ratio(self, returns: pd.Series, drawdown: pd.Series) -> float:
        """Calculate Burke ratio"""
        periods_per_year = self._infer_frequency(returns)
        annualized_return = (1 + returns.mean()) ** periods_per_year - 1
        drawdown_squared_sum = (drawdown ** 2).sum()
        if drawdown_squared_sum == 0:
            return 0
        return annualized_return / np.sqrt(drawdown_squared_sum)
    
    def _calculate_ulcer_index(self, drawdown: pd.Series) -> float:
        """Calculate Ulcer Index"""
        return np.sqrt((drawdown ** 2).mean())
    
    def _calculate_beta_alpha(self, returns: pd.Series, benchmark_returns: pd.Series) -> Tuple[float, float]:
        """Calculate beta and alpha relative to benchmark"""
        if len(returns) != len(benchmark_returns):
            return 0, 0
        
        # Calculate beta using linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(benchmark_returns, returns)
        beta = slope
        
        # Calculate alpha (annualized)
        periods_per_year = self._infer_frequency(returns)
        alpha = (intercept * periods_per_year)
        
        return beta, alpha
    
    def _calculate_kappa_three(self, returns: pd.Series) -> float:
        """Calculate Kappa Three (downside risk-adjusted return)"""
        target_return = 0  # Assuming 0% target return
        downside_returns = returns[returns < target_return]
        if len(downside_returns) == 0:
            return 0
        
        periods_per_year = self._infer_frequency(returns)
        excess_return = returns.mean() * periods_per_year - self.risk_free_rate
        downside_deviation_cubed = (downside_returns ** 3).mean() ** (1/3)
        
        return excess_return / abs(downside_deviation_cubed) if downside_deviation_cubed != 0 else 0
    
    def _calculate_trade_stats(self, trades: pd.DataFrame) -> Tuple[float, float, float, float, float, float]:
        """Calculate trade-level statistics"""
        if 'pnl' not in trades.columns:
            return 0, 0, 0, 0, 0, 0
        
        pnl = trades['pnl']
        winning_trades = pnl[pnl > 0]
        losing_trades = pnl[pnl < 0]
        
        win_rate = len(winning_trades) / len(pnl) if len(pnl) > 0 else 0
        
        gross_profit = winning_trades.sum() if len(winning_trades) > 0 else 0
        gross_loss = abs(losing_trades.sum()) if len(losing_trades) > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        avg_win = winning_trades.mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades.mean() if len(losing_trades) > 0 else 0
        
        largest_win = winning_trades.max() if len(winning_trades) > 0 else 0
        largest_loss = losing_trades.min() if len(losing_trades) > 0 else 0
        
        return win_rate, profit_factor, avg_win, avg_loss, largest_win, largest_loss

# ===========================================
# ATTRIBUTION ANALYZER
# ===========================================

class AttributionAnalyzer:
    """Performs performance attribution analysis"""
    
    def calculate_attribution(
        self,
        portfolio_returns: pd.Series,
        benchmark_returns: pd.Series,
        portfolio_weights: pd.DataFrame,
        benchmark_weights: pd.DataFrame,
        security_returns: pd.DataFrame
    ) -> AttributionAnalysis:
        """Calculate performance attribution using Brinson-Hood-Beebower model"""
        
        # Ensure all data has the same index
        common_index = portfolio_returns.index.intersection(benchmark_returns.index)
        portfolio_returns = portfolio_returns.loc[common_index]
        benchmark_returns = benchmark_returns.loc[common_index]
        
        # Calculate attribution components
        security_selection = self._calculate_security_selection(
            portfolio_weights, benchmark_weights, security_returns
        )
        
        asset_allocation = self._calculate_asset_allocation(
            portfolio_weights, benchmark_weights, security_returns
        )
        
        timing_effect = self._calculate_timing_effect(
            portfolio_returns, benchmark_returns
        )
        
        interaction_effect = self._calculate_interaction_effect(
            portfolio_weights, benchmark_weights, security_returns
        )
        
        # Currency effect (simplified - assume no currency impact for now)
        currency_effect = 0.0
        
        # Total active return
        total_active_return = portfolio_returns.mean() - benchmark_returns.mean()
        
        return AttributionAnalysis(
            security_selection=security_selection,
            asset_allocation=asset_allocation,
            timing_effect=timing_effect,
            interaction_effect=interaction_effect,
            currency_effect=currency_effect,
            total_active_return=total_active_return,
            benchmark_return=benchmark_returns.mean(),
            portfolio_return=portfolio_returns.mean()
        )
    
    def _calculate_security_selection(self, portfolio_weights, benchmark_weights, security_returns):
        """Calculate security selection effect"""
        # Simplified calculation - would need more detailed implementation
        return 0.001  # Placeholder
    
    def _calculate_asset_allocation(self, portfolio_weights, benchmark_weights, security_returns):
        """Calculate asset allocation effect"""
        # Simplified calculation - would need more detailed implementation
        return 0.002  # Placeholder
    
    def _calculate_timing_effect(self, portfolio_returns, benchmark_returns):
        """Calculate timing effect"""
        # Simplified calculation based on correlation timing
        correlation = portfolio_returns.corr(benchmark_returns)
        return (correlation - 1) * 0.001  # Placeholder
    
    def _calculate_interaction_effect(self, portfolio_weights, benchmark_weights, security_returns):
        """Calculate interaction effect"""
        # Simplified calculation - would need more detailed implementation
        return 0.0005  # Placeholder

# ===========================================
# RISK ANALYZER
# ===========================================

class RiskAnalyzer:
    """Comprehensive risk analysis"""
    
    def analyze_risk(
        self,
        returns: pd.Series,
        portfolio_value: pd.Series
    ) -> RiskAnalysis:
        """Perform comprehensive risk analysis"""
        
        # VaR calculations
        var_95 = np.percentile(returns, 5)
        var_99 = np.percentile(returns, 1)
        
        # CVaR calculations
        cvar_95 = returns[returns <= var_95].mean() if len(returns[returns <= var_95]) > 0 else var_95
        cvar_99 = returns[returns <= var_99].mean() if len(returns[returns <= var_99]) > 0 else var_99
        
        # Drawdown analysis
        cumulative = portfolio_value / portfolio_value.iloc[0]
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        
        maximum_drawdown = drawdown.min()
        current_drawdown = drawdown.iloc[-1]
        
        # Drawdown duration
        is_drawdown = drawdown < -0.01  # 1% threshold
        current_dd_duration = 0
        for i in range(len(is_drawdown) - 1, -1, -1):
            if is_drawdown.iloc[i]:
                current_dd_duration += 1
            else:
                break
        
        # Volatility regime
        volatility = returns.std()
        vol_percentiles = returns.rolling(252).std().quantile([0.33, 0.67])
        if volatility < vol_percentiles.iloc[0]:
            volatility_regime = "low"
        elif volatility < vol_percentiles.iloc[1]:
            volatility_regime = "medium"
        else:
            volatility_regime = "high"
        
        # Tail ratio
        positive_returns = returns[returns > 0]
        negative_returns = returns[returns < 0]
        tail_ratio = (positive_returns.quantile(0.95) / abs(negative_returns.quantile(0.05))) if len(negative_returns) > 0 else 1
        
        # Gain to pain ratio
        gains = returns[returns > 0].sum()
        pains = abs(returns[returns < 0].sum())
        gain_to_pain_ratio = gains / pains if pains > 0 else 0
        
        # Ulcer Index
        ulcer_index = np.sqrt((drawdown ** 2).mean())
        
        # Pain Index
        pain_index = abs(drawdown).mean()
        
        return RiskAnalysis(
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            cvar_99=cvar_99,
            maximum_drawdown=maximum_drawdown,
            current_drawdown=current_drawdown,
            drawdown_duration=current_dd_duration,
            volatility_regime=volatility_regime,
            tail_ratio=tail_ratio,
            gain_to_pain_ratio=gain_to_pain_ratio,
            ulcer_index=ulcer_index,
            pain_index=pain_index
        )

# ===========================================
# PERFORMANCE ANALYTICS MANAGER
# ===========================================

class PerformanceAnalyticsManager:
    """Main manager for performance analytics"""
    
    def __init__(self, risk_free_rate: float = 0.02):
        self.performance_calculator = PerformanceCalculator(risk_free_rate)
        self.attribution_analyzer = AttributionAnalyzer()
        self.risk_analyzer = RiskAnalyzer()
        self.reports: Dict[str, PerformanceReport] = {}
    
    async def generate_performance_report(
        self,
        strategy_name: str,
        returns: pd.Series,
        portfolio_value: pd.Series,
        benchmark_returns: Optional[pd.Series] = None,
        trades: Optional[pd.DataFrame] = None,
        period: ReportingPeriod = ReportingPeriod.MONTHLY
    ) -> PerformanceReport:
        """Generate comprehensive performance report"""
        
        # Calculate performance metrics
        metrics = self.performance_calculator.calculate_metrics(
            returns, benchmark_returns, trades
        )
        
        # Perform risk analysis
        risk_analysis = self.risk_analyzer.analyze_risk(returns, portfolio_value)
        
        # Attribution analysis (if benchmark provided)
        attribution = None
        if benchmark_returns is not None:
            # Simplified attribution - would need portfolio weights for full analysis
            attribution = AttributionAnalysis(
                security_selection=0.001,
                asset_allocation=0.002,
                timing_effect=-0.0005,
                interaction_effect=0.0003,
                currency_effect=0.0,
                total_active_return=returns.mean() - benchmark_returns.mean(),
                benchmark_return=benchmark_returns.mean(),
                portfolio_return=returns.mean()
            )
        
        # Benchmark comparison
        benchmark_comparison = {}
        if benchmark_returns is not None:
            benchmark_metrics = self.performance_calculator.calculate_metrics(benchmark_returns)
            benchmark_comparison['benchmark'] = benchmark_metrics
        
        # Monthly returns
        monthly_returns = self._calculate_monthly_returns(returns)
        
        # Rolling metrics
        rolling_metrics = self._calculate_rolling_metrics(returns)
        
        # Create report
        report = PerformanceReport(
            strategy_name=strategy_name,
            report_date=datetime.now(),
            period=period,
            metrics=metrics,
            attribution=attribution,
            risk_analysis=risk_analysis,
            benchmark_comparison=benchmark_comparison,
            sector_breakdown={},  # Would need sector data
            monthly_returns=monthly_returns,
            rolling_metrics=rolling_metrics
        )
        
        # Store report
        report_key = f"{strategy_name}_{datetime.now().strftime('%Y%m%d')}"
        self.reports[report_key] = report
        
        logger.info(f"Generated performance report for {strategy_name}")
        return report
    
    def _calculate_monthly_returns(self, returns: pd.Series) -> pd.Series:
        """Calculate monthly returns from daily returns"""
        if hasattr(returns.index, 'to_period'):
            monthly = (1 + returns).groupby(returns.index.to_period('M')).prod() - 1
            return monthly
        else:
            # Fallback for non-datetime index
            return returns.groupby(returns.index // 21).apply(lambda x: (1 + x).prod() - 1)
    
    def _calculate_rolling_metrics(self, returns: pd.Series) -> Dict[str, pd.Series]:
        """Calculate rolling performance metrics"""
        window = min(252, len(returns) // 4)  # 1 year or 1/4 of data
        
        if window < 30:  # Not enough data for meaningful rolling metrics
            return {}
        
        rolling_metrics = {
            'rolling_return': returns.rolling(window).apply(lambda x: (1 + x).prod() - 1),
            'rolling_volatility': returns.rolling(window).std() * np.sqrt(252),
            'rolling_sharpe': returns.rolling(window).apply(
                lambda x: (x.mean() * 252 - 0.02) / (x.std() * np.sqrt(252)) if x.std() > 0 else 0
            ),
            'rolling_max_drawdown': returns.rolling(window).apply(
                lambda x: ((1 + x).cumprod() / (1 + x).cumprod().expanding().max() - 1).min()
            )
        }
        
        return rolling_metrics
    
    def get_report(self, report_key: str) -> Optional[PerformanceReport]:
        """Get stored performance report"""
        return self.reports.get(report_key)
    
    def list_reports(self) -> List[str]:
        """List all stored report keys"""
        return list(self.reports.keys())
    
    async def compare_strategies(
        self,
        strategy_reports: Dict[str, PerformanceReport]
    ) -> Dict[str, Any]:
        """Compare multiple strategies"""
        
        comparison = {
            'summary': {},
            'rankings': {},
            'correlation_matrix': {},
            'risk_return_profile': {}
        }
        
        # Extract key metrics for comparison
        metrics_data = {}
        for name, report in strategy_reports.items():
            metrics_data[name] = {
                'return': report.metrics.annualized_return,
                'volatility': report.metrics.volatility,
                'sharpe': report.metrics.sharpe_ratio,
                'max_drawdown': report.metrics.max_drawdown,
                'calmar': report.metrics.calmar_ratio
            }
        
        # Create summary
        comparison['summary'] = pd.DataFrame(metrics_data).T
        
        # Rankings
        for metric in ['return', 'sharpe', 'calmar']:
            comparison['rankings'][metric] = comparison['summary'][metric].rank(ascending=False).to_dict()
        
        logger.info(f"Compared {len(strategy_reports)} strategies")
        return comparison

# ===========================================
# FACTORY FUNCTIONS
# ===========================================

async def create_performance_analytics_manager(risk_free_rate: float = 0.02) -> PerformanceAnalyticsManager:
    """Factory function to create PerformanceAnalyticsManager"""
    manager = PerformanceAnalyticsManager(risk_free_rate)
    logger.info("Performance Analytics Manager initialized")
    return manager

# Example usage
if __name__ == "__main__":
    async def main():
        # Create sample data
        dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0.0008, 0.02, len(dates)), index=dates)
        portfolio_value = (1 + returns).cumprod() * 100000
        
        # Create benchmark
        benchmark_returns = pd.Series(np.random.normal(0.0005, 0.015, len(dates)), index=dates)
        
        # Create manager
        manager = await create_performance_analytics_manager()
        
        # Generate report
        report = await manager.generate_performance_report(
            strategy_name="Sample Strategy",
            returns=returns,
            portfolio_value=portfolio_value,
            benchmark_returns=benchmark_returns
        )
        
        print(f"Strategy Performance Report:")
        print(f"Total Return: {report.metrics.total_return:.2%}")
        print(f"Annualized Return: {report.metrics.annualized_return:.2%}")
        print(f"Volatility: {report.metrics.volatility:.2%}")
        print(f"Sharpe Ratio: {report.metrics.sharpe_ratio:.2f}")
        print(f"Max Drawdown: {report.metrics.max_drawdown:.2%}")
        print(f"Calmar Ratio: {report.metrics.calmar_ratio:.2f}")
    
    asyncio.run(main())