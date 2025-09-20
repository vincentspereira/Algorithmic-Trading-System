"""Performance Analyzer

Comprehensive performance analysis with advanced metrics, regime analysis,
and institutional-grade reporting capabilities.
"""

from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
import logging
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

from .results import BacktestResults, Trade, PortfolioSnapshot, TradeType
from .metrics import MetricsCalculator, PerformanceMetrics, RiskMetrics

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RegimeAnalysis:
    """Market regime analysis results"""
    regime_periods: Dict[str, List[Tuple[datetime, datetime]]]
    regime_returns: Dict[str, pd.Series]
    regime_metrics: Dict[str, Dict[str, float]]
    regime_transitions: pd.DataFrame
    current_regime: Optional[str] = None
    regime_probabilities: Dict[str, float] = field(default_factory=dict)


@dataclass
class AttributionAnalysis:
    """Performance attribution analysis"""
    factor_returns: pd.DataFrame
    factor_loadings: pd.DataFrame
    specific_returns: pd.Series
    attribution_summary: Dict[str, float]
    r_squared: float
    tracking_error: float


@dataclass
class RiskDecomposition:
    """Risk decomposition analysis"""
    total_risk: float
    systematic_risk: float
    idiosyncratic_risk: float
    factor_contributions: Dict[str, float]
    concentration_risk: float
    liquidity_risk: float
    tail_risk: float


class PerformanceAnalyzer:
    """Advanced performance analysis engine"""
    
    def __init__(self, results: BacktestResults):
        self.results = results
        self.returns = results.returns_series
        self.benchmark_returns = results.benchmark_returns
        self.trades = results.trades
        self.portfolio_history = results.portfolio_history
        
        # Analysis cache
        self._regime_analysis: Optional[RegimeAnalysis] = None
        self._attribution_analysis: Optional[AttributionAnalysis] = None
        self._risk_decomposition: Optional[RiskDecomposition] = None
        
        logger.info(f"Initialized performance analyzer for {len(self.returns)} periods")
    
    def analyze_regimes(self, method: str = 'volatility', 
                       lookback_window: int = 252) -> RegimeAnalysis:
        """Analyze market regimes and strategy performance by regime
        
        Args:
            method: Regime identification method ('volatility', 'trend', 'correlation')
            lookback_window: Lookback window for regime calculation
        
        Returns:
            RegimeAnalysis object with comprehensive regime analysis
        """
        if self._regime_analysis is not None:
            return self._regime_analysis
        
        logger.info(f"Analyzing market regimes using {method} method")
        
        if method == 'volatility':
            regimes = self._identify_volatility_regimes(lookback_window)
        elif method == 'trend':
            regimes = self._identify_trend_regimes(lookback_window)
        elif method == 'correlation':
            regimes = self._identify_correlation_regimes(lookback_window)
        else:
            raise ValueError(f"Unknown regime method: {method}")
        
        # Analyze performance by regime
        regime_periods = self._extract_regime_periods(regimes)
        regime_returns = self._calculate_regime_returns(regime_periods)
        regime_metrics = self._calculate_regime_metrics(regime_returns)
        regime_transitions = self._analyze_regime_transitions(regimes)
        
        # Current regime
        current_regime = regimes.iloc[-1] if len(regimes) > 0 else None
        
        # Regime probabilities (simplified)
        regime_probs = regimes.value_counts(normalize=True).to_dict()
        
        self._regime_analysis = RegimeAnalysis(
            regime_periods=regime_periods,
            regime_returns=regime_returns,
            regime_metrics=regime_metrics,
            regime_transitions=regime_transitions,
            current_regime=current_regime,
            regime_probabilities=regime_probs
        )
        
        return self._regime_analysis
    
    def _identify_volatility_regimes(self, lookback_window: int) -> pd.Series:
        """Identify volatility regimes"""
        # Calculate rolling volatility
        rolling_vol = self.returns.rolling(window=21).std() * np.sqrt(252)
        
        # Calculate long-term volatility percentiles
        vol_percentiles = rolling_vol.rolling(window=lookback_window).quantile([0.33, 0.67])
        
        regimes = pd.Series(index=self.returns.index, dtype=str)
        
        for date in self.returns.index:
            if date in vol_percentiles.index:
                current_vol = rolling_vol.loc[date]
                low_threshold = vol_percentiles.loc[date, 0.33]
                high_threshold = vol_percentiles.loc[date, 0.67]
                
                if pd.isna(current_vol) or pd.isna(low_threshold) or pd.isna(high_threshold):
                    regimes.loc[date] = 'Unknown'
                elif current_vol <= low_threshold:
                    regimes.loc[date] = 'Low Volatility'
                elif current_vol >= high_threshold:
                    regimes.loc[date] = 'High Volatility'
                else:
                    regimes.loc[date] = 'Medium Volatility'
            else:
                regimes.loc[date] = 'Unknown'
        
        return regimes.dropna()
    
    def _identify_trend_regimes(self, lookback_window: int) -> pd.Series:
        """Identify trend regimes"""
        if self.benchmark_returns is None or len(self.benchmark_returns) == 0:
            # Use portfolio returns if no benchmark
            price_series = (1 + self.returns).cumprod()
        else:
            price_series = (1 + self.benchmark_returns).cumprod()
        
        # Calculate trend indicators
        sma_short = price_series.rolling(window=50).mean()
        sma_long = price_series.rolling(window=200).mean()
        
        regimes = pd.Series(index=self.returns.index, dtype=str)
        
        for date in self.returns.index:
            if date in sma_short.index and date in sma_long.index:
                short_ma = sma_short.loc[date]
                long_ma = sma_long.loc[date]
                current_price = price_series.loc[date]
                
                if pd.isna(short_ma) or pd.isna(long_ma) or pd.isna(current_price):
                    regimes.loc[date] = 'Unknown'
                elif current_price > short_ma > long_ma:
                    regimes.loc[date] = 'Bull Market'
                elif current_price < short_ma < long_ma:
                    regimes.loc[date] = 'Bear Market'
                else:
                    regimes.loc[date] = 'Sideways Market'
            else:
                regimes.loc[date] = 'Unknown'
        
        return regimes.dropna()
    
    def _identify_correlation_regimes(self, lookback_window: int) -> pd.Series:
        """Identify correlation regimes"""
        if self.benchmark_returns is None or len(self.benchmark_returns) == 0:
            return pd.Series(index=self.returns.index, data='No Benchmark', dtype=str)
        
        # Calculate rolling correlation
        rolling_corr = self.returns.rolling(window=63).corr(self.benchmark_returns)
        
        regimes = pd.Series(index=self.returns.index, dtype=str)
        
        for date in self.returns.index:
            if date in rolling_corr.index:
                corr = rolling_corr.loc[date]
                
                if pd.isna(corr):
                    regimes.loc[date] = 'Unknown'
                elif corr >= 0.7:
                    regimes.loc[date] = 'High Correlation'
                elif corr <= 0.3:
                    regimes.loc[date] = 'Low Correlation'
                else:
                    regimes.loc[date] = 'Medium Correlation'
            else:
                regimes.loc[date] = 'Unknown'
        
        return regimes.dropna()
    
    def _extract_regime_periods(self, regimes: pd.Series) -> Dict[str, List[Tuple[datetime, datetime]]]:
        """Extract continuous periods for each regime"""
        regime_periods = {}
        
        for regime_name in regimes.unique():
            if regime_name == 'Unknown':
                continue
            
            regime_mask = regimes == regime_name
            periods = []
            
            start_date = None
            for date, is_regime in regime_mask.items():
                if is_regime and start_date is None:
                    start_date = date
                elif not is_regime and start_date is not None:
                    periods.append((start_date, date))
                    start_date = None
            
            # Handle case where regime continues to end
            if start_date is not None:
                periods.append((start_date, regimes.index[-1]))
            
            regime_periods[regime_name] = periods
        
        return regime_periods
    
    def _calculate_regime_returns(self, regime_periods: Dict[str, List[Tuple[datetime, datetime]]]) -> Dict[str, pd.Series]:
        """Calculate returns for each regime"""
        regime_returns = {}
        
        for regime_name, periods in regime_periods.items():
            regime_return_list = []
            
            for start_date, end_date in periods:
                period_returns = self.returns.loc[start_date:end_date]
                regime_return_list.extend(period_returns.tolist())
            
            regime_returns[regime_name] = pd.Series(regime_return_list)
        
        return regime_returns
    
    def _calculate_regime_metrics(self, regime_returns: Dict[str, pd.Series]) -> Dict[str, Dict[str, float]]:
        """Calculate performance metrics for each regime"""
        regime_metrics = {}
        
        for regime_name, returns in regime_returns.items():
            if len(returns) == 0:
                continue
            
            # Calculate basic metrics
            total_return = (1 + returns).prod() - 1
            annualized_return = (1 + total_return) ** (252 / len(returns)) - 1 if len(returns) > 0 else 0
            volatility = returns.std() * np.sqrt(252)
            sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
            
            # Downside metrics
            downside_returns = returns[returns < 0]
            downside_deviation = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
            sortino_ratio = annualized_return / downside_deviation if downside_deviation > 0 else 0
            
            # Drawdown
            cumulative = (1 + returns).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            max_drawdown = drawdown.min()
            
            regime_metrics[regime_name] = {
                'total_return': total_return,
                'annualized_return': annualized_return,
                'volatility': volatility,
                'sharpe_ratio': sharpe_ratio,
                'sortino_ratio': sortino_ratio,
                'max_drawdown': max_drawdown,
                'periods': len(returns),
                'win_rate': (returns > 0).mean(),
                'avg_return': returns.mean(),
                'skewness': returns.skew(),
                'kurtosis': returns.kurtosis()
            }
        
        return regime_metrics
    
    def _analyze_regime_transitions(self, regimes: pd.Series) -> pd.DataFrame:
        """Analyze regime transition patterns"""
        transitions = []
        
        prev_regime = None
        for date, regime in regimes.items():
            if prev_regime is not None and regime != prev_regime:
                transitions.append({
                    'date': date,
                    'from_regime': prev_regime,
                    'to_regime': regime,
                    'return_1d': self.returns.loc[date] if date in self.returns.index else np.nan,
                    'return_5d': self.returns.loc[date:].head(5).sum() if date in self.returns.index else np.nan,
                    'return_21d': self.returns.loc[date:].head(21).sum() if date in self.returns.index else np.nan
                })
            prev_regime = regime
        
        return pd.DataFrame(transitions)
    
    def analyze_attribution(self, factors: Optional[pd.DataFrame] = None) -> AttributionAnalysis:
        """Perform factor-based performance attribution
        
        Args:
            factors: Factor returns DataFrame (if None, uses simple market factor)
        
        Returns:
            AttributionAnalysis object
        """
        if self._attribution_analysis is not None:
            return self._attribution_analysis
        
        logger.info("Performing performance attribution analysis")
        
        if factors is None:
            # Create simple market factor
            if self.benchmark_returns is not None and len(self.benchmark_returns) > 0:
                factors = pd.DataFrame({
                    'Market': self.benchmark_returns
                }, index=self.benchmark_returns.index)
            else:
                # No factors available
                self._attribution_analysis = AttributionAnalysis(
                    factor_returns=pd.DataFrame(),
                    factor_loadings=pd.DataFrame(),
                    specific_returns=pd.Series(dtype=float),
                    attribution_summary={},
                    r_squared=0.0,
                    tracking_error=0.0
                )
                return self._attribution_analysis
        
        # Align data
        common_index = self.returns.index.intersection(factors.index)
        aligned_returns = self.returns.loc[common_index]
        aligned_factors = factors.loc[common_index]
        
        if len(aligned_returns) == 0:
            # No common data
            self._attribution_analysis = AttributionAnalysis(
                factor_returns=pd.DataFrame(),
                factor_loadings=pd.DataFrame(),
                specific_returns=pd.Series(dtype=float),
                attribution_summary={},
                r_squared=0.0,
                tracking_error=0.0
            )
            return self._attribution_analysis
        
        # Perform regression
        from sklearn.linear_model import LinearRegression
        
        X = aligned_factors.values
        y = aligned_returns.values
        
        model = LinearRegression(fit_intercept=True)
        model.fit(X, y)
        
        # Calculate factor loadings
        factor_loadings = pd.Series(model.coef_, index=aligned_factors.columns)
        alpha = model.intercept_
        
        # Calculate predicted returns
        predicted_returns = pd.Series(
            model.predict(X),
            index=aligned_returns.index
        )
        
        # Calculate specific returns (residuals)
        specific_returns = aligned_returns - predicted_returns
        
        # Calculate R-squared
        r_squared = model.score(X, y)
        
        # Calculate tracking error
        tracking_error = specific_returns.std() * np.sqrt(252)
        
        # Attribution summary
        factor_contributions = {}
        for factor_name in aligned_factors.columns:
            factor_return = aligned_factors[factor_name].mean() * 252  # Annualized
            factor_loading = factor_loadings[factor_name]
            contribution = factor_return * factor_loading
            factor_contributions[factor_name] = contribution
        
        attribution_summary = {
            'alpha': alpha * 252,  # Annualized alpha
            'total_factor_contribution': sum(factor_contributions.values()),
            'specific_return': specific_returns.mean() * 252,
            **factor_contributions
        }
        
        # Create factor loadings DataFrame
        factor_loadings_df = pd.DataFrame({
            'Loading': factor_loadings,
            'T-Stat': factor_loadings / (specific_returns.std() / np.sqrt(len(specific_returns))),
            'Contribution': list(factor_contributions.values())
        })
        
        self._attribution_analysis = AttributionAnalysis(
            factor_returns=aligned_factors,
            factor_loadings=factor_loadings_df,
            specific_returns=specific_returns,
            attribution_summary=attribution_summary,
            r_squared=r_squared,
            tracking_error=tracking_error
        )
        
        return self._attribution_analysis
    
    def decompose_risk(self) -> RiskDecomposition:
        """Decompose portfolio risk into components"""
        if self._risk_decomposition is not None:
            return self._risk_decomposition
        
        logger.info("Decomposing portfolio risk")
        
        # Total risk (volatility)
        total_risk = self.returns.std() * np.sqrt(252)
        
        # Systematic vs idiosyncratic risk
        if self.benchmark_returns is not None and len(self.benchmark_returns) > 0:
            # Calculate beta
            common_index = self.returns.index.intersection(self.benchmark_returns.index)
            if len(common_index) > 0:
                aligned_returns = self.returns.loc[common_index]
                aligned_benchmark = self.benchmark_returns.loc[common_index]
                
                covariance = np.cov(aligned_returns, aligned_benchmark)[0, 1]
                benchmark_variance = aligned_benchmark.var()
                beta = covariance / benchmark_variance if benchmark_variance > 0 else 0
                
                # Systematic risk
                systematic_risk = abs(beta) * aligned_benchmark.std() * np.sqrt(252)
                
                # Idiosyncratic risk
                idiosyncratic_risk = np.sqrt(max(0, total_risk**2 - systematic_risk**2))
            else:
                systematic_risk = 0.0
                idiosyncratic_risk = total_risk
        else:
            systematic_risk = 0.0
            idiosyncratic_risk = total_risk
        
        # Factor contributions (simplified)
        factor_contributions = {
            'Market': systematic_risk,
            'Specific': idiosyncratic_risk
        }
        
        # Concentration risk (based on position concentration)
        concentration_risk = self._calculate_concentration_risk()
        
        # Liquidity risk (based on trading patterns)
        liquidity_risk = self._calculate_liquidity_risk()
        
        # Tail risk (VaR-based)
        tail_risk = abs(np.percentile(self.returns, 5)) * np.sqrt(252)
        
        self._risk_decomposition = RiskDecomposition(
            total_risk=total_risk,
            systematic_risk=systematic_risk,
            idiosyncratic_risk=idiosyncratic_risk,
            factor_contributions=factor_contributions,
            concentration_risk=concentration_risk,
            liquidity_risk=liquidity_risk,
            tail_risk=tail_risk
        )
        
        return self._risk_decomposition
    
    def _calculate_concentration_risk(self) -> float:
        """Calculate concentration risk based on position weights"""
        if not self.results.positions_history:
            return 0.0
        
        # Get latest portfolio snapshot
        latest_snapshot = self.results.positions_history[-1]
        
        if not latest_snapshot.positions:
            return 0.0
        
        # Calculate Herfindahl index
        weights = [abs(pos.weight) for pos in latest_snapshot.positions]
        total_weight = sum(weights)
        
        if total_weight == 0:
            return 0.0
        
        normalized_weights = [w / total_weight for w in weights]
        herfindahl_index = sum(w**2 for w in normalized_weights)
        
        # Convert to concentration risk measure
        return herfindahl_index
    
    def _calculate_liquidity_risk(self) -> float:
        """Calculate liquidity risk based on trading patterns"""
        if not self.trades:
            return 0.0
        
        # Calculate average market impact
        market_impacts = [trade.market_impact for trade in self.trades if trade.market_impact > 0]
        
        if not market_impacts:
            return 0.0
        
        return np.mean(market_impacts)
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        logger.info("Generating comprehensive performance report")
        
        # Basic metrics
        basic_metrics = self.results.get_summary_stats()
        
        # Regime analysis
        regime_analysis = self.analyze_regimes()
        
        # Attribution analysis
        attribution_analysis = self.analyze_attribution()
        
        # Risk decomposition
        risk_decomposition = self.decompose_risk()
        
        # Trade analysis
        trade_analysis = self._analyze_trades()
        
        # Rolling performance
        rolling_performance = self._calculate_rolling_performance()
        
        report = {
            'summary': basic_metrics,
            'regime_analysis': {
                'current_regime': regime_analysis.current_regime,
                'regime_probabilities': regime_analysis.regime_probabilities,
                'regime_metrics': regime_analysis.regime_metrics,
                'transition_count': len(regime_analysis.regime_transitions)
            },
            'attribution': {
                'r_squared': attribution_analysis.r_squared,
                'tracking_error': attribution_analysis.tracking_error,
                'attribution_summary': attribution_analysis.attribution_summary
            },
            'risk_decomposition': {
                'total_risk': risk_decomposition.total_risk,
                'systematic_risk': risk_decomposition.systematic_risk,
                'idiosyncratic_risk': risk_decomposition.idiosyncratic_risk,
                'concentration_risk': risk_decomposition.concentration_risk,
                'liquidity_risk': risk_decomposition.liquidity_risk,
                'tail_risk': risk_decomposition.tail_risk
            },
            'trade_analysis': trade_analysis,
            'rolling_performance': rolling_performance
        }
        
        return report
    
    def _analyze_trades(self) -> Dict[str, Any]:
        """Analyze trading patterns and execution quality"""
        if not self.trades:
            return {}
        
        # Convert trades to DataFrame
        trade_data = []
        for trade in self.trades:
            trade_data.append({
                'timestamp': trade.timestamp,
                'symbol': trade.symbol,
                'quantity': trade.quantity,
                'price': trade.price,
                'commission': trade.commission,
                'slippage': trade.slippage,
                'market_impact': trade.market_impact,
                'pnl': trade.pnl,
                'trade_type': trade.trade_type.value,
                'signal_strength': trade.signal_strength,
                'confidence': trade.confidence
            })
        
        trades_df = pd.DataFrame(trade_data)
        
        # Execution quality metrics
        avg_slippage = trades_df['slippage'].mean()
        avg_commission = trades_df['commission'].mean()
        avg_market_impact = trades_df['market_impact'].mean()
        
        # Trading frequency
        trades_per_day = len(trades_df) / len(self.returns) if len(self.returns) > 0 else 0
        
        # Signal quality
        signal_strength_avg = trades_df['signal_strength'].mean() if 'signal_strength' in trades_df.columns else 0
        confidence_avg = trades_df['confidence'].mean() if 'confidence' in trades_df.columns else 0
        
        # PnL distribution
        pnl_stats = trades_df['pnl'].describe().to_dict() if 'pnl' in trades_df.columns else {}
        
        return {
            'execution_quality': {
                'avg_slippage': avg_slippage,
                'avg_commission': avg_commission,
                'avg_market_impact': avg_market_impact
            },
            'trading_frequency': {
                'trades_per_day': trades_per_day,
                'total_trades': len(trades_df)
            },
            'signal_quality': {
                'avg_signal_strength': signal_strength_avg,
                'avg_confidence': confidence_avg
            },
            'pnl_distribution': pnl_stats
        }
    
    def _calculate_rolling_performance(self, windows: List[int] = [21, 63, 252]) -> Dict[str, pd.DataFrame]:
        """Calculate rolling performance metrics"""
        rolling_metrics = {}
        
        for window in windows:
            if len(self.returns) < window:
                continue
            
            # Rolling returns
            rolling_returns = self.returns.rolling(window=window).sum()
            
            # Rolling volatility
            rolling_vol = self.returns.rolling(window=window).std() * np.sqrt(252)
            
            # Rolling Sharpe ratio
            rolling_sharpe = (rolling_returns.rolling(window=window).mean() * 252) / rolling_vol
            
            # Rolling max drawdown
            rolling_cumret = (1 + self.returns).rolling(window=window).apply(lambda x: x.prod() - 1)
            rolling_cumulative = rolling_cumret.expanding().max()
            rolling_drawdown = (rolling_cumret - rolling_cumulative) / rolling_cumulative
            rolling_max_dd = rolling_drawdown.rolling(window=window).min()
            
            rolling_metrics[f'{window}d'] = pd.DataFrame({
                'returns': rolling_returns,
                'volatility': rolling_vol,
                'sharpe_ratio': rolling_sharpe,
                'max_drawdown': rolling_max_dd
            })
        
        return rolling_metrics
    
    def export_report(self, filepath: str, format: str = 'json'):
        """Export performance report to file
        
        Args:
            filepath: Output file path
            format: Export format ('json', 'excel', 'html')
        """
        report = self.generate_performance_report()
        
        if format == 'json':
            import json
            from nautilus_trader_engine.indicators.consolidated_indicators import ConsolidatedIndicators

            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2, default=str)
        
        elif format == 'excel':
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # Summary sheet
                summary_df = pd.DataFrame([report['summary']]).T
                summary_df.to_excel(writer, sheet_name='Summary')
                
                # Regime analysis
                if 'regime_analysis' in report and 'regime_metrics' in report['regime_analysis']:
                    regime_df = pd.DataFrame(report['regime_analysis']['regime_metrics']).T
                    regime_df.to_excel(writer, sheet_name='Regime Analysis')
                
                # Returns series
                self.returns.to_excel(writer, sheet_name='Returns')
                
                # Portfolio history
                self.portfolio_history.to_excel(writer, sheet_name='Portfolio History')
        
        elif format == 'html':
            # Simple HTML report
            html_content = self._generate_html_report(report)
            with open(filepath, 'w') as f:
                f.write(html_content)
        
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Performance report exported to {filepath}")
    
    def _generate_html_report(self, report: Dict[str, Any]) -> str:
        """Generate HTML performance report"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Performance Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .metric {{ margin: 10px 0; }}
                .section {{ margin: 30px 0; }}
            </style>
        </head>
        <body>
            <h1>Strategy Performance Report</h1>
            
            <div class="section">
                <h2>Summary Statistics</h2>
                <table>
        """
        
        # Add summary statistics
        for key, value in report['summary'].items():
            if isinstance(value, (int, float)):
                formatted_value = f"{value:.4f}" if abs(value) < 1 else f"{value:,.2f}"
            else:
                formatted_value = str(value)
            html += f"<tr><td>{key}</td><td>{formatted_value}</td></tr>"
        
        html += """
                </table>
            </div>
            
            <div class="section">
                <h2>Risk Analysis</h2>
                <table>
        """
        
        # Add risk metrics
        if 'risk_decomposition' in report:
            for key, value in report['risk_decomposition'].items():
                if isinstance(value, (int, float)):
                    formatted_value = f"{value:.4f}"
                else:
                    formatted_value = str(value)
                html += f"<tr><td>{key}</td><td>{formatted_value}</td></tr>"
        
        html += """
                </table>
            </div>
        </body>
        </html>
        """
        
        return html