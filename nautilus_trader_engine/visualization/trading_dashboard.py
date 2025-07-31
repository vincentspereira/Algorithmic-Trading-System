"""
Trading Dashboard and Visualization System
This module provides comprehensive dashboard and visualization capabilities including:
- Real-time trading dashboard
- Performance analytics visualization
- Risk monitoring displays
- Compliance status dashboards
- Interactive charts and graphs
"""
import logging
import asyncio
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
from pathlib import Path
import base64
import io

# Try to import optional visualization dependencies
try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.figure import Figure
    import seaborn as sns
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    import plotly.offline as pyo
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    from flask import Flask, render_template, jsonify, request, send_file
    from flask_socketio import SocketIO, emit
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False


class ChartType(Enum):
    """Chart types for visualization"""
    LINE = "line"
    BAR = "bar"
    CANDLESTICK = "candlestick"
    SCATTER = "scatter"
    PIE = "pie"
    HEATMAP = "heatmap"
    HISTOGRAM = "histogram"
    BOX_PLOT = "box_plot"


class DashboardType(Enum):
    """Dashboard types"""
    TRADING = "trading"
    RISK = "risk"
    COMPLIANCE = "compliance"
    PERFORMANCE = "performance"
    PORTFOLIO = "portfolio"
    MARKET = "market"


@dataclass
class ChartConfig:
    """Chart configuration"""
    chart_id: str
    chart_type: ChartType
    title: str
    data_source: str
    x_axis: str
    y_axis: str
    width: int = 800
    height: int = 400
    refresh_interval: int = 30  # seconds
    parameters: Dict[str, Any] = field(default_factory=dict)
    styling: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DashboardConfig:
    """Dashboard configuration"""
    dashboard_id: str
    dashboard_type: DashboardType
    name: str
    description: str
    charts: List[ChartConfig] = field(default_factory=list)
    layout: Dict[str, Any] = field(default_factory=dict)
    refresh_interval: int = 30
    is_active: bool = True


@dataclass
class VisualizationData:
    """Data structure for visualization"""
    data_id: str
    timestamp: datetime
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


class DataProvider:
    """Base class for data providers"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(__name__)
    
    async def get_data(self, data_source: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get data for visualization"""
        raise NotImplementedError


class TradingDataProvider(DataProvider):
    """Trading data provider"""
    
    def __init__(self):
        super().__init__("trading")
        self.trades_data = []
        self.positions_data = []
        self.orders_data = []
        self.pnl_data = []
    
    async def get_data(self, data_source: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get trading data"""
        try:
            if data_source == "trades":
                return await self._get_trades_data(parameters or {})
            elif data_source == "positions":
                return await self._get_positions_data(parameters or {})
            elif data_source == "orders":
                return await self._get_orders_data(parameters or {})
            elif data_source == "pnl":
                return await self._get_pnl_data(parameters or {})
            elif data_source == "volume":
                return await self._get_volume_data(parameters or {})
            else:
                return {}
        except Exception as e:
            self.logger.error(f"Error getting trading data: {e}")
            return {}
    
    async def _get_trades_data(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get trades data"""
        # Generate sample trading data
        now = datetime.now()
        dates = pd.date_range(start=now - timedelta(days=30), end=now, freq='H')
        trades = []
        cumulative_pnl = 0
        
        for i, date in enumerate(dates):
            # Generate random trade data
            trade_pnl = np.random.normal(50, 200)  # Random P&L
            cumulative_pnl += trade_pnl
            trades.append({
                'timestamp': date.isoformat(),
                'symbol': np.random.choice(['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']),
                'side': np.random.choice(['buy', 'sell']),
                'quantity': np.random.randint(10, 1000),
                'price': 100 + np.random.normal(0, 10),
                'pnl': trade_pnl,
                'cumulative_pnl': cumulative_pnl
            })
        
        return {
            'trades': trades,
            'total_trades': len(trades),
            'total_pnl': cumulative_pnl,
            'avg_pnl_per_trade': cumulative_pnl / len(trades) if trades else 0
        }
    
    async def _get_positions_data(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get positions data"""
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'NVDA', 'META', 'NFLX']
        positions = []
        
        for symbol in symbols:
            quantity = np.random.randint(-1000, 1000)
            if quantity != 0:
                market_price = 100 + np.random.normal(0, 20)
                avg_price = market_price + np.random.normal(0, 5)
                market_value = quantity * market_price
                unrealized_pnl = quantity * (market_price - avg_price)
                
                positions.append({
                    'symbol': symbol,
                    'quantity': quantity,
                    'avg_price': avg_price,
                    'market_price': market_price,
                    'market_value': market_value,
                    'unrealized_pnl': unrealized_pnl,
                    'side': 'long' if quantity > 0 else 'short'
                })
        
        total_market_value = sum(p['market_value'] for p in positions)
        total_unrealized_pnl = sum(p['unrealized_pnl'] for p in positions)
        
        return {
            'positions': positions,
            'total_positions': len(positions),
            'total_market_value': total_market_value,
            'total_unrealized_pnl': total_unrealized_pnl
        }
    
    async def _get_orders_data(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get orders data"""
        order_statuses = ['pending', 'filled', 'cancelled', 'rejected']
        orders = []
        
        for i in range(50):
            orders.append({
                'order_id': f"ORD_{i:04d}",
                'symbol': np.random.choice(['AAPL', 'GOOGL', 'MSFT', 'TSLA']),
                'side': np.random.choice(['buy', 'sell']),
                'quantity': np.random.randint(10, 500),
                'price': 100 + np.random.normal(0, 10),
                'status': np.random.choice(order_statuses),
                'timestamp': (datetime.now() - timedelta(hours=np.random.randint(0, 24))).isoformat()
            })
        
        status_counts = {}
        for status in order_statuses:
            status_counts[status] = len([o for o in orders if o['status'] == status])
        
        return {
            'orders': orders,
            'total_orders': len(orders),
            'status_breakdown': status_counts
        }
    
    async def _get_pnl_data(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get P&L data"""
        days = parameters.get('days', 30)
        now = datetime.now()
        dates = pd.date_range(start=now - timedelta(days=days), end=now, freq='D')
        pnl_data = []
        cumulative_pnl = 0
        
        for date in dates:
            daily_pnl = np.random.normal(1000, 5000)  # Random daily P&L
            cumulative_pnl += daily_pnl
            pnl_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'daily_pnl': daily_pnl,
                'cumulative_pnl': cumulative_pnl
            })
        
        return {
            'pnl_data': pnl_data,
            'total_pnl': cumulative_pnl,
            'avg_daily_pnl': cumulative_pnl / len(dates) if dates else 0,
            'best_day': max(pnl_data, key=lambda x: x['daily_pnl'])['daily_pnl'] if pnl_data else 0,
            'worst_day': min(pnl_data, key=lambda x: x['daily_pnl'])['daily_pnl'] if pnl_data else 0
        }
    
    async def _get_volume_data(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get volume data"""
        hours = parameters.get('hours', 24)
        now = datetime.now()
        timestamps = pd.date_range(start=now - timedelta(hours=hours), end=now, freq='H')
        volume_data = []
        
        for timestamp in timestamps:
            volume_data.append({
                'timestamp': timestamp.isoformat(),
                'volume': np.random.randint(1000, 50000),
                'trade_count': np.random.randint(10, 500)
            })
        
        total_volume = sum(v['volume'] for v in volume_data)
        total_trades = sum(v['trade_count'] for v in volume_data)
        
        return {
            'volume_data': volume_data,
            'total_volume': total_volume,
            'total_trades': total_trades,
            'avg_volume_per_hour': total_volume / len(volume_data) if volume_data else 0
        }


class ChartGenerator:
    """Chart generation utility"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_chart(self, chart_config: ChartConfig, data: Dict[str, Any]) -> str:
        """Generate chart based on configuration and data"""
        try:
            if PLOTLY_AVAILABLE:
                return self._generate_plotly_chart(chart_config, data)
            elif MATPLOTLIB_AVAILABLE:
                return self._generate_matplotlib_chart(chart_config, data)
            else:
                return self._generate_text_chart(chart_config, data)
        except Exception as e:
            self.logger.error(f"Error generating chart: {e}")
            return ""
    
    def _generate_plotly_chart(self, chart_config: ChartConfig, data: Dict[str, Any]) -> str:
        """Generate Plotly chart"""
        try:
            fig = None
            
            if chart_config.chart_type == ChartType.LINE:
                fig = self._create_plotly_line_chart(chart_config, data)
            elif chart_config.chart_type == ChartType.BAR:
                fig = self._create_plotly_bar_chart(chart_config, data)
            elif chart_config.chart_type == ChartType.PIE:
                fig = self._create_plotly_pie_chart(chart_config, data)
            elif chart_config.chart_type == ChartType.SCATTER:
                fig = self._create_plotly_scatter_chart(chart_config, data)
            elif chart_config.chart_type == ChartType.HEATMAP:
                fig = self._create_plotly_heatmap(chart_config, data)
            
            if fig:
                return fig.to_html(include_plotlyjs='cdn', div_id=chart_config.chart_id)
            else:
                return f"<div id='{chart_config.chart_id}'>Chart type not supported</div>"
                
        except Exception as e:
            self.logger.error(f"Error generating Plotly chart: {e}")
            return f"<div id='{chart_config.chart_id}'>Error generating chart</div>"
    
    def _create_plotly_line_chart(self, chart_config: ChartConfig, data: Dict[str, Any]) -> go.Figure:
        """Create Plotly line chart"""
        fig = go.Figure()
        
        # Extract data based on chart configuration
        if 'pnl_data' in data:
            pnl_data = data['pnl_data']
            dates = [item['date'] for item in pnl_data]
            values = [item['cumulative_pnl'] for item in pnl_data]
            
            fig.add_trace(go.Scatter(
                x=dates,
                y=values,
                mode='lines+markers',
                name='Cumulative P&L',
                line=dict(color='blue', width=2)
            ))
        elif 'volume_data' in data:
            volume_data = data['volume_data']
            timestamps = [item['timestamp'] for item in volume_data]
            volumes = [item['volume'] for item in volume_data]
            
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=volumes,
                mode='lines',
                name='Volume',
                line=dict(color='green', width=2)
            ))
        
        fig.update_layout(
            title=chart_config.title,
            xaxis_title=chart_config.x_axis,
            yaxis_title=chart_config.y_axis,
            width=chart_config.width,
            height=chart_config.height
        )
        
        return fig
    
    def _create_plotly_bar_chart(self, chart_config: ChartConfig, data: Dict[str, Any]) -> go.Figure:
        """Create Plotly bar chart"""
        fig = go.Figure()
        
        if 'positions' in data:
            positions = data['positions']
            symbols = [pos['symbol'] for pos in positions]
            values = [pos['market_value'] for pos in positions]
            
            fig.add_trace(go.Bar(
                x=symbols,
                y=values,
                name='Market Value',
                marker_color='lightblue'
            ))
        elif 'status_breakdown' in data:
            statuses = list(data['status_breakdown'].keys())
            counts = list(data['status_breakdown'].values())
            
            fig.add_trace(go.Bar(
                x=statuses,
                y=counts,
                name='Order Status',
                marker_color='orange'
            ))
        
        fig.update_layout(
            title=chart_config.title,
            xaxis_title=chart_config.x_axis,
            yaxis_title=chart_config.y_axis,
            width=chart_config.width,
            height=chart_config.height
        )
        
        return fig
    
    def _create_plotly_pie_chart(self, chart_config: ChartConfig, data: Dict[str, Any]) -> go.Figure:
        """Create Plotly pie chart"""
        fig = go.Figure()
        
        if 'sector_exposures' in data:
            exposures = data['sector_exposures']
            labels = [exp['sector'] for exp in exposures]
            values = [exp['exposure'] for exp in exposures]
            
            fig.add_trace(go.Pie(
                labels=labels,
                values=values,
                name="Sector Exposure"
            ))
        elif 'concentrations' in data:
            concentrations = data['concentrations'][:10]  # Top 10
            labels = [conc['symbol'] for conc in concentrations]
            values = [conc['percentage'] for conc in concentrations]
            
            fig.add_trace(go.Pie(
                labels=labels,
                values=values,
                name="Position Concentration"
            ))
        
        fig.update_layout(
            title=chart_config.title,
            width=chart_config.width,
            height=chart_config.height
        )
        
        return fig
    
    def _generate_text_chart(self, chart_config: ChartConfig, data: Dict[str, Any]) -> str:
        """Generate text-based chart when no visualization libraries available"""
        return f"""
        <div id='{chart_config.chart_id}' class='text-chart'>
            <h3>{chart_config.title}</h3>
            <p>Chart data: {json.dumps(data, indent=2, default=str)}</p>
            <p>Note: Install plotly or matplotlib for visual charts</p>
        </div>
        """


class DashboardManager:
    """Dashboard management system"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.dashboards: Dict[str, DashboardConfig] = {}
        self.data_providers: Dict[str, DataProvider] = {}
        self.chart_generator = ChartGenerator()
        
        # Initialize default data providers
        self.data_providers['trading'] = TradingDataProvider()
        
    def register_data_provider(self, provider: DataProvider):
        """Register a data provider"""
        self.data_providers[provider.name] = provider
        self.logger.info(f"Registered data provider: {provider.name}")
    
    def create_dashboard(self, config: DashboardConfig):
        """Create a new dashboard"""
        self.dashboards[config.dashboard_id] = config
        self.logger.info(f"Created dashboard: {config.name}")
    
    async def get_dashboard_data(self, dashboard_id: str) -> Dict[str, Any]:
        """Get data for a dashboard"""
        if dashboard_id not in self.dashboards:
            return {}
        
        dashboard = self.dashboards[dashboard_id]
        dashboard_data = {
            'dashboard_id': dashboard_id,
            'name': dashboard.name,
            'charts': []
        }
        
        for chart_config in dashboard.charts:
            try:
                # Get data from appropriate provider
                provider_name = chart_config.data_source.split('.')[0]
                data_source = chart_config.data_source.split('.', 1)[1] if '.' in chart_config.data_source else chart_config.data_source
                
                if provider_name in self.data_providers:
                    data = await self.data_providers[provider_name].get_data(data_source, chart_config.parameters)
                    chart_html = self.chart_generator.generate_chart(chart_config, data)
                    
                    dashboard_data['charts'].append({
                        'chart_id': chart_config.chart_id,
                        'title': chart_config.title,
                        'html': chart_html,
                        'data': data
                    })
                else:
                    self.logger.warning(f"Data provider not found: {provider_name}")
                    
            except Exception as e:
                self.logger.error(f"Error getting chart data: {e}")
        
        return dashboard_data
    
    def get_default_trading_dashboard(self) -> DashboardConfig:
        """Get default trading dashboard configuration"""
        charts = [
            ChartConfig(
                chart_id="pnl_chart",
                chart_type=ChartType.LINE,
                title="Cumulative P&L",
                data_source="trading.pnl",
                x_axis="Date",
                y_axis="P&L ($)",
                parameters={'days': 30}
            ),
            ChartConfig(
                chart_id="positions_chart",
                chart_type=ChartType.BAR,
                title="Current Positions",
                data_source="trading.positions",
                x_axis="Symbol",
                y_axis="Market Value ($)"
            ),
            ChartConfig(
                chart_id="orders_chart",
                chart_type=ChartType.PIE,
                title="Order Status Distribution",
                data_source="trading.orders",
                x_axis="Status",
                y_axis="Count"
            ),
            ChartConfig(
                chart_id="volume_chart",
                chart_type=ChartType.LINE,
                title="Trading Volume",
                data_source="trading.volume",
                x_axis="Time",
                y_axis="Volume",
                parameters={'hours': 24}
            )
        ]
        
        return DashboardConfig(
            dashboard_id="default_trading",
            dashboard_type=DashboardType.TRADING,
            name="Trading Dashboard",
            description="Main trading dashboard with P&L, positions, and orders",
            charts=charts
        )


class WebDashboardServer:
    """Web-based dashboard server"""
    
    def __init__(self, dashboard_manager: DashboardManager, host: str = "localhost", port: int = 8080):
        self.dashboard_manager = dashboard_manager
        self.host = host
        self.port = port
        self.logger = logging.getLogger(__name__)
        
        if FLASK_AVAILABLE:
            self.app = Flask(__name__)
            self.socketio = SocketIO(self.app, cors_allowed_origins="*")
            self._setup_routes()
        else:
            self.app = None
            self.socketio = None
            self.logger.warning("Flask not available - web dashboard disabled")
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            return self.render_dashboard_list()
        
        @self.app.route('/dashboard/<dashboard_id>')
        def dashboard(dashboard_id):
            return self.render_dashboard(dashboard_id)
        
        @self.app.route('/api/dashboard/<dashboard_id>/data')
        async def dashboard_data(dashboard_id):
            data = await self.dashboard_manager.get_dashboard_data(dashboard_id)
            return jsonify(data)
        
        @self.socketio.on('connect')
        def handle_connect():
            self.logger.info("Client connected to dashboard")
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            self.logger.info("Client disconnected from dashboard")
    
    def render_dashboard_list(self) -> str:
        """Render dashboard list page"""
        dashboards = list(self.dashboard_manager.dashboards.values())
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Nautilus Trader Dashboards</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .dashboard-list { list-style-type: none; padding: 0; }
                .dashboard-item { 
                    background: #f5f5f5; 
                    margin: 10px 0; 
                    padding: 15px; 
                    border-radius: 5px; 
                }
                .dashboard-item a { text-decoration: none; color: #333; }
                .dashboard-item:hover { background: #e5e5e5; }
            </style>
        </head>
        <body>
            <h1>Nautilus Trader Dashboards</h1>
            <ul class="dashboard-list">
        """
        
        for dashboard in dashboards:
            html += f"""
                <li class="dashboard-item">
                    <a href="/dashboard/{dashboard.dashboard_id}">
                        <h3>{dashboard.name}</h3>
                        <p>{dashboard.description}</p>
                    </a>
                </li>
            """
        
        html += """
            </ul>
        </body>
        </html>
        """
        
        return html
    
    def render_dashboard(self, dashboard_id: str) -> str:
        """Render individual dashboard page"""
        if dashboard_id not in self.dashboard_manager.dashboards:
            return "<h1>Dashboard not found</h1>"
        
        dashboard = self.dashboard_manager.dashboards[dashboard_id]
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{dashboard.name} - Nautilus Trader</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .dashboard-header {{ margin-bottom: 30px; }}
                .chart-container {{ 
                    display: inline-block; 
                    margin: 10px; 
                    border: 1px solid #ddd; 
                    border-radius: 5px; 
                    padding: 10px; 
                }}
                .loading {{ text-align: center; padding: 50px; }}
            </style>
        </head>
        <body>
            <div class="dashboard-header">
                <h1>{dashboard.name}</h1>
                <p>{dashboard.description}</p>
                <button onclick="refreshDashboard()">Refresh</button>
            </div>
            
            <div id="charts-container">
                <div class="loading">Loading charts...</div>
            </div>
            
            <script>
                const socket = io();
                
                async function loadDashboard() {{
                    try {{
                        const response = await fetch('/api/dashboard/{dashboard_id}/data');
                        const data = await response.json();
                        renderCharts(data.charts);
                    }} catch (error) {{
                        console.error('Error loading dashboard:', error);
                        document.getElementById('charts-container').innerHTML = 
                            '<div class="error">Error loading dashboard data</div>';
                    }}
                }}
                
                function renderCharts(charts) {{
                    const container = document.getElementById('charts-container');
                    container.innerHTML = '';
                    
                    charts.forEach(chart => {{
                        const chartDiv = document.createElement('div');
                        chartDiv.className = 'chart-container';
                        chartDiv.innerHTML = chart.html;
                        container.appendChild(chartDiv);
                    }});
                }}
                
                function refreshDashboard() {{
                    loadDashboard();
                }}
                
                // Auto-refresh every 30 seconds
                setInterval(refreshDashboard, 30000);
                
                // Load dashboard on page load
                loadDashboard();
            </script>
        </body>
        </html>
        """
        
        return html
    
    def run(self):
        """Run the web dashboard server"""
        if self.app and self.socketio:
            self.logger.info(f"Starting web dashboard server on {self.host}:{self.port}")
            self.socketio.run(self.app, host=self.host, port=self.port, debug=False)
        else:
            self.logger.error("Cannot start web server - Flask not available")


# Example usage and testing
async def main():
    """Main function for testing"""
    logging.basicConfig(level=logging.INFO)
    
    # Create dashboard manager
    dashboard_manager = DashboardManager()
    
    # Create default trading dashboard
    trading_dashboard = dashboard_manager.get_default_trading_dashboard()
    dashboard_manager.create_dashboard(trading_dashboard)
    
    # Test dashboard data generation
    dashboard_data = await dashboard_manager.get_dashboard_data("default_trading")
    print("Dashboard data generated successfully")
    print(f"Number of charts: {len(dashboard_data.get('charts', []))}")
    
    # Start web server if Flask is available
    if FLASK_AVAILABLE:
        web_server = WebDashboardServer(dashboard_manager)
        print(f"Web dashboard available at: http://localhost:8080")
        # web_server.run()  # Uncomment to start web server
    else:
        print("Install Flask and Flask-SocketIO to enable web dashboard")


if __name__ == "__main__":
    asyncio.run(main())