"""Backtesting Results

Data structures for storing and managing backtesting results with comprehensive
performance metrics, trade history, and analysis data.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from decimal import Decimal
from enum import Enum


class TradeStatus(Enum):
    """Trade execution status"""
    PENDING = "pending"
    FILLED = "filled"
    PARTIAL = "partial"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class TradeType(Enum):
    """Trade types"""
    BUY = "buy"
    SELL = "sell"
    SHORT = "short"
    COVER = "cover"


@dataclass
class Trade:
    """Individual trade record"""
    timestamp: datetime
    symbol: str
    trade_type: TradeType
    quantity: float
    price: float
    commission: float
    slippage: float
    market_impact: float
    
    # Trade identification
    trade_id: str
    strategy_id: str
    signal_strength: Optional[float] = None
    confidence: Optional[float] = None
    
    # Execution details
    status: TradeStatus = TradeStatus.FILLED
    fill_time: Optional[datetime] = None
    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None
    order_type: str = "market"
    
    # P&L tracking
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    
    # Risk metrics
    position_size: float = 0.0  # Position size as % of portfolio
    portfolio_value: float = 0.0
    
    # Market context
    market_regime: Optional[str] = None
    volatility: Optional[float] = None
    volume: Optional[float] = None
    
    @property
    def trade_value(self) -> float:
        """Total trade value"""
        return abs(self.quantity * self.price)
    
    @property
    def total_cost(self) -> float:
        """Total transaction cost"""
        return self.commission + self.slippage + self.market_impact
    
    @property
    def net_proceeds(self) -> float:
        """Net proceeds after costs"""
        multiplier = 1 if self.trade_type in [TradeType.BUY, TradeType.COVER] else -1
        return (self.quantity * self.price * multiplier) - self.total_cost


@dataclass
class Position:
    """Portfolio position record"""
    timestamp: datetime
    symbol: str
    quantity: float
    avg_price: float
    market_price: float
    market_value: float
    
    # P&L tracking
    unrealized_pnl: float
    realized_pnl: float
    total_pnl: float
    
    # Risk metrics
    weight: float  # Position weight in portfolio
    beta: Optional[float] = None
    volatility: Optional[float] = None
    var_contribution: Optional[float] = None
    
    # Attribution
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[str] = None
    
    @property
    def pnl_percent(self) -> float:
        """P&L as percentage of cost basis"""
        cost_basis = abs(self.quantity * self.avg_price)
        return (self.total_pnl / cost_basis) * 100 if cost_basis > 0 else 0.0


@dataclass
class PortfolioSnapshot:
    """Portfolio state at a point in time"""
    timestamp: datetime
    total_value: float
    cash: float
    positions_value: float
    
    # Performance metrics
    daily_return: float
    cumulative_return: float
    volatility: float
    sharpe_ratio: float
    
    # Risk metrics
    beta: float
    var_95: float
    var_99: float
    max_drawdown: float
    
    # Positions
    positions: List[Position] = field(default_factory=list)
    
    # Exposures
    sector_exposure: Dict[str, float] = field(default_factory=dict)
    market_cap_exposure: Dict[str, float] = field(default_factory=dict)
    
    # Leverage and concentration
    leverage: float = 1.0
    concentration: float = 0.0  # Herfindahl index
    
    @property
    def num_positions(self) -> int:
        """Number of active positions"""
        return len([p for p in self.positions if abs(p.quantity) > 0])
    
    @property
    def long_exposure(self) -> float:
        """Long exposure as % of portfolio"""
        return sum(p.weight for p in self.positions if p.quantity > 0)
    
    @property
    def short_exposure(self) -> float:
        """Short exposure as % of portfolio"""
        return sum(abs(p.weight) for p in self.positions if p.quantity < 0)
    
    @property
    def net_exposure(self) -> float:
        """Net exposure (long - short)"""
        return self.long_exposure - self.short_exposure
    
    @property
    def gross_exposure(self) -> float:
        """Gross exposure (long + short)"""
        return self.long_exposure + self.short_exposure


@dataclass
class BacktestResults:
    """Comprehensive backtesting results"""
    
    # Basic information
    strategy_name: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    
    # Time series data
    portfolio_history: pd.DataFrame  # Portfolio value over time
    returns_series: pd.Series  # Daily returns
    benchmark_returns: pd.Series  # Benchmark returns
    
    # Trade history
    trades: List[Trade] = field(default_factory=list)
    positions_history: List[PortfolioSnapshot] = field(default_factory=list)
    
    # Performance metrics
    total_return: float = 0.0
    annualized_return: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    
    # Risk metrics
    max_drawdown: float = 0.0
    var_95: float = 0.0
    var_99: float = 0.0
    cvar_95: float = 0.0
    cvar_99: float = 0.0
    
    # Benchmark comparison
    alpha: float = 0.0
    beta: float = 0.0
    information_ratio: float = 0.0
    tracking_error: float = 0.0
    
    # Trade statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    
    # Advanced metrics
    regime_performance: Dict[str, Dict[str, float]] = field(default_factory=dict)
    factor_attribution: Dict[str, float] = field(default_factory=dict)
    sector_attribution: Dict[str, float] = field(default_factory=dict)
    
    # Stress test results
    stress_test_results: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Monte Carlo results
    monte_carlo_results: Optional[Dict[str, Any]] = None
    
    # Walk-forward results
    walk_forward_results: Optional[Dict[str, Any]] = None
    
    # Execution quality
    avg_slippage: float = 0.0
    avg_commission: float = 0.0
    total_costs: float = 0.0
    
    # Additional analysis
    correlation_matrix: Optional[pd.DataFrame] = None
    rolling_metrics: Optional[pd.DataFrame] = None
    
    def __post_init__(self):
        """Calculate derived metrics after initialization"""
        if len(self.trades) > 0:
            self._calculate_trade_statistics()
        
        if not self.portfolio_history.empty:
            self._calculate_performance_metrics()
    
    def _calculate_trade_statistics(self):
        """Calculate trade-based statistics"""
        self.total_trades = len(self.trades)
        
        if self.total_trades == 0:
            return
        
        # Calculate win/loss statistics
        pnls = [trade.realized_pnl for trade in self.trades if trade.realized_pnl != 0]
        
        if pnls:
            winning_pnls = [pnl for pnl in pnls if pnl > 0]
            losing_pnls = [pnl for pnl in pnls if pnl < 0]
            
            self.winning_trades = len(winning_pnls)
            self.losing_trades = len(losing_pnls)
            self.win_rate = self.winning_trades / len(pnls) if pnls else 0
            
            self.avg_win = np.mean(winning_pnls) if winning_pnls else 0
            self.avg_loss = np.mean(losing_pnls) if losing_pnls else 0
            
            total_wins = sum(winning_pnls) if winning_pnls else 0
            total_losses = abs(sum(losing_pnls)) if losing_pnls else 0
            self.profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        # Calculate execution costs
        self.avg_slippage = np.mean([trade.slippage for trade in self.trades])
        self.avg_commission = np.mean([trade.commission for trade in self.trades])
        self.total_costs = sum(trade.total_cost for trade in self.trades)
    
    def _calculate_performance_metrics(self):
        """Calculate performance metrics from portfolio history"""
        if self.portfolio_history.empty or 'portfolio_value' not in self.portfolio_history.columns:
            return
        
        # Calculate returns
        portfolio_values = self.portfolio_history['portfolio_value']
        self.returns_series = portfolio_values.pct_change().dropna()
        
        if len(self.returns_series) == 0:
            return
        
        # Basic performance metrics
        self.total_return = (portfolio_values.iloc[-1] / portfolio_values.iloc[0]) - 1
        
        # Annualized metrics
        trading_days = len(self.returns_series)
        years = trading_days / 252  # Assuming 252 trading days per year
        
        if years > 0:
            self.annualized_return = (1 + self.total_return) ** (1 / years) - 1
            self.volatility = self.returns_series.std() * np.sqrt(252)
        
        # Risk-adjusted returns
        if self.volatility > 0:
            excess_returns = self.returns_series.mean() * 252 - 0.02  # Assuming 2% risk-free rate
            self.sharpe_ratio = excess_returns / self.volatility
            
            # Sortino ratio (using downside deviation)
            downside_returns = self.returns_series[self.returns_series < 0]
            if len(downside_returns) > 0:
                downside_deviation = downside_returns.std() * np.sqrt(252)
                self.sortino_ratio = excess_returns / downside_deviation
        
        # Drawdown analysis
        cumulative_returns = (1 + self.returns_series).cumprod()
        rolling_max = cumulative_returns.expanding().max()
        drawdowns = (cumulative_returns - rolling_max) / rolling_max
        self.max_drawdown = abs(drawdowns.min())
        
        # Calmar ratio
        if self.max_drawdown > 0:
            self.calmar_ratio = self.annualized_return / self.max_drawdown
        
        # VaR calculations
        self.var_95 = np.percentile(self.returns_series, 5)
        self.var_99 = np.percentile(self.returns_series, 1)
        
        # CVaR (Expected Shortfall)
        var_95_returns = self.returns_series[self.returns_series <= self.var_95]
        var_99_returns = self.returns_series[self.returns_series <= self.var_99]
        
        self.cvar_95 = var_95_returns.mean() if len(var_95_returns) > 0 else 0
        self.cvar_99 = var_99_returns.mean() if len(var_99_returns) > 0 else 0
        
        # Benchmark comparison (if benchmark returns available)
        if not self.benchmark_returns.empty and len(self.benchmark_returns) == len(self.returns_series):
            self._calculate_benchmark_metrics()
    
    def _calculate_benchmark_metrics(self):
        """Calculate benchmark comparison metrics"""
        # Align returns
        aligned_returns = pd.DataFrame({
            'strategy': self.returns_series,
            'benchmark': self.benchmark_returns
        }).dropna()
        
        if len(aligned_returns) < 2:
            return
        
        strategy_returns = aligned_returns['strategy']
        benchmark_returns = aligned_returns['benchmark']
        
        # Beta calculation
        covariance = np.cov(strategy_returns, benchmark_returns)[0, 1]
        benchmark_variance = np.var(benchmark_returns)
        
        if benchmark_variance > 0:
            self.beta = covariance / benchmark_variance
        
        # Alpha calculation (CAPM)
        strategy_mean = strategy_returns.mean() * 252
        benchmark_mean = benchmark_returns.mean() * 252
        risk_free_rate = 0.02  # Assuming 2% risk-free rate
        
        self.alpha = strategy_mean - (risk_free_rate + self.beta * (benchmark_mean - risk_free_rate))
        
        # Tracking error and information ratio
        excess_returns = strategy_returns - benchmark_returns
        self.tracking_error = excess_returns.std() * np.sqrt(252)
        
        if self.tracking_error > 0:
            self.information_ratio = (excess_returns.mean() * 252) / self.tracking_error
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics dictionary"""
        return {
            'Strategy': self.strategy_name,
            'Start Date': self.start_date.strftime('%Y-%m-%d'),
            'End Date': self.end_date.strftime('%Y-%m-%d'),
            'Initial Capital': f"${self.initial_capital:,.2f}",
            'Final Capital': f"${self.final_capital:,.2f}",
            'Total Return': f"{self.total_return:.2%}",
            'Annualized Return': f"{self.annualized_return:.2%}",
            'Volatility': f"{self.volatility:.2%}",
            'Sharpe Ratio': f"{self.sharpe_ratio:.3f}",
            'Sortino Ratio': f"{self.sortino_ratio:.3f}",
            'Calmar Ratio': f"{self.calmar_ratio:.3f}",
            'Max Drawdown': f"{self.max_drawdown:.2%}",
            'VaR (95%)': f"{self.var_95:.2%}",
            'VaR (99%)': f"{self.var_99:.2%}",
            'Alpha': f"{self.alpha:.2%}",
            'Beta': f"{self.beta:.3f}",
            'Information Ratio': f"{self.information_ratio:.3f}",
            'Total Trades': self.total_trades,
            'Win Rate': f"{self.win_rate:.2%}",
            'Profit Factor': f"{self.profit_factor:.2f}",
            'Avg Slippage': f"{self.avg_slippage:.4f}",
            'Total Costs': f"${self.total_costs:,.2f}"
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert results to dictionary for serialization"""
        return {
            'strategy_name': self.strategy_name,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'initial_capital': self.initial_capital,
            'final_capital': self.final_capital,
            'performance_metrics': {
                'total_return': self.total_return,
                'annualized_return': self.annualized_return,
                'volatility': self.volatility,
                'sharpe_ratio': self.sharpe_ratio,
                'sortino_ratio': self.sortino_ratio,
                'calmar_ratio': self.calmar_ratio,
                'max_drawdown': self.max_drawdown,
                'var_95': self.var_95,
                'var_99': self.var_99,
                'alpha': self.alpha,
                'beta': self.beta,
                'information_ratio': self.information_ratio
            },
            'trade_statistics': {
                'total_trades': self.total_trades,
                'winning_trades': self.winning_trades,
                'losing_trades': self.losing_trades,
                'win_rate': self.win_rate,
                'avg_win': self.avg_win,
                'avg_loss': self.avg_loss,
                'profit_factor': self.profit_factor
            },
            'execution_quality': {
                'avg_slippage': self.avg_slippage,
                'avg_commission': self.avg_commission,
                'total_costs': self.total_costs
            }
        }