"""
Mobile Trading Application
Provides mobile-optimized trading interface with responsive design and touch-friendly controls.
"""
import logging
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid

try:
    from flask import Flask, render_template, jsonify, request, session, redirect, url_for
    from flask_socketio import SocketIO, emit, join_room, leave_room
    from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

# Import offline capability
try:
    from .offline_capability import (
        OfflineCapabilityManager, OfflineActionType, create_offline_manager,
        handle_offline_order, cache_market_data, cache_portfolio_data
    )
    OFFLINE_AVAILABLE = True
except ImportError:
    OFFLINE_AVAILABLE = False

class MobileScreenSize(Enum):
    """Mobile screen size categories"""
    SMALL = "small"      # < 576px
    MEDIUM = "medium"    # 576px - 768px
    LARGE = "large"      # 768px - 992px
    XLARGE = "xlarge"    # > 992px

class TouchGesture(Enum):
    """Touch gesture types"""
    TAP = "tap"
    DOUBLE_TAP = "double_tap"
    LONG_PRESS = "long_press"
    SWIPE_LEFT = "swipe_left"
    SWIPE_RIGHT = "swipe_right"
    SWIPE_UP = "swipe_up"
    SWIPE_DOWN = "swipe_down"
    PINCH_ZOOM = "pinch_zoom"
    SPREAD_ZOOM = "spread_zoom"

@dataclass
class MobileUser:
    """Mobile user session"""
    id: str
    username: str
    device_id: str
    device_type: str
    screen_size: MobileScreenSize
    is_authenticated: bool = True
    last_activity: datetime = field(default_factory=datetime.now)
    preferences: Dict[str, Any] = field(default_factory=dict)
    
    def get_id(self):
        """Required for Flask-Login compatibility"""
        return self.id

@dataclass
class MobileOrder:
    """Mobile-optimized order structure"""
    order_id: str
    symbol: str
    side: str
    quantity: float
    order_type: str
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "DAY"
    status: str = "PENDING"
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class MobilePosition:
    """Mobile-optimized position structure"""
    symbol: str
    quantity: float
    avg_price: float
    market_price: float
    unrealized_pnl: float
    percentage_change: float
    side: str

@dataclass
class MobileWatchlistItem:
    """Mobile watchlist item"""
    symbol: str
    last_price: float
    change: float
    change_percent: float
    volume: int
    is_favorite: bool = False

class MobileTradingApp:
    """Mobile trading application"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 5001, enable_offline: bool = True):
        self.host = host
        self.port = port
        self.enable_offline = enable_offline
        self.logger = logging.getLogger(__name__)
        
        if not FLASK_AVAILABLE:
            raise ImportError("Flask and related packages are required for mobile app")
        
        self.app = Flask(__name__)
        self.app.secret_key = 'mobile_trading_secret_key'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # Login manager
        self.login_manager = LoginManager()
        self.login_manager.init_app(self.app)
        self.login_manager.login_view = 'mobile_login'
        
        # Offline capability manager
        self.offline_manager = None
        if self.enable_offline and OFFLINE_AVAILABLE:
            self.offline_manager = create_offline_manager()
            self.offline_manager.add_sync_callback(self._on_sync_event)
        
        # In-memory storage (replace with proper database in production)
        self.users: Dict[str, MobileUser] = {}
        self.orders: Dict[str, List[MobileOrder]] = {}
        self.positions: Dict[str, List[MobilePosition]] = {}
        self.watchlists: Dict[str, List[MobileWatchlistItem]] = {}
        
        self._setup_routes()
        self._setup_socket_events()
        self._initialize_sample_data()
    
    def _on_sync_event(self, event_type: str, data: Any):
        """Handle offline sync events"""
        self.logger.info(f"Sync event: {event_type}")
        
        # Broadcast sync events to all connected clients
        self.socketio.emit('sync_event', {
            'event_type': event_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        })
    
    @property
    def login_manager_user_loader(self):
        @self.login_manager.user_loader
        def load_user(user_id):
            return self.users.get(user_id)
        return load_user
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def mobile_home():
            """Mobile home page"""
            if current_user.is_authenticated:
                return redirect(url_for('mobile_dashboard'))
            return redirect(url_for('mobile_login'))
        
        @self.app.route('/login', methods=['GET', 'POST'])
        def mobile_login():
            """Mobile login page"""
            if request.method == 'POST':
                data = request.get_json() if request.is_json else request.form
                username = data.get('username')
                device_id = data.get('device_id', str(uuid.uuid4()))
                device_type = data.get('device_type', 'mobile')
                screen_size = MobileScreenSize(data.get('screen_size', 'medium'))
                
                # Simple authentication (replace with proper auth)
                if username:
                    user_id = str(uuid.uuid4())
                    user = MobileUser(
                        id=user_id,
                        username=username,
                        device_id=device_id,
                        device_type=device_type,
                        screen_size=screen_size
                    )
                    self.users[user_id] = user
                    login_user(user)
                    
                    if request.is_json:
                        return jsonify({'success': True, 'redirect': url_for('mobile_dashboard')})
                    return redirect(url_for('mobile_dashboard'))
                
                if request.is_json:
                    return jsonify({'success': False, 'error': 'Invalid credentials'})
                return render_template('mobile_login.html', error='Invalid credentials')
            
            return render_template('mobile_login.html')
        
        @self.app.route('/logout')
        @login_required
        def mobile_logout():
            """Mobile logout"""
            logout_user()
            return redirect(url_for('mobile_login'))
        
        @self.app.route('/dashboard')
        @login_required
        def mobile_dashboard():
            """Mobile dashboard"""
            user_positions = self.positions.get(current_user.id, [])
            user_orders = self.orders.get(current_user.id, [])
            user_watchlist = self.watchlists.get(current_user.id, [])
            
            return render_template('mobile_dashboard.html',
                                 positions=user_positions,
                                 orders=user_orders,
                                 watchlist=user_watchlist,
                                 user=current_user)
        
        @self.app.route('/trade')
        @login_required
        def mobile_trade():
            """Mobile trading interface"""
            return render_template('mobile_trade.html', user=current_user)
        
        @self.app.route('/portfolio')
        @login_required
        def mobile_portfolio():
            """Mobile portfolio view"""
            user_positions = self.positions.get(current_user.id, [])
            total_value = sum(pos.quantity * pos.market_price for pos in user_positions)
            total_pnl = sum(pos.unrealized_pnl for pos in user_positions)
            
            return render_template('mobile_portfolio.html',
                                 positions=user_positions,
                                 total_value=total_value,
                                 total_pnl=total_pnl,
                                 user=current_user)
        
        @self.app.route('/orders')
        @login_required
        def mobile_orders():
            """Mobile orders view"""
            user_orders = self.orders.get(current_user.id, [])
            return render_template('mobile_orders.html', orders=user_orders, user=current_user)
        
        @self.app.route('/watchlist')
        @login_required
        def mobile_watchlist():
            """Mobile watchlist view"""
            user_watchlist = self.watchlists.get(current_user.id, [])
            return render_template('mobile_watchlist.html', watchlist=user_watchlist, user=current_user)
        
        @self.app.route('/api/place_order', methods=['POST'])
        @login_required
        def api_place_order():
            """API endpoint to place order"""
            try:
                data = request.get_json()
                order = MobileOrder(
                    order_id=str(uuid.uuid4()),
                    symbol=data['symbol'],
                    side=data['side'],
                    quantity=float(data['quantity']),
                    order_type=data['order_type'],
                    price=float(data.get('price', 0)) if data.get('price') else None,
                    stop_price=float(data.get('stop_price', 0)) if data.get('stop_price') else None,
                    time_in_force=data.get('time_in_force', 'DAY')
                )
                
                # Check if offline mode is enabled and we're offline
                if (self.offline_manager and 
                    not self.offline_manager.is_online()):
                    
                    # Queue order for offline processing
                    asyncio.create_task(handle_offline_order(
                        self.offline_manager,
                        {
                            'order_id': order.order_id,
                            'symbol': order.symbol,
                            'side': order.side,
                            'quantity': order.quantity,
                            'order_type': order.order_type,
                            'price': order.price,
                            'stop_price': order.stop_price,
                            'time_in_force': order.time_in_force
                        },
                        current_user.id
                    ))
                    
                    order.status = 'QUEUED_OFFLINE'
                    
                    # Emit offline order update
                    self.socketio.emit('order_update', {
                        'order_id': order.order_id,
                        'status': 'QUEUED_OFFLINE',
                        'message': f'Order queued offline for {order.quantity} {order.symbol}'
                    }, room=current_user.id)
                    
                else:
                    # Normal online processing
                    order.status = 'PLACED'
                    
                    # Emit order update to user's room
                    self.socketio.emit('order_update', {
                        'order_id': order.order_id,
                        'status': 'PLACED',
                        'message': f'Order placed for {order.quantity} {order.symbol}'
                    }, room=current_user.id)
                
                # Store order locally
                if current_user.id not in self.orders:
                    self.orders[current_user.id] = []
                self.orders[current_user.id].append(order)
                
                return jsonify({'success': True, 'order_id': order.order_id})
            
            except Exception as e:
                self.logger.error(f"Error placing order: {e}")
                return jsonify({'success': False, 'error': str(e)}), 400
        
        @self.app.route('/api/cancel_order', methods=['POST'])
        @login_required
        def api_cancel_order():
            """API endpoint to cancel order"""
            try:
                data = request.get_json()
                order_id = data['order_id']
                
                user_orders = self.orders.get(current_user.id, [])
                for order in user_orders:
                    if order.order_id == order_id:
                        order.status = 'CANCELLED'
                        
                        self.socketio.emit('order_update', {
                            'order_id': order_id,
                            'status': 'CANCELLED',
                            'message': f'Order {order_id} cancelled'
                        }, room=current_user.id)
                        
                        return jsonify({'success': True})
                
                return jsonify({'success': False, 'error': 'Order not found'}), 404
            
            except Exception as e:
                self.logger.error(f"Error cancelling order: {e}")
                return jsonify({'success': False, 'error': str(e)}), 400
        
        @self.app.route('/api/add_to_watchlist', methods=['POST'])
        @login_required
        def api_add_to_watchlist():
            """API endpoint to add symbol to watchlist"""
            try:
                data = request.get_json()
                symbol = data['symbol']
                
                if current_user.id not in self.watchlists:
                    self.watchlists[current_user.id] = []
                
                # Check if already in watchlist
                user_watchlist = self.watchlists[current_user.id]
                if any(item.symbol == symbol for item in user_watchlist):
                    return jsonify({'success': False, 'error': 'Symbol already in watchlist'})
                
                # Create new watchlist item with sample data
                watchlist_item = MobileWatchlistItem(
                    symbol=symbol,
                    last_price=100.0 + hash(symbol) % 100,
                    change=(-5.0 + hash(symbol) % 10),
                    change_percent=(-2.5 + hash(symbol) % 5),
                    volume=10000 + hash(symbol) % 50000
                )
                
                user_watchlist.append(watchlist_item)
                
                return jsonify({'success': True})
            
            except Exception as e:
                self.logger.error(f"Error adding to watchlist: {e}")
                return jsonify({'success': False, 'error': str(e)}), 400
        
        @self.app.route('/api/market_data/<symbol>')
        @login_required
        def api_market_data(symbol):
            """API endpoint to get market data for symbol"""
            try:
                # Generate sample market data
                base_price = 100.0 + hash(symbol) % 100
                market_data = {
                    'symbol': symbol,
                    'last_price': base_price,
                    'bid': base_price - 0.01,
                    'ask': base_price + 0.01,
                    'change': (-5.0 + hash(symbol) % 10),
                    'change_percent': (-2.5 + hash(symbol) % 5),
                    'volume': 10000 + hash(symbol) % 50000,
                    'high': base_price + 5,
                    'low': base_price - 5,
                    'timestamp': datetime.now().isoformat()
                }
                
                return jsonify(market_data)
            
            except Exception as e:
                self.logger.error(f"Error getting market data: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/offline_status')
        @login_required
        def api_offline_status():
            """API endpoint to get offline status"""
            if not self.offline_manager:
                return jsonify({'offline_enabled': False})
            
            try:
                status = self.offline_manager.get_sync_status()
                return jsonify({
                    'offline_enabled': True,
                    'status': status
                })
            
            except Exception as e:
                self.logger.error(f"Error getting offline status: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/force_sync', methods=['POST'])
        @login_required
        def api_force_sync():
            """API endpoint to force synchronization"""
            if not self.offline_manager:
                return jsonify({'success': False, 'error': 'Offline mode not enabled'})
            
            try:
                self.offline_manager.force_sync()
                return jsonify({'success': True, 'message': 'Sync initiated'})
            
            except Exception as e:
                self.logger.error(f"Error forcing sync: {e}")
                return jsonify({'success': False, 'error': str(e)}), 400
        
        @self.app.route('/api/cached_data/<data_type>')
        @login_required
        def api_get_cached_data(data_type):
            """API endpoint to get cached data"""
            if not self.offline_manager:
                return jsonify({'error': 'Offline mode not enabled'}), 400
            
            try:
                cached_data = self.offline_manager.get_cached_data(data_type, current_user.id)
                return jsonify({
                    'data_type': data_type,
                    'data': cached_data,
                    'count': len(cached_data)
                })
            
            except Exception as e:
                self.logger.error(f"Error getting cached data: {e}")
                return jsonify({'error': str(e)}), 500
    
    def _setup_socket_events(self):
        """Setup SocketIO events"""
        
        @self.socketio.on('connect')
        def handle_connect():
            if current_user.is_authenticated:
                join_room(current_user.id)
                emit('connected', {'message': 'Connected to mobile trading app'})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            if current_user.is_authenticated:
                leave_room(current_user.id)
        
        @self.socketio.on('subscribe_market_data')
        def handle_subscribe_market_data(data):
            """Subscribe to market data updates"""
            if current_user.is_authenticated:
                symbols = data.get('symbols', [])
                # In a real implementation, this would subscribe to actual market data feeds
                emit('market_data_subscribed', {'symbols': symbols})
        
        @self.socketio.on('touch_gesture')
        def handle_touch_gesture(data):
            """Handle touch gesture events"""
            if current_user.is_authenticated:
                gesture = data.get('gesture')
                element = data.get('element')
                coordinates = data.get('coordinates', {})
                
                self.logger.info(f"Touch gesture: {gesture} on {element} at {coordinates}")
                
                # Process gesture-based actions
                if gesture == TouchGesture.DOUBLE_TAP.value and element == 'chart':
                    emit('chart_zoom', {'action': 'zoom_in'})
                elif gesture == TouchGesture.PINCH_ZOOM.value and element == 'chart':
                    emit('chart_zoom', {'action': 'zoom_out'})
                elif gesture == TouchGesture.SWIPE_LEFT.value and element == 'watchlist_item':
                    emit('show_actions', {'actions': ['buy', 'sell', 'remove']})
        
        @self.socketio.on('request_offline_status')
        def handle_offline_status_request():
            """Handle offline status request"""
            if current_user.is_authenticated and self.offline_manager:
                status = self.offline_manager.get_sync_status()
                emit('offline_status', status)
        
        @self.socketio.on('cache_data_request')
        def handle_cache_data_request(data):
            """Handle data caching request"""
            if current_user.is_authenticated and self.offline_manager:
                data_type = data.get('data_type')
                data_payload = data.get('data')
                ttl_hours = data.get('ttl_hours', 24)
                
                try:
                    asyncio.create_task(self.offline_manager.cache_data(
                        data_type, data_payload, current_user.id, ttl_hours
                    ))
                    emit('cache_success', {'data_type': data_type})
                except Exception as e:
                    emit('cache_error', {'error': str(e)})
    
    def _initialize_sample_data(self):
        """Initialize sample data for demonstration"""
        # This would be replaced with actual data sources in production
        sample_symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'NVDA', 'META']
        
        # Create sample positions and watchlist items
        for symbol in sample_symbols:
            base_price = 100.0 + hash(symbol) % 100
            
            # Sample position
            position = MobilePosition(
                symbol=symbol,
                quantity=100 + hash(symbol) % 500,
                avg_price=base_price - 5,
                market_price=base_price,
                unrealized_pnl=(base_price - (base_price - 5)) * (100 + hash(symbol) % 500),
                percentage_change=2.5 - hash(symbol) % 5,
                side='long' if hash(symbol) % 2 == 0 else 'short'
            )
            
            # Sample watchlist item
            watchlist_item = MobileWatchlistItem(
                symbol=symbol,
                last_price=base_price,
                change=(-5.0 + hash(symbol) % 10),
                change_percent=(-2.5 + hash(symbol) % 5),
                volume=10000 + hash(symbol) % 50000,
                is_favorite=hash(symbol) % 3 == 0
            )
    
    async def start_price_updates(self):
        """Start background task for price updates"""
        while True:
            try:
                # Simulate price updates
                for user_id in self.users:
                    user_watchlist = self.watchlists.get(user_id, [])
                    market_data_batch = {}
                    
                    for item in user_watchlist:
                        # Simulate price movement
                        price_change = (hash(item.symbol + str(datetime.now().second)) % 200 - 100) / 100
                        item.last_price += price_change
                        item.change += price_change
                        item.change_percent = (item.change / (item.last_price - item.change)) * 100
                        
                        # Prepare market data for caching
                        market_data_batch[item.symbol] = {
                            'symbol': item.symbol,
                            'price': item.last_price,
                            'change': item.change,
                            'change_percent': item.change_percent,
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        # Emit price update
                        self.socketio.emit('price_update', {
                            'symbol': item.symbol,
                            'price': item.last_price,
                            'change': item.change,
                            'change_percent': item.change_percent
                        }, room=user_id)
                    
                    # Cache market data for offline access
                    if self.offline_manager and market_data_batch:
                        try:
                            await cache_market_data(
                                self.offline_manager,
                                market_data_batch,
                                user_id
                            )
                        except Exception as e:
                            self.logger.error(f"Error caching market data: {e}")
                    
                    # Cache portfolio data periodically
                    user_positions = self.positions.get(user_id, [])
                    if self.offline_manager and user_positions:
                        try:
                            portfolio_data = {
                                'positions': [
                                    {
                                        'symbol': pos.symbol,
                                        'quantity': pos.quantity,
                                        'avg_price': pos.avg_price,
                                        'market_price': pos.market_price,
                                        'unrealized_pnl': pos.unrealized_pnl,
                                        'percentage_change': pos.percentage_change,
                                        'side': pos.side
                                    }
                                    for pos in user_positions
                                ],
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            await cache_portfolio_data(
                                self.offline_manager,
                                portfolio_data,
                                user_id
                            )
                        except Exception as e:
                            self.logger.error(f"Error caching portfolio data: {e}")
                
                await asyncio.sleep(5)  # Update every 5 seconds
            
            except Exception as e:
                self.logger.error(f"Error in price updates: {e}")
                await asyncio.sleep(10)
    
    def run(self, debug: bool = False):
        """Run the mobile trading app"""
        self.logger.info(f"Starting mobile trading app on {self.host}:{self.port}")
        
        if self.offline_manager:
            self.logger.info("Offline capability enabled")
        
        # Start background tasks
        asyncio.create_task(self.start_price_updates())
        
        try:
            self.socketio.run(self.app, host=self.host, port=self.port, debug=debug)
        finally:
            # Cleanup offline manager on shutdown
            if self.offline_manager:
                self.offline_manager.shutdown()

# Mobile app templates (would be in separate template files in production)
MOBILE_TEMPLATES = {
    'mobile_login.html': '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mobile Trading - Login</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .login-container { max-width: 400px; margin: 50px auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 5px; font-size: 16px; }
        button { width: 100%; padding: 15px; background: #007bff; color: white; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; }
        button:hover { background: #0056b3; }
        .error { color: red; margin-top: 10px; }
        .logo { text-align: center; margin-bottom: 30px; font-size: 24px; font-weight: bold; color: #007bff; }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">📱 Mobile Trading</div>
        <form method="POST">
            <div class="form-group">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" required>
            </div>
            <div class="form-group">
                <label for="device_type">Device Type:</label>
                <select id="device_type" name="device_type">
                    <option value="mobile">Mobile</option>
                    <option value="tablet">Tablet</option>
                </select>
            </div>
            <button type="submit">Login</button>
            {% if error %}
                <div class="error">{{ error }}</div>
            {% endif %}
        </form>
    </div>
</body>
</html>
    ''',
    
    'mobile_dashboard.html': '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mobile Trading - Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 0; background: #f5f5f5; }
        .header { background: #007bff; color: white; padding: 15px; text-align: center; position: sticky; top: 0; z-index: 100; }
        .nav-tabs { display: flex; background: white; border-bottom: 1px solid #ddd; }
        .nav-tab { flex: 1; padding: 15px; text-align: center; border: none; background: none; cursor: pointer; }
        .nav-tab.active { background: #007bff; color: white; }
        .content { padding: 20px; }
        .card { background: white; margin-bottom: 15px; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .position { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #eee; }
        .position:last-child { border-bottom: none; }
        .symbol { font-weight: bold; font-size: 16px; }
        .pnl.positive { color: green; }
        .pnl.negative { color: red; }
        .quick-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 20px; }
        .action-btn { padding: 15px; background: #28a745; color: white; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; }
        .action-btn.sell { background: #dc3545; }
        .floating-trade-btn { position: fixed; bottom: 20px; right: 20px; width: 60px; height: 60px; background: #007bff; color: white; border: none; border-radius: 50%; font-size: 24px; cursor: pointer; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
    </style>
</head>
<body>
    <div class="header">
        <h1>📱 Mobile Trading</h1>
        <div>Welcome, {{ user.username }}</div>
    </div>
    
    <div class="nav-tabs">
        <button class="nav-tab active" onclick="showTab('portfolio')">Portfolio</button>
        <button class="nav-tab" onclick="showTab('watchlist')">Watchlist</button>
        <button class="nav-tab" onclick="showTab('orders')">Orders</button>
    </div>
    
    <div class="content">
        <div id="portfolio-tab" class="tab-content">
            <div class="card">
                <h3>Portfolio Summary</h3>
                <div>Total Value: ${{ "%.2f"|format(positions|sum(attribute='quantity')|multiply(100)) }}</div>
                <div>Total P&L: <span class="pnl {{ 'positive' if positions|sum(attribute='unrealized_pnl') > 0 else 'negative' }}">${{ "%.2f"|format(positions|sum(attribute='unrealized_pnl')) }}</span></div>
            </div>
            
            <div class="card">
                <h3>Positions</h3>
                {% for position in positions %}
                <div class="position">
                    <div>
                        <div class="symbol">{{ position.symbol }}</div>
                        <div>{{ position.quantity }} shares @ ${{ "%.2f"|format(position.avg_price) }}</div>
                    </div>
                    <div>
                        <div class="pnl {{ 'positive' if position.unrealized_pnl > 0 else 'negative' }}">${{ "%.2f"|format(position.unrealized_pnl) }}</div>
                        <div>{{ "%.1f"|format(position.percentage_change) }}%</div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        
        <div id="watchlist-tab" class="tab-content" style="display: none;">
            <div class="card">
                <h3>Watchlist</h3>
                {% for item in watchlist %}
                <div class="position">
                    <div>
                        <div class="symbol">{{ item.symbol }}</div>
                        <div>Vol: {{ "{:,}"|format(item.volume) }}</div>
                    </div>
                    <div>
                        <div>${{ "%.2f"|format(item.last_price) }}</div>
                        <div class="pnl {{ 'positive' if item.change > 0 else 'negative' }}">{{ "%.2f"|format(item.change_percent) }}%</div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        
        <div id="orders-tab" class="tab-content" style="display: none;">
            <div class="card">
                <h3>Recent Orders</h3>
                {% for order in orders %}
                <div class="position">
                    <div>
                        <div class="symbol">{{ order.symbol }}</div>
                        <div>{{ order.side.upper() }} {{ order.quantity }} @ ${{ "%.2f"|format(order.price or 0) }}</div>
                    </div>
                    <div>
                        <div>{{ order.status }}</div>
                        <div>{{ order.timestamp.strftime('%H:%M') }}</div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
    </div>
    
    <button class="floating-trade-btn" onclick="window.location.href='/trade'">+</button>
    
    <script>
        function showTab(tabName) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => tab.style.display = 'none');
            document.querySelectorAll('.nav-tab').forEach(tab => tab.classList.remove('active'));
            
            // Show selected tab
            document.getElementById(tabName + '-tab').style.display = 'block';
            event.target.classList.add('active');
        }
    </script>
</body>
</html>
    '''
}

def create_mobile_app(host: str = "0.0.0.0", port: int = 5001, enable_offline: bool = True) -> MobileTradingApp:
    """Create and configure mobile trading app"""
    return MobileTradingApp(host=host, port=port, enable_offline=enable_offline)

if __name__ == "__main__":
    app = create_mobile_app()
    app.run(debug=True)