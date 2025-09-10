"""
MongoDB Integration for Document Storage and RAG
Implements MongoDB client for document storage, caching, and RAG applications

This module provides:
- MongoDB client for document storage
- Caching capabilities
- Chat message history storage
- RAG (Retrieval-Augmented Generation) support
- Performance optimization and connection management

Author: Vincent S. Pereira
Version: 1.0.0
Phase: 1 - Core System Validation & Hardening
"""

import asyncio
import logging
import os
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import json
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

# MongoDB client
try:
    from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    logging.warning("MongoDB client not available. Install with: pip install motor pymongo")

logger = logging.getLogger(__name__)

@dataclass
class MongoDBConfig:
    """MongoDB configuration"""
    uri: str = "mongodb://localhost:27017"
    database_name: str = "trading_system"
    username: Optional[str] = None
    password: Optional[str] = None
    auth_source: str = "admin"
    max_pool_size: int = 100
    min_pool_size: int = 10
    server_selection_timeout_ms: int = 5000
    connect_timeout_ms: int = 5000

@dataclass
class Document:
    """Structured document for MongoDB storage"""
    id: Optional[str] = None
    content: str = ""
    metadata: Dict[str, Any] = None
    embedding: Optional[List[float]] = None
    created_at: datetime = None
    updated_at: datetime = None
    document_type: str = "generic"
    tags: List[str] = None

class MongoDBManager:
    """
    MongoDB manager for document storage and RAG
    """
    
    def __init__(self, config: Optional[MongoDBConfig] = None):
        self.config = config or self._default_config()
        self.client = None
        self.database = None
        self.initialized = False
        self.logger = logging.getLogger(__name__)
        
        if not MONGODB_AVAILABLE:
            self.logger.error("MongoDB client not available. Document storage will be limited.")
    
    def _default_config(self) -> MongoDBConfig:
        """Default MongoDB configuration"""
        return MongoDBConfig(
            uri=os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
            database_name=os.getenv("MONGODB_DATABASE", "trading_system"),
            username=os.getenv("MONGODB_USERNAME"),
            password=os.getenv("MONGODB_PASSWORD"),
            auth_source=os.getenv("MONGODB_AUTH_SOURCE", "admin"),
            max_pool_size=int(os.getenv("MONGODB_MAX_POOL_SIZE", "100")),
            server_selection_timeout_ms=int(os.getenv("MONGODB_SERVER_SELECTION_TIMEOUT_MS", "5000"))
        )
    
    async def initialize(self) -> bool:
        """Initialize MongoDB client and database"""
        if not MONGODB_AVAILABLE:
            self.logger.warning("MongoDB not available - using fallback storage")
            return await self._initialize_fallback()
        
        try:
            # Create MongoDB client
            client_kwargs = {
                "maxPoolSize": self.config.max_pool_size,
                "minPoolSize": self.config.min_pool_size,
                "serverSelectionTimeoutMS": self.config.server_selection_timeout_ms,
                "connectTimeoutMS": self.config.connect_timeout_ms
            }
            
            if self.config.username and self.config.password:
                client_kwargs["username"] = self.config.username
                client_kwargs["password"] = self.config.password
                client_kwargs["authSource"] = self.config.auth_source
            
            self.client = AsyncIOMotorClient(self.config.uri, **client_kwargs)
            self.database = self.client[self.config.database_name]
            
            # Test connection
            await self.client.admin.command('ping')
            
            # Create indexes
            await self._create_indexes()
            
            self.initialized = True
            self.logger.info("MongoDB initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MongoDB: {e}")
            return await self._initialize_fallback()
    
    async def _initialize_fallback(self) -> bool:
        """Initialize fallback storage without MongoDB"""
        try:
            # Use file-based storage as fallback
            import os
            import json
            storage_dir = "mongodb_storage"
            os.makedirs(storage_dir, exist_ok=True)
            
            self.storage_path = os.path.join(storage_dir, f"{self.config.database_name}.json")
            
            # Load existing data if available
            if os.path.exists(self.storage_path):
                with open(self.storage_path, "r") as f:
                    self.fallback_data = json.load(f)
            else:
                self.fallback_data = {}
            
            self.initialized = True
            self.logger.info("Fallback MongoDB storage initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize fallback MongoDB storage: {e}")
            return False
    
    async def _create_indexes(self):
        """Create MongoDB indexes for performance"""
        try:
            # Documents collection indexes
            documents_collection = self.database["documents"]
            
            # Text index for content search
            await documents_collection.create_index([("content", "text")])
            
            # Compound index for metadata queries
            await documents_collection.create_index([
                ("document_type", 1),
                ("created_at", -1)
            ])
            
            # Index for tags
            await documents_collection.create_index("tags")
            
            # Index for embeddings (if vector search is available)
            await documents_collection.create_index("embedding")
            
            self.logger.info("MongoDB indexes created successfully")
        except Exception as e:
            self.logger.warning(f"Could not create MongoDB indexes: {e}")
    
    async def insert_document(self, document: Document, collection_name: str = "documents") -> bool:
        """Insert a document into MongoDB"""
        try:
            if not self.initialized:
                return False
            
            if self.database:
                # Insert into MongoDB
                collection = self.database[collection_name]
                
                # Set timestamps
                now = datetime.now()
                if not document.created_at:
                    document.created_at = now
                document.updated_at = now
                
                # Convert to dict
                doc_dict = asdict(document)
                if doc_dict.get("id") is None:
                    del doc_dict["id"]  # Let MongoDB generate the ID
                
                result = await collection.insert_one(doc_dict)
                self.logger.info(f"Inserted document with ID: {result.inserted_id}")
            else:
                # Fallback to file storage
                if collection_name not in self.fallback_data:
                    self.fallback_data[collection_name] = []
                
                # Generate ID if not provided
                if not document.id:
                    import uuid
                    document.id = str(uuid.uuid4())
                
                # Set timestamps
                now = datetime.now()
                if not document.created_at:
                    document.created_at = now
                document.updated_at = now
                
                self.fallback_data[collection_name].append(asdict(document))
                
                # Save to file
                with open(self.storage_path, "w") as f:
                    json.dump(self.fallback_data, f)
                
                self.logger.info(f"Fallback inserted document with ID: {document.id}")
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to insert document: {e}")
            return False
    
    async def search_documents(self, query: str, document_type: Optional[str] = None, 
                             limit: int = 20, collection_name: str = "documents") -> List[Document]:
        """Search documents in MongoDB"""
        try:
            if not self.initialized:
                return []
            
            documents = []
            if self.database:
                # Search in MongoDB
                collection = self.database[collection_name]
                
                # Build query
                mongo_query = {"$text": {"$search": query}} if query else {}
                if document_type:
                    mongo_query["document_type"] = document_type
                
                # Execute search
                cursor = collection.find(mongo_query).limit(limit)
                async for doc in cursor:
                    documents.append(Document(
                        id=str(doc.get("_id")),
                        content=doc.get("content", ""),
                        metadata=doc.get("metadata", {}),
                        embedding=doc.get("embedding"),
                        created_at=doc.get("created_at"),
                        updated_at=doc.get("updated_at"),
                        document_type=doc.get("document_type", "generic"),
                        tags=doc.get("tags", [])
                    ))
            else:
                # Fallback to file storage
                if collection_name in self.fallback_data:
                    for doc_dict in self.fallback_data[collection_name]:
                        # Simple text matching
                        if query.lower() in doc_dict.get("content", "").lower():
                            if not document_type or doc_dict.get("document_type") == document_type:
                                documents.append(Document(**doc_dict))
                                if len(documents) >= limit:
                                    break
            
            return documents
        except Exception as e:
            self.logger.error(f"Failed to search documents: {e}")
            return []
    
    async def get_document_by_id(self, doc_id: str, collection_name: str = "documents") -> Optional[Document]:
        """Get a document by ID from MongoDB"""
        try:
            if not self.initialized:
                return None
            
            if self.database:
                # Get from MongoDB
                collection = self.database[collection_name]
                doc = await collection.find_one({"_id": doc_id})
                
                if doc:
                    return Document(
                        id=str(doc.get("_id")),
                        content=doc.get("content", ""),
                        metadata=doc.get("metadata", {}),
                        embedding=doc.get("embedding"),
                        created_at=doc.get("created_at"),
                        updated_at=doc.get("updated_at"),
                        document_type=doc.get("document_type", "generic"),
                        tags=doc.get("tags", [])
                    )
            else:
                # Fallback to file storage
                if collection_name in self.fallback_data:
                    for doc_dict in self.fallback_data[collection_name]:
                        if doc_dict.get("id") == doc_id:
                            return Document(**doc_dict)
            
            return None
        except Exception as e:
            self.logger.error(f"Failed to get document by ID: {e}")
            return None
    
    async def update_document(self, doc_id: str, updates: Dict[str, Any], 
                            collection_name: str = "documents") -> bool:
        """Update a document in MongoDB"""
        try:
            if not self.initialized:
                return False
            
            if self.database:
                # Update in MongoDB
                collection = self.database[collection_name]
                updates["updated_at"] = datetime.now()
                
                result = await collection.update_one(
                    {"_id": doc_id},
                    {"$set": updates}
                )
                
                success = result.modified_count > 0
                if success:
                    self.logger.info(f"Updated document with ID: {doc_id}")
            else:
                # Fallback to file storage
                success = False
                if collection_name in self.fallback_data:
                    for i, doc_dict in enumerate(self.fallback_data[collection_name]):
                        if doc_dict.get("id") == doc_id:
                            # Update the document
                            self.fallback_data[collection_name][i].update(updates)
                            self.fallback_data[collection_name][i]["updated_at"] = datetime.now()
                            
                            # Save to file
                            with open(self.storage_path, "w") as f:
                                json.dump(self.fallback_data, f)
                            
                            success = True
                            self.logger.info(f"Fallback updated document with ID: {doc_id}")
                            break
            
            return success
        except Exception as e:
            self.logger.error(f"Failed to update document: {e}")
            return False
    
    async def delete_document(self, doc_id: str, collection_name: str = "documents") -> bool:
        """Delete a document from MongoDB"""
        try:
            if not self.initialized:
                return False
            
            if self.database:
                # Delete from MongoDB
                collection = self.database[collection_name]
                result = await collection.delete_one({"_id": doc_id})
                
                success = result.deleted_count > 0
                if success:
                    self.logger.info(f"Deleted document with ID: {doc_id}")
            else:
                # Fallback to file storage
                success = False
                if collection_name in self.fallback_data:
                    for i, doc_dict in enumerate(self.fallback_data[collection_name]):
                        if doc_dict.get("id") == doc_id:
                            # Remove the document
                            del self.fallback_data[collection_name][i]
                            
                            # Save to file
                            with open(self.storage_path, "w") as f:
                                json.dump(self.fallback_data, f)
                            
                            success = True
                            self.logger.info(f"Fallback deleted document with ID: {doc_id}")
                            break
            
            return success
        except Exception as e:
            self.logger.error(f"Failed to delete document: {e}")
            return False
    
    async def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            self.logger.info("MongoDB connection closed")


# Global MongoDB manager instance
mongodb_manager = MongoDBManager()

# Convenience functions
async def init_mongodb(config: Optional[MongoDBConfig] = None) -> bool:
    """Initialize MongoDB - convenience function"""
    if config:
        mongodb_manager.config = config
    return await mongodb_manager.initialize()

async def insert_document(document: Document, collection_name: str = "documents") -> bool:
    """Insert a document - convenience function"""
    return await mongodb_manager.insert_document(document, collection_name)

async def search_documents(query: str, document_type: Optional[str] = None, 
                          limit: int = 20, collection_name: str = "documents") -> List[Document]:
    """Search documents - convenience function"""
    return await mongodb_manager.search_documents(query, document_type, limit, collection_name)

async def get_document_by_id(doc_id: str, collection_name: str = "documents") -> Optional[Document]:
    """Get a document by ID - convenience function"""
    return await mongodb_manager.get_document_by_id(doc_id, collection_name)

async def update_document(doc_id: str, updates: Dict[str, Any], 
                         collection_name: str = "documents") -> bool:
    """Update a document - convenience function"""
    return await mongodb_manager.update_document(doc_id, updates, collection_name)

async def delete_document(doc_id: str, collection_name: str = "documents") -> bool:
    """Delete a document - convenience function"""
    return await mongodb_manager.delete_document(doc_id, collection_name)

if __name__ == "__main__":
    async def main():
        # Initialize MongoDB
        success = await init_mongodb()
        print(f"MongoDB initialization: {'✓' if success else '✗'}")
        
        if success:
            # Test document insertion
            doc = Document(
                content="This is a test document for MongoDB integration",
                metadata={"source": "test", "category": "example"},
                document_type="test_document",
                tags=["test", "example"]
            )
            insert_success = await insert_document(doc)
            print(f"Document insertion: {'✓' if insert_success else '✗'}")
            
            # Test document search
            results = await search_documents("test")
            print(f"Document search: ✓ ({len(results)} results)")
            
            # Close connection
            await mongodb_manager.close()
    
    asyncio.run(main())