"""Visualization Module

Comprehensive visualization system for backtesting results, performance analytics,
and risk analysis with interactive charts and professional reporting.
"""

from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dataclasses import dataclass
import logging
import warnings
warnings.filterwarnings('ignore')

# Plotting libraries
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.patches import Rectangle
    import seaborn as sns
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None
    sns = None

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import plotly.express as px
    import plotly.offline as pyo
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    go = None
    make_subplots = None
    px = None

from .results import BacktestResults, Trade, PortfolioSnapshot
from .metrics import PerformanceMetrics, RiskMetrics
from .performance_analyzer import PerformanceAnalyzer
from .risk_analyzer import RiskAnalyzer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ChartConfig:
    """Chart configuration settings"""
    width: int = 1200
    height: int = 800
    theme: str = 'plotly_white'  # 'plotly', 'plotly_white', 'plotly_dark', 'ggplot2', 'seaborn'
    color_palette: List[str] = None
    show_grid: bool = True
    show_legend: bool = True
    font_size: int = 12
    title_font_size: int = 16
    
    def __post_init__(self):
        if self.color_palette is None:
            self.color_palette = [
                '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
                '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
            ]


class VisualizationEngine:
    """Comprehensive visualization engine for backtesting results"""
    
    def __init__(self, results: BacktestResults, config: Optional[ChartConfig] = None):
        self.results = results
        self.config = config or ChartConfig()
        
        # Initialize analyzers
        self.performance_analyzer = PerformanceAnalyzer(results)
        self.risk_analyzer = RiskAnalyzer(results)
        
        # Check library availability
        if not MATPLOTLIB_AVAILABLE and not PLOTLY_AVAILABLE:
            logger.warning("Neither matplotlib nor plotly available. Limited visualization capabilities.")
        
        logger.info(f"Initialized visualization engine with {len(results.trades)} trades")
    
    def create_performance_dashboard(self, save_path: Optional[str] = None, 
                                   interactive: bool = True) -> Optional[Any]:
        """Create comprehensive performance dashboard
        
        Args:
            save_path: Path to save the dashboard
            interactive: Whether to create interactive charts (requires plotly)
        
        Returns:
            Plotly figure if interactive=True and plotly available, else None
        """
        if interactive and PLOTLY_AVAILABLE:
            return self._create_plotly_dashboard(save_path)
        elif MATPLOTLIB_AVAILABLE:
            return self._create_matplotlib_dashboard(save_path)
        else:
            logger.error("No visualization libraries available")
            return None
    
    def _create_plotly_dashboard(self, save_path: Optional[str] = None) -> go.Figure:
        """Create interactive Plotly dashboard"""
        logger.info("Creating interactive Plotly dashboard")
        
        # Create subplots
        fig = make_subplots(
            rows=4, cols=2,
            subplot_titles=[
                'Portfolio Value Over Time', 'Drawdown Analysis',
                'Monthly Returns Heatmap', 'Rolling Sharpe Ratio',
                'Trade Distribution', 'Risk Metrics',
                'Cumulative Returns vs Benchmark', 'Position Exposure'
            ],
            specs=[
                [{"secondary_y": True}, {"type": "scatter"}],
                [{"type": "heatmap"}, {"type": "scatter"}],
                [{"type": "histogram"}, {"type": "bar"}],
                [{"secondary_y": True}, {"type": "bar"}]
            ],
            vertical_spacing=0.08,
            horizontal_spacing=0.1
        )
        
        # 1. Portfolio Value Over Time
        if len(self.results.portfolio_history) > 0:
            portfolio_df = self.results.portfolio_history
            fig.add_trace(
                go.Scatter(
                    x=portfolio_df.index,
                    y=portfolio_df['portfolio_value'],
                    name='Portfolio Value',
                    line=dict(color=self.config.color_palette[0], width=2)
                ),
                row=1, col=1
            )
            
            # Add benchmark if available
            if self.results.benchmark_returns is not None:
                benchmark_cumulative = (1 + self.results.benchmark_returns).cumprod()
                initial_value = portfolio_df['portfolio_value'].iloc[0]
                benchmark_value = benchmark_cumulative * initial_value
                
                fig.add_trace(
                    go.Scatter(
                        x=benchmark_value.index,
                        y=benchmark_value.values,
                        name='Benchmark',
                        line=dict(color=self.config.color_palette[1], width=2, dash='dash')
                    ),
                    row=1, col=1
                )
        
        # 2. Drawdown Analysis
        if len(self.results.returns_series) > 0:
            cumulative_returns = (1 + self.results.returns_series).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - running_max) / running_max
            
            fig.add_trace(
                go.Scatter(
                    x=drawdown.index,
                    y=drawdown.values * 100,
                    fill='tonexty',
                    name='Drawdown %',
                    line=dict(color=self.config.color_palette[2])
                ),
                row=1, col=2
            )
        
        # 3. Monthly Returns Heatmap
        if len(self.results.returns_series) > 0:
            monthly_returns = self.results.returns_series.resample('M').apply(lambda x: (1 + x).prod() - 1)
            monthly_returns_df = monthly_returns.to_frame('returns')
            monthly_returns_df['year'] = monthly_returns_df.index.year
            monthly_returns_df['month'] = monthly_returns_df.index.month
            
            pivot_table = monthly_returns_df.pivot_table(
                values='returns', index='year', columns='month', fill_value=0
            )
            
            fig.add_trace(
                go.Heatmap(
                    z=pivot_table.values * 100,
                    x=[f'M{i}' for i in range(1, 13)],
                    y=pivot_table.index,
                    colorscale='RdYlGn',
                    name='Monthly Returns %'
                ),
                row=2, col=1
            )
        
        # 4. Rolling Sharpe Ratio
        if len(self.results.returns_series) > 0:
            rolling_sharpe = self.results.returns_series.rolling(252).apply(
                lambda x: x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0
            )
            
            fig.add_trace(
                go.Scatter(
                    x=rolling_sharpe.index,
                    y=rolling_sharpe.values,
                    name='Rolling Sharpe (252d)',
                    line=dict(color=self.config.color_palette[3])
                ),
                row=2, col=2
            )
        
        # 5. Trade Distribution
        if self.results.trades:
            trade_returns = [trade.return_pct for trade in self.results.trades if trade.return_pct is not None]
            
            fig.add_trace(
                go.Histogram(
                    x=np.array(trade_returns) * 100,
                    nbinsx=50,
                    name='Trade Returns %',
                    marker_color=self.config.color_palette[4]
                ),
                row=3, col=1
            )
        
        # 6. Risk Metrics
        risk_metrics = self.risk_analyzer.calculate_comprehensive_risk_metrics()
        risk_data = {
            'VaR 95%': risk_metrics.portfolio_var.var_95 * 100,
            'VaR 99%': risk_metrics.portfolio_var.var_99 * 100,
            'Concentration': risk_metrics.concentration_risk * 100,
            'Leverage': risk_metrics.leverage_ratio,
            'Liquidity Score': risk_metrics.liquidity_score * 100
        }
        
        fig.add_trace(
            go.Bar(
                x=list(risk_data.keys()),
                y=list(risk_data.values()),
                name='Risk Metrics',
                marker_color=self.config.color_palette[5]
            ),
            row=3, col=2
        )
        
        # 7. Cumulative Returns vs Benchmark
        if len(self.results.returns_series) > 0:
            cumulative_returns = (1 + self.results.returns_series).cumprod()
            
            fig.add_trace(
                go.Scatter(
                    x=cumulative_returns.index,
                    y=(cumulative_returns - 1) * 100,
                    name='Strategy Cumulative Return %',
                    line=dict(color=self.config.color_palette[0], width=2)
                ),
                row=4, col=1
            )
            
            if self.results.benchmark_returns is not None:
                benchmark_cumulative = (1 + self.results.benchmark_returns).cumprod()
                fig.add_trace(
                    go.Scatter(
                        x=benchmark_cumulative.index,
                        y=(benchmark_cumulative - 1) * 100,
                        name='Benchmark Cumulative Return %',
                        line=dict(color=self.config.color_palette[1], width=2, dash='dash')
                    ),
                    row=4, col=1
                )
        
        # 8. Position Exposure
        if self.results.positions_history:
            latest_positions = self.results.positions_history[-1].positions
            if latest_positions:
                symbols = [pos.symbol for pos in latest_positions]
                exposures = [abs(pos.market_value) for pos in latest_positions]
                
                fig.add_trace(
                    go.Bar(
                        x=symbols,
                        y=exposures,
                        name='Position Exposure',
                        marker_color=self.config.color_palette[6]
                    ),
                    row=4, col=2
                )
        
        # Update layout
        fig.update_layout(
            height=self.config.height * 1.5,
            width=self.config.width,
            title_text="Portfolio Performance Dashboard",
            title_font_size=self.config.title_font_size,
            showlegend=self.config.show_legend,
            template=self.config.theme
        )
        
        # Save if path provided
        if save_path:
            if save_path.endswith('.html'):
                fig.write_html(save_path)
            elif save_path.endswith('.png'):
                fig.write_image(save_path)
            else:
                fig.write_html(save_path + '.html')
            logger.info(f"Dashboard saved to {save_path}")
        
        return fig
    
    def _create_matplotlib_dashboard(self, save_path: Optional[str] = None):
        """Create static matplotlib dashboard"""
        logger.info("Creating matplotlib dashboard")
        
        # Set style
        plt.style.use('seaborn-v0_8' if hasattr(plt.style, 'seaborn-v0_8') else 'default')
        
        # Create figure with subplots
        fig, axes = plt.subplots(3, 3, figsize=(18, 15))
        fig.suptitle('Portfolio Performance Dashboard', fontsize=16, fontweight='bold')
        
        # 1. Portfolio Value Over Time
        if len(self.results.portfolio_history) > 0:
            portfolio_df = self.results.portfolio_history
            axes[0, 0].plot(portfolio_df.index, portfolio_df['portfolio_value'], 
                           color=self.config.color_palette[0], linewidth=2, label='Portfolio')
            
            if self.results.benchmark_returns is not None:
                benchmark_cumulative = (1 + self.results.benchmark_returns).cumprod()
                initial_value = portfolio_df['portfolio_value'].iloc[0]
                benchmark_value = benchmark_cumulative * initial_value
                axes[0, 0].plot(benchmark_value.index, benchmark_value.values, 
                               color=self.config.color_palette[1], linewidth=2, 
                               linestyle='--', label='Benchmark')
            
            axes[0, 0].set_title('Portfolio Value Over Time')
            axes[0, 0].legend()
            axes[0, 0].grid(True)
        
        # 2. Drawdown Analysis
        if len(self.results.returns_series) > 0:
            cumulative_returns = (1 + self.results.returns_series).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - running_max) / running_max
            
            axes[0, 1].fill_between(drawdown.index, drawdown.values * 100, 0, 
                                   color=self.config.color_palette[2], alpha=0.7)
            axes[0, 1].set_title('Drawdown Analysis')
            axes[0, 1].set_ylabel('Drawdown %')
            axes[0, 1].grid(True)
        
        # 3. Monthly Returns Heatmap
        if len(self.results.returns_series) > 0:
            monthly_returns = self.results.returns_series.resample('M').apply(lambda x: (1 + x).prod() - 1)
            monthly_returns_df = monthly_returns.to_frame('returns')
            monthly_returns_df['year'] = monthly_returns_df.index.year
            monthly_returns_df['month'] = monthly_returns_df.index.month
            
            pivot_table = monthly_returns_df.pivot_table(
                values='returns', index='year', columns='month', fill_value=0
            )
            
            if sns is not None:
                sns.heatmap(pivot_table * 100, annot=True, fmt='.1f', cmap='RdYlGn', 
                           center=0, ax=axes[0, 2])
            else:
                im = axes[0, 2].imshow(pivot_table.values * 100, cmap='RdYlGn', aspect='auto')
                axes[0, 2].set_xticks(range(len(pivot_table.columns)))
                axes[0, 2].set_xticklabels([f'M{i}' for i in pivot_table.columns])
                axes[0, 2].set_yticks(range(len(pivot_table.index)))
                axes[0, 2].set_yticklabels(pivot_table.index)
                plt.colorbar(im, ax=axes[0, 2])
            
            axes[0, 2].set_title('Monthly Returns Heatmap (%)')
        
        # 4. Rolling Sharpe Ratio
        if len(self.results.returns_series) > 0:
            rolling_sharpe = self.results.returns_series.rolling(252).apply(
                lambda x: x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0
            )
            
            axes[1, 0].plot(rolling_sharpe.index, rolling_sharpe.values, 
                           color=self.config.color_palette[3], linewidth=2)
            axes[1, 0].set_title('Rolling Sharpe Ratio (252d)')
            axes[1, 0].axhline(y=0, color='black', linestyle='-', alpha=0.3)
            axes[1, 0].grid(True)
        
        # 5. Trade Distribution
        if self.results.trades:
            trade_returns = [trade.return_pct for trade in self.results.trades if trade.return_pct is not None]
            
            axes[1, 1].hist(np.array(trade_returns) * 100, bins=50, 
                           color=self.config.color_palette[4], alpha=0.7, edgecolor='black')
            axes[1, 1].set_title('Trade Returns Distribution')
            axes[1, 1].set_xlabel('Return %')
            axes[1, 1].set_ylabel('Frequency')
            axes[1, 1].axvline(x=0, color='red', linestyle='--', alpha=0.7)
            axes[1, 1].grid(True)
        
        # 6. Risk Metrics
        risk_metrics = self.risk_analyzer.calculate_comprehensive_risk_metrics()
        risk_data = {
            'VaR 95%': risk_metrics.portfolio_var.var_95 * 100,
            'VaR 99%': risk_metrics.portfolio_var.var_99 * 100,
            'Concentration': risk_metrics.concentration_risk * 100,
            'Leverage': risk_metrics.leverage_ratio,
            'Liquidity Score': risk_metrics.liquidity_score * 100
        }
        
        bars = axes[1, 2].bar(list(risk_data.keys()), list(risk_data.values()), 
                             color=self.config.color_palette[5], alpha=0.7)
        axes[1, 2].set_title('Risk Metrics')
        axes[1, 2].tick_params(axis='x', rotation=45)
        axes[1, 2].grid(True, axis='y')
        
        # Add value labels on bars
        for bar, value in zip(bars, risk_data.values()):
            height = bar.get_height()
            axes[1, 2].text(bar.get_x() + bar.get_width()/2., height,
                           f'{value:.2f}', ha='center', va='bottom')
        
        # 7. Cumulative Returns
        if len(self.results.returns_series) > 0:
            cumulative_returns = (1 + self.results.returns_series).cumprod()
            
            axes[2, 0].plot(cumulative_returns.index, (cumulative_returns - 1) * 100, 
                           color=self.config.color_palette[0], linewidth=2, label='Strategy')
            
            if self.results.benchmark_returns is not None:
                benchmark_cumulative = (1 + self.results.benchmark_returns).cumprod()
                axes[2, 0].plot(benchmark_cumulative.index, (benchmark_cumulative - 1) * 100, 
                               color=self.config.color_palette[1], linewidth=2, 
                               linestyle='--', label='Benchmark')
            
            axes[2, 0].set_title('Cumulative Returns')
            axes[2, 0].set_ylabel('Return %')
            axes[2, 0].legend()
            axes[2, 0].grid(True)
        
        # 8. Position Exposure
        if self.results.positions_history:
            latest_positions = self.results.positions_history[-1].positions
            if latest_positions:
                symbols = [pos.symbol for pos in latest_positions[:10]]  # Top 10
                exposures = [abs(pos.market_value) for pos in latest_positions[:10]]
                
                bars = axes[2, 1].bar(symbols, exposures, color=self.config.color_palette[6], alpha=0.7)
                axes[2, 1].set_title('Top 10 Position Exposures')
                axes[2, 1].tick_params(axis='x', rotation=45)
                axes[2, 1].grid(True, axis='y')
        
        # 9. Performance Metrics Summary
        perf_analyzer = PerformanceAnalyzer(self.results)
        perf_metrics = perf_analyzer.calculate_performance_metrics()
        
        metrics_text = f"""
        Total Return: {perf_metrics.total_return:.2%}
        Annualized Return: {perf_metrics.annualized_return:.2%}
        Volatility: {perf_metrics.volatility:.2%}
        Sharpe Ratio: {perf_metrics.sharpe_ratio:.2f}
        Max Drawdown: {perf_metrics.max_drawdown:.2%}
        Win Rate: {perf_metrics.win_rate:.2%}
        Profit Factor: {perf_metrics.profit_factor:.2f}
        Calmar Ratio: {perf_metrics.calmar_ratio:.2f}
        """
        
        axes[2, 2].text(0.1, 0.9, metrics_text, transform=axes[2, 2].transAxes, 
                        fontsize=10, verticalalignment='top', 
                        bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
        axes[2, 2].set_title('Performance Summary')
        axes[2, 2].axis('off')
        
        # Adjust layout
        plt.tight_layout()
        
        # Save if path provided
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Dashboard saved to {save_path}")
        
        return fig
    
    def create_trade_analysis_chart(self, save_path: Optional[str] = None, 
                                   interactive: bool = True) -> Optional[Any]:
        """Create detailed trade analysis visualization"""
        if not self.results.trades:
            logger.warning("No trades available for analysis")
            return None
        
        if interactive and PLOTLY_AVAILABLE:
            return self._create_plotly_trade_analysis(save_path)
        elif MATPLOTLIB_AVAILABLE:
            return self._create_matplotlib_trade_analysis(save_path)
        else:
            logger.error("No visualization libraries available")
            return None
    
    def _create_plotly_trade_analysis(self, save_path: Optional[str] = None) -> go.Figure:
        """Create interactive trade analysis with Plotly"""
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=[
                'Trade P&L Over Time', 'Trade Duration vs Return',
                'Win/Loss Distribution', 'Trade Size Analysis'
            ]
        )
        
        # Prepare trade data
        trade_dates = [trade.exit_time for trade in self.results.trades if trade.exit_time]
        trade_pnl = [trade.pnl for trade in self.results.trades]
        trade_returns = [trade.return_pct for trade in self.results.trades if trade.return_pct is not None]
        trade_durations = [(trade.exit_time - trade.entry_time).total_seconds() / 3600 
                          for trade in self.results.trades 
                          if trade.exit_time and trade.entry_time]
        trade_sizes = [abs(trade.quantity * trade.entry_price) for trade in self.results.trades]
        
        # 1. Trade P&L Over Time
        cumulative_pnl = np.cumsum(trade_pnl)
        colors = ['green' if pnl > 0 else 'red' for pnl in trade_pnl]
        
        fig.add_trace(
            go.Scatter(
                x=trade_dates,
                y=cumulative_pnl,
                mode='lines+markers',
                name='Cumulative P&L',
                line=dict(color=self.config.color_palette[0], width=2)
            ),
            row=1, col=1
        )
        
        # 2. Trade Duration vs Return
        if trade_durations and trade_returns:
            fig.add_trace(
                go.Scatter(
                    x=trade_durations,
                    y=np.array(trade_returns) * 100,
                    mode='markers',
                    name='Duration vs Return',
                    marker=dict(
                        color=[self.config.color_palette[0] if r > 0 else self.config.color_palette[3] 
                              for r in trade_returns],
                        size=8
                    )
                ),
                row=1, col=2
            )
        
        # 3. Win/Loss Distribution
        winning_trades = [pnl for pnl in trade_pnl if pnl > 0]
        losing_trades = [pnl for pnl in trade_pnl if pnl < 0]
        
        fig.add_trace(
            go.Histogram(
                x=winning_trades,
                name='Winning Trades',
                marker_color='green',
                opacity=0.7,
                nbinsx=20
            ),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Histogram(
                x=losing_trades,
                name='Losing Trades',
                marker_color='red',
                opacity=0.7,
                nbinsx=20
            ),
            row=2, col=1
        )
        
        # 4. Trade Size Analysis
        fig.add_trace(
            go.Scatter(
                x=trade_sizes,
                y=trade_pnl,
                mode='markers',
                name='Size vs P&L',
                marker=dict(
                    color=[self.config.color_palette[0] if pnl > 0 else self.config.color_palette[3] 
                          for pnl in trade_pnl],
                    size=8
                )
            ),
            row=2, col=2
        )
        
        # Update layout
        fig.update_layout(
            height=800,
            width=1200,
            title_text="Trade Analysis Dashboard",
            showlegend=True
        )
        
        # Update axis labels
        fig.update_xaxes(title_text="Date", row=1, col=1)
        fig.update_yaxes(title_text="Cumulative P&L", row=1, col=1)
        
        fig.update_xaxes(title_text="Duration (hours)", row=1, col=2)
        fig.update_yaxes(title_text="Return %", row=1, col=2)
        
        fig.update_xaxes(title_text="P&L", row=2, col=1)
        fig.update_yaxes(title_text="Frequency", row=2, col=1)
        
        fig.update_xaxes(title_text="Trade Size", row=2, col=2)
        fig.update_yaxes(title_text="P&L", row=2, col=2)
        
        if save_path:
            fig.write_html(save_path)
            logger.info(f"Trade analysis saved to {save_path}")
        
        return fig
    
    def _create_matplotlib_trade_analysis(self, save_path: Optional[str] = None):
        """Create static trade analysis with matplotlib"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Trade Analysis Dashboard', fontsize=16, fontweight='bold')
        
        # Prepare trade data
        trade_dates = [trade.exit_time for trade in self.results.trades if trade.exit_time]
        trade_pnl = [trade.pnl for trade in self.results.trades]
        trade_returns = [trade.return_pct for trade in self.results.trades if trade.return_pct is not None]
        trade_durations = [(trade.exit_time - trade.entry_time).total_seconds() / 3600 
                          for trade in self.results.trades 
                          if trade.exit_time and trade.entry_time]
        trade_sizes = [abs(trade.quantity * trade.entry_price) for trade in self.results.trades]
        
        # 1. Trade P&L Over Time
        cumulative_pnl = np.cumsum(trade_pnl)
        axes[0, 0].plot(trade_dates, cumulative_pnl, color=self.config.color_palette[0], linewidth=2)
        axes[0, 0].set_title('Cumulative Trade P&L')
        axes[0, 0].set_ylabel('Cumulative P&L')
        axes[0, 0].grid(True)
        
        # 2. Trade Duration vs Return
        if trade_durations and trade_returns:
            colors = ['green' if r > 0 else 'red' for r in trade_returns]
            axes[0, 1].scatter(trade_durations, np.array(trade_returns) * 100, c=colors, alpha=0.6)
            axes[0, 1].set_title('Trade Duration vs Return')
            axes[0, 1].set_xlabel('Duration (hours)')
            axes[0, 1].set_ylabel('Return %')
            axes[0, 1].axhline(y=0, color='black', linestyle='--', alpha=0.5)
            axes[0, 1].grid(True)
        
        # 3. Win/Loss Distribution
        winning_trades = [pnl for pnl in trade_pnl if pnl > 0]
        losing_trades = [pnl for pnl in trade_pnl if pnl < 0]
        
        axes[1, 0].hist(winning_trades, bins=20, color='green', alpha=0.7, label='Winning Trades')
        axes[1, 0].hist(losing_trades, bins=20, color='red', alpha=0.7, label='Losing Trades')
        axes[1, 0].set_title('Win/Loss Distribution')
        axes[1, 0].set_xlabel('P&L')
        axes[1, 0].set_ylabel('Frequency')
        axes[1, 0].legend()
        axes[1, 0].grid(True)
        
        # 4. Trade Size Analysis
        colors = ['green' if pnl > 0 else 'red' for pnl in trade_pnl]
        axes[1, 1].scatter(trade_sizes, trade_pnl, c=colors, alpha=0.6)
        axes[1, 1].set_title('Trade Size vs P&L')
        axes[1, 1].set_xlabel('Trade Size')
        axes[1, 1].set_ylabel('P&L')
        axes[1, 1].axhline(y=0, color='black', linestyle='--', alpha=0.5)
        axes[1, 1].grid(True)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Trade analysis saved to {save_path}")
        
        return fig
    
    def create_risk_dashboard(self, save_path: Optional[str] = None, 
                             interactive: bool = True) -> Optional[Any]:
        """Create comprehensive risk analysis dashboard"""
        if interactive and PLOTLY_AVAILABLE:
            return self._create_plotly_risk_dashboard(save_path)
        elif MATPLOTLIB_AVAILABLE:
            return self._create_matplotlib_risk_dashboard(save_path)
        else:
            logger.error("No visualization libraries available")
            return None
    
    def _create_plotly_risk_dashboard(self, save_path: Optional[str] = None) -> go.Figure:
        """Create interactive risk dashboard with Plotly"""
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=[
                'VaR Analysis', 'Drawdown Distribution',
                'Rolling Volatility', 'Correlation Heatmap',
                'Stress Test Results', 'Risk Attribution'
            ],
            specs=[
                [{"type": "scatter"}, {"type": "histogram"}],
                [{"type": "scatter"}, {"type": "heatmap"}],
                [{"type": "bar"}, {"type": "pie"}]
            ]
        )
        
        # Calculate risk metrics
        risk_metrics = self.risk_analyzer.calculate_comprehensive_risk_metrics()
        
        # 1. VaR Analysis
        var_data = {
            'VaR 95%': risk_metrics.portfolio_var.var_95 * 100,
            'VaR 99%': risk_metrics.portfolio_var.var_99 * 100,
            'CVaR 95%': risk_metrics.portfolio_var.cvar_95 * 100,
            'CVaR 99%': risk_metrics.portfolio_var.cvar_99 * 100
        }
        
        fig.add_trace(
            go.Bar(
                x=list(var_data.keys()),
                y=list(var_data.values()),
                name='VaR Metrics',
                marker_color=self.config.color_palette[0]
            ),
            row=1, col=1
        )
        
        # 2. Drawdown Distribution
        if len(self.results.returns_series) > 0:
            cumulative_returns = (1 + self.results.returns_series).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdowns = (cumulative_returns - running_max) / running_max
            
            fig.add_trace(
                go.Histogram(
                    x=drawdowns.values * 100,
                    nbinsx=50,
                    name='Drawdown Distribution',
                    marker_color=self.config.color_palette[1]
                ),
                row=1, col=2
            )
        
        # 3. Rolling Volatility
        if len(self.results.returns_series) > 0:
            rolling_vol = self.results.returns_series.rolling(63).std() * np.sqrt(252)
            
            fig.add_trace(
                go.Scatter(
                    x=rolling_vol.index,
                    y=rolling_vol.values * 100,
                    name='Rolling Volatility (63d)',
                    line=dict(color=self.config.color_palette[2])
                ),
                row=2, col=1
            )
        
        # 4. Correlation Heatmap (simplified)
        if len(self.results.returns_series) > 0 and self.results.benchmark_returns is not None:
            corr_matrix = pd.DataFrame({
                'Strategy': self.results.returns_series,
                'Benchmark': self.results.benchmark_returns
            }).corr()
            
            fig.add_trace(
                go.Heatmap(
                    z=corr_matrix.values,
                    x=corr_matrix.columns,
                    y=corr_matrix.index,
                    colorscale='RdBu',
                    zmid=0
                ),
                row=2, col=2
            )
        
        # 5. Stress Test Results
        stress_results = self.risk_analyzer.run_stress_tests()
        scenario_names = [result.scenario_name for result in stress_results]
        scenario_returns = [result.portfolio_return * 100 for result in stress_results]
        
        fig.add_trace(
            go.Bar(
                x=scenario_names,
                y=scenario_returns,
                name='Stress Test Returns',
                marker_color=['red' if r < 0 else 'green' for r in scenario_returns]
            ),
            row=3, col=1
        )
        
        # 6. Risk Attribution
        risk_attribution = risk_metrics.risk_attribution
        
        fig.add_trace(
            go.Pie(
                labels=list(risk_attribution.keys()),
                values=list(risk_attribution.values()),
                name='Risk Attribution'
            ),
            row=3, col=2
        )
        
        # Update layout
        fig.update_layout(
            height=1200,
            width=1200,
            title_text="Risk Analysis Dashboard",
            showlegend=True
        )
        
        if save_path:
            fig.write_html(save_path)
            logger.info(f"Risk dashboard saved to {save_path}")
        
        return fig
    
    def _create_matplotlib_risk_dashboard(self, save_path: Optional[str] = None):
        """Create static risk dashboard with matplotlib"""
        fig, axes = plt.subplots(3, 2, figsize=(15, 12))
        fig.suptitle('Risk Analysis Dashboard', fontsize=16, fontweight='bold')
        
        # Calculate risk metrics
        risk_metrics = self.risk_analyzer.calculate_comprehensive_risk_metrics()
        
        # 1. VaR Analysis
        var_data = {
            'VaR 95%': risk_metrics.portfolio_var.var_95 * 100,
            'VaR 99%': risk_metrics.portfolio_var.var_99 * 100,
            'CVaR 95%': risk_metrics.portfolio_var.cvar_95 * 100,
            'CVaR 99%': risk_metrics.portfolio_var.cvar_99 * 100
        }
        
        bars = axes[0, 0].bar(list(var_data.keys()), list(var_data.values()), 
                             color=self.config.color_palette[0], alpha=0.7)
        axes[0, 0].set_title('VaR Analysis')
        axes[0, 0].set_ylabel('Value at Risk %')
        axes[0, 0].tick_params(axis='x', rotation=45)
        axes[0, 0].grid(True, axis='y')
        
        # 2. Drawdown Distribution
        if len(self.results.returns_series) > 0:
            cumulative_returns = (1 + self.results.returns_series).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdowns = (cumulative_returns - running_max) / running_max
            
            axes[0, 1].hist(drawdowns.values * 100, bins=50, 
                           color=self.config.color_palette[1], alpha=0.7, edgecolor='black')
            axes[0, 1].set_title('Drawdown Distribution')
            axes[0, 1].set_xlabel('Drawdown %')
            axes[0, 1].set_ylabel('Frequency')
            axes[0, 1].grid(True)
        
        # 3. Rolling Volatility
        if len(self.results.returns_series) > 0:
            rolling_vol = self.results.returns_series.rolling(63).std() * np.sqrt(252)
            
            axes[1, 0].plot(rolling_vol.index, rolling_vol.values * 100, 
                           color=self.config.color_palette[2], linewidth=2)
            axes[1, 0].set_title('Rolling Volatility (63d)')
            axes[1, 0].set_ylabel('Volatility %')
            axes[1, 0].grid(True)
        
        # 4. Correlation Heatmap
        if len(self.results.returns_series) > 0 and self.results.benchmark_returns is not None:
            corr_matrix = pd.DataFrame({
                'Strategy': self.results.returns_series,
                'Benchmark': self.results.benchmark_returns
            }).corr()
            
            if sns is not None:
                sns.heatmap(corr_matrix, annot=True, cmap='RdBu', center=0, ax=axes[1, 1])
            else:
                im = axes[1, 1].imshow(corr_matrix.values, cmap='RdBu', aspect='auto')
                axes[1, 1].set_xticks(range(len(corr_matrix.columns)))
                axes[1, 1].set_xticklabels(corr_matrix.columns)
                axes[1, 1].set_yticks(range(len(corr_matrix.index)))
                axes[1, 1].set_yticklabels(corr_matrix.index)
                plt.colorbar(im, ax=axes[1, 1])
            
            axes[1, 1].set_title('Correlation Matrix')
        
        # 5. Stress Test Results
        stress_results = self.risk_analyzer.run_stress_tests()
        scenario_names = [result.scenario_name for result in stress_results]
        scenario_returns = [result.portfolio_return * 100 for result in stress_results]
        
        colors = ['red' if r < 0 else 'green' for r in scenario_returns]
        bars = axes[2, 0].bar(scenario_names, scenario_returns, color=colors, alpha=0.7)
        axes[2, 0].set_title('Stress Test Results')
        axes[2, 0].set_ylabel('Portfolio Return %')
        axes[2, 0].tick_params(axis='x', rotation=45)
        axes[2, 0].axhline(y=0, color='black', linestyle='--', alpha=0.5)
        axes[2, 0].grid(True, axis='y')
        
        # 6. Risk Attribution
        risk_attribution = risk_metrics.risk_attribution
        
        axes[2, 1].pie(list(risk_attribution.values()), labels=list(risk_attribution.keys()), 
                      autopct='%1.1f%%', colors=self.config.color_palette[:len(risk_attribution)])
        axes[2, 1].set_title('Risk Attribution')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Risk dashboard saved to {save_path}")
        
        return fig
    
    def generate_html_report(self, save_path: str) -> str:
        """Generate comprehensive HTML report
        
        Args:
            save_path: Path to save the HTML report
        
        Returns:
            HTML content as string
        """
        logger.info("Generating comprehensive HTML report")
        
        # Calculate metrics
        perf_analyzer = PerformanceAnalyzer(self.results)
        perf_metrics = perf_analyzer.calculate_performance_metrics()
        risk_metrics = self.risk_analyzer.calculate_comprehensive_risk_metrics()
        
        # Generate charts
        dashboard_html = ""
        trade_analysis_html = ""
        risk_dashboard_html = ""
        
        if PLOTLY_AVAILABLE:
            # Create charts and get HTML
            dashboard_fig = self._create_plotly_dashboard()
            dashboard_html = dashboard_fig.to_html(include_plotlyjs='cdn', div_id='dashboard')
            
            trade_fig = self._create_plotly_trade_analysis()
            if trade_fig:
                trade_analysis_html = trade_fig.to_html(include_plotlyjs='cdn', div_id='trade_analysis')
            
            risk_fig = self._create_plotly_risk_dashboard()
            risk_dashboard_html = risk_fig.to_html(include_plotlyjs='cdn', div_id='risk_dashboard')
        
        # Generate HTML content
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Backtesting Report</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 1400px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 0 20px rgba(0,0,0,0.1);
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 40px;
                    border-bottom: 2px solid #e0e0e0;
                    padding-bottom: 20px;
                }}
                .metrics-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                    margin-bottom: 40px;
                }}
                .metric-card {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 10px;
                    text-align: center;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                }}
                .metric-value {{
                    font-size: 2em;
                    font-weight: bold;
                    margin-bottom: 5px;
                }}
                .metric-label {{
                    font-size: 0.9em;
                    opacity: 0.9;
                }}
                .section {{
                    margin: 40px 0;
                }}
                .section-title {{
                    font-size: 1.8em;
                    color: #333;
                    border-left: 4px solid #667eea;
                    padding-left: 15px;
                    margin-bottom: 20px;
                }}
                .chart-container {{
                    margin: 20px 0;
                    padding: 20px;
                    background-color: #fafafa;
                    border-radius: 8px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                th, td {{
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }}
                th {{
                    background-color: #f8f9fa;
                    font-weight: bold;
                }}
                .positive {{ color: #28a745; }}
                .negative {{ color: #dc3545; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Backtesting Performance Report</h1>
                    <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-value">{perf_metrics.total_return:.2%}</div>
                        <div class="metric-label">Total Return</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{perf_metrics.annualized_return:.2%}</div>
                        <div class="metric-label">Annualized Return</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{perf_metrics.sharpe_ratio:.2f}</div>
                        <div class="metric-label">Sharpe Ratio</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{perf_metrics.max_drawdown:.2%}</div>
                        <div class="metric-label">Max Drawdown</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{perf_metrics.win_rate:.2%}</div>
                        <div class="metric-label">Win Rate</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{risk_metrics.portfolio_var.var_95:.2%}</div>
                        <div class="metric-label">VaR 95%</div>
                    </div>
                </div>
                
                <div class="section">
                    <h2 class="section-title">Performance Dashboard</h2>
                    <div class="chart-container">
                        {dashboard_html}
                    </div>
                </div>
                
                <div class="section">
                    <h2 class="section-title">Trade Analysis</h2>
                    <div class="chart-container">
                        {trade_analysis_html}
                    </div>
                </div>
                
                <div class="section">
                    <h2 class="section-title">Risk Analysis</h2>
                    <div class="chart-container">
                        {risk_dashboard_html}
                    </div>
                </div>
                
                <div class="section">
                    <h2 class="section-title">Detailed Metrics</h2>
                    <table>
                        <tr><th>Metric</th><th>Value</th></tr>
                        <tr><td>Total Trades</td><td>{len(self.results.trades)}</td></tr>
                        <tr><td>Winning Trades</td><td>{len([t for t in self.results.trades if t.pnl > 0])}</td></tr>
                        <tr><td>Losing Trades</td><td>{len([t for t in self.results.trades if t.pnl < 0])}</td></tr>
                        <tr><td>Average Trade</td><td class="{'positive' if perf_metrics.avg_trade_return > 0 else 'negative'}">{perf_metrics.avg_trade_return:.2%}</td></tr>
                        <tr><td>Profit Factor</td><td>{perf_metrics.profit_factor:.2f}</td></tr>
                        <tr><td>Calmar Ratio</td><td>{perf_metrics.calmar_ratio:.2f}</td></tr>
                        <tr><td>Volatility</td><td>{perf_metrics.volatility:.2%}</td></tr>
                        <tr><td>Skewness</td><td>{perf_metrics.skewness:.2f}</td></tr>
                        <tr><td>Kurtosis</td><td>{perf_metrics.kurtosis:.2f}</td></tr>
                    </table>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Save HTML report
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML report saved to {save_path}")
        return html_content
    
    def export_charts(self, output_dir: str, formats: List[str] = ['html', 'png']):
        """Export all charts to specified directory
        
        Args:
            output_dir: Output directory for charts
            formats: List of formats to export ('html', 'png', 'svg')
        """
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"Exporting charts to {output_dir}")
        
        # Export performance dashboard
        for fmt in formats:
            dashboard_path = os.path.join(output_dir, f'performance_dashboard.{fmt}')
            self.create_performance_dashboard(dashboard_path, interactive=(fmt == 'html'))
        
        # Export trade analysis
        for fmt in formats:
            trade_path = os.path.join(output_dir, f'trade_analysis.{fmt}')
            self.create_trade_analysis_chart(trade_path, interactive=(fmt == 'html'))
        
        # Export risk dashboard
        for fmt in formats:
            risk_path = os.path.join(output_dir, f'risk_dashboard.{fmt}')
            self.create_risk_dashboard(risk_path, interactive=(fmt == 'html'))
        
        # Export comprehensive HTML report
        report_path = os.path.join(output_dir, 'comprehensive_report.html')
        self.generate_html_report(report_path)
        
        logger.info(f"All charts exported to {output_dir}")