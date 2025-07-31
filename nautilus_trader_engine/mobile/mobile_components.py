"""
Mobile Trading Components
Reusable mobile UI components and utilities for the trading application.
"""
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import json

class ComponentType(Enum):
    """Mobile component types"""
    CHART = "chart"
    ORDER_FORM = "order_form"
    POSITION_CARD = "position_card"
    WATCHLIST_ITEM = "watchlist_item"
    PRICE_TICKER = "price_ticker"
    ORDER_BOOK = "order_book"
    TRADE_HISTORY = "trade_history"
    ALERT_BANNER = "alert_banner"

class TouchAction(Enum):
    """Touch action types"""
    BUY = "buy"
    SELL = "sell"
    ADD_TO_WATCHLIST = "add_to_watchlist"
    REMOVE_FROM_WATCHLIST = "remove_from_watchlist"
    VIEW_DETAILS = "view_details"
    CANCEL_ORDER = "cancel_order"
    MODIFY_ORDER = "modify_order"

@dataclass
class MobileComponent:
    """Base mobile component"""
    component_id: str
    component_type: ComponentType
    title: str
    data: Dict[str, Any] = field(default_factory=dict)
    style: Dict[str, Any] = field(default_factory=dict)
    touch_actions: List[TouchAction] = field(default_factory=list)
    is_visible: bool = True
    refresh_interval: int = 30  # seconds

@dataclass
class ResponsiveLayout:
    """Responsive layout configuration"""
    breakpoints: Dict[str, int] = field(default_factory=lambda: {
        'xs': 0,      # Extra small devices
        'sm': 576,    # Small devices
        'md': 768,    # Medium devices
        'lg': 992,    # Large devices
        'xl': 1200    # Extra large devices
    })
    grid_columns: Dict[str, int] = field(default_factory=lambda: {
        'xs': 1,
        'sm': 2,
        'md': 3,
        'lg': 4,
        'xl': 6
    })

class MobileComponentRenderer:
    """Mobile component renderer"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.layout = ResponsiveLayout()
    
    def render_component(self, component: MobileComponent) -> str:
        """Render mobile component to HTML"""
        try:
            if component.component_type == ComponentType.CHART:
                return self._render_chart_component(component)
            elif component.component_type == ComponentType.ORDER_FORM:
                return self._render_order_form_component(component)
            elif component.component_type == ComponentType.POSITION_CARD:
                return self._render_position_card_component(component)
            elif component.component_type == ComponentType.WATCHLIST_ITEM:
                return self._render_watchlist_item_component(component)
            elif component.component_type == ComponentType.PRICE_TICKER:
                return self._render_price_ticker_component(component)
            elif component.component_type == ComponentType.ORDER_BOOK:
                return self._render_order_book_component(component)
            elif component.component_type == ComponentType.TRADE_HISTORY:
                return self._render_trade_history_component(component)
            elif component.component_type == ComponentType.ALERT_BANNER:
                return self._render_alert_banner_component(component)
            else:
                return f"<div>Unknown component type: {component.component_type}</div>"
        
        except Exception as e:
            self.logger.error(f"Error rendering component: {e}")
            return f"<div>Error rendering component: {e}</div>"
    
    def _render_chart_component(self, component: MobileComponent) -> str:
        """Render chart component"""
        chart_data = component.data
        symbol = chart_data.get('symbol', 'N/A')
        price = chart_data.get('price', 0)
        change = chart_data.get('change', 0)
        change_class = 'positive' if change >= 0 else 'negative'
        
        return f'''
        <div class="mobile-chart-component" id="{component.component_id}" 
             data-symbol="{symbol}" data-refresh="{component.refresh_interval}">
            <div class="chart-header">
                <h3>{symbol}</h3>
                <div class="price-info">
                    <span class="price">${price:.2f}</span>
                    <span class="change {change_class}">{change:+.2f}</span>
                </div>
            </div>
            <div class="chart-container" style="height: 200px; background: #f8f9fa; border-radius: 5px; margin: 10px 0;">
                <canvas id="chart-{component.component_id}" width="100%" height="200"></canvas>
            </div>
            <div class="chart-actions">
                <button class="action-btn buy" onclick="quickTrade('{symbol}', 'buy')">Buy</button>
                <button class="action-btn sell" onclick="quickTrade('{symbol}', 'sell')">Sell</button>
            </div>
        </div>
        '''
    
    def _render_order_form_component(self, component: MobileComponent) -> str:
        """Render order form component"""
        form_data = component.data
        symbol = form_data.get('symbol', '')
        
        return f'''
        <div class="mobile-order-form" id="{component.component_id}">
            <div class="form-header">
                <h3>Place Order</h3>
            </div>
            <form id="order-form-{component.component_id}" onsubmit="submitOrder(event)">
                <div class="form-group">
                    <label>Symbol</label>
                    <input type="text" name="symbol" value="{symbol}" required>
                </div>
                <div class="form-group">
                    <label>Side</label>
                    <div class="button-group">
                        <button type="button" class="side-btn buy active" onclick="selectSide('buy', this)">Buy</button>
                        <button type="button" class="side-btn sell" onclick="selectSide('sell', this)">Sell</button>
                    </div>
                    <input type="hidden" name="side" value="buy">
                </div>
                <div class="form-group">
                    <label>Quantity</label>
                    <input type="number" name="quantity" min="1" required>
                </div>
                <div class="form-group">
                    <label>Order Type</label>
                    <select name="order_type" onchange="togglePriceField(this.value)">
                        <option value="market">Market</option>
                        <option value="limit">Limit</option>
                        <option value="stop">Stop</option>
                        <option value="stop_limit">Stop Limit</option>
                    </select>
                </div>
                <div class="form-group price-field" style="display: none;">
                    <label>Price</label>
                    <input type="number" name="price" step="0.01">
                </div>
                <div class="form-group stop-price-field" style="display: none;">
                    <label>Stop Price</label>
                    <input type="number" name="stop_price" step="0.01">
                </div>
                <button type="submit" class="submit-btn">Place Order</button>
            </form>
        </div>
        '''
    
    def _render_position_card_component(self, component: MobileComponent) -> str:
        """Render position card component"""
        position_data = component.data
        symbol = position_data.get('symbol', 'N/A')
        quantity = position_data.get('quantity', 0)
        avg_price = position_data.get('avg_price', 0)
        market_price = position_data.get('market_price', 0)
        unrealized_pnl = position_data.get('unrealized_pnl', 0)
        percentage_change = position_data.get('percentage_change', 0)
        
        pnl_class = 'positive' if unrealized_pnl >= 0 else 'negative'
        change_class = 'positive' if percentage_change >= 0 else 'negative'
        
        return f'''
        <div class="mobile-position-card" id="{component.component_id}" 
             data-symbol="{symbol}" ontouchstart="handleTouch(event)">
            <div class="position-header">
                <div class="symbol-info">
                    <h4>{symbol}</h4>
                    <span class="quantity">{quantity} shares</span>
                </div>
                <div class="price-info">
                    <span class="market-price">${market_price:.2f}</span>
                    <span class="avg-price">Avg: ${avg_price:.2f}</span>
                </div>
            </div>
            <div class="position-pnl">
                <div class="unrealized-pnl {pnl_class}">
                    ${unrealized_pnl:+.2f}
                </div>
                <div class="percentage-change {change_class}">
                    {percentage_change:+.2f}%
                </div>
            </div>
            <div class="position-actions" style="display: none;">
                <button class="action-btn" onclick="closePosition('{symbol}')">Close</button>
                <button class="action-btn" onclick="addToPosition('{symbol}')">Add</button>
                <button class="action-btn" onclick="viewDetails('{symbol}')">Details</button>
            </div>
        </div>
        '''
    
    def _render_watchlist_item_component(self, component: MobileComponent) -> str:
        """Render watchlist item component"""
        item_data = component.data
        symbol = item_data.get('symbol', 'N/A')
        last_price = item_data.get('last_price', 0)
        change = item_data.get('change', 0)
        change_percent = item_data.get('change_percent', 0)
        volume = item_data.get('volume', 0)
        is_favorite = item_data.get('is_favorite', False)
        
        change_class = 'positive' if change >= 0 else 'negative'
        favorite_icon = '★' if is_favorite else '☆'
        
        return f'''
        <div class="mobile-watchlist-item" id="{component.component_id}" 
             data-symbol="{symbol}" ontouchstart="handleWatchlistTouch(event)">
            <div class="watchlist-main">
                <div class="symbol-section">
                    <span class="favorite-icon" onclick="toggleFavorite('{symbol}')">{favorite_icon}</span>
                    <span class="symbol">{symbol}</span>
                </div>
                <div class="price-section">
                    <span class="last-price">${last_price:.2f}</span>
                    <span class="change {change_class}">
                        {change:+.2f} ({change_percent:+.2f}%)
                    </span>
                </div>
            </div>
            <div class="watchlist-details">
                <span class="volume">Vol: {volume:,}</span>
            </div>
            <div class="watchlist-actions" style="display: none;">
                <button class="action-btn buy" onclick="quickTrade('{symbol}', 'buy')">Buy</button>
                <button class="action-btn sell" onclick="quickTrade('{symbol}', 'sell')">Sell</button>
                <button class="action-btn remove" onclick="removeFromWatchlist('{symbol}')">Remove</button>
            </div>
        </div>
        '''
    
    def _render_price_ticker_component(self, component: MobileComponent) -> str:
        """Render price ticker component"""
        ticker_data = component.data
        symbols = ticker_data.get('symbols', [])
        
        ticker_items = []
        for symbol_data in symbols:
            symbol = symbol_data.get('symbol', 'N/A')
            price = symbol_data.get('price', 0)
            change = symbol_data.get('change', 0)
            change_class = 'positive' if change >= 0 else 'negative'
            
            ticker_items.append(f'''
                <div class="ticker-item {change_class}">
                    <span class="ticker-symbol">{symbol}</span>
                    <span class="ticker-price">${price:.2f}</span>
                    <span class="ticker-change">{change:+.2f}</span>
                </div>
            ''')
        
        return f'''
        <div class="mobile-price-ticker" id="{component.component_id}">
            <div class="ticker-container">
                <div class="ticker-scroll">
                    {''.join(ticker_items)}
                </div>
            </div>
        </div>
        '''
    
    def _render_order_book_component(self, component: MobileComponent) -> str:
        """Render order book component"""
        book_data = component.data
        symbol = book_data.get('symbol', 'N/A')
        bids = book_data.get('bids', [])
        asks = book_data.get('asks', [])
        
        bid_rows = []
        for bid in bids[:5]:  # Top 5 bids
            price, size = bid
            bid_rows.append(f'''
                <div class="order-book-row bid">
                    <span class="size">{size}</span>
                    <span class="price">${price:.2f}</span>
                </div>
            ''')
        
        ask_rows = []
        for ask in asks[:5]:  # Top 5 asks
            price, size = ask
            ask_rows.append(f'''
                <div class="order-book-row ask">
                    <span class="price">${price:.2f}</span>
                    <span class="size">{size}</span>
                </div>
            ''')
        
        return f'''
        <div class="mobile-order-book" id="{component.component_id}">
            <div class="order-book-header">
                <h4>{symbol} Order Book</h4>
            </div>
            <div class="order-book-content">
                <div class="asks-section">
                    <div class="section-header">
                        <span>Price</span>
                        <span>Size</span>
                    </div>
                    {''.join(reversed(ask_rows))}
                </div>
                <div class="spread-section">
                    <div class="spread">Spread: ${(asks[0][0] - bids[0][0]):.2f if asks and bids else 0:.2f}</div>
                </div>
                <div class="bids-section">
                    <div class="section-header">
                        <span>Size</span>
                        <span>Price</span>
                    </div>
                    {''.join(bid_rows)}
                </div>
            </div>
        </div>
        '''
    
    def _render_trade_history_component(self, component: MobileComponent) -> str:
        """Render trade history component"""
        history_data = component.data
        trades = history_data.get('trades', [])
        
        trade_rows = []
        for trade in trades[-10:]:  # Last 10 trades
            timestamp = trade.get('timestamp', '')
            symbol = trade.get('symbol', 'N/A')
            side = trade.get('side', 'N/A')
            quantity = trade.get('quantity', 0)
            price = trade.get('price', 0)
            pnl = trade.get('pnl', 0)
            
            side_class = 'buy' if side.lower() == 'buy' else 'sell'
            pnl_class = 'positive' if pnl >= 0 else 'negative'
            
            trade_rows.append(f'''
                <div class="trade-history-row">
                    <div class="trade-main">
                        <span class="trade-symbol">{symbol}</span>
                        <span class="trade-side {side_class}">{side.upper()}</span>
                        <span class="trade-quantity">{quantity}</span>
                        <span class="trade-price">${price:.2f}</span>
                    </div>
                    <div class="trade-details">
                        <span class="trade-time">{timestamp}</span>
                        <span class="trade-pnl {pnl_class}">${pnl:+.2f}</span>
                    </div>
                </div>
            ''')
        
        return f'''
        <div class="mobile-trade-history" id="{component.component_id}">
            <div class="trade-history-header">
                <h4>Recent Trades</h4>
            </div>
            <div class="trade-history-content">
                {''.join(trade_rows)}
            </div>
        </div>
        '''
    
    def _render_alert_banner_component(self, component: MobileComponent) -> str:
        """Render alert banner component"""
        alert_data = component.data
        message = alert_data.get('message', '')
        alert_type = alert_data.get('type', 'info')  # info, warning, error, success
        is_dismissible = alert_data.get('dismissible', True)
        
        dismiss_btn = '''
            <button class="alert-dismiss" onclick="dismissAlert(this)">×</button>
        ''' if is_dismissible else ''
        
        return f'''
        <div class="mobile-alert-banner alert-{alert_type}" id="{component.component_id}">
            <div class="alert-content">
                <span class="alert-message">{message}</span>
                {dismiss_btn}
            </div>
        </div>
        '''

class MobileStyleGenerator:
    """Generate mobile-optimized CSS styles"""
    
    @staticmethod
    def generate_mobile_styles() -> str:
        """Generate comprehensive mobile styles"""
        return '''
        /* Mobile Trading App Styles */
        
        /* Base Styles */
        * {
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
            background: #f8f9fa;
            font-size: 16px;
            line-height: 1.5;
        }
        
        /* Touch-friendly button styles */
        button, .btn {
            min-height: 44px;
            min-width: 44px;
            padding: 12px 16px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.2s ease;
            -webkit-appearance: none;
        }
        
        button:active, .btn:active {
            transform: scale(0.98);
        }
        
        /* Color scheme */
        .positive { color: #28a745; }
        .negative { color: #dc3545; }
        .buy { background: #28a745; color: white; }
        .sell { background: #dc3545; color: white; }
        .action-btn { background: #007bff; color: white; }
        
        /* Component Styles */
        .mobile-chart-component {
            background: white;
            border-radius: 12px;
            padding: 16px;
            margin: 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .chart-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        
        .price-info {
            text-align: right;
        }
        
        .price {
            font-size: 24px;
            font-weight: bold;
        }
        
        .change {
            font-size: 16px;
            margin-left: 8px;
        }
        
        .chart-actions {
            display: flex;
            gap: 12px;
            margin-top: 16px;
        }
        
        .chart-actions button {
            flex: 1;
        }
        
        /* Order Form Styles */
        .mobile-order-form {
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin: 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #333;
        }
        
        .form-group input,
        .form-group select {
            width: 100%;
            padding: 12px;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.2s ease;
        }
        
        .form-group input:focus,
        .form-group select:focus {
            outline: none;
            border-color: #007bff;
        }
        
        .button-group {
            display: flex;
            gap: 8px;
            margin-bottom: 8px;
        }
        
        .side-btn {
            flex: 1;
            background: #f8f9fa;
            color: #333;
            border: 2px solid #e9ecef;
        }
        
        .side-btn.active.buy {
            background: #28a745;
            color: white;
            border-color: #28a745;
        }
        
        .side-btn.active.sell {
            background: #dc3545;
            color: white;
            border-color: #dc3545;
        }
        
        .submit-btn {
            width: 100%;
            background: #007bff;
            color: white;
            font-size: 18px;
            font-weight: 600;
            padding: 16px;
        }
        
        /* Position Card Styles */
        .mobile-position-card {
            background: white;
            border-radius: 12px;
            padding: 16px;
            margin: 8px 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.2s ease;
        }
        
        .mobile-position-card:active {
            transform: scale(0.98);
        }
        
        .position-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 12px;
        }
        
        .symbol-info h4 {
            margin: 0 0 4px 0;
            font-size: 18px;
            font-weight: bold;
        }
        
        .quantity {
            font-size: 14px;
            color: #666;
        }
        
        .price-info {
            text-align: right;
        }
        
        .market-price {
            font-size: 18px;
            font-weight: bold;
        }
        
        .avg-price {
            font-size: 14px;
            color: #666;
            display: block;
        }
        
        .position-pnl {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-top: 12px;
            border-top: 1px solid #e9ecef;
        }
        
        .unrealized-pnl {
            font-size: 18px;
            font-weight: bold;
        }
        
        .percentage-change {
            font-size: 16px;
            font-weight: 600;
        }
        
        .position-actions {
            display: flex;
            gap: 8px;
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid #e9ecef;
        }
        
        .position-actions button {
            flex: 1;
            padding: 8px 12px;
            font-size: 14px;
        }
        
        /* Watchlist Item Styles */
        .mobile-watchlist-item {
            background: white;
            border-radius: 12px;
            padding: 16px;
            margin: 8px 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.2s ease;
        }
        
        .watchlist-main {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .symbol-section {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .favorite-icon {
            font-size: 20px;
            color: #ffc107;
            cursor: pointer;
        }
        
        .symbol {
            font-size: 18px;
            font-weight: bold;
        }
        
        .price-section {
            text-align: right;
        }
        
        .last-price {
            font-size: 18px;
            font-weight: bold;
            display: block;
        }
        
        .change {
            font-size: 14px;
            font-weight: 600;
        }
        
        .watchlist-details {
            margin-top: 8px;
            font-size: 14px;
            color: #666;
        }
        
        .watchlist-actions {
            display: flex;
            gap: 8px;
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid #e9ecef;
        }
        
        .watchlist-actions button {
            flex: 1;
            padding: 8px 12px;
            font-size: 14px;
        }
        
        /* Price Ticker Styles */
        .mobile-price-ticker {
            background: #333;
            color: white;
            padding: 8px 0;
            overflow: hidden;
            white-space: nowrap;
        }
        
        .ticker-container {
            width: 100%;
        }
        
        .ticker-scroll {
            display: inline-block;
            animation: scroll-left 30s linear infinite;
        }
        
        .ticker-item {
            display: inline-block;
            margin-right: 40px;
            font-size: 14px;
        }
        
        .ticker-symbol {
            font-weight: bold;
            margin-right: 8px;
        }
        
        .ticker-price {
            margin-right: 8px;
        }
        
        .ticker-change.positive {
            color: #28a745;
        }
        
        .ticker-change.negative {
            color: #dc3545;
        }
        
        @keyframes scroll-left {
            0% { transform: translate3d(100%, 0, 0); }
            100% { transform: translate3d(-100%, 0, 0); }
        }
        
        /* Order Book Styles */
        .mobile-order-book {
            background: white;
            border-radius: 12px;
            padding: 16px;
            margin: 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .order-book-header h4 {
            margin: 0 0 16px 0;
            text-align: center;
        }
        
        .section-header {
            display: flex;
            justify-content: space-between;
            font-weight: bold;
            font-size: 12px;
            color: #666;
            margin-bottom: 8px;
            padding: 0 8px;
        }
        
        .order-book-row {
            display: flex;
            justify-content: space-between;
            padding: 4px 8px;
            font-size: 14px;
            font-family: monospace;
        }
        
        .order-book-row.bid {
            background: rgba(40, 167, 69, 0.1);
        }
        
        .order-book-row.ask {
            background: rgba(220, 53, 69, 0.1);
        }
        
        .spread-section {
            text-align: center;
            padding: 12px 0;
            border-top: 1px solid #e9ecef;
            border-bottom: 1px solid #e9ecef;
            margin: 8px 0;
            font-weight: bold;
            color: #666;
        }
        
        /* Trade History Styles */
        .mobile-trade-history {
            background: white;
            border-radius: 12px;
            padding: 16px;
            margin: 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .trade-history-header h4 {
            margin: 0 0 16px 0;
        }
        
        .trade-history-row {
            padding: 12px 0;
            border-bottom: 1px solid #e9ecef;
        }
        
        .trade-history-row:last-child {
            border-bottom: none;
        }
        
        .trade-main {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 4px;
        }
        
        .trade-symbol {
            font-weight: bold;
        }
        
        .trade-side {
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }
        
        .trade-side.buy {
            background: #28a745;
            color: white;
        }
        
        .trade-side.sell {
            background: #dc3545;
            color: white;
        }
        
        .trade-details {
            display: flex;
            justify-content: space-between;
            font-size: 12px;
            color: #666;
        }
        
        .trade-pnl {
            font-weight: bold;
        }
        
        /* Alert Banner Styles */
        .mobile-alert-banner {
            padding: 12px 16px;
            margin: 8px 16px;
            border-radius: 8px;
            position: relative;
        }
        
        .alert-info {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }
        
        .alert-warning {
            background: #fff3cd;
            color: #856404;
            border: 1px solid #ffeaa7;
        }
        
        .alert-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .alert-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .alert-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .alert-dismiss {
            background: none;
            border: none;
            font-size: 20px;
            font-weight: bold;
            cursor: pointer;
            padding: 0;
            min-height: auto;
            min-width: auto;
            margin-left: 12px;
        }
        
        /* Responsive Design */
        @media (max-width: 576px) {
            .chart-actions {
                flex-direction: column;
            }
            
            .position-actions {
                flex-direction: column;
            }
            
            .watchlist-actions {
                flex-direction: column;
            }
            
            .button-group {
                flex-direction: column;
            }
        }
        
        @media (min-width: 768px) {
            .mobile-chart-component,
            .mobile-order-form,
            .mobile-order-book,
            .mobile-trade-history {
                margin: 16px auto;
                max-width: 600px;
            }
        }
        
        /* Dark mode support */
        @media (prefers-color-scheme: dark) {
            body {
                background: #1a1a1a;
                color: #ffffff;
            }
            
            .mobile-chart-component,
            .mobile-order-form,
            .mobile-position-card,
            .mobile-watchlist-item,
            .mobile-order-book,
            .mobile-trade-history {
                background: #2d2d2d;
                color: #ffffff;
            }
            
            .form-group input,
            .form-group select {
                background: #3d3d3d;
                color: #ffffff;
                border-color: #555;
            }
            
            .section-header,
            .quantity,
            .avg-price,
            .watchlist-details,
            .trade-details {
                color: #ccc;
            }
        }
        '''

def create_mobile_component(component_type: ComponentType, component_id: str, 
                          title: str, data: Dict[str, Any] = None) -> MobileComponent:
    """Create a mobile component"""
    return MobileComponent(
        component_id=component_id,
        component_type=component_type,
        title=title,
        data=data or {},
        touch_actions=[]
    )

if __name__ == "__main__":
    # Example usage
    renderer = MobileComponentRenderer()
    
    # Create a sample chart component
    chart_component = create_mobile_component(
        ComponentType.CHART,
        "chart-1",
        "AAPL Chart",
        {
            'symbol': 'AAPL',
            'price': 150.25,
            'change': 2.50
        }
    )
    
    print(renderer.render_component(chart_component))