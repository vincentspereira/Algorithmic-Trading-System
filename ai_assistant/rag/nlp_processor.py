"""
NLP Processor for AI Assistant - Phase 3
Advanced Natural Language Processing using Hugging Face Transformers

This module provides comprehensive NLP capabilities including:
1. Financial sentiment analysis using FinBERT and other domain-specific models
2. Named Entity Recognition (NER) for companies, tickers, and financial terms
3. Text summarization for long documents and reports
4. Question answering capabilities for financial queries
5. Multi-model support with caching and performance optimization

The processor integrates seamlessly with the AI Assistant's existing tools
and provides real-time analysis capabilities with confidence scores.
"""

import os
import re
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import hashlib

import torch
import numpy as np
from transformers import (
    AutoTokenizer, AutoModelForSequenceClassification,
    AutoModelForTokenClassification, AutoModelForQuestionAnswering,
    pipeline, BertTokenizer, BertForSequenceClassification,
    RobertaTokenizer, RobertaForSequenceClassification,
    T5Tokenizer, T5ForConditionalGeneration
)
from sentence_transformers import SentenceTransformer
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Supported NLP model types"""
    FINBERT = "finbert"
    ROBERTA_FINANCIAL = "roberta_financial"
    BERT_BASE = "bert_base"
    DISTILBERT = "distilbert"
    T5_SUMMARIZATION = "t5_summarization"
    BERT_NER = "bert_ner"
    ROBERTA_QA = "roberta_qa"


class SentimentLabel(Enum):
    """Financial sentiment labels"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    BULLISH = "bullish"
    BEARISH = "bearish"


class EntityType(Enum):
    """Financial entity types for NER"""
    COMPANY = "ORG"
    TICKER = "TICKER"
    PERSON = "PER"
    MONEY = "MONEY"
    PERCENT = "PERCENT"
    DATE = "DATE"
    FINANCIAL_TERM = "FIN_TERM"


@dataclass
class NLPResult:
    """Base class for NLP processing results"""
    text: str
    model_used: str
    confidence: float
    processing_time: float
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SentimentResult(NLPResult):
    """Sentiment analysis result"""
    sentiment: SentimentLabel
    scores: Dict[str, float] = field(default_factory=dict)
    financial_indicators: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityResult(NLPResult):
    """Named Entity Recognition result"""
    entities: List[Dict[str, Any]] = field(default_factory=list)
    entity_counts: Dict[str, int] = field(default_factory=dict)
    relationships: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class SummarizationResult(NLPResult):
    """Text summarization result"""
    summary: str
    compression_ratio: float
    key_points: List[str] = field(default_factory=list)
    original_length: int = 0
    summary_length: int = 0


@dataclass
class QAResult(NLPResult):
    """Question answering result"""
    question: str
    answer: str
    context: str
    start_position: int
    end_position: int
    answer_confidence: float


class NLPProcessor:
    """
    Advanced NLP processor with financial domain specialization
    
    Features:
    - Multi-model support with automatic model selection
    - Caching for improved performance
    - Batch processing capabilities
    - Real-time confidence scoring
    - Financial domain optimization
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the NLP processor
        
        Args:
            config_path: Path to configuration file (optional)
        """
        self.config = self._load_config(config_path)
        self.models = {}
        self.tokenizers = {}
        self.pipelines = {}
        self.cache = {}
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        logger.info(f"NLP Processor initialized with device: {self.device}")
        
        # Initialize core models
        self._initialize_models()
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load configuration from file or use defaults"""
        default_config = {
            "models": {
                "finbert": {
                    "model_name": "ProsusAI/finbert",
                    "cache_dir": "./models/finbert",
                    "max_length": 512
                },
                "roberta_financial": {
                    "model_name": "cardiffnlp/twitter-roberta-base-sentiment-latest",
                    "cache_dir": "./models/roberta_financial",
                    "max_length": 512
                },
                "bert_ner": {
                    "model_name": "dbmdz/bert-large-cased-finetuned-conll03-english",
                    "cache_dir": "./models/bert_ner",
                    "max_length": 512
                },
                "t5_summarization": {
                    "model_name": "t5-small",
                    "cache_dir": "./models/t5_summarization",
                    "max_length": 512,
                    "min_length": 50
                },
                "roberta_qa": {
                    "model_name": "deepset/roberta-base-squad2",
                    "cache_dir": "./models/roberta_qa",
                    "max_length": 512
                }
            },
            "cache": {
                "enabled": True,
                "max_size": 1000,
                "ttl_hours": 24
            },
            "performance": {
                "batch_size": 16,
                "max_workers": 4,
                "timeout_seconds": 30
            },
            "financial_terms": [
                "earnings", "revenue", "profit", "loss", "dividend", "stock", "share",
                "market", "trading", "investment", "portfolio", "risk", "return",
                "volatility", "bull", "bear", "growth", "value", "momentum"
            ]
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                    # Merge with defaults
                    default_config.update(user_config)
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")
        
        # Load financial domain data from external JSON
        financial_data_path = Path(__file__).parent.parent / "config" / "financial_nlp_data.json"
        if financial_data_path.exists():
            try:
                with open(financial_data_path, 'r') as f:
                    financial_data = json.load(f)
                    default_config["financial_terms"] = financial_data.get("financial_terms", [])
                    # Add other financial domain data as needed
            except Exception as e:
                logger.warning(f"Failed to load financial terms from {financial_data_path}: {e}")
        else:
            logger.warning(f"Financial domain data file not found: {financial_data_path}")

        return default_config
    
    def _initialize_models(self):
        """Initialize core NLP models"""
        try:
            # Initialize FinBERT for financial sentiment
            self._load_finbert()
            
            # Initialize RoBERTa for general sentiment
            self._load_roberta_sentiment()
            
            # Initialize BERT for NER
            self._load_bert_ner()
            
            # Initialize T5 for summarization
            self._load_t5_summarization()
            
            # Initialize RoBERTa for QA
            self._load_roberta_qa()
            
            logger.info("All NLP models initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing models: {e}")
            raise
    
    def _load_finbert(self):
        """Load FinBERT model for financial sentiment analysis"""
        try:
            model_config = self.config["models"]["finbert"]
            model_name = model_config["model_name"]
            cache_dir = model_config["cache_dir"]
            
            # Create cache directory
            os.makedirs(cache_dir, exist_ok=True)
            
            # Load tokenizer and model
            self.tokenizers["finbert"] = AutoTokenizer.from_pretrained(
                model_name, cache_dir=cache_dir
            )
            self.models["finbert"] = AutoModelForSequenceClassification.from_pretrained(
                model_name, cache_dir=cache_dir
            ).to(self.device)
            
            # Create pipeline
            self.pipelines["finbert"] = pipeline(
                "sentiment-analysis",
                model=self.models["finbert"],
                tokenizer=self.tokenizers["finbert"],
                device=0 if self.device.type == "cuda" else -1
            )
            
            logger.info("FinBERT model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load FinBERT: {e}")
            # Fallback to a simpler model
            self._load_fallback_sentiment_model()
    
    def _load_roberta_sentiment(self):
        """Load RoBERTa model for general sentiment analysis"""
        try:
            model_config = self.config["models"]["roberta_financial"]
            model_name = model_config["model_name"]
            cache_dir = model_config["cache_dir"]
            
            os.makedirs(cache_dir, exist_ok=True)
            
            self.pipelines["roberta_sentiment"] = pipeline(
                "sentiment-analysis",
                model=model_name,
                device=0 if self.device.type == "cuda" else -1
            )
            
            logger.info("RoBERTa sentiment model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load RoBERTa sentiment: {e}")
    
    def _load_bert_ner(self):
        """Load BERT model for Named Entity Recognition"""
        try:
            model_config = self.config["models"]["bert_ner"]
            model_name = model_config["model_name"]
            cache_dir = model_config["cache_dir"]
            
            os.makedirs(cache_dir, exist_ok=True)
            
            self.pipelines["bert_ner"] = pipeline(
                "ner",
                model=model_name,
                tokenizer=model_name,
                aggregation_strategy="simple",
                device=0 if self.device.type == "cuda" else -1
            )
            
            logger.info("BERT NER model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load BERT NER: {e}")
    
    def _load_t5_summarization(self):
        """Load T5 model for text summarization"""
        try:
            model_config = self.config["models"]["t5_summarization"]
            model_name = model_config["model_name"]
            cache_dir = model_config["cache_dir"]
            
            os.makedirs(cache_dir, exist_ok=True)
            
            self.pipelines["t5_summarization"] = pipeline(
                "summarization",
                model=model_name,
                device=0 if self.device.type == "cuda" else -1
            )
            
            logger.info("T5 summarization model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load T5 summarization: {e}")
    
    def _load_roberta_qa(self):
        """Load RoBERTa model for question answering"""
        try:
            model_config = self.config["models"]["roberta_qa"]
            model_name = model_config["model_name"]
            cache_dir = model_config["cache_dir"]
            
            os.makedirs(cache_dir, exist_ok=True)
            
            self.pipelines["roberta_qa"] = pipeline(
                "question-answering",
                model=model_name,
                device=0 if self.device.type == "cuda" else -1
            )
            
            logger.info("RoBERTa QA model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load RoBERTa QA: {e}")
    
    def _load_fallback_sentiment_model(self):
        """Load a fallback sentiment model if FinBERT fails"""
        try:
            self.pipelines["fallback_sentiment"] = pipeline(
                "sentiment-analysis",
                model="distilbert-base-uncased-finetuned-sst-2-english",
                device=0 if self.device.type == "cuda" else -1
            )
            logger.info("Fallback sentiment model loaded")
        except Exception as e:
            logger.error(f"Failed to load fallback sentiment model: {e}")
    
    def _get_cache_key(self, text: str, model_type: str, **kwargs) -> str:
        """Generate cache key for text and parameters"""
        content = f"{text}_{model_type}_{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get result from cache if available and not expired"""
        if not self.config["cache"]["enabled"]:
            return None
        
        if cache_key in self.cache:
            result, timestamp = self.cache[cache_key]
            ttl_hours = self.config["cache"]["ttl_hours"]
            
            if datetime.now() - timestamp < timedelta(hours=ttl_hours):
                return result
            else:
                # Remove expired entry
                del self.cache[cache_key]
        
        return None
    
    def _save_to_cache(self, cache_key: str, result: Any):
        """Save result to cache"""
        if not self.config["cache"]["enabled"]:
            return
        
        # Check cache size limit
        max_size = self.config["cache"]["max_size"]
        if len(self.cache) >= max_size:
            # Remove oldest entries
            oldest_keys = sorted(
                self.cache.keys(),
                key=lambda k: self.cache[k][1]
            )[:len(self.cache) - max_size + 1]
            
            for key in oldest_keys:
                del self.cache[key]
        
        self.cache[cache_key] = (result, datetime.now())
    
    def analyze_sentiment(
        self,
        text: str,
        model_type: ModelType = ModelType.FINBERT,
        include_financial_indicators: bool = True
    ) -> SentimentResult:
        """
        Analyze sentiment of financial text
        
        Args:
            text: Input text to analyze
            model_type: Model to use for analysis
            include_financial_indicators: Whether to include financial indicators
            
        Returns:
            SentimentResult with sentiment analysis
        """
        start_time = datetime.now()
        
        # Check cache
        cache_key = self._get_cache_key(
            text, model_type.value, include_financial_indicators=include_financial_indicators
        )
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # Select appropriate pipeline
            if model_type == ModelType.FINBERT and "finbert" in self.pipelines:
                pipeline_name = "finbert"
            elif "roberta_sentiment" in self.pipelines:
                pipeline_name = "roberta_sentiment"
            elif "fallback_sentiment" in self.pipelines:
                pipeline_name = "fallback_sentiment"
            else:
                raise ValueError("No sentiment analysis model available")
            
            # Perform sentiment analysis
            results = self.pipelines[pipeline_name](text)
            
            # Process results
            if isinstance(results, list):
                result = results[0]
            else:
                result = results
            
            # Map labels to financial sentiment
            label = result["label"].lower()
            confidence = result["score"]
            
            # Map to financial sentiment labels
            if label in ["positive", "pos", "bullish"]:
                sentiment = SentimentLabel.POSITIVE
            elif label in ["negative", "neg", "bearish"]:
                sentiment = SentimentLabel.NEGATIVE
            else:
                sentiment = SentimentLabel.NEUTRAL
            
            # Create scores dictionary
            scores = {sentiment.value: confidence}
            
            # Add financial indicators if requested
            financial_indicators = {}
            if include_financial_indicators:
                financial_indicators = self._extract_financial_indicators(text)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            sentiment_result = SentimentResult(
                text=text,
                model_used=pipeline_name,
                confidence=confidence,
                processing_time=processing_time,
                sentiment=sentiment,
                scores=scores,
                financial_indicators=financial_indicators,
                metadata={
                    "model_type": model_type.value,
                    "text_length": len(text),
                    "device": str(self.device)
                }
            )
            
            # Cache result
            self._save_to_cache(cache_key, sentiment_result)
            
            return sentiment_result
            
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {e}")
            # Return neutral sentiment with low confidence
            processing_time = (datetime.now() - start_time).total_seconds()
            return SentimentResult(
                text=text,
                model_used="error",
                confidence=0.0,
                processing_time=processing_time,
                sentiment=SentimentLabel.NEUTRAL,
                scores={"neutral": 0.5},
                metadata={"error": str(e)}
            )
    
    def extract_entities(
        self,
        text: str,
        include_financial_terms: bool = True,
        extract_tickers: bool = True
    ) -> EntityResult:
        """
        Extract named entities from financial text
        
        Args:
            text: Input text to analyze
            include_financial_terms: Whether to identify financial terms
            extract_tickers: Whether to extract stock tickers
            
        Returns:
            EntityResult with extracted entities
        """
        start_time = datetime.now()
        
        # Check cache
        cache_key = self._get_cache_key(
            text, "ner", 
            include_financial_terms=include_financial_terms,
            extract_tickers=extract_tickers
        )
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        try:
            entities = []
            entity_counts = {}
            
            # Use BERT NER if available
            if "bert_ner" in self.pipelines:
                ner_results = self.pipelines["bert_ner"](text)
                
                for entity in ner_results:
                    entity_info = {
                        "text": entity["word"],
                        "label": entity["entity_group"],
                        "confidence": entity["score"],
                        "start": entity["start"],
                        "end": entity["end"]
                    }
                    entities.append(entity_info)
                    
                    # Count entities by type
                    label = entity["entity_group"]
                    entity_counts[label] = entity_counts.get(label, 0) + 1
            
            # Extract stock tickers if requested
            if extract_tickers:
                ticker_entities = self._extract_tickers(text)
                entities.extend(ticker_entities)
                if ticker_entities:
                    entity_counts["TICKER"] = len(ticker_entities)
            
            # Extract financial terms if requested
            if include_financial_terms:
                financial_entities = self._extract_financial_terms(text)
                entities.extend(financial_entities)
                if financial_entities:
                    entity_counts["FIN_TERM"] = len(financial_entities)
            
            # Extract relationships between entities
            relationships = self._extract_entity_relationships(entities, text)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            entity_result = EntityResult(
                text=text,
                model_used="bert_ner" if "bert_ner" in self.pipelines else "rule_based",
                confidence=np.mean([e.get("confidence", 0.5) for e in entities]) if entities else 0.0,
                processing_time=processing_time,
                entities=entities,
                entity_counts=entity_counts,
                relationships=relationships,
                metadata={
                    "total_entities": len(entities),
                    "unique_types": len(entity_counts),
                    "text_length": len(text)
                }
            )
            
            # Cache result
            self._save_to_cache(cache_key, entity_result)
            
            return entity_result
            
        except Exception as e:
            logger.error(f"Error in entity extraction: {e}")
            processing_time = (datetime.now() - start_time).total_seconds()
            return EntityResult(
                text=text,
                model_used="error",
                confidence=0.0,
                processing_time=processing_time,
                metadata={"error": str(e)}
            )
    
    def summarize_text(
        self,
        text: str,
        max_length: Optional[int] = None,
        min_length: Optional[int] = None,
        extract_key_points: bool = True
    ) -> SummarizationResult:
        """
        Summarize long financial documents
        
        Args:
            text: Input text to summarize
            max_length: Maximum length of summary
            min_length: Minimum length of summary
            extract_key_points: Whether to extract key points
            
        Returns:
            SummarizationResult with summary and key points
        """
        start_time = datetime.now()
        
        # Check cache
        cache_key = self._get_cache_key(
            text, "summarization",
            max_length=max_length, min_length=min_length,
            extract_key_points=extract_key_points
        )
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        try:
            original_length = len(text)
            
            # Set default lengths based on input
            if max_length is None:
                max_length = min(512, max(50, original_length // 4))
            if min_length is None:
                min_length = min(50, max_length // 3)
            
            # Use T5 summarization if available
            if "t5_summarization" in self.pipelines:
                # Chunk text if too long
                max_input_length = 512
                if len(text) > max_input_length:
                    chunks = self._chunk_text(text, max_input_length)
                    summaries = []
                    
                    for chunk in chunks:
                        chunk_summary = self.pipelines["t5_summarization"](
                            chunk,
                            max_length=max_length // len(chunks),
                            min_length=min_length // len(chunks),
                            do_sample=False
                        )
                        summaries.append(chunk_summary[0]["summary_text"])
                    
                    # Combine chunk summaries
                    combined_summary = " ".join(summaries)
                    
                    # Summarize the combined summary if still too long
                    if len(combined_summary) > max_length:
                        final_summary = self.pipelines["t5_summarization"](
                            combined_summary,
                            max_length=max_length,
                            min_length=min_length,
                            do_sample=False
                        )
                        summary = final_summary[0]["summary_text"]
                    else:
                        summary = combined_summary
                else:
                    # Single summarization
                    result = self.pipelines["t5_summarization"](
                        text,
                        max_length=max_length,
                        min_length=min_length,
                        do_sample=False
                    )
                    summary = result[0]["summary_text"]
            else:
                # Fallback to extractive summarization
                summary = self._extractive_summarization(text, max_length)
            
            summary_length = len(summary)
            compression_ratio = summary_length / original_length if original_length > 0 else 0
            
            # Extract key points if requested
            key_points = []
            if extract_key_points:
                key_points = self._extract_key_points(text, summary)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            summarization_result = SummarizationResult(
                text=text,
                model_used="t5_summarization" if "t5_summarization" in self.pipelines else "extractive",
                confidence=0.8,  # Default confidence for summarization
                processing_time=processing_time,
                summary=summary,
                compression_ratio=compression_ratio,
                key_points=key_points,
                original_length=original_length,
                summary_length=summary_length,
                metadata={
                    "max_length": max_length,
                    "min_length": min_length,
                    "chunks_processed": len(self._chunk_text(text, 512)) if len(text) > 512 else 1
                }
            )
            
            # Cache result
            self._save_to_cache(cache_key, summarization_result)
            
            return summarization_result
            
        except Exception as e:
            logger.error(f"Error in text summarization: {e}")
            processing_time = (datetime.now() - start_time).total_seconds()
            return SummarizationResult(
                text=text,
                model_used="error",
                confidence=0.0,
                processing_time=processing_time,
                summary="Error occurred during summarization",
                compression_ratio=0.0,
                original_length=len(text),
                summary_length=0,
                metadata={"error": str(e)}
            )
    
    def answer_question(
        self,
        question: str,
        context: str,
        max_answer_length: int = 100
    ) -> QAResult:
        """
        Answer questions based on provided context
        
        Args:
            question: Question to answer
            context: Context text containing the answer
            max_answer_length: Maximum length of answer
            
        Returns:
            QAResult with answer and confidence
        """
        start_time = datetime.now()
        
        # Check cache
        cache_key = self._get_cache_key(
            f"{question}_{context}", "qa",
            max_answer_length=max_answer_length
        )
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # Use RoBERTa QA if available
            if "roberta_qa" in self.pipelines:
                result = self.pipelines["roberta_qa"](
                    question=question,
                    context=context
                )
                
                answer = result["answer"]
                confidence = result["score"]
                start_pos = result["start"]
                end_pos = result["end"]
            else:
                # Fallback to simple keyword matching
                answer, confidence, start_pos, end_pos = self._simple_qa(question, context)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            qa_result = QAResult(
                text=f"Q: {question}\nContext: {context[:200]}...",
                model_used="roberta_qa" if "roberta_qa" in self.pipelines else "keyword_matching",
                confidence=confidence,
                processing_time=processing_time,
                question=question,
                answer=answer,
                context=context,
                start_position=start_pos,
                end_position=end_pos,
                answer_confidence=confidence,
                metadata={
                    "question_length": len(question),
                    "context_length": len(context),
                    "answer_length": len(answer)
                }
            )
            
            # Cache result
            self._save_to_cache(cache_key, qa_result)
            
            return qa_result
            
        except Exception as e:
            logger.error(f"Error in question answering: {e}")
            processing_time = (datetime.now() - start_time).total_seconds()
            return QAResult(
                text=f"Q: {question}",
                model_used="error",
                confidence=0.0,
                processing_time=processing_time,
                question=question,
                answer="Error occurred while processing question",
                context=context,
                start_position=0,
                end_position=0,
                answer_confidence=0.0,
                metadata={"error": str(e)}
            )
    
    def _extract_financial_indicators(self, text: str) -> Dict[str, Any]:
        """Extract financial indicators from text"""
        indicators = {
            "mentions_earnings": bool(re.search(r'\bearnings?\b', text, re.IGNORECASE)),
            "mentions_revenue": bool(re.search(r'\brevenue\b', text, re.IGNORECASE)),
            "mentions_profit": bool(re.search(r'\bloss\b', text, re.IGNORECASE)),
            "mentions_loss": bool(re.search(r'\bloss\b', text, re.IGNORECASE)),
            "mentions_growth": bool(re.search(r'\bgrowth\b', text, re.IGNORECASE)),
            "mentions_decline": bool(re.search(r'\bdecline\b', text, re.IGNORECASE)),
            "has_percentages": bool(re.search(r'\d+\.?\d*%', text)),
            "has_dollar_amounts": bool(re.search(r'\$\d+', text)),
            "financial_term_count": len([term for term in self.config["financial_terms"] 
                                       if term.lower() in text.lower()])
        }
        return indicators
    
    def _extract_tickers(self, text: str) -> List[Dict[str, Any]]:
        """Extract stock ticker symbols from text"""
        # Pattern for stock tickers (1-5 uppercase letters)
        ticker_pattern = r'\b[A-Z]{1,5}\b'
        matches = re.finditer(ticker_pattern, text)
        
        tickers = []
        for match in matches:
            ticker_text = match.group()
            # Filter out common words that might match the pattern
            if ticker_text not in ['THE', 'AND', 'OR', 'FOR', 'WITH', 'FROM', 'TO', 'IN', 'ON', 'AT']:
                tickers.append({
                    "text": ticker_text,
                    "label": "TICKER",
                    "confidence": 0.8,
                    "start": match.start(),
                    "end": match.end()
                })
        
        return tickers
    
    def _extract_financial_terms(self, text: str) -> List[Dict[str, Any]]:
        """Extract financial terms from text"""
        financial_terms = []
        text_lower = text.lower()
        
        for term in self.config["financial_terms"]:
            pattern = r'\b' + re.escape(term.lower()) + r'\b'
            matches = re.finditer(pattern, text_lower)
            
            for match in matches:
                financial_terms.append({
                    "text": text[match.start():match.end()],
                    "label": "FIN_TERM",
                    "confidence": 0.7,
                    "start": match.start(),
                    "end": match.end()
                })
        
        return financial_terms
    
    def _extract_entity_relationships(self, entities: List[Dict[str, Any]], text: str) -> List[Dict[str, Any]]:
        """Extract relationships between entities"""
        relationships = []
        
        # Simple relationship extraction based on proximity
        for i, entity1 in enumerate(entities):
            for j, entity2 in enumerate(entities[i+1:], i+1):
                # Check if entities are close to each other
                distance = abs(entity1["start"] - entity2["start"])
                if distance < 100:  # Within 100 characters
                    relationships.append({
                        "entity1": entity1["text"],
                        "entity2": entity2["text"],
                        "type": "proximity",
                        "distance": distance,
                        "confidence": max(0.1, 1.0 - distance / 100.0)
                    })
        
        return relationships
    
    def _chunk_text(self, text: str, max_length: int) -> List[str]:
        """Split text into chunks of maximum length"""
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_length = len(word) + 1  # +1 for space
            if current_length + word_length > max_length and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    def _extractive_summarization(self, text: str, max_length: int) -> str:
        """Simple extractive summarization as fallback"""
        sentences = text.split('. ')
        if len(sentences) <= 3:
            return text
        
        # Score sentences based on financial terms
        scored_sentences = []
        for sentence in sentences:
            score = 0
            for term in self.config["financial_terms"]:
                if term.lower() in sentence.lower():
                    score += 1
            scored_sentences.append((sentence, score))
        
        # Sort by score and take top sentences
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        top_sentences = scored_sentences[:3]
        
        # Reconstruct summary
        summary = '. '.join([s[0] for s in top_sentences])
        
        # Truncate if too long
        if len(summary) > max_length:
            summary = summary[:max_length-3] + "..."
        
        return summary
    
    def _extract_key_points(self, text: str, summary: str) -> List[str]:
        """Extract key points from text and summary"""
        key_points = []
        
        # Look for bullet points or numbered lists
        bullet_pattern = r'[•\-\*\]\s*(.+)'
        number_pattern = r'\d+\.\s*(.+)'
        
        for pattern in [bullet_pattern, number_pattern]:
            matches = re.findall(pattern, text)
            key_points.extend(matches[:5])  # Limit to 5 points
        
        # If no structured points found, extract from summary
        if not key_points:
            sentences = summary.split('. ')
            key_points = [s.strip() for s in sentences[:3] if len(s.strip()) > 10]
        
        return key_points[:5]  # Maximum 5 key points
    
    def _simple_qa(self, question: str, context: str) -> Tuple[str, float, int, int]:
        """Simple keyword-based question answering as fallback"""
        question_words = set(question.lower().split())
        context_lower = context.lower()
        
        # Find sentences containing question keywords
        sentences = context.split('. ')
        best_sentence = ""
        best_score = 0
        best_start = 0
        best_end = 0
        
        for sentence in sentences:
            sentence_words = set(sentence.lower().split())
            overlap = len(question_words.intersection(sentence_words))
            
            if overlap > best_score:
                best_score = overlap
                best_sentence = sentence.strip()
                best_start = context.find(sentence)
                best_end = best_start + len(sentence)
        
        if best_sentence:
            confidence = min(0.8, best_score / len(question_words))
            return best_sentence, confidence, best_start, best_end
        else:
            return "No answer found", 0.1, 0, 0
    
    def batch_process(
        self,
        texts: List[str],
        operation: str,
        **kwargs
    ) -> List[Any]:
        """
        Process multiple texts in batch for improved performance
        
        Args:
            texts: List of texts to process
            operation: Operation to perform ('sentiment', 'entities', 'summarize', 'qa')
            **kwargs: Additional arguments for the operation
            
        Returns:
            List of results for each text
        """
        results = []
        
        for text in texts:
            try:
                if operation == "sentiment":
                    result = self.analyze_sentiment(text, **kwargs)
                    results.append({
                        "text": text,
                        "sentiment": result.sentiment.value,
                        "confidence": result.confidence,
                        "processing_time": result.processing_time
                    })
                
                elif operation == "classification":
                    result = self.classify_document(text, **kwargs)
                    results.append({
                        "text": text,
                        "category": result.category.value,
                        "confidence": result.confidence,
                        "processing_time": result.processing_time
                    })
                
                elif operation == "risk":
                    result = self.assess_risk(text)
                    results.append({
                        "text": text,
                        "risk_level": result.risk_level.value,
                        "confidence": result.confidence,
                        "processing_time": result.processing_time
                    })
                
                elif operation == "comprehensive":
                    result = self.comprehensive_analysis(text, **kwargs)
                    results.append(result)
                
                else:
                    raise ValueError(f"Unsupported operation: {operation}")
                    
            except Exception as e:
                logger.error(f"Error analyzing text: {e}")
                results.append({
                    "text": text,
                    "error": str(e)
                })
        
        return results
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded models"""
        return {
            "available_models": list(self.pipelines.keys()),
            "device": str(self.device),
            "cache_size": len(self.cache),
            "config": self.config,
            "model_details": {
                name: {
                    "loaded": name in self.pipelines,
                    "model_name": self.config["models"].get(name, {}).get("model_name", "Unknown")
                }
                for name in ["finbert", "roberta_sentiment", "bert_ner", "t5_summarization", "roberta_qa"]
            }
        }
    
    def clear_cache(self):
        """Clear the processing cache"""
        self.cache.clear()
        logger.info("NLP processor cache cleared")
    
    def __del__(self):
        """Cleanup when processor is destroyed"""
        try:
            # Clear cache
            self.cache.clear()
            
            # Move models to CPU to free GPU memory
            if hasattr(self, 'models'):
                for model in self.models.values():
                    if hasattr(model, 'cpu'):
                        model.cpu()
            
            logger.info("NLP Processor cleanup completed")
        except Exception as e:
            logger.error(f"Error during NLP Processor cleanup: {e}")


# Factory function for easy initialization
def create_nlp_processor(config_path: Optional[str] = None) -> NLPProcessor:
    """
    Factory function to create and initialize NLP processor
    
    Args:
        config_path: Optional path to configuration file
        
    Returns:
        Initialized NLPProcessor instance
    """
    return NLPProcessor(config_path)


# Export main classes and functions
__all__ = [
    "NLPProcessor",
    "NLPResult",
    "SentimentResult",
    "EntityResult",
    "SummarizationResult",
    "QAResult",
    "ModelType",
    "SentimentLabel",
    "EntityType",
    "create_nlp_processor"
]
