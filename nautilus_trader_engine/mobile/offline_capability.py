"""
Mobile Offline Capability System
Provides offline functionality for mobile trading app including data caching,
offline order queuing, and synchronization when connection is restored.
"""
import logging
import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
from pathlib import Path
import threading
import time

class OfflineStatus(Enum):
    """Offline status types"""
    ONLINE = "online"
    OFFLINE = "offline"
    SYNCING = "syncing"
    SYNC_ERROR = "sync_error"

class DataSyncStatus(Enum):
    """Data synchronization status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"

class OfflineActionType(Enum):
    """Types of offline actions"""
    PLACE_ORDER = "place_order"
    CANCEL_ORDER = "cancel_order"
    MODIFY_ORDER = "modify_order"
    ADD_TO_WATCHLIST = "add_to_watchlist"
    REMOVE_FROM_WATCHLIST = "remove_from_watchlist"
    UPDATE_PREFERENCES = "update_preferences"

@dataclass
class OfflineAction:
    """Offline action to be synchronized"""
    action_id: str
    action_type: OfflineActionType
    data: Dict[str, Any]
    timestamp: datetime
    user_id: str
    sync_status: DataSyncStatus = DataSyncStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None

@dataclass
class CachedData:
    """Cached data structure"""
    data_id: str
    data_type: str
    data: Dict[str, Any]
    timestamp: datetime
    expiry_time: datetime
    user_id: str
    is_dirty: bool = False  # Modified while offline

@dataclass
class SyncConflict:
    """Data synchronization conflict"""
    conflict_id: str
    data_type: str
    local_data: Dict[str, Any]
    server_data: Dict[str, Any]
    timestamp: datetime
    user_id: str
    resolution_strategy: str = "server_wins"  # server_wins, client_wins, merge

class OfflineStorage:
    """SQLite-based offline storage"""
    
    def __init__(self, db_path: str = "mobile_offline.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS offline_actions (
                    action_id TEXT PRIMARY KEY,
                    action_type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    sync_status TEXT DEFAULT 'pending',
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    error_message TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cached_data (
                    data_id TEXT PRIMARY KEY,
                    data_type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    expiry_time TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    is_dirty INTEGER DEFAULT 0
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sync_conflicts (
                    conflict_id TEXT PRIMARY KEY,
                    data_type TEXT NOT NULL,
                    local_data TEXT NOT NULL,
                    server_data TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    resolution_strategy TEXT DEFAULT 'server_wins'
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sync_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
            raise
    
    def store_offline_action(self, action: OfflineAction) -> bool:
        """Store offline action"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO offline_actions 
                (action_id, action_type, data, timestamp, user_id, sync_status, retry_count, max_retries, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                action.action_id,
                action.action_type.value,
                json.dumps(action.data),
                action.timestamp.isoformat(),
                action.user_id,
                action.sync_status.value,
                action.retry_count,
                action.max_retries,
                action.error_message
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing offline action: {e}")
            return False
    
    def get_pending_actions(self, user_id: str = None) -> List[OfflineAction]:
        """Get pending offline actions"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if user_id:
                cursor.execute('''
                    SELECT * FROM offline_actions 
                    WHERE sync_status = 'pending' AND user_id = ?
                    ORDER BY timestamp ASC
                ''', (user_id,))
            else:
                cursor.execute('''
                    SELECT * FROM offline_actions 
                    WHERE sync_status = 'pending'
                    ORDER BY timestamp ASC
                ''')
            
            actions = []
            for row in cursor.fetchall():
                action = OfflineAction(
                    action_id=row[0],
                    action_type=OfflineActionType(row[1]),
                    data=json.loads(row[2]),
                    timestamp=datetime.fromisoformat(row[3]),
                    user_id=row[4],
                    sync_status=DataSyncStatus(row[5]),
                    retry_count=row[6],
                    max_retries=row[7],
                    error_message=row[8]
                )
                actions.append(action)
            
            conn.close()
            return actions
            
        except Exception as e:
            self.logger.error(f"Error getting pending actions: {e}")
            return []
    
    def store_cached_data(self, cached_data: CachedData) -> bool:
        """Store cached data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO cached_data 
                (data_id, data_type, data, timestamp, expiry_time, user_id, is_dirty)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                cached_data.data_id,
                cached_data.data_type,
                json.dumps(cached_data.data),
                cached_data.timestamp.isoformat(),
                cached_data.expiry_time.isoformat(),
                cached_data.user_id,
                1 if cached_data.is_dirty else 0
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing cached data: {e}")
            return False
    
    def get_cached_data(self, data_type: str, user_id: str) -> List[CachedData]:
        """Get cached data by type and user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM cached_data 
                WHERE data_type = ? AND user_id = ? AND expiry_time > ?
                ORDER BY timestamp DESC
            ''', (data_type, user_id, datetime.now().isoformat()))
            
            cached_items = []
            for row in cursor.fetchall():
                cached_data = CachedData(
                    data_id=row[0],
                    data_type=row[1],
                    data=json.loads(row[2]),
                    timestamp=datetime.fromisoformat(row[3]),
                    expiry_time=datetime.fromisoformat(row[4]),
                    user_id=row[5],
                    is_dirty=bool(row[6])
                )
                cached_items.append(cached_data)
            
            conn.close()
            return cached_items
            
        except Exception as e:
            self.logger.error(f"Error getting cached data: {e}")
            return []
    
    def cleanup_expired_data(self) -> int:
        """Clean up expired cached data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM cached_data 
                WHERE expiry_time < ?
            ''', (datetime.now().isoformat(),))
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Error cleaning up expired data: {e}")
            return 0

class NetworkMonitor:
    """Network connectivity monitor"""
    
    def __init__(self, check_interval: int = 5):
        self.check_interval = check_interval
        self.is_online = True
        self.logger = logging.getLogger(__name__)
        self.callbacks: List[Callable[[bool], None]] = []
        self._monitoring = False
        self._monitor_thread = None
    
    def add_callback(self, callback: Callable[[bool], None]):
        """Add callback for connectivity changes"""
        self.callbacks.append(callback)
    
    def start_monitoring(self):
        """Start network monitoring"""
        if not self._monitoring:
            self._monitoring = True
            self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop network monitoring"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1)
    
    def _monitor_loop(self):
        """Network monitoring loop"""
        while self._monitoring:
            try:
                # Simple connectivity check (in production, use more robust methods)
                import socket
                socket.create_connection(("8.8.8.8", 53), timeout=3)
                new_status = True
            except (socket.error, OSError):
                new_status = False
            
            if new_status != self.is_online:
                self.is_online = new_status
                self.logger.info(f"Network status changed: {'online' if new_status else 'offline'}")
                
                # Notify callbacks
                for callback in self.callbacks:
                    try:
                        callback(new_status)
                    except Exception as e:
                        self.logger.error(f"Error in network callback: {e}")
            
            time.sleep(self.check_interval)
    
    def force_check(self) -> bool:
        """Force immediate connectivity check"""
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            self.is_online = True
            return True
        except (socket.error, OSError):
            self.is_online = False
            return False

class OfflineCapabilityManager:
    """Main offline capability manager"""
    
    def __init__(self, db_path: str = "mobile_offline.db"):
        self.storage = OfflineStorage(db_path)
        self.network_monitor = NetworkMonitor()
        self.logger = logging.getLogger(__name__)
        self.status = OfflineStatus.ONLINE
        self.sync_in_progress = False
        self.sync_callbacks: List[Callable[[str, Any], None]] = []
        
        # Setup network monitoring
        self.network_monitor.add_callback(self._on_network_change)
        self.network_monitor.start_monitoring()
    
    def add_sync_callback(self, callback: Callable[[str, Any], None]):
        """Add callback for sync events"""
        self.sync_callbacks.append(callback)
    
    def _notify_sync_event(self, event_type: str, data: Any):
        """Notify sync event callbacks"""
        for callback in self.sync_callbacks:
            try:
                callback(event_type, data)
            except Exception as e:
                self.logger.error(f"Error in sync callback: {e}")
    
    def _on_network_change(self, is_online: bool):
        """Handle network connectivity changes"""
        if is_online:
            self.status = OfflineStatus.ONLINE
            self.logger.info("Network connection restored, starting sync...")
            asyncio.create_task(self.sync_offline_data())
        else:
            self.status = OfflineStatus.OFFLINE
            self.logger.info("Network connection lost, switching to offline mode")
        
        self._notify_sync_event("network_change", {"is_online": is_online})
    
    def is_online(self) -> bool:
        """Check if currently online"""
        return self.network_monitor.is_online
    
    def get_status(self) -> OfflineStatus:
        """Get current offline status"""
        return self.status
    
    async def queue_offline_action(self, action_type: OfflineActionType, 
                                 data: Dict[str, Any], user_id: str) -> str:
        """Queue an action for offline execution"""
        action = OfflineAction(
            action_id=str(uuid.uuid4()),
            action_type=action_type,
            data=data,
            timestamp=datetime.now(),
            user_id=user_id
        )
        
        if self.storage.store_offline_action(action):
            self.logger.info(f"Queued offline action: {action_type.value}")
            self._notify_sync_event("action_queued", {"action_id": action.action_id})
            
            # If online, try to sync immediately
            if self.is_online() and not self.sync_in_progress:
                asyncio.create_task(self.sync_offline_data())
            
            return action.action_id
        else:
            raise Exception("Failed to queue offline action")
    
    async def cache_data(self, data_type: str, data: Dict[str, Any], 
                        user_id: str, ttl_hours: int = 24) -> str:
        """Cache data for offline access"""
        cached_data = CachedData(
            data_id=str(uuid.uuid4()),
            data_type=data_type,
            data=data,
            timestamp=datetime.now(),
            expiry_time=datetime.now() + timedelta(hours=ttl_hours),
            user_id=user_id
        )
        
        if self.storage.store_cached_data(cached_data):
            self.logger.debug(f"Cached data: {data_type}")
            return cached_data.data_id
        else:
            raise Exception("Failed to cache data")
    
    def get_cached_data(self, data_type: str, user_id: str) -> List[Dict[str, Any]]:
        """Get cached data for offline access"""
        cached_items = self.storage.get_cached_data(data_type, user_id)
        return [item.data for item in cached_items]
    
    async def sync_offline_data(self):
        """Synchronize offline data with server"""
        if self.sync_in_progress or not self.is_online():
            return
        
        self.sync_in_progress = True
        self.status = OfflineStatus.SYNCING
        self._notify_sync_event("sync_started", {})
        
        try:
            # Get pending actions
            pending_actions = self.storage.get_pending_actions()
            
            sync_results = {
                "successful": 0,
                "failed": 0,
                "conflicts": 0
            }
            
            for action in pending_actions:
                try:
                    # Simulate API call (replace with actual API calls)
                    success = await self._execute_action(action)
                    
                    if success:
                        action.sync_status = DataSyncStatus.COMPLETED
                        sync_results["successful"] += 1
                        self.logger.info(f"Synced action: {action.action_id}")
                    else:
                        action.retry_count += 1
                        if action.retry_count >= action.max_retries:
                            action.sync_status = DataSyncStatus.FAILED
                            sync_results["failed"] += 1
                        else:
                            action.sync_status = DataSyncStatus.PENDING
                    
                    # Update action in storage
                    self.storage.store_offline_action(action)
                    
                except Exception as e:
                    self.logger.error(f"Error syncing action {action.action_id}: {e}")
                    action.retry_count += 1
                    action.error_message = str(e)
                    
                    if action.retry_count >= action.max_retries:
                        action.sync_status = DataSyncStatus.FAILED
                        sync_results["failed"] += 1
                    
                    self.storage.store_offline_action(action)
            
            # Clean up expired cached data
            expired_count = self.storage.cleanup_expired_data()
            if expired_count > 0:
                self.logger.info(f"Cleaned up {expired_count} expired cache entries")
            
            self.status = OfflineStatus.ONLINE
            self._notify_sync_event("sync_completed", sync_results)
            
        except Exception as e:
            self.logger.error(f"Error during sync: {e}")
            self.status = OfflineStatus.SYNC_ERROR
            self._notify_sync_event("sync_error", {"error": str(e)})
        
        finally:
            self.sync_in_progress = False
    
    async def _execute_action(self, action: OfflineAction) -> bool:
        """Execute offline action (simulate API call)"""
        # In a real implementation, this would make actual API calls
        # For now, we'll simulate success/failure
        
        await asyncio.sleep(0.1)  # Simulate network delay
        
        # Simulate 90% success rate
        import random
        return random.random() < 0.9
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get synchronization status"""
        pending_actions = self.storage.get_pending_actions()
        
        return {
            "status": self.status.value,
            "is_online": self.is_online(),
            "sync_in_progress": self.sync_in_progress,
            "pending_actions": len(pending_actions),
            "last_sync": datetime.now().isoformat()  # In production, track actual last sync
        }
    
    def force_sync(self):
        """Force immediate synchronization"""
        if self.is_online() and not self.sync_in_progress:
            asyncio.create_task(self.sync_offline_data())
        else:
            self.logger.warning("Cannot force sync: offline or sync already in progress")
    
    def clear_cache(self, user_id: str = None, data_type: str = None):
        """Clear cached data"""
        try:
            conn = sqlite3.connect(self.storage.db_path)
            cursor = conn.cursor()
            
            if user_id and data_type:
                cursor.execute('DELETE FROM cached_data WHERE user_id = ? AND data_type = ?', 
                             (user_id, data_type))
            elif user_id:
                cursor.execute('DELETE FROM cached_data WHERE user_id = ?', (user_id,))
            elif data_type:
                cursor.execute('DELETE FROM cached_data WHERE data_type = ?', (data_type,))
            else:
                cursor.execute('DELETE FROM cached_data')
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            self.logger.info(f"Cleared {deleted_count} cache entries")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Error clearing cache: {e}")
            return 0
    
    def shutdown(self):
        """Shutdown offline capability manager"""
        self.network_monitor.stop_monitoring()
        self.logger.info("Offline capability manager shutdown")

# Utility functions for mobile app integration
def create_offline_manager(db_path: str = "mobile_offline.db") -> OfflineCapabilityManager:
    """Create offline capability manager"""
    return OfflineCapabilityManager(db_path)

async def handle_offline_order(manager: OfflineCapabilityManager, 
                             order_data: Dict[str, Any], user_id: str) -> str:
    """Handle order placement in offline mode"""
    return await manager.queue_offline_action(
        OfflineActionType.PLACE_ORDER,
        order_data,
        user_id
    )

async def cache_market_data(manager: OfflineCapabilityManager,
                          market_data: Dict[str, Any], user_id: str) -> str:
    """Cache market data for offline access"""
    return await manager.cache_data("market_data", market_data, user_id, ttl_hours=1)

async def cache_portfolio_data(manager: OfflineCapabilityManager,
                             portfolio_data: Dict[str, Any], user_id: str) -> str:
    """Cache portfolio data for offline access"""
    return await manager.cache_data("portfolio", portfolio_data, user_id, ttl_hours=24)

if __name__ == "__main__":
    # Example usage
    async def main():
        manager = create_offline_manager()
        
        # Add sync callback
        def sync_callback(event_type: str, data: Any):
            print(f"Sync event: {event_type}, data: {data}")
        
        manager.add_sync_callback(sync_callback)
        
        # Queue some offline actions
        await manager.queue_offline_action(
            OfflineActionType.PLACE_ORDER,
            {"symbol": "AAPL", "quantity": 100, "side": "buy"},
            "user_1"
        )
        
        # Cache some data
        await manager.cache_data(
            "positions",
            {"AAPL": {"quantity": 100, "avg_price": 150.0}},
            "user_1"
        )
        
        # Get sync status
        status = manager.get_sync_status()
        print(f"Sync status: {status}")
        
        # Wait a bit then shutdown
        await asyncio.sleep(2)
        manager.shutdown()
    
    asyncio.run(main())