"""
Test suite for Smart Order Router
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from .smart_order_router import (
    SmartOrderRouter, OrderRequest, RoutingDecision, VenueInfo,
    OrderType, RoutingStrategy, VenueType
)


class TestSmartOrderRouter:
    """Test cases for Smart Order Router"""
    
    @pytest.fixture
    async def router(self):
        """Create router instance for testing"""
        router = SmartOrderRouter(
            enable_ml_routing=False,  # Disable ML for basic tests
            max_concurrent_routes=5
        )
        
        # Add test venues
        await self._add_test_venues(router)
        
        await router.start()
        yield router
        await router.stop()
    
    async def _add_test_venues(self, router):
        """Add test venues to router"""
        # Exchange venue
        exchange_venue = VenueInfo(
            venue_id="NYSE",
            venue_name="New York Stock Exchange",
            venue_type=VenueType.EXCHANGE,
            latency_ms=2.0,
            maker_fee=0.0015,
            taker_fee=0.0025,
            rebate=0.0010,
            avg_spread_bps=5.0,
            avg_depth=1000.0,
            fill_rate=0.95,
            bid_price=100.0,
            ask_price=100.05,
            bid_size=500.0,
            ask_size=500.0,
            avg_fill_time_ms=50.0,
            rejection_rate=0.02,
            uptime_percentage=99.9,
            connection_status="connected"
        )
        await router.add_venue(exchange_venue)
        
        # Dark pool venue
        dark_pool_venue = VenueInfo(
            venue_id="DARK1",
            venue_name="Dark Pool 1",
            venue_type=VenueType.DARK_POOL,
            latency_ms=5.0,
            maker_fee=0.0010,
            taker_fee=0.0020,
            rebate=0.0005,
            avg_spread_bps=2.0,
            avg_depth=800.0,
            fill_rate=0.80,
            avg_fill_time_ms=100.0,
            rejection_rate=0.05,
            uptime_percentage=99.5,
            connection_status="connected",
            is_dark=True,
            hidden_liquidity_score=0.7
        )
        await router.add_venue(dark_pool_venue)
        
        # ECN venue
        ecn_venue = VenueInfo(
            venue_id="ECN1",
            venue_name="Electronic Communication Network 1",
            venue_type=VenueType.ECN,
            latency_ms=1.5,
            maker_fee=0.0012,
            taker_fee=0.0022,
            rebate=0.0008,
            avg_spread_bps=3.0,
            avg_depth=1200.0,
            fill_rate=0.92,
            bid_price=100.01,
            ask_price=100.04,
            bid_size=800.0,
            ask_size=800.0,
            avg_fill_time_ms=30.0,
            rejection_rate=0.01,
            uptime_percentage=99.8,
            connection_status="connected"
        )
        await router.add_venue(ecn_venue)
    
    @pytest.mark.asyncio
    async def test_basic_routing(self, router):
        """Test basic order routing functionality"""
        order_request = OrderRequest(
            order_id="test_001",
            symbol="AAPL",
            side="buy",
            quantity=1000.0,
            order_type=OrderType.MARKET,
            routing_strategy=RoutingStrategy.BEST_PRICE
        )
        
        decision = await router.route_order(order_request)
        
        assert decision is not None
        assert decision.order_id == "test_001"
        assert len(decision.venue_allocations) > 0
        assert decision.confidence > 0
        
        # Check that total allocated quantity matches order quantity
        total_allocated = sum(qty for _, qty, _ in decision.venue_allocations)
        assert abs(total_allocated - order_request.quantity) < 0.01
    
    @pytest.mark.asyncio
    async def test_best_price_strategy(self, router):
        """Test best price routing strategy"""
        order_request = OrderRequest(
            order_id="test_002",
            symbol="AAPL",
            side="buy",
            quantity=500.0,
            order_type=OrderType.LIMIT,
            limit_price=100.10,
            routing_strategy=RoutingStrategy.BEST_PRICE
        )
        
        decision = await router.route_order(order_request)
        
        assert decision.routing_strategy == RoutingStrategy.BEST_PRICE
        assert len(decision.venue_allocations) > 0
        
        # Should prefer venues with lower ask prices for buy orders
        prices = [price for _, _, price in decision.venue_allocations]
        assert all(price <= 100.10 for price in prices)
    
    @pytest.mark.asyncio
    async def test_dark_first_strategy(self, router):
        """Test dark pool first routing strategy"""
        order_request = OrderRequest(
            order_id="test_003",
            symbol="AAPL",
            side="sell",
            quantity=800.0,
            order_type=OrderType.MARKET,
            routing_strategy=RoutingStrategy.DARK_FIRST,
            allow_dark_pools=True
        )
        
        decision = await router.route_order(order_request)
        
        assert decision.routing_strategy == RoutingStrategy.DARK_FIRST
        
        # Should include dark pool venues
        venue_ids = [venue_id for venue_id, _, _ in decision.venue_allocations]
        dark_venues = [vid for vid in venue_ids if router.get_venue_info(vid).is_dark]
        assert len(dark_venues) > 0
    
    @pytest.mark.asyncio
    async def test_smart_routing_strategy(self, router):
        """Test smart routing strategy"""
        order_request = OrderRequest(
            order_id="test_004",
            symbol="AAPL",
            side="buy",
            quantity=2000.0,
            order_type=OrderType.MARKET,
            routing_strategy=RoutingStrategy.SMART_ROUTING,
            minimize_market_impact=True
        )
        
        decision = await router.route_order(order_request)
        
        assert decision.routing_strategy == RoutingStrategy.SMART_ROUTING
        assert decision.confidence > 0.8  # Smart routing should have high confidence
        
        # Should spread across multiple venues for large orders
        assert len(decision.venue_allocations) >= 2
    
    @pytest.mark.asyncio
    async def test_minimal_impact_strategy(self, router):
        """Test minimal impact routing strategy"""
        order_request = OrderRequest(
            order_id="test_005",
            symbol="AAPL",
            side="buy",
            quantity=5000.0,  # Large order
            order_type=OrderType.MARKET,
            routing_strategy=RoutingStrategy.MINIMAL_IMPACT,
            minimize_market_impact=True
        )
        
        decision = await router.route_order(order_request)
        
        assert decision.routing_strategy == RoutingStrategy.MINIMAL_IMPACT
        
        # Should spread across multiple venues to minimize impact
        assert len(decision.venue_allocations) >= 2
        
        # Should have reasonable expected impact
        assert decision.expected_impact >= 0
    
    @pytest.mark.asyncio
    async def test_fastest_fill_strategy(self, router):
        """Test fastest fill routing strategy"""
        order_request = OrderRequest(
            order_id="test_006",
            symbol="AAPL",
            side="sell",
            quantity=300.0,
            order_type=OrderType.MARKET,
            routing_strategy=RoutingStrategy.FASTEST_FILL
        )
        
        decision = await router.route_order(order_request)
        
        assert decision.routing_strategy == RoutingStrategy.FASTEST_FILL
        assert decision.expected_fill_time_ms > 0
        
        # Should prefer venues with low latency and fast fill times
        for venue_id, _, _ in decision.venue_allocations:
            venue = router.get_venue_info(venue_id)
            assert venue.connection_status == "connected"
            assert venue.rejection_rate <= 0.1
    
    @pytest.mark.asyncio
    async def test_liquidity_seeking_strategy(self, router):
        """Test liquidity seeking routing strategy"""
        order_request = OrderRequest(
            order_id="test_007",
            symbol="AAPL",
            side="buy",
            quantity=1500.0,
            order_type=OrderType.MARKET,
            routing_strategy=RoutingStrategy.LIQUIDITY_SEEKING
        )
        
        decision = await router.route_order(order_request)
        
        assert decision.routing_strategy == RoutingStrategy.LIQUIDITY_SEEKING
        
        # Should prefer venues with higher liquidity
        for venue_id, _, _ in decision.venue_allocations:
            venue = router.get_venue_info(venue_id)
            assert venue.avg_depth > 0
    
    @pytest.mark.asyncio
    async def test_order_validation(self, router):
        """Test order request validation"""
        # Invalid order - no symbol
        invalid_order = OrderRequest(
            order_id="test_invalid_001",
            symbol="",
            side="buy",
            quantity=100.0,
            order_type=OrderType.MARKET
        )
        
        with pytest.raises(ValueError):
            await router.route_order(invalid_order)
        
        # Invalid order - negative quantity
        invalid_order2 = OrderRequest(
            order_id="test_invalid_002",
            symbol="AAPL",
            side="buy",
            quantity=-100.0,
            order_type=OrderType.MARKET
        )
        
        with pytest.raises(ValueError):
            await router.route_order(invalid_order2)
        
        # Invalid order - invalid side
        invalid_order3 = OrderRequest(
            order_id="test_invalid_003",
            symbol="AAPL",
            side="invalid",
            quantity=100.0,
            order_type=OrderType.MARKET
        )
        
        with pytest.raises(ValueError):
            await router.route_order(invalid_order3)
    
    @pytest.mark.asyncio
    async def test_venue_management(self, router):
        """Test venue management functionality"""
        # Test getting venue info
        venue_info = router.get_venue_info("NYSE")
        assert venue_info is not None
        assert venue_info.venue_id == "NYSE"
        
        # Test getting all venues
        all_venues = router.get_all_venues()
        assert len(all_venues) >= 3  # We added 3 test venues
        
        # Test adding new venue
        new_venue = VenueInfo(
            venue_id="TEST_VENUE",
            venue_name="Test Venue",
            venue_type=VenueType.ECN,
            latency_ms=3.0,
            fill_rate=0.9,
            connection_status="connected"
        )
        
        await router.add_venue(new_venue)
        
        # Verify venue was added
        added_venue = router.get_venue_info("TEST_VENUE")
        assert added_venue is not None
        assert added_venue.venue_id == "TEST_VENUE"
        
        # Test removing venue
        await router.remove_venue("TEST_VENUE")
        
        # Verify venue was removed
        removed_venue = router.get_venue_info("TEST_VENUE")
        assert removed_venue is None
    
    @pytest.mark.asyncio
    async def test_market_data_update(self, router):
        """Test market data updates"""
        # Update market data for a venue
        new_market_data = {
            'bid_price': 99.95,
            'ask_price': 100.00,
            'bid_size': 1000.0,
            'ask_size': 1000.0
        }
        
        await router.update_venue_market_data("NYSE", "AAPL", new_market_data)
        
        # Verify market data was updated
        venue = router.get_venue_info("NYSE")
        assert venue.bid_price == 99.95
        assert venue.ask_price == 100.00
        assert venue.bid_size == 1000.0
        assert venue.ask_size == 1000.0
    
    @pytest.mark.asyncio
    async def test_routing_metrics(self, router):
        """Test routing metrics collection"""
        # Route a few orders to generate metrics
        for i in range(3):
            order_request = OrderRequest(
                order_id=f"metrics_test_{i}",
                symbol="AAPL",
                side="buy",
                quantity=100.0,
                order_type=OrderType.MARKET
            )
            await router.route_order(order_request)
        
        # Check metrics
        metrics = router.get_routing_metrics()
        assert metrics['total_routes'] >= 3
        assert metrics['successful_routes'] >= 3
        assert metrics['avg_routing_time_ms'] > 0
    
    @pytest.mark.asyncio
    async def test_routing_recommendation(self, router):
        """Test routing recommendation without placing order"""
        recommendation = await router.get_routing_recommendation(
            symbol="AAPL",
            side="buy",
            quantity=1000.0
        )
        
        assert 'recommended_venues' in recommendation
        assert 'expected_cost' in recommendation
        assert 'expected_impact' in recommendation
        assert 'confidence' in recommendation
        assert 'reasoning' in recommendation
        
        assert len(recommendation['recommended_venues']) > 0
        assert recommendation['expected_cost'] > 0
        assert recommendation['confidence'] >= 0
    
    @pytest.mark.asyncio
    async def test_concurrent_routing(self, router):
        """Test concurrent order routing"""
        # Create multiple order requests
        orders = []
        for i in range(10):
            order = OrderRequest(
                order_id=f"concurrent_test_{i}",
                symbol="AAPL",
                side="buy" if i % 2 == 0 else "sell",
                quantity=100.0 + i * 10,
                order_type=OrderType.MARKET,
                routing_strategy=RoutingStrategy.SMART_ROUTING
            )
            orders.append(order)
        
        # Route orders concurrently
        tasks = [router.route_order(order) for order in orders]
        decisions = await asyncio.gather(*tasks)
        
        # Verify all orders were routed
        assert len(decisions) == 10
        for decision in decisions:
            assert decision is not None
            assert len(decision.venue_allocations) > 0
    
    @pytest.mark.asyncio
    async def test_performance_tracking(self, router):
        """Test venue performance tracking"""
        # Get performance metrics for a venue
        performance = router.get_venue_performance("NYSE")
        assert performance is not None
        assert performance.venue_id == "NYSE"
        
        # Performance metrics should be initialized
        assert performance.total_orders >= 0
        assert performance.last_updated is not None
    
    def test_venue_score_calculation(self, router):
        """Test venue scoring algorithm"""
        # This would test the internal scoring methods
        # For now, we'll test that venues are properly scored during routing
        pass
    
    @pytest.mark.asyncio
    async def test_market_impact_estimation(self, router):
        """Test market impact estimation"""
        # Create order with market data
        order_request = OrderRequest(
            order_id="impact_test",
            symbol="AAPL",
            side="buy",
            quantity=10000.0,  # Large order
            order_type=OrderType.MARKET,
            routing_strategy=RoutingStrategy.MINIMAL_IMPACT
        )
        
        # Set up market data
        market_data = {
            'bid_price': 100.0,
            'ask_price': 100.05,
            'bid_size': 1000.0,
            'ask_size': 1000.0,
            'avg_daily_volume': 1000000.0,
            'volatility': 0.02
        }
        
        # Test impact estimation (internal method)
        impact = await router._estimate_market_impact(order_request, market_data)
        
        assert 'temporary_impact' in impact
        assert 'permanent_impact' in impact
        assert impact['temporary_impact'] >= 0
        assert impact['permanent_impact'] >= 0
    
    @pytest.mark.asyncio
    async def test_hidden_liquidity_detection(self, router):
        """Test hidden liquidity detection"""
        venues = router.get_all_venues()
        
        # Test hidden liquidity detection
        hidden_liquidity = await router._detect_hidden_liquidity("AAPL", venues)
        
        assert isinstance(hidden_liquidity, dict)
        
        # Should have entries for all venues
        for venue in venues:
            assert venue.venue_id in hidden_liquidity
            assert 0 <= hidden_liquidity[venue.venue_id] <= 1


@pytest.mark.asyncio
async def test_smart_order_router_integration():
    """Integration test for Smart Order Router"""
    # Create router with ML disabled for testing
    router = SmartOrderRouter(enable_ml_routing=False)
    
    try:
        await router.start()
        
        # Add a test venue
        test_venue = VenueInfo(
            venue_id="INTEGRATION_TEST",
            venue_name="Integration Test Venue",
            venue_type=VenueType.EXCHANGE,
            latency_ms=1.0,
            fill_rate=0.95,
            bid_price=100.0,
            ask_price=100.05,
            bid_size=1000.0,
            ask_size=1000.0,
            connection_status="connected"
        )
        
        await router.add_venue(test_venue)
        
        # Test order routing
        order = OrderRequest(
            order_id="integration_test",
            symbol="TEST",
            side="buy",
            quantity=500.0,
            order_type=OrderType.MARKET
        )
        
        decision = await router.route_order(order)
        
        assert decision is not None
        assert decision.order_id == "integration_test"
        assert len(decision.venue_allocations) > 0
        
    finally:
        await router.stop()


if __name__ == "__main__":
    # Run basic test
    asyncio.run(test_smart_order_router_integration())
    print("Smart Order Router integration test passed!")