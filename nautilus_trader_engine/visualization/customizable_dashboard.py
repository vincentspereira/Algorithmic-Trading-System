"""
Customizable Dashboard System
Provides flexible, user-configurable dashboards with drag-and-drop widgets,
custom layouts, and personalized views for trading, risk, and compliance monitoring.
"""
import logging
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
from pathlib import Path

try:
    from flask import Flask, render_template, jsonify, request, session
    from flask_socketio import SocketIO, emit, join_room, leave_room
    FLASK_AVAILABLE = True
except ImportError:
    Flask = None
    SocketIO = None
    FLASK_AVAILABLE = False

class WidgetType(Enum):
    """Dashboard widget types"""
    CHART = "chart"
    TABLE = "table"
    METRIC = "metric"
    GAUGE = "gauge"
    ALERT = "alert"
    NEWS = "news"
    CALENDAR = "calendar"
    WATCHLIST = "watchlist"
    POSITION_SUMMARY = "position_summary"
    ORDER_BOOK = "order_book"
    TRADE_HISTORY = "trade_history"
    RISK_METRICS = "risk_metrics"
    COMPLIANCE_STATUS = "compliance_status"
    PERFORMANCE_CHART = "performance_chart"
    CUSTOM_HTML = "custom_html"

class LayoutType(Enum):
    """Dashboard layout types"""
    GRID = "grid"
    FLEX = "flex"
    MASONRY = "masonry"
    TABS = "tabs"
    ACCORDION = "accordion"

class ThemeType(Enum):
    """Dashboard theme types"""
    LIGHT = "light"
    DARK = "dark"
    BLUE = "blue"
    GREEN = "green"
    CUSTOM = "custom"

@dataclass
class WidgetConfig:
    """Widget configuration"""
    widget_id: str
    widget_type: WidgetType
    title: str
    data_source: str
    position: Dict[str, int] = field(default_factory=lambda: {"x": 0, "y": 0, "w": 4, "h": 3})
    refresh_interval: int = 30  # seconds
    parameters: Dict[str, Any] = field(default_factory=dict)
    styling: Dict[str, Any] = field(default_factory=dict)
    is_visible: bool = True
    is_resizable: bool = True
    is_draggable: bool = True
    min_size: Dict[str, int] = field(default_factory=lambda: {"w": 2, "h": 2})
    max_size: Dict[str, int] = field(default_factory=lambda: {"w": 12, "h": 8})

@dataclass
class DashboardLayout:
    """Dashboard layout configuration"""
    layout_id: str
    layout_type: LayoutType
    grid_columns: int = 12
    grid_rows: int = 20
    row_height: int = 60
    margin: List[int] = field(default_factory=lambda: [10, 10])
    container_padding: List[int] = field(default_factory=lambda: [10, 10])
    breakpoints: Dict[str, int] = field(default_factory=lambda: {
        "lg": 1200, "md": 996, "sm": 768, "xs": 480, "xxs": 0
    })
    responsive_layouts: Dict[str, List[Dict]] = field(default_factory=dict)

@dataclass
class DashboardTheme:
    """Dashboard theme configuration"""
    theme_id: str
    theme_type: ThemeType
    name: str
    colors: Dict[str, str] = field(default_factory=dict)
    fonts: Dict[str, str] = field(default_factory=dict)
    spacing: Dict[str, int] = field(default_factory=dict)
    custom_css: str = ""

@dataclass
class Dashboard:
    """Dashboard configuration"""
    dashboard_id: str
    name: str
    description: str
    owner_id: str
    widgets: List[WidgetConfig] = field(default_factory=list)
    layout: DashboardLayout = None
    theme: DashboardTheme = None
    is_public: bool = False
    is_template: bool = False
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    access_permissions: Dict[str, List[str]] = field(default_factory=dict)

@dataclass
class DashboardTemplate:
    """Pre-built dashboard template"""
    template_id: str
    name: str
    description: str
    category: str
    widgets: List[WidgetConfig]
    layout: DashboardLayout
    theme: DashboardTheme
    preview_image: str = ""
    tags: List[str] = field(default_factory=list)

class WidgetDataProvider:
    """Base class for widget data providers"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(__name__)
    
    async def get_widget_data(self, widget_config: WidgetConfig) -> Dict[str, Any]:
        """Get data for widget"""
        raise NotImplementedError
    
    async def validate_config(self, widget_config: WidgetConfig) -> bool:
        """Validate widget configuration"""
        return True

class ChartWidgetProvider(WidgetDataProvider):
    """Chart widget data provider"""
    
    def __init__(self):
        super().__init__("chart")
    
    async def get_widget_data(self, widget_config: WidgetConfig) -> Dict[str, Any]:
        """Get chart data"""
        try:
            data_source = widget_config.data_source
            parameters = widget_config.parameters
            
            if data_source == "price_history":
                return await self._get_price_history_data(parameters)
            elif data_source == "volume_profile":
                return await self._get_volume_profile_data(parameters)
            elif data_source == "pnl_chart":
                return await self._get_pnl_chart_data(parameters)
            elif data_source == "risk_metrics":
                return await self._get_risk_metrics_data(parameters)
            else:
                return {"error": f"Unknown data source: {data_source}"}
        
        except Exception as e:
            self.logger.error(f"Error getting chart data: {e}")
            return {"error": str(e)}
    
    async def _get_price_history_data(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get price history data"""
        symbol = parameters.get('symbol', 'AAPL')
        days = parameters.get('days', 30)
        
        # Generate sample price data
        dates = []
        prices = []
        volumes = []
        
        base_price = 100.0 + hash(symbol) % 100
        current_date = datetime.now()
        
        for i in range(days):
            date = current_date - timedelta(days=days-i)
            price_change = (hash(f"{symbol}{i}") % 200 - 100) / 100
            price = max(base_price + price_change, 1.0)
            volume = 10000 + hash(f"{symbol}{i}vol") % 50000
            
            dates.append(date.isoformat())
            prices.append(price)
            volumes.append(volume)
            base_price = price
        
        return {
            "chart_type": "line",
            "data": {
                "labels": dates,
                "datasets": [
                    {
                        "label": f"{symbol} Price",
                        "data": prices,
                        "borderColor": "#007bff",
                        "backgroundColor": "rgba(0, 123, 255, 0.1)",
                        "fill": True
                    }
                ]
            },
            "options": {
                "responsive": True,
                "scales": {
                    "x": {"type": "time", "time": {"unit": "day"}},
                    "y": {"beginAtZero": False}
                }
            }
        }
    
    async def _get_volume_profile_data(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get volume profile data"""
        symbol = parameters.get('symbol', 'AAPL')
        
        # Generate sample volume profile
        price_levels = []
        volumes = []
        
        base_price = 100.0 + hash(symbol) % 100
        for i in range(20):
            price = base_price + (i - 10) * 0.5
            volume = max(1000, 10000 - abs(i - 10) * 500 + hash(f"{symbol}{i}") % 2000)
            price_levels.append(price)
            volumes.append(volume)
        
        return {
            "chart_type": "bar",
            "data": {
                "labels": [f"${p:.2f}" for p in price_levels],
                "datasets": [
                    {
                        "label": "Volume",
                        "data": volumes,
                        "backgroundColor": "rgba(40, 167, 69, 0.6)",
                        "borderColor": "#28a745",
                        "borderWidth": 1
                    }
                ]
            },
            "options": {
                "indexAxis": "y",
                "responsive": True
            }
        }
    
    async def _get_pnl_chart_data(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get P&L chart data"""
        days = parameters.get('days', 30)
        
        # Generate sample P&L data
        dates = []
        daily_pnl = []
        cumulative_pnl = []
        
        current_date = datetime.now()
        cumulative = 0
        
        for i in range(days):
            date = current_date - timedelta(days=days-i)
            pnl = (hash(f"pnl{i}") % 10000 - 5000)
            cumulative += pnl
            
            dates.append(date.isoformat())
            daily_pnl.append(pnl)
            cumulative_pnl.append(cumulative)
        
        return {
            "chart_type": "line",
            "data": {
                "labels": dates,
                "datasets": [
                    {
                        "label": "Daily P&L",
                        "data": daily_pnl,
                        "borderColor": "#dc3545",
                        "backgroundColor": "rgba(220, 53, 69, 0.1)",
                        "yAxisID": "y"
                    },
                    {
                        "label": "Cumulative P&L",
                        "data": cumulative_pnl,
                        "borderColor": "#007bff",
                        "backgroundColor": "rgba(0, 123, 255, 0.1)",
                        "yAxisID": "y1"
                    }
                ]
            },
            "options": {
                "responsive": True,
                "scales": {
                    "y": {"type": "linear", "display": True, "position": "left"},
                    "y1": {"type": "linear", "display": True, "position": "right", "grid": {"drawOnChartArea": False}}
                }
            }
        }
    
    async def _get_risk_metrics_data(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get risk metrics data"""
        # Generate sample risk metrics
        metrics = ['VaR 95%', 'VaR 99%', 'Expected Shortfall', 'Beta', 'Sharpe Ratio']
        values = []
        limits = []
        
        for i, metric in enumerate(metrics):
            value = 50 + hash(f"risk{i}") % 100
            limit = value + 20 + hash(f"limit{i}") % 30
            values.append(value)
            limits.append(limit)
        
        return {
            "chart_type": "bar",
            "data": {
                "labels": metrics,
                "datasets": [
                    {
                        "label": "Current",
                        "data": values,
                        "backgroundColor": "rgba(255, 193, 7, 0.6)",
                        "borderColor": "#ffc107",
                        "borderWidth": 1
                    },
                    {
                        "label": "Limit",
                        "data": limits,
                        "backgroundColor": "rgba(220, 53, 69, 0.6)",
                        "borderColor": "#dc3545",
                        "borderWidth": 1
                    }
                ]
            },
            "options": {
                "responsive": True,
                "scales": {
                    "y": {"beginAtZero": True}
                }
            }
        }

class MetricWidgetProvider(WidgetDataProvider):
    """Metric widget data provider"""
    
    def __init__(self):
        super().__init__("metric")
    
    async def get_widget_data(self, widget_config: WidgetConfig) -> Dict[str, Any]:
        """Get metric data"""
        try:
            data_source = widget_config.data_source
            parameters = widget_config.parameters
            
            if data_source == "portfolio_value":
                return await self._get_portfolio_value(parameters)
            elif data_source == "daily_pnl":
                return await self._get_daily_pnl(parameters)
            elif data_source == "position_count":
                return await self._get_position_count(parameters)
            elif data_source == "risk_utilization":
                return await self._get_risk_utilization(parameters)
            else:
                return {"error": f"Unknown data source: {data_source}"}
        
        except Exception as e:
            self.logger.error(f"Error getting metric data: {e}")
            return {"error": str(e)}
    
    async def _get_portfolio_value(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get portfolio value metric"""
        # Generate sample portfolio value
        value = 1000000 + hash("portfolio") % 5000000
        change = (hash("portfolio_change") % 200000 - 100000)
        change_percent = (change / value) * 100
        
        return {
            "value": value,
            "formatted_value": f"${value:,.2f}",
            "change": change,
            "change_percent": change_percent,
            "status": "positive" if change >= 0 else "negative",
            "trend": "up" if change >= 0 else "down",
            "last_updated": datetime.now().isoformat()
        }
    
    async def _get_daily_pnl(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get daily P&L metric"""
        pnl = (hash("daily_pnl") % 100000 - 50000)
        
        return {
            "value": pnl,
            "formatted_value": f"${pnl:+,.2f}",
            "status": "positive" if pnl >= 0 else "negative",
            "trend": "up" if pnl >= 0 else "down",
            "last_updated": datetime.now().isoformat()
        }
    
    async def _get_position_count(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get position count metric"""
        count = 5 + hash("positions") % 20
        
        return {
            "value": count,
            "formatted_value": str(count),
            "status": "neutral",
            "trend": "stable",
            "last_updated": datetime.now().isoformat()
        }
    
    async def _get_risk_utilization(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get risk utilization metric"""
        utilization = 30 + hash("risk_util") % 60
        
        status = "normal"
        if utilization > 80:
            status = "critical"
        elif utilization > 60:
            status = "warning"
        
        return {
            "value": utilization,
            "formatted_value": f"{utilization}%",
            "status": status,
            "trend": "stable",
            "last_updated": datetime.now().isoformat()
        }

class TableWidgetProvider(WidgetDataProvider):
    """Table widget data provider"""
    
    def __init__(self):
        super().__init__("table")
    
    async def get_widget_data(self, widget_config: WidgetConfig) -> Dict[str, Any]:
        """Get table data"""
        try:
            data_source = widget_config.data_source
            parameters = widget_config.parameters
            
            if data_source == "positions":
                return await self._get_positions_table(parameters)
            elif data_source == "orders":
                return await self._get_orders_table(parameters)
            elif data_source == "trades":
                return await self._get_trades_table(parameters)
            elif data_source == "watchlist":
                return await self._get_watchlist_table(parameters)
            else:
                return {"error": f"Unknown data source: {data_source}"}
        
        except Exception as e:
            self.logger.error(f"Error getting table data: {e}")
            return {"error": str(e)}
    
    async def _get_positions_table(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get positions table data"""
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'NVDA', 'META']
        
        columns = [
            {"key": "symbol", "title": "Symbol", "sortable": True},
            {"key": "quantity", "title": "Quantity", "sortable": True, "type": "number"},
            {"key": "avg_price", "title": "Avg Price", "sortable": True, "type": "currency"},
            {"key": "market_price", "title": "Market Price", "sortable": True, "type": "currency"},
            {"key": "market_value", "title": "Market Value", "sortable": True, "type": "currency"},
            {"key": "unrealized_pnl", "title": "Unrealized P&L", "sortable": True, "type": "currency"},
            {"key": "percentage_change", "title": "% Change", "sortable": True, "type": "percentage"}
        ]
        
        rows = []
        for symbol in symbols:
            quantity = 100 + hash(f"{symbol}qty") % 500
            avg_price = 100 + hash(f"{symbol}avg") % 100
            market_price = avg_price + (hash(f"{symbol}mkt") % 20 - 10)
            market_value = quantity * market_price
            unrealized_pnl = quantity * (market_price - avg_price)
            percentage_change = ((market_price - avg_price) / avg_price) * 100
            
            rows.append({
                "symbol": symbol,
                "quantity": quantity,
                "avg_price": avg_price,
                "market_price": market_price,
                "market_value": market_value,
                "unrealized_pnl": unrealized_pnl,
                "percentage_change": percentage_change
            })
        
        return {
            "columns": columns,
            "rows": rows,
            "total_rows": len(rows),
            "sortable": True,
            "filterable": True,
            "paginated": True,
            "page_size": 10
        }
    
    async def _get_orders_table(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get orders table data"""
        columns = [
            {"key": "order_id", "title": "Order ID", "sortable": True},
            {"key": "symbol", "title": "Symbol", "sortable": True},
            {"key": "side", "title": "Side", "sortable": True},
            {"key": "quantity", "title": "Quantity", "sortable": True, "type": "number"},
            {"key": "price", "title": "Price", "sortable": True, "type": "currency"},
            {"key": "status", "title": "Status", "sortable": True},
            {"key": "timestamp", "title": "Time", "sortable": True, "type": "datetime"}
        ]
        
        rows = []
        statuses = ['PENDING', 'FILLED', 'CANCELLED', 'REJECTED']
        sides = ['BUY', 'SELL']
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA']
        
        for i in range(20):
            rows.append({
                "order_id": f"ORD_{i:04d}",
                "symbol": symbols[i % len(symbols)],
                "side": sides[i % len(sides)],
                "quantity": 100 + hash(f"ord{i}") % 500,
                "price": 100 + hash(f"price{i}") % 100,
                "status": statuses[hash(f"status{i}") % len(statuses)],
                "timestamp": (datetime.now() - timedelta(hours=hash(f"time{i}") % 24)).isoformat()
            })
        
        return {
            "columns": columns,
            "rows": rows,
            "total_rows": len(rows),
            "sortable": True,
            "filterable": True,
            "paginated": True,
            "page_size": 10
        }
    
    async def _get_trades_table(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get trades table data"""
        columns = [
            {"key": "trade_id", "title": "Trade ID", "sortable": True},
            {"key": "symbol", "title": "Symbol", "sortable": True},
            {"key": "side", "title": "Side", "sortable": True},
            {"key": "quantity", "title": "Quantity", "sortable": True, "type": "number"},
            {"key": "price", "title": "Price", "sortable": True, "type": "currency"},
            {"key": "pnl", "title": "P&L", "sortable": True, "type": "currency"},
            {"key": "timestamp", "title": "Time", "sortable": True, "type": "datetime"}
        ]
        
        rows = []
        sides = ['BUY', 'SELL']
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']
        
        for i in range(30):
            pnl = (hash(f"pnl{i}") % 2000 - 1000)
            rows.append({
                "trade_id": f"TRD_{i:04d}",
                "symbol": symbols[i % len(symbols)],
                "side": sides[i % len(sides)],
                "quantity": 50 + hash(f"trd{i}") % 200,
                "price": 100 + hash(f"tprice{i}") % 100,
                "pnl": pnl,
                "timestamp": (datetime.now() - timedelta(hours=hash(f"ttime{i}") % 48)).isoformat()
            })
        
        return {
            "columns": columns,
            "rows": rows,
            "total_rows": len(rows),
            "sortable": True,
            "filterable": True,
            "paginated": True,
            "page_size": 15
        }
    
    async def _get_watchlist_table(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get watchlist table data"""
        columns = [
            {"key": "symbol", "title": "Symbol", "sortable": True},
            {"key": "last_price", "title": "Last Price", "sortable": True, "type": "currency"},
            {"key": "change", "title": "Change", "sortable": True, "type": "currency"},
            {"key": "change_percent", "title": "% Change", "sortable": True, "type": "percentage"},
            {"key": "volume", "title": "Volume", "sortable": True, "type": "number"},
            {"key": "market_cap", "title": "Market Cap", "sortable": True, "type": "currency"}
        ]
        
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'NVDA', 'META', 'NFLX', 'CRM', 'ORCL']
        rows = []
        
        for symbol in symbols:
            last_price = 100 + hash(f"{symbol}price") % 200
            change = (hash(f"{symbol}change") % 20 - 10)
            change_percent = (change / last_price) * 100
            volume = 1000000 + hash(f"{symbol}vol") % 10000000
            market_cap = last_price * (1000000000 + hash(f"{symbol}cap") % 2000000000)
            
            rows.append({
                "symbol": symbol,
                "last_price": last_price,
                "change": change,
                "change_percent": change_percent,
                "volume": volume,
                "market_cap": market_cap
            })
        
        return {
            "columns": columns,
            "rows": rows,
            "total_rows": len(rows),
            "sortable": True,
            "filterable": True,
            "paginated": True,
            "page_size": 10
        }

class CustomizableDashboardSystem:
    """Main customizable dashboard system"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 5002):
        self.host = host
        self.port = port
        self.logger = logging.getLogger(__name__)
        
        if not FLASK_AVAILABLE:
            raise ImportError("Flask and related packages are required for dashboard system")
        
        self.app = Flask(__name__)
        self.app.secret_key = 'dashboard_secret_key'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # Data storage (replace with proper database in production)
        self.dashboards: Dict[str, Dashboard] = {}
        self.templates: Dict[str, DashboardTemplate] = {}
        self.themes: Dict[str, DashboardTheme] = {}
        
        # Widget data providers
        self.data_providers: Dict[str, WidgetDataProvider] = {
            "chart": ChartWidgetProvider(),
            "metric": MetricWidgetProvider(),
            "table": TableWidgetProvider()
        }
        
        self._setup_routes()
        self._setup_socket_events()
        self._initialize_default_themes()
        self._initialize_default_templates()
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def dashboard_home():
            """Dashboard home page"""
            return render_template('dashboard_home.html', 
                                 dashboards=list(self.dashboards.values()),
                                 templates=list(self.templates.values()))
        
        @self.app.route('/dashboard/<dashboard_id>')
        def view_dashboard(dashboard_id):
            """View specific dashboard"""
            dashboard = self.dashboards.get(dashboard_id)
            if not dashboard:
                return "Dashboard not found", 404
            
            return render_template('dashboard_view.html', dashboard=dashboard)
        
        @self.app.route('/dashboard/<dashboard_id>/edit')
        def edit_dashboard(dashboard_id):
            """Edit dashboard"""
            dashboard = self.dashboards.get(dashboard_id)
            if not dashboard:
                return "Dashboard not found", 404
            
            return render_template('dashboard_edit.html', 
                                 dashboard=dashboard,
                                 themes=list(self.themes.values()))
        
        @self.app.route('/create_dashboard')
        def create_dashboard_page():
            """Create new dashboard page"""
            return render_template('dashboard_create.html',
                                 templates=list(self.templates.values()),
                                 themes=list(self.themes.values()))
        
        @self.app.route('/api/dashboards', methods=['GET'])
        def api_get_dashboards():
            """Get all dashboards"""
            return jsonify([asdict(dashboard) for dashboard in self.dashboards.values()])
        
        @self.app.route('/api/dashboards', methods=['POST'])
        def api_create_dashboard():
            """Create new dashboard"""
            try:
                data = request.get_json()
                
                dashboard = Dashboard(
                    dashboard_id=str(uuid.uuid4()),
                    name=data['name'],
                    description=data.get('description', ''),
                    owner_id=data.get('owner_id', 'default_user'),
                    widgets=[],
                    layout=DashboardLayout(
                        layout_id=str(uuid.uuid4()),
                        layout_type=LayoutType(data.get('layout_type', 'grid'))
                    ),
                    theme=self.themes.get(data.get('theme_id', 'light')),
                    tags=data.get('tags', [])
                )
                
                self.dashboards[dashboard.dashboard_id] = dashboard
                
                return jsonify({
                    'success': True,
                    'dashboard_id': dashboard.dashboard_id,
                    'dashboard': asdict(dashboard)
                })
            
            except Exception as e:
                self.logger.error(f"Error creating dashboard: {e}")
                return jsonify({'success': False, 'error': str(e)}), 400
        
        @self.app.route('/api/dashboards/<dashboard_id>', methods=['PUT'])
        def api_update_dashboard(dashboard_id):
            """Update dashboard"""
            try:
                dashboard = self.dashboards.get(dashboard_id)
                if not dashboard:
                    return jsonify({'success': False, 'error': 'Dashboard not found'}), 404
                
                data = request.get_json()
                
                # Update dashboard properties
                if 'name' in data:
                    dashboard.name = data['name']
                if 'description' in data:
                    dashboard.description = data['description']
                if 'widgets' in data:
                    dashboard.widgets = [WidgetConfig(**widget) for widget in data['widgets']]
                if 'layout' in data:
                    dashboard.layout = DashboardLayout(**data['layout'])
                if 'theme_id' in data:
                    dashboard.theme = self.themes.get(data['theme_id'])
                
                dashboard.updated_at = datetime.now()
                
                return jsonify({'success': True, 'dashboard': asdict(dashboard)})
            
            except Exception as e:
                self.logger.error(f"Error updating dashboard: {e}")
                return jsonify({'success': False, 'error': str(e)}), 400
        
        @self.app.route('/api/dashboards/<dashboard_id>', methods=['DELETE'])
        def api_delete_dashboard(dashboard_id):
            """Delete dashboard"""
            try:
                if dashboard_id in self.dashboards:
                    del self.dashboards[dashboard_id]
                    return jsonify({'success': True})
                else:
                    return jsonify({'success': False, 'error': 'Dashboard not found'}), 404
            
            except Exception as e:
                self.logger.error(f"Error deleting dashboard: {e}")
                return jsonify({'success': False, 'error': str(e)}), 400
        
        @self.app.route('/api/widgets/<widget_id>/data')
        def api_get_widget_data(widget_id):
            """Get widget data"""
            try:
                # Find widget in all dashboards
                widget_config = None
                for dashboard in self.dashboards.values():
                    for widget in dashboard.widgets:
                        if widget.widget_id == widget_id:
                            widget_config = widget
                            break
                    if widget_config:
                        break
                
                if not widget_config:
                    return jsonify({'error': 'Widget not found'}), 404
                
                # Get data provider
                provider = self.data_providers.get(widget_config.widget_type.value)
                if not provider:
                    return jsonify({'error': f'No provider for widget type: {widget_config.widget_type.value}'}), 400
                
                # Get widget data (run async function in event loop)
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    data = loop.run_until_complete(provider.get_widget_data(widget_config))
                except RuntimeError:
                    # No event loop running, create one
                    data = asyncio.run(provider.get_widget_data(widget_config))
                
                return jsonify({
                    'widget_id': widget_id,
                    'data': data,
                    'last_updated': datetime.now().isoformat()
                })
            
            except Exception as e:
                self.logger.error(f"Error getting widget data: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/templates')
        def api_get_templates():
            """Get dashboard templates"""
            return jsonify([asdict(template) for template in self.templates.values()])
        
        @self.app.route('/api/themes')
        def api_get_themes():
            """Get dashboard themes"""
            return jsonify([asdict(theme) for theme in self.themes.values()])
    
    def _setup_socket_events(self):
        """Setup SocketIO events"""
        
        @self.socketio.on('connect')
        def handle_connect():
            emit('connected', {'message': 'Connected to dashboard system'})
        
        @self.socketio.on('join_dashboard')
        def handle_join_dashboard(data):
            """Join dashboard room for real-time updates"""
            dashboard_id = data.get('dashboard_id')
            if dashboard_id:
                join_room(dashboard_id)
                emit('joined_dashboard', {'dashboard_id': dashboard_id})
        
        @self.socketio.on('leave_dashboard')
        def handle_leave_dashboard(data):
            """Leave dashboard room"""
            dashboard_id = data.get('dashboard_id')
            if dashboard_id:
                leave_room(dashboard_id)
                emit('left_dashboard', {'dashboard_id': dashboard_id})
        
        @self.socketio.on('update_widget_layout')
        def handle_update_widget_layout(data):
            """Update widget layout in real-time"""
            dashboard_id = data.get('dashboard_id')
            widget_id = data.get('widget_id')
            new_position = data.get('position')
            
            if dashboard_id and widget_id and new_position:
                dashboard = self.dashboards.get(dashboard_id)
                if dashboard:
                    for widget in dashboard.widgets:
                        if widget.widget_id == widget_id:
                            widget.position = new_position
                            break
                    
                    # Broadcast update to all users viewing this dashboard
                    emit('widget_layout_updated', {
                        'dashboard_id': dashboard_id,
                        'widget_id': widget_id,
                        'position': new_position
                    }, room=dashboard_id)
        
        @self.socketio.on('request_widget_refresh')
        def handle_widget_refresh(data):
            """Handle widget refresh request"""
            widget_id = data.get('widget_id')
            if widget_id:
                # Trigger widget data refresh
                emit('widget_refresh_requested', {'widget_id': widget_id})
    
    def _initialize_default_themes(self):
        """Initialize default dashboard themes"""
        # Light theme
        light_theme = DashboardTheme(
            theme_id="light",
            theme_type=ThemeType.LIGHT,
            name="Light Theme",
            colors={
                "primary": "#007bff",
                "secondary": "#6c757d",
                "success": "#28a745",
                "danger": "#dc3545",
                "warning": "#ffc107",
                "info": "#17a2b8",
                "background": "#ffffff",
                "surface": "#f8f9fa",
                "text": "#212529"
            },
            fonts={
                "primary": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                "monospace": "'Monaco', 'Menlo', 'Ubuntu Mono', monospace"
            },
            spacing={
                "xs": 4,
                "sm": 8,
                "md": 16,
                "lg": 24,
                "xl": 32
            }
        )
        
        # Dark theme
        dark_theme = DashboardTheme(
            theme_id="dark",
            theme_type=ThemeType.DARK,
            name="Dark Theme",
            colors={
                "primary": "#0d6efd",
                "secondary": "#6c757d",
                "success": "#198754",
                "danger": "#dc3545",
                "warning": "#ffc107",
                "info": "#0dcaf0",
                "background": "#212529",
                "surface": "#343a40",
                "text": "#ffffff"
            },
            fonts={
                "primary": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                "monospace": "'Monaco', 'Menlo', 'Ubuntu Mono', monospace"
            },
            spacing={
                "xs": 4,
                "sm": 8,
                "md": 16,
                "lg": 24,
                "xl": 32
            }
        )
        
        self.themes["light"] = light_theme
        self.themes["dark"] = dark_theme
    
    def _initialize_default_templates(self):
        """Initialize default dashboard templates"""
        # Trading dashboard template
        trading_template = DashboardTemplate(
            template_id="trading_dashboard",
            name="Trading Dashboard",
            description="Comprehensive trading dashboard with positions, orders, and market data",
            category="Trading",
            widgets=[
                WidgetConfig(
                    widget_id="portfolio_value",
                    widget_type=WidgetType.METRIC,
                    title="Portfolio Value",
                    data_source="portfolio_value",
                    position={"x": 0, "y": 0, "w": 3, "h": 2}
                ),
                WidgetConfig(
                    widget_id="daily_pnl",
                    widget_type=WidgetType.METRIC,
                    title="Daily P&L",
                    data_source="daily_pnl",
                    position={"x": 3, "y": 0, "w": 3, "h": 2}
                ),
                WidgetConfig(
                    widget_id="positions_table",
                    widget_type=WidgetType.TABLE,
                    title="Positions",
                    data_source="positions",
                    position={"x": 0, "y": 2, "w": 6, "h": 4}
                ),
                WidgetConfig(
                    widget_id="pnl_chart",
                    widget_type=WidgetType.CHART,
                    title="P&L Chart",
                    data_source="pnl_chart",
                    position={"x": 6, "y": 0, "w": 6, "h": 6}
                )
            ],
            layout=DashboardLayout(
                layout_id="trading_layout",
                layout_type=LayoutType.GRID
            ),
            theme=self.themes["light"],
            tags=["trading", "portfolio", "pnl"]
        )
        
        # Risk dashboard template
        risk_template = DashboardTemplate(
            template_id="risk_dashboard",
            name="Risk Dashboard",
            description="Risk monitoring dashboard with VaR, exposure, and compliance metrics",
            category="Risk",
            widgets=[
                WidgetConfig(
                    widget_id="risk_utilization",
                    widget_type=WidgetType.METRIC,
                    title="Risk Utilization",
                    data_source="risk_utilization",
                    position={"x": 0, "y": 0, "w": 3, "h": 2}
                ),
                WidgetConfig(
                    widget_id="risk_metrics_chart",
                    widget_type=WidgetType.CHART,
                    title="Risk Metrics",
                    data_source="risk_metrics",
                    position={"x": 3, "y": 0, "w": 9, "h": 4}
                )
            ],
            layout=DashboardLayout(
                layout_id="risk_layout",
                layout_type=LayoutType.GRID
            ),
            theme=self.themes["dark"],
            tags=["risk", "var", "compliance"]
        )
        
        self.templates["trading_dashboard"] = trading_template
        self.templates["risk_dashboard"] = risk_template
    
    async def start_widget_updates(self):
        """Start background task for widget updates"""
        while True:
            try:
                # Update all widgets that need refreshing
                for dashboard in self.dashboards.values():
                    for widget in dashboard.widgets:
                        if widget.refresh_interval > 0:
                            # Check if widget needs updating
                            # In a real implementation, you'd track last update times
                            
                            # Get data provider
                            provider = self.data_providers.get(widget.widget_type.value)
                            if provider:
                                try:
                                    data = await provider.get_widget_data(widget)
                                    
                                    # Emit update to dashboard room
                                    self.socketio.emit('widget_data_updated', {
                                        'widget_id': widget.widget_id,
                                        'data': data,
                                        'timestamp': datetime.now().isoformat()
                                    }, room=dashboard.dashboard_id)
                                
                                except Exception as e:
                                    self.logger.error(f"Error updating widget {widget.widget_id}: {e}")
                
                await asyncio.sleep(30)  # Update every 30 seconds
            
            except Exception as e:
                self.logger.error(f"Error in widget updates: {e}")
                await asyncio.sleep(60)
    
    def run(self, debug: bool = False):
        """Run the dashboard system"""
        self.logger.info(f"Starting customizable dashboard system on {self.host}:{self.port}")
        
        # Start background tasks
        asyncio.create_task(self.start_widget_updates())
        
        self.socketio.run(self.app, host=self.host, port=self.port, debug=debug)

def create_dashboard_system(host: str = "0.0.0.0", port: int = 5002) -> CustomizableDashboardSystem:
    """Create and configure dashboard system"""
    return CustomizableDashboardSystem(host=host, port=port)

if __name__ == "__main__":
    system = create_dashboard_system()
    system.run(debug=True)