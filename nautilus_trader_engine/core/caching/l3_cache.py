"""
L3 Cache Implementation
Persistent database-backed cache for long-term data storage
"""

import asyncio
import json
import pickle
import sqlite3
import time
from typing import Any, Optional, Dict, List, Set
from dataclasses import dataclass
import logging
import threading

try:
    import aiosqlite
    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False
    aiosqlite = None


@dataclass
class CacheRecord:
    """Database cache record structure"""
    key: str
    value: bytes
    created_at: float
    accessed_at: float
    access_count: int
    ttl: Optional[int]
    tags: str  # JSON string of tags
    size: int


class L3Cache:
    """
    Persistent L3 cache using SQLite/Database
    
    Features:
    - Persistent storage across restarts
    - SQL-based querying and analytics
    - Tag-based invalidation
    - Automatic cleanup of expired entries
    - Batch operations
    - Size-based eviction
    """
    
    def __init__(self, 
                 database_url: str = "sqlite:///cache.db",
                 max_size: int = 1000000,
                 ttl: int = 86400,
                 cleanup_interval: int = 3600):
        
        if not SQLITE_AVAILABLE:
            raise ImportError("aiosqlite is required for L3Cache. Install with: pip install aiosqlite")
        
        self.database_url = database_url
        self.max_size = max_size
        self.default_ttl = ttl
        self.cleanup_interval = cleanup_interval
        
        # Extract database path from URL
        if database_url.startswith("sqlite:///"):
            self.db_path = database_url[10:]  # Remove "sqlite:///"
        else:
            self.db_path = "cache.db"
        
        # Database connection
        self.db: Optional[aiosqlite.Connection] = None
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._sets = 0
        self._deletes = 0
        self._evictions = 0
        self._errors = 0
        
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Initialize database connection and schema"""
        try:
            self.db = await aiosqlite.connect(self.db_path)
            
            # Enable WAL mode for better concurrency
            await self.db.execute("PRAGMA journal_mode=WAL")
            await self.db.execute("PRAGMA synchronous=NORMAL")
            await self.db.execute("PRAGMA cache_size=10000")
            await self.db.execute("PRAGMA temp_store=MEMORY")
            
            # Create schema
            await self._create_schema()
            
            # Start background cleanup task
            self._running = True
            self._cleanup_task = asyncio.create_task(self._cleanup_worker())
            
            self.logger.info(f"L3Cache initialized with database: {self.db_path}")
        
        except Exception as e:
            self.logger.error(f"Failed to initialize L3Cache: {e}")
            raise
    
    async def stop(self):
        """Close database connection and cleanup"""
        self._running = False
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self.db:
            await self.db.close()
        
        self.logger.info("L3Cache stopped")
    
    async def _create_schema(self):
        """Create database schema"""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS cache_entries (
            key TEXT PRIMARY KEY,
            value BLOB NOT NULL,
            created_at REAL NOT NULL,
            accessed_at REAL NOT NULL,
            access_count INTEGER NOT NULL DEFAULT 1,
            ttl INTEGER,
            tags TEXT,
            size INTEGER NOT NULL DEFAULT 0
        );
        
        CREATE INDEX IF NOT EXISTS idx_cache_accessed_at ON cache_entries(accessed_at);
        CREATE INDEX IF NOT EXISTS idx_cache_created_at ON cache_entries(created_at);
        CREATE INDEX IF NOT EXISTS idx_cache_ttl ON cache_entries(ttl);
        CREATE INDEX IF NOT EXISTS idx_cache_size ON cache_entries(size);
        
        CREATE TABLE IF NOT EXISTS cache_tags (
            tag TEXT NOT NULL,
            key TEXT NOT NULL,
            PRIMARY KEY (tag, key),
            FOREIGN KEY (key) REFERENCES cache_entries(key) ON DELETE CASCADE
        );
        
        CREATE INDEX IF NOT EXISTS idx_cache_tags_tag ON cache_tags(tag);
        CREATE INDEX IF NOT EXISTS idx_cache_tags_key ON cache_tags(key);
        """
        
        await self.db.executescript(schema_sql)
        await self.db.commit()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from database cache"""
        if not self.db:
            return None
        
        try:
            # Get entry from database
            cursor = await self.db.execute(
                "SELECT value, created_at, ttl, access_count FROM cache_entries WHERE key = ?",
                (key,)
            )
            row = await cursor.fetchone()
            
            if row is None:
                self._misses += 1
                return None
            
            value_blob, created_at, ttl, access_count = row
            
            # Check expiration
            if ttl is not None and (time.time() - created_at) > ttl:
                await self.delete(key)
                self._misses += 1
                return None
            
            # Update access metadata
            await self.db.execute(
                "UPDATE cache_entries SET accessed_at = ?, access_count = ? WHERE key = ?",
                (time.time(), access_count + 1, key)
            )
            await self.db.commit()
            
            # Deserialize value
            value = self._deserialize(value_blob)
            self._hits += 1
            
            return value
        
        except Exception as e:
            self.logger.error(f"L3Cache get error for key {key}: {e}")
            self._errors += 1
            return None
    
    async def set(self, 
                  key: str, 
                  value: Any, 
                  ttl: Optional[int] = None,
                  tags: Optional[List[str]] = None) -> bool:
        """Set value in database cache"""
        if not self.db:
            return False
        
        try:
            # Serialize value
            value_blob = self._serialize(value)
            value_size = len(value_blob)
            
            current_time = time.time()
            ttl_value = ttl or self.default_ttl
            tags_json = json.dumps(tags) if tags else None
            
            # Check if we need to evict entries
            await self._ensure_space(value_size)
            
            # Insert or replace entry
            await self.db.execute(
                """INSERT OR REPLACE INTO cache_entries 
                   (key, value, created_at, accessed_at, access_count, ttl, tags, size)
                   VALUES (?, ?, ?, ?, 1, ?, ?, ?)""",
                (key, value_blob, current_time, current_time, ttl_value, tags_json, value_size)
            )
            
            # Handle tags
            if tags:
                # Delete existing tag associations
                await self.db.execute("DELETE FROM cache_tags WHERE key = ?", (key,))
                
                # Insert new tag associations
                for tag in tags:
                    await self.db.execute(
                        "INSERT OR IGNORE INTO cache_tags (tag, key) VALUES (?, ?)",
                        (tag, key)
                    )
            
            await self.db.commit()
            self._sets += 1
            
            return True
        
        except Exception as e:
            self.logger.error(f"L3Cache set error for key {key}: {e}")
            self._errors += 1
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from database cache"""
        if not self.db:
            return False
        
        try:
            # Delete entry (tags will be deleted by CASCADE)
            cursor = await self.db.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
            await self.db.commit()
            
            if cursor.rowcount > 0:
                self._deletes += 1
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"L3Cache delete error for key {key}: {e}")
            self._errors += 1
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists and is not expired"""
        if not self.db:
            return False
        
        try:
            cursor = await self.db.execute(
                "SELECT created_at, ttl FROM cache_entries WHERE key = ?",
                (key,)
            )
            row = await cursor.fetchone()
            
            if row is None:
                return False
            
            created_at, ttl = row
            
            # Check expiration
            if ttl is not None and (time.time() - created_at) > ttl:
                await self.delete(key)
                return False
            
            return True
        
        except Exception as e:
            self.logger.error(f"L3Cache exists error for key {key}: {e}")
            return False
    
    async def clear(self):
        """Clear all cache entries"""
        if not self.db:
            return
        
        try:
            await self.db.execute("DELETE FROM cache_entries")
            await self.db.execute("DELETE FROM cache_tags")
            await self.db.commit()
            
            self.logger.info("L3Cache cleared all entries")
        
        except Exception as e:
            self.logger.error(f"L3Cache clear error: {e}")
    
    async def invalidate_by_tags(self, tags: List[str]):
        """Invalidate cache entries by tags"""
        if not self.db or not tags:
            return
        
        try:
            # Build query to find keys with any of the specified tags
            placeholders = ','.join('?' * len(tags))
            cursor = await self.db.execute(
                f"SELECT DISTINCT key FROM cache_tags WHERE tag IN ({placeholders})",
                tags
            )
            
            keys_to_delete = [row[0] for row in await cursor.fetchall()]
            
            # Delete entries
            if keys_to_delete:
                placeholders = ','.join('?' * len(keys_to_delete))
                await self.db.execute(
                    f"DELETE FROM cache_entries WHERE key IN ({placeholders})",
                    keys_to_delete
                )
                await self.db.commit()
            
            self.logger.debug(f"L3Cache invalidated {len(keys_to_delete)} keys for tags: {tags}")
        
        except Exception as e:
            self.logger.error(f"L3Cache tag invalidation error: {e}")
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple keys efficiently"""
        if not self.db or not keys:
            return {}
        
        try:
            # Build query for multiple keys
            placeholders = ','.join('?' * len(keys))
            cursor = await self.db.execute(
                f"""SELECT key, value, created_at, ttl, access_count 
                    FROM cache_entries 
                    WHERE key IN ({placeholders})""",
                keys
            )
            
            results = {}
            updates = []
            current_time = time.time()
            
            async for row in cursor:
                key, value_blob, created_at, ttl, access_count = row
                
                # Check expiration
                if ttl is not None and (current_time - created_at) > ttl:
                    await self.delete(key)
                    self._misses += 1
                    continue
                
                # Deserialize value
                try:
                    value = self._deserialize(value_blob)
                    results[key] = value
                    updates.append((current_time, access_count + 1, key))
                    self._hits += 1
                except Exception as e:
                    self.logger.error(f"Deserialization error for key {key}: {e}")
                    self._misses += 1
            
            # Batch update access metadata
            if updates:
                await self.db.executemany(
                    "UPDATE cache_entries SET accessed_at = ?, access_count = ? WHERE key = ?",
                    updates
                )
                await self.db.commit()
            
            return results
        
        except Exception as e:
            self.logger.error(f"L3Cache get_many error: {e}")
            self._errors += 1
            return {}
    
    async def set_many(self, items: Dict[str, Any], ttl: Optional[int] = None):
        """Set multiple keys efficiently"""
        if not self.db or not items:
            return
        
        try:
            current_time = time.time()
            ttl_value = ttl or self.default_ttl
            
            # Prepare batch insert data
            insert_data = []
            total_size = 0
            
            for key, value in items.items():
                value_blob = self._serialize(value)
                value_size = len(value_blob)
                total_size += value_size
                
                insert_data.append((
                    key, value_blob, current_time, current_time, 1, ttl_value, None, value_size
                ))
            
            # Ensure we have space
            await self._ensure_space(total_size)
            
            # Batch insert
            await self.db.executemany(
                """INSERT OR REPLACE INTO cache_entries 
                   (key, value, created_at, accessed_at, access_count, ttl, tags, size)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                insert_data
            )
            
            await self.db.commit()
            self._sets += len(items)
            
            self.logger.debug(f"L3Cache set_many: {len(items)} items")
        
        except Exception as e:
            self.logger.error(f"L3Cache set_many error: {e}")
            self._errors += 1
    
    async def _ensure_space(self, required_size: int):
        """Ensure there's enough space by evicting old entries if needed"""
        try:
            # Get current cache size
            cursor = await self.db.execute("SELECT COUNT(*), SUM(size) FROM cache_entries")
            row = await cursor.fetchone()
            current_count, current_size = row[0] or 0, row[1] or 0
            
            # Check if we need to evict
            if current_count >= self.max_size:
                # Evict 10% of entries (oldest accessed)
                evict_count = max(1, self.max_size // 10)
                
                cursor = await self.db.execute(
                    "SELECT key FROM cache_entries ORDER BY accessed_at ASC LIMIT ?",
                    (evict_count,)
                )
                
                keys_to_evict = [row[0] for row in await cursor.fetchall()]
                
                if keys_to_evict:
                    placeholders = ','.join('?' * len(keys_to_evict))
                    await self.db.execute(
                        f"DELETE FROM cache_entries WHERE key IN ({placeholders})",
                        keys_to_evict
                    )
                    
                    self._evictions += len(keys_to_evict)
                    self.logger.debug(f"L3Cache evicted {len(keys_to_evict)} entries")
        
        except Exception as e:
            self.logger.error(f"L3Cache space management error: {e}")
    
    async def _cleanup_worker(self):
        """Background worker to clean up expired entries"""
        while self._running:
            try:
                await self._cleanup_expired()
                await asyncio.sleep(self.cleanup_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"L3Cache cleanup worker error: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _cleanup_expired(self):
        """Remove expired entries"""
        if not self.db:
            return
        
        try:
            current_time = time.time()
            
            # Find expired entries
            cursor = await self.db.execute(
                "SELECT COUNT(*) FROM cache_entries WHERE ttl IS NOT NULL AND (created_at + ttl) < ?",
                (current_time,)
            )
            expired_count = (await cursor.fetchone())[0]
            
            if expired_count > 0:
                # Delete expired entries
                await self.db.execute(
                    "DELETE FROM cache_entries WHERE ttl IS NOT NULL AND (created_at + ttl) < ?",
                    (current_time,)
                )
                await self.db.commit()
                
                self.logger.debug(f"L3Cache cleaned up {expired_count} expired entries")
        
        except Exception as e:
            self.logger.error(f"L3Cache cleanup error: {e}")
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize value for database storage"""
        try:
            # Use pickle for reliable serialization
            return pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception as e:
            self.logger.error(f"L3Cache serialization error: {e}")
            # Fallback to string representation
            return str(value).encode('utf-8')
    
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value from database storage"""
        try:
            return pickle.loads(data)
        except Exception as e:
            # Fallback: assume it's a UTF-8 string
            try:
                return data.decode('utf-8')
            except:
                self.logger.error(f"L3Cache deserialization error: {e}")
                return None
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = {
            'hits': self._hits,
            'misses': self._misses,
            'sets': self._sets,
            'deletes': self._deletes,
            'evictions': self._evictions,
            'errors': self._errors,
            'hit_rate_pct': (self._hits / (self._hits + self._misses) * 100) if (self._hits + self._misses) > 0 else 0
        }
        
        # Get database statistics
        if self.db:
            try:
                cursor = await self.db.execute(
                    "SELECT COUNT(*), SUM(size), AVG(access_count) FROM cache_entries"
                )
                row = await cursor.fetchone()
                
                if row:
                    count, total_size, avg_access = row
                    stats.update({
                        'entry_count': count or 0,
                        'total_size_bytes': total_size or 0,
                        'avg_access_count': avg_access or 0,
                        'utilization_pct': ((count or 0) / self.max_size) * 100
                    })
                
                # Get tag statistics
                cursor = await self.db.execute("SELECT COUNT(DISTINCT tag) FROM cache_tags")
                tag_count = (await cursor.fetchone())[0]
                stats['unique_tags'] = tag_count or 0
            
            except Exception as e:
                self.logger.error(f"Error getting L3Cache stats: {e}")
        
        return stats
    
    async def get_size(self) -> int:
        """Get current number of entries"""
        if not self.db:
            return 0
        
        try:
            cursor = await self.db.execute("SELECT COUNT(*) FROM cache_entries")
            return (await cursor.fetchone())[0]
        except Exception as e:
            self.logger.error(f"Error getting L3Cache size: {e}")
            return 0


class DatabaseCache(L3Cache):
    """Alias for L3Cache for backward compatibility"""
    pass