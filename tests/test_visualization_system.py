"""
Comprehensive tests for the User Experience and Visualization system
"""
import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

# Import visualization components
from nautilus_trader_engine.visualization.trading_dashboard import (
    DashboardManager, TradingDataProvider, ChartGenerator, ChartConfig, 
    ChartType, DashboardConfig, DashboardType
)
from nautilus_trader_engine.visualization.advanced_charts import (
    AdvancedChartGenerator, TechnicalAnalysis, IndicatorType, TechnicalIndicator,
    OHLCV, OrderBookLevel, SampleDataGenerator
)
from nautilus_trader_engine.visualization.dashboard_builder import (
    DashboardBuilder, WidgetConfig, WidgetType, WidgetPosition, DashboardLayout,
    MetricWidgetProvider
)


class TestTradingDashboard:
    """Test trading dashboard functionality"""
    
    @pytest.fixture
    def dashboard_manager(self):
        """Create dashboard manager for testing"""
        return DashboardManager()
    
    @pytest.fixture
    def trading_data_provider(self):
        """Create trading data provider for testing"""
        return TradingDataProvider()
    
    def test_dashboard_manager_initialization(self, dashboard_manager):
        """Test dashboard manager initialization"""
        assert dashboard_manager is not None
        assert 'trading' in dashboard_manager.data_providers
        assert isinstance(dashboard_manager.data_providers['trading'], TradingDataProvider)
    
    def test_create_dashboard(self, dashboard_manager):
        """Test dashboard creation"""
        config = DashboardConfig(
            dashboard_id="test_dashboard",
            dashboard_type=DashboardType.TRADING,
            name="Test Dashboard",
            description="Test dashboard for unit tests"
        )
        
        dashboard_manager.create_dashboard(config)
        assert "test_dashboard" in dashboard_manager.dashboards
        assert dashboard_manager.dashboards["test_dashboard"].name == "Test Dashboard"
    
    @pytest.mark.asyncio
    async def test_trading_data_provider_trades(self, trading_data_provider):
        """Test trading data provider trades data"""
        data = await trading_data_provider.get_data("trades", {"days": 7})
        
        assert "trades" in data
        assert "total_trades" in data
        assert "total_pnl" in data
        assert isinstance(data["trades"], list)
        assert data["total_trades"] > 0
    
    @pytest.mark.asyncio
    async def test_trading_data_provider_positions(self, trading_data_provider):
        """Test trading data provider positions data"""
        data = await trading_data_provider.get_data("positions")
        
        assert "positions" in data
        assert "total_positions" in data
        assert "total_market_value" in data
        assert isinstance(data["positions"], list)
    
    @pytest.mark.asyncio
    async def test_trading_data_provider_orders(self, trading_data_provider):
        """Test trading data provider orders data"""
        data = await trading_data_provider.get_data("orders")
        
        assert "orders" in data
        assert "total_orders" in data
        assert "status_breakdown" in data
        assert isinstance(data["orders"], list)
        assert isinstance(data["status_breakdown"], dict)
    
    @pytest.mark.asyncio
    async def test_trading_data_provider_pnl(self, trading_data_provider):
        """Test trading data provider P&L data"""
        data = await trading_data_provider.get_data("pnl", {"days": 30})
        
        assert "pnl_data" in data
        assert "total_pnl" in data
        assert "avg_daily_pnl" in data
        assert "best_day" in data
        assert "worst_day" in data
        assert isinstance(data["pnl_data"], list)
    
    @pytest.mark.asyncio
    async def test_get_dashboard_data(self, dashboard_manager):
        """Test getting dashboard data"""
        # Create default trading dashboard
        config = dashboard_manager.get_default_trading_dashboard()
        dashboard_manager.create_dashboard(config)
        
        # Get dashboard data
        data = await dashboard_manager.get_dashboard_data("default_trading")
        
        assert "dashboard_id" in data
        assert "name" in data
        assert "charts" in data
        assert len(data["charts"]) > 0
        
        # Check chart data structure
        for chart in data["charts"]:
            assert "chart_id" in chart
            assert "title" in chart
            assert "html" in chart
            assert "data" in chart
    
    def test_chart_generator_initialization(self):
        """Test chart generator initialization"""
        generator = ChartGenerator()
        assert generator is not None
    
    def test_chart_config_creation(self):
        """Test chart configuration creation"""
        config = ChartConfig(
            chart_id="test_chart",
            chart_type=ChartType.LINE,
            title="Test Chart",
            data_source="test.data",
            x_axis="Time",
            y_axis="Value"
        )
        
        assert config.chart_id == "test_chart"
        assert config.chart_type == ChartType.LINE
        assert config.title == "Test Chart"
        assert config.width == 800  # default value
        assert config.height == 400  # default value


class TestAdvancedCharts:
    """Test advanced charting functionality"""
    
    @pytest.fixture
    def chart_generator(self):
        """Create advanced chart generator for testing"""
        return AdvancedChartGenerator()
    
    @pytest.fixture
    def sample_ohlcv_data(self):
        """Create sample OHLCV data for testing"""
        return SampleDataGenerator.generate_ohlcv_data(days=7)
    
    @pytest.fixture
    def sample_order_book_data(self):
        """Create sample order book data for testing"""
        return SampleDataGenerator.generate_order_book_data()
    
    def test_technical_analysis_sma(self):
        """Test Simple Moving Average calculation"""
        prices = [10, 12, 14, 16, 18, 20, 22, 24, 26, 28]
        sma = TechnicalAnalysis.simple_moving_average(prices, 5)
        
        # First 4 values should be None
        assert sma[:4] == [None, None, None, None]
        
        # 5th value should be average of first 5 prices
        expected_5th = sum(prices[:5]) / 5
        assert abs(sma[4] - expected_5th) < 0.001
    
    def test_technical_analysis_ema(self):
        """Test Exponential Moving Average calculation"""
        prices = [10, 12, 14, 16, 18, 20, 22, 24, 26, 28]
        ema = TechnicalAnalysis.exponential_moving_average(prices, 5)
        
        # First value should equal first price
        assert ema[0] == prices[0]
        
        # EMA should have same length as input
        assert len(ema) == len(prices)
        
        # EMA values should be increasing for increasing prices
        assert ema[-1] > ema[0]
    
    def test_technical_analysis_rsi(self):
        """Test RSI calculation"""
        # Create price data with clear trend
        prices = list(range(10, 30)) + list(range(30, 10, -1))
        rsi = TechnicalAnalysis.rsi(prices, 14)
        
        # RSI should have same length as input
        assert len(rsi) == len(prices)
        
        # First 14 values should be None
        assert all(x is None for x in rsi[:14])
        
        # RSI values should be between 0 and 100
        valid_rsi = [x for x in rsi if x is not None]
        assert all(0 <= x <= 100 for x in valid_rsi)
    
    def test_technical_analysis_macd(self):
        """Test MACD calculation"""
        prices = [10 + i * 0.5 for i in range(50)]  # Trending prices
        macd_line, signal_line, histogram = TechnicalAnalysis.macd(prices, 12, 26, 9)
        
        # All arrays should have same length as input
        assert len(macd_line) == len(prices)
        assert len(signal_line) == len(prices)
        assert len(histogram) == len(prices)
    
    def test_technical_analysis_bollinger_bands(self):
        """Test Bollinger Bands calculation"""
        prices = [10 + i * 0.1 for i in range(30)]  # Slightly trending prices
        sma, upper, lower = TechnicalAnalysis.bollinger_bands(prices, 20, 2)
        
        # All arrays should have same length as input
        assert len(sma) == len(prices)
        assert len(upper) == len(prices)
        assert len(lower) == len(prices)
        
        # Upper band should be above SMA, lower band below
        for i in range(20, len(prices)):
            if sma[i] is not None and upper[i] is not None and lower[i] is not None:
                assert upper[i] > sma[i]
                assert lower[i] < sma[i]
    
    def test_sample_data_generator_ohlcv(self):
        """Test OHLCV data generation"""
        data = SampleDataGenerator.generate_ohlcv_data(days=5)
        
        assert len(data) == 5 * 24  # 5 days * 24 hours
        
        for ohlcv in data:
            assert isinstance(ohlcv, OHLCV)
            assert ohlcv.high >= ohlcv.low
            assert ohlcv.high >= ohlcv.open
            assert ohlcv.high >= ohlcv.close
            assert ohlcv.low <= ohlcv.open
            assert ohlcv.low <= ohlcv.close
            assert ohlcv.volume > 0
    
    def test_sample_data_generator_order_book(self):
        """Test order book data generation"""
        bids, asks = SampleDataGenerator.generate_order_book_data()
        
        assert len(bids) == 20
        assert len(asks) == 20
        
        # Check bid prices are descending
        bid_prices = [bid.price for bid in bids]
        assert bid_prices == sorted(bid_prices, reverse=True)
        
        # Check ask prices are ascending
        ask_prices = [ask.price for ask in asks]
        assert ask_prices == sorted(ask_prices)
        
        # Check all quantities are positive
        for bid in bids:
            assert bid.quantity > 0
            assert bid.side == 'bid'
        
        for ask in asks:
            assert ask.quantity > 0
            assert ask.side == 'ask'
    
    def test_create_candlestick_chart(self, chart_generator, sample_ohlcv_data):
        """Test candlestick chart creation"""
        indicators = [
            TechnicalIndicator(
                indicator_type=IndicatorType.SMA,
                parameters={'period': 20},
                name="SMA 20",
                color="blue"
            )
        ]
        
        chart_html = chart_generator.create_candlestick_chart(
            sample_ohlcv_data, 
            indicators, 
            "Test Candlestick Chart"
        )
        
        assert isinstance(chart_html, str)
        assert len(chart_html) > 0
    
    def test_create_order_book_visualization(self, chart_generator, sample_order_book_data):
        """Test order book visualization creation"""
        bids, asks = sample_order_book_data
        
        chart_html = chart_generator.create_order_book_visualization(
            bids, asks, "Test Order Book"
        )
        
        assert isinstance(chart_html, str)
        assert len(chart_html) > 0
    
    def test_create_volume_profile(self, chart_generator, sample_ohlcv_data):
        """Test volume profile creation"""
        chart_html = chart_generator.create_volume_profile(
            sample_ohlcv_data, bins=20, title="Test Volume Profile"
        )
        
        assert isinstance(chart_html, str)
        assert len(chart_html) > 0


class TestDashboardBuilder:
    """Test dashboard builder functionality"""
    
    @pytest.fixture
    def dashboard_builder(self):
        """Create dashboard builder for testing"""
        return DashboardBuilder()
    
    @pytest.fixture
    def sample_widget_config(self):
        """Create sample widget configuration"""
        return WidgetConfig(
            widget_id="test_widget",
            widget_type=WidgetType.METRIC,
            title="Test Widget",
            position=WidgetPosition(x=0, y=0, width=4, height=2),
            data_source="test.data",
            parameters={'metric_type': 'portfolio_value'}
        )
    
    def test_dashboard_builder_initialization(self, dashboard_builder):
        """Test dashboard builder initialization"""
        assert dashboard_builder is not None
        assert len(dashboard_builder.layouts) == 0
        assert 'metric' in dashboard_builder.widget_providers
    
    def test_create_layout(self, dashboard_builder):
        """Test layout creation"""
        layout = dashboard_builder.create_layout(
            "Test Layout", 
            "Test layout description", 
            "test_user"
        )
        
        assert layout is not None
        assert layout.name == "Test Layout"
        assert layout.description == "Test layout description"
        assert layout.owner_id == "test_user"
        assert layout.layout_id in dashboard_builder.layouts
    
    def test_add_widget(self, dashboard_builder, sample_widget_config):
        """Test adding widget to layout"""
        layout = dashboard_builder.create_layout("Test Layout", "Test description")
        
        success = dashboard_builder.add_widget(layout.layout_id, sample_widget_config)
        
        assert success is True
        assert len(layout.widgets) == 1
        assert layout.widgets[0].widget_id == "test_widget"
    
    def test_add_widget_invalid_layout(self, dashboard_builder, sample_widget_config):
        """Test adding widget to invalid layout"""
        success = dashboard_builder.add_widget("invalid_layout_id", sample_widget_config)
        assert success is False
    
    @pytest.mark.asyncio
    async def test_get_layout_data(self, dashboard_builder, sample_widget_config):
        """Test getting layout data with widget data"""
        layout = dashboard_builder.create_layout("Test Layout", "Test description")
        dashboard_builder.add_widget(layout.layout_id, sample_widget_config)
        
        layout_data = await dashboard_builder.get_layout_data(layout.layout_id)
        
        assert "layout_id" in layout_data
        assert "name" in layout_data
        assert "widgets" in layout_data
        assert "widget_data" in layout_data
        assert len(layout_data["widgets"]) == 1
        assert "test_widget" in layout_data["widget_data"]
    
    @pytest.mark.asyncio
    async def test_get_layout_data_invalid_layout(self, dashboard_builder):
        """Test getting data for invalid layout"""
        layout_data = await dashboard_builder.get_layout_data("invalid_layout_id")
        assert layout_data == {}
    
    @pytest.mark.asyncio
    async def test_metric_widget_provider(self):
        """Test metric widget data provider"""
        provider = MetricWidgetProvider()
        
        widget_config = WidgetConfig(
            widget_id="test_metric",
            widget_type=WidgetType.METRIC,
            title="Portfolio Value",
            position=WidgetPosition(x=0, y=0, width=4, height=2),
            data_source="portfolio.value",
            parameters={'metric_type': 'portfolio_value'}
        )
        
        data = await provider.get_widget_data(widget_config)
        
        assert "value" in data
        assert "change" in data
        assert "change_percent" in data
        assert "format" in data
        assert "trend" in data
        assert data["format"] == "currency"
    
    def test_widget_position(self):
        """Test widget position creation"""
        position = WidgetPosition(x=2, y=3, width=6, height=4, z_index=1)
        
        assert position.x == 2
        assert position.y == 3
        assert position.width == 6
        assert position.height == 4
        assert position.z_index == 1
    
    def test_widget_config_creation(self):
        """Test widget configuration creation"""
        position = WidgetPosition(x=0, y=0, width=4, height=2)
        
        config = WidgetConfig(
            widget_id="test_widget",
            widget_type=WidgetType.CHART,
            title="Test Chart Widget",
            position=position,
            data_source="market.data",
            refresh_interval=60,
            parameters={'chart_type': 'line'},
            styling={'color': 'blue'}
        )
        
        assert config.widget_id == "test_widget"
        assert config.widget_type == WidgetType.CHART
        assert config.title == "Test Chart Widget"
        assert config.position == position
        assert config.data_source == "market.data"
        assert config.refresh_interval == 60
        assert config.parameters['chart_type'] == 'line'
        assert config.styling['color'] == 'blue'
        assert config.is_visible is True
    
    def test_dashboard_layout_creation(self):
        """Test dashboard layout creation"""
        layout = DashboardLayout(
            layout_id="test_layout",
            name="Test Layout",
            description="Test layout for unit tests",
            theme="light",
            owner_id="test_user"
        )
        
        assert layout.layout_id == "test_layout"
        assert layout.name == "Test Layout"
        assert layout.description == "Test layout for unit tests"
        assert layout.theme == "light"
        assert layout.owner_id == "test_user"
        assert len(layout.widgets) == 0
        assert layout.grid_size["width"] == 12
        assert layout.grid_size["height"] == 20


class TestIntegration:
    """Integration tests for visualization system"""
    
    @pytest.mark.asyncio
    async def test_full_dashboard_workflow(self):
        """Test complete dashboard creation and data retrieval workflow"""
        # Create dashboard manager
        dashboard_manager = DashboardManager()
        
        # Create default trading dashboard
        config = dashboard_manager.get_default_trading_dashboard()
        dashboard_manager.create_dashboard(config)
        
        # Get dashboard data
        data = await dashboard_manager.get_dashboard_data("default_trading")
        
        # Verify complete data structure
        assert "dashboard_id" in data
        assert "name" in data
        assert "charts" in data
        assert len(data["charts"]) == 4  # Default dashboard has 4 charts
        
        # Verify each chart has required data
        for chart in data["charts"]:
            assert "chart_id" in chart
            assert "title" in chart
            assert "html" in chart
            assert "data" in chart
            assert len(chart["html"]) > 0
    
    @pytest.mark.asyncio
    async def test_dashboard_builder_with_multiple_widgets(self):
        """Test dashboard builder with multiple widget types"""
        builder = DashboardBuilder()
        
        # Create layout
        layout = builder.create_layout("Multi-Widget Dashboard", "Dashboard with multiple widgets")
        
        # Add different widget types
        widgets = [
            WidgetConfig(
                widget_id="metric_1",
                widget_type=WidgetType.METRIC,
                title="Portfolio Value",
                position=WidgetPosition(x=0, y=0, width=3, height=2),
                data_source="portfolio.value",
                parameters={'metric_type': 'portfolio_value'}
            ),
            WidgetConfig(
                widget_id="metric_2",
                widget_type=WidgetType.METRIC,
                title="Day P&L",
                position=WidgetPosition(x=3, y=0, width=3, height=2),
                data_source="portfolio.pnl",
                parameters={'metric_type': 'day_pnl'}
            )
        ]
        
        for widget in widgets:
            success = builder.add_widget(layout.layout_id, widget)
            assert success is True
        
        # Get layout data
        layout_data = await builder.get_layout_data(layout.layout_id)
        
        assert len(layout_data["widgets"]) == 2
        assert len(layout_data["widget_data"]) == 2
        assert "metric_1" in layout_data["widget_data"]
        assert "metric_2" in layout_data["widget_data"]
    
    def test_technical_indicators_integration(self):
        """Test technical indicators with chart generation"""
        # Generate sample data
        ohlcv_data = SampleDataGenerator.generate_ohlcv_data(days=30)
        
        # Create indicators
        indicators = [
            TechnicalIndicator(
                indicator_type=IndicatorType.SMA,
                parameters={'period': 20},
                name="SMA 20",
                color="blue"
            ),
            TechnicalIndicator(
                indicator_type=IndicatorType.RSI,
                parameters={'period': 14},
                name="RSI 14",
                color="purple"
            ),
            TechnicalIndicator(
                indicator_type=IndicatorType.BOLLINGER_BANDS,
                parameters={'period': 20, 'std_dev': 2},
                name="Bollinger Bands",
                color="red"
            )
        ]
        
        # Create chart generator
        chart_gen = AdvancedChartGenerator()
        
        # Generate chart with indicators
        chart_html = chart_gen.create_candlestick_chart(
            ohlcv_data, 
            indicators, 
            "Integration Test Chart"
        )
        
        assert isinstance(chart_html, str)
        assert len(chart_html) > 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])