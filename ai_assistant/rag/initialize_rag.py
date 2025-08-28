"""
RAG Pipeline Initialization Script
Processes sample documents and initializes the vector database for the RAG pipeline.
"""

import os
import sys
import logging
import asyncio
from pathlib import Path
from typing import List, Optional

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rag_config import RAGPipelineConfig, get_config, validate_config
from rag_pipeline import RAGPipeline
from document_processor import DocumentProcessor
from embedding_service import EmbeddingService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_sample_documents() -> List[str]:
    """
    Get list of sample document files
    
    Returns:
        List of file paths to process
    """
    sample_docs_dir = Path(__file__).parent / "sample_documents"
    
    if not sample_docs_dir.exists():
        logger.error(f"Sample documents directory not found: {sample_docs_dir}")
        return []
    
    # Get all supported document files
    supported_extensions = ['.md', '.txt', '.pdf', '.docx', '.csv']
    sample_files = []
    
    for ext in supported_extensions:
        files = list(sample_docs_dir.glob(f"*{ext}"))
        sample_files.extend([str(f) for f in files])
    
    logger.info(f"Found {len(sample_files)} sample documents")
    for file_path in sample_files:
        logger.info(f"  - {Path(file_path).name}")
    
    return sample_files


def check_dependencies() -> bool:
    """
    Check if all required dependencies are available
    
    Returns:
        True if all dependencies are available
    """
    try:
        # Test imports
        import sentence_transformers
        import qdrant_client
        import unstructured
        
        logger.info("All required dependencies are available")
        return True
        
    except ImportError as e:
        logger.error(f"Missing required dependency: {e}")
        logger.error("Please install all dependencies from requirements.txt")
        return False


def test_vector_store_connection(config: RAGPipelineConfig) -> bool:
    """
    Test connection to vector store
    
    Args:
        config: RAG pipeline configuration
        
    Returns:
        True if connection successful
    """
    try:
        if config.vector_store.value == "qdrant":
            from qdrant_client import QdrantClient
            
            client = QdrantClient(
                url=config.qdrant.url,
                api_key=config.qdrant.api_key
            )
            
            # Test connection
            collections = client.get_collections()
            logger.info(f"Successfully connected to Qdrant at {config.qdrant.url}")
            return True
            
        else:  # PostgreSQL
            import psycopg2
            
            conn_string = (
                f"host={config.postgresql.host} "
                f"port={config.postgresql.port} "
                f"dbname={config.postgresql.database} "
                f"user={config.postgresql.username} "
                f"password={config.postgresql.password}"
            )
            
            conn = psycopg2.connect(conn_string)
            conn.close()
            logger.info(f"Successfully connected to PostgreSQL at {config.postgresql.host}")
            return True
            
    except Exception as e:
        logger.error(f"Failed to connect to vector store: {e}")
        return False


def initialize_rag_pipeline(config: RAGPipelineConfig) -> Optional[RAGPipeline]:
    """
    Initialize the RAG pipeline
    
    Args:
        config: RAG pipeline configuration
        
    Returns:
        Initialized RAG pipeline or None if failed
    """
    try:
        logger.info("Initializing RAG pipeline...")
        
        # Create RAG pipeline
        rag_pipeline = RAGPipeline(config)
        
        # Initialize storage
        if not rag_pipeline.initialize_storage():
            logger.error("Failed to initialize vector storage")
            return None
        
        # Test pipeline health
        health = rag_pipeline.health_check()
        if health["status"] != "healthy":
            logger.warning(f"RAG pipeline health check failed: {health}")
        
        logger.info("RAG pipeline initialized successfully")
        return rag_pipeline
        
    except Exception as e:
        logger.error(f"Failed to initialize RAG pipeline: {e}")
        return None


def process_and_index_documents(rag_pipeline: RAGPipeline, file_paths: List[str]) -> bool:
    """
    Process and index documents in the RAG pipeline
    
    Args:
        rag_pipeline: Initialized RAG pipeline
        file_paths: List of file paths to process
        
    Returns:
        True if successful
    """
    try:
        logger.info(f"Processing and indexing {len(file_paths)} documents...")
        
        # Process documents
        success = rag_pipeline.process_and_store_documents(file_paths)
        
        if success:
            logger.info("Successfully processed and indexed all documents")
            
            # Get pipeline info
            info = rag_pipeline.get_pipeline_info()
            logger.info(f"Pipeline info: {info}")
            
        else:
            logger.error("Failed to process and index documents")
        
        return success
        
    except Exception as e:
        logger.error(f"Error processing documents: {e}")
        return False


def test_search_functionality(rag_pipeline: RAGPipeline) -> bool:
    """
    Test the search functionality with sample queries
    
    Args:
        rag_pipeline: Initialized RAG pipeline
        
    Returns:
        True if search tests pass
    """
    test_queries = [
        "What is a moving average crossover strategy?",
        "How to calculate Sharpe ratio?",
        "Risk management techniques",
        "Portfolio optimization methods",
        "Backtesting best practices"
    ]
    
    logger.info("Testing search functionality...")
    
    try:
        for query in test_queries:
            logger.info(f"Testing query: '{query}'")
            
            response = rag_pipeline.search(query, top_k=3)
            
            logger.info(f"  Found {len(response.results)} results in {response.processing_time:.2f}s")
            
            if response.results:
                top_result = response.results[0]
                logger.info(f"  Top result: {top_result.chunk.metadata.title} (score: {top_result.score:.3f})")
            else:
                logger.warning(f"  No results found for query: {query}")
        
        logger.info("Search functionality test completed")
        return True
        
    except Exception as e:
        logger.error(f"Search functionality test failed: {e}")
        return False


def main():
    """Main initialization function"""
    logger.info("Starting RAG Pipeline Initialization")
    
    # Check dependencies
    if not check_dependencies():
        logger.error("Dependency check failed. Exiting.")
        sys.exit(1)
    
    # Load configuration
    try:
        config = get_config()
        logger.info("Configuration loaded successfully")
        
        # Validate configuration
        errors = validate_config(config)
        if errors:
            logger.error("Configuration validation failed:")
            for error in errors:
                logger.error(f"  - {error}")
            sys.exit(1)
        
        logger.info("Configuration validation passed")
        
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)
    
    # Test vector store connection
    if not test_vector_store_connection(config):
        logger.error("Vector store connection test failed. Exiting.")
        sys.exit(1)
    
    # Get sample documents
    sample_files = setup_sample_documents()
    if not sample_files:
        logger.error("No sample documents found. Exiting.")
        sys.exit(1)
    
    # Initialize RAG pipeline
    rag_pipeline = initialize_rag_pipeline(config)
    if not rag_pipeline:
        logger.error("RAG pipeline initialization failed. Exiting.")
        sys.exit(1)
    
    # Process and index documents
    if not process_and_index_documents(rag_pipeline, sample_files):
        logger.error("Document processing failed. Exiting.")
        sys.exit(1)
    
    # Test search functionality
    if not test_search_functionality(rag_pipeline):
        logger.warning("Search functionality test failed, but continuing...")
    
    logger.info("RAG Pipeline initialization completed successfully!")
    logger.info("The system is ready to process document queries.")
    
    # Print usage instructions
    print("\n" + "="*60)
    print("RAG PIPELINE INITIALIZATION COMPLETE")
    print("="*60)
    print("\nThe RAG pipeline has been successfully initialized with sample documents.")
    print("\nYou can now:")
    print("1. Use the query_documents_tool in the AI assistant")
    print("2. Search for trading-related information")
    print("3. Add more documents to the system")
    print("\nSample queries to try:")
    print("- 'What are the best risk management techniques?'")
    print("- 'How to implement a moving average strategy?'")
    print("- 'What performance metrics should I track?'")
    print("\n" + "="*60)


if __name__ == "__main__":
    main()