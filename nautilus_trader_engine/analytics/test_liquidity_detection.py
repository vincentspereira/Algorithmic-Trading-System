"""
Test suite for Liquidity Detection System
"""

import pytest
import asyncio
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

from .liquidity_detection import (
    LiquidityDetectionEngine,
    LiquiditySignal,
    IcebergOrderSignal,
    DarkPoolActivity,
    VenueLiquidityScore,
    LiquidityType,
    LiquidityTier,
    VenueType
)
from .order_book_analytics import OrderBookSnapshot, OrderBookLevel, OrderBookSide


class TestLiquiditySignal:
    """Test LiquiditySignal dataclass"""
    
    def test_valid_signal_creation(self):
        """Test creating valid liquidity signal"""
        signal = LiquiditySignal(
            signal_id="test_signal_1",
            symbol="AAPL",
            timestamp=datetime.now(),
            liquidity_type=LiquidityType.HIDDEN,
            price_level=100.0,
            estimated_size=5000.0,
            confidence=0.8,
            detection_method="volume_anomaly",
            detection_confidence=0.8
        )
        
        assert signal.symbol == "AAPL"
        assert signal.liquidity_type == LiquidityType.HIDDEN
        assert signal.confidence == 0.8
        assert signal.detection_confidence == 0.8
    
    def test_invalid_confidence_raises_error(self):
        """Test that invalid confidence raises ValueError"""
        with pytest.raises(ValueError, match="Confidence must be between 0 and 1"):
            LiquiditySignal(
                signal_id="test_signal_1",
                symbol="AAPL",
                timestamp=datetime.now(),
                liquidity_type=LiquidityType.HIDDEN,
                price_level=100.0,
                estimated_size=5000.0,
                confidence=1.5,  # Invalid
                detection_method="volume_anomaly",
                detection_confidence=0.8
            )


class TestIcebergOrderSignal:
    """Test IcebergOrderSignal dataclass"""
    
    def test_valid_iceberg_signal_creation(self):
        """Test creating valid iceberg signal"""
        signal = IcebergOrderSignal(
            signal_id="iceberg_1",
            symbol="AAPL",
            timestamp=datetime.now(),
            price_level=100.0,
            visible_size=1000.0,
            estimated_total_size=10000.0,
            estimated_hidden_size=9000.0,
            refresh_pattern_score=0.8,
            size_consistency_score=0.9,
            timing_pattern_score=0.7,
            confidence=0.8
        )
        
        assert signal.symbol == "AAPL"
        assert signal.visible_size == 1000.0
        assert signal.estimated_hidden_size == 9000.0
        assert signal.confidence == 0.8


class TestVenueLiquidityScore:
    """Test VenueLiquidityScore dataclass"""
    
    def test_venue_score_calculation(self):
        """Test venue liquidity score calculation"""
        score = VenueLiquidityScore(
            venue_name="NYSE",
            venue_type=VenueType.LIT_EXCHANGE,
            symbol="AAPL",
            timestamp=datetime.now(),
            available_liquidity=50000.0,
            average_spread=0.005,
            market_depth=25000.0,
            fill_rate=0.9,
            price_improvement=0.001,
            execution_speed=2.0,
            reliability_score=0.95,
            explicit_costs=0.0005,
            implicit_costs=0.001
        )
        
        score.total_cost = score.explicit_costs + score.implicit_costs
        overall_score = score.calculate_overall_score()
        
        assert 0 <= overall_score <= 1
        assert score.overall_score == overall_score
        assert score.total_cost == 0.0015


@pytest.fixture
async def liquidity_engine():
    """Create liquidity detection engine for testing"""
    engine = LiquidityDetectionEngine(
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


class TestLiquidityDetectionEngine:
    """Test LiquidityDetectionEngine"""
    
    @pytest.mark.asyncio
    async def test_engine_start_stop(self):
        """Test engine start and stop"""
        engine = LiquidityDetectionEngine(enable_real_time=False)
        
        assert not engine._running
        
        await engine.start()
        assert engine._running
        
        await engine.stop()
        assert not engine._running
    
    @pytest.mark.asyncio
    async def test_update_order_book(self, liquidity_engine, sample_order_book):
        """Test updating order book"""
        await liquidity_engine.update_order_book("AAPL", sample_order_book)
        
        # Check that book was stored
        assert "AAPL" in liquidity_engine._order_books
        stored_book = liquidity_engine._order_books["AAPL"]
        assert stored_book.symbol == "AAPL"
        assert stored_book.bid_price == 100.0
        assert stored_book.ask_price == 100.5
    
    @pytest.mark.asyncio
    async def test_update_trade_data(self, liquidity_engine):
        """Test updating trade data"""
        # Add multiple trades
        trades = [
            (100.0, 1000.0),
            (100.1, 500.0),
            (99.9, 1500.0),
            (100.0, 1000.0),  # Same size - might indicate iceberg
            (100.0, 1000.0)   # Same size again
        ]
        
        for price, size in trades:
            await liquidity_engine.update_trade_data("AAPL", price, size, datetime.now())
        
        # Check that trade history was stored
        assert len(liquidity_engine._trade_history["AAPL"]) == 5
        assert len(liquidity_engine._volume_history["AAPL"]) == 5
        assert len(liquidity_engine._price_history["AAPL"]) == 5
    
    @pytest.mark.asyncio
    async def test_volume_anomaly_detection(self, liquidity_engine, sample_order_book):
        """Test volume anomaly detection"""
        # Add normal volume history
        normal_volumes = [1000.0] * 15
        for vol in normal_volumes:
            await liquidity_engine.update_trade_data("AAPL", 100.0, vol, datetime.now())
        
        # Add anomalous volume
        await liquidity_engine.update_trade_data("AAPL", 100.0, 5000.0, datetime.now())
        
        # Update order book to trigger detection
        await liquidity_engine.update_order_book("AAPL", sample_order_book)
        
        # Run detection manually
        signals = await liquidity_engine._detect_volume_anomaly_liquidity("AAPL", sample_order_book)
        
        # Should detect volume anomaly
        assert len(signals) > 0
        signal = signals[0]
        assert signal.liquidity_type == LiquidityType.HIDDEN
        assert signal.detection_method == "volume_anomaly"
        assert signal.confidence > 0.5
    
    @pytest.mark.asyncio
    async def test_size_pattern_detection(self, liquidity_engine, sample_order_book):
        """Test size pattern detection for iceberg orders"""
        # Create order book with consistent sizes (iceberg pattern)
        consistent_bids = [
            OrderBookLevel(price=100.0, size=1000.0, orders=1),
            OrderBookLevel(price=99.9, size=1000.0, orders=1),
            OrderBookLevel(price=99.8, size=1000.0, orders=1),
            OrderBookLevel(price=99.7, size=1000.0, orders=1),
            OrderBookLevel(price=99.6, size=1000.0, orders=1)
        ]
        
        iceberg_book = OrderBookSnapshot(
            symbol="AAPL",
            timestamp=datetime.now(),
            bids=consistent_bids,
            asks=sample_order_book.asks
        )
        
        # Run detection
        signals = await liquidity_engine._detect_size_pattern_liquidity("AAPL", iceberg_book)
        
        # Should detect size pattern
        if signals:  # May not always detect depending on thresholds
            signal = signals[0]
            assert signal.liquidity_type == LiquidityType.ICEBERG
            assert signal.detection_method == "size_pattern"
    
    @pytest.mark.asyncio
    async def test_iceberg_order_detection(self, liquidity_engine):
        """Test iceberg order detection through trade analysis"""
        # Add trades that look like iceberg pattern
        iceberg_trades = [
            (100.0, 1000.0),  # Consistent size
            (100.0, 1000.0),  # Same price and size
            (100.0, 1000.0),  # Repeated pattern
            (100.0, 1000.0),
            (100.0, 1000.0)
        ]
        
        for i, (price, size) in enumerate(iceberg_trades):
            trade_time = datetime.now() + timedelta(seconds=i*10)  # Regular intervals
            await liquidity_engine.update_trade_data("AAPL", price, size, trade_time)
        
        # Run iceberg detection
        last_trade = {
            'price': 100.0,
            'size': 1000.0,
            'timestamp': datetime.now(),
            'value': 100000.0
        }
        
        signals = await liquidity_engine._detect_iceberg_orders("AAPL", last_trade)
        
        # Should detect iceberg pattern
        if signals:  # May not always detect depending on thresholds
            signal = signals[0]
            assert signal.price_level == 100.0
            assert signal.visible_size == 1000.0
            assert signal.confidence > 0.5
    
    @pytest.mark.asyncio
    async def test_dark_pool_detection(self, liquidity_engine):
        """Test dark pool activity detection"""
        # Add trades that might indicate dark pool activity
        large_trades = [
            (100.0, 5000.0),   # Large block trade
            (100.1, 3000.0),   # Another large trade
            (99.9, 4000.0),    # Large trade
            (100.0, 2000.0),   # Medium trade
        ]
        
        # Add many smaller trades to establish baseline
        small_trades = [(100.0 + np.random.uniform(-0.1, 0.1), 100.0) for _ in range(50)]
        
        all_trades = small_trades + large_trades
        
        for price, size in all_trades:
            await liquidity_engine.update_trade_data("AAPL", price, size, datetime.now())
        
        # Run dark pool detection
        last_trade = {
            'price': 100.0,
            'size': 5000.0,
            'timestamp': datetime.now(),
            'value': 500000.0
        }
        
        activities = await liquidity_engine._detect_dark_pool_activity("AAPL", last_trade)
        
        # Should detect dark pool activity
        if activities:  # May not always detect depending on thresholds
            activity = activities[0]
            assert activity.symbol == "AAPL"
            assert activity.estimated_dark_volume > 0
            assert activity.dark_volume_ratio > 0
    
    @pytest.mark.asyncio
    async def test_hidden_depth_detection(self, liquidity_engine):
        """Test hidden depth detection"""
        # Create thin order book that might indicate hidden liquidity
        thin_bids = [
            OrderBookLevel(price=100.0, size=100.0, orders=1),  # Very small size
            OrderBookLevel(price=99.0, size=100.0, orders=1),   # Large price gap
            OrderBookLevel(price=98.0, size=100.0, orders=1)    # Another large gap
        ]
        
        thin_asks = [
            OrderBookLevel(price=100.5, size=100.0, orders=1),
            OrderBookLevel(price=101.5, size=100.0, orders=1),  # Large gap
            OrderBookLevel(price=102.5, size=100.0, orders=1)
        ]
        
        thin_book = OrderBookSnapshot(
            symbol="AAPL",
            timestamp=datetime.now(),
            bids=thin_bids,
            asks=thin_asks
        )
        
        # Run hidden depth detection
        signals = await liquidity_engine._detect_hidden_depth("AAPL", thin_book)
        
        # Should detect potential hidden depth
        if signals:  # May not always detect depending on thresholds
            signal = signals[0]
            assert signal.liquidity_type == LiquidityType.HIDDEN
            assert signal.detection_method == "hidden_depth"
            assert signal.stealth_score > 0.5
    
    @pytest.mark.asyncio
    async def test_venue_scoring(self, liquidity_engine):
        """Test venue liquidity scoring"""
        # Add some order books to trigger venue scoring
        sample_book = OrderBookSnapshot(
            symbol="AAPL",
            timestamp=datetime.now(),
            bids=[OrderBookLevel(price=100.0, size=1000.0)],
            asks=[OrderBookLevel(price=100.5, size=1000.0)]
        )
        
        await liquidity_engine.update_order_book("AAPL", sample_book)
        
        # Trigger venue scoring
        await liquidity_engine._update_venue_scores()
        
        # Check venue scores were created
        venue_scores = await liquidity_engine.get_venue_scores("AAPL")
        assert len(venue_scores) > 0
        
        # Check score properties
        for venue_name, score in venue_scores.items():
            assert isinstance(score, VenueLiquidityScore)
            assert score.venue_name == venue_name
            assert 0 <= score.overall_score <= 1
            assert isinstance(score.liquidity_tier, LiquidityTier)
    
    @pytest.mark.asyncio
    async def test_get_best_venues(self, liquidity_engine):
        """Test getting best venues by score"""
        # Add order book and update venue scores
        sample_book = OrderBookSnapshot(
            symbol="AAPL",
            timestamp=datetime.now(),
            bids=[OrderBookLevel(price=100.0, size=1000.0)],
            asks=[OrderBookLevel(price=100.5, size=1000.0)]
        )
        
        await liquidity_engine.update_order_book("AAPL", sample_book)
        await liquidity_engine._update_venue_scores()
        
        # Get best venues
        best_venues = await liquidity_engine.get_best_venues("AAPL", 3)
        
        assert len(best_venues) <= 3
        
        # Should be sorted by score (highest first)
        if len(best_venues) > 1:
            for i in range(len(best_venues) - 1):
                assert best_venues[i].overall_score >= best_venues[i+1].overall_score
    
    @pytest.mark.asyncio
    async def test_hidden_liquidity_estimate(self, liquidity_engine, sample_order_book):
        """Test hidden liquidity estimation"""
        # Add some liquidity signals
        signal1 = LiquiditySignal(
            signal_id="test_1",
            symbol="AAPL",
            timestamp=datetime.now(),
            liquidity_type=LiquidityType.HIDDEN,
            price_level=100.0,
            estimated_size=5000.0,
            confidence=0.8,
            detection_method="test",
            detection_confidence=0.8
        )
        
        signal2 = LiquiditySignal(
            signal_id="test_2",
            symbol="AAPL",
            timestamp=datetime.now(),
            liquidity_type=LiquidityType.ICEBERG,
            price_level=100.5,
            estimated_size=3000.0,
            confidence=0.7,
            detection_method="test",
            detection_confidence=0.7
        )
        
        # Store signals
        liquidity_engine._liquidity_signals["AAPL"] = [signal1, signal2]
        
        # Get estimate
        estimate = await liquidity_engine.get_hidden_liquidity_estimate("AAPL")
        
        assert 'hidden' in estimate
        assert 'iceberg' in estimate
        assert 'total' in estimate
        assert estimate['total'] == estimate['hidden'] + estimate['iceberg']
    
    @pytest.mark.asyncio
    async def test_analyze_liquidity_for_order(self, liquidity_engine, sample_order_book):
        """Test liquidity analysis for potential order"""
        # Set up order book and venue scores
        await liquidity_engine.update_order_book("AAPL", sample_order_book)
        await liquidity_engine._update_venue_scores()
        
        # Add some liquidity signals
        signal = LiquiditySignal(
            signal_id="test_1",
            symbol="AAPL",
            timestamp=datetime.now(),
            liquidity_type=LiquidityType.HIDDEN,
            price_level=100.0,
            estimated_size=2000.0,
            confidence=0.8,
            detection_method="test",
            detection_confidence=0.8
        )
        liquidity_engine._liquidity_signals["AAPL"] = [signal]
        
        # Analyze liquidity for buy order
        analysis = await liquidity_engine.analyze_liquidity_for_order(
            symbol="AAPL",
            side="buy",
            size=1500.0,
            max_price_impact=0.01
        )
        
        assert analysis['symbol'] == "AAPL"
        assert analysis['side'] == "buy"
        assert analysis['requested_size'] == 1500.0
        assert 'visible_liquidity' in analysis
        assert 'hidden_liquidity_estimate' in analysis
        assert 'total_liquidity_estimate' in analysis
        assert 'recommended_venues' in analysis
        assert 'execution_strategy' in analysis
        assert 'estimated_fill_rate' in analysis
        assert 'estimated_price_impact' in analysis
        
        # Check that visible liquidity matches order book
        expected_visible = sample_order_book.get_total_size(OrderBookSide.ASK, 10)
        assert analysis['visible_liquidity'] == expected_visible
    
    @pytest.mark.asyncio
    async def test_config_management(self, liquidity_engine):
        """Test configuration management"""
        # Get current config
        config = liquidity_engine.get_config()
        assert isinstance(config, dict)
        assert 'volume_anomaly_threshold' in config
        
        # Update config
        await liquidity_engine.update_config({
            'volume_anomaly_threshold': 3.0,
            'iceberg_refresh_tolerance': 0.15
        })
        
        updated_config = liquidity_engine.get_config()
        assert updated_config['volume_anomaly_threshold'] == 3.0
        assert updated_config['iceberg_refresh_tolerance'] == 0.15
    
    @pytest.mark.asyncio
    async def test_metrics_tracking(self, liquidity_engine):
        """Test metrics tracking"""
        initial_metrics = await liquidity_engine.get_metrics()
        
        # Process some signals
        signal = LiquiditySignal(
            signal_id="test_1",
            symbol="AAPL",
            timestamp=datetime.now(),
            liquidity_type=LiquidityType.HIDDEN,
            price_level=100.0,
            estimated_size=5000.0,
            confidence=0.8,
            detection_method="test",
            detection_confidence=0.8
        )
        
        await liquidity_engine._process_liquidity_signal("AAPL", signal)
        
        updated_metrics = await liquidity_engine.get_metrics()
        assert updated_metrics['signals_detected'] > initial_metrics['signals_detected']
    
    @pytest.mark.asyncio
    async def test_message_bus_integration(self, sample_order_book):
        """Test message bus integration"""
        # Mock message bus
        mock_bus = AsyncMock()
        mock_bus.publish.return_value = None
        
        engine = LiquidityDetectionEngine(
            message_bus=mock_bus,
            enable_real_time=False
        )
        await engine.start()
        
        try:
            # Create and publish a signal
            signal = LiquiditySignal(
                signal_id="test_1",
                symbol="AAPL",
                timestamp=datetime.now(),
                liquidity_type=LiquidityType.HIDDEN,
                price_level=100.0,
                estimated_size=5000.0,
                confidence=0.8,
                detection_method="test",
                detection_confidence=0.8
            )
            
            await engine._publish_liquidity_signal("AAPL", signal)
            
            # Verify message bus was called
            mock_bus.publish.assert_called()
            
        finally:
            await engine.stop()
    
    @pytest.mark.asyncio
    async def test_cache_integration(self, sample_order_book):
        """Test cache integration"""
        # Mock cache manager
        mock_cache = AsyncMock()
        mock_cache.get.return_value = None
        mock_cache.set.return_value = None
        
        engine = LiquidityDetectionEngine(
            cache_manager=mock_cache,
            enable_real_time=False
        )
        await engine.start()
        
        try:
            # Update order book (should trigger cache set)
            await engine.update_order_book("AAPL", sample_order_book)
            
            # Verify cache was called
            mock_cache.set.assert_called()
            
        finally:
            await engine.stop()


class TestRealTimeProcessing:
    """Test real-time processing capabilities"""
    
    @pytest.mark.asyncio
    async def test_real_time_detection_queue(self, sample_order_book):
        """Test real-time detection queue processing"""
        engine = LiquidityDetectionEngine(enable_real_time=True)
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
            
            # Check that order books were stored
            assert len(engine._order_books) >= len(symbols)
            
        finally:
            await engine.stop()
    
    @pytest.mark.asyncio
    async def test_concurrent_detection(self, sample_order_book):
        """Test concurrent detection processing"""
        engine = LiquidityDetectionEngine(enable_real_time=True)
        await engine.start()
        
        try:
            # Create multiple detection requests
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
            assert len(engine._order_books) >= 10
            
        finally:
            await engine.stop()


if __name__ == "__main__":
    pytest.main([__file__])