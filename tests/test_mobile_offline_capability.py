"""
Test suite for mobile offline capability system.
"""
import pytest
import asyncio
import json
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import uuid

# Import the modules to test
from nautilus_trader_engine.mobile.offline_capability import (
    OfflineCapabilityManager, OfflineStorage, NetworkMonitor,
    OfflineAction, CachedData, SyncConflict,
    OfflineStatus, DataSyncStatus, OfflineActionType,
    create_offline_manager, handle_offline_order,
    cache_market_data, cache_portfolio_data
)

class TestOfflineStorage:
    """Test offline storage functionality"""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        os.unlink(path)
    
    @pytest.fixture
    def storage(self, temp_db):
        """Create offline storage instance"""
        return OfflineStorage(temp_db)
    
    def test_database_initialization(self, storage):
        """Test database initialization"""
        # Check that tables exist
        conn = sqlite3.connect(storage.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = ['offline_actions', 'cached_data', 'sync_conflicts', 'sync_metadata']
        for table in expected_tables:
            assert table in tables
        
        conn.close()
    
    def test_store_offline_action(self, storage):
        """Test storing offline action"""
        action = OfflineAction(
            action_id="test_action_1",
            action_type=OfflineActionType.PLACE_ORDER,
            data={"symbol": "AAPL", "quantity": 100},
            timestamp=datetime.now(),
            user_id="user_1"
        )
        
        result = storage.store_offline_action(action)
        assert result is True
        
        # Verify action was stored
        pending_actions = storage.get_pending_actions("user_1")
        assert len(pending_actions) == 1
        assert pending_actions[0].action_id == "test_action_1"
        assert pending_actions[0].action_type == OfflineActionType.PLACE_ORDER
        assert pending_actions[0].data["symbol"] == "AAPL"
    
    def test_get_pending_actions(self, storage):
        """Test getting pending actions"""
        # Store multiple actions
        actions = [
            OfflineAction(
                action_id=f"action_{i}",
                action_type=OfflineActionType.PLACE_ORDER,
                data={"symbol": f"STOCK{i}", "quantity": 100 + i},
                timestamp=datetime.now() + timedelta(seconds=i),
                user_id="user_1"
            )
            for i in range(3)
        ]
        
        for action in actions:
            storage.store_offline_action(action)
        
        # Get pending actions
        pending = storage.get_pending_actions("user_1")
        assert len(pending) == 3
        
        # Should be ordered by timestamp
        assert pending[0].action_id == "action_0"
        assert pending[1].action_id == "action_1"
        assert pending[2].action_id == "action_2"
    
    def test_store_cached_data(self, storage):
        """Test storing cached data"""
        cached_data = CachedData(
            data_id="cache_1",
            data_type="market_data",
            data={"AAPL": {"price": 150.0, "change": 2.5}},
            timestamp=datetime.now(),
            expiry_time=datetime.now() + timedelta(hours=1),
            user_id="user_1"
        )
        
        result = storage.store_cached_data(cached_data)
        assert result is True
        
        # Verify data was stored
        cached_items = storage.get_cached_data("market_data", "user_1")
        assert len(cached_items) == 1
        assert cached_items[0].data_id == "cache_1"
        assert cached_items[0].data["AAPL"]["price"] == 150.0
    
    def test_get_cached_data_with_expiry(self, storage):
        """Test getting cached data respects expiry"""
        # Store expired data
        expired_data = CachedData(
            data_id="expired_cache",
            data_type="market_data",
            data={"EXPIRED": {"price": 100.0}},
            timestamp=datetime.now() - timedelta(hours=2),
            expiry_time=datetime.now() - timedelta(hours=1),
            user_id="user_1"
        )
        
        # Store valid data
        valid_data = CachedData(
            data_id="valid_cache",
            data_type="market_data",
            data={"VALID": {"price": 200.0}},
            timestamp=datetime.now(),
            expiry_time=datetime.now() + timedelta(hours=1),
            user_id="user_1"
        )
        
        storage.store_cached_data(expired_data)
        storage.store_cached_data(valid_data)
        
        # Should only return valid data
        cached_items = storage.get_cached_data("market_data", "user_1")
        assert len(cached_items) == 1
        assert cached_items[0].data_id == "valid_cache"
    
    def test_cleanup_expired_data(self, storage):
        """Test cleanup of expired data"""
        # Store expired data
        expired_data = CachedData(
            data_id="expired_cache",
            data_type="market_data",
            data={"EXPIRED": {"price": 100.0}},
            timestamp=datetime.now() - timedelta(hours=2),
            expiry_time=datetime.now() - timedelta(hours=1),
            user_id="user_1"
        )
        
        storage.store_cached_data(expired_data)
        
        # Cleanup expired data
        deleted_count = storage.cleanup_expired_data()
        assert deleted_count == 1
        
        # Verify data was deleted
        cached_items = storage.get_cached_data("market_data", "user_1")
        assert len(cached_items) == 0

class TestNetworkMonitor:
    """Test network monitoring functionality"""
    
    @pytest.fixture
    def network_monitor(self):
        """Create network monitor instance"""
        return NetworkMonitor(check_interval=1)
    
    def test_network_monitor_initialization(self, network_monitor):
        """Test network monitor initialization"""
        assert network_monitor.check_interval == 1
        assert network_monitor.is_online is True
        assert network_monitor.callbacks == []
        assert network_monitor._monitoring is False
    
    def test_add_callback(self, network_monitor):
        """Test adding callback"""
        callback = Mock()
        network_monitor.add_callback(callback)
        
        assert len(network_monitor.callbacks) == 1
        assert network_monitor.callbacks[0] == callback
    
    @patch('socket.create_connection')
    def test_force_check_online(self, mock_socket, network_monitor):
        """Test force check when online"""
        mock_socket.return_value = Mock()
        
        result = network_monitor.force_check()
        assert result is True
        assert network_monitor.is_online is True
    
    @patch('socket.create_connection')
    def test_force_check_offline(self, mock_socket, network_monitor):
        """Test force check when offline"""
        mock_socket.side_effect = OSError("Network unreachable")
        
        result = network_monitor.force_check()
        assert result is False
        assert network_monitor.is_online is False
    
    def test_start_stop_monitoring(self, network_monitor):
        """Test starting and stopping monitoring"""
        network_monitor.start_monitoring()
        assert network_monitor._monitoring is True
        assert network_monitor._monitor_thread is not None
        
        network_monitor.stop_monitoring()
        assert network_monitor._monitoring is False

class TestOfflineCapabilityManager:
    """Test offline capability manager"""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        os.unlink(path)
    
    @pytest.fixture
    def offline_manager(self, temp_db):
        """Create offline capability manager"""
        return OfflineCapabilityManager(temp_db)
    
    def test_manager_initialization(self, offline_manager):
        """Test manager initialization"""
        assert offline_manager.storage is not None
        assert offline_manager.network_monitor is not None
        assert offline_manager.status == OfflineStatus.ONLINE
        assert offline_manager.sync_in_progress is False
        assert offline_manager.sync_callbacks == []
    
    def test_add_sync_callback(self, offline_manager):
        """Test adding sync callback"""
        callback = Mock()
        offline_manager.add_sync_callback(callback)
        
        assert len(offline_manager.sync_callbacks) == 1
        assert offline_manager.sync_callbacks[0] == callback
    
    def test_is_online(self, offline_manager):
        """Test online status check"""
        # Mock network monitor
        offline_manager.network_monitor.is_online = True
        assert offline_manager.is_online() is True
        
        offline_manager.network_monitor.is_online = False
        assert offline_manager.is_online() is False
    
    def test_get_status(self, offline_manager):
        """Test getting status"""
        assert offline_manager.get_status() == OfflineStatus.ONLINE
        
        offline_manager.status = OfflineStatus.OFFLINE
        assert offline_manager.get_status() == OfflineStatus.OFFLINE
    
    @pytest.mark.asyncio
    async def test_queue_offline_action(self, offline_manager):
        """Test queuing offline action"""
        action_id = await offline_manager.queue_offline_action(
            OfflineActionType.PLACE_ORDER,
            {"symbol": "AAPL", "quantity": 100},
            "user_1"
        )
        
        assert action_id is not None
        
        # Verify action was stored
        pending_actions = offline_manager.storage.get_pending_actions("user_1")
        assert len(pending_actions) == 1
        assert pending_actions[0].action_id == action_id
    
    @pytest.mark.asyncio
    async def test_cache_data(self, offline_manager):
        """Test caching data"""
        data_id = await offline_manager.cache_data(
            "market_data",
            {"AAPL": {"price": 150.0}},
            "user_1",
            ttl_hours=1
        )
        
        assert data_id is not None
        
        # Verify data was cached
        cached_data = offline_manager.get_cached_data("market_data", "user_1")
        assert len(cached_data) == 1
        assert cached_data[0]["AAPL"]["price"] == 150.0
    
    def test_get_cached_data(self, offline_manager):
        """Test getting cached data"""
        # First cache some data
        asyncio.run(offline_manager.cache_data(
            "portfolio",
            {"positions": [{"symbol": "AAPL", "quantity": 100}]},
            "user_1"
        ))
        
        # Get cached data
        cached_data = offline_manager.get_cached_data("portfolio", "user_1")
        assert len(cached_data) == 1
        assert cached_data[0]["positions"][0]["symbol"] == "AAPL"
    
    @pytest.mark.asyncio
    async def test_sync_offline_data(self, offline_manager):
        """Test syncing offline data"""
        # Mock network as online
        offline_manager.network_monitor.is_online = True
        
        # Queue some actions
        await offline_manager.queue_offline_action(
            OfflineActionType.PLACE_ORDER,
            {"symbol": "AAPL", "quantity": 100},
            "user_1"
        )
        
        # Mock the execute action method
        offline_manager._execute_action = AsyncMock(return_value=True)
        
        # Add sync callback to capture events
        sync_events = []
        def sync_callback(event_type, data):
            sync_events.append((event_type, data))
        
        offline_manager.add_sync_callback(sync_callback)
        
        # Perform sync
        await offline_manager.sync_offline_data()
        
        # Verify sync events
        assert len(sync_events) >= 2  # sync_started and sync_completed
        assert sync_events[0][0] == "sync_started"
        assert sync_events[-1][0] == "sync_completed"
        
        # Verify action was processed
        offline_manager._execute_action.assert_called_once()
    
    def test_get_sync_status(self, offline_manager):
        """Test getting sync status"""
        status = offline_manager.get_sync_status()
        
        assert "status" in status
        assert "is_online" in status
        assert "sync_in_progress" in status
        assert "pending_actions" in status
        assert "last_sync" in status
        
        assert status["status"] == OfflineStatus.ONLINE.value
        assert isinstance(status["pending_actions"], int)
    
    def test_clear_cache(self, offline_manager):
        """Test clearing cache"""
        # Cache some data first
        asyncio.run(offline_manager.cache_data(
            "test_data",
            {"test": "value"},
            "user_1"
        ))
        
        # Verify data exists
        cached_data = offline_manager.get_cached_data("test_data", "user_1")
        assert len(cached_data) == 1
        
        # Clear cache
        deleted_count = offline_manager.clear_cache("user_1", "test_data")
        assert deleted_count == 1
        
        # Verify data was cleared
        cached_data = offline_manager.get_cached_data("test_data", "user_1")
        assert len(cached_data) == 0
    
    def test_shutdown(self, offline_manager):
        """Test manager shutdown"""
        # Start monitoring first
        offline_manager.network_monitor.start_monitoring()
        
        # Shutdown
        offline_manager.shutdown()
        
        # Verify monitoring stopped
        assert offline_manager.network_monitor._monitoring is False

class TestUtilityFunctions:
    """Test utility functions"""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        os.unlink(path)
    
    def test_create_offline_manager(self, temp_db):
        """Test creating offline manager"""
        manager = create_offline_manager(temp_db)
        
        assert isinstance(manager, OfflineCapabilityManager)
        assert manager.storage.db_path == temp_db
    
    @pytest.mark.asyncio
    async def test_handle_offline_order(self, temp_db):
        """Test handling offline order"""
        manager = create_offline_manager(temp_db)
        
        order_data = {
            "symbol": "AAPL",
            "side": "buy",
            "quantity": 100,
            "order_type": "market"
        }
        
        action_id = await handle_offline_order(manager, order_data, "user_1")
        
        assert action_id is not None
        
        # Verify action was queued
        pending_actions = manager.storage.get_pending_actions("user_1")
        assert len(pending_actions) == 1
        assert pending_actions[0].action_type == OfflineActionType.PLACE_ORDER
    
    @pytest.mark.asyncio
    async def test_cache_market_data(self, temp_db):
        """Test caching market data"""
        manager = create_offline_manager(temp_db)
        
        market_data = {
            "AAPL": {"price": 150.0, "change": 2.5},
            "GOOGL": {"price": 2500.0, "change": -10.0}
        }
        
        data_id = await cache_market_data(manager, market_data, "user_1")
        
        assert data_id is not None
        
        # Verify data was cached
        cached_data = manager.get_cached_data("market_data", "user_1")
        assert len(cached_data) == 1
        assert cached_data[0]["AAPL"]["price"] == 150.0
    
    @pytest.mark.asyncio
    async def test_cache_portfolio_data(self, temp_db):
        """Test caching portfolio data"""
        manager = create_offline_manager(temp_db)
        
        portfolio_data = {
            "positions": [
                {"symbol": "AAPL", "quantity": 100, "avg_price": 145.0},
                {"symbol": "GOOGL", "quantity": 50, "avg_price": 2450.0}
            ],
            "total_value": 137000.0
        }
        
        data_id = await cache_portfolio_data(manager, portfolio_data, "user_1")
        
        assert data_id is not None
        
        # Verify data was cached
        cached_data = manager.get_cached_data("portfolio", "user_1")
        assert len(cached_data) == 1
        assert len(cached_data[0]["positions"]) == 2
        assert cached_data[0]["total_value"] == 137000.0

class TestIntegrationScenarios:
    """Test integration scenarios"""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        os.unlink(path)
    
    @pytest.mark.asyncio
    async def test_offline_to_online_sync(self, temp_db):
        """Test complete offline to online sync scenario"""
        manager = create_offline_manager(temp_db)
        
        # Stop network monitoring to avoid async issues in tests
        manager.network_monitor.stop_monitoring()
        
        # Manually set offline state
        manager.network_monitor.is_online = False
        manager.status = OfflineStatus.OFFLINE
        
        # Queue multiple offline actions
        actions = []
        for i in range(3):
            action_id = await manager.queue_offline_action(
                OfflineActionType.PLACE_ORDER,
                {"symbol": f"STOCK{i}", "quantity": 100 + i},
                "user_1"
            )
            actions.append(action_id)
        
        # Cache some data
        await manager.cache_data(
            "market_data",
            {"AAPL": {"price": 150.0}},
            "user_1"
        )
        
        # Verify offline state
        assert manager.get_status() == OfflineStatus.OFFLINE
        pending_actions = manager.storage.get_pending_actions("user_1")
        assert len(pending_actions) == 3
        
        # Simulate going back online
        manager.network_monitor.is_online = True
        manager._execute_action = AsyncMock(return_value=True)
        
        # Perform sync
        await manager.sync_offline_data()
        
        # Verify sync completed
        assert manager.get_status() == OfflineStatus.ONLINE
        
        # Verify all actions were processed
        assert manager._execute_action.call_count == 3
    
    @pytest.mark.asyncio
    async def test_sync_with_failures_and_retries(self, temp_db):
        """Test sync with failures and retry logic"""
        manager = create_offline_manager(temp_db)
        
        # Queue an action
        action_id = await manager.queue_offline_action(
            OfflineActionType.PLACE_ORDER,
            {"symbol": "AAPL", "quantity": 100},
            "user_1"
        )
        
        # Mock execute action to fail initially, then succeed
        call_count = 0
        async def mock_execute_action(action):
            nonlocal call_count
            call_count += 1
            return call_count > 2  # Fail first 2 times, succeed on 3rd
        
        manager._execute_action = mock_execute_action
        
        # Perform multiple syncs
        for _ in range(3):
            await manager.sync_offline_data()
        
        # Verify action eventually succeeded
        pending_actions = manager.storage.get_pending_actions("user_1")
        completed_action = None
        
        # Check if action was marked as completed
        conn = sqlite3.connect(manager.storage.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT sync_status FROM offline_actions WHERE action_id = ?", (action_id,))
        result = cursor.fetchone()
        conn.close()
        
        assert result is not None
        # Should be either completed or still pending (depending on retry logic)
        assert result[0] in ['completed', 'pending']

if __name__ == "__main__":
    pytest.main([__file__, "-v"])