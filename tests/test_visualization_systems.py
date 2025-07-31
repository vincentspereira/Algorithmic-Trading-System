"""
Test suite for visualization systems including mobile app and customizable dashboards.
"""
import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import uuid

# Import the modules to test
from nautilus_trader_engine.mobile.mobile_trading_app import (
    MobileTradingApp, MobileUser, MobileOrder, MobilePosition, 
    MobileWatchlistItem, MobileScreenSize, TouchGesture
)
from nautilus_trader_engine.mobile.mobile_components import (
    MobileComponentRenderer, ComponentType, TouchAction, 
    MobileComponent, ResponsiveLayout, create_mobile_component
)
from nautilus_trader_engine.visualization.customizable_dashboard import (
    CustomizableDashboardSystem, Dashboard, WidgetConfig, DashboardLayout,
    DashboardTheme, WidgetType, LayoutType, ThemeType,
    ChartWidgetProvider, MetricWidgetProvider, TableWidgetProvider
)

class TestMobileTradingApp:
    """Test mobile trading application"""
    
    @pytest.fixture
    def mobile_app(self):
        """Create mobile app instance for testing"""
        with patch('nautilus_trader_engine.mobile.mobile_trading_app.FLASK_AVAILABLE', True):
            app = MobileTradingApp(host="127.0.0.1", port=5555)
            return app
    
    def test_mobile_user_creation(self):
        """Test mobile user creation"""
        user = MobileUser(
            id="test_user_1",
            username="testuser",
            device_id="device_123",
            device_type="mobile",
            screen_size=MobileScreenSize.MEDIUM
        )
        
        assert user.id == "test_user_1"
        assert user.username == "testuser"
        assert user.device_id == "device_123"
        assert user.device_type == "mobile"
        assert user.screen_size == MobileScreenSize.MEDIUM
        assert user.is_authenticated is True
        assert isinstance(user.last_activity, datetime)
    
    def test_mobile_order_creation(self):
        """Test mobile order creation"""
        order = MobileOrder(
            order_id="ORD_001",
            symbol="AAPL",
            side="buy",
            quantity=100.0,
            order_type="market"
        )
        
        assert order.order_id == "ORD_001"
        assert order.symbol == "AAPL"
        assert order.side == "buy"
        assert order.quantity == 100.0
        assert order.order_type == "market"
        assert order.status == "PENDING"
        assert isinstance(order.timestamp, datetime)
    
    def test_mobile_position_creation(self):
        """Test mobile position creation"""
        position = MobilePosition(
            symbol="GOOGL",
            quantity=50.0,
            avg_price=2500.0,
            market_price=2550.0,
            unrealized_pnl=2500.0,
            percentage_change=2.0,
            side="long"
        )
        
        assert position.symbol == "GOOGL"
        assert position.quantity == 50.0
        assert position.avg_price == 2500.0
        assert position.market_price == 2550.0
        assert position.unrealized_pnl == 2500.0
        assert position.percentage_change == 2.0
        assert position.side == "long"
    
    def test_mobile_watchlist_item_creation(self):
        """Test mobile watchlist item creation"""
        item = MobileWatchlistItem(
            symbol="TSLA",
            last_price=800.0,
            change=25.0,
            change_percent=3.2,
            volume=1500000,
            is_favorite=True
        )
        
        assert item.symbol == "TSLA"
        assert item.last_price == 800.0
        assert item.change == 25.0
        assert item.change_percent == 3.2
        assert item.volume == 1500000
        assert item.is_favorite is True
    
    @patch('nautilus_trader_engine.mobile.mobile_trading_app.FLASK_AVAILABLE', True)
    @patch('nautilus_trader_engine.mobile.mobile_trading_app.OFFLINE_AVAILABLE', True)
    def test_mobile_app_initialization(self):
        """Test mobile app initialization"""
        app = MobileTradingApp(host="127.0.0.1", port=5555)
        
        assert app.host == "127.0.0.1"
        assert app.port == 5555
        assert app.enable_offline is True
        assert app.users == {}
        assert app.orders == {}
        assert app.positions == {}
        assert app.watchlists == {}
        assert app.offline_manager is not None
    
    @patch('nautilus_trader_engine.mobile.mobile_trading_app.FLASK_AVAILABLE', False)
    def test_mobile_app_no_flask(self):
        """Test mobile app without Flask"""
        with pytest.raises(ImportError, match="Flask and related packages are required"):
            MobileTradingApp()
    
    @patch('nautilus_trader_engine.mobile.mobile_trading_app.FLASK_AVAILABLE', True)
    @patch('nautilus_trader_engine.mobile.mobile_trading_app.OFFLINE_AVAILABLE', False)
    def test_mobile_app_no_offline(self):
        """Test mobile app without offline capability"""
        app = MobileTradingApp(host="127.0.0.1", port=5555, enable_offline=True)
        
        assert app.offline_manager is None
    
    @patch('nautilus_trader_engine.mobile.mobile_trading_app.FLASK_AVAILABLE', True)
    @patch('nautilus_trader_engine.mobile.mobile_trading_app.OFFLINE_AVAILABLE', True)
    def test_mobile_app_offline_disabled(self):
        """Test mobile app with offline capability disabled"""
        app = MobileTradingApp(host="127.0.0.1", port=5555, enable_offline=False)
        
        assert app.offline_manager is None
    
    @pytest.mark.asyncio
    async def test_start_price_updates(self, mobile_app):
        """Test price updates background task"""
        # Add a test user and watchlist
        user_id = "test_user"
        mobile_app.users[user_id] = MobileUser(
            id=user_id,
            username="testuser",
            device_id="device_123",
            device_type="mobile",
            screen_size=MobileScreenSize.MEDIUM
        )
        
        mobile_app.watchlists[user_id] = [
            MobileWatchlistItem(
                symbol="AAPL",
                last_price=150.0,
                change=2.0,
                change_percent=1.35,
                volume=1000000
            )
        ]
        
        # Mock socketio emit
        mobile_app.socketio.emit = Mock()
        
        # Run price updates for a short time
        task = asyncio.create_task(mobile_app.start_price_updates())
        await asyncio.sleep(0.1)  # Let it run briefly
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        # Verify that emit was called (price updates occurred)
        assert mobile_app.socketio.emit.called

class TestMobileComponents:
    """Test mobile components system"""
    
    @pytest.fixture
    def component_renderer(self):
        """Create component renderer for testing"""
        return MobileComponentRenderer()
    
    def test_responsive_layout_creation(self):
        """Test responsive layout creation"""
        layout = ResponsiveLayout()
        
        assert layout.breakpoints['xs'] == 0
        assert layout.breakpoints['sm'] == 576
        assert layout.breakpoints['md'] == 768
        assert layout.breakpoints['lg'] == 992
        assert layout.breakpoints['xl'] == 1200
        
        assert layout.grid_columns['xs'] == 1
        assert layout.grid_columns['xl'] == 6
    
    def test_mobile_component_creation(self):
        """Test mobile component creation"""
        component = create_mobile_component(
            ComponentType.CHART,
            "test_chart",
            "Test Chart",
            {"symbol": "AAPL", "price": 150.0}
        )
        
        assert component.component_id == "test_chart"
        assert component.component_type == ComponentType.CHART
        assert component.title == "Test Chart"
        assert component.data["symbol"] == "AAPL"
        assert component.data["price"] == 150.0
        assert component.is_visible is True
        assert component.is_resizable is True
        assert component.is_draggable is True
    
    def test_chart_component_rendering(self, component_renderer):
        """Test chart component rendering"""
        component = MobileComponent(
            component_id="chart_1",
            component_type=ComponentType.CHART,
            title="AAPL Chart",
            data={
                "symbol": "AAPL",
                "price": 150.25,
                "change": 2.50
            }
        )
        
        html = component_renderer.render_component(component)
        
        assert "mobile-chart-component" in html
        assert "AAPL" in html
        assert "150.25" in html
        assert "chart-chart_1" in html
        assert "Buy" in html
        assert "Sell" in html
    
    def test_order_form_component_rendering(self, component_renderer):
        """Test order form component rendering"""
        component = MobileComponent(
            component_id="order_form_1",
            component_type=ComponentType.ORDER_FORM,
            title="Place Order",
            data={"symbol": "TSLA"}
        )
        
        html = component_renderer.render_component(component)
        
        assert "mobile-order-form" in html
        assert "Place Order" in html
        assert "TSLA" in html
        assert "submitOrder" in html
        assert "selectSide" in html
    
    def test_position_card_component_rendering(self, component_renderer):
        """Test position card component rendering"""
        component = MobileComponent(
            component_id="position_1",
            component_type=ComponentType.POSITION_CARD,
            title="Position",
            data={
                "symbol": "GOOGL",
                "quantity": 50,
                "avg_price": 2500.0,
                "market_price": 2550.0,
                "unrealized_pnl": 2500.0,
                "percentage_change": 2.0
            }
        )
        
        html = component_renderer.render_component(component)
        
        assert "mobile-position-card" in html
        assert "GOOGL" in html
        assert "50 shares" in html
        assert "2550.00" in html
        assert "2500.00" in html
        assert "+2.00%" in html
    
    def test_watchlist_item_component_rendering(self, component_renderer):
        """Test watchlist item component rendering"""
        component = MobileComponent(
            component_id="watchlist_1",
            component_type=ComponentType.WATCHLIST_ITEM,
            title="Watchlist Item",
            data={
                "symbol": "MSFT",
                "last_price": 300.0,
                "change": 5.0,
                "change_percent": 1.69,
                "volume": 2000000,
                "is_favorite": True
            }
        )
        
        html = component_renderer.render_component(component)
        
        assert "mobile-watchlist-item" in html
        assert "MSFT" in html
        assert "300.00" in html
        assert "+5.00" in html
        assert "+1.69%" in html
        assert "★" in html  # Favorite icon
    
    def test_unknown_component_type_rendering(self, component_renderer):
        """Test rendering unknown component type"""
        component = MobileComponent(
            component_id="unknown_1",
            component_type="unknown_type",  # Invalid type
            title="Unknown Component",
            data={}
        )
        
        html = component_renderer.render_component(component)
        assert "Unknown component type" in html

class TestCustomizableDashboardSystem:
    """Test customizable dashboard system"""
    
    @pytest.fixture
    def dashboard_system(self):
        """Create dashboard system for testing"""
        with patch('nautilus_trader_engine.visualization.customizable_dashboard.FLASK_AVAILABLE', True):
            system = CustomizableDashboardSystem(host="127.0.0.1", port=5556)
            return system
    
    def test_widget_config_creation(self):
        """Test widget configuration creation"""
        widget = WidgetConfig(
            widget_id="test_widget",
            widget_type=WidgetType.CHART,
            title="Test Chart",
            data_source="price_history",
            parameters={"symbol": "AAPL", "days": 30}
        )
        
        assert widget.widget_id == "test_widget"
        assert widget.widget_type == WidgetType.CHART
        assert widget.title == "Test Chart"
        assert widget.data_source == "price_history"
        assert widget.parameters["symbol"] == "AAPL"
        assert widget.parameters["days"] == 30
        assert widget.is_visible is True
        assert widget.is_resizable is True
        assert widget.is_draggable is True
    
    def test_dashboard_layout_creation(self):
        """Test dashboard layout creation"""
        layout = DashboardLayout(
            layout_id="test_layout",
            layout_type=LayoutType.GRID,
            grid_columns=12,
            grid_rows=20
        )
        
        assert layout.layout_id == "test_layout"
        assert layout.layout_type == LayoutType.GRID
        assert layout.grid_columns == 12
        assert layout.grid_rows == 20
        assert layout.row_height == 60
        assert layout.margin == [10, 10]
    
    def test_dashboard_theme_creation(self):
        """Test dashboard theme creation"""
        theme = DashboardTheme(
            theme_id="test_theme",
            theme_type=ThemeType.DARK,
            name="Test Dark Theme",
            colors={"primary": "#007bff", "background": "#212529"}
        )
        
        assert theme.theme_id == "test_theme"
        assert theme.theme_type == ThemeType.DARK
        assert theme.name == "Test Dark Theme"
        assert theme.colors["primary"] == "#007bff"
        assert theme.colors["background"] == "#212529"
    
    def test_dashboard_creation(self):
        """Test dashboard creation"""
        layout = DashboardLayout(
            layout_id="layout_1",
            layout_type=LayoutType.GRID
        )
        
        theme = DashboardTheme(
            theme_id="theme_1",
            theme_type=ThemeType.LIGHT,
            name="Light Theme"
        )
        
        dashboard = Dashboard(
            dashboard_id="dash_1",
            name="Test Dashboard",
            description="A test dashboard",
            owner_id="user_1",
            layout=layout,
            theme=theme,
            tags=["test", "demo"]
        )
        
        assert dashboard.dashboard_id == "dash_1"
        assert dashboard.name == "Test Dashboard"
        assert dashboard.description == "A test dashboard"
        assert dashboard.owner_id == "user_1"
        assert dashboard.layout == layout
        assert dashboard.theme == theme
        assert dashboard.tags == ["test", "demo"]
        assert dashboard.is_public is False
        assert dashboard.is_template is False
    
    @patch('nautilus_trader_engine.visualization.customizable_dashboard.FLASK_AVAILABLE', True)
    def test_dashboard_system_initialization(self):
        """Test dashboard system initialization"""
        system = CustomizableDashboardSystem(host="127.0.0.1", port=5556)
        
        assert system.host == "127.0.0.1"
        assert system.port == 5556
        assert system.dashboards == {}
        assert system.templates != {}  # Should have default templates
        assert system.themes != {}     # Should have default themes
        assert "chart" in system.data_providers
        assert "metric" in system.data_providers
        assert "table" in system.data_providers
    
    @patch('nautilus_trader_engine.visualization.customizable_dashboard.FLASK_AVAILABLE', False)
    def test_dashboard_system_no_flask(self):
        """Test dashboard system without Flask"""
        with pytest.raises(ImportError, match="Flask and related packages are required"):
            CustomizableDashboardSystem()
    
    def test_default_themes_initialization(self, dashboard_system):
        """Test default themes are properly initialized"""
        assert "light" in dashboard_system.themes
        assert "dark" in dashboard_system.themes
        
        light_theme = dashboard_system.themes["light"]
        assert light_theme.theme_type == ThemeType.LIGHT
        assert light_theme.colors["background"] == "#ffffff"
        assert light_theme.colors["text"] == "#212529"
        
        dark_theme = dashboard_system.themes["dark"]
        assert dark_theme.theme_type == ThemeType.DARK
        assert dark_theme.colors["background"] == "#212529"
        assert dark_theme.colors["text"] == "#ffffff"
    
    def test_default_templates_initialization(self, dashboard_system):
        """Test default templates are properly initialized"""
        assert "trading_dashboard" in dashboard_system.templates
        assert "risk_dashboard" in dashboard_system.templates
        
        trading_template = dashboard_system.templates["trading_dashboard"]
        assert trading_template.name == "Trading Dashboard"
        assert trading_template.category == "Trading"
        assert len(trading_template.widgets) > 0
        assert "trading" in trading_template.tags
        
        risk_template = dashboard_system.templates["risk_dashboard"]
        assert risk_template.name == "Risk Dashboard"
        assert risk_template.category == "Risk"
        assert len(risk_template.widgets) > 0
        assert "risk" in risk_template.tags

class TestWidgetDataProviders:
    """Test widget data providers"""
    
    @pytest.fixture
    def chart_provider(self):
        """Create chart widget provider"""
        return ChartWidgetProvider()
    
    @pytest.fixture
    def metric_provider(self):
        """Create metric widget provider"""
        return MetricWidgetProvider()
    
    @pytest.fixture
    def table_provider(self):
        """Create table widget provider"""
        return TableWidgetProvider()
    
    @pytest.mark.asyncio
    async def test_chart_provider_price_history(self, chart_provider):
        """Test chart provider price history data"""
        widget_config = WidgetConfig(
            widget_id="chart_1",
            widget_type=WidgetType.CHART,
            title="Price Chart",
            data_source="price_history",
            parameters={"symbol": "AAPL", "days": 10}
        )
        
        data = await chart_provider.get_widget_data(widget_config)
        
        assert "chart_type" in data
        assert data["chart_type"] == "line"
        assert "data" in data
        assert "labels" in data["data"]
        assert "datasets" in data["data"]
        assert len(data["data"]["datasets"]) == 1
        assert data["data"]["datasets"][0]["label"] == "AAPL Price"
    
    @pytest.mark.asyncio
    async def test_chart_provider_volume_profile(self, chart_provider):
        """Test chart provider volume profile data"""
        widget_config = WidgetConfig(
            widget_id="chart_2",
            widget_type=WidgetType.CHART,
            title="Volume Profile",
            data_source="volume_profile",
            parameters={"symbol": "GOOGL"}
        )
        
        data = await chart_provider.get_widget_data(widget_config)
        
        assert "chart_type" in data
        assert data["chart_type"] == "bar"
        assert "data" in data
        assert "options" in data
        assert data["options"]["indexAxis"] == "y"
    
    @pytest.mark.asyncio
    async def test_chart_provider_pnl_chart(self, chart_provider):
        """Test chart provider P&L chart data"""
        widget_config = WidgetConfig(
            widget_id="chart_3",
            widget_type=WidgetType.CHART,
            title="P&L Chart",
            data_source="pnl_chart",
            parameters={"days": 15}
        )
        
        data = await chart_provider.get_widget_data(widget_config)
        
        assert "chart_type" in data
        assert data["chart_type"] == "line"
        assert "data" in data
        assert len(data["data"]["datasets"]) == 2
        assert data["data"]["datasets"][0]["label"] == "Daily P&L"
        assert data["data"]["datasets"][1]["label"] == "Cumulative P&L"
    
    @pytest.mark.asyncio
    async def test_chart_provider_unknown_source(self, chart_provider):
        """Test chart provider with unknown data source"""
        widget_config = WidgetConfig(
            widget_id="chart_4",
            widget_type=WidgetType.CHART,
            title="Unknown Chart",
            data_source="unknown_source"
        )
        
        data = await chart_provider.get_widget_data(widget_config)
        
        assert "error" in data
        assert "Unknown data source" in data["error"]
    
    @pytest.mark.asyncio
    async def test_metric_provider_portfolio_value(self, metric_provider):
        """Test metric provider portfolio value"""
        widget_config = WidgetConfig(
            widget_id="metric_1",
            widget_type=WidgetType.METRIC,
            title="Portfolio Value",
            data_source="portfolio_value"
        )
        
        data = await metric_provider.get_widget_data(widget_config)
        
        assert "value" in data
        assert "formatted_value" in data
        assert "change" in data
        assert "change_percent" in data
        assert "status" in data
        assert "trend" in data
        assert "last_updated" in data
        assert data["formatted_value"].startswith("$")
    
    @pytest.mark.asyncio
    async def test_metric_provider_daily_pnl(self, metric_provider):
        """Test metric provider daily P&L"""
        widget_config = WidgetConfig(
            widget_id="metric_2",
            widget_type=WidgetType.METRIC,
            title="Daily P&L",
            data_source="daily_pnl"
        )
        
        data = await metric_provider.get_widget_data(widget_config)
        
        assert "value" in data
        assert "formatted_value" in data
        assert "status" in data
        assert "trend" in data
        assert data["status"] in ["positive", "negative"]
        assert data["trend"] in ["up", "down"]
    
    @pytest.mark.asyncio
    async def test_metric_provider_risk_utilization(self, metric_provider):
        """Test metric provider risk utilization"""
        widget_config = WidgetConfig(
            widget_id="metric_3",
            widget_type=WidgetType.METRIC,
            title="Risk Utilization",
            data_source="risk_utilization"
        )
        
        data = await metric_provider.get_widget_data(widget_config)
        
        assert "value" in data
        assert "formatted_value" in data
        assert "status" in data
        assert data["formatted_value"].endswith("%")
        assert data["status"] in ["normal", "warning", "critical"]
    
    @pytest.mark.asyncio
    async def test_table_provider_positions(self, table_provider):
        """Test table provider positions data"""
        widget_config = WidgetConfig(
            widget_id="table_1",
            widget_type=WidgetType.TABLE,
            title="Positions",
            data_source="positions"
        )
        
        data = await table_provider.get_widget_data(widget_config)
        
        assert "columns" in data
        assert "rows" in data
        assert "total_rows" in data
        assert "sortable" in data
        assert "filterable" in data
        assert "paginated" in data
        
        # Check columns
        column_keys = [col["key"] for col in data["columns"]]
        assert "symbol" in column_keys
        assert "quantity" in column_keys
        assert "avg_price" in column_keys
        assert "market_price" in column_keys
        assert "unrealized_pnl" in column_keys
        
        # Check rows
        assert len(data["rows"]) > 0
        first_row = data["rows"][0]
        assert "symbol" in first_row
        assert "quantity" in first_row
        assert isinstance(first_row["quantity"], (int, float))
    
    @pytest.mark.asyncio
    async def test_table_provider_orders(self, table_provider):
        """Test table provider orders data"""
        widget_config = WidgetConfig(
            widget_id="table_2",
            widget_type=WidgetType.TABLE,
            title="Orders",
            data_source="orders"
        )
        
        data = await table_provider.get_widget_data(widget_config)
        
        assert "columns" in data
        assert "rows" in data
        
        # Check columns
        column_keys = [col["key"] for col in data["columns"]]
        assert "order_id" in column_keys
        assert "symbol" in column_keys
        assert "side" in column_keys
        assert "quantity" in column_keys
        assert "status" in column_keys
        
        # Check rows
        assert len(data["rows"]) > 0
        first_row = data["rows"][0]
        assert "order_id" in first_row
        assert "status" in first_row
        assert first_row["status"] in ["PENDING", "FILLED", "CANCELLED", "REJECTED"]
    
    @pytest.mark.asyncio
    async def test_table_provider_trades(self, table_provider):
        """Test table provider trades data"""
        widget_config = WidgetConfig(
            widget_id="table_3",
            widget_type=WidgetType.TABLE,
            title="Trades",
            data_source="trades"
        )
        
        data = await table_provider.get_widget_data(widget_config)
        
        assert "columns" in data
        assert "rows" in data
        
        # Check columns
        column_keys = [col["key"] for col in data["columns"]]
        assert "trade_id" in column_keys
        assert "symbol" in column_keys
        assert "side" in column_keys
        assert "pnl" in column_keys
        
        # Check rows
        assert len(data["rows"]) > 0
        first_row = data["rows"][0]
        assert "trade_id" in first_row
        assert "pnl" in first_row
        assert isinstance(first_row["pnl"], (int, float))
    
    @pytest.mark.asyncio
    async def test_table_provider_watchlist(self, table_provider):
        """Test table provider watchlist data"""
        widget_config = WidgetConfig(
            widget_id="table_4",
            widget_type=WidgetType.TABLE,
            title="Watchlist",
            data_source="watchlist"
        )
        
        data = await table_provider.get_widget_data(widget_config)
        
        assert "columns" in data
        assert "rows" in data
        
        # Check columns
        column_keys = [col["key"] for col in data["columns"]]
        assert "symbol" in column_keys
        assert "last_price" in column_keys
        assert "change" in column_keys
        assert "change_percent" in column_keys
        assert "volume" in column_keys
        
        # Check rows
        assert len(data["rows"]) > 0
        first_row = data["rows"][0]
        assert "symbol" in first_row
        assert "last_price" in first_row
        assert isinstance(first_row["volume"], (int, float))

class TestIntegration:
    """Integration tests for visualization systems"""
    
    @pytest.mark.asyncio
    async def test_mobile_app_dashboard_integration(self):
        """Test integration between mobile app and dashboard system"""
        # This would test real integration scenarios
        # For now, we'll test that both systems can coexist
        
        with patch('nautilus_trader_engine.mobile.mobile_trading_app.FLASK_AVAILABLE', True):
            mobile_app = MobileTradingApp(host="127.0.0.1", port=5557)
            
        with patch('nautilus_trader_engine.visualization.customizable_dashboard.FLASK_AVAILABLE', True):
            dashboard_system = CustomizableDashboardSystem(host="127.0.0.1", port=5558)
        
        # Both systems should be initialized without conflicts
        assert mobile_app.host == "127.0.0.1"
        assert mobile_app.port == 5557
        assert dashboard_system.host == "127.0.0.1"
        assert dashboard_system.port == 5558
    
    def test_component_data_consistency(self):
        """Test data consistency between mobile components and dashboard widgets"""
        # Create similar data structures
        mobile_position = MobilePosition(
            symbol="AAPL",
            quantity=100.0,
            avg_price=150.0,
            market_price=155.0,
            unrealized_pnl=500.0,
            percentage_change=3.33,
            side="long"
        )
        
        widget_config = WidgetConfig(
            widget_id="position_widget",
            widget_type=WidgetType.POSITION_SUMMARY,
            title="Position Summary",
            data_source="positions",
            parameters={"symbol": "AAPL"}
        )
        
        # Both should represent the same underlying data
        assert mobile_position.symbol == widget_config.parameters["symbol"]
        assert isinstance(mobile_position.quantity, float)
        assert isinstance(mobile_position.unrealized_pnl, float)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])