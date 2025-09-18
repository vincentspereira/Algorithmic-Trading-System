#!/usr/bin/env python3
"""
Report Generator Module

Generates comprehensive reports for backtesting results, including:
- Performance summaries
- Risk analysis reports
- Trade analysis
- Visual charts and graphs
- Export capabilities (PDF, HTML, Excel)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from pathlib import Path
import json

try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

from .results import BacktestResults, Trade
from .metrics import PerformanceMetrics, RiskMetrics, TradeMetrics


@dataclass
class ReportConfig:
    """Configuration for report generation."""
    title: str = "Backtest Report"
    subtitle: str = ""
    include_charts: bool = True
    include_trade_analysis: bool = True
    include_risk_analysis: bool = True
    chart_style: str = "plotly"  # 'plotly' or 'matplotlib'
    export_format: str = "html"  # 'html', 'pdf', 'json'
    output_dir: str = "reports"
    

class ReportGenerator:
    """Generates comprehensive backtesting reports."""
    
    def __init__(self, config: Optional[ReportConfig] = None):
        self.config = config or ReportConfig()
        self.results: Optional[BacktestResults] = None
        self.performance_metrics: Optional[PerformanceMetrics] = None
        self.risk_metrics: Optional[RiskMetrics] = None
        self.trade_metrics: Optional[TradeMetrics] = None
        
    def generate_report(
        self,
        results: BacktestResults,
        performance_metrics: PerformanceMetrics,
        risk_metrics: Optional[RiskMetrics] = None,
        trade_metrics: Optional[TradeMetrics] = None,
        output_path: Optional[str] = None
    ) -> str:
        """Generate a comprehensive backtest report.
        
        Args:
            results: Backtest results
            performance_metrics: Performance metrics
            risk_metrics: Risk metrics (optional)
            trade_metrics: Trade metrics (optional)
            output_path: Custom output path (optional)
            
        Returns:
            Path to generated report
        """
        self.results = results
        self.performance_metrics = performance_metrics
        self.risk_metrics = risk_metrics
        self.trade_metrics = trade_metrics
        
        # Generate report content
        report_data = self._generate_report_data()
        
        # Create output directory
        output_dir = Path(output_path or self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate report based on format
        if self.config.export_format == "html":
            return self._generate_html_report(report_data, output_dir)
        elif self.config.export_format == "json":
            return self._generate_json_report(report_data, output_dir)
        else:
            raise ValueError(f"Unsupported export format: {self.config.export_format}")
    
    def _generate_report_data(self) -> Dict[str, Any]:
        """Generate structured report data."""
        report_data = {
            "metadata": {
                "title": self.config.title,
                "subtitle": self.config.subtitle,
                "generated_at": datetime.now().isoformat(),
                "period": {
                    "start": self.results.timestamps[0].isoformat() if self.results.timestamps else None,
                    "end": self.results.timestamps[-1].isoformat() if self.results.timestamps else None,
                    "duration_days": len(self.results.timestamps) if self.results.timestamps else 0
                }
            },
            "summary": self._generate_summary(),
            "performance": self._generate_performance_section(),
            "trades": self._generate_trades_section() if self.config.include_trade_analysis else None,
            "risk": self._generate_risk_section() if self.config.include_risk_analysis else None,
            "charts": self._generate_charts() if self.config.include_charts else None
        }
        
        return report_data
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate executive summary."""
        if not self.performance_metrics:
            return {}
            
        return {
            "total_return": f"{self.performance_metrics.total_return:.2%}",
            "annualized_return": f"{self.performance_metrics.annualized_return:.2%}",
            "volatility": f"{self.performance_metrics.volatility:.2%}",
            "sharpe_ratio": f"{self.performance_metrics.sharpe_ratio:.2f}",
            "max_drawdown": f"{self.performance_metrics.max_drawdown:.2%}",
            "total_trades": len(self.results.trades) if self.results else 0,
            "win_rate": f"{self.trade_metrics.win_rate:.2%}" if self.trade_metrics else "N/A"
        }
    
    def _generate_performance_section(self) -> Dict[str, Any]:
        """Generate performance analysis section."""
        if not self.performance_metrics:
            return {}
            
        return {
            "returns": {
                "total_return": self.performance_metrics.total_return,
                "annualized_return": self.performance_metrics.annualized_return,
                "monthly_returns": self._calculate_monthly_returns(),
                "yearly_returns": self._calculate_yearly_returns()
            },
            "risk_adjusted": {
                "sharpe_ratio": self.performance_metrics.sharpe_ratio,
                "sortino_ratio": getattr(self.performance_metrics, 'sortino_ratio', None),
                "calmar_ratio": getattr(self.performance_metrics, 'calmar_ratio', None),
                "volatility": self.performance_metrics.volatility
            },
            "drawdown": {
                "max_drawdown": self.performance_metrics.max_drawdown,
                "avg_drawdown": getattr(self.performance_metrics, 'avg_drawdown', None),
                "drawdown_duration": getattr(self.performance_metrics, 'max_drawdown_duration', None)
            }
        }
    
    def _generate_trades_section(self) -> Dict[str, Any]:
        """Generate trade analysis section."""
        if not self.results or not self.results.trades:
            return {"message": "No trades executed"}
            
        trades_df = pd.DataFrame([
            {
                "symbol": trade.symbol,
                "side": trade.side,
                "quantity": trade.quantity,
                "entry_price": trade.entry_price,
                "exit_price": trade.exit_price,
                "pnl": trade.pnl,
                "entry_time": trade.entry_time,
                "exit_time": trade.exit_time,
                "duration": (trade.exit_time - trade.entry_time).total_seconds() / 3600 if trade.exit_time else None
            }
            for trade in self.results.trades
        ])
        
        return {
            "summary": {
                "total_trades": len(trades_df),
                "winning_trades": len(trades_df[trades_df['pnl'] > 0]),
                "losing_trades": len(trades_df[trades_df['pnl'] < 0]),
                "win_rate": len(trades_df[trades_df['pnl'] > 0]) / len(trades_df) if len(trades_df) > 0 else 0,
                "avg_win": trades_df[trades_df['pnl'] > 0]['pnl'].mean() if len(trades_df[trades_df['pnl'] > 0]) > 0 else 0,
                "avg_loss": trades_df[trades_df['pnl'] < 0]['pnl'].mean() if len(trades_df[trades_df['pnl'] < 0]) > 0 else 0,
                "profit_factor": abs(trades_df[trades_df['pnl'] > 0]['pnl'].sum() / trades_df[trades_df['pnl'] < 0]['pnl'].sum()) if trades_df[trades_df['pnl'] < 0]['pnl'].sum() != 0 else float('inf')
            },
            "by_symbol": trades_df.groupby('symbol')['pnl'].agg(['count', 'sum', 'mean']).to_dict('index'),
            "monthly_pnl": self._calculate_monthly_pnl(trades_df)
        }
    
    def _generate_risk_section(self) -> Dict[str, Any]:
        """Generate risk analysis section."""
        if not self.risk_metrics:
            return {"message": "Risk analysis not available"}
            
        return {
            "var": {
                "daily_var_95": getattr(self.risk_metrics, 'var_95', None),
                "daily_var_99": getattr(self.risk_metrics, 'var_99', None)
            },
            "exposure": {
                "max_leverage": getattr(self.risk_metrics, 'max_leverage', None),
                "avg_leverage": getattr(self.risk_metrics, 'avg_leverage', None)
            },
            "correlation": getattr(self.risk_metrics, 'correlation_analysis', None)
        }
    
    def _generate_charts(self) -> Dict[str, Any]:
        """Generate chart configurations."""
        charts = {}
        
        if self.results and self.results.portfolio_values:
            charts["equity_curve"] = self._create_equity_curve_config()
            charts["drawdown"] = self._create_drawdown_config()
            
        if self.results and self.results.trades:
            charts["monthly_returns"] = self._create_monthly_returns_config()
            charts["trade_pnl"] = self._create_trade_pnl_config()
            
        return charts
    
    def _create_equity_curve_config(self) -> Dict[str, Any]:
        """Create equity curve chart configuration."""
        return {
            "type": "line",
            "title": "Portfolio Equity Curve",
            "x_data": [ts.isoformat() for ts in self.results.timestamps],
            "y_data": self.results.portfolio_values,
            "x_label": "Date",
            "y_label": "Portfolio Value ($)"
        }
    
    def _create_drawdown_config(self) -> Dict[str, Any]:
        """Create drawdown chart configuration."""
        portfolio_values = np.array(self.results.portfolio_values)
        peak = np.maximum.accumulate(portfolio_values)
        drawdown = (portfolio_values - peak) / peak
        
        return {
            "type": "area",
            "title": "Drawdown",
            "x_data": [ts.isoformat() for ts in self.results.timestamps],
            "y_data": drawdown.tolist(),
            "x_label": "Date",
            "y_label": "Drawdown (%)"
        }
    
    def _create_monthly_returns_config(self) -> Dict[str, Any]:
        """Create monthly returns chart configuration."""
        monthly_returns = self._calculate_monthly_returns()
        
        return {
            "type": "bar",
            "title": "Monthly Returns",
            "x_data": list(monthly_returns.keys()),
            "y_data": list(monthly_returns.values()),
            "x_label": "Month",
            "y_label": "Return (%)"
        }
    
    def _create_trade_pnl_config(self) -> Dict[str, Any]:
        """Create trade P&L chart configuration."""
        pnl_data = [trade.pnl for trade in self.results.trades]
        cumulative_pnl = np.cumsum(pnl_data)
        
        return {
            "type": "line",
            "title": "Cumulative Trade P&L",
            "x_data": list(range(1, len(pnl_data) + 1)),
            "y_data": cumulative_pnl.tolist(),
            "x_label": "Trade Number",
            "y_label": "Cumulative P&L ($)"
        }
    
    def _calculate_monthly_returns(self) -> Dict[str, float]:
        """Calculate monthly returns."""
        if not self.results or not self.results.portfolio_values:
            return {}
            
        df = pd.DataFrame({
            'date': self.results.timestamps,
            'value': self.results.portfolio_values
        })
        df.set_index('date', inplace=True)
        
        monthly_values = df.resample('M').last()
        monthly_returns = monthly_values.pct_change().dropna()
        
        return {
            month.strftime('%Y-%m'): return_val * 100
            for month, return_val in monthly_returns['value'].items()
        }
    
    def _calculate_yearly_returns(self) -> Dict[str, float]:
        """Calculate yearly returns."""
        if not self.results or not self.results.portfolio_values:
            return {}
            
        df = pd.DataFrame({
            'date': self.results.timestamps,
            'value': self.results.portfolio_values
        })
        df.set_index('date', inplace=True)
        
        yearly_values = df.resample('Y').last()
        yearly_returns = yearly_values.pct_change().dropna()
        
        return {
            year.strftime('%Y'): return_val * 100
            for year, return_val in yearly_returns['value'].items()
        }
    
    def _calculate_monthly_pnl(self, trades_df: pd.DataFrame) -> Dict[str, float]:
        """Calculate monthly P&L from trades."""
        if trades_df.empty:
            return {}
            
        trades_df['month'] = pd.to_datetime(trades_df['exit_time']).dt.to_period('M')
        monthly_pnl = trades_df.groupby('month')['pnl'].sum()
        
        return {
            str(month): pnl
            for month, pnl in monthly_pnl.items()
        }
    
    def _generate_html_report(self, report_data: Dict[str, Any], output_dir: Path) -> str:
        """Generate HTML report."""
        html_content = self._create_html_template(report_data)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backtest_report_{timestamp}.html"
        output_path = output_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        return str(output_path)
    
    def _generate_json_report(self, report_data: Dict[str, Any], output_dir: Path) -> str:
        """Generate JSON report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backtest_report_{timestamp}.json"
        output_path = output_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, default=str)
            
        return str(output_path)
    
    def _create_html_template(self, report_data: Dict[str, Any]) -> str:
        """Create HTML report template."""
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_data['metadata']['title']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; margin-bottom: 30px; border-bottom: 2px solid #007bff; padding-bottom: 20px; }}
        .section {{ margin-bottom: 30px; }}
        .section h2 {{ color: #007bff; border-bottom: 1px solid #dee2e6; padding-bottom: 10px; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
        .metric-card {{ background: #f8f9fa; padding: 15px; border-radius: 5px; text-align: center; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #007bff; }}
        .metric-label {{ font-size: 14px; color: #6c757d; margin-top: 5px; }}
        .table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        .table th, .table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #dee2e6; }}
        .table th {{ background-color: #f8f9fa; font-weight: bold; }}
        .positive {{ color: #28a745; }}
        .negative {{ color: #dc3545; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{report_data['metadata']['title']}</h1>
            <p>{report_data['metadata']['subtitle']}</p>
            <p>Generated: {report_data['metadata']['generated_at']}</p>
        </div>
        
        <div class="section">
            <h2>Executive Summary</h2>
            <div class="metrics-grid">
                {self._generate_summary_cards(report_data['summary'])}
            </div>
        </div>
        
        {self._generate_performance_html(report_data.get('performance', {}))}
        {self._generate_trades_html(report_data.get('trades', {}))}
        {self._generate_risk_html(report_data.get('risk', {}))}
    </div>
</body>
</html>
        """
    
    def _generate_summary_cards(self, summary: Dict[str, Any]) -> str:
        """Generate HTML for summary metric cards."""
        cards = []
        for key, value in summary.items():
            label = key.replace('_', ' ').title()
            cards.append(f"""
                <div class="metric-card">
                    <div class="metric-value">{value}</div>
                    <div class="metric-label">{label}</div>
                </div>
            """)
        return ''.join(cards)
    
    def _generate_performance_html(self, performance: Dict[str, Any]) -> str:
        """Generate HTML for performance section."""
        if not performance:
            return ""
            
        return f"""
        <div class="section">
            <h2>Performance Analysis</h2>
            <h3>Returns</h3>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{performance.get('returns', {}).get('total_return', 0):.2%}</div>
                    <div class="metric-label">Total Return</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{performance.get('returns', {}).get('annualized_return', 0):.2%}</div>
                    <div class="metric-label">Annualized Return</div>
                </div>
            </div>
        </div>
        """
    
    def _generate_trades_html(self, trades: Dict[str, Any]) -> str:
        """Generate HTML for trades section."""
        if not trades or 'summary' not in trades:
            return ""
            
        summary = trades['summary']
        return f"""
        <div class="section">
            <h2>Trade Analysis</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{summary.get('total_trades', 0)}</div>
                    <div class="metric-label">Total Trades</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{summary.get('win_rate', 0):.2%}</div>
                    <div class="metric-label">Win Rate</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${summary.get('avg_win', 0):.2f}</div>
                    <div class="metric-label">Average Win</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${summary.get('avg_loss', 0):.2f}</div>
                    <div class="metric-label">Average Loss</div>
                </div>
            </div>
        </div>
        """
    
    def _generate_risk_html(self, risk: Dict[str, Any]) -> str:
        """Generate HTML for risk section."""
        if not risk or 'var' not in risk:
            return ""
            
        return f"""
        <div class="section">
            <h2>Risk Analysis</h2>
            <p>Risk metrics and analysis would be displayed here.</p>
        </div>
        """


def create_report_generator(config: Optional[ReportConfig] = None) -> ReportGenerator:
    """Factory function to create a ReportGenerator instance.
    
    Args:
        config: Report configuration
        
    Returns:
        ReportGenerator instance
    """
    return ReportGenerator(config)


# Example usage
if __name__ == "__main__":
    # Create sample report
    from datetime import datetime, timedelta
    
    # Mock data for demonstration
    timestamps = [datetime.now() - timedelta(days=i) for i in range(100, 0, -1)]
    portfolio_values = [100000 * (1 + 0.001 * i + np.random.normal(0, 0.01)) for i in range(100)]
    
    results = BacktestResults(
        trades=[],
        portfolio_values=portfolio_values,
        timestamps=timestamps
    )
    
    performance_metrics = PerformanceMetrics(
        total_return=0.15,
        annualized_return=0.12,
        volatility=0.18,
        sharpe_ratio=0.67,
        max_drawdown=-0.08
    )
    
    # Generate report
    generator = ReportGenerator()
    report_path = generator.generate_report(results, performance_metrics)
    print(f"Report generated: {report_path}")