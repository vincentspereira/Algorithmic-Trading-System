"""
Test suite for GraphQL API implementation including queries, mutations,
subscriptions, caching, and complexity analysis.
"""
import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import uuid

# Import the modules to test
from nautilus_trader_engine.api.graphql_api import (
    GraphQLAPI, GraphQLCache, QueryComplexityAnalyzer, GraphQLMetrics,
    QueryComplexity, create_graphql_api
)

# Test with and without GraphQL dependencies
try:
    import graphene
    from graphene import Schema, ObjectType, String, Int, Float
    GRAPHQL_AVAILABLE = True
except ImportError:
    GRAPHQL_AVAILABLE = False

class TestGraphQLCache:
    """Test GraphQL caching functionality"""
    
    @pytest.fixture
    def cache(self):
        """Create GraphQL cache for testing"""
        return GraphQLCache(default_ttl=300)
    
    def test_cache_initialization(self, cache):
        """Test cache initialization"""
        assert cache.redis_client is None
        assert cache.default_ttl == 300
        assert cache.memory_cache == {}
        assert cache.logger is not None
    
    def test_generate_cache_key(self, cache):
        """Test cache key generation"""
        query1 = "query { orders { id symbol } }"
        variables1 = {"limit": 10}
        
        query2 = "query{orders{id symbol}}"  # Different formatting
        variables2 = {"limit": 10}
        
        # Same normalized query should generate same key
        key1 = cache._generate_cache_key(query1, variables1)
        key2 = cache._generate_cache_key(query2, variables2)
        
        assert key1 == key2
        assert len(key1) == 32  # MD5 hash length
    
    @pytest.mark.asyncio
    async def test_memory_cache_set_get(self, cache):
        """Test memory cache set and get operations"""
        query = "query { orders { id } }"
        variables = {"limit": 5}
        result = {"data": {"orders": [{"id": "1"}, {"id": "2"}]}}
        
        # Set cache
        success = await cache.set(query, variables, result, ttl=60)
        assert success is True
        
        # Get from cache
        cached_result = await cache.get(query, variables)
        assert cached_result == result
    
    @pytest.mark.asyncio
    async def test_memory_cache_expiration(self, cache):
        """Test memory cache expiration"""
        query = "query { orders { id } }"
        variables = {}
        result = {"data": {"orders": []}}
        
        # Set cache with short TTL
        await cache.set(query, variables, result, ttl=1)
        
        # Should be available immediately
        cached_result = await cache.get(query, variables)
        assert cached_result == result
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Should be expired
        cached_result = await cache.get(query, variables)
        assert cached_result is None
    
    @pytest.mark.asyncio
    async def test_cache_miss(self, cache):
        """Test cache miss"""
        query = "query { nonexistent { id } }"
        variables = {}
        
        cached_result = await cache.get(query, variables)
        assert cached_result is None
    
    @pytest.mark.asyncio
    async def test_invalidate_pattern(self, cache):
        """Test cache pattern invalidation"""
        # Set multiple cache entries
        queries = [
            "query { orders { id } }",
            "query { positions { symbol } }",
            "query { orders { symbol } }"
        ]
        
        for i, query in enumerate(queries):
            await cache.set(query, {}, {"data": f"result_{i}"})
        
        # Invalidate entries containing "orders"
        invalidated_count = await cache.invalidate_pattern("orders")
        assert invalidated_count == 2
        
        # Check that orders queries are gone but positions query remains
        assert await cache.get(queries[0], {}) is None
        assert await cache.get(queries[2], {}) is None
        assert await cache.get(queries[1], {}) is not None

class TestQueryComplexityAnalyzer:
    """Test GraphQL query complexity analysis"""
    
    @pytest.fixture
    def analyzer(self):
        """Create complexity analyzer for testing"""
        return QueryComplexityAnalyzer(max_complexity=50, max_depth=5)
    
    def test_analyzer_initialization(self, analyzer):
        """Test analyzer initialization"""
        assert analyzer.max_complexity == 50
        assert analyzer.max_depth == 5
        assert analyzer.logger is not None
    
    def test_get_field_complexity(self, analyzer):
        """Test field complexity mapping"""
        # Simple fields
        assert analyzer._get_field_complexity('id') == 1
        assert analyzer._get_field_complexity('name') == 1
        
        # Medium complexity fields
        assert analyzer._get_field_complexity('orders') == 5
        assert analyzer._get_field_complexity('positions') == 5
        
        # High complexity fields
        assert analyzer._get_field_complexity('analytics') == 10
        
        # Very high complexity fields
        assert analyzer._get_field_complexity('marketData') == 25
        
        # Unknown field (default)
        assert analyzer._get_field_complexity('unknown_field') == 3
    
    @pytest.mark.skipif(not GRAPHQL_AVAILABLE, reason="GraphQL not available")
    def test_analyze_simple_query(self, analyzer):
        """Test analyzing simple query"""
        from graphql import parse
        
        query = """
        query {
            orders {
                id
                symbol
            }
        }
        """
        
        query_ast = parse(query)
        analysis = analyzer.analyze_query(query_ast)
        
        assert 'complexity' in analysis
        assert 'depth' in analysis
        assert 'field_count' in analysis
        assert 'is_valid' in analysis
        assert analysis['is_valid'] is True
        assert analysis['complexity'] > 0
        assert analysis['depth'] > 0
    
    def test_analyze_query_error_handling(self, analyzer):
        """Test query analysis error handling"""
        # Pass invalid query AST
        invalid_ast = Mock()
        
        analysis = analyzer.analyze_query(invalid_ast)
        
        # Should return default values on error
        assert analysis['complexity'] == 0
        assert analysis['depth'] == 0
        assert analysis['field_count'] == 0
        assert analysis['is_valid'] is True

@pytest.mark.skipif(not GRAPHQL_AVAILABLE, reason="GraphQL not available")
class TestGraphQLAPI:
    """Test GraphQL API functionality"""
    
    @pytest.fixture
    def graphql_api(self):
        """Create GraphQL API for testing"""
        with patch('nautilus_trader_engine.api.graphql_api.Flask') as mock_flask:
            mock_app = Mock()
            mock_flask.return_value = mock_app
            
            api = GraphQLAPI()
            api.app = mock_app
            return api
    
    def test_graphql_api_initialization(self, graphql_api):
        """Test GraphQL API initialization"""
        assert graphql_api.cache is not None
        assert graphql_api.complexity_analyzer is not None
        assert graphql_api.schema is not None
        assert graphql_api.metrics == []
        assert graphql_api.logger is not None
    
    def test_schema_creation(self, graphql_api):
        """Test GraphQL schema creation"""
        schema = graphql_api.schema
        
        # Check that schema exists and has the expected structure
        assert schema is not None
        assert hasattr(schema, 'execute')
        assert hasattr(schema, 'get_query_type')
        assert hasattr(schema, 'get_mutation_type')
        assert hasattr(schema, 'get_subscription_type')
        
        # Check that we can execute a simple introspection query
        result = schema.execute('{ __schema { types { name } } }')
        assert result.errors is None
        assert result.data is not None
        assert '__schema' in result.data
    
    def test_get_schema_sdl(self, graphql_api):
        """Test getting schema SDL"""
        sdl = graphql_api.get_schema_sdl()
        
        assert isinstance(sdl, str)
        assert len(sdl) > 100  # Should be substantial
        assert 'type Query' in sdl
        assert 'type Mutation' in sdl
        assert 'type Subscription' in sdl
    
    def test_metrics_summary_empty(self, graphql_api):
        """Test metrics summary with no data"""
        summary = graphql_api.get_metrics_summary()
        
        assert summary['total_queries'] == 0
        assert summary['avg_execution_time'] == 0
        assert summary['avg_complexity'] == 0
        assert summary['error_rate'] == 0
        assert summary['top_queries'] == []
        assert summary['complexity_distribution'] == {}
    
    def test_metrics_summary_with_data(self, graphql_api):
        """Test metrics summary with sample data"""
        # Add sample metrics
        for i in range(10):
            metric = GraphQLMetrics(
                query_id=f"query_{i}",
                query=f"query {{ orders(limit: {i}) {{ id }} }}",
                variables={"limit": i},
                execution_time=0.1 + (i * 0.01),
                complexity_score=5 + i,
                field_count=2,
                depth=2,
                user_id=f"user_{i % 3}",
                timestamp=datetime.now(),
                errors=[] if i % 5 != 0 else ["Sample error"]
            )
            graphql_api.metrics.append(metric)
        
        summary = graphql_api.get_metrics_summary()
        
        assert summary['total_queries'] == 10
        assert summary['avg_execution_time'] > 0
        assert summary['avg_complexity'] > 0
        assert summary['error_rate'] == 20.0  # 2 out of 10 have errors
        assert len(summary['top_queries']) > 0
        assert 'low (1-5)' in summary['complexity_distribution']
    
    @pytest.mark.asyncio
    async def test_invalidate_cache(self, graphql_api):
        """Test cache invalidation"""
        # Add some cache entries
        await graphql_api.cache.set("query1", {}, {"data": "result1"})
        await graphql_api.cache.set("query2", {}, {"data": "result2"})
        
        # Invalidate all cache
        count = await graphql_api.invalidate_cache()
        assert count == 2
        
        # Verify cache is empty
        result1 = await graphql_api.cache.get("query1", {})
        result2 = await graphql_api.cache.get("query2", {})
        assert result1 is None
        assert result2 is None

class TestGraphQLTypes:
    """Test GraphQL type definitions"""
    
    @pytest.mark.skipif(not GRAPHQL_AVAILABLE, reason="GraphQL not available")
    def test_order_type_resolvers(self):
        """Test OrderType resolvers"""
        from nautilus_trader_engine.api.graphql_api import OrderType
        
        # Test created_at resolver
        order_data = {'id': '123', 'symbol': 'AAPL'}
        created_at = OrderType.resolve_created_at(order_data, None)
        
        assert isinstance(created_at, str)
        # Should be valid ISO format
        datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    
    @pytest.mark.skipif(not GRAPHQL_AVAILABLE, reason="GraphQL not available")
    def test_position_type_resolvers(self):
        """Test PositionType resolvers"""
        from nautilus_trader_engine.api.graphql_api import PositionType
        
        position_data = {
            'symbol': 'AAPL',
            'quantity': 100,
            'average_price': 150.0,
            'market_price': 155.0
        }
        
        # Test market_value resolver
        market_value = PositionType.resolve_market_value(position_data, None)
        assert market_value == 15500.0  # 100 * 155.0
        
        # Test unrealized_pnl resolver
        unrealized_pnl = PositionType.resolve_unrealized_pnl(position_data, None)
        assert unrealized_pnl == 500.0  # 100 * (155.0 - 150.0)
    
    @pytest.mark.skipif(not GRAPHQL_AVAILABLE, reason="GraphQL not available")
    def test_portfolio_type_resolvers(self):
        """Test PortfolioType resolvers"""
        from nautilus_trader_engine.api.graphql_api import PortfolioType
        
        portfolio_data = {
            'positions': [
                {'symbol': 'AAPL', 'unrealized_pnl': 500.0},
                {'symbol': 'GOOGL', 'unrealized_pnl': -200.0},
                {'symbol': 'MSFT', 'unrealized_pnl': 300.0}
            ]
        }
        
        # Test positions_count resolver
        count = PortfolioType.resolve_positions_count(portfolio_data, None)
        assert count == 3
        
        # Test total_pnl resolver
        total_pnl = PortfolioType.resolve_total_pnl(portfolio_data, None)
        assert total_pnl == 600.0  # 500 - 200 + 300
    
    @pytest.mark.skipif(not GRAPHQL_AVAILABLE, reason="GraphQL not available")
    def test_market_data_type_resolvers(self):
        """Test MarketDataType resolvers"""
        from nautilus_trader_engine.api.graphql_api import MarketDataType
        
        market_data = {
            'symbol': 'AAPL',
            'last_price': 150.0,
            'change': 5.0
        }
        
        # Test change_percent resolver
        change_percent = MarketDataType.resolve_change_percent(market_data, None)
        expected_percent = (5.0 / (150.0 - 5.0)) * 100  # (change / previous_price) * 100
        assert abs(change_percent - expected_percent) < 0.01
    
    @pytest.mark.skipif(not GRAPHQL_AVAILABLE, reason="GraphQL not available")
    def test_analytics_type_resolvers(self):
        """Test AnalyticsType resolvers"""
        from nautilus_trader_engine.api.graphql_api import AnalyticsType
        
        analytics_data = {
            'winning_trades': 60,
            'total_trades': 100
        }
        
        # Test win_rate resolver
        win_rate = AnalyticsType.resolve_win_rate(analytics_data, None)
        assert win_rate == 60.0  # (60 / 100) * 100
        
        # Test with zero trades
        zero_trades_data = {'winning_trades': 0, 'total_trades': 0}
        win_rate_zero = AnalyticsType.resolve_win_rate(zero_trades_data, None)
        assert win_rate_zero == 0

@pytest.mark.skipif(not GRAPHQL_AVAILABLE, reason="GraphQL not available")
class TestGraphQLQueries:
    """Test GraphQL query execution"""
    
    @pytest.fixture
    def schema(self):
        """Create GraphQL schema for testing"""
        from nautilus_trader_engine.api.graphql_api import Query, Mutation, Subscription
        from graphene import Schema
        
        return Schema(query=Query, mutation=Mutation, subscription=Subscription)
    
    def test_orders_query(self, schema):
        """Test orders query execution"""
        query = """
        query {
            orders(limit: 5) {
                id
                symbol
                side
                quantity
                status
            }
        }
        """
        
        result = schema.execute(query)
        
        assert result.errors is None
        assert result.data is not None
        assert 'orders' in result.data
        assert len(result.data['orders']) == 5
        
        # Check order structure
        order = result.data['orders'][0]
        assert 'id' in order
        assert 'symbol' in order
        assert 'side' in order
        assert 'quantity' in order
        assert 'status' in order
    
    def test_portfolio_query(self, schema):
        """Test portfolio query execution"""
        query = """
        query {
            portfolio {
                totalValue
                cashBalance
                totalPnl
                positionsCount
                positions {
                    symbol
                    quantity
                    marketValue
                    unrealizedPnl
                }
            }
        }
        """
        
        result = schema.execute(query)
        
        assert result.errors is None
        assert result.data is not None
        assert 'portfolio' in result.data
        
        portfolio = result.data['portfolio']
        assert 'totalValue' in portfolio
        assert 'cashBalance' in portfolio
        assert 'totalPnl' in portfolio
        assert 'positionsCount' in portfolio
        assert 'positions' in portfolio
        assert isinstance(portfolio['positions'], list)
    
    def test_market_data_query(self, schema):
        """Test market data query execution"""
        query = """
        query {
            marketData(symbol: "AAPL") {
                symbol
                lastPrice
                bid
                ask
                volume
                change
                changePercent
            }
        }
        """
        
        result = schema.execute(query)
        
        assert result.errors is None
        assert result.data is not None
        assert 'marketData' in result.data
        
        market_data = result.data['marketData']
        assert market_data['symbol'] == 'AAPL'
        assert 'lastPrice' in market_data
        assert 'bid' in market_data
        assert 'ask' in market_data
        assert 'volume' in market_data
    
    def test_create_order_mutation(self, schema):
        """Test create order mutation"""
        mutation = """
        mutation {
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
        """
        
        result = schema.execute(mutation)
        
        assert result.errors is None
        assert result.data is not None
        assert 'createOrder' in result.data
        
        create_order = result.data['createOrder']
        assert create_order['success'] is True
        assert 'message' in create_order
        assert 'order' in create_order
        
        order = create_order['order']
        assert order['symbol'] == 'AAPL'
        assert order['side'] == 'buy'
        assert order['quantity'] == 100
        assert order['price'] == 150.25
    
    def test_create_order_validation(self, schema):
        """Test create order mutation validation"""
        mutation = """
        mutation {
            createOrder(
                symbol: "AAPL"
                side: "invalid_side"
                quantity: -100
                orderType: "limit"
            ) {
                success
                message
            }
        }
        """
        
        result = schema.execute(mutation)
        
        assert result.errors is None
        assert result.data is not None
        
        create_order = result.data['createOrder']
        assert create_order['success'] is False
        assert 'Invalid side' in create_order['message']

class TestGraphQLIntegration:
    """Integration tests for GraphQL API"""
    
    def test_create_graphql_api_without_dependencies(self):
        """Test creating GraphQL API without dependencies"""
        with patch('nautilus_trader_engine.api.graphql_api.GRAPHQL_AVAILABLE', False):
            with pytest.raises(ImportError, match="GraphQL packages are required"):
                create_graphql_api()
    
    @pytest.mark.skipif(not GRAPHQL_AVAILABLE, reason="GraphQL not available")
    def test_create_graphql_api_with_dependencies(self):
        """Test creating GraphQL API with dependencies"""
        with patch('nautilus_trader_engine.api.graphql_api.Flask') as mock_flask:
            mock_app = Mock()
            mock_flask.return_value = mock_app
            
            api = create_graphql_api()
            
            assert api is not None
            assert api.cache is not None
            assert api.complexity_analyzer is not None
            assert api.schema is not None
    
    @pytest.mark.skipif(not GRAPHQL_AVAILABLE, reason="GraphQL not available")
    def test_end_to_end_workflow(self):
        """Test complete GraphQL workflow"""
        with patch('nautilus_trader_engine.api.graphql_api.Flask') as mock_flask:
            mock_app = Mock()
            mock_flask.return_value = mock_app
            
            # Create API
            api = create_graphql_api()
            
            # Test schema generation
            sdl = api.get_schema_sdl()
            assert len(sdl) > 0
            
            # Test metrics (empty initially)
            metrics = api.get_metrics_summary()
            assert metrics['total_queries'] == 0
            
            # Add sample metric
            sample_metric = GraphQLMetrics(
                query_id="test_query",
                query="query { orders { id } }",
                variables={},
                execution_time=0.15,
                complexity_score=8,
                field_count=2,
                depth=2,
                user_id="test_user",
                timestamp=datetime.now(),
                errors=[]
            )
            
            api.metrics.append(sample_metric)
            
            # Test metrics with data
            metrics = api.get_metrics_summary()
            assert metrics['total_queries'] == 1
            assert metrics['avg_execution_time'] == 0.15
            assert metrics['avg_complexity'] == 8

if __name__ == "__main__":
    pytest.main([__file__, "-v"])