"""
Document Processor for RAG Pipeline
Handles document processing using Unstructured.io, text chunking, and metadata extraction
for various document types including PDF, Word, TXT, CSV, and more.
"""

import os
import io
import logging
import hashlib
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field

import pandas as pd
from unstructured.partition.auto import partition
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.docx import partition_docx
from unstructured.partition.text import partition_text
from unstructured.partition.csv import partition_csv
from unstructured.chunking.title import chunk_by_title
from unstructured.chunking.basic import chunk_elements

from .rag_config import RAGPipelineConfig, ChunkingStrategy, get_config

logger = logging.getLogger(__name__)


@dataclass
class DocumentMetadata:
    """Metadata for processed documents"""
    title: str
    source: str
    file_type: str
    file_size: int
    created_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    author: Optional[str] = None
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    language: str = "en"
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    checksum: Optional[str] = None


@dataclass
class DocumentChunk:
    """Represents a chunk of processed document"""
    content: str
    metadata: DocumentMetadata
    chunk_id: str
    chunk_index: int
    start_char: int
    end_char: int
    embedding: Optional[List[float]] = None


class DocumentProcessor:
    """
    Document processor using Unstructured.io for parsing various document formats
    and implementing different chunking strategies.
    """
    
    def __init__(self, config: Optional[RAGPipelineConfig] = None):
        """
        Initialize document processor
        
        Args:
            config: RAG pipeline configuration
        """
        self.config = config or get_config()
        self.supported_formats = set(self.config.document_processing.supported_formats)
        
        # Initialize Unstructured.io client if API key is provided
        self.unstructured_api_key = self.config.document_processing.unstructured_api_key
        self.unstructured_url = self.config.document_processing.unstructured_url
        
        logger.info(f"DocumentProcessor initialized with supported formats: {self.supported_formats}")
    
    def is_supported_format(self, file_path: Union[str, Path]) -> bool:
        """
        Check if file format is supported
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if format is supported
        """
        file_path = Path(file_path)
        return file_path.suffix.lower() in self.supported_formats
    
    def extract_metadata(self, file_path: Union[str, Path], content: str = "") -> DocumentMetadata:
        """
        Extract metadata from file
        
        Args:
            file_path: Path to the file
            content: File content for additional metadata extraction
            
        Returns:
            DocumentMetadata object
        """
        file_path = Path(file_path)
        
        # Basic file information
        stat = file_path.stat() if file_path.exists() else None
        file_size = stat.st_size if stat else len(content.encode('utf-8'))
        
        # Determine category based on filename and content
        category = self._determine_category(file_path.name, content)
        
        # Extract tags from filename and content
        tags = self._extract_tags(file_path.name, content)
        
        # Calculate checksum
        checksum = self._calculate_checksum(content)
        
        metadata = DocumentMetadata(
            title=file_path.stem.replace('_', ' ').replace('-', ' ').title(),
            source=str(file_path),
            file_type=file_path.suffix.lower(),
            file_size=file_size,
            created_date=datetime.fromtimestamp(stat.st_ctime) if stat else datetime.now(),
            modified_date=datetime.fromtimestamp(stat.st_mtime) if stat else datetime.now(),
            category=category,
            tags=tags,
            word_count=len(content.split()) if content else 0,
            checksum=checksum
        )
        
        return metadata
    
    def _determine_category(self, filename: str, content: str) -> str:
        """
        Determine document category based on filename and content
        
        Args:
            filename: Name of the file
            content: File content
            
        Returns:
            Category string
        """
        filename_lower = filename.lower()
        content_lower = content.lower()
        
        # Trading-specific categories
        if any(term in filename_lower for term in ['strategy', 'trading', 'backtest']):
            return "trading_strategies"
        elif any(term in filename_lower for term in ['risk', 'management', 'portfolio']):
            return "risk_management"
        elif any(term in filename_lower for term in ['market', 'analysis', 'research']):
            return "market_analysis"
        elif any(term in filename_lower for term in ['technical', 'indicator', 'signal']):
            return "technical_analysis"
        elif any(term in filename_lower for term in ['performance', 'metrics', 'report']):
            return "performance_metrics"
        elif any(term in filename_lower for term in ['guide', 'tutorial', 'documentation']):
            return "documentation"
        
        # Content-based categorization
        if any(term in content_lower for term in ['moving average', 'rsi', 'macd', 'bollinger']):
            return "technical_analysis"
        elif any(term in content_lower for term in ['sharpe ratio', 'drawdown', 'volatility']):
            return "performance_metrics"
        elif any(term in content_lower for term in ['position sizing', 'stop loss', 'risk']):
            return "risk_management"
        
        return "general"
    
    def _extract_tags(self, filename: str, content: str) -> List[str]:
        """
        Extract relevant tags from filename and content
        
        Args:
            filename: Name of the file
            content: File content
            
        Returns:
            List of tags
        """
        tags = set()
        
        # Common trading terms
        trading_terms = [
            'strategy', 'backtest', 'trading', 'portfolio', 'risk', 'management',
            'technical', 'analysis', 'indicator', 'signal', 'market', 'volatility',
            'sharpe', 'drawdown', 'performance', 'metrics', 'moving_average',
            'rsi', 'macd', 'bollinger', 'crossover', 'momentum', 'trend'
        ]
        
        filename_lower = filename.lower()
        content_lower = content.lower()
        
        # Extract tags from filename
        for term in trading_terms:
            if term in filename_lower:
                tags.add(term)
        
        # Extract tags from content (first 1000 characters for efficiency)
        content_sample = content_lower[:1000]
        for term in trading_terms:
            if term in content_sample:
                tags.add(term)
        
        return list(tags)
    
    def _calculate_checksum(self, content: str) -> str:
        """
        Calculate SHA-256 checksum of content
        
        Args:
            content: Content to hash
            
        Returns:
            SHA-256 checksum string
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def process_file(self, file_path: Union[str, Path]) -> List[DocumentChunk]:
        """
        Process a single file and return document chunks
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            List of DocumentChunk objects
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not self.is_supported_format(file_path):
            raise ValueError(f"Unsupported file format: {file_path.suffix}")
        
        logger.info(f"Processing file: {file_path}")
        
        try:
            # Extract text content using Unstructured.io
            content = self._extract_content(file_path)
            
            # Extract metadata
            metadata = self.extract_metadata(file_path, content)
            
            # Apply content filtering
            if len(content) < self.config.document_processing.min_content_length:
                logger.warning(f"Content too short, skipping: {file_path}")
                return []
            
            if len(content) > self.config.document_processing.max_content_length:
                logger.warning(f"Content too long, truncating: {file_path}")
                content = content[:self.config.document_processing.max_content_length]
            
            # Clean content
            content = self._clean_content(content)
            
            # Create chunks
            chunks = self._create_chunks(content, metadata)
            
            logger.info(f"Successfully processed {file_path}: {len(chunks)} chunks created")
            return chunks
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            raise
    
    def _extract_content(self, file_path: Path) -> str:
        """
        Extract text content from file using Unstructured.io
        
        Args:
            file_path: Path to the file
            
        Returns:
            Extracted text content
        """
        try:
            file_extension = file_path.suffix.lower()
            
            # Use specific partitioners for better results
            if file_extension == '.pdf':
                elements = partition_pdf(
                    filename=str(file_path),
                    extract_images_in_pdf=self.config.document_processing.extract_images,
                    infer_table_structure=self.config.document_processing.extract_tables,
                    ocr_languages=self.config.document_processing.ocr_languages
                )
            elif file_extension in ['.docx', '.doc']:
                elements = partition_docx(filename=str(file_path))
            elif file_extension == '.csv':
                elements = partition_csv(filename=str(file_path))
            elif file_extension in ['.txt', '.md']:
                elements = partition_text(filename=str(file_path))
            else:
                # Use auto partitioner for other formats
                elements = partition(filename=str(file_path))
            
            # Extract text from elements
            content_parts = []
            for element in elements:
                if hasattr(element, 'text') and element.text:
                    content_parts.append(element.text)
            
            content = '\n\n'.join(content_parts)
            
            if not content.strip():
                logger.warning(f"No content extracted from {file_path}")
                return ""
            
            return content
            
        except Exception as e:
            logger.error(f"Error extracting content from {file_path}: {str(e)}")
            # Fallback to simple text reading
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            except Exception as fallback_error:
                logger.error(f"Fallback reading failed for {file_path}: {str(fallback_error)}")
                raise e
    
    def _clean_content(self, content: str) -> str:
        """
        Clean and preprocess content
        
        Args:
            content: Raw content to clean
            
        Returns:
            Cleaned content
        """
        if not self.config.document_processing.clean_whitespace:
            return content
        
        # Remove excessive whitespace
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line:  # Skip empty lines
                cleaned_lines.append(line)
        
        # Join with single newlines
        cleaned_content = '\n'.join(cleaned_lines)
        
        # Remove multiple consecutive newlines
        import re
        cleaned_content = re.sub(r'\n{3,}', '\n\n', cleaned_content)
        
        return cleaned_content
    
    def _create_chunks(self, content: str, metadata: DocumentMetadata) -> List[DocumentChunk]:
        """
        Create document chunks using the configured chunking strategy
        
        Args:
            content: Content to chunk
            metadata: Document metadata
            
        Returns:
            List of DocumentChunk objects
        """
        strategy = self.config.chunking.strategy
        
        if strategy == ChunkingStrategy.FIXED_SIZE:
            return self._chunk_fixed_size(content, metadata)
        elif strategy == ChunkingStrategy.SLIDING_WINDOW:
            return self._chunk_sliding_window(content, metadata)
        elif strategy == ChunkingStrategy.SEMANTIC:
            return self._chunk_semantic(content, metadata)
        elif strategy == ChunkingStrategy.RECURSIVE:
            return self._chunk_recursive(content, metadata)
        else:
            raise ValueError(f"Unsupported chunking strategy: {strategy}")
    
    def _chunk_fixed_size(self, content: str, metadata: DocumentMetadata) -> List[DocumentChunk]:
        """Fixed size chunking"""
        chunks = []
        chunk_size = self.config.chunking.chunk_size
        overlap = self.config.chunking.chunk_overlap
        
        start = 0
        chunk_index = 0
        
        while start < len(content):
            end = min(start + chunk_size, len(content))
            chunk_content = content[start:end]
            
            if len(chunk_content.strip()) >= self.config.chunking.min_chunk_size:
                chunk_id = f"{metadata.checksum}_{chunk_index}"
                
                chunk = DocumentChunk(
                    content=chunk_content.strip(),
                    metadata=metadata,
                    chunk_id=chunk_id,
                    chunk_index=chunk_index,
                    start_char=start,
                    end_char=end
                )
                chunks.append(chunk)
                chunk_index += 1
            
            start = end - overlap
            if start >= len(content):
                break
        
        return chunks
    
    def _chunk_sliding_window(self, content: str, metadata: DocumentMetadata) -> List[DocumentChunk]:
        """Sliding window chunking"""
        chunks = []
        window_size = self.config.chunking.window_size
        step_size = self.config.chunking.step_size
        
        start = 0
        chunk_index = 0
        
        while start < len(content):
            end = min(start + window_size, len(content))
            chunk_content = content[start:end]
            
            if len(chunk_content.strip()) >= self.config.chunking.min_chunk_size:
                chunk_id = f"{metadata.checksum}_{chunk_index}"
                
                chunk = DocumentChunk(
                    content=chunk_content.strip(),
                    metadata=metadata,
                    chunk_id=chunk_id,
                    chunk_index=chunk_index,
                    start_char=start,
                    end_char=end
                )
                chunks.append(chunk)
                chunk_index += 1
            
            start += step_size
            if start >= len(content):
                break
        
        return chunks
    
    def _chunk_recursive(self, content: str, metadata: DocumentMetadata) -> List[DocumentChunk]:
        """Recursive chunking using text splitters"""
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunking.chunk_size,
            chunk_overlap=self.config.chunking.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        text_chunks = text_splitter.split_text(content)
        chunks = []
        
        current_pos = 0
        for chunk_index, chunk_content in enumerate(text_chunks):
            if len(chunk_content.strip()) >= self.config.chunking.min_chunk_size:
                # Find the position of this chunk in the original content
                start_pos = content.find(chunk_content, current_pos)
                if start_pos == -1:
                    start_pos = current_pos
                
                end_pos = start_pos + len(chunk_content)
                current_pos = end_pos
                
                chunk_id = f"{metadata.checksum}_{chunk_index}"
                
                chunk = DocumentChunk(
                    content=chunk_content.strip(),
                    metadata=metadata,
                    chunk_id=chunk_id,
                    chunk_index=chunk_index,
                    start_char=start_pos,
                    end_char=end_pos
                )
                chunks.append(chunk)
        
        return chunks
    
    def _chunk_semantic(self, content: str, metadata: DocumentMetadata) -> List[DocumentChunk]:
        """Semantic chunking (simplified implementation)"""
        # For now, use recursive chunking as semantic chunking requires more complex NLP
        # In a full implementation, this would use sentence embeddings to group semantically similar sentences
        logger.warning("Semantic chunking not fully implemented, falling back to recursive chunking")
        return self._chunk_recursive(content, metadata)
    
    def process_directory(self, directory_path: Union[str, Path], recursive: bool = True) -> List[DocumentChunk]:
        """
        Process all supported files in a directory
        
        Args:
            directory_path: Path to the directory
            recursive: Whether to process subdirectories
            
        Returns:
            List of all DocumentChunk objects
        """
        directory_path = Path(directory_path)
        
        if not directory_path.exists() or not directory_path.is_dir():
            raise ValueError(f"Invalid directory path: {directory_path}")
        
        all_chunks = []
        
        # Get all files to process
        if recursive:
            files = [f for f in directory_path.rglob("*") if f.is_file() and self.is_supported_format(f)]
        else:
            files = [f for f in directory_path.iterdir() if f.is_file() and self.is_supported_format(f)]
        
        logger.info(f"Processing {len(files)} files from {directory_path}")
        
        for file_path in files:
            try:
                chunks = self.process_file(file_path)
                all_chunks.extend(chunks)
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {str(e)}")
                continue
        
        logger.info(f"Successfully processed {len(files)} files, created {len(all_chunks)} chunks")
        return all_chunks
    
    def process_content(self, content: str, source: str = "string", title: str = "Document") -> List[DocumentChunk]:
        """
        Process content directly from string
        
        Args:
            content: Content to process
            source: Source identifier
            title: Document title
            
        Returns:
            List of DocumentChunk objects
        """
        # Create metadata for string content
        metadata = DocumentMetadata(
            title=title,
            source=source,
            file_type=".txt",
            file_size=len(content.encode('utf-8')),
            created_date=datetime.now(),
            modified_date=datetime.now(),
            category=self._determine_category(title, content),
            tags=self._extract_tags(title, content),
            word_count=len(content.split()),
            checksum=self._calculate_checksum(content)
        )
        
        # Clean content
        cleaned_content = self._clean_content(content)
        
        # Create chunks
        chunks = self._create_chunks(cleaned_content, metadata)
        
        return chunks


# Export main classes
__all__ = [
    "DocumentProcessor",
    "DocumentMetadata", 
    "DocumentChunk"
]