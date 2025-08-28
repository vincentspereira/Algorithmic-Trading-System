
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Distance, VectorParams, PointStruct

from ai_assistant.rag_config import RAGPipelineConfig
from ai_assistant.document_processor import DocumentChunk, DocumentMetadata
from ai_assistant.schemas import SearchResult

logger = logging.getLogger(__name__)

class QdrantVectorStore:
    """Qdrant vector database implementation"""

    def __init__(self, config: RAGPipelineConfig):
        """
        Initialize Qdrant vector store

        Args:
            config: RAG pipeline configuration
        """
        self.config = config
        self.qdrant_config = config.qdrant

        # Initialize Qdrant client
        self.client = QdrantClient(
            url=self.qdrant_config.url,
            api_key=self.qdrant_config.api_key
        )

        self.collection_name = self.qdrant_config.collection_name
        self.vector_size = self.qdrant_config.vector_size

        logger.info(f"QdrantVectorStore initialized: {self.qdrant_config.url}")

    def create_collection(self) -> bool:
        """
        Create Qdrant collection if it doesn't exist

        Returns:
            True if collection was created or already exists
        """
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]

            if self.collection_name in collection_names:
                logger.info(f"Collection '{self.collection_name}' already exists")
                return True

            # Create collection
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                ),
                hnsw_config=models.HnswConfigDiff(**self.qdrant_config.hnsw_config)
            )

            logger.info(f"Created Qdrant collection: {self.collection_name}")
            return True

        except Exception as e:
            logger.error(f"Error creating Qdrant collection: {e}")
            return False

    def add_chunks(self, chunks: List[DocumentChunk]) -> bool:
        """
        Add document chunks to Qdrant collection

        Args:
            chunks: List of document chunks with embeddings

        Returns:
            True if successful
        """
        try:
            if not chunks:
                return True

            # Prepare points for insertion
            points = []
            for chunk in chunks:
                if chunk.embedding is None:
                    logger.warning(f"Chunk {chunk.chunk_id} has no embedding, skipping")
                    continue

                # Prepare payload with metadata
                payload = {
                    "content": chunk.content,
                    "title": chunk.metadata.title,
                    "source": chunk.metadata.source,
                    "category": chunk.metadata.category,
                    "tags": chunk.metadata.tags,
                    "file_type": chunk.metadata.file_type,
                    "chunk_index": chunk.chunk_index,
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                    "created_date": chunk.metadata.created_date.isoformat() if chunk.metadata.created_date else None,
                    "word_count": chunk.metadata.word_count,
                    "checksum": chunk.metadata.checksum
                }

                point = PointStruct(
                    id=hash(chunk.chunk_id) % (2**63),  # Convert string ID to int
                    vector=chunk.embedding,
                    payload=payload
                )
                points.append(point)

            # Insert points in batches
            batch_size = 100
            for i in range(0, len(points), batch_size):
                batch_points = points[i:i + batch_size]
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch_points
                )

            logger.info(f"Added {len(points)} chunks to Qdrant collection")
            return True

        except Exception as e:
            logger.error(f"Error adding chunks to Qdrant: {e}")
            return False

    def search(self, query_embedding: List[float], top_k: int = 10,
               filters: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """
        Search for similar chunks using vector similarity

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            filters: Optional filters for metadata

        Returns:
            List of search results
        """
        try:
            # Prepare filter conditions
            query_filter = None
            if filters:
                conditions = []
                for key, value in filters.items():
                    if isinstance(value, list):
                        conditions.append(models.FieldCondition(
                            key=key,
                            match=models.MatchAny(any=value)
                        ))
                    else:
                        conditions.append(models.FieldCondition(
                            key=key,
                            match=models.MatchValue(value=value)
                        ))

                if conditions:
                    query_filter = models.Filter(must=conditions)

            # Perform search
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True
            )

            # Convert to SearchResult objects
            results = []
            for i, result in enumerate(search_results):
                payload = result.payload

                # Reconstruct DocumentMetadata
                metadata = DocumentMetadata(
                    title=payload.get("title", ""),
                    source=payload.get("source", ""),
                    file_type=payload.get("file_type", ""),
                    file_size=0,  # Not stored in payload
                    created_date=datetime.fromisoformat(payload["created_date"]) if payload.get("created_date") else None,
                    category=payload.get("category", "general"),
                    tags=payload.get("tags", []),
                    word_count=payload.get("word_count", 0),
                    checksum=payload.get("checksum", "")
                )

                # Reconstruct DocumentChunk
                chunk = DocumentChunk(
                    content=payload.get("content", ""),
                    metadata=metadata,
                    chunk_id=str(result.id),
                    chunk_index=payload.get("chunk_index", 0),
                    start_char=payload.get("start_char", 0),
                    end_char=payload.get("end_char", 0)
                )

                search_result = SearchResult(
                    chunk=chunk,
                    score=result.score,
                    rank=i + 1
                )
                results.append(search_result)

            return results

        except Exception as e:
            logger.error(f"Error searching Qdrant: {e}")
            return []

    def delete_collection(self) -> bool:
        """Delete the collection"""
        try:
            self.client.delete_collection(self.collection_name)
            logger.info(f"Deleted Qdrant collection: {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting Qdrant collection: {e}")
            return False

    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection"""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "points_count": info.points_count,
                "status": info.status
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return {}
