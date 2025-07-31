"""
Real-time Order Book Visualization
Advanced order book depth visualization with WebSocket updates
"""
import logging
import asyncio
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import deque
import uuid

try:
    from flask import Flask, render_template, jsonify, request
    from flask_socketio import SocketIO, emit, join_room, leave_room
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


@dataclass
class OrderBookLevel:
    """Order book price level"""
    price: float
    quantity: float
    orders: int = 1
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class OrderBookSnapshot:
    """Complete order book snapshot"""
    symbol: str
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]
    timestamp: datetime
    sequence: int = 0
    
    @property
    def spread(self) -> float:
        """Calculate bid-ask spread"""
        if self.bids and self.asks:
            return self.asks[0].price - self.bids[0].price
        return 0.0
    
    @property
    def mid_price(self) -> float:
        """Calculate mid price"""
        if self.bids and self.asks:
            return (self.bids[0].price + self.asks[0].price) / 2
        return 0.0


@dataclass
class OrderBookMetrics:
    """Order book analytics metrics"""
    symbol: str
    timestamp: datetime
    spread: float
    spread_bps: float
    mid_price: float
    bid_depth: float
    ask_depth: float
    imbalance: float
    weighted_mid: float
    microprice: float


class OrderBookAnalyzer:
    """Order book analysis and metrics calculation"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def calculate_metrics(self, snapshot: OrderBookSnapshot, depth_levels: int = 5) -> OrderBookMetrics:
        """Calculate comprehensive order book metrics"""
        if not snapshot.bids or not snapshot.asks:
            return OrderBookMetrics(
                symbol=snapshot.symbol,
                timestamp=snapshot.timestamp,
                spread=0, spread_bps=0, mid_price=0,
                bid_depth=0, ask_depth=0, imbalance=0,
                weighted_mid=0, microprice=0
            )
        
        # Basic metrics
        best_bid = snapshot.bids[0].price
        best_ask = snapshot.asks[0].price
        spread = best_ask - best_bid
        mid_price = (best_bid + best_ask) / 2
        spread_bps = (spread / mid_price) * 10000 if mid_price > 0 else 0
        
        # Depth calculations
        bid_depth = sum(level.quantity for level in snapshot.bids[:depth_levels])
        ask_depth = sum(level.quantity for level in snapshot.asks[:depth_levels])
        
        # Order book imbalance
        total_depth = bid_depth + ask_depth
        imbalance = (bid_depth - ask_depth) / total_depth if total_depth > 0 else 0
        
        # Weighted mid price
        bid_weight = snapshot.bids[0].quantity if snapshot.bids else 0
        ask_weight = snapshot.asks[0].quantity if snapshot.asks else 0
        total_weight = bid_weight + ask_weight
        
        if total_weight > 0:
            weighted_mid = (best_bid * ask_weight + best_ask * bid_weight) / total_weight
        else:
            weighted_mid = mid_price
        
        # Microprice (probability-weighted mid)
        if bid_weight + ask_weight > 0:
            bid_prob = ask_weight / (bid_weight + ask_weight)
            ask_prob = bid_weight / (bid_weight + ask_weight)
            microprice = best_bid * bid_prob + best_ask * ask_prob
        else:
            microprice = mid_price
        
        return OrderBookMetrics(
            symbol=snapshot.symbol,
            timestamp=snapshot.timestamp,
            spread=spread,
            spread_bps=spread_bps,
            mid_price=mid_price,
            bid_depth=bid_depth,
            ask_depth=ask_depth,
            imbalance=imbalance,
            weighted_mid=weighted_mid,
            microprice=microprice
        )
    
    def detect_anomalies(self, snapshots: List[OrderBookSnapshot]) -> List[Dict[str, Any]]:
        """Detect order book anomalies"""
        anomalies = []
        
        if len(snapshots) < 2:
            return anomalies
        
        for i in range(1, len(snapshots)):
            current = snapshots[i]
            previous = snapshots[i-1]
            
            # Large spread increase
            if current.spread > previous.spread * 2:
                anomalies.append({
                    'type': 'large_spread_increase',
                    'timestamp': current.timestamp,
                    'current_spread': current.spread,
                    'previous_spread': previous.spread,
                    'severity': 'high'
                })
            
            # Significant depth reduction
            current_metrics = self.calculate_metrics(current)
            previous_metrics = self.calculate_metrics(previous)
            
            depth_reduction = (previous_metrics.bid_depth + previous_metrics.ask_depth) - \
                            (current_metrics.bid_depth + current_metrics.ask_depth)
            
            if depth_reduction > (previous_metrics.bid_depth + previous_metrics.ask_depth) * 0.5:
                anomalies.append({
                    'type': 'depth_reduction',
                    'timestamp': current.timestamp,
                    'depth_reduction': depth_reduction,
                    'severity': 'medium'
                })
        
        return anomalies


class RealTimeOrderBookVisualizer:
    """Real-time order book visualization with advanced features"""
    
    def __init__(self, max_history: int = 1000):
        self.logger = logging.getLogger(__name__)
        self.max_history = max_history
        self.order_books: Dict[str, deque] = {}
        self.subscribers: Dict[str, List[str]] = {}  # symbol -> list of session_ids
        self.analyzer = OrderBookAnalyzer()
        
        if FLASK_AVAILABLE:
            self.app = Flask(__name__)
            self.socketio = SocketIO(self.app, cors_allowed_origins="*")
            self._setup_routes()
        else:
            self.app = None
            self.socketio = None
    
    def _setup_routes(self):
        """Setup Flask routes for order book visualization"""
        
        @self.app.route('/orderbook/<symbol>')
        def orderbook_page(symbol):
            """Order book visualization page"""
            return render_template('orderbook.html', symbol=symbol)
        
        @self.app.route('/api/orderbook/<symbol>/snapshot')
        def get_orderbook_snapshot(symbol):
            """Get current order book snapshot"""
            if symbol in self.order_books and self.order_books[symbol]:
                latest = self.order_books[symbol][-1]
                return jsonify({
                    'symbol': latest.symbol,
                    'bids': [{'price': level.price, 'quantity': level.quantity, 'orders': level.orders} 
                            for level in latest.bids],
                    'asks': [{'price': level.price, 'quantity': level.quantity, 'orders': level.orders} 
                            for level in latest.asks],
                    'timestamp': latest.timestamp.isoformat(),
                    'spread': latest.spread,
                    'mid_price': latest.mid_price
                })
            else:
                return jsonify({'error': 'No data available'}), 404
        
        @self.app.route('/api/orderbook/<symbol>/metrics')
        def get_orderbook_metrics(symbol):
            """Get order book metrics"""
            if symbol in self.order_books and self.order_books[symbol]:
                latest = self.order_books[symbol][-1]
                metrics = self.analyzer.calculate_metrics(latest)
                return jsonify({
                    'symbol': metrics.symbol,
                    'timestamp': metrics.timestamp.isoformat(),
                    'spread': metrics.spread,
                    'spread_bps': metrics.spread_bps,
                    'mid_price': metrics.mid_price,
                    'bid_depth': metrics.bid_depth,
                    'ask_depth': metrics.ask_depth,
                    'imbalance': metrics.imbalance,
                    'weighted_mid': metrics.weighted_mid,
                    'microprice': metrics.microprice
                })
            else:
                return jsonify({'error': 'No data available'}), 404
        
        @self.socketio.on('subscribe_orderbook')
        def handle_subscribe(data):
            """Handle order book subscription"""
            symbol = data.get('symbol')
            if symbol:
                if symbol not in self.subscribers:
                    self.subscribers[symbol] = []
                
                if request.sid not in self.subscribers[symbol]:
                    self.subscribers[symbol].append(request.sid)
                    join_room(f"orderbook_{symbol}")
                    
                    # Send current snapshot if available
                    if symbol in self.order_books and self.order_books[symbol]:
                        latest = self.order_books[symbol][-1]
                        emit('orderbook_snapshot', {
                            'symbol': latest.symbol,
                            'bids': [{'price': level.price, 'quantity': level.quantity} 
                                    for level in latest.bids[:20]],
                            'asks': [{'price': level.price, 'quantity': level.quantity} 
                                    for level in latest.asks[:20]],
                            'timestamp': latest.timestamp.isoformat(),
                            'spread': latest.spread,
                            'mid_price': latest.mid_price
                        })
        
        @self.socketio.on('unsubscribe_orderbook')
        def handle_unsubscribe(data):
            """Handle order book unsubscription"""
            symbol = data.get('symbol')
            if symbol and symbol in self.subscribers:
                if request.sid in self.subscribers[symbol]:
                    self.subscribers[symbol].remove(request.sid)
                    leave_room(f"orderbook_{symbol}")
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnect"""
            for symbol, sids in self.subscribers.items():
                if request.sid in sids:
                    sids.remove(request.sid)
    
    def update_order_book(self, symbol: str, bids: List[Dict[str, float]], 
                         asks: List[Dict[str, float]]):
        """Update order book data"""
        # Convert to OrderBookLevel objects
        bid_levels = [OrderBookLevel(price=bid['price'], quantity=bid['quantity'], 
                                   orders=bid.get('orders', 1)) for bid in bids]
        ask_levels = [OrderBookLevel(price=ask['price'], quantity=ask['quantity'],
                                   orders=ask.get('orders', 1)) for ask in asks]
        
        # Sort levels
        bid_levels.sort(key=lambda x: x.price, reverse=True)
        ask_levels.sort(key=lambda x: x.price)
        
        # Create snapshot
        snapshot = OrderBookSnapshot(
            symbol=symbol,
            bids=bid_levels,
            asks=ask_levels,
            timestamp=datetime.now()
        )
        
        # Store in history
        if symbol not in self.order_books:
            self.order_books[symbol] = deque(maxlen=self.max_history)
        
        self.order_books[symbol].append(snapshot)
        
        # Broadcast to subscribers
        if self.socketio and symbol in self.subscribers:
            self.socketio.emit('orderbook_update', {
                'symbol': symbol,
                'bids': [{'price': level.price, 'quantity': level.quantity} 
                        for level in bid_levels[:20]],
                'asks': [{'price': level.price, 'quantity': level.quantity} 
                        for level in ask_levels[:20]],
                'timestamp': snapshot.timestamp.isoformat(),
                'spread': snapshot.spread,
                'mid_price': snapshot.mid_price
            }, room=f"orderbook_{symbol}")
    
    def get_depth_chart_html(self, symbol: str, container_id: str) -> str:
        """Generate HTML for order book depth chart"""
        if not PLOTLY_AVAILABLE:
            return f"<div id='{container_id}'>Plotly not available for depth chart</div>"
        
        html = f"""
        <div id="{container_id}" class="depth-chart-container">
            <div id="{container_id}_chart"></div>
        </div>
        
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <script>
        function updateDepthChart_{container_id}(data) {{
            const bids = data.bids || [];
            const asks = data.asks || [];
            
            // Calculate cumulative quantities
            let bidCumulative = 0;
            const bidData = bids.map(level => {{
                bidCumulative += level.quantity;
                return {{
                    x: level.price,
                    y: bidCumulative,
                    quantity: level.quantity
                }};
            }});
            
            let askCumulative = 0;
            const askData = asks.map(level => {{
                askCumulative += level.quantity;
                return {{
                    x: level.price,
                    y: askCumulative,
                    quantity: level.quantity
                }};
            }});
            
            const traces = [
                {{
                    x: bidData.map(d => d.x),
                    y: bidData.map(d => d.y),
                    type: 'scatter',
                    mode: 'lines',
                    fill: 'tozeroy',
                    name: 'Bids',
                    line: {{ color: '#00ff00', width: 2 }},
                    fillcolor: 'rgba(0, 255, 0, 0.1)',
                    hovertemplate: 'Price: $%{{x}}<br>Cumulative: %{{y}}<extra></extra>'
                }},
                {{
                    x: askData.map(d => d.x),
                    y: askData.map(d => d.y),
                    type: 'scatter',
                    mode: 'lines',
                    fill: 'tozeroy',
                    name: 'Asks',
                    line: {{ color: '#ff0000', width: 2 }},
                    fillcolor: 'rgba(255, 0, 0, 0.1)',
                    hovertemplate: 'Price: $%{{x}}<br>Cumulative: %{{y}}<extra></extra>'
                }}
            ];
            
            const layout = {{
                title: `Order Book Depth - ${{data.symbol}}`,
                xaxis: {{
                    title: 'Price ($)',
                    gridcolor: '#333'
                }},
                yaxis: {{
                    title: 'Cumulative Quantity',
                    gridcolor: '#333'
                }},
                plot_bgcolor: '#1a1a1a',
                paper_bgcolor: '#1a1a1a',
                font: {{ color: '#fff' }},
                showlegend: true,
                hovermode: 'x unified'
            }};
            
            Plotly.newPlot('{container_id}_chart', traces, layout, {{responsive: true}});
        }}
        
        // Initialize with sample data
        const sampleData = {{
            symbol: '{symbol}',
            bids: Array.from({{length: 20}}, (_, i) => ({{
                price: 150.00 - (i * 0.01),
                quantity: Math.floor(Math.random() * 1000) + 100
            }})),
            asks: Array.from({{length: 20}}, (_, i) => ({{
                price: 150.01 + (i * 0.01),
                quantity: Math.floor(Math.random() * 1000) + 100
            }}))
        }};
        
        updateDepthChart_{container_id}(sampleData);
        
        // Update every 2 seconds with new sample data
        setInterval(() => {{
            const newData = {{
                symbol: '{symbol}',
                bids: Array.from({{length: 20}}, (_, i) => ({{
                    price: 150.00 - (i * 0.01) + (Math.random() - 0.5) * 0.02,
                    quantity: Math.floor(Math.random() * 1000) + 100
                }})),
                asks: Array.from({{length: 20}}, (_, i) => ({{
                    price: 150.01 + (i * 0.01) + (Math.random() - 0.5) * 0.02,
                    quantity: Math.floor(Math.random() * 1000) + 100
                }}))
            }};
            updateDepthChart_{container_id}(newData);
        }}, 2000);
        </script>
        """
        
        return html
    
    def get_heatmap_html(self, symbol: str, container_id: str) -> str:
        """Generate HTML for order book heatmap visualization"""
        html = f"""
        <div id="{container_id}" class="orderbook-heatmap-container">
            <div class="heatmap-header">
                <h3>Order Book Heatmap - {symbol}</h3>
                <div class="heatmap-controls">
                    <label>Time Range: 
                        <select id="timeRange_{container_id}">
                            <option value="1m">1 Minute</option>
                            <option value="5m" selected>5 Minutes</option>
                            <option value="15m">15 Minutes</option>
                            <option value="1h">1 Hour</option>
                        </select>
                    </label>
                </div>
            </div>
            <canvas id="{container_id}_canvas" width="800" height="400"></canvas>
        </div>
        
        <style>
        .orderbook-heatmap-container {{
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 15px;
            color: #fff;
        }}
        
        .heatmap-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        
        .heatmap-header h3 {{
            margin: 0;
            color: #4a90e2;
        }}
        
        .heatmap-controls select {{
            background: #333;
            color: #fff;
            border: 1px solid #555;
            padding: 5px;
            border-radius: 4px;
        }}
        
        #{container_id}_canvas {{
            border: 1px solid #333;
            border-radius: 4px;
        }}
        </style>
        
        <script>
        class OrderBookHeatmap {{
            constructor(canvasId, symbol) {{
                this.canvas = document.getElementById(canvasId);
                this.ctx = this.canvas.getContext('2d');
                this.symbol = symbol;
                this.data = [];
                this.priceRange = {{ min: 149, max: 151 }};
                this.timeRange = 300; // 5 minutes in seconds
                
                this.init();
            }}
            
            init() {{
                this.canvas.width = 800;
                this.canvas.height = 400;
                this.generateSampleData();
                this.render();
                
                // Update every second
                setInterval(() => {{
                    this.addNewDataPoint();
                    this.render();
                }}, 1000);
            }}
            
            generateSampleData() {{
                const now = Date.now();
                for (let i = 0; i < this.timeRange; i++) {{
                    const timestamp = now - (this.timeRange - i) * 1000;
                    const dataPoint = {{
                        timestamp: timestamp,
                        bids: this.generateLevels(149.99, -0.01, 20),
                        asks: this.generateLevels(150.01, 0.01, 20)
                    }};
                    this.data.push(dataPoint);
                }}
            }}
            
            generateLevels(startPrice, increment, count) {{
                const levels = [];
                for (let i = 0; i < count; i++) {{
                    levels.push({{
                        price: startPrice + (i * increment),
                        quantity: Math.floor(Math.random() * 1000) + 100
                    }});
                }}
                return levels;
            }}
            
            addNewDataPoint() {{
                const timestamp = Date.now();
                const dataPoint = {{
                    timestamp: timestamp,
                    bids: this.generateLevels(149.99, -0.01, 20),
                    asks: this.generateLevels(150.01, 0.01, 20)
                }};
                
                this.data.push(dataPoint);
                
                // Remove old data
                const cutoff = timestamp - (this.timeRange * 1000);
                this.data = this.data.filter(d => d.timestamp > cutoff);
            }}
            
            render() {{
                this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
                
                if (this.data.length === 0) return;
                
                const width = this.canvas.width;
                const height = this.canvas.height;
                const timeStep = width / this.timeRange;
                const priceStep = height / ((this.priceRange.max - this.priceRange.min) * 100);
                
                // Create heatmap data
                const heatmapData = new Map();
                
                this.data.forEach((dataPoint, timeIndex) => {{
                    const x = Math.floor(timeIndex * timeStep);
                    
                    // Process bids
                    dataPoint.bids.forEach(bid => {{
                        const y = Math.floor((this.priceRange.max - bid.price) * 100 * priceStep);
                        const key = `${{x}},${{y}}`;
                        heatmapData.set(key, (heatmapData.get(key) || 0) + bid.quantity);
                    }});
                    
                    // Process asks
                    dataPoint.asks.forEach(ask => {{
                        const y = Math.floor((this.priceRange.max - ask.price) * 100 * priceStep);
                        const key = `${{x}},${{y}}`;
                        heatmapData.set(key, (heatmapData.get(key) || 0) + ask.quantity);
                    }});
                }});
                
                // Find max intensity for normalization
                const maxIntensity = Math.max(...heatmapData.values());
                
                // Draw heatmap
                heatmapData.forEach((intensity, key) => {{
                    const [x, y] = key.split(',').map(Number);
                    const normalizedIntensity = intensity / maxIntensity;
                    
                    // Color based on intensity
                    const alpha = normalizedIntensity * 0.8;
                    this.ctx.fillStyle = `rgba(74, 144, 226, ${{alpha}})`;
                    this.ctx.fillRect(x, y, timeStep, priceStep);
                }});
                
                // Draw price levels
                this.ctx.strokeStyle = '#333';
                this.ctx.lineWidth = 1;
                for (let price = this.priceRange.min; price <= this.priceRange.max; price += 0.1) {{
                    const y = (this.priceRange.max - price) * 100 * priceStep;
                    this.ctx.beginPath();
                    this.ctx.moveTo(0, y);
                    this.ctx.lineTo(width, y);
                    this.ctx.stroke();
                }}
                
                // Draw time grid
                for (let t = 0; t < this.timeRange; t += 60) {{
                    const x = t * timeStep;
                    this.ctx.beginPath();
                    this.ctx.moveTo(x, 0);
                    this.ctx.lineTo(x, height);
                    this.ctx.stroke();
                }}
            }}
        }}
        
        // Initialize heatmap
        const heatmap_{container_id} = new OrderBookHeatmap('{container_id}_canvas', '{symbol}');
        </script>
        """
        
        return html
    
    def create_orderbook_template(self):
        """Create HTML template for order book page"""
        template_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Order Book - {{ symbol }}</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body {
            font-family: 'Courier New', monospace;
            background: #0a0a0a;
            color: #fff;
            margin: 0;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .header h1 {
            color: #4a90e2;
            margin: 0;
        }
        
        .orderbook-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .depth-chart-section {
            grid-column: 1 / -1;
            margin-bottom: 30px;
        }
        
        .heatmap-section {
            grid-column: 1 / -1;
        }
        
        .section-title {
            color: #4a90e2;
            font-size: 18px;
            margin-bottom: 15px;
            border-bottom: 1px solid #333;
            padding-bottom: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Real-Time Order Book</h1>
            <h2>{{ symbol }}</h2>
        </div>
        
        <div class="orderbook-grid">
            <div class="orderbook-table">
                <div class="section-title">Order Book Levels</div>
                <div id="orderbook-levels"></div>
            </div>
            
            <div class="metrics-panel">
                <div class="section-title">Metrics</div>
                <div id="orderbook-metrics"></div>
            </div>
        </div>
        
        <div class="depth-chart-section">
            <div class="section-title">Depth Chart</div>
            <div id="depth-chart"></div>
        </div>
        
        <div class="heatmap-section">
            <div class="section-title">Order Book Heatmap</div>
            <div id="orderbook-heatmap"></div>
        </div>
    </div>
    
    <script>
        const socket = io();
        const symbol = '{{ symbol }}';
        
        // Subscribe to order book updates
        socket.emit('subscribe_orderbook', { symbol: symbol });
        
        // Handle order book updates
        socket.on('orderbook_update', function(data) {
            updateOrderBookLevels(data);
            updateMetrics(data);
        });
        
        function updateOrderBookLevels(data) {
            // Implementation for updating order book levels table
            console.log('Order book update:', data);
        }
        
        function updateMetrics(data) {
            // Implementation for updating metrics panel
            console.log('Metrics update:', data);
        }
    </script>
</body>
</html>
        """
        
        # Create templates directory
        from pathlib import Path
        templates_dir = Path("nautilus_trader_engine/visualization/templates")
        templates_dir.mkdir(parents=True, exist_ok=True)
        
        with open(templates_dir / "orderbook.html", "w") as f:
            f.write(template_html)
    
    def run(self, host: str = "localhost", port: int = 8083):
        """Run the order book visualization server"""
        if self.app and self.socketio:
            self.create_orderbook_template()
            self.logger.info(f"Starting order book visualization server on {host}:{port}")
            self.socketio.run(self.app, host=host, port=port, debug=False)
        else:
            self.logger.error("Cannot start server - Flask not available")


# Sample data generator for testing
class OrderBookDataGenerator:
    """Generate realistic order book data for testing"""
    
    def __init__(self, base_price: float = 150.0):
        self.base_price = base_price
        self.current_price = base_price
        self.sequence = 0
    
    def generate_snapshot(self, symbol: str, levels: int = 20) -> OrderBookSnapshot:
        """Generate realistic order book snapshot"""
        # Add some price movement
        self.current_price += np.random.normal(0, 0.01)
        
        # Generate bid levels
        bids = []
        for i in range(levels):
            price = self.current_price - 0.01 - (i * 0.01)
            quantity = np.random.exponential(500) + 100
            orders = np.random.randint(1, 10)
            bids.append(OrderBookLevel(price=price, quantity=quantity, orders=orders))
        
        # Generate ask levels
        asks = []
        for i in range(levels):
            price = self.current_price + 0.01 + (i * 0.01)
            quantity = np.random.exponential(500) + 100
            orders = np.random.randint(1, 10)
            asks.append(OrderBookLevel(price=price, quantity=quantity, orders=orders))
        
        self.sequence += 1
        
        return OrderBookSnapshot(
            symbol=symbol,
            bids=bids,
            asks=asks,
            timestamp=datetime.now(),
            sequence=self.sequence
        )


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Create order book visualizer
    visualizer = RealTimeOrderBookVisualizer()
    
    # Generate sample data
    generator = OrderBookDataGenerator()
    
    # Simulate order book updates
    async def simulate_updates():
        while True:
            snapshot = generator.generate_snapshot("AAPL")
            
            # Convert to dict format for update
            bids = [{'price': level.price, 'quantity': level.quantity, 'orders': level.orders} 
                   for level in snapshot.bids]
            asks = [{'price': level.price, 'quantity': level.quantity, 'orders': level.orders} 
                   for level in snapshot.asks]
            
            visualizer.update_order_book("AAPL", bids, asks)
            await asyncio.sleep(0.1)  # Update every 100ms
    
    # Test HTML generation
    depth_chart_html = visualizer.get_depth_chart_html("AAPL", "aapl_depth")
    heatmap_html = visualizer.get_heatmap_html("AAPL", "aapl_heatmap")
    
    print("Order book visualizer created successfully")
    print(f"Depth chart HTML length: {len(depth_chart_html)}")
    print(f"Heatmap HTML length: {len(heatmap_html)}")
    
    # Start the server (uncomment to run)
    # visualizer.run()