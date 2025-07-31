"""
Modern Web Trading Interface
React-based trading dashboard with real-time WebSocket data feeds
"""
import logging
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

try:
    from flask import Flask, render_template, jsonify, request, send_from_directory
    from flask_socketio import SocketIO, emit, join_room, leave_room
    from flask_cors import CORS
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False


@dataclass
class UserSession:
    """User session data"""
    user_id: str
    username: str
    permissions: List[str]
    session_id: str
    created_at: datetime
    last_activity: datetime


class WebTradingInterface:
    """Modern web trading interface"""
    
    def __init__(self, host: str = "localhost", port: int = 3000):
        self.host = host
        self.port = port
        self.logger = logging.getLogger(__name__)
        self.active_sessions: Dict[str, UserSession] = {}
        
        if FLASK_AVAILABLE:
            self.app = Flask(__name__, 
                           static_folder='static',
                           template_folder='templates')
            self.app.config['SECRET_KEY'] = 'nautilus-trader-secret-key'
            
            # Enable CORS for development
            CORS(self.app)
            
            self.socketio = SocketIO(self.app, 
                                   cors_allowed_origins="*",
                                   async_mode='threading')
            
            self._setup_routes()
            self._setup_websocket_handlers()
        else:
            self.app = None
            self.socketio = None
            self.logger.warning("Flask not available - web interface disabled")
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            """Main trading dashboard"""
            return render_template('index.html')
        
        @self.app.route('/login')
        def login():
            """Login page"""
            return render_template('login.html')
        
        @self.app.route('/api/auth/login', methods=['POST'])
        def api_login():
            """API login endpoint"""
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
            
            # Simple authentication (replace with real auth)
            if username and password:
                session_id = f"session_{datetime.now().timestamp()}"
                user_session = UserSession(
                    user_id=f"user_{username}",
                    username=username,
                    permissions=['trade', 'view_positions', 'view_orders'],
                    session_id=session_id,
                    created_at=datetime.now(),
                    last_activity=datetime.now()
                )
                
                self.active_sessions[session_id] = user_session
                
                return jsonify({
                    'success': True,
                    'session_id': session_id,
                    'user': {
                        'username': username,
                        'permissions': user_session.permissions
                    }
                })
            else:
                return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
        
        @self.app.route('/api/market/data')
        def api_market_data():
            """Get market data"""
            return jsonify({
                'timestamp': datetime.now().isoformat(),
                'symbols': [
                    {
                        'symbol': 'AAPL',
                        'price': 150.25,
                        'change': 2.15,
                        'change_percent': 1.45,
                        'volume': 45000000
                    },
                    {
                        'symbol': 'GOOGL',
                        'price': 2750.80,
                        'change': -15.20,
                        'change_percent': -0.55,
                        'volume': 1200000
                    },
                    {
                        'symbol': 'MSFT',
                        'price': 305.15,
                        'change': 5.75,
                        'change_percent': 1.92,
                        'volume': 28000000
                    }
                ]
            })
        
        @self.app.route('/api/portfolio/positions')
        def api_positions():
            """Get portfolio positions"""
            return jsonify({
                'positions': [
                    {
                        'symbol': 'AAPL',
                        'quantity': 100,
                        'avg_price': 145.50,
                        'market_price': 150.25,
                        'market_value': 15025.00,
                        'unrealized_pnl': 475.00,
                        'unrealized_pnl_percent': 3.26
                    },
                    {
                        'symbol': 'GOOGL',
                        'quantity': 10,
                        'avg_price': 2800.00,
                        'market_price': 2750.80,
                        'market_value': 27508.00,
                        'unrealized_pnl': -492.00,
                        'unrealized_pnl_percent': -1.76
                    }
                ],
                'total_value': 42533.00,
                'total_pnl': -17.00,
                'total_pnl_percent': -0.04
            })
        
        @self.app.route('/api/orders')
        def api_orders():
            """Get orders"""
            return jsonify({
                'orders': [
                    {
                        'order_id': 'ORD_001',
                        'symbol': 'TSLA',
                        'side': 'buy',
                        'quantity': 50,
                        'price': 800.00,
                        'status': 'pending',
                        'timestamp': '2024-01-15T10:30:00Z'
                    },
                    {
                        'order_id': 'ORD_002',
                        'symbol': 'AMZN',
                        'side': 'sell',
                        'quantity': 25,
                        'price': 3200.00,
                        'status': 'filled',
                        'timestamp': '2024-01-15T09:15:00Z'
                    }
                ]
            })
        
        @self.app.route('/api/orders', methods=['POST'])
        def api_place_order():
            """Place new order"""
            data = request.get_json()
            
            # Validate order data
            required_fields = ['symbol', 'side', 'quantity', 'price']
            if not all(field in data for field in required_fields):
                return jsonify({'error': 'Missing required fields'}), 400
            
            # Create order (mock implementation)
            order = {
                'order_id': f"ORD_{datetime.now().timestamp()}",
                'symbol': data['symbol'],
                'side': data['side'],
                'quantity': data['quantity'],
                'price': data['price'],
                'status': 'pending',
                'timestamp': datetime.now().isoformat()
            }
            
            # Emit order update via WebSocket
            self.socketio.emit('order_update', order)
            
            return jsonify({'success': True, 'order': order})
        
        @self.app.route('/static/<path:filename>')
        def static_files(filename):
            """Serve static files"""
            return send_from_directory('static', filename)
    
    def _setup_websocket_handlers(self):
        """Setup WebSocket event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect():
            self.logger.info(f"Client connected: {request.sid}")
            emit('connected', {'message': 'Connected to Nautilus Trader'})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            self.logger.info(f"Client disconnected: {request.sid}")
        
        @self.socketio.on('join_room')
        def handle_join_room(data):
            room = data.get('room')
            if room:
                join_room(room)
                emit('joined_room', {'room': room})
                self.logger.info(f"Client {request.sid} joined room: {room}")
        
        @self.socketio.on('leave_room')
        def handle_leave_room(data):
            room = data.get('room')
            if room:
                leave_room(room)
                emit('left_room', {'room': room})
                self.logger.info(f"Client {request.sid} left room: {room}")
        
        @self.socketio.on('subscribe_market_data')
        def handle_subscribe_market_data(data):
            symbols = data.get('symbols', [])
            join_room('market_data')
            emit('market_data_subscribed', {'symbols': symbols})
            self.logger.info(f"Client {request.sid} subscribed to market data: {symbols}")
        
        @self.socketio.on('place_order')
        def handle_place_order(data):
            # Validate and process order
            order_id = f"ORD_{datetime.now().timestamp()}"
            order = {
                'order_id': order_id,
                'symbol': data.get('symbol'),
                'side': data.get('side'),
                'quantity': data.get('quantity'),
                'price': data.get('price'),
                'status': 'pending',
                'timestamp': datetime.now().isoformat()
            }
            
            # Emit order confirmation
            emit('order_placed', order)
            
            # Broadcast order update to all clients
            self.socketio.emit('order_update', order, room='orders')
            
            self.logger.info(f"Order placed: {order_id}")
    
    async def start_market_data_feed(self):
        """Start real-time market data feed"""
        while True:
            try:
                # Generate mock market data
                market_data = {
                    'timestamp': datetime.now().isoformat(),
                    'data': [
                        {
                            'symbol': 'AAPL',
                            'price': 150.25 + (hash(str(datetime.now())) % 100 - 50) / 100,
                            'volume': 1000 + (hash(str(datetime.now())) % 5000)
                        },
                        {
                            'symbol': 'GOOGL',
                            'price': 2750.80 + (hash(str(datetime.now())) % 200 - 100) / 100,
                            'volume': 500 + (hash(str(datetime.now())) % 2000)
                        }
                    ]
                }
                
                # Broadcast to all clients in market_data room
                if self.socketio:
                    self.socketio.emit('market_data_update', market_data, room='market_data')
                
                await asyncio.sleep(1)  # Update every second
                
            except Exception as e:
                self.logger.error(f"Error in market data feed: {e}")
                await asyncio.sleep(5)
    
    def create_static_files(self):
        """Create static files for the web interface"""
        static_dir = Path("nautilus_trader_engine/visualization/static")
        templates_dir = Path("nautilus_trader_engine/visualization/templates")
        
        static_dir.mkdir(parents=True, exist_ok=True)
        templates_dir.mkdir(parents=True, exist_ok=True)
        
        # Create main CSS file
        css_content = """
/* Nautilus Trader Web Interface Styles */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background-color: #1a1a1a;
    color: #ffffff;
    line-height: 1.6;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

/* Header */
.header {
    background-color: #2d2d2d;
    padding: 1rem 0;
    border-bottom: 2px solid #4a90e2;
}

.header h1 {
    color: #4a90e2;
    text-align: center;
}

/* Navigation */
.nav {
    background-color: #333;
    padding: 1rem 0;
}

.nav ul {
    list-style: none;
    display: flex;
    justify-content: center;
}

.nav li {
    margin: 0 1rem;
}

.nav a {
    color: #fff;
    text-decoration: none;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    transition: background-color 0.3s;
}

.nav a:hover {
    background-color: #4a90e2;
}

/* Dashboard Grid */
.dashboard {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-top: 20px;
}

.widget {
    background-color: #2d2d2d;
    border-radius: 8px;
    padding: 20px;
    border: 1px solid #444;
}

.widget h3 {
    color: #4a90e2;
    margin-bottom: 15px;
    border-bottom: 1px solid #444;
    padding-bottom: 10px;
}

/* Market Data */
.market-data {
    grid-column: 1 / -1;
}

.symbol-list {
    display: flex;
    gap: 20px;
    flex-wrap: wrap;
}

.symbol-card {
    background-color: #333;
    padding: 15px;
    border-radius: 6px;
    min-width: 150px;
    text-align: center;
}

.symbol-name {
    font-weight: bold;
    font-size: 1.2em;
    margin-bottom: 5px;
}

.symbol-price {
    font-size: 1.5em;
    color: #4a90e2;
    margin-bottom: 5px;
}

.symbol-change.positive {
    color: #28a745;
}

.symbol-change.negative {
    color: #dc3545;
}

/* Tables */
.table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 10px;
}

.table th,
.table td {
    padding: 10px;
    text-align: left;
    border-bottom: 1px solid #444;
}

.table th {
    background-color: #333;
    color: #4a90e2;
}

.table tr:hover {
    background-color: #333;
}

/* Forms */
.form-group {
    margin-bottom: 15px;
}

.form-group label {
    display: block;
    margin-bottom: 5px;
    color: #ccc;
}

.form-control {
    width: 100%;
    padding: 10px;
    background-color: #333;
    border: 1px solid #555;
    border-radius: 4px;
    color: #fff;
}

.form-control:focus {
    outline: none;
    border-color: #4a90e2;
}

.btn {
    padding: 10px 20px;
    background-color: #4a90e2;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.3s;
}

.btn:hover {
    background-color: #357abd;
}

.btn-success {
    background-color: #28a745;
}

.btn-success:hover {
    background-color: #218838;
}

.btn-danger {
    background-color: #dc3545;
}

.btn-danger:hover {
    background-color: #c82333;
}

/* Status indicators */
.status {
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 0.8em;
    font-weight: bold;
}

.status.pending {
    background-color: #ffc107;
    color: #000;
}

.status.filled {
    background-color: #28a745;
    color: #fff;
}

.status.cancelled {
    background-color: #dc3545;
    color: #fff;
}

/* Responsive */
@media (max-width: 768px) {
    .dashboard {
        grid-template-columns: 1fr;
    }
    
    .symbol-list {
        justify-content: center;
    }
    
    .nav ul {
        flex-direction: column;
        align-items: center;
    }
}

/* Loading spinner */
.loading {
    display: inline-block;
    width: 20px;
    height: 20px;
    border: 3px solid #f3f3f3;
    border-top: 3px solid #4a90e2;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* Connection status */
.connection-status {
    position: fixed;
    top: 10px;
    right: 10px;
    padding: 5px 10px;
    border-radius: 4px;
    font-size: 0.8em;
}

.connection-status.connected {
    background-color: #28a745;
    color: white;
}

.connection-status.disconnected {
    background-color: #dc3545;
    color: white;
}
"""
        
        with open(static_dir / "style.css", "w") as f:
            f.write(css_content)
        
        # Create main JavaScript file
        js_content = """
// Nautilus Trader Web Interface JavaScript
class NautilusTrader {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.marketData = {};
        this.positions = [];
        this.orders = [];
        
        this.init();
    }
    
    init() {
        this.connectWebSocket();
        this.setupEventListeners();
        this.loadInitialData();
        this.updateConnectionStatus();
    }
    
    connectWebSocket() {
        this.socket = io();
        
        this.socket.on('connect', () => {
            console.log('Connected to Nautilus Trader');
            this.isConnected = true;
            this.updateConnectionStatus();
            
            // Join market data room
            this.socket.emit('join_room', { room: 'market_data' });
            this.socket.emit('join_room', { room: 'orders' });
        });
        
        this.socket.on('disconnect', () => {
            console.log('Disconnected from Nautilus Trader');
            this.isConnected = false;
            this.updateConnectionStatus();
        });
        
        this.socket.on('market_data_update', (data) => {
            this.updateMarketData(data);
        });
        
        this.socket.on('order_update', (order) => {
            this.updateOrderStatus(order);
        });
        
        this.socket.on('order_placed', (order) => {
            this.showNotification('Order placed successfully', 'success');
            this.loadOrders();
        });
    }
    
    setupEventListeners() {
        // Order form submission
        const orderForm = document.getElementById('order-form');
        if (orderForm) {
            orderForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.placeOrder();
            });
        }
        
        // Refresh buttons
        document.querySelectorAll('.refresh-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const target = btn.dataset.target;
                this.refreshData(target);
            });
        });
    }
    
    async loadInitialData() {
        try {
            await Promise.all([
                this.loadMarketData(),
                this.loadPositions(),
                this.loadOrders()
            ]);
        } catch (error) {
            console.error('Error loading initial data:', error);
        }
    }
    
    async loadMarketData() {
        try {
            const response = await fetch('/api/market/data');
            const data = await response.json();
            this.renderMarketData(data.symbols);
        } catch (error) {
            console.error('Error loading market data:', error);
        }
    }
    
    async loadPositions() {
        try {
            const response = await fetch('/api/portfolio/positions');
            const data = await response.json();
            this.positions = data.positions;
            this.renderPositions(data);
        } catch (error) {
            console.error('Error loading positions:', error);
        }
    }
    
    async loadOrders() {
        try {
            const response = await fetch('/api/orders');
            const data = await response.json();
            this.orders = data.orders;
            this.renderOrders(data.orders);
        } catch (error) {
            console.error('Error loading orders:', error);
        }
    }
    
    renderMarketData(symbols) {
        const container = document.getElementById('market-data');
        if (!container) return;
        
        const symbolsHtml = symbols.map(symbol => `
            <div class="symbol-card">
                <div class="symbol-name">${symbol.symbol}</div>
                <div class="symbol-price">$${symbol.price.toFixed(2)}</div>
                <div class="symbol-change ${symbol.change >= 0 ? 'positive' : 'negative'}">
                    ${symbol.change >= 0 ? '+' : ''}${symbol.change.toFixed(2)} 
                    (${symbol.change_percent.toFixed(2)}%)
                </div>
                <div class="symbol-volume">Vol: ${symbol.volume.toLocaleString()}</div>
            </div>
        `).join('');
        
        container.innerHTML = `
            <div class="symbol-list">
                ${symbolsHtml}
            </div>
        `;
    }
    
    renderPositions(data) {
        const container = document.getElementById('positions-table');
        if (!container) return;
        
        const positionsHtml = data.positions.map(pos => `
            <tr>
                <td>${pos.symbol}</td>
                <td>${pos.quantity}</td>
                <td>$${pos.avg_price.toFixed(2)}</td>
                <td>$${pos.market_price.toFixed(2)}</td>
                <td>$${pos.market_value.toFixed(2)}</td>
                <td class="${pos.unrealized_pnl >= 0 ? 'positive' : 'negative'}">
                    $${pos.unrealized_pnl.toFixed(2)} (${pos.unrealized_pnl_percent.toFixed(2)}%)
                </td>
            </tr>
        `).join('');
        
        container.innerHTML = positionsHtml;
        
        // Update summary
        const summary = document.getElementById('portfolio-summary');
        if (summary) {
            summary.innerHTML = `
                <p>Total Value: $${data.total_value.toFixed(2)}</p>
                <p class="${data.total_pnl >= 0 ? 'positive' : 'negative'}">
                    Total P&L: $${data.total_pnl.toFixed(2)} (${data.total_pnl_percent.toFixed(2)}%)
                </p>
            `;
        }
    }
    
    renderOrders(orders) {
        const container = document.getElementById('orders-table');
        if (!container) return;
        
        const ordersHtml = orders.map(order => `
            <tr>
                <td>${order.order_id}</td>
                <td>${order.symbol}</td>
                <td>${order.side.toUpperCase()}</td>
                <td>${order.quantity}</td>
                <td>$${order.price.toFixed(2)}</td>
                <td><span class="status ${order.status}">${order.status.toUpperCase()}</span></td>
                <td>${new Date(order.timestamp).toLocaleString()}</td>
            </tr>
        `).join('');
        
        container.innerHTML = ordersHtml;
    }
    
    async placeOrder() {
        const form = document.getElementById('order-form');
        const formData = new FormData(form);
        
        const orderData = {
            symbol: formData.get('symbol'),
            side: formData.get('side'),
            quantity: parseInt(formData.get('quantity')),
            price: parseFloat(formData.get('price'))
        };
        
        try {
            const response = await fetch('/api/orders', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(orderData)
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification('Order placed successfully', 'success');
                form.reset();
                this.loadOrders();
            } else {
                this.showNotification('Error placing order: ' + result.error, 'error');
            }
        } catch (error) {
            console.error('Error placing order:', error);
            this.showNotification('Error placing order', 'error');
        }
    }
    
    updateMarketData(data) {
        // Update market data in real-time
        data.data.forEach(symbol => {
            this.marketData[symbol.symbol] = symbol;
        });
        
        // Re-render market data
        this.renderMarketData(Object.values(this.marketData));
    }
    
    updateOrderStatus(order) {
        // Update order in the list
        const index = this.orders.findIndex(o => o.order_id === order.order_id);
        if (index >= 0) {
            this.orders[index] = order;
        } else {
            this.orders.push(order);
        }
        
        this.renderOrders(this.orders);
    }
    
    updateConnectionStatus() {
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            statusElement.textContent = this.isConnected ? 'Connected' : 'Disconnected';
            statusElement.className = `connection-status ${this.isConnected ? 'connected' : 'disconnected'}`;
        }
    }
    
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        // Add to page
        document.body.appendChild(notification);
        
        // Remove after 3 seconds
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 3000);
    }
    
    refreshData(target) {
        switch (target) {
            case 'market':
                this.loadMarketData();
                break;
            case 'positions':
                this.loadPositions();
                break;
            case 'orders':
                this.loadOrders();
                break;
            default:
                this.loadInitialData();
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.nautilusTrader = new NautilusTrader();
});
"""
        
        with open(static_dir / "app.js", "w") as f:
            f.write(js_content)
        
        self.logger.info("Static files created successfully")
    
    def create_templates(self):
        """Create HTML templates"""
        templates_dir = Path("nautilus_trader_engine/visualization/templates")
        templates_dir.mkdir(parents=True, exist_ok=True)
        
        # Main index template
        index_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nautilus Trader - Trading Dashboard</title>
    <link rel="stylesheet" href="/static/style.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
</head>
<body>
    <div id="connection-status" class="connection-status">Connecting...</div>
    
    <header class="header">
        <div class="container">
            <h1>Nautilus Trader</h1>
        </div>
    </header>
    
    <nav class="nav">
        <div class="container">
            <ul>
                <li><a href="#dashboard">Dashboard</a></li>
                <li><a href="#positions">Positions</a></li>
                <li><a href="#orders">Orders</a></li>
                <li><a href="#trading">Trading</a></li>
            </ul>
        </div>
    </nav>
    
    <main class="container">
        <div class="dashboard">
            <!-- Market Data Widget -->
            <div class="widget market-data">
                <h3>Market Data <button class="btn refresh-btn" data-target="market">Refresh</button></h3>
                <div id="market-data">
                    <div class="loading"></div>
                </div>
            </div>
            
            <!-- Portfolio Widget -->
            <div class="widget">
                <h3>Portfolio <button class="btn refresh-btn" data-target="positions">Refresh</button></h3>
                <div id="portfolio-summary"></div>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Symbol</th>
                            <th>Quantity</th>
                            <th>Avg Price</th>
                            <th>Market Price</th>
                            <th>Market Value</th>
                            <th>Unrealized P&L</th>
                        </tr>
                    </thead>
                    <tbody id="positions-table">
                        <tr><td colspan="6">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
            
            <!-- Orders Widget -->
            <div class="widget">
                <h3>Orders <button class="btn refresh-btn" data-target="orders">Refresh</button></h3>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Order ID</th>
                            <th>Symbol</th>
                            <th>Side</th>
                            <th>Quantity</th>
                            <th>Price</th>
                            <th>Status</th>
                            <th>Time</th>
                        </tr>
                    </thead>
                    <tbody id="orders-table">
                        <tr><td colspan="7">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
            
            <!-- Trading Widget -->
            <div class="widget">
                <h3>Place Order</h3>
                <form id="order-form">
                    <div class="form-group">
                        <label for="symbol">Symbol</label>
                        <input type="text" id="symbol" name="symbol" class="form-control" required placeholder="e.g., AAPL">
                    </div>
                    
                    <div class="form-group">
                        <label for="side">Side</label>
                        <select id="side" name="side" class="form-control" required>
                            <option value="">Select Side</option>
                            <option value="buy">Buy</option>
                            <option value="sell">Sell</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="quantity">Quantity</label>
                        <input type="number" id="quantity" name="quantity" class="form-control" required min="1">
                    </div>
                    
                    <div class="form-group">
                        <label for="price">Price</label>
                        <input type="number" id="price" name="price" class="form-control" required step="0.01" min="0.01">
                    </div>
                    
                    <button type="submit" class="btn btn-success">Place Order</button>
                </form>
            </div>
        </div>
    </main>
    
    <script src="/static/app.js"></script>
</body>
</html>
"""
        
        with open(templates_dir / "index.html", "w") as f:
            f.write(index_html)
        
        # Login template
        login_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nautilus Trader - Login</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="container" style="max-width: 400px; margin-top: 100px;">
        <div class="widget">
            <h3>Login to Nautilus Trader</h3>
            <form id="login-form">
                <div class="form-group">
                    <label for="username">Username</label>
                    <input type="text" id="username" name="username" class="form-control" required>
                </div>
                
                <div class="form-group">
                    <label for="password">Password</label>
                    <input type="password" id="password" name="password" class="form-control" required>
                </div>
                
                <button type="submit" class="btn">Login</button>
            </form>
        </div>
    </div>
    
    <script>
        document.getElementById('login-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(e.target);
            const loginData = {
                username: formData.get('username'),
                password: formData.get('password')
            };
            
            try {
                const response = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(loginData)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    localStorage.setItem('session_id', result.session_id);
                    window.location.href = '/';
                } else {
                    alert('Login failed: ' + result.error);
                }
            } catch (error) {
                console.error('Login error:', error);
                alert('Login failed');
            }
        });
    </script>
</body>
</html>
"""
        
        with open(templates_dir / "login.html", "w") as f:
            f.write(login_html)
        
        self.logger.info("Templates created successfully")
    
    def run(self):
        """Run the web interface server"""
        if self.app and self.socketio:
            self.create_static_files()
            self.create_templates()
            
            self.logger.info(f"Starting web interface server on {self.host}:{self.port}")
            self.socketio.run(self.app, host=self.host, port=self.port, debug=False)
        else:
            self.logger.error("Cannot start web server - Flask not available")


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    web_interface = WebTradingInterface()
    web_interface.run()