"""
Portfolio Performance Analytics Charts
Advanced portfolio analytics with performance attribution and risk metrics
"""
import logging
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import seaborn as sns
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class PerformanceMetric(Enum):
    """Performance metrics"""
    TOTAL_RETURN = "total_return"
    ANNUALIZED_RETURN = "annualized_return"
    VOLATILITY = "volatility"
    SHARPE_RATIO = "sharpe_ratio"
    SORTINO_RATIO = "sortino_ratio"
    MAX_DRAWDOWN = "max_drawdown"
    CALMAR_RATIO = "calmar_ratio"
    ALPHA = "alpha"
    BETA = "beta"
    INFORMATION_RATIO = "information_ratio"


@dataclass
class PerformanceData:
    """Portfolio performance data"""
    dates: List[datetime]
    values: List[float]
    returns: List[float]
    benchmark_values: List[float] = field(default_factory=list)
    benchmark_returns: List[float] = field(default_factory=list)
    positions: Dict[str, List[float]] = field(default_factory=dict)
    cash: List[float] = field(default_factory=list)


@dataclass
class RiskMetrics:
    """Risk metrics data"""
    var_95: float
    var_99: float
    cvar_95: float
    cvar_99: float
    max_drawdown: float
    volatility: float
    downside_deviation: float
    beta: float
    correlation: float


@dataclass
class AttributionData:
    """Performance attribution data"""
    asset_allocation: Dict[str, float]
    sector_allocation: Dict[str, float]
    security_selection: Dict[str, float]
    interaction_effect: Dict[str, float]
    total_attribution: float


class PerformanceCalculator:
    """Portfolio performance calculations"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def calculate_returns(self, values: List[float]) -> List[float]:
        """Calculate returns from values"""
        if len(values) < 2:
            return []
        
        returns = []
        for i in range(1, len(values)):
            if values[i-1] != 0:
                ret = (values[i] - values[i-1]) / values[i-1]
                returns.append(ret)
            else:
                returns.append(0.0)
        
        return returns
    
    def calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio"""
        if not returns:
            return 0.0
        
        excess_returns = [r - risk_free_rate/252 for r in returns]  # Daily risk-free rate
        mean_excess = np.mean(excess_returns)
        std_excess = np.std(excess_returns, ddof=1)
        
        if std_excess == 0:
            return 0.0
        
        return (mean_excess / std_excess) * np.sqrt(252)  # Annualized
    
    def calculate_sortino_ratio(self, returns: List[float], risk_free_rate: float = 0.02) -> float:
        """Calculate Sortino ratio"""
        if not returns:
            return 0.0
        
        excess_returns = [r - risk_free_rate/252 for r in returns]
        mean_excess = np.mean(excess_returns)
        
        # Downside deviation
        downside_returns = [r for r in excess_returns if r < 0]
        if not downside_returns:
            return float('inf') if mean_excess > 0 else 0.0
        
        downside_std = np.std(downside_returns, ddof=1)
        if downside_std == 0:
            return 0.0
        
        return (mean_excess / downside_std) * np.sqrt(252)
    
    def calculate_max_drawdown(self, values: List[float]) -> Tuple[float, int, int]:
        """Calculate maximum drawdown and its duration"""
        if len(values) < 2:
            return 0.0, 0, 0
        
        peak = values[0]
        max_dd = 0.0
        max_dd_start = 0
        max_dd_end = 0
        current_dd_start = 0
        
        for i, value in enumerate(values):
            if value > peak:
                peak = value
                current_dd_start = i
            else:
                dd = (peak - value) / peak
                if dd > max_dd:
                    max_dd = dd
                    max_dd_start = current_dd_start
                    max_dd_end = i
        
        return max_dd, max_dd_start, max_dd_end
    
    def calculate_var(self, returns: List[float], confidence: float = 0.95) -> float:
        """Calculate Value at Risk"""
        if not returns:
            return 0.0
        
        return np.percentile(returns, (1 - confidence) * 100)
    
    def calculate_cvar(self, returns: List[float], confidence: float = 0.95) -> float:
        """Calculate Conditional Value at Risk"""
        if not returns:
            return 0.0
        
        var = self.calculate_var(returns, confidence)
        tail_returns = [r for r in returns if r <= var]
        
        if not tail_returns:
            return var
        
        return np.mean(tail_returns)
    
    def calculate_beta(self, portfolio_returns: List[float], 
                     benchmark_returns: List[float]) -> float:
        """Calculate portfolio beta"""
        if len(portfolio_returns) != len(benchmark_returns) or len(portfolio_returns) < 2:
            return 0.0
        
        covariance = np.cov(portfolio_returns, benchmark_returns)[0][1]
        benchmark_variance = np.var(benchmark_returns, ddof=1)
        
        if benchmark_variance == 0:
            return 0.0
        
        return covariance / benchmark_variance
    
    def calculate_alpha(self, portfolio_returns: List[float], 
                       benchmark_returns: List[float], 
                       risk_free_rate: float = 0.02) -> float:
        """Calculate portfolio alpha"""
        if len(portfolio_returns) != len(benchmark_returns):
            return 0.0
        
        beta = self.calculate_beta(portfolio_returns, benchmark_returns)
        
        portfolio_mean = np.mean(portfolio_returns) * 252  # Annualized
        benchmark_mean = np.mean(benchmark_returns) * 252  # Annualized
        
        alpha = portfolio_mean - (risk_free_rate + beta * (benchmark_mean - risk_free_rate))
        return alpha


class PortfolioAnalyticsCharts:
    """Portfolio analytics chart generator"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.calculator = PerformanceCalculator()
    
    def create_performance_chart(self, data: PerformanceData, 
                               container_id: str = "performance_chart") -> str:
        """Create comprehensive performance chart"""
        if not PLOTLY_AVAILABLE:
            return self._create_text_chart("Performance chart requires Plotly")
        
        try:
            # Create subplots
            fig = make_subplots(
                rows=3, cols=2,
                subplot_titles=('Portfolio Value', 'Returns Distribution', 
                              'Rolling Sharpe Ratio', 'Drawdown', 
                              'Risk-Return Scatter', 'Monthly Returns Heatmap'),
                specs=[[{"secondary_y": False}, {"secondary_y": False}],
                       [{"secondary_y": False}, {"secondary_y": False}],
                       [{"secondary_y": False}, {"secondary_y": False}]]
            )
            
            # 1. Portfolio Value Chart
            fig.add_trace(
                go.Scatter(
                    x=data.dates,
                    y=data.values,
                    name='Portfolio',
                    line=dict(color='#4a90e2', width=2)
                ),
                row=1, col=1
            )
            
            if data.benchmark_values:
                fig.add_trace(
                    go.Scatter(
                        x=data.dates,
                        y=data.benchmark_values,
                        name='Benchmark',
                        line=dict(color='#ff6b6b', width=2)
                    ),
                    row=1, col=1
                )
            
            # 2. Returns Distribution
            fig.add_trace(
                go.Histogram(
                    x=data.returns,
                    name='Returns',
                    nbinsx=50,
                    marker_color='#4a90e2',
                    opacity=0.7
                ),
                row=1, col=2
            )
            
            # 3. Rolling Sharpe Ratio
            if len(data.returns) > 60:  # Need at least 60 days for rolling calculation
                rolling_sharpe = self._calculate_rolling_sharpe(data.returns, window=60)
                fig.add_trace(
                    go.Scatter(
                        x=data.dates[60:],
                        y=rolling_sharpe,
                        name='Rolling Sharpe',
                        line=dict(color='#4ecdc4', width=2)
                    ),
                    row=2, col=1
                )
            
            # 4. Drawdown Chart
            drawdown = self._calculate_drawdown_series(data.values)
            fig.add_trace(
                go.Scatter(
                    x=data.dates,
                    y=drawdown,
                    name='Drawdown',
                    fill='tozeroy',
                    fillcolor='rgba(255, 107, 107, 0.3)',
                    line=dict(color='#ff6b6b', width=1)
                ),
                row=2, col=2
            )
            
            # 5. Risk-Return Scatter (if benchmark available)
            if data.benchmark_returns:
                fig.add_trace(
                    go.Scatter(
                        x=[np.std(data.benchmark_returns) * np.sqrt(252)],
                        y=[np.mean(data.benchmark_returns) * 252],
                        mode='markers',
                        name='Benchmark',
                        marker=dict(size=12, color='#ff6b6b')
                    ),
                    row=3, col=1
                )
                
                fig.add_trace(
                    go.Scatter(
                        x=[np.std(data.returns) * np.sqrt(252)],
                        y=[np.mean(data.returns) * 252],
                        mode='markers',
                        name='Portfolio',
                        marker=dict(size=12, color='#4a90e2')
                    ),
                    row=3, col=1
                )
            
            # 6. Monthly Returns Heatmap
            monthly_returns = self._calculate_monthly_returns(data.dates, data.returns)
            if monthly_returns:
                years = sorted(monthly_returns.keys())
                months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                         'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                
                z_data = []
                for year in years:
                    year_data = []
                    for month in range(1, 13):
                        value = monthly_returns[year].get(month, None)
                        year_data.append(value)
                    z_data.append(year_data)
                
                fig.add_trace(
                    go.Heatmap(
                        z=z_data,
                        x=months,
                        y=years,
                        colorscale='RdYlGn',
                        zmid=0,
                        showscale=False
                    ),
                    row=3, col=2
                )
            
            # Update layout
            fig.update_layout(
                height=900,
                showlegend=True,
                title_text="Portfolio Performance Analytics",
                title_x=0.5
            )
            
            return fig.to_html(include_plotlyjs='cdn', div_id=container_id)
            
        except Exception as e:
            self.logger.error(f"Error creating performance chart: {e}")
            return self._create_text_chart(f"Error: {e}")
    
    def create_risk_metrics_dashboard(self, data: PerformanceData,
                                    container_id: str = "risk_dashboard") -> str:
        """Create risk metrics dashboard"""
        if not PLOTLY_AVAILABLE:
            return self._create_text_chart("Risk dashboard requires Plotly")
        
        try:
            # Calculate risk metrics
            risk_metrics = self._calculate_risk_metrics(data)
            
            # Create dashboard layout
            fig = make_subplots(
                rows=2, cols=3,
                subplot_titles=('VaR Analysis', 'Risk Decomposition', 'Correlation Matrix',
                              'Risk Over Time', 'Tail Risk', 'Risk-Adjusted Returns'),
                specs=[[{"type": "bar"}, {"type": "pie"}, {"type": "heatmap"}],
                       [{"type": "scatter"}, {"type": "histogram"}, {"type": "bar"}]]
            )
            
            # 1. VaR Analysis
            var_data = {
                'VaR 95%': risk_metrics.var_95,
                'VaR 99%': risk_metrics.var_99,
                'CVaR 95%': risk_metrics.cvar_95,
                'CVaR 99%': risk_metrics.cvar_99
            }
            
            fig.add_trace(
                go.Bar(
                    x=list(var_data.keys()),
                    y=list(var_data.values()),
                    marker_color=['#ff6b6b', '#ff4757', '#ff3838', '#ff1e1e']
                ),
                row=1, col=1
            )
            
            # 2. Risk Decomposition (pie chart)
            risk_components = {
                'Market Risk': 0.6,
                'Specific Risk': 0.25,
                'Currency Risk': 0.1,
                'Other': 0.05
            }
            
            fig.add_trace(
                go.Pie(
                    labels=list(risk_components.keys()),
                    values=list(risk_components.values()),
                    hole=0.3
                ),
                row=1, col=2
            )
            
            # 3. Correlation Matrix (sample data)
            if data.positions:
                symbols = list(data.positions.keys())[:5]  # Top 5 positions
                corr_matrix = np.random.rand(len(symbols), len(symbols))
                corr_matrix = (corr_matrix + corr_matrix.T) / 2  # Make symmetric
                np.fill_diagonal(corr_matrix, 1)  # Diagonal = 1
                
                fig.add_trace(
                    go.Heatmap(
                        z=corr_matrix,
                        x=symbols,
                        y=symbols,
                        colorscale='RdBu',
                        zmid=0
                    ),
                    row=1, col=3
                )
            
            # 4. Risk Over Time
            if len(data.returns) > 30:
                rolling_vol = self._calculate_rolling_volatility(data.returns, window=30)
                fig.add_trace(
                    go.Scatter(
                        x=data.dates[30:],
                        y=rolling_vol,
                        name='Rolling Volatility',
                        line=dict(color='#4a90e2')
                    ),
                    row=2, col=1
                )
            
            # 5. Tail Risk Distribution
            tail_returns = [r for r in data.returns if r < np.percentile(data.returns, 5)]
            if tail_returns:
                fig.add_trace(
                    go.Histogram(
                        x=tail_returns,
                        name='Tail Returns',
                        marker_color='#ff6b6b',
                        opacity=0.7
                    ),
                    row=2, col=2
                )
            
            # 6. Risk-Adjusted Returns
            sharpe = self.calculator.calculate_sharpe_ratio(data.returns)
            sortino = self.calculator.calculate_sortino_ratio(data.returns)
            calmar = -np.mean(data.returns) * 252 / risk_metrics.max_drawdown if risk_metrics.max_drawdown > 0 else 0
            
            risk_adj_metrics = {
                'Sharpe Ratio': sharpe,
                'Sortino Ratio': sortino,
                'Calmar Ratio': calmar
            }
            
            fig.add_trace(
                go.Bar(
                    x=list(risk_adj_metrics.keys()),
                    y=list(risk_adj_metrics.values()),
                    marker_color=['#4a90e2', '#4ecdc4', '#45b7d1']
                ),
                row=2, col=3
            )
            
            fig.update_layout(
                height=800,
                showlegend=False,
                title_text="Risk Metrics Dashboard",
                title_x=0.5
            )
            
            return fig.to_html(include_plotlyjs='cdn', div_id=container_id)
            
        except Exception as e:
            self.logger.error(f"Error creating risk dashboard: {e}")
            return self._create_text_chart(f"Error: {e}")
    
    def create_attribution_analysis(self, attribution_data: AttributionData,
                                  container_id: str = "attribution_chart") -> str:
        """Create performance attribution analysis chart"""
        if not PLOTLY_AVAILABLE:
            return self._create_text_chart("Attribution analysis requires Plotly")
        
        try:
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('Asset Allocation Effect', 'Security Selection Effect',
                              'Sector Attribution', 'Total Attribution Waterfall'),
                specs=[[{"type": "bar"}, {"type": "bar"}],
                       [{"type": "bar"}, {"type": "waterfall"}]]
            )
            
            # 1. Asset Allocation Effect
            fig.add_trace(
                go.Bar(
                    x=list(attribution_data.asset_allocation.keys()),
                    y=list(attribution_data.asset_allocation.values()),
                    name='Asset Allocation',
                    marker_color='#4a90e2'
                ),
                row=1, col=1
            )
            
            # 2. Security Selection Effect
            fig.add_trace(
                go.Bar(
                    x=list(attribution_data.security_selection.keys()),
                    y=list(attribution_data.security_selection.values()),
                    name='Security Selection',
                    marker_color='#4ecdc4'
                ),
                row=1, col=2
            )
            
            # 3. Sector Attribution
            fig.add_trace(
                go.Bar(
                    x=list(attribution_data.sector_allocation.keys()),
                    y=list(attribution_data.sector_allocation.values()),
                    name='Sector Attribution',
                    marker_color='#45b7d1'
                ),
                row=2, col=1
            )
            
            # 4. Attribution Waterfall
            categories = ['Asset Allocation', 'Security Selection', 'Interaction', 'Total']
            values = [
                sum(attribution_data.asset_allocation.values()),
                sum(attribution_data.security_selection.values()),
                sum(attribution_data.interaction_effect.values()),
                attribution_data.total_attribution
            ]
            
            fig.add_trace(
                go.Waterfall(
                    x=categories,
                    y=values,
                    connector={"line": {"color": "rgb(63, 63, 63)"}},
                    decreasing={"marker": {"color": "#ff6b6b"}},
                    increasing={"marker": {"color": "#4a90e2"}},
                    totals={"marker": {"color": "#4ecdc4"}}
                ),
                row=2, col=2
            )
            
            fig.update_layout(
                height=700,
                showlegend=False,
                title_text="Performance Attribution Analysis",
                title_x=0.5
            )
            
            return fig.to_html(include_plotlyjs='cdn', div_id=container_id)
            
        except Exception as e:
            self.logger.error(f"Error creating attribution chart: {e}")
            return self._create_text_chart(f"Error: {e}")
    
    def _calculate_rolling_sharpe(self, returns: List[float], window: int = 60) -> List[float]:
        """Calculate rolling Sharpe ratio"""
        rolling_sharpe = []
        for i in range(window, len(returns)):
            window_returns = returns[i-window:i]
            sharpe = self.calculator.calculate_sharpe_ratio(window_returns)
            rolling_sharpe.append(sharpe)
        return rolling_sharpe
    
    def _calculate_rolling_volatility(self, returns: List[float], window: int = 30) -> List[float]:
        """Calculate rolling volatility"""
        rolling_vol = []
        for i in range(window, len(returns)):
            window_returns = returns[i-window:i]
            vol = np.std(window_returns) * np.sqrt(252)  # Annualized
            rolling_vol.append(vol)
        return rolling_vol
    
    def _calculate_drawdown_series(self, values: List[float]) -> List[float]:
        """Calculate drawdown series"""
        if not values:
            return []
        
        peak = values[0]
        drawdowns = []
        
        for value in values:
            if value > peak:
                peak = value
            
            drawdown = (value - peak) / peak if peak > 0 else 0
            drawdowns.append(drawdown)
        
        return drawdowns
    
    def _calculate_monthly_returns(self, dates: List[datetime], 
                                 returns: List[float]) -> Dict[int, Dict[int, float]]:
        """Calculate monthly returns"""
        if len(dates) != len(returns) + 1:  # dates includes start date
            return {}
        
        monthly_returns = {}
        current_month_start = 0
        
        for i, date in enumerate(dates[1:], 1):  # Skip first date
            if i == len(dates) - 1 or date.month != dates[i-1].month:
                # End of month or end of data
                month_returns = returns[current_month_start:i]
                if month_returns:
                    # Calculate compound monthly return
                    monthly_return = np.prod([1 + r for r in month_returns]) - 1
                    
                    year = dates[i-1].year
                    month = dates[i-1].month
                    
                    if year not in monthly_returns:
                        monthly_returns[year] = {}
                    
                    monthly_returns[year][month] = monthly_return
                
                current_month_start = i
        
        return monthly_returns
    
    def _calculate_risk_metrics(self, data: PerformanceData) -> RiskMetrics:
        """Calculate comprehensive risk metrics"""
        returns = data.returns
        
        var_95 = self.calculator.calculate_var(returns, 0.95)
        var_99 = self.calculator.calculate_var(returns, 0.99)
        cvar_95 = self.calculator.calculate_cvar(returns, 0.95)
        cvar_99 = self.calculator.calculate_cvar(returns, 0.99)
        
        max_dd, _, _ = self.calculator.calculate_max_drawdown(data.values)
        volatility = np.std(returns) * np.sqrt(252) if returns else 0
        
        # Downside deviation
        downside_returns = [r for r in returns if r < 0]
        downside_deviation = np.std(downside_returns) * np.sqrt(252) if downside_returns else 0
        
        # Beta and correlation with benchmark
        beta = 0.0
        correlation = 0.0
        if data.benchmark_returns and len(data.benchmark_returns) == len(returns):
            beta = self.calculator.calculate_beta(returns, data.benchmark_returns)
            correlation = np.corrcoef(returns, data.benchmark_returns)[0][1] if len(returns) > 1 else 0
        
        return RiskMetrics(
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            cvar_99=cvar_99,
            max_drawdown=max_dd,
            volatility=volatility,
            downside_deviation=downside_deviation,
            beta=beta,
            correlation=correlation
        )
    
    def _create_text_chart(self, message: str) -> str:
        """Create text-based chart when visualization libraries not available"""
        return f"""
        <div class="text-chart">
            <h3>Chart Unavailable</h3>
            <p>{message}</p>
            <p>Install plotly for interactive charts</p>
        </div>
        """


# Sample data generator for testing
class PortfolioDataGenerator:
    """Generate sample portfolio data for testing"""
    
    @staticmethod
    def generate_sample_data(days: int = 252) -> PerformanceData:
        """Generate sample portfolio performance data"""
        # Generate dates
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        dates = pd.date_range(start=start_date, end=end_date, freq='D').tolist()
        
        # Generate portfolio values with some volatility
        initial_value = 1000000
        values = [initial_value]
        
        for i in range(1, len(dates)):
            # Random walk with slight upward drift
            daily_return = np.random.normal(0.0008, 0.015)  # ~20% annual return, 15% volatility
            new_value = values[-1] * (1 + daily_return)
            values.append(new_value)
        
        # Calculate returns
        returns = []
        for i in range(1, len(values)):
            ret = (values[i] - values[i-1]) / values[i-1]
            returns.append(ret)
        
        # Generate benchmark data
        benchmark_values = [initial_value]
        for i in range(1, len(dates)):
            # Benchmark with lower volatility
            daily_return = np.random.normal(0.0006, 0.010)  # ~15% annual return, 10% volatility
            new_value = benchmark_values[-1] * (1 + daily_return)
            benchmark_values.append(new_value)
        
        benchmark_returns = []
        for i in range(1, len(benchmark_values)):
            ret = (benchmark_values[i] - benchmark_values[i-1]) / benchmark_values[i-1]
            benchmark_returns.append(ret)
        
        # Generate position data
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
        positions = {}
        for symbol in symbols:
            # Generate position values over time
            position_values = []
            for i, value in enumerate(values):
                # Each position is a percentage of total portfolio
                weight = np.random.uniform(0.1, 0.3)
                position_value = value * weight
                position_values.append(position_value)
            positions[symbol] = position_values
        
        # Generate cash values
        cash = [value * 0.05 for value in values]  # 5% cash
        
        return PerformanceData(
            dates=dates,
            values=values,
            returns=returns,
            benchmark_values=benchmark_values,
            benchmark_returns=benchmark_returns,
            positions=positions,
            cash=cash
        )
    
    @staticmethod
    def generate_attribution_data() -> AttributionData:
        """Generate sample attribution data"""
        return AttributionData(
            asset_allocation={
                'Equities': 0.025,
                'Bonds': -0.008,
                'Commodities': 0.012,
                'Real Estate': 0.005
            },
            sector_allocation={
                'Technology': 0.035,
                'Healthcare': 0.018,
                'Finance': -0.012,
                'Energy': 0.008,
                'Consumer': 0.015
            },
            security_selection={
                'AAPL': 0.022,
                'GOOGL': 0.018,
                'MSFT': 0.015,
                'AMZN': -0.005,
                'TSLA': 0.030
            },
            interaction_effect={
                'Tech-Growth': 0.008,
                'Value-Cyclical': -0.003,
                'Defensive': 0.002
            },
            total_attribution=0.087
        )


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Create portfolio analytics
    analytics = PortfolioAnalyticsCharts()
    
    # Generate sample data
    sample_data = PortfolioDataGenerator.generate_sample_data(252)
    attribution_data = PortfolioDataGenerator.generate_attribution_data()
    
    # Create charts
    performance_chart = analytics.create_performance_chart(sample_data)
    risk_dashboard = analytics.create_risk_metrics_dashboard(sample_data)
    attribution_chart = analytics.create_attribution_analysis(attribution_data)
    
    print("Portfolio analytics charts created successfully")
    print(f"Performance chart HTML length: {len(performance_chart)}")
    print(f"Risk dashboard HTML length: {len(risk_dashboard)}")
    print(f"Attribution chart HTML length: {len(attribution_chart)}")
    
    # Calculate some metrics
    calculator = PerformanceCalculator()
    sharpe = calculator.calculate_sharpe_ratio(sample_data.returns)
    max_dd, _, _ = calculator.calculate_max_drawdown(sample_data.values)
    
    print(f"Portfolio Sharpe Ratio: {sharpe:.3f}")
    print(f"Maximum Drawdown: {max_dd:.3%}")