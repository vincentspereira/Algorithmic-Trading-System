"""
GraphQL API Implementation
Provides comprehensive GraphQL API with real-time subscriptions, query optimization,
caching, and interactive GraphQL playground for flexible data queries.
"""
import logging
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable, AsyncGenerator
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
import time
from collections import defaultdict

try:
    import graphene
    from graphene import ObjectType, String, Int, Float, Boolean, List as GrapheneList
    from graphene import Field, Argument, Schema, Mutation
    from graphene.relay import Node, Connection, ConnectionField
    from flask import Flask, request, jsonify
    import redis
    
    # Try to import AsyncioExecutor with fallback
    try:
        from graphql.execution.executors.asyncio import AsyncioExecutor
    except ImportError:
        AsyncioExecutor = None
    
    # Try to import flask_graphql with fallback
    try:
        from flask_graphql import GraphQLView
    except ImportError:
        # Create a mock GraphQLView for compatibility
        class GraphQLView:
            @staticmethod
            def as_view(*args, **kwargs):
                def view():
                    return jsonify({"error": "GraphQL view not available"})
                return view
    
    GRAPHQL_AVAILABLE = True
except ImportError:
    graphene = None
    ObjectType = None
    String = Int = Float = Boolean = GrapheneList = None
    Field = Argument = Schema = Mutation = None
    Node = Connection = ConnectionField = None
    AsyncioExecutor = None
    Flask = None
    GraphQLView = None
    redis = None
    GRAPHQL_AVAILABLE = False

class QueryComplexity(Enum):
    """Query complexity levels"""
    LOW = 1
    MEDIUM = 5
    HIGH = 10
    VERY_HIGH = 20

@dataclass
class GraphQLMetrics:
    """GraphQL query metrics"""
    query_id: str
    query: str
    variables: Dict[str, Any]
    execution_time: float
    complexity_score: int
    field_count: int
    depth: int
    user_id: Optional[str]
    timestamp: datetime
    errors: List[str] = field(default_factory=list)

class GraphQLCache:
    """GraphQL query result caching system"""
    
    def __init__(self, redis_client=None, default_ttl: int = 300):
        self.redis_client = redis_client
        self.default_ttl = default_ttl
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.query_mapping: Dict[str, str] = {}  # Maps cache key to original query
        self.logger = logging.getLogger(__name__)
    
    def _generate_cache_key(self, query: str, variables: Dict[str, Any] = None) -> str:
        """Generate cache key for query and variables"""
        import hashlib
        import re
        
        # Normalize query by removing all whitespace and standardizing format
        # Remove all whitespace first
        normalized_query = re.sub(r'\s+', '', query.strip())
        
        # Include variables in key
        variables_str = json.dumps(variables or {}, sort_keys=True)
        
        # Create hash
        key_data = f"{normalized_query}:{variables_str}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def get(self, query: str, variables: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Get cached query result"""
        cache_key = self._generate_cache_key(query, variables)
        
        try:
            if self.redis_client:
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    return json.loads(cached_data)
            else:
                # Memory cache
                cached_entry = self.memory_cache.get(cache_key)
                if cached_entry and cached_entry['expires_at'] > time.time():
                    return cached_entry['data']
                elif cached_entry:
                    # Remove expired entry
                    del self.memory_cache[cache_key]
            
            return None
        
        except Exception as e:
            self.logger.error(f"Error getting cached result: {e}")
            return None
    
    async def set(self, query: str, variables: Dict[str, Any], result: Dict[str, Any], ttl: int = None) -> bool:
        """Cache query result"""
        cache_key = self._generate_cache_key(query, variables)
        ttl = ttl or self.default_ttl
        
        try:
            # Store query mapping for pattern invalidation
            self.query_mapping[cache_key] = query
            
            if self.redis_client:
                await self.redis_client.setex(
                    cache_key, 
                    ttl, 
                    json.dumps(result, default=str)
                )
            else:
                # Memory cache
                self.memory_cache[cache_key] = {
                    'data': result,
                    'expires_at': time.time() + ttl
                }
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error caching result: {e}")
            return False
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern"""
        try:
            keys_to_delete = []
            
            # Find keys where the original query contains the pattern
            for cache_key, original_query in self.query_mapping.items():
                if pattern in original_query:
                    keys_to_delete.append(cache_key)
            
            # Delete from cache
            deleted_count = 0
            for cache_key in keys_to_delete:
                if self.redis_client:
                    deleted = await self.redis_client.delete(cache_key)
                    deleted_count += deleted
                else:
                    if cache_key in self.memory_cache:
                        del self.memory_cache[cache_key]
                        deleted_count += 1
                
                # Remove from query mapping
                if cache_key in self.query_mapping:
                    del self.query_mapping[cache_key]
            
            return deleted_count
        
        except Exception as e:
            self.logger.error(f"Error invalidating cache pattern: {e}")
            return 0

class QueryComplexityAnalyzer:
    """Analyze GraphQL query complexity"""
    
    def __init__(self, max_complexity: int = 100, max_depth: int = 10):
        self.max_complexity = max_complexity
        self.max_depth = max_depth
        self.logger = logging.getLogger(__name__)
    
    def analyze_query(self, query_ast) -> Dict[str, Any]:
        """Analyze query complexity and depth"""
        try:
            complexity = self._calculate_complexity(query_ast)
            depth = self._calculate_depth(query_ast)
            field_count = self._count_fields(query_ast)
            
            return {
                'complexity': complexity,
                'depth': depth,
                'field_count': field_count,
                'is_valid': complexity <= self.max_complexity and depth <= self.max_depth
            }
        
        except Exception as e:
            self.logger.error(f"Error analyzing query: {e}")
            return {
                'complexity': 0,
                'depth': 0,
                'field_count': 0,
                'is_valid': True
            }
    
    def _calculate_complexity(self, node, multiplier: int = 1) -> int:
        """Calculate query complexity score"""
        # Handle different node types
        if hasattr(node, 'definitions'):
            # Document node - start with definitions
            complexity = 0
            for definition in node.definitions:
                complexity += self._calculate_complexity(definition, multiplier)
            return complexity
        
        if not hasattr(node, 'selection_set') or not node.selection_set:
            return 1
        
        complexity = 0
        for selection in node.selection_set.selections:
            if hasattr(selection, 'name'):
                field_complexity = self._get_field_complexity(selection.name.value)
                child_complexity = self._calculate_complexity(selection, multiplier)
                complexity += field_complexity + child_complexity
            else:
                complexity += self._calculate_complexity(selection, multiplier)
        
        return complexity
    
    def _calculate_depth(self, node, current_depth: int = 0) -> int:
        """Calculate query depth"""
        # Handle different node types
        if hasattr(node, 'definitions'):
            # Document node - start with definitions
            max_depth = 0
            for definition in node.definitions:
                depth = self._calculate_depth(definition, 0)
                max_depth = max(max_depth, depth)
            return max_depth
        
        if not hasattr(node, 'selection_set') or not node.selection_set:
            return current_depth
        
        # If we have selections, increment depth
        max_depth = current_depth + 1
        for selection in node.selection_set.selections:
            depth = self._calculate_depth(selection, current_depth + 1)
            max_depth = max(max_depth, depth)
        
        return max_depth
    
    def _count_fields(self, node) -> int:
        """Count total fields in query"""
        # Handle different node types
        if hasattr(node, 'definitions'):
            # Document node - start with definitions
            count = 0
            for definition in node.definitions:
                count += self._count_fields(definition)
            return count
        
        if not hasattr(node, 'selection_set') or not node.selection_set:
            return 0
        
        count = len(node.selection_set.selections)
        for selection in node.selection_set.selections:
            count += self._count_fields(selection)
        
        return count
    
    def _get_field_complexity(self, field_name: str) -> int:
        """Get complexity score for specific field"""
        # Define field complexity mapping
        complexity_map = {
            # Simple fields
            'id': 1,
            'name': 1,
            'status': 1,
            'timestamp': 1,
            
            # Medium complexity fields
            'orders': 5,
            'positions': 5,
            'trades': 5,
            'portfolio': 5,
            
            # High complexity fields
            'analytics': 10,
            'backtest': 15,
            'optimization': 20,
            
            # Very high complexity fields
            'marketData': 25,
            'historicalData': 30
        }
        
        return complexity_map.get(field_name, 3)  # Default complexity

# GraphQL Types
if GRAPHQL_AVAILABLE:
    
    class OrderType(ObjectType):
        """GraphQL Order type"""
        id = String(required=True)
        symbol = String(required=True)
        side = String(required=True)
        quantity = Float(required=True)
        price = Float()
        order_type = String(required=True)
        status = String(required=True)
        created_at = String(required=True)
        updated_at = String()
        filled_quantity = Float()
        average_price = Float()
        
        @staticmethod
        def resolve_created_at(root, info):
            return root.get('created_at', datetime.now().isoformat())
    
    class PositionType(ObjectType):
        """GraphQL Position type"""
        symbol = String(required=True)
        quantity = Float(required=True)
        average_price = Float(required=True)
        market_price = Float(required=True)
        market_value = Float(required=True)
        unrealized_pnl = Float(required=True)
        realized_pnl = Float()
        percentage_change = Float()
        
        @staticmethod
        def resolve_market_value(root, info):
            return root.get('quantity', 0) * root.get('market_price', 0)
        
        @staticmethod
        def resolve_unrealized_pnl(root, info):
            quantity = root.get('quantity', 0)
            market_price = root.get('market_price', 0)
            avg_price = root.get('average_price', 0)
            return quantity * (market_price - avg_price)
    
    class TradeType(ObjectType):
        """GraphQL Trade type"""
        id = String(required=True)
        order_id = String()
        symbol = String(required=True)
        side = String(required=True)
        quantity = Float(required=True)
        price = Float(required=True)
        commission = Float()
        timestamp = String(required=True)
        pnl = Float()
        
        @staticmethod
        def resolve_timestamp(root, info):
            return root.get('timestamp', datetime.now().isoformat())
    
    class PortfolioType(ObjectType):
        """GraphQL Portfolio type"""
        total_value = Float(required=True)
        cash_balance = Float(required=True)
        positions = GrapheneList(PositionType)
        total_pnl = Float()
        daily_pnl = Float()
        positions_count = Int()
        
        @staticmethod
        def resolve_positions_count(root, info):
            return len(root.get('positions', []))
        
        @staticmethod
        def resolve_total_pnl(root, info):
            positions = root.get('positions', [])
            return sum(pos.get('unrealized_pnl', 0) for pos in positions)
    
    class MarketDataType(ObjectType):
        """GraphQL Market Data type"""
        symbol = String(required=True)
        last_price = Float(required=True)
        bid = Float()
        ask = Float()
        volume = Int()
        change = Float()
        change_percent = Float()
        high = Float()
        low = Float()
        timestamp = String(required=True)
        
        @staticmethod
        def resolve_change_percent(root, info):
            last_price = root.get('last_price', 0)
            change = root.get('change', 0)
            if last_price > 0:
                return (change / (last_price - change)) * 100
            return 0
    
    class AnalyticsType(ObjectType):
        """GraphQL Analytics type"""
        total_trades = Int()
        win_rate = Float()
        profit_factor = Float()
        sharpe_ratio = Float()
        max_drawdown = Float()
        average_trade_pnl = Float()
        best_trade = Float()
        worst_trade = Float()
        
        @staticmethod
        def resolve_win_rate(root, info):
            winning_trades = root.get('winning_trades', 0)
            total_trades = root.get('total_trades', 1)
            return (winning_trades / total_trades) * 100 if total_trades > 0 else 0

else:
    # Dummy classes when GraphQL is not available
    OrderType = PositionType = TradeType = PortfolioType = None
    MarketDataType = AnalyticsType = None

# GraphQL Queries, Mutations, and Subscriptions
if GRAPHQL_AVAILABLE:
    
    class Query(ObjectType):
        """GraphQL Query root"""
        
        # Order queries
        order = Field(OrderType, id=Argument(String, required=True))
        orders = GrapheneList(
            OrderType,
            symbol=Argument(String),
            status=Argument(String),
            limit=Argument(Int, default_value=50),
            offset=Argument(Int, default_value=0)
        )
        
        # Position queries
        position = Field(PositionType, symbol=Argument(String, required=True))
        positions = GrapheneList(PositionType)
        
        # Trade queries
        trade = Field(TradeType, id=Argument(String, required=True))
        trades = GrapheneList(
            TradeType,
            symbol=Argument(String),
            start_date=Argument(String),
            end_date=Argument(String),
            limit=Argument(Int, default_value=100),
            offset=Argument(Int, default_value=0)
        )
        
        # Portfolio queries
        portfolio = Field(PortfolioType)
        
        # Market data queries
        market_data = Field(MarketDataType, symbol=Argument(String, required=True))
        market_data_list = GrapheneList(
            MarketDataType,
            symbols=Argument(GrapheneList(String), required=True)
        )
        
        # Analytics queries
        analytics = Field(
            AnalyticsType,
            start_date=Argument(String),
            end_date=Argument(String)
        )
        
        # Resolvers
        def resolve_order(self, info, id):
            """Resolve single order by ID"""
            # Simulate database lookup
            return {
                'id': id,
                'symbol': 'AAPL',
                'side': 'buy',
                'quantity': 100,
                'price': 150.25,
                'order_type': 'limit',
                'status': 'filled',
                'created_at': datetime.now().isoformat()
            }
        
        def resolve_orders(self, info, symbol=None, status=None, limit=50, offset=0):
            """Resolve orders with filtering"""
            # Simulate database query
            orders = []
            for i in range(limit):
                orders.append({
                    'id': f'order_{i + offset}',
                    'symbol': symbol or f'STOCK{i % 5}',
                    'side': 'buy' if i % 2 == 0 else 'sell',
                    'quantity': 100 + (i * 10),
                    'price': 100 + (i * 0.5),
                    'order_type': 'limit',
                    'status': status or ('filled' if i % 3 == 0 else 'pending'),
                    'created_at': (datetime.now() - timedelta(hours=i)).isoformat()
                })
            return orders
        
        def resolve_position(self, info, symbol):
            """Resolve single position by symbol"""
            return {
                'symbol': symbol,
                'quantity': 100,
                'average_price': 150.0,
                'market_price': 155.0,
                'market_value': 15500.0,
                'unrealized_pnl': 500.0,
                'percentage_change': 3.33
            }
        
        def resolve_positions(self, info):
            """Resolve all positions"""
            symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']
            positions = []
            for i, symbol in enumerate(symbols):
                positions.append({
                    'symbol': symbol,
                    'quantity': 100 + (i * 50),
                    'average_price': 100 + (i * 20),
                    'market_price': 105 + (i * 20),
                    'market_value': (100 + i * 50) * (105 + i * 20),
                    'unrealized_pnl': (100 + i * 50) * 5,
                    'percentage_change': 2.5 + i
                })
            return positions
        
        def resolve_trades(self, info, symbol=None, start_date=None, end_date=None, limit=100, offset=0):
            """Resolve trades with filtering"""
            trades = []
            for i in range(limit):
                trades.append({
                    'id': f'trade_{i + offset}',
                    'order_id': f'order_{i + offset}',
                    'symbol': symbol or f'STOCK{i % 5}',
                    'side': 'buy' if i % 2 == 0 else 'sell',
                    'quantity': 50 + (i * 5),
                    'price': 100 + (i * 0.25),
                    'commission': 1.0,
                    'timestamp': (datetime.now() - timedelta(minutes=i * 30)).isoformat(),
                    'pnl': (-50 + i * 10) if i % 3 == 0 else 0
                })
            return trades
        
        def resolve_portfolio(self, info):
            """Resolve portfolio summary"""
            # Generate positions directly instead of calling self.resolve_positions
            symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']
            positions = []
            for i, symbol in enumerate(symbols):
                positions.append({
                    'symbol': symbol,
                    'quantity': 100 + (i * 50),
                    'average_price': 100 + (i * 20),
                    'market_price': 105 + (i * 20),
                    'market_value': (100 + i * 50) * (105 + i * 20),
                    'unrealized_pnl': (100 + i * 50) * 5,
                    'percentage_change': 2.5 + i
                })
            
            total_value = sum(pos['market_value'] for pos in positions)
            total_pnl = sum(pos['unrealized_pnl'] for pos in positions)
            
            return {
                'total_value': total_value,
                'cash_balance': 50000.0,
                'positions': positions,
                'total_pnl': total_pnl,
                'daily_pnl': total_pnl * 0.1,  # Simulate daily P&L
                'positions_count': len(positions)
            }
        
        def resolve_market_data(self, info, symbol):
            """Resolve market data for symbol"""
            base_price = 100 + hash(symbol) % 100
            change = (hash(symbol) % 20) - 10
            
            return {
                'symbol': symbol,
                'last_price': base_price,
                'bid': base_price - 0.01,
                'ask': base_price + 0.01,
                'volume': 10000 + hash(symbol) % 50000,
                'change': change,
                'change_percent': (change / base_price) * 100,
                'high': base_price + 5,
                'low': base_price - 5,
                'timestamp': datetime.now().isoformat()
            }
        
        def resolve_market_data_list(self, info, symbols):
            """Resolve market data for multiple symbols"""
            market_data = []
            for symbol in symbols:
                data = self.resolve_market_data(info, symbol)
                market_data.append(data)
            return market_data
        
        def resolve_analytics(self, info, start_date=None, end_date=None):
            """Resolve trading analytics"""
            return {
                'total_trades': 150,
                'winning_trades': 90,
                'total_trades': 150,
                'win_rate': 60.0,
                'profit_factor': 1.5,
                'sharpe_ratio': 1.2,
                'max_drawdown': -5.5,
                'average_trade_pnl': 125.50,
                'best_trade': 2500.0,
                'worst_trade': -1200.0
            }
    
    class CreateOrder(Mutation):
        """Create new order mutation"""
        
        class Arguments:
            symbol = String(required=True)
            side = String(required=True)
            quantity = Float(required=True)
            order_type = String(required=True)
            price = Float()
            stop_price = Float()
        
        order = Field(OrderType)
        success = Boolean()
        message = String()
        
        def mutate(self, info, symbol, side, quantity, order_type, price=None, stop_price=None):
            """Create new order"""
            try:
                # Validate input
                if side not in ['buy', 'sell']:
                    return CreateOrder(success=False, message="Invalid side. Must be 'buy' or 'sell'")
                
                if quantity <= 0:
                    return CreateOrder(success=False, message="Quantity must be greater than 0")
                
                if order_type not in ['market', 'limit', 'stop', 'stop_limit']:
                    return CreateOrder(success=False, message="Invalid order type")
                
                # Create order
                order = {
                    'id': str(uuid.uuid4()),
                    'symbol': symbol,
                    'side': side,
                    'quantity': quantity,
                    'price': price,
                    'order_type': order_type,
                    'status': 'pending',
                    'created_at': datetime.now().isoformat()
                }
                
                # Simulate order processing (removed async sleep)
                import time
                time.sleep(0.01)  # Very short delay for realism
                
                return CreateOrder(
                    order=order,
                    success=True,
                    message=f"Order created successfully for {quantity} {symbol}"
                )
            
            except Exception as e:
                return CreateOrder(
                    success=False,
                    message=f"Error creating order: {str(e)}"
                )
    
    class CancelOrder(Mutation):
        """Cancel order mutation"""
        
        class Arguments:
            order_id = String(required=True)
        
        success = Boolean()
        message = String()
        
        def mutate(self, info, order_id):
            """Cancel order"""
            try:
                # Simulate order cancellation (removed async sleep)
                import time
                time.sleep(0.01)  # Very short delay for realism
                
                return CancelOrder(
                    success=True,
                    message=f"Order {order_id} cancelled successfully"
                )
            
            except Exception as e:
                return CancelOrder(
                    success=False,
                    message=f"Error cancelling order: {str(e)}"
                )
    
    class Mutation(ObjectType):
        """GraphQL Mutation root"""
        create_order = CreateOrder.Field()
        cancel_order = CancelOrder.Field()
    
    class Subscription(ObjectType):
        """GraphQL Subscription root"""
        
        # Real-time subscriptions
        order_updates = Field(OrderType, symbol=Argument(String))
        position_updates = Field(PositionType, symbol=Argument(String))
        market_data_updates = Field(MarketDataType, symbol=Argument(String, required=True))
        portfolio_updates = Field(PortfolioType)
        
        async def resolve_order_updates(self, info, symbol=None):
            """Subscribe to order updates"""
            while True:
                # Simulate order update
                await asyncio.sleep(5)
                yield {
                    'id': str(uuid.uuid4()),
                    'symbol': symbol or 'AAPL',
                    'side': 'buy',
                    'quantity': 100,
                    'price': 150.0 + (time.time() % 10),
                    'order_type': 'limit',
                    'status': 'filled',
                    'created_at': datetime.now().isoformat()
                }
        
        async def resolve_position_updates(self, info, symbol=None):
            """Subscribe to position updates"""
            while True:
                await asyncio.sleep(10)
                base_price = 150.0 + (time.time() % 20)
                yield {
                    'symbol': symbol or 'AAPL',
                    'quantity': 100,
                    'average_price': 145.0,
                    'market_price': base_price,
                    'market_value': 100 * base_price,
                    'unrealized_pnl': 100 * (base_price - 145.0),
                    'percentage_change': ((base_price - 145.0) / 145.0) * 100
                }
        
        async def resolve_market_data_updates(self, info, symbol):
            """Subscribe to market data updates"""
            while True:
                await asyncio.sleep(1)  # Update every second
                base_price = 100 + hash(symbol + str(int(time.time()))) % 100
                change = (hash(symbol + str(int(time.time()))) % 20) - 10
                
                yield {
                    'symbol': symbol,
                    'last_price': base_price,
                    'bid': base_price - 0.01,
                    'ask': base_price + 0.01,
                    'volume': 10000 + hash(symbol) % 50000,
                    'change': change,
                    'change_percent': (change / base_price) * 100,
                    'high': base_price + 5,
                    'low': base_price - 5,
                    'timestamp': datetime.now().isoformat()
                }
        
        async def resolve_portfolio_updates(self, info):
            """Subscribe to portfolio updates"""
            while True:
                await asyncio.sleep(30)  # Update every 30 seconds
                total_value = 100000 + (time.time() % 10000)
                daily_pnl = (time.time() % 2000) - 1000
                
                yield {
                    'total_value': total_value,
                    'cash_balance': 50000.0,
                    'positions': [],  # Would include actual positions
                    'total_pnl': daily_pnl * 5,
                    'daily_pnl': daily_pnl,
                    'positions_count': 5
                }

else:
    # Dummy classes when GraphQL is not available
    Query = Mutation = Subscription = None

class GraphQLAPI:
    """GraphQL API implementation"""
    
    def __init__(self, app: Flask = None, redis_url: str = None):
        if not GRAPHQL_AVAILABLE:
            raise ImportError("GraphQL packages are required. Install with: pip install graphene flask-graphql")
        
        self.app = app or Flask(__name__)
        self.logger = logging.getLogger(__name__)
        
        # Initialize cache
        redis_client = redis.from_url(redis_url) if redis_url else None
        self.cache = GraphQLCache(redis_client)
        
        # Initialize complexity analyzer
        self.complexity_analyzer = QueryComplexityAnalyzer()
        
        # Metrics storage
        self.metrics: List[GraphQLMetrics] = []
        
        # Create GraphQL schema
        self.schema = Schema(
            query=Query,
            mutation=Mutation,
            subscription=Subscription
        )
        
        # Setup GraphQL endpoint
        self._setup_graphql_endpoint()
        
        # Setup GraphQL playground
        self._setup_playground()
    
    def _setup_graphql_endpoint(self):
        """Setup GraphQL endpoint"""
        
        def graphql_view():
            """Custom GraphQL view with caching and complexity analysis"""
            try:
                # Get request data
                data = request.get_json()
                query = data.get('query', '')
                variables = data.get('variables', {})
                operation_name = data.get('operationName')
                
                # Generate query ID for metrics
                query_id = str(uuid.uuid4())
                start_time = time.time()
                
                # Check cache first
                cached_result = asyncio.run(self.cache.get(query, variables))
                if cached_result:
                    self.logger.debug(f"Cache hit for query {query_id}")
                    return jsonify(cached_result)
                
                # Analyze query complexity
                try:
                    from graphql import parse
                    query_ast = parse(query)
                    complexity_info = self.complexity_analyzer.analyze_query(query_ast)
                    
                    if not complexity_info['is_valid']:
                        return jsonify({
                            'errors': [{
                                'message': f'Query too complex. Complexity: {complexity_info["complexity"]}, Max: {self.complexity_analyzer.max_complexity}',
                                'extensions': {
                                    'code': 'QUERY_TOO_COMPLEX',
                                    'complexity': complexity_info['complexity'],
                                    'depth': complexity_info['depth']
                                }
                            }]
                        }), 400
                
                except Exception as e:
                    self.logger.warning(f"Could not analyze query complexity: {e}")
                    complexity_info = {'complexity': 0, 'depth': 0, 'field_count': 0}
                
                # Execute query
                result = self.schema.execute(
                    query,
                    variables=variables,
                    operation_name=operation_name,
                    executor=AsyncioExecutor()
                )
                
                # Convert result to dict
                result_dict = {
                    'data': result.data,
                    'errors': [{'message': str(error)} for error in result.errors] if result.errors else None
                }
                
                # Cache successful results
                if not result.errors and result.data:
                    asyncio.run(self.cache.set(query, variables, result_dict))
                
                # Record metrics
                execution_time = time.time() - start_time
                metrics = GraphQLMetrics(
                    query_id=query_id,
                    query=query,
                    variables=variables,
                    execution_time=execution_time,
                    complexity_score=complexity_info['complexity'],
                    field_count=complexity_info['field_count'],
                    depth=complexity_info['depth'],
                    user_id=request.headers.get('X-User-ID'),
                    timestamp=datetime.now(),
                    errors=[str(error) for error in result.errors] if result.errors else []
                )
                
                self.metrics.append(metrics)
                
                # Keep only recent metrics (last 1000)
                if len(self.metrics) > 1000:
                    self.metrics = self.metrics[-1000:]
                
                return jsonify(result_dict)
            
            except Exception as e:
                self.logger.error(f"GraphQL execution error: {e}")
                return jsonify({
                    'errors': [{
                        'message': 'Internal server error',
                        'extensions': {'code': 'INTERNAL_ERROR'}
                    }]
                }), 500
        
        # Add GraphQL endpoint
        self.app.add_url_rule(
            '/graphql',
            view_func=graphql_view,
            methods=['POST']
        )
        
        # Add GraphQL GET endpoint for introspection
        self.app.add_url_rule(
            '/graphql',
            view_func=lambda: GraphQLView.as_view(
                'graphql',
                schema=self.schema,
                graphiql=False
            )(),
            methods=['GET']
        )
    
    def _setup_playground(self):
        """Setup GraphQL Playground"""
        
        @self.app.route('/graphql/playground')
        def graphql_playground():
            """GraphQL Playground interface"""
            playground_html = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>GraphQL Playground</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/graphql-playground-react@1.7.26/build/static/css/index.css" />
    <link rel="shortcut icon" href="https://cdn.jsdelivr.net/npm/graphql-playground-react@1.7.26/build/favicon.png" />
    <script src="https://cdn.jsdelivr.net/npm/graphql-playground-react@1.7.26/build/static/js/middleware.js"></script>
</head>
<body>
    <div id="root">
        <style>
            body { margin: 0; font-family: Open Sans, sans-serif; overflow: hidden; }
            #root { height: 100vh; }
        </style>
    </div>
    <script>
        window.addEventListener('load', function (event) {
            GraphQLPlayground.init(document.getElementById('root'), {
                endpoint: '/graphql',
                settings: {
                    'editor.theme': 'dark',
                    'editor.fontSize': 14,
                    'editor.fontFamily': '"Source Code Pro", "Consolas", "Inconsolata", "Droid Sans Mono", "Monaco", monospace',
                    'request.credentials': 'same-origin',
                },
                tabs: [
                    {
                        endpoint: '/graphql',
                        query: `# Welcome to GraphQL Playground
# GraphQL Playground is a powerful GraphQL IDE for better development workflows.
#
# Here are some example queries to get you started:

# Get all orders
query GetOrders {
  orders(limit: 10) {
    id
    symbol
    side
    quantity
    price
    status
    createdAt
  }
}

# Get portfolio summary
query GetPortfolio {
  portfolio {
    totalValue
    cashBalance
    totalPnl
    dailyPnl
    positionsCount
    positions {
      symbol
      quantity
      averagePrice
      marketPrice
      unrealizedPnl
    }
  }
}

# Get market data
query GetMarketData {
  marketData(symbol: "AAPL") {
    symbol
    lastPrice
    bid
    ask
    volume
    change
    changePercent
    timestamp
  }
}

# Create an order (mutation)
mutation CreateOrder {
  createOrder(
    symbol: "AAPL"
    side: "buy"
    quantity: 100
    orderType: "limit"
    price: 150.25
  ) {
    success
    message
    order {
      id
      symbol
      side
      quantity
      price
      status
    }
  }
}

# Subscribe to market data updates
subscription MarketDataUpdates {
  marketDataUpdates(symbol: "AAPL") {
    symbol
    lastPrice
    change
    changePercent
    timestamp
  }
}`,
                    },
                ],
            })
        })
    </script>
</body>
</html>
            '''
            return playground_html
    
    def get_schema_sdl(self) -> str:
        """Get GraphQL Schema Definition Language"""
        from graphql import print_schema
        # Convert Graphene schema to GraphQL schema
        graphql_schema = self.schema.graphql_schema if hasattr(self.schema, 'graphql_schema') else self.schema
        return print_schema(graphql_schema)
    
    def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get GraphQL metrics summary"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [m for m in self.metrics if m.timestamp > cutoff_time]
        
        if not recent_metrics:
            return {
                'total_queries': 0,
                'avg_execution_time': 0,
                'avg_complexity': 0,
                'error_rate': 0,
                'top_queries': [],
                'complexity_distribution': {}
            }
        
        total_queries = len(recent_metrics)
        avg_execution_time = sum(m.execution_time for m in recent_metrics) / total_queries
        avg_complexity = sum(m.complexity_score for m in recent_metrics) / total_queries
        error_count = len([m for m in recent_metrics if m.errors])
        error_rate = (error_count / total_queries) * 100
        
        # Top queries by frequency
        query_counts = defaultdict(int)
        for metric in recent_metrics:
            # Use first 100 chars of query as identifier
            query_key = metric.query[:100] + "..." if len(metric.query) > 100 else metric.query
            query_counts[query_key] += 1
        
        top_queries = sorted(query_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Complexity distribution
        complexity_ranges = {
            'low (1-5)': 0,
            'medium (6-15)': 0,
            'high (16-30)': 0,
            'very_high (31+)': 0
        }
        
        for metric in recent_metrics:
            if metric.complexity_score <= 5:
                complexity_ranges['low (1-5)'] += 1
            elif metric.complexity_score <= 15:
                complexity_ranges['medium (6-15)'] += 1
            elif metric.complexity_score <= 30:
                complexity_ranges['high (16-30)'] += 1
            else:
                complexity_ranges['very_high (31+)'] += 1
        
        return {
            'total_queries': total_queries,
            'avg_execution_time': avg_execution_time,
            'avg_complexity': avg_complexity,
            'error_rate': error_rate,
            'top_queries': [{'query': q, 'count': c} for q, c in top_queries],
            'complexity_distribution': complexity_ranges
        }
    
    async def invalidate_cache(self, pattern: str = None) -> int:
        """Invalidate cache entries"""
        if pattern:
            return await self.cache.invalidate_pattern(pattern)
        else:
            # Clear all cache
            if self.cache.redis_client:
                return await self.cache.redis_client.flushdb()
            else:
                count = len(self.cache.memory_cache)
                self.cache.memory_cache.clear()
                return count
    
    def run(self, host: str = "0.0.0.0", port: int = 8001, debug: bool = False):
        """Run GraphQL API server"""
        self.logger.info(f"Starting GraphQL API on {host}:{port}")
        self.logger.info(f"GraphQL endpoint: http://{host}:{port}/graphql")
        self.logger.info(f"GraphQL Playground: http://{host}:{port}/graphql/playground")
        
        self.app.run(host=host, port=port, debug=debug)

def create_graphql_api(redis_url: str = None) -> GraphQLAPI:
    """Create GraphQL API instance"""
    return GraphQLAPI(redis_url=redis_url)

if __name__ == "__main__":
    # Example usage
    try:
        api = create_graphql_api()
        
        print("GraphQL API created successfully!")
        print("Available endpoints:")
        print("- POST /graphql - GraphQL endpoint")
        print("- GET /graphql/playground - GraphQL Playground")
        
        # Get schema SDL
        schema_sdl = api.get_schema_sdl()
        print(f"\nSchema SDL length: {len(schema_sdl)} characters")
        
        # Run the API
        api.run(debug=True)
        
    except ImportError as e:
        print(f"GraphQL dependencies not available: {e}")
        print("Install with: pip install graphene flask-graphql")