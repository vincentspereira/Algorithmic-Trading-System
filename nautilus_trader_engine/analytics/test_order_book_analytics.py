"""
Test suite for Order Book Analytics Engine
"""

import pytest
import asyncio
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

from .order_book_analytics import (
    OrderBookAnalyticsEngine,
    OrderBookSnapshot,
    OrderBookLevel,
    OrderBookSide,
    SpreadAnalysis,
    MarketDepthAnalysis,
    OrderBookImbalance,
    PriceLevelCluster,
    ImbalanceType,
    LiquidityTier
)


class TestOrderBookLevel:
    """Test OrderBookLevel dataclass"""
    
    def test_valid_level_creation(self):
        """Test creating valid order book level"""
        level = OrderBookLevel(price=100.0, size=1000.0, orders=5)
        assert level.price == 100.0
        assert level.size == 1000.0
        assert level.orders == 5
        assert isinstance(level.timestamp, datetime)
    
    def test_invalid_price_raises_error(self):
        """Test that invalid price raises ValueError"""
        with pytest.raises(ValueError, match="Price must be positive"):
            OrderBookLevel(price=-100.0, size=1000.0)
    
    def test_invalid_size_raises_error(self):
        """Test that invalid size raises ValueError"""
        with pytest.raises(ValueError, match="Size must be positive"):
            OrderBookLevel(price=100.0, size=-1000.0)


class TestOrderBookSnapshot:
    """Test OrderBookSnapshot dataclass"""
    
    def test_empty_snapshot_creation(self):
        """Test creating empty order book snapshot"""
        snapshot = OrderBookSnapshot(
            symbol="AAPL",
            timestamp=datetime.now()
        )
        assert snapshot.symbol == "AAPL"
        assert snapshot.bid_price is None
        assert snapshot.ask_price is None
        assert snapshot.spread is None
        assert snapshot.mid_price is None
    
    def test_snapshot_with_levels(self):
        """Test snapshot with bid/ask levels"""
        bids = [
            OrderBookLevel(price=100.0, size=1000.0),
            OrderBookLevel(price=99.5, size=500.0)
        ]
        asks = [
            OrderBookLevel(price=100.5, size=800.0),
            OrderBookLevel(price=101.0, size=600.0)
        ]
        
        snapshot = OrderBookSnapshot(
            symbol="AAPL",
            timestamp=datetime.now(),
            bids=bids,
            asks=asks
        )
        
        assert snapshot.bid_price == 100.0
        assert snapshot.ask_price == 100.5
        assert snapshot.spread == 0.5
        assert snapshot.mid_price == 100.25
    
    def test_get_total_size(self):
        """Test getting total size for a side"""
        bids = [
            OrderBookLevel(price=100.0, size=1000.0),
            OrderBookLevel(price=99.5, size=500.0),
            OrderBookLevel(price=99.0, size=300.0)
        ]
        
        snapshot = OrderBookSnapshot(
            symbol="AAPL",
            timestamp=datetime.now(),
            bids=bids
        )
        
        # Test total size
        assert snapshot.get_total_size(OrderBookSide.BID) == 1800.0
        
        # Test limited levels
        assert snapshot.get_total_size(OrderBookSide.BID, 2) == 1500.0
        assert snapshot.get_total_size(OrderBookSide.BID, 1) == 1000.0
    
    def test_get_weighted_price(self):
        """Test getting weighted average price"""
        bids = [
            OrderBookLevel(price=100.0, size=1000.0),
            OrderBookLevel(price=99.0, size=1000.0)
        ]
        
        snapshot = OrderBookSnapshot(
            symbol="AAPL",
            timestamp=datetime.now(),
            bids=bids
        )
        
        # Weighted price should be (100*1000 + 99*1000) / 2000 = 99.5
        weighted_price = snapshot.get_weighted_price(OrderBookSide.BID)
        assert weighted_price == 99.5


class TestSpreadAnalysis:
    """Test SpreadAnalysis dataclass"""
    
    def test_spread_quality_score(self):
        """Test spread quality score calculation"""
        analysis = SpreadAnalysis(
            symbol="AAPL",
            timestamp=datetime.now(),
            absolute_spread=0.01,
            relative_spread=0.0001,  # 0.01%
            spread_volatility=0.001,  # 0.1%
            spread_stability=0.9
        )
        
        score = analysis.get_spread_quality_score()
        assert 0 <= score <= 1
        assert score > 0.8  # Should be high quality


class TestMarketDepthAnalysis:
    """Test MarketDepthAnalysis dataclass"""
    
    def test_liquidity_score(self):
        """Test liquidity score calculation"""
        analysis = MarketDepthAnalysis(
            symbol="AAPL",
            timestamp=datetime.now(),
            bid_depth_10=50000.0,
            ask_depth_10=50000.0,
            depth_ratio_10=1.0,
            depth_consistency=0.8,
            depth_resilience=0.7
        )
        
        score = analysis.get_liquidity_score()
        assert 0 <= score <= 1
        assert score > 0.6  # Should be decent liquidity


class TestOrderBookImbalance:
    """Test OrderBookImbalance dataclass"""
    
    def test_imbalance_significance(self):
        """Test imbalance significance detection"""
        # Significant bid imbalance
        imbalance = OrderBookImbalance(
            symbol="AAPL",
            timestamp=datetime.now(),
            imbalance_ratio=0.4,
            imbalance_type=ImbalanceType.BID_HEAVY,
            imbalance_strength=0.4
        )
        
        assert imbalance.is_significant(0.3)
        assert not imbalance.is_significant(0.5)
    
    def test_direction_signal(self):
        """Test direction signal from imbalance"""
        # Bullish imbalance
        imbalance = OrderBookImbalance(
            symbol="AAPL",
            timestamp=datetime.now(),
            imbalance_ratio=0.3,
            imbalance_type=ImbalanceType.BID_HEAVY,
            imbalance_strength=0.3
        )
        
        assert imbalance.get_direction_signal() == "bullish"
        
        # Bearish imbalance
        imbalance.imbalance_ratio = -0.3
        assert imbalance.get_direction_signal() == "bearish"
        
        # Neutral imbalance
        imbalance.imbalance_ratio = 0.1
        assert imbalance.get_direction_signal() == "neutral"


@pytest.fixture
async def analytics_engine():
    """Create analytics engine for testing"""
    engine = OrderBookAnalyticsEngine(
        enable_real_time=False  # Disable for testing
    )
    await engine.start()
    yield engine
    await engine.stop()


@pytest.fixture
def sample_order_book():
    """Create sample order book for testing"""
    bids = [
        OrderBookLevel(price=100.0, size=1000.0, orders=5),
        OrderBookLevel(price=99.5, size=800.0, orders=3),
        OrderBookLevel(price=99.0, size=600.0, orders=2),
        OrderBookLevel(price=98.5, size=400.0, orders=1),
        OrderBookLevel(price=98.0, size=200.0, orders=1)
    ]
    
    asks = [
        OrderBookLevel(price=100.5, size=900.0, orders=4),
        OrderBookLevel(price=101.0, size=700.0, orders=3),
        OrderBookLevel(price=101.5, size=500.0, orders=2),
        OrderBookLevel(price=102.0, size=300.0, orders=1),
        OrderBookLevel(price=102.5, size=100.0, orders=1)
    ]
    
    return OrderBookSnapshot(
        symbol="AAPL",
        timestamp=datetime.now(),
        bids=bids,
        asks=asks,
        last_price=100.25,
        last_size=100.0,
        volume=10000.0
    )


class TestOrderBookAnalyticsEngine:
    """Test OrderBookAnalyticsEngine"""
    
    @pytest.mark.asyncio
    async def test_engine_start_stop(self):
        """Test engine start and stop"""
        engine = OrderBookAnalyticsEngine(enable_real_time=False)
        
        assert not engine._running
        
        await engine.start()
        assert engine._running
        
        await engine.stop()
        assert not engine._running
    
    @pytest.mark.asyncio
    async def test_update_order_book(self, analytics_engine, sample_order_book):
        """Test updating order book"""
        await analytics_engine.update_order_book("AAPL", sample_order_book)
        
        # Check that book was stored
        stored_book = await analytics_engine.get_current_order_book("AAPL")
        assert stored_book is not None
        assert stored_book.symbol == "AAPL"
        assert stored_book.bid_price == 100.0
        assert stored_book.ask_price == 100.5
        
        # Check metrics
        metrics = await analytics_engine.get_metrics()
        assert metrics['books_processed'] >= 1
    
    @pytest.mark.asyncio
    async def test_spread_analysis(self, analytics_engine, sample_order_book):
        """Test spread analysis"""
        # Add some history for statistical analysis
        for i in range(20):
            book_copy = OrderBookSnapshot(
                symbol="AAPL",
                timestamp=datetime.now() - timedelta(seconds=i),
                bids=sample_order_book.bids,
                asks=sample_order_book.asks
            )
            await analytics_engine.update_order_book("AAPL", book_copy)
        
        # Trigger analysis manually
        await analytics_engine._analyze_spread("AAPL", sample_order_book)
        
        # Get analysis results
        spread_analysis = await analytics_engine.get_spread_analysis("AAPL")
        assert spread_analysis is not None
        assert spread_analysis.symbol == "AAPL"
        assert spread_analysis.absolute_spread == 0.5
        assert spread_analysis.relative_spread > 0
        
        # Test quality score
        quality_score = spread_analysis.get_spread_quality_score()
        assert 0 <= quality_score <= 1
    
    @pytest.mark.asyncio
    async def test_depth_analysis(self, analytics_engine, sample_order_book):
        """Test market depth analysis"""
        await analytics_engine._analyze_market_depth("AAPL", sample_order_book)
        
        depth_analysis = await analytics_engine.get_depth_analysis("AAPL")
        assert depth_analysis is not None
        assert depth_analysis.symbol == "AAPL"
        assert depth_analysis.bid_depth_1 == 1000.0
        assert depth_analysis.ask_depth_1 == 900.0
        assert depth_analysis.depth_ratio_1 > 1.0  # More bids than asks at top
        
        # Test liquidity score
        liquidity_score = depth_analysis.get_liquidity_score()
        assert 0 <= liquidity_score <= 1
    
    @pytest.mark.asyncio
    async def test_imbalance_analysis(self, analytics_engine, sample_order_book):
        """Test order book imbalance analysis"""
        await analytics_engine._analyze_imbalance("AAPL", sample_order_book)
        
        imbalance_analysis = await analytics_engine.get_imbalance_analysis("AAPL")
        assert imbalance_analysis is not None
        assert imbalance_analysis.symbol == "AAPL"
        assert isinstance(imbalance_analysis.imbalance_type, ImbalanceType)
        assert -1 <= imbalance_analysis.imbalance_ratio <= 1
        assert 0 <= imbalance_analysis.imbalance_strength <= 1
    
    @pytest.mark.asyncio
    async def test_price_clustering(self, analytics_engine, sample_order_book):
        """Test price level clustering analysis"""
        await analytics_engine._analyze_price_clustering("AAPL", sample_order_book)
        
        clusters = await analytics_engine.get_price_clusters("AAPL")
        assert isinstance(clusters, list)
        
        # Check cluster properties if any exist
        for cluster in clusters:
            assert isinstance(cluster, PriceLevelCluster)
            assert cluster.symbol == "AAPL"
            assert cluster.total_size > 0
            assert cluster.level_count > 0
            assert cluster.cluster_strength >= 0
    
    @pytest.mark.asyncio
    async def test_support_resistance_identification(self, analytics_engine, sample_order_book):
        """Test support and resistance level identification"""
        # Create clusters first
        await analytics_engine._analyze_price_clustering("AAPL", sample_order_book)
        
        # Get support/resistance levels
        sr_levels = await analytics_engine.get_support_resistance_levels("AAPL")
        
        if sr_levels:  # May be None if no significant clusters
            assert 'support_levels' in sr_levels
            assert 'resistance_levels' in sr_levels
            assert 'timestamp' in sr_levels
    
    @pytest.mark.asyncio
    async def test_price_impact_estimation(self, analytics_engine, sample_order_book):
        """Test price impact estimation"""
        # Test different trade sizes
        impact_1000 = analytics_engine._estimate_price_impact(sample_order_book, 1000.0)
        impact_5000 = analytics_engine._estimate_price_impact(sample_order_book, 5000.0)
        impact_10000 = analytics_engine._estimate_price_impact(sample_order_book, 10000.0)
        
        # Larger trades should have higher impact
        assert impact_1000 >= 0
        assert impact_5000 >= impact_1000
        assert impact_10000 >= impact_5000
    
    @pytest.mark.asyncio
    async def test_depth_consistency_calculation(self, analytics_engine, sample_order_book):
        """Test depth consistency calculation"""
        consistency = analytics_engine._calculate_depth_consistency(sample_order_book)
        assert 0 <= consistency <= 1
    
    @pytest.mark.asyncio
    async def test_config_management(self, analytics_engine):
        """Test configuration management"""
        # Get current config
        config = analytics_engine.get_config()
        assert isinstance(config, dict)
        assert 'spread_analysis_enabled' in config
        
        # Update config
        await analytics_engine.update_config({
            'imbalance_threshold': 0.2,
            'cluster_min_size': 2000.0
        })
        
        updated_config = analytics_engine.get_config()
        assert updated_config['imbalance_threshold'] == 0.2
        assert updated_config['cluster_min_size'] == 2000.0
    
    @pytest.mark.asyncio
    async def test_metrics_tracking(self, analytics_engine, sample_order_book):
        """Test metrics tracking"""
        initial_metrics = await analytics_engine.get_metrics()
        
        # Process some order books
        for i in range(5):
            await analytics_engine.update_order_book(f"SYMBOL_{i}", sample_order_book)
        
        updated_metrics = await analytics_engine.get_metrics()
        assert updated_metrics['books_processed'] > initial_metrics['books_processed']
    
    @pytest.mark.asyncio
    async def test_cache_integration(self, sample_order_book):
        """Test cache integration"""
        # Mock cache manager
        mock_cache = AsyncMock()
        mock_cache.get.return_value = None
        mock_cache.set.return_value = None
        
        engine = OrderBookAnalyticsEngine(
            cache_manager=mock_cache,
            enable_real_time=False
        )
        await engine.start()
        
        try:
            # Update order book (should trigger cache set)
            await engine.update_order_book("AAPL", sample_order_book)
            
            # Verify cache was called
            mock_cache.set.assert_called()
            
            # Get order book (should trigger cache get)
            await engine.get_current_order_book("AAPL")
            mock_cache.get.assert_called()
            
        finally:
            await engine.stop()
    
    @pytest.mark.asyncio
    async def test_message_bus_integration(self, sample_order_book):
        """Test message bus integration"""
        # Mock message bus
        mock_bus = AsyncMock()
        mock_bus.publish.return_value = None
        
        engine = OrderBookAnalyticsEngine(
            message_bus=mock_bus,
            enable_real_time=False
        )
        await engine.start()
        
        try:
            # Update order book and trigger analysis
            await engine.update_order_book("AAPL", sample_order_book)
            await engine._analyze_spread("AAPL", sample_order_book)
            await engine._analyze_market_depth("AAPL", sample_order_book)
            await engine._analyze_imbalance("AAPL", sample_order_book)
            
            # Publish results
            await engine._publish_analysis_results("AAPL")
            
            # Verify message bus was called
            mock_bus.publish.assert_called()
            
        finally:
            await engine.stop()


class TestRealTimeProcessing:
    """Test real-time processing capabilities"""
    
    @pytest.mark.asyncio
    async def test_real_time_analysis_queue(self, sample_order_book):
        """Test real-time analysis queue processing"""
        engine = OrderBookAnalyticsEngine(
            enable_real_time=True,
            max_book_levels=10
        )
        await engine.start()
        
        try:
            # Update multiple order books rapidly
            symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]
            
            for symbol in symbols:
                book_copy = OrderBookSnapshot(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    bids=sample_order_book.bids,
                    asks=sample_order_book.asks
                )
                await engine.update_order_book(symbol, book_copy)
            
            # Wait for processing
            await asyncio.sleep(1)
            
            # Check that analyses were completed
            metrics = await engine.get_metrics()
            assert metrics['books_processed'] >= len(symbols)
            
        finally:
            await engine.stop()
    
    @pytest.mark.asyncio
    async def test_concurrent_analysis(self, sample_order_book):
        """Test concurrent analysis processing"""
        engine = OrderBookAnalyticsEngine(enable_real_time=True)
        await engine.start()
        
        try:
            # Create multiple analysis requests
            tasks = []
            for i in range(10):
                book_copy = OrderBookSnapshot(
                    symbol=f"SYMBOL_{i}",
                    timestamp=datetime.now(),
                    bids=sample_order_book.bids,
                    asks=sample_order_book.asks
                )
                task = engine.update_order_book(f"SYMBOL_{i}", book_copy)
                tasks.append(task)
            
            # Execute concurrently
            await asyncio.gather(*tasks)
            
            # Wait for processing
            await asyncio.sleep(2)
            
            # Verify all were processed
            metrics = await engine.get_metrics()
            assert metrics['books_processed'] >= 10
            
        finally:
            await engine.stop()


if __name__ == "__main__":
    pytest.main([__file__])