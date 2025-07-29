"""
Cache Coherency Manager
Ensures consistency across multi-level cache hierarchy
"""

import asyncio
import time
import hashlib
from typing import List, Optional, Dict, Any, Set
from dataclasses import dataclass
from enum import Enum
import logging


class CoherencyEvent(Enum):
    """Types of coherency events"""
    INVALIDATE = "invalidate"
    UPDATE = "update"
    DELETE = "delete"
    CLEAR = "clear"


@dataclass
class CoherencyMessage:
    """Message for cache coherency coordination"""
    event: CoherencyEvent
    key: Optional[str] = None
    keys: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    timestamp: float = 0.0
    source_level: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class CacheCoherencyManager:
    """
    Manages coherency across multiple cache levels
    
    Features:
    - Automatic invalidation propagation
    - Version-based consistency checking
    - Write-through and write-back policies
    - Conflict resolution
    - Performance monitoring
    """
    
    def __init__(self, cache_levels: List[Any], check_interval: int = 60):
        self.cache_levels = [cache for cache in cache_levels if cache is not None]
        self.check_interval = check_interval
        
        # Coherency tracking
        self._version_map: Dict[str, int] = {}
        self._pending_invalidations: Set[str] = set()
        
        # Background tasks
        self._coherency_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Statistics
        self._invalidations_sent = 0
        self._invalidations_received = 0
        self._conflicts_resolved = 0
        self._coherency_violations = 0
        
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Start coherency management"""
        if self._running:
            return
        
        self._running = True
        
        # Start background coherency checker
        self._coherency_task = asyncio.create_task(self._coherency_worker())
        
        self.logger.info("Cache coherency manager started")
    
    async def stop(self):
        """Stop coherency management"""
        self._running = False
        
        if self._coherency_task:
            self._coherency_task.cancel()
            try:
                await self._coherency_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Cache coherency manager stopped")
    
    async def on_cache_write(self, key: str, value: Any, source_level: int):
        """Handle cache write event for coherency"""
        try:
            # Update version
            self._version_map[key] = self._version_map.get(key, 0) + 1
            current_version = self._version_map[key]
            
            # Propagate to other levels based on write policy
            await self._propagate_write(key, value, source_level, current_version)
            
        except Exception as e:
            self.logger.error(f"Error handling cache write for key {key}: {e}")
    
    async def on_cache_delete(self, key: str, source_level: int):
        """Handle cache delete event for coherency"""
        try:
            # Remove from version map
            self._version_map.pop(key, None)
            
            # Propagate deletion to all levels
            message = CoherencyMessage(
                event=CoherencyEvent.DELETE,
                key=key,
                source_level=f"L{source_level}"
            )
            
            await self._broadcast_coherency_message(message, exclude_level=source_level)
            self._invalidations_sent += 1
            
        except Exception as e:
            self.logger.error(f"Error handling cache delete for key {key}: {e}")
    
    async def on_cache_invalidate(self, keys: Optional[List[str]] = None, tags: Optional[List[str]] = None):
        """Handle cache invalidation event"""
        try:
            message = CoherencyMessage(
                event=CoherencyEvent.INVALIDATE,
                keys=keys,
                tags=tags
            )
            
            await self._broadcast_coherency_message(message)
            
            # Update tracking
            if keys:
                for key in keys:
                    self._pending_invalidations.add(key)
                    self._version_map.pop(key, None)
            
            self._invalidations_sent += 1
            
        except Exception as e:
            self.logger.error(f"Error handling cache invalidation: {e}")
    
    async def on_cache_clear(self, source_level: Optional[int] = None):
        """Handle cache clear event"""
        try:
            message = CoherencyMessage(
                event=CoherencyEvent.CLEAR,
                source_level=f"L{source_level}" if source_level else None
            )
            
            await self._broadcast_coherency_message(message, exclude_level=source_level)
            
            # Clear tracking data
            self._version_map.clear()
            self._pending_invalidations.clear()
            
        except Exception as e:
            self.logger.error(f"Error handling cache clear: {e}")
    
    async def check_coherency(self, key: str) -> bool:
        """Check if key is coherent across all cache levels"""
        try:
            values = {}
            versions = {}
            
            # Get value and version from each level
            for i, cache_level in enumerate(self.cache_levels):
                level_name = f"L{i+1}"
                
                if hasattr(cache_level, 'get'):
                    value = await cache_level.get(key)
                    if value is not None:
                        values[level_name] = value
                        # Get version if available
                        if hasattr(cache_level, 'get_version'):
                            versions[level_name] = await cache_level.get_version(key)
                        else:
                            # Use content hash as version
                            versions[level_name] = self._hash_value(value)
            
            # Check if all versions match
            if len(set(versions.values())) <= 1:
                return True
            
            # Coherency violation detected
            self._coherency_violations += 1
            self.logger.warning(f"Coherency violation detected for key {key}: {versions}")
            
            # Resolve conflict
            await self._resolve_coherency_conflict(key, values, versions)
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking coherency for key {key}: {e}")
            return False
    
    async def _propagate_write(self, key: str, value: Any, source_level: int, version: int):
        """Propagate write to appropriate cache levels"""
        try:
            # Write-through policy: propagate to lower levels
            for i, cache_level in enumerate(self.cache_levels):
                level_num = i + 1
                
                if level_num <= source_level:
                    continue  # Skip source and higher levels
                
                if hasattr(cache_level, 'set'):
                    await cache_level.set(key, value)
                    
                    # Set version if supported
                    if hasattr(cache_level, 'set_version'):
                        await cache_level.set_version(key, version)
            
        except Exception as e:
            self.logger.error(f"Error propagating write for key {key}: {e}")
    
    async def _broadcast_coherency_message(self, message: CoherencyMessage, exclude_level: Optional[int] = None):
        """Broadcast coherency message to all cache levels"""
        try:
            for i, cache_level in enumerate(self.cache_levels):
                level_num = i + 1
                
                if exclude_level and level_num == exclude_level:
                    continue
                
                await self._send_coherency_message(cache_level, message)
            
        except Exception as e:
            self.logger.error(f"Error broadcasting coherency message: {e}")
    
    async def _send_coherency_message(self, cache_level: Any, message: CoherencyMessage):
        """Send coherency message to specific cache level"""
        try:
            if message.event == CoherencyEvent.DELETE and message.key:
                if hasattr(cache_level, 'delete'):
                    await cache_level.delete(message.key)
            
            elif message.event == CoherencyEvent.INVALIDATE:
                if message.keys and hasattr(cache_level, 'delete_many'):
                    # Batch delete if supported
                    await cache_level.delete_many(message.keys)
                elif message.keys:
                    # Individual deletes
                    for key in message.keys:
                        if hasattr(cache_level, 'delete'):
                            await cache_level.delete(key)
                
                if message.tags and hasattr(cache_level, 'invalidate_by_tags'):
                    await cache_level.invalidate_by_tags(message.tags)
            
            elif message.event == CoherencyEvent.CLEAR:
                if hasattr(cache_level, 'clear'):
                    await cache_level.clear()
            
        except Exception as e:
            self.logger.error(f"Error sending coherency message to cache level: {e}")
    
    async def _resolve_coherency_conflict(self, key: str, values: Dict[str, Any], versions: Dict[str, Any]):
        """Resolve coherency conflict using conflict resolution strategy"""
        try:
            # Strategy: Use the value from the highest level (L1 > L2 > L3)
            resolution_order = ['L1', 'L2', 'L3']
            
            authoritative_value = None
            authoritative_level = None
            
            for level in resolution_order:
                if level in values:
                    authoritative_value = values[level]
                    authoritative_level = level
                    break
            
            if authoritative_value is None:
                # No value found, delete from all levels
                await self.on_cache_delete(key, source_level=0)
                return
            
            # Propagate authoritative value to all other levels
            new_version = self._version_map.get(key, 0) + 1
            self._version_map[key] = new_version
            
            for i, cache_level in enumerate(self.cache_levels):
                level_name = f"L{i+1}"
                
                if level_name == authoritative_level:
                    continue  # Skip authoritative level
                
                if hasattr(cache_level, 'set'):
                    await cache_level.set(key, authoritative_value)
                    
                    if hasattr(cache_level, 'set_version'):
                        await cache_level.set_version(key, new_version)
            
            self._conflicts_resolved += 1
            self.logger.info(f"Resolved coherency conflict for key {key} using value from {authoritative_level}")
            
        except Exception as e:
            self.logger.error(f"Error resolving coherency conflict for key {key}: {e}")
    
    async def _coherency_worker(self):
        """Background worker for coherency checking"""
        while self._running:
            try:
                await self._periodic_coherency_check()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Coherency worker error: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _periodic_coherency_check(self):
        """Perform periodic coherency check on random sample of keys"""
        try:
            # Get sample of keys from version map
            sample_keys = list(self._version_map.keys())[:100]  # Check up to 100 keys
            
            violations = 0
            for key in sample_keys:
                if not await self.check_coherency(key):
                    violations += 1
            
            if violations > 0:
                self.logger.warning(f"Periodic coherency check found {violations} violations out of {len(sample_keys)} keys")
            
        except Exception as e:
            self.logger.error(f"Error in periodic coherency check: {e}")
    
    def _hash_value(self, value: Any) -> str:
        """Generate hash of value for version comparison"""
        try:
            import pickle
            serialized = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
            return hashlib.md5(serialized).hexdigest()
        except Exception:
            return hashlib.md5(str(value).encode('utf-8')).hexdigest()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get coherency statistics"""
        return {
            'cache_levels': len(self.cache_levels),
            'tracked_keys': len(self._version_map),
            'pending_invalidations': len(self._pending_invalidations),
            'invalidations_sent': self._invalidations_sent,
            'invalidations_received': self._invalidations_received,
            'conflicts_resolved': self._conflicts_resolved,
            'coherency_violations': self._coherency_violations,
            'check_interval_seconds': self.check_interval
        }
    
    async def force_coherency_check(self, keys: Optional[List[str]] = None):
        """Force coherency check on specific keys or all tracked keys"""
        try:
            check_keys = keys or list(self._version_map.keys())
            violations = 0
            
            for key in check_keys:
                if not await self.check_coherency(key):
                    violations += 1
            
            self.logger.info(f"Forced coherency check completed: {violations} violations found in {len(check_keys)} keys")
            
            return violations
            
        except Exception as e:
            self.logger.error(f"Error in forced coherency check: {e}")
            return -1