"""
Test suite for Execution Algorithms
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from .execution_algorithms import (
    ExecutionEngine, ExecutionParameters, ExecutionAlgorithm,
    ExecutionState, MarketCondition
)
from .smart_order_router import SmartOrderRouter, VenueInfo, VenueType


class TestExecutionAlgorithms:
    """Test cases for Execution Algorithms"""
    
    @pytest.fixture
    async def smart_router(self):
        """Create smart router for testing"""
        router = SmartOrderRouter(enable_ml_routing=False)
        
        # Add test venue
        test_venue = VenueInfo(
            venue_id="TEST_VENUE",
            venue_name="Test Venue",
            venue_type=VenueType.EXCHANGE,
            latency_ms=1.0,
            fill_rate=0.95,
            bid_price=99.95,
            ask_price=100.05,
            bid_size=1000.0,
            ask_size=1000.0,
            connection_status="connected"
        )
        await router.add_venue(test_venue)
        await router.start()
        
        yield router
        await router.stop()
    
    @pytest.fixture
    async def execution_engine(self, smart_router):
        """Create execution engine for testing"""
        engine = ExecutionEngine(
            smart_router=smart_router,
            max_concurrent_executions=10
        )
        await engine.start()
        yield engine
        await engine.stop()
    
    @pytest.mark.asyncio
    async def test_twap_execution(self, execution_engine):
        """Test TWAP algorithm execution"""
        # Create TWAP parameters
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=10)
        
        parameters = ExecutionParameters(
            algorithm=ExecutionAlgorithm.TWAP,
            total_quantity=1000.0,
            start_time=start_time,
            end_time=end_time,
            twap_interval_minutes=2,
            twap_randomization=0.1
        )
        
        # Start execution
        order_id = await execution_engine.start_execution(
            order_id="twap_test_001",
            symbol="AAPL",
            side="buy",
            parameters=parameters
        )
        
        assert order_id == "twap_test_001"
        
        # Check execution state
        execution_state = execution_engine.get_execution_state(order_id)
        assert execution_state is not None
        assert execution_state.algorithm == ExecutionAlgorithm.TWAP
        assert execution_state.total_quantity == 1000.0
        
        # Wait a bit for execution to start
        await asyncio.sleep(1)
        
        # Check that execution is active
        active_executions = execution_engine.get_active_executions()
        assert len(active_executions) > 0
        assert any(ex.order_id == order_id for ex in active_executions)
    
    @pytest.mark.asyncio
    async def test_vwap_execution(self, execution_engine):
        """Test VWAP algorithm execution"""
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=15)
        
        parameters = ExecutionParameters(
            algorithm=ExecutionAlgorithm.VWAP,
            total_quantity=2000.0,
            start_time=start_time,
            end_time=end_time,
            vwap_lookback_days=10,
            vwap_participation_rate=0.15,
            vwap_max_participation=0.25
        )
        
        order_id = await execution_engine.start_execution(
            order_id="vwap_test_001",
            symbol="AAPL",
            side="sell",
            parameters=parameters
        )
        
        execution_state = execution_engine.get_execution_state(order_id)
        assert execution_state is not None
        assert execution_state.algorithm == ExecutionAlgorithm.VWAP
        assert execution_state.total_quantity == 2000.0
    
    @pytest.mark.asyncio
    async def test_implementation_shortfall_execution(self, execution_engine):
        """Test Implementation Shortfall algorithm"""
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=20)
        
        parameters = ExecutionParameters(
            algorithm=ExecutionAlgorithm.IMPLEMENTATION_SHORTFALL,
            total_quantity=1500.0,
            start_time=start_time,
            end_time=end_time,
            is_risk_aversion=1.5,
            is_alpha=0.001,
            is_volatility=0.025
        )
        
        order_id = await execution_engine.start_execution(
            order_id="is_test_001",
            symbol="AAPL",
            side="buy",
            parameters=parameters
        )
        
        execution_state = execution_engine.get_execution_state(order_id)
        assert execution_state is not None
        assert execution_state.algorithm == ExecutionAlgorithm.IMPLEMENTATION_SHORTFALL
    
    @pytest.mark.asyncio
    async def test_adaptive_execution(self, execution_engine):
        """Test Adaptive algorithm execution"""
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=12)
        
        parameters = ExecutionParameters(
            algorithm=ExecutionAlgorithm.ADAPTIVE,
            total_quantity=800.0,
            start_time=start_time,
            end_time=end_time,
            adaptive_learning_rate=0.15,
            adaptive_min_interval=1,
            adaptive_max_interval=5
        )
        
        order_id = await execution_engine.start_execution(
            order_id="adaptive_test_001",
            symbol="AAPL",
            side="buy",
            parameters=parameters
        )
        
        execution_state = execution_engine.get_execution_state(order_id)
        assert execution_state is not None
        assert execution_state.algorithm == ExecutionAlgorithm.ADAPTIVE
    
    @pytest.mark.asyncio
    async def test_pov_execution(self, execution_engine):
        """Test POV (Percentage of Volume) algorithm"""
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=8)
        
        parameters = ExecutionParameters(
            algorithm=ExecutionAlgorithm.POV,
            total_quantity=1200.0,
            start_time=start_time,
            end_time=end_time,
            pov_target_rate=0.12,
            pov_min_rate=0.08,
            pov_max_rate=0.20
        )
        
        order_id = await execution_engine.start_execution(
            order_id="pov_test_001",
            symbol="AAPL",
            side="sell",
            parameters=parameters
        )
        
        execution_state = execution_engine.get_execution_state(order_id)
        assert execution_state is not None
        assert execution_state.algorithm == ExecutionAlgorithm.POV
    
    @pytest.mark.asyncio
    async def test_arrival_price_execution(self, execution_engine):
        """Test Arrival Price algorithm (immediate execution)"""
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=1)
        
        parameters = ExecutionParameters(
            algorithm=ExecutionAlgorithm.ARRIVAL_PRICE,
            total_quantity=500.0,
            start_time=start_time,
            end_time=end_time
        )
        
        order_id = await execution_engine.start_execution(
            order_id="arrival_test_001",
            symbol="AAPL",
            side="buy",
            parameters=parameters
        )
        
        execution_state = execution_engine.get_execution_state(order_id)
        assert execution_state is not None
        assert execution_state.algorithm == ExecutionAlgorithm.ARRIVAL_PRICE
        
        # Arrival price should execute immediately
        await asyncio.sleep(2)
        
        # Check if execution completed
        updated_state = execution_engine.get_execution_state(order_id)
        assert updated_state.executed_quantity > 0
    
    @pytest.mark.asyncio
    async def test_iceberg_execution(self, execution_engine):
        """Test Iceberg algorithm execution"""
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=15)
        
        parameters = ExecutionParameters(
            algorithm=ExecutionAlgorithm.ICEBERG,
            total_quantity=3000.0,
            start_time=start_time,
            end_time=end_time,
            metadata={'iceberg_ratio': 0.15}  # 15% slice size
        )
        
        order_id = await execution_engine.start_execution(
            order_id="iceberg_test_001",
            symbol="AAPL",
            side="buy",
            parameters=parameters
        )
        
        execution_state = execution_engine.get_execution_state(order_id)
        assert execution_state is not None
        assert execution_state.algorithm == ExecutionAlgorithm.ICEBERG
    
    @pytest.mark.asyncio
    async def test_execution_control(self, execution_engine):
        """Test execution control (pause, resume, cancel)"""
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=30)
        
        parameters = ExecutionParameters(
            algorithm=ExecutionAlgorithm.TWAP,
            total_quantity=1000.0,
            start_time=start_time,
            end_time=end_time,
            twap_interval_minutes=5
        )
        
        order_id = await execution_engine.start_execution(
            order_id="control_test_001",
            symbol="AAPL",
            side="buy",
            parameters=parameters
        )
        
        # Test pause
        result = await execution_engine.pause_execution(order_id)
        assert result is True
        
        execution_state = execution_engine.get_execution_state(order_id)
        assert execution_state.state == ExecutionState.PAUSED
        
        # Test resume
        result = await execution_engine.resume_execution(order_id)
        assert result is True
        
        execution_state = execution_engine.get_execution_state(order_id)
        assert execution_state.state == ExecutionState.RUNNING
        
        # Test cancel
        result = await execution_engine.cancel_execution(order_id)
        assert result is True
        
        # Should be moved to history
        execution_state = execution_engine.get_execution_state(order_id)
        assert execution_state.state == ExecutionState.CANCELLED
    
    @pytest.mark.asyncio
    async def test_parameter_validation(self, execution_engine):
        """Test execution parameter validation"""
        # Invalid quantity
        with pytest.raises(ValueError):
            parameters = ExecutionParameters(
                algorithm=ExecutionAlgorithm.TWAP,
                total_quantity=-100.0,  # Invalid negative quantity
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(minutes=10)
            )
            await execution_engine.start_execution(
                order_id="invalid_test_001",
                symbol="AAPL",
                side="buy",
                parameters=parameters
            )
        
        # Invalid time range
        with pytest.raises(ValueError):
            parameters = ExecutionParameters(
                algorithm=ExecutionAlgorithm.TWAP,
                total_quantity=1000.0,
                start_time=datetime.now() + timedelta(minutes=10),
                end_time=datetime.now()  # End before start
            )
            await execution_engine.start_execution(
                order_id="invalid_test_002",
                symbol="AAPL",
                side="buy",
                parameters=parameters
            )
        
        # Past end time
        with pytest.raises(ValueError):
            parameters = ExecutionParameters(
                algorithm=ExecutionAlgorithm.TWAP,
                total_quantity=1000.0,
                start_time=datetime.now() - timedelta(minutes=20),
                end_time=datetime.now() - timedelta(minutes=10)  # In the past
            )
            await execution_engine.start_execution(
                order_id="invalid_test_003",
                symbol="AAPL",
                side="buy",
                parameters=parameters
            )
    
    @pytest.mark.asyncio
    async def test_market_data_update(self, execution_engine):
        """Test market data updates"""
        # Update market data
        market_data = {
            'bid_price': 99.90,
            'ask_price': 100.10,
            'mid_price': 100.00,
            'volume': 75000.0,
            'volatility': 0.025
        }
        
        await execution_engine.update_market_data("AAPL", market_data)
        
        # Verify data was updated
        retrieved_data = await execution_engine._get_market_data("AAPL")
        assert retrieved_data['bid_price'] == 99.90
        assert retrieved_data['ask_price'] == 100.10
        assert retrieved_data['volume'] == 75000.0
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self, execution_engine):
        """Test performance metrics collection"""
        # Start a few executions to generate metrics
        for i in range(3):
            start_time = datetime.now()
            end_time = start_time + timedelta(minutes=5)
            
            parameters = ExecutionParameters(
                algorithm=ExecutionAlgorithm.ARRIVAL_PRICE,
                total_quantity=100.0 * (i + 1),
                start_time=start_time,
                end_time=end_time
            )
            
            await execution_engine.start_execution(
                order_id=f"metrics_test_{i}",
                symbol="AAPL",
                side="buy",
                parameters=parameters
            )
        
        # Wait for executions to process
        await asyncio.sleep(2)
        
        # Check metrics
        metrics = execution_engine.get_performance_metrics()
        assert 'total_executions' in metrics
        assert 'completed_executions' in metrics
        assert 'avg_execution_time_minutes' in metrics
        assert 'total_volume_executed' in metrics
        
        assert metrics['total_executions'] >= 3
    
    @pytest.mark.asyncio
    async def test_volume_profile_generation(self, execution_engine):
        """Test volume profile generation"""
        # Test volume profile retrieval
        volume_profile = await execution_engine._get_volume_profile("AAPL", 5)
        
        assert not volume_profile.empty
        assert 'datetime' in volume_profile.columns
        assert 'volume' in volume_profile.columns
        assert 'hour' in volume_profile.columns
        
        # Test volume distribution calculation
        start_time = datetime.now().replace(hour=9, minute=30, second=0, microsecond=0)
        end_time = start_time + timedelta(hours=2)
        
        distribution = execution_engine._calculate_volume_distribution(
            volume_profile, start_time, end_time, 4
        )
        
        assert len(distribution) == 4
        assert abs(sum(distribution) - 1.0) < 0.01  # Should sum to 1
        assert all(d >= 0 for d in distribution)  # All non-negative
    
    @pytest.mark.asyncio
    async def test_market_condition_detection(self, execution_engine):
        """Test market condition detection"""
        # Test with normal conditions
        condition = await execution_engine._detect_market_condition("AAPL")
        assert isinstance(condition, MarketCondition)
        
        # Test with high volatility data
        high_vol_data = {
            'volatility': 0.05,  # High volatility
            'volume': 50000.0,
            'avg_volume': 100000.0
        }
        await execution_engine.update_market_data("AAPL", high_vol_data)
        
        condition = await execution_engine._detect_market_condition("AAPL")
        assert condition == MarketCondition.VOLATILE
        
        # Test with high volume data
        high_vol_data = {
            'volatility': 0.015,  # Normal volatility
            'volume': 250000.0,  # High volume
            'avg_volume': 100000.0
        }
        await execution_engine.update_market_data("AAPL", high_vol_data)
        
        condition = await execution_engine._detect_market_condition("AAPL")
        assert condition == MarketCondition.HIGH_VOLUME
    
    @pytest.mark.asyncio
    async def test_implementation_shortfall_calculation(self, execution_engine):
        """Test implementation shortfall calculation"""
        # Create mock execution state
        execution_state = ExecutionState(
            order_id="is_calc_test",
            algorithm=ExecutionAlgorithm.IMPLEMENTATION_SHORTFALL,
            state=ExecutionState.RUNNING,
            total_quantity=1000.0,
            executed_quantity=600.0,
            remaining_quantity=400.0,
            avg_execution_price=100.50
        )
        
        arrival_price = 100.00
        current_price = 100.25
        
        is_value = execution_engine._calculate_implementation_shortfall(
            execution_state, arrival_price, current_price
        )
        
        # Should be positive (we paid more than arrival price)
        assert is_value > 0
        assert isinstance(is_value, float)
    
    @pytest.mark.asyncio
    async def test_concurrent_executions(self, execution_engine):
        """Test concurrent execution handling"""
        # Start multiple executions concurrently
        tasks = []
        for i in range(5):
            start_time = datetime.now()
            end_time = start_time + timedelta(minutes=3)
            
            parameters = ExecutionParameters(
                algorithm=ExecutionAlgorithm.ARRIVAL_PRICE,
                total_quantity=200.0 + i * 50,
                start_time=start_time,
                end_time=end_time
            )
            
            task = execution_engine.start_execution(
                order_id=f"concurrent_test_{i}",
                symbol="AAPL",
                side="buy" if i % 2 == 0 else "sell",
                parameters=parameters
            )
            tasks.append(task)
        
        # Wait for all to start
        order_ids = await asyncio.gather(*tasks)
        
        assert len(order_ids) == 5
        assert all(oid.startswith("concurrent_test_") for oid in order_ids)
        
        # Check that all executions are tracked
        active_executions = execution_engine.get_active_executions()
        assert len(active_executions) >= 5
    
    def test_algorithm_info(self, execution_engine):
        """Test algorithm information retrieval"""
        info = execution_engine.get_algorithm_info()
        
        assert 'algorithms' in info
        assert 'descriptions' in info
        
        assert 'twap' in info['algorithms']
        assert 'vwap' in info['algorithms']
        assert 'implementation_shortfall' in info['algorithms']
        assert 'adaptive' in info['algorithms']
        
        assert 'twap' in info['descriptions']
        assert len(info['descriptions']['twap']) > 0


@pytest.mark.asyncio
async def test_execution_engine_integration():
    """Integration test for Execution Engine"""
    # Create smart router
    router = SmartOrderRouter(enable_ml_routing=False)
    
    # Add test venue
    test_venue = VenueInfo(
        venue_id="INTEGRATION_VENUE",
        venue_name="Integration Test Venue",
        venue_type=VenueType.EXCHANGE,
        latency_ms=2.0,
        fill_rate=0.9,
        bid_price=100.0,
        ask_price=100.05,
        bid_size=2000.0,
        ask_size=2000.0,
        connection_status="connected"
    )
    
    try:
        await router.add_venue(test_venue)
        await router.start()
        
        # Create execution engine
        engine = ExecutionEngine(smart_router=router)
        await engine.start()
        
        # Test TWAP execution
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=5)
        
        parameters = ExecutionParameters(
            algorithm=ExecutionAlgorithm.TWAP,
            total_quantity=1000.0,
            start_time=start_time,
            end_time=end_time,
            twap_interval_minutes=1
        )
        
        order_id = await engine.start_execution(
            order_id="integration_test",
            symbol="TEST",
            side="buy",
            parameters=parameters
        )
        
        assert order_id == "integration_test"
        
        # Check execution state
        execution_state = engine.get_execution_state(order_id)
        assert execution_state is not None
        assert execution_state.total_quantity == 1000.0
        
        # Wait a bit for execution to progress
        await asyncio.sleep(2)
        
        # Check metrics
        metrics = engine.get_performance_metrics()
        assert metrics['total_executions'] >= 1
        
        await engine.stop()
        
    finally:
        await router.stop()


if __name__ == "__main__":
    # Run basic integration test
    asyncio.run(test_execution_engine_integration())
    print("Execution Algorithms integration test passed!")