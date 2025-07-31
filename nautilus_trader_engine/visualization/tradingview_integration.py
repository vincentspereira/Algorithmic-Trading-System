"""
TradingView Integration for Advanced Data Visualization
Interactive charting with TradingView widgets and custom indicators
"""
import logging
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid

try:
    from flask import Flask, render_template, jsonify, request
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False


class TradingViewWidgetType(Enum):
    """TradingView widget types"""
    ADVANCED_CHART = "advanced_chart"
    MINI_CHART = "mini_chart"
    SYMBOL_OVERVIEW = "symbol_overview"
    MARKET_OVERVIEW = "market_overview"
    SCREENER = "screener"
    WATCHLIST = "watchlist"
    ECONOMIC_CALENDAR = "economic_calendar"
    TECHNICAL_ANALYSIS = "technical_analysis"


@dataclass
class TradingViewConfig:
    """TradingView widget configuration"""
    widget_id: str
    widget_type: TradingViewWidgetType
    symbol: str
    interval: str = "1D"
    theme: str = "dark"
    style: str = "1"  # 1=Candles, 2=Hollow Candles, 3=Line, etc.
    locale: str = "en"
    timezone: str = "Etc/UTC"
    toolbar_bg: str = "#f1f3f6"
    enable_publishing: bool = False
    allow_symbol_change: bool = True
    container_id: str = ""
    width: Union[int, str] = "100%"
    height: Union[int, str] = 400
    studies: List[str] = field(default_factory=list)
    custom_css_url: str = ""


class TradingViewIntegration:
    """TradingView integration manager"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.widgets: Dict[str, TradingViewConfig] = {}
        self.custom_indicators: Dict[str, Dict[str, Any]] = {}
    
    def create_advanced_chart_widget(self, symbol: str, container_id: str, 
                                   config: Optional[Dict[str, Any]] = None) -> str:
        """Create TradingView advanced chart widget"""
        widget_config = config or {}
        
        widget_html = f"""
        <!-- TradingView Widget BEGIN -->
        <div class="tradingview-widget-container" id="{container_id}">
            <div id="{container_id}_chart" style="height: {widget_config.get('height', 400)}px;"></div>
            <div class="tradingview-widget-copyright">
                <a href="https://www.tradingview.com/symbols/{symbol}/" rel="noopener" target="_blank">
                    <span class="blue-text">{symbol} Chart</span>
                </a> by TradingView
            </div>
        </div>
        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        <script type="text/javascript">
        new TradingView.widget({{
            "width": "{widget_config.get('width', '100%')}",
            "height": {widget_config.get('height', 400)},
            "symbol": "{symbol}",
            "interval": "{widget_config.get('interval', '1D')}",
            "timezone": "{widget_config.get('timezone', 'Etc/UTC')}",
            "theme": "{widget_config.get('theme', 'dark')}",
            "style": "{widget_config.get('style', '1')}",
            "locale": "{widget_config.get('locale', 'en')}",
            "toolbar_bg": "{widget_config.get('toolbar_bg', '#f1f3f6')}",
            "enable_publishing": {str(widget_config.get('enable_publishing', False)).lower()},
            "allow_symbol_change": {str(widget_config.get('allow_symbol_change', True)).lower()},
            "container_id": "{container_id}_chart",
            "studies": {json.dumps(widget_config.get('studies', []))},
            "show_popup_button": true,
            "popup_width": "1000",
            "popup_height": "650",
            "no_referral_id": true
        }});
        </script>
        <!-- TradingView Widget END -->
        """
        
        return widget_html
    
    def create_mini_chart_widget(self, symbol: str, container_id: str,
                               config: Optional[Dict[str, Any]] = None) -> str:
        """Create TradingView mini chart widget"""
        widget_config = config or {}
        
        widget_html = f"""
        <!-- TradingView Widget BEGIN -->
        <div class="tradingview-widget-container" id="{container_id}">
            <div class="tradingview-widget-container__widget" id="{container_id}_chart"></div>
            <div class="tradingview-widget-copyright">
                <a href="https://www.tradingview.com/symbols/{symbol}/" rel="noopener" target="_blank">
                    <span class="blue-text">{symbol}</span>
                </a> by TradingView
            </div>
        </div>
        <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-mini-symbol-overview.js" async>
        {{
            "symbol": "{symbol}",
            "width": "{widget_config.get('width', '100%')}",
            "height": "{widget_config.get('height', 400)}",
            "locale": "{widget_config.get('locale', 'en')}",
            "dateRange": "{widget_config.get('dateRange', '12M')}",
            "colorTheme": "{widget_config.get('theme', 'dark')}",
            "trendLineColor": "{widget_config.get('trendLineColor', 'rgba(41, 98, 255, 1)')}",
            "underLineColor": "{widget_config.get('underLineColor', 'rgba(41, 98, 255, 0.3)')}",
            "underLineBottomColor": "{widget_config.get('underLineBottomColor', 'rgba(41, 98, 255, 0)')}",
            "isTransparent": {str(widget_config.get('isTransparent', False)).lower()},
            "autosize": {str(widget_config.get('autosize', True)).lower()},
            "largeChartUrl": ""
        }}
        </script>
        <!-- TradingView Widget END -->
        """
        
        return widget_html
    
    def create_symbol_overview_widget(self, symbols: List[str], container_id: str,
                                    config: Optional[Dict[str, Any]] = None) -> str:
        """Create TradingView symbol overview widget"""
        widget_config = config or {}
        
        widget_html = f"""
        <!-- TradingView Widget BEGIN -->
        <div class="tradingview-widget-container" id="{container_id}">
            <div class="tradingview-widget-container__widget" id="{container_id}_overview"></div>
            <div class="tradingview-widget-copyright">
                <a href="https://www.tradingview.com/" rel="noopener" target="_blank">
                    <span class="blue-text">Track all markets on TradingView</span>
                </a>
            </div>
        </div>
        <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-symbol-overview.js" async>
        {{
            "symbols": {json.dumps([[symbol, symbol.split(':')[-1]] for symbol in symbols])},
            "chartOnly": {str(widget_config.get('chartOnly', False)).lower()},
            "width": "{widget_config.get('width', '100%')}",
            "height": "{widget_config.get('height', 400)}",
            "locale": "{widget_config.get('locale', 'en')}",
            "colorTheme": "{widget_config.get('theme', 'dark')}",
            "autosize": {str(widget_config.get('autosize', True)).lower()},
            "showVolume": {str(widget_config.get('showVolume', False)).lower()},
            "showMA": {str(widget_config.get('showMA', False)).lower()},
            "hideDateRanges": {str(widget_config.get('hideDateRanges', False)).lower()},
            "hideMarketStatus": {str(widget_config.get('hideMarketStatus', False)).lower()},
            "hideSymbolLogo": {str(widget_config.get('hideSymbolLogo', False)).lower()},
            "scalePosition": "{widget_config.get('scalePosition', 'right')}",
            "scaleMode": "{widget_config.get('scaleMode', 'Normal')}",
            "fontFamily": "{widget_config.get('fontFamily', '-apple-system, BlinkMacSystemFont, Trebuchet MS, Roboto, Ubuntu, sans-serif')}",
            "fontSize": "{widget_config.get('fontSize', '10')}",
            "noTimeScale": {str(widget_config.get('noTimeScale', False)).lower()},
            "valuesTracking": "{widget_config.get('valuesTracking', '1')}",
            "changeMode": "{widget_config.get('changeMode', 'price-and-percent')}",
            "chartType": "{widget_config.get('chartType', 'area')}",
            "maLineColor": "{widget_config.get('maLineColor', '#2962FF')}",
            "maLineWidth": {widget_config.get('maLineWidth', 1)},
            "maLength": {widget_config.get('maLength', 9)},
            "lineWidth": {widget_config.get('lineWidth', 2)},
            "lineType": {widget_config.get('lineType', 0)},
            "dateRanges": {json.dumps(widget_config.get('dateRanges', ['1d', '1m', '3m', '12m', '60m']))}
        }}
        </script>
        <!-- TradingView Widget END -->
        """
        
        return widget_html
    
    def create_market_overview_widget(self, container_id: str,
                                    config: Optional[Dict[str, Any]] = None) -> str:
        """Create TradingView market overview widget"""
        widget_config = config or {}
        
        tabs = widget_config.get('tabs', [
            {"title": "Indices", "symbols": [
                {"s": "FOREXCOM:SPXUSD", "d": "S&P 500"},
                {"s": "FOREXCOM:NSXUSD", "d": "US 100"},
                {"s": "FOREXCOM:DJI", "d": "Dow 30"},
                {"s": "INDEX:NKY", "d": "Nikkei 225"},
                {"s": "INDEX:DEU40", "d": "DAX Index"},
                {"s": "FOREXCOM:UKXGBP", "d": "UK 100"}
            ]},
            {"title": "Futures", "symbols": [
                {"s": "CME_MINI:ES1!", "d": "S&P 500"},
                {"s": "CME:6E1!", "d": "Euro"},
                {"s": "COMEX:GC1!", "d": "Gold"},
                {"s": "NYMEX:CL1!", "d": "Crude Oil"},
                {"s": "NYMEX:NG1!", "d": "Natural Gas"},
                {"s": "CBOT:ZC1!", "d": "Corn"}
            ]},
            {"title": "Bonds", "symbols": [
                {"s": "CME:GE1!", "d": "Eurodollar"},
                {"s": "CBOT:ZB1!", "d": "T-Bond"},
                {"s": "CBOT:UB1!", "d": "Ultra T-Bond"},
                {"s": "EUREX:FGBL1!", "d": "Euro Bund"},
                {"s": "EUREX:FBTP1!", "d": "Euro BTP"},
                {"s": "EUREX:FGBM1!", "d": "Euro BOBL"}
            ]},
            {"title": "Forex", "symbols": [
                {"s": "FX:EURUSD", "d": "EUR/USD"},
                {"s": "FX:GBPUSD", "d": "GBP/USD"},
                {"s": "FX:USDJPY", "d": "USD/JPY"},
                {"s": "FX:USDCHF", "d": "USD/CHF"},
                {"s": "FX:AUDUSD", "d": "AUD/USD"},
                {"s": "FX:USDCAD", "d": "USD/CAD"}
            ]}
        ])
        
        widget_html = f"""
        <!-- TradingView Widget BEGIN -->
        <div class="tradingview-widget-container" id="{container_id}">
            <div class="tradingview-widget-container__widget" id="{container_id}_overview"></div>
            <div class="tradingview-widget-copyright">
                <a href="https://www.tradingview.com/markets/" rel="noopener" target="_blank">
                    <span class="blue-text">Financial Markets</span>
                </a> by TradingView
            </div>
        </div>
        <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-market-overview.js" async>
        {{
            "colorTheme": "{widget_config.get('theme', 'dark')}",
            "dateRange": "{widget_config.get('dateRange', '12M')}",
            "showChart": {str(widget_config.get('showChart', True)).lower()},
            "locale": "{widget_config.get('locale', 'en')}",
            "width": "{widget_config.get('width', '100%')}",
            "height": "{widget_config.get('height', 400)}",
            "largeChartUrl": "",
            "isTransparent": {str(widget_config.get('isTransparent', False)).lower()},
            "showSymbolLogo": {str(widget_config.get('showSymbolLogo', True)).lower()},
            "showFloatingTooltip": {str(widget_config.get('showFloatingTooltip', False)).lower()},
            "plotLineColorGrowing": "{widget_config.get('plotLineColorGrowing', 'rgba(41, 98, 255, 1)')}",
            "plotLineColorFalling": "{widget_config.get('plotLineColorFalling', 'rgba(41, 98, 255, 1)')}",
            "gridLineColor": "{widget_config.get('gridLineColor', 'rgba(240, 243, 250, 0)')}",
            "scaleFontColor": "{widget_config.get('scaleFontColor', 'rgba(120, 123, 134, 1)')}",
            "belowLineFillColorGrowing": "{widget_config.get('belowLineFillColorGrowing', 'rgba(41, 98, 255, 0.12)')}",
            "belowLineFillColorFalling": "{widget_config.get('belowLineFillColorFalling', 'rgba(41, 98, 255, 0.12)')}",
            "belowLineFillColorGrowingBottom": "{widget_config.get('belowLineFillColorGrowingBottom', 'rgba(41, 98, 255, 0)')}",
            "belowLineFillColorFallingBottom": "{widget_config.get('belowLineFillColorFallingBottom', 'rgba(41, 98, 255, 0)')}",
            "symbolActiveColor": "{widget_config.get('symbolActiveColor', 'rgba(41, 98, 255, 0.12)')}",
            "tabs": {json.dumps(tabs)}
        }}
        </script>
        <!-- TradingView Widget END -->
        """
        
        return widget_html
    
    def create_screener_widget(self, container_id: str,
                             config: Optional[Dict[str, Any]] = None) -> str:
        """Create TradingView screener widget"""
        widget_config = config or {}
        
        widget_html = f"""
        <!-- TradingView Widget BEGIN -->
        <div class="tradingview-widget-container" id="{container_id}">
            <div class="tradingview-widget-container__widget" id="{container_id}_screener"></div>
            <div class="tradingview-widget-copyright">
                <a href="https://www.tradingview.com/screener/" rel="noopener" target="_blank">
                    <span class="blue-text">Stock Screener</span>
                </a> by TradingView
            </div>
        </div>
        <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-screener.js" async>
        {{
            "width": "{widget_config.get('width', '100%')}",
            "height": "{widget_config.get('height', 400)}",
            "defaultColumn": "{widget_config.get('defaultColumn', 'overview')}",
            "defaultScreen": "{widget_config.get('defaultScreen', 'general')}",
            "market": "{widget_config.get('market', 'us')}",
            "showToolbar": {str(widget_config.get('showToolbar', True)).lower()},
            "colorTheme": "{widget_config.get('theme', 'dark')}",
            "locale": "{widget_config.get('locale', 'en')}",
            "isTransparent": {str(widget_config.get('isTransparent', False)).lower()}
        }}
        </script>
        <!-- TradingView Widget END -->
        """
        
        return widget_html
    
    def create_economic_calendar_widget(self, container_id: str,
                                      config: Optional[Dict[str, Any]] = None) -> str:
        """Create TradingView economic calendar widget"""
        widget_config = config or {}
        
        widget_html = f"""
        <!-- TradingView Widget BEGIN -->
        <div class="tradingview-widget-container" id="{container_id}">
            <div class="tradingview-widget-container__widget" id="{container_id}_calendar"></div>
            <div class="tradingview-widget-copyright">
                <a href="https://www.tradingview.com/economic-calendar/" rel="noopener" target="_blank">
                    <span class="blue-text">Economic Calendar</span>
                </a> by TradingView
            </div>
        </div>
        <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>
        {{
            "colorTheme": "{widget_config.get('theme', 'dark')}",
            "isTransparent": {str(widget_config.get('isTransparent', False)).lower()},
            "width": "{widget_config.get('width', '100%')}",
            "height": "{widget_config.get('height', 400)}",
            "locale": "{widget_config.get('locale', 'en')}",
            "importanceFilter": "{widget_config.get('importanceFilter', '-1,0,1')}",
            "countryFilter": "{widget_config.get('countryFilter', 'ar,au,br,ca,cn,fr,de,in,id,it,jp,kr,mx,ru,sa,za,tr,gb,us,eu')}"
        }}
        </script>
        <!-- TradingView Widget END -->
        """
        
        return widget_html
    
    def create_technical_analysis_widget(self, symbol: str, container_id: str,
                                       config: Optional[Dict[str, Any]] = None) -> str:
        """Create TradingView technical analysis widget"""
        widget_config = config or {}
        
        widget_html = f"""
        <!-- TradingView Widget BEGIN -->
        <div class="tradingview-widget-container" id="{container_id}">
            <div class="tradingview-widget-container__widget" id="{container_id}_analysis"></div>
            <div class="tradingview-widget-copyright">
                <a href="https://www.tradingview.com/symbols/{symbol}/technicals/" rel="noopener" target="_blank">
                    <span class="blue-text">Technical Analysis for {symbol}</span>
                </a> by TradingView
            </div>
        </div>
        <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-technical-analysis.js" async>
        {{
            "interval": "{widget_config.get('interval', '1m')}",
            "width": "{widget_config.get('width', '100%')}",
            "isTransparent": {str(widget_config.get('isTransparent', False)).lower()},
            "height": "{widget_config.get('height', 400)}",
            "symbol": "{symbol}",
            "showIntervalTabs": {str(widget_config.get('showIntervalTabs', True)).lower()},
            "locale": "{widget_config.get('locale', 'en')}",
            "colorTheme": "{widget_config.get('theme', 'dark')}"
        }}
        </script>
        <!-- TradingView Widget END -->
        """
        
        return widget_html
    
    def create_custom_study(self, name: str, script: str) -> Dict[str, Any]:
        """Create custom Pine Script study"""
        study = {
            "id": str(uuid.uuid4()),
            "name": name,
            "script": script,
            "created_at": datetime.now().isoformat()
        }
        
        self.custom_indicators[study["id"]] = study
        return study
    
    def get_pine_script_template(self, indicator_type: str) -> str:
        """Get Pine Script template for common indicators"""
        templates = {
            "custom_sma": '''
//@version=5
indicator("Custom SMA", shorttitle="CSMA", overlay=true)

length = input.int(20, title="Length", minval=1)
source = input(close, title="Source")

sma_value = ta.sma(source, length)
plot(sma_value, color=color.blue, linewidth=2, title="SMA")
            ''',
            
            "custom_rsi": '''
//@version=5
indicator("Custom RSI", shorttitle="CRSI")

length = input.int(14, title="RSI Length", minval=1)
source = input(close, title="Source")

rsi_value = ta.rsi(source, length)
plot(rsi_value, color=color.purple, linewidth=2, title="RSI")
hline(70, "Overbought", color=color.red, linestyle=hline.style_dashed)
hline(30, "Oversold", color=color.green, linestyle=hline.style_dashed)
hline(50, "Midline", color=color.gray, linestyle=hline.style_dotted)
            ''',
            
            "volume_profile": '''
//@version=5
indicator("Volume Profile", shorttitle="VP")

length = input.int(100, title="Length", minval=1)
resolution = input.int(24, title="Resolution", minval=1)

// Calculate volume profile
var float[] price_levels = array.new_float()
var float[] volume_levels = array.new_float()

if barstate.islast
    highest_price = ta.highest(high, length)
    lowest_price = ta.lowest(low, length)
    price_range = highest_price - lowest_price
    level_size = price_range / resolution
    
    for i = 0 to resolution - 1
        level_price = lowest_price + (i * level_size)
        level_volume = 0.0
        
        for j = 0 to length - 1
            if high[j] >= level_price and low[j] <= level_price
                level_volume += volume[j]
        
        array.push(price_levels, level_price)
        array.push(volume_levels, level_volume)

// Plot volume profile (simplified visualization)
plot(volume, color=color.blue, style=plot.style_histogram, title="Volume")
            '''
        }
        
        return templates.get(indicator_type, "")


class RealTimeOrderBookVisualizer:
    """Real-time order book visualization"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.order_book_data: Dict[str, Dict[str, Any]] = {}
        self.subscribers: List[str] = []
    
    def update_order_book(self, symbol: str, bids: List[Dict[str, float]], 
                         asks: List[Dict[str, float]]):
        """Update order book data"""
        self.order_book_data[symbol] = {
            'symbol': symbol,
            'bids': bids,
            'asks': asks,
            'timestamp': datetime.now().isoformat(),
            'spread': asks[0]['price'] - bids[0]['price'] if bids and asks else 0
        }
    
    def get_order_book_html(self, symbol: str, container_id: str) -> str:
        """Generate HTML for order book visualization"""
        html = f"""
        <div id="{container_id}" class="order-book-container">
            <div class="order-book-header">
                <h3>Order Book - {symbol}</h3>
                <div class="spread-info">
                    <span id="spread-{symbol}">Spread: $0.00</span>
                </div>
            </div>
            
            <div class="order-book-content">
                <div class="asks-section">
                    <div class="section-header">Asks</div>
                    <div class="order-book-levels" id="asks-{symbol}">
                        <!-- Ask levels will be populated here -->
                    </div>
                </div>
                
                <div class="spread-line">
                    <div class="current-price" id="price-{symbol}">$0.00</div>
                </div>
                
                <div class="bids-section">
                    <div class="section-header">Bids</div>
                    <div class="order-book-levels" id="bids-{symbol}">
                        <!-- Bid levels will be populated here -->
                    </div>
                </div>
            </div>
        </div>
        
        <style>
        .order-book-container {{
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 15px;
            font-family: 'Courier New', monospace;
            color: #fff;
        }}
        
        .order-book-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            border-bottom: 1px solid #333;
            padding-bottom: 10px;
        }}
        
        .order-book-header h3 {{
            margin: 0;
            color: #4a90e2;
        }}
        
        .spread-info {{
            font-size: 14px;
            color: #ffa500;
        }}
        
        .order-book-content {{
            display: flex;
            flex-direction: column;
            height: 400px;
        }}
        
        .asks-section, .bids-section {{
            flex: 1;
            overflow-y: auto;
        }}
        
        .section-header {{
            font-weight: bold;
            padding: 5px 0;
            text-align: center;
            border-bottom: 1px solid #333;
            margin-bottom: 5px;
        }}
        
        .asks-section .section-header {{
            color: #ff4444;
        }}
        
        .bids-section .section-header {{
            color: #44ff44;
        }}
        
        .order-book-levels {{
            display: flex;
            flex-direction: column;
        }}
        
        .order-level {{
            display: flex;
            justify-content: space-between;
            padding: 2px 5px;
            font-size: 12px;
            position: relative;
        }}
        
        .order-level.ask {{
            background: linear-gradient(to left, rgba(255, 68, 68, 0.1) 0%, rgba(255, 68, 68, 0.1) var(--volume-percent), transparent var(--volume-percent));
        }}
        
        .order-level.bid {{
            background: linear-gradient(to left, rgba(68, 255, 68, 0.1) 0%, rgba(68, 255, 68, 0.1) var(--volume-percent), transparent var(--volume-percent));
        }}
        
        .price {{
            font-weight: bold;
        }}
        
        .ask .price {{
            color: #ff4444;
        }}
        
        .bid .price {{
            color: #44ff44;
        }}
        
        .quantity {{
            color: #ccc;
        }}
        
        .spread-line {{
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 10px 0;
            border-top: 1px solid #333;
            border-bottom: 1px solid #333;
            margin: 5px 0;
        }}
        
        .current-price {{
            font-size: 16px;
            font-weight: bold;
            color: #ffa500;
        }}
        </style>
        
        <script>
        function updateOrderBook_{symbol.replace('.', '_')}(data) {{
            const asksContainer = document.getElementById('asks-{symbol}');
            const bidsContainer = document.getElementById('bids-{symbol}');
            const spreadElement = document.getElementById('spread-{symbol}');
            const priceElement = document.getElementById('price-{symbol}');
            
            // Update spread
            if (data.spread !== undefined) {{
                spreadElement.textContent = `Spread: $` + data.spread.toFixed(2);
            }}
            
            // Update current price (mid price)
            if (data.bids && data.bids.length > 0 && data.asks && data.asks.length > 0) {{
                const midPrice = (data.bids[0].price + data.asks[0].price) / 2;
                priceElement.textContent = `$` + midPrice.toFixed(2);
            }}
            
            // Update asks
            if (data.asks) {{
                const maxVolume = Math.max(...data.asks.map(level => level.quantity));
                asksContainer.innerHTML = data.asks.slice(0, 10).reverse().map(level => {{
                    const volumePercent = (level.quantity / maxVolume) * 100;
                    return `
                        <div class="order-level ask" style="--volume-percent: ${{volumePercent}}%">
                            <span class="price">$$${{level.price.toFixed(2)}}</span>
                            <span class="quantity">${{level.quantity.toLocaleString()}}</span>
                        </div>
                    `;
                }}).join('');
            }}
            
            // Update bids
            if (data.bids) {{
                const maxVolume = Math.max(...data.bids.map(level => level.quantity));
                bidsContainer.innerHTML = data.bids.slice(0, 10).map(level => {{
                    const volumePercent = (level.quantity / maxVolume) * 100;
                    return `
                        <div class="order-level bid" style="--volume-percent: ${{volumePercent}}%">
                            <span class="price">$$${{level.price.toFixed(2)}}</span>
                            <span class="quantity">${{level.quantity.toLocaleString()}}</span>
                        </div>
                    `;
                }}).join('');
            }}
        }}
        
        // Sample data update (replace with real WebSocket connection)
        setInterval(() => {{
            const sampleData = {{
                symbol: '{symbol}',
                bids: Array.from({{length: 15}}, (_, i) => ({{
                    price: 150.00 - (i * 0.01),
                    quantity: Math.floor(Math.random() * 5000) + 100
                }})),
                asks: Array.from({{length: 15}}, (_, i) => ({{
                    price: 150.01 + (i * 0.01),
                    quantity: Math.floor(Math.random() * 5000) + 100
                }})),
                spread: 0.01
            }};
            updateOrderBook_{symbol.replace('.', '_')}(sampleData);
        }}, 1000);
        </script>
        """
        
        return html


class PortfolioAnalyticsCharts:
    """Portfolio performance analytics charts"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def create_performance_chart(self, container_id: str, data: Dict[str, Any]) -> str:
        """Create portfolio performance chart"""
        html = f"""
        <div id="{container_id}" class="portfolio-chart-container">
            <canvas id="{container_id}_canvas"></canvas>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script>
        const ctx_{container_id} = document.getElementById('{container_id}_canvas').getContext('2d');
        const chart_{container_id} = new Chart(ctx_{container_id}, {{
            type: 'line',
            data: {{
                labels: {json.dumps(data.get('dates', []))},
                datasets: [{{
                    label: 'Portfolio Value',
                    data: {json.dumps(data.get('values', []))},
                    borderColor: '#4a90e2',
                    backgroundColor: 'rgba(74, 144, 226, 0.1)',
                    borderWidth: 2,
                    fill: true
                }}, {{
                    label: 'Benchmark',
                    data: {json.dumps(data.get('benchmark', []))},
                    borderColor: '#ff6b6b',
                    backgroundColor: 'rgba(255, 107, 107, 0.1)',
                    borderWidth: 2,
                    fill: false
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Portfolio Performance'
                    }},
                    legend: {{
                        display: true,
                        position: 'top'
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: false,
                        ticks: {{
                            callback: function(value) {{
                                return '$' + value.toLocaleString();
                            }}
                        }}
                    }}
                }}
            }}
        }});
        </script>
        """
        
        return html
    
    def create_allocation_chart(self, container_id: str, data: Dict[str, Any]) -> str:
        """Create portfolio allocation pie chart"""
        html = f"""
        <div id="{container_id}" class="allocation-chart-container">
            <canvas id="{container_id}_canvas"></canvas>
        </div>
        
        <script>
        const ctx_alloc_{container_id} = document.getElementById('{container_id}_canvas').getContext('2d');
        const chart_alloc_{container_id} = new Chart(ctx_alloc_{container_id}, {{
            type: 'doughnut',
            data: {{
                labels: {json.dumps(data.get('labels', []))},
                datasets: [{{
                    data: {json.dumps(data.get('values', []))},
                    backgroundColor: [
                        '#4a90e2', '#ff6b6b', '#4ecdc4', '#45b7d1',
                        '#96ceb4', '#feca57', '#ff9ff3', '#54a0ff'
                    ],
                    borderWidth: 2,
                    borderColor: '#1a1a1a'
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Portfolio Allocation'
                    }},
                    legend: {{
                        display: true,
                        position: 'right'
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                const label = context.label || '';
                                const value = context.parsed;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((value / total) * 100).toFixed(1);
                                return label + ': $' + value.toLocaleString() + ' (' + percentage + '%)';
                            }}
                        }}
                    }}
                }}
            }}
        }});
        </script>
        """
        
        return html


# Example usage and integration
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Create TradingView integration
    tv_integration = TradingViewIntegration()
    
    # Create advanced chart widget
    chart_html = tv_integration.create_advanced_chart_widget(
        symbol="NASDAQ:AAPL",
        container_id="aapl_chart",
        config={
            'height': 500,
            'theme': 'dark',
            'studies': ['RSI@tv-basicstudies', 'MACD@tv-basicstudies']
        }
    )
    
    print("TradingView chart widget created")
    print(f"Chart HTML length: {len(chart_html)}")
    
    # Create order book visualizer
    order_book = RealTimeOrderBookVisualizer()
    order_book_html = order_book.get_order_book_html("AAPL", "aapl_orderbook")
    
    print("Order book visualizer created")
    print(f"Order book HTML length: {len(order_book_html)}")
    
    # Create portfolio analytics
    portfolio_charts = PortfolioAnalyticsCharts()
    
    sample_data = {
        'dates': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05'],
        'values': [100000, 101500, 99800, 102300, 104100],
        'benchmark': [100000, 100800, 99500, 101200, 102000]
    }
    
    performance_chart = portfolio_charts.create_performance_chart("portfolio_perf", sample_data)
    
    print("Portfolio analytics charts created")
    print(f"Performance chart HTML length: {len(performance_chart)}")