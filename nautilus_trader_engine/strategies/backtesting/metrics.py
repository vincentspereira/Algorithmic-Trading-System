"""Performance Metrics

Comprehensive collection of institutional-grade performance and risk metrics
for backtesting analysis and strategy evaluation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LinearRegression
import warnings
from nautilus_trader_engine.indicators.consolidated_indicators import ConsolidatedIndicators

warnings.filterwarnings('ignore')


@dataclass
class PerformanceMetrics:
    """Core performance metrics"""
    
    # Return metrics
    total_return: float = 0.0
    annualized_return: float = 0.0
    compound_annual_growth_rate: float = 0.0
    
    # Risk-adjusted returns
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    omega_ratio: float = 0.0
    
    # Volatility metrics
    volatility: float = 0.0
    downside_deviation: float = 0.0
    upside_deviation: float = 0.0
    
    # Higher moments
    skewness: float = 0.0
    kurtosis: float = 0.0
    
    # Tail risk
    tail_ratio: float = 0.0
    
    @classmethod
    def calculate(cls, returns: pd.Series, risk_free_rate: float = 0.02, 
                 target_return: float = 0.0) -> 'PerformanceMetrics':
        """Calculate performance metrics from returns series"""
        if len(returns) == 0:
            return cls()
        
        # Annualization factor
        periods_per_year = 252  # Trading days
        
        # Basic return metrics
        total_return = (1 + returns).prod() - 1
        periods = len(returns)
        years = periods / periods_per_year
        
        if years > 0:
            annualized_return = (1 + total_return) ** (1 / years) - 1
            cagr = annualized_return  # Same calculation
        else:
            annualized_return = 0.0
            cagr = 0.0
        
        # Volatility metrics
        volatility = returns.std() * np.sqrt(periods_per_year)
        
        # Downside and upside deviation
        downside_returns = returns[returns < target_return]
        upside_returns = returns[returns > target_return]
        
        downside_deviation = downside_returns.std() * np.sqrt(periods_per_year) if len(downside_returns) > 0 else 0.0
        upside_deviation = upside_returns.std() * np.sqrt(periods_per_year) if len(upside_returns) > 0 else 0.0
        
        # Risk-adjusted ratios
        excess_return = annualized_return - risk_free_rate
        
        sharpe_ratio = excess_return / volatility if volatility > 0 else 0.0
        sortino_ratio = excess_return / downside_deviation if downside_deviation > 0 else 0.0
        
        # Calmar ratio (requires drawdown calculation)
        cumulative_returns = (1 + returns).cumprod()
        rolling_max = cumulative_returns.expanding().max()
        drawdowns = (cumulative_returns - rolling_max) / rolling_max
        max_drawdown = abs(drawdowns.min())
        
        calmar_ratio = annualized_return / max_drawdown if max_drawdown > 0 else 0.0
        
        # Omega ratio
        excess_returns = returns - target_return
        gains = excess_returns[excess_returns > 0].sum()
        losses = abs(excess_returns[excess_returns < 0].sum())
        omega_ratio = gains / losses if losses > 0 else float('inf')
        
        # Higher moments
        skewness = returns.skew()
        kurtosis = returns.kurtosis()
        
        # Tail ratio (95th percentile / 5th percentile)
        p95 = returns.quantile(0.95)
        p5 = returns.quantile(0.05)
        tail_ratio = abs(p95 / p5) if p5 != 0 else 0.0
        
        return cls(
            total_return=total_return,
            annualized_return=annualized_return,
            compound_annual_growth_rate=cagr,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            omega_ratio=omega_ratio,
            volatility=volatility,
            downside_deviation=downside_deviation,
            upside_deviation=upside_deviation,
            skewness=skewness,
            kurtosis=kurtosis,
            tail_ratio=tail_ratio
        )


@dataclass
class RiskMetrics:
    """Comprehensive risk metrics"""
    
    # Value at Risk
    var_95: float = 0.0
    var_99: float = 0.0
    var_99_9: float = 0.0
    
    # Conditional Value at Risk (Expected Shortfall)
    cvar_95: float = 0.0
    cvar_99: float = 0.0
    cvar_99_9: float = 0.0
    
    # Drawdown metrics
    max_drawdown: float = 0.0
    avg_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    avg_drawdown_duration: float = 0.0
    
    # Volatility metrics
    realized_volatility: float = 0.0
    volatility_of_volatility: float = 0.0
    
    # Correlation and beta
    beta: float = 0.0
    correlation_with_market: float = 0.0
    
    # Risk-adjusted metrics
    treynor_ratio: float = 0.0
    jensen_alpha: float = 0.0
    
    # Tail risk measures
    maximum_loss: float = 0.0
    pain_index: float = 0.0
    ulcer_index: float = 0.0
    
    @classmethod
    def calculate(cls, returns: pd.Series, benchmark_returns: Optional[pd.Series] = None,
                 risk_free_rate: float = 0.02) -> 'RiskMetrics':
        """Calculate risk metrics from returns series"""
        if len(returns) == 0:
            return cls()
        
        # VaR calculations
        var_95 = np.percentile(returns, 5)
        var_99 = np.percentile(returns, 1)
        var_99_9 = np.percentile(returns, 0.1)
        
        # CVaR calculations
        cvar_95 = returns[returns <= var_95].mean() if len(returns[returns <= var_95]) > 0 else 0.0
        cvar_99 = returns[returns <= var_99].mean() if len(returns[returns <= var_99]) > 0 else 0.0
        cvar_99_9 = returns[returns <= var_99_9].mean() if len(returns[returns <= var_99_9]) > 0 else 0.0
        
        # Drawdown analysis
        cumulative_returns = (1 + returns).cumprod()
        rolling_max = cumulative_returns.expanding().max()
        drawdowns = (cumulative_returns - rolling_max) / rolling_max
        
        max_drawdown = abs(drawdowns.min())
        avg_drawdown = abs(drawdowns[drawdowns < 0].mean()) if len(drawdowns[drawdowns < 0]) > 0 else 0.0
        
        # Drawdown duration analysis
        drawdown_periods = (drawdowns < -0.001).astype(int)  # Consider drawdowns > 0.1%
        drawdown_durations = []
        current_duration = 0
        
        for in_drawdown in drawdown_periods:
            if in_drawdown:
                current_duration += 1
            else:
                if current_duration > 0:
                    drawdown_durations.append(current_duration)
                    current_duration = 0
        
        if current_duration > 0:  # Handle case where backtest ends in drawdown
            drawdown_durations.append(current_duration)
        
        max_drawdown_duration = max(drawdown_durations) if drawdown_durations else 0
        avg_drawdown_duration = np.mean(drawdown_durations) if drawdown_durations else 0.0
        
        # Volatility metrics
        realized_volatility = returns.std() * np.sqrt(252)
        
        # Rolling volatility for volatility of volatility
        rolling_vol = returns.rolling(window=21).std() * np.sqrt(252)
        volatility_of_volatility = rolling_vol.std() if len(rolling_vol.dropna()) > 0 else 0.0
        
        # Maximum loss
        maximum_loss = returns.min()
        
        # Pain Index (average drawdown)
        pain_index = abs(drawdowns.mean())
        
        # Ulcer Index (RMS of drawdowns)
        ulcer_index = np.sqrt((drawdowns ** 2).mean())
        
        # Benchmark-related metrics
        beta = 0.0
        correlation_with_market = 0.0
        treynor_ratio = 0.0
        jensen_alpha = 0.0
        
        if benchmark_returns is not None and len(benchmark_returns) == len(returns):
            # Beta calculation
            covariance = np.cov(returns, benchmark_returns)[0, 1]
            benchmark_variance = np.var(benchmark_returns)
            beta = covariance / benchmark_variance if benchmark_variance > 0 else 0.0
            
            # Correlation
            correlation_with_market = returns.corr(benchmark_returns)
            
            # Treynor ratio
            excess_return = returns.mean() * 252 - risk_free_rate
            treynor_ratio = excess_return / beta if beta != 0 else 0.0
            
            # Jensen's Alpha
            benchmark_excess_return = benchmark_returns.mean() * 252 - risk_free_rate
            jensen_alpha = excess_return - beta * benchmark_excess_return
        
        return cls(
            var_95=var_95,
            var_99=var_99,
            var_99_9=var_99_9,
            cvar_95=cvar_95,
            cvar_99=cvar_99,
            cvar_99_9=cvar_99_9,
            max_drawdown=max_drawdown,
            avg_drawdown=avg_drawdown,
            max_drawdown_duration=max_drawdown_duration,
            avg_drawdown_duration=avg_drawdown_duration,
            realized_volatility=realized_volatility,
            volatility_of_volatility=volatility_of_volatility,
            beta=beta,
            correlation_with_market=correlation_with_market,
            treynor_ratio=treynor_ratio,
            jensen_alpha=jensen_alpha,
            maximum_loss=maximum_loss,
            pain_index=pain_index,
            ulcer_index=ulcer_index
        )


@dataclass
class TradeMetrics:
    """Trade-level performance metrics"""
    
    # Basic trade statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    # Win/loss ratios
    win_rate: float = 0.0
    loss_rate: float = 0.0
    
    # P&L statistics
    total_pnl: float = 0.0
    avg_pnl: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    
    # Risk-reward metrics
    profit_factor: float = 0.0
    payoff_ratio: float = 0.0
    
    # Trade duration
    avg_trade_duration: float = 0.0
    max_trade_duration: float = 0.0
    
    # Consecutive trades
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    
    # Execution quality
    avg_slippage: float = 0.0
    avg_commission: float = 0.0
    total_costs: float = 0.0
    
    @classmethod
    def calculate(cls, trades: List) -> 'TradeMetrics':
        """Calculate trade metrics from trade list"""
        if not trades:
            return cls()
        
        total_trades = len(trades)
        
        # Extract P&L values
        pnls = [trade.realized_pnl for trade in trades if hasattr(trade, 'realized_pnl') and trade.realized_pnl != 0]
        
        if not pnls:
            return cls(total_trades=total_trades)
        
        # Win/loss analysis
        winning_pnls = [pnl for pnl in pnls if pnl > 0]
        losing_pnls = [pnl for pnl in pnls if pnl < 0]
        
        winning_trades = len(winning_pnls)
        losing_trades = len(losing_pnls)
        
        win_rate = winning_trades / len(pnls) if pnls else 0.0
        loss_rate = losing_trades / len(pnls) if pnls else 0.0
        
        # P&L statistics
        total_pnl = sum(pnls)
        avg_pnl = np.mean(pnls)
        avg_win = np.mean(winning_pnls) if winning_pnls else 0.0
        avg_loss = np.mean(losing_pnls) if losing_pnls else 0.0
        
        # Risk-reward metrics
        total_wins = sum(winning_pnls) if winning_pnls else 0.0
        total_losses = abs(sum(losing_pnls)) if losing_pnls else 0.0
        
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        payoff_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0.0
        
        # Consecutive wins/losses
        consecutive_wins = 0
        consecutive_losses = 0
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        
        for pnl in pnls:
            if pnl > 0:
                consecutive_wins += 1
                consecutive_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, consecutive_wins)
            else:
                consecutive_losses += 1
                consecutive_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
        
        # Execution quality
        slippages = [getattr(trade, 'slippage', 0) for trade in trades]
        commissions = [getattr(trade, 'commission', 0) for trade in trades]
        costs = [getattr(trade, 'total_cost', 0) for trade in trades]
        
        avg_slippage = np.mean(slippages) if slippages else 0.0
        avg_commission = np.mean(commissions) if commissions else 0.0
        total_costs = sum(costs) if costs else 0.0
        
        # Trade duration (if available)
        durations = []
        for trade in trades:
            if hasattr(trade, 'timestamp') and hasattr(trade, 'fill_time'):
                if trade.fill_time:
                    duration = (trade.fill_time - trade.timestamp).total_seconds() / 3600  # Hours
                    durations.append(duration)
        
        avg_trade_duration = np.mean(durations) if durations else 0.0
        max_trade_duration = max(durations) if durations else 0.0
        
        return cls(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            loss_rate=loss_rate,
            total_pnl=total_pnl,
            avg_pnl=avg_pnl,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            payoff_ratio=payoff_ratio,
            max_consecutive_wins=max_consecutive_wins,
            max_consecutive_losses=max_consecutive_losses,
            avg_slippage=avg_slippage,
            avg_commission=avg_commission,
            total_costs=total_costs,
            avg_trade_duration=avg_trade_duration,
            max_trade_duration=max_trade_duration
        )


@dataclass
class DrawdownMetrics:
    """Detailed drawdown analysis"""
    
    # Drawdown statistics
    max_drawdown: float = 0.0
    avg_drawdown: float = 0.0
    drawdown_volatility: float = 0.0
    
    # Duration statistics
    max_drawdown_duration: int = 0
    avg_drawdown_duration: float = 0.0
    recovery_time: int = 0
    
    # Drawdown frequency
    num_drawdown_periods: int = 0
    drawdown_frequency: float = 0.0
    
    # Underwater curve metrics
    time_underwater: float = 0.0  # Percentage of time in drawdown
    
    @classmethod
    def calculate(cls, returns: pd.Series, threshold: float = 0.001) -> 'DrawdownMetrics':
        """Calculate detailed drawdown metrics"""
        if len(returns) == 0:
            return cls()
        
        # Calculate drawdowns
        cumulative_returns = (1 + returns).cumprod()
        rolling_max = cumulative_returns.expanding().max()
        drawdowns = (cumulative_returns - rolling_max) / rolling_max
        
        # Basic drawdown statistics
        max_drawdown = abs(drawdowns.min())
        drawdown_values = drawdowns[drawdowns < -threshold]
        avg_drawdown = abs(drawdown_values.mean()) if len(drawdown_values) > 0 else 0.0
        drawdown_volatility = drawdown_values.std() if len(drawdown_values) > 0 else 0.0
        
        # Identify drawdown periods
        in_drawdown = (drawdowns < -threshold).astype(int)
        drawdown_periods = []
        current_period = {'start': None, 'end': None, 'duration': 0, 'depth': 0}
        
        for i, is_drawdown in enumerate(in_drawdown):
            if is_drawdown and current_period['start'] is None:
                # Start of new drawdown period
                current_period['start'] = i
                current_period['depth'] = drawdowns.iloc[i]
            elif is_drawdown:
                # Continue drawdown period
                current_period['depth'] = min(current_period['depth'], drawdowns.iloc[i])
            elif not is_drawdown and current_period['start'] is not None:
                # End of drawdown period
                current_period['end'] = i - 1
                current_period['duration'] = current_period['end'] - current_period['start'] + 1
                drawdown_periods.append(current_period.copy())
                current_period = {'start': None, 'end': None, 'duration': 0, 'depth': 0}
        
        # Handle case where backtest ends in drawdown
        if current_period['start'] is not None:
            current_period['end'] = len(drawdowns) - 1
            current_period['duration'] = current_period['end'] - current_period['start'] + 1
            drawdown_periods.append(current_period)
        
        # Duration statistics
        durations = [period['duration'] for period in drawdown_periods]
        max_drawdown_duration = max(durations) if durations else 0
        avg_drawdown_duration = np.mean(durations) if durations else 0.0
        
        # Recovery time (time to recover from max drawdown)
        recovery_time = 0
        if len(drawdowns) > 0 and not drawdowns.empty:
            max_dd_idx = drawdowns.idxmin()
            if max_dd_idx is not None:
                recovery_series = drawdowns[max_dd_idx:].ge(-threshold)
                if recovery_series.any():
                    recovery_idx = recovery_series.idxmax()
                    if recovery_idx != max_dd_idx:
                        recovery_time = recovery_idx - max_dd_idx
        
        # Frequency metrics
        num_drawdown_periods = len(drawdown_periods)
        total_periods = len(returns)
        drawdown_frequency = num_drawdown_periods / (total_periods / 252) if total_periods > 0 else 0.0  # Per year
        
        # Time underwater
        underwater_periods = sum(durations) if durations else 0
        time_underwater = underwater_periods / total_periods if total_periods > 0 else 0.0
        
        return cls(
            max_drawdown=max_drawdown,
            avg_drawdown=avg_drawdown,
            drawdown_volatility=drawdown_volatility,
            max_drawdown_duration=max_drawdown_duration,
            avg_drawdown_duration=avg_drawdown_duration,
            recovery_time=recovery_time,
            num_drawdown_periods=num_drawdown_periods,
            drawdown_frequency=drawdown_frequency,
            time_underwater=time_underwater
        )


@dataclass
class BenchmarkMetrics:
    """Benchmark comparison metrics"""
    
    # Relative performance
    alpha: float = 0.0
    beta: float = 0.0
    r_squared: float = 0.0
    
    # Information metrics
    information_ratio: float = 0.0
    tracking_error: float = 0.0
    active_return: float = 0.0
    
    # Correlation metrics
    correlation: float = 0.0
    up_capture: float = 0.0
    down_capture: float = 0.0
    
    # Relative risk metrics
    relative_var: float = 0.0
    relative_max_drawdown: float = 0.0
    
    @classmethod
    def calculate(cls, strategy_returns: pd.Series, benchmark_returns: pd.Series,
                 risk_free_rate: float = 0.02) -> 'BenchmarkMetrics':
        """Calculate benchmark comparison metrics"""
        if len(strategy_returns) == 0 or len(benchmark_returns) == 0:
            return cls()
        
        # Align returns
        aligned_data = pd.DataFrame({
            'strategy': strategy_returns,
            'benchmark': benchmark_returns
        }).dropna()
        
        if len(aligned_data) < 2:
            return cls()
        
        strategy_ret = aligned_data['strategy']
        benchmark_ret = aligned_data['benchmark']
        
        # Regression analysis for alpha and beta
        X = benchmark_ret.values.reshape(-1, 1)
        y = strategy_ret.values
        
        reg = LinearRegression().fit(X, y)
        beta = reg.coef_[0]
        alpha = reg.intercept_ * 252  # Annualized alpha
        r_squared = reg.score(X, y)
        
        # Excess returns
        strategy_excess = strategy_ret - risk_free_rate / 252
        benchmark_excess = benchmark_ret - risk_free_rate / 252
        
        # Active return and tracking error
        active_returns = strategy_ret - benchmark_ret
        active_return = active_returns.mean() * 252
        tracking_error = active_returns.std() * np.sqrt(252)
        
        # Information ratio
        information_ratio = active_return / tracking_error if tracking_error > 0 else 0.0
        
        # Correlation
        correlation = strategy_ret.corr(benchmark_ret)
        
        # Up/Down capture ratios
        up_periods = benchmark_ret > 0
        down_periods = benchmark_ret < 0
        
        if up_periods.sum() > 0:
            up_capture = (strategy_ret[up_periods].mean() / benchmark_ret[up_periods].mean()) * 100
        else:
            up_capture = 0.0
        
        if down_periods.sum() > 0:
            down_capture = (strategy_ret[down_periods].mean() / benchmark_ret[down_periods].mean()) * 100
        else:
            down_capture = 0.0
        
        # Relative VaR
        relative_var = np.percentile(active_returns, 5)
        
        # Relative drawdown
        strategy_cumret = (1 + strategy_ret).cumprod()
        benchmark_cumret = (1 + benchmark_ret).cumprod()
        
        strategy_dd = (strategy_cumret / strategy_cumret.expanding().max() - 1).min()
        benchmark_dd = (benchmark_cumret / benchmark_cumret.expanding().max() - 1).min()
        
        relative_max_drawdown = strategy_dd - benchmark_dd
        
        return cls(
            alpha=alpha,
            beta=beta,
            r_squared=r_squared,
            information_ratio=information_ratio,
            tracking_error=tracking_error,
            active_return=active_return,
            correlation=correlation,
            up_capture=up_capture,
            down_capture=down_capture,
            relative_var=relative_var,
            relative_max_drawdown=relative_max_drawdown
        )


class MetricsCalculator:
    """Unified metrics calculator"""
    
    @staticmethod
    def calculate_all_metrics(returns: pd.Series, benchmark_returns: Optional[pd.Series] = None,
                            trades: Optional[List] = None, risk_free_rate: float = 0.02) -> Dict[str, any]:
        """Calculate all metrics categories"""
        
        # Performance metrics
        performance = PerformanceMetrics.calculate(returns, risk_free_rate)
        
        # Risk metrics
        risk = RiskMetrics.calculate(returns, benchmark_returns, risk_free_rate)
        
        # Drawdown metrics
        drawdown = DrawdownMetrics.calculate(returns)
        
        # Trade metrics (if trades provided)
        trade_metrics = TradeMetrics.calculate(trades) if trades else TradeMetrics()
        
        # Benchmark metrics (if benchmark provided)
        benchmark_metrics = BenchmarkMetrics.calculate(returns, benchmark_returns, risk_free_rate) if benchmark_returns is not None else BenchmarkMetrics()
        
        return {
            'performance': performance,
            'risk': risk,
            'drawdown': drawdown,
            'trades': trade_metrics,
            'benchmark': benchmark_metrics
        }
    
    @staticmethod
    def create_summary_table(metrics: Dict[str, any]) -> pd.DataFrame:
        """Create summary table of all metrics"""
        summary_data = []
        
        # Performance metrics
        perf = metrics['performance']
        summary_data.extend([
            ('Total Return', f"{perf.total_return:.2%}"),
            ('Annualized Return', f"{perf.annualized_return:.2%}"),
            ('Volatility', f"{perf.volatility:.2%}"),
            ('Sharpe Ratio', f"{perf.sharpe_ratio:.3f}"),
            ('Sortino Ratio', f"{perf.sortino_ratio:.3f}"),
            ('Calmar Ratio', f"{perf.calmar_ratio:.3f}")
        ])
        
        # Risk metrics
        risk = metrics['risk']
        summary_data.extend([
            ('Max Drawdown', f"{risk.max_drawdown:.2%}"),
            ('VaR (95%)', f"{risk.var_95:.2%}"),
            ('VaR (99%)', f"{risk.var_99:.2%}"),
            ('Beta', f"{risk.beta:.3f}")
        ])
        
        # Trade metrics
        trades = metrics['trades']
        summary_data.extend([
            ('Total Trades', f"{trades.total_trades:,}"),
            ('Win Rate', f"{trades.win_rate:.2%}"),
            ('Profit Factor', f"{trades.profit_factor:.2f}")
        ])
        
        # Benchmark metrics
        bench = metrics['benchmark']
        if bench.alpha != 0 or bench.beta != 0:
            summary_data.extend([
                ('Alpha', f"{bench.alpha:.2%}"),
                ('Information Ratio', f"{bench.information_ratio:.3f}"),
                ('Tracking Error', f"{bench.tracking_error:.2%}")
            ])
        
        return pd.DataFrame(summary_data, columns=['Metric', 'Value'])