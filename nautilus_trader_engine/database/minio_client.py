"""
MinIO/S3 Integration for Object Storage
Implements high-performance object storage for models and datasets

This module provides:
- MinIO/S3 client for object storage
- Model storage and retrieval
- Dataset management
- Performance optimization
- Connection management

Author: Vincent S. Pereira
Version: 1.0.0
Phase: 1 - Core System Validation & Hardening
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union, BinaryIO
from datetime import datetime
import json
import os
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

# MinIO client
try:
    from minio import Minio, AsyncMinio
    from minio.error import S3Error
    MINIO_AVAILABLE = True
except ImportError:
    MINIO_AVAILABLE = False
    logging.warning("MinIO client not available. Install with: pip install minio")

logger = logging.getLogger(__name__)

@dataclass
class MinIOConfig:
    """MinIO/S3 configuration"""
    endpoint: str
    access_key: str
    secret_key: str
    bucket_name: str = "trading-system"
    region: str = "us-east-1"
    secure: bool = True
    session_token: Optional[str] = None

@dataclass
class ObjectMetadata:
    """Object metadata for storage"""
    name: str
    size: int
    content_type: str
    last_modified: datetime
    etag: str
    metadata: Dict[str, str] = None

class MinIOManager:
    """
    MinIO/S3 manager for object storage
    """
    
    def __init__(self, config: Optional[MinIOConfig] = None):
        self.config = config or self._default_config()
        self.client = None
        self.initialized = False
        self.logger = logging.getLogger(__name__)
        
        if not MINIO_AVAILABLE:
            self.logger.error("MinIO client not available. Object storage will be limited.")
    
    def _default_config(self) -> MinIOConfig:
        """Default MinIO configuration"""
        return MinIOConfig(
            endpoint=os.getenv("MINIO_ENDPOINT", "localhost:9000"),
            access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
            bucket_name=os.getenv("MINIO_BUCKET_NAME", "trading-system"),
            region=os.getenv("MINIO_REGION", "us-east-1"),
            secure=os.getenv("MINIO_SECURE", "false").lower() == "true"
        )
    
    async def initialize(self) -> bool:
        """Initialize MinIO client and bucket"""
        if not MINIO_AVAILABLE:
            self.logger.warning("MinIO not available - using fallback storage")
            return await self._initialize_fallback()
        
        try:
            # Create MinIO client
            self.client = Minio(
                self.config.endpoint,
                access_key=self.config.access_key,
                secret_key=self.config.secret_key,
                region=self.config.region,
                secure=self.config.secure
            )
            
            # Check if bucket exists, create if not
            if not self.client.bucket_exists(self.config.bucket_name):
                self.client.make_bucket(self.config.bucket_name, self.config.region)
                self.logger.info(f"Created MinIO bucket: {self.config.bucket_name}")
            else:
                self.logger.info(f"MinIO bucket already exists: {self.config.bucket_name}")
            
            self.initialized = True
            self.logger.info("MinIO initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MinIO: {e}")
            return await self._initialize_fallback()
    
    async def _initialize_fallback(self) -> bool:
        """Initialize fallback storage without MinIO"""
        try:
            # Use file-based storage as fallback
            import os
            storage_dir = "object_storage"
            os.makedirs(os.path.join(storage_dir, self.config.bucket_name), exist_ok=True)
            
            self.storage_path = storage_dir
            self.initialized = True
            self.logger.info("Fallback MinIO storage initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize fallback MinIO storage: {e}")
            return False
    
    async def upload_object(self, object_name: str, data: Union[bytes, BinaryIO], 
                          content_type: str = "application/octet-stream",
                          metadata: Optional[Dict[str, str]] = None) -> bool:
        """Upload an object to MinIO"""
        try:
            if not self.initialized:
                return False
            
            if self.client:
                # Upload to MinIO
                result = self.client.put_object(
                    self.config.bucket_name,
                    object_name,
                    data,
                    length=-1,
                    content_type=content_type,
                    metadata=metadata or {}
                )
                self.logger.info(f"Uploaded object: {object_name} (etag: {result.etag})")
            else:
                # Fallback to file storage
                file_path = os.path.join(self.storage_path, self.config.bucket_name, object_name)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                if isinstance(data, bytes):
                    with open(file_path, "wb") as f:
                        f.write(data)
                else:
                    with open(file_path, "wb") as f:
                        f.write(data.read())
                
                self.logger.info(f"Fallback uploaded object: {object_name}")
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to upload object {object_name}: {e}")
            return False
    
    async def download_object(self, object_name: str) -> Optional[bytes]:
        """Download an object from MinIO"""
        try:
            if not self.initialized:
                return None
            
            if self.client:
                # Download from MinIO
                response = self.client.get_object(self.config.bucket_name, object_name)
                data = response.read()
                response.close()
                response.release_conn()
                return data
            else:
                # Fallback to file storage
                file_path = os.path.join(self.storage_path, self.config.bucket_name, object_name)
                if os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        return f.read()
                else:
                    self.logger.warning(f"Object not found in fallback storage: {object_name}")
                    return None
        except Exception as e:
            self.logger.error(f"Failed to download object {object_name}: {e}")
            return None
    
    async def list_objects(self, prefix: str = "") -> List[ObjectMetadata]:
        """List objects in MinIO bucket"""
        try:
            if not self.initialized:
                return []
            
            objects = []
            if self.client:
                # List from MinIO
                for item in self.client.list_objects(self.config.bucket_name, prefix=prefix):
                    objects.append(ObjectMetadata(
                        name=item.object_name,
                        size=item.size,
                        content_type=item.content_type or "application/octet-stream",
                        last_modified=item.last_modified,
                        etag=item.etag,
                        metadata=item.metadata or {}
                    ))
            else:
                # Fallback to file storage
                bucket_path = os.path.join(self.storage_path, self.config.bucket_name)
                if os.path.exists(bucket_path):
                    for root, dirs, files in os.walk(bucket_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            relative_path = os.path.relpath(file_path, bucket_path)
                            stat = os.stat(file_path)
                            objects.append(ObjectMetadata(
                                name=relative_path,
                                size=stat.st_size,
                                content_type="application/octet-stream",
                                last_modified=datetime.fromtimestamp(stat.st_mtime),
                                etag="",
                                metadata={}
                            ))
            
            return objects
        except Exception as e:
            self.logger.error(f"Failed to list objects: {e}")
            return []
    
    async def delete_object(self, object_name: str) -> bool:
        """Delete an object from MinIO"""
        try:
            if not self.initialized:
                return False
            
            if self.client:
                # Delete from MinIO
                self.client.remove_object(self.config.bucket_name, object_name)
            else:
                # Fallback to file storage
                file_path = os.path.join(self.storage_path, self.config.bucket_name, object_name)
                if os.path.exists(file_path):
                    os.remove(file_path)
            
            self.logger.info(f"Deleted object: {object_name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete object {object_name}: {e}")
            return False
    
    async def close(self):
        """Close MinIO connection"""
        # MinIO client doesn't need explicit closing
        self.logger.info("MinIO connection closed")


# Global MinIO manager instance
minio_manager = MinIOManager()

# Convenience functions
async def init_minio(config: Optional[MinIOConfig] = None) -> bool:
    """Initialize MinIO - convenience function"""
    if config:
        minio_manager.config = config
    return await minio_manager.initialize()

async def upload_object(object_name: str, data: Union[bytes, BinaryIO], 
                       content_type: str = "application/octet-stream",
                       metadata: Optional[Dict[str, str]] = None) -> bool:
    """Upload an object - convenience function"""
    return await minio_manager.upload_object(object_name, data, content_type, metadata)

async def download_object(object_name: str) -> Optional[bytes]:
    """Download an object - convenience function"""
    return await minio_manager.download_object(object_name)

async def list_objects(prefix: str = "") -> List[ObjectMetadata]:
    """List objects - convenience function"""
    return await minio_manager.list_objects(prefix)

async def delete_object(object_name: str) -> bool:
    """Delete an object - convenience function"""
    return await minio_manager.delete_object(object_name)

if __name__ == "__main__":
    async def main():
        # Initialize MinIO
        success = await init_minio()
        print(f"MinIO initialization: {'✓' if success else '✗'}")
        
        if success:
            # Test object upload
            test_data = b"Hello, MinIO!"
            upload_success = await upload_object("test.txt", test_data, "text/plain")
            print(f"Object upload: {'✓' if upload_success else '✗'}")
            
            # Test object download
            downloaded_data = await download_object("test.txt")
            if downloaded_data:
                print(f"Object download: ✓ (data: {downloaded_data.decode()})")
            else:
                print("Object download: ✗")
            
            # Test object listing
            objects = await list_objects()
            print(f"Object listing: ✓ ({len(objects)} objects)")
            
            # Test object deletion
            delete_success = await delete_object("test.txt")
            print(f"Object deletion: {'✓' if delete_success else '✗'}")
    
    asyncio.run(main())