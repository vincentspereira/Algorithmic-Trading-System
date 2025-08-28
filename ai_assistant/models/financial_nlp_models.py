"""
Financial NLP Models for AI Assistant - Phase 3
Specialized financial NLP models including FinBERT and domain-specific implementations

This module provides:
1. FinBERT integration for financial sentiment analysis
2. Custom tokenizers for financial terminology
3. Domain-specific embeddings for financial texts
4. Text classification for document categorization
5. Relation extraction for financial entities
6. Financial news analysis and market sentiment detection

All models are optimized for financial domain understanding and provide
enhanced accuracy for trading and investment-related text analysis.
"""

import os
import re
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple, Set
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import pickle
import warnings

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import pandas as pd
from transformers import (
    AutoTokenizer, AutoModelForSequenceClassification,
    AutoModelForTokenClassification, AutoConfig,
    BertTokenizer, BertForSequenceClassification, BertModel,
    RobertaTokenizer, RobertaForSequenceClassification, RobertaModel,
    pipeline, Trainer, TrainingArguments
)
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress warnings
warnings.filterwarnings('ignore', category=UserWarning)


class FinancialModelType(Enum):
    """Types of financial NLP models"""
    FINBERT_SENTIMENT = "finbert_sentiment"
    FINBERT_ESG = "finbert_esg"
    FINANCIAL_ROBERTA = "financial_roberta"
    SECTOR_CLASSIFIER = "sector_classifier"
    RISK_CLASSIFIER = "risk_classifier"
    EARNINGS_ANALYZER = "earnings_analyzer"
    NEWS_CATEGORIZER = "news_categorizer"
    ENTITY_EXTRACTOR = "entity_extractor"


class FinancialSentiment(Enum):
    """Financial sentiment labels"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    NEGATIVE = "negative"
    UNCERTAIN = "uncertain"


class FinancialCategory(Enum):
    """Financial document categories"""
    EARNINGS_REPORT = "earnings_report"
    NEWS_ARTICLE = "news_article"
    ANALYST_REPORT = "analyst_report"
    SEC_FILING = "sec_filing"
    PRESS_RELEASE = "press_release"
    RESEARCH_NOTE = "research_note"
    MARKET_COMMENTARY = "market_commentary"
    ECONOMIC_DATA = "economic_data"


class RiskLevel(Enum):
    """Risk assessment levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FinancialAnalysisResult:
    """Result from financial NLP analysis"""
    text: str
    model_type: FinancialModelType
    confidence: float
    processing_time: float
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FinancialSentimentResult(FinancialAnalysisResult):
    """Financial sentiment analysis result"""
    sentiment: FinancialSentiment
    sentiment_scores: Dict[str, float] = field(default_factory=dict)
    market_indicators: Dict[str, Any] = field(default_factory=dict)
    key_phrases: List[str] = field(default_factory=list)


@dataclass
class DocumentClassificationResult(FinancialAnalysisResult):
    """Document classification result"""
    category: FinancialCategory
    category_scores: Dict[str, float] = field(default_factory=dict)
    subcategory: Optional[str] = None
    topics: List[str] = field(default_factory=list)


@dataclass
class RiskAssessmentResult(FinancialAnalysisResult):
    """Risk assessment result"""
    risk_level: RiskLevel
    risk_factors: List[str] = field(default_factory=list)
    risk_scores: Dict[str, float] = field(default_factory=dict)
    mitigation_suggestions: List[str] = field(default_factory=list)


@dataclass
class EntityRelationResult(FinancialAnalysisResult):
    """Entity relation extraction result"""
    entities: List[Dict[str, Any]] = field(default_factory=list)
    relations: List[Dict[str, Any]] = field(default_factory=list)
    entity_network: Dict[str, List[str]] = field(default_factory=dict)


class FinancialTokenizer:
    """
    Custom tokenizer for financial texts with domain-specific vocabulary
    """
    
    def __init__(self, base_tokenizer_name: str = "bert-base-uncased"):
        """
        Initialize financial tokenizer
        
        Args:
            base_tokenizer_name: Base tokenizer to extend
        """
        self.base_tokenizer = AutoTokenizer.from_pretrained(base_tokenizer_name)
        self.financial_vocab = self._load_financial_vocabulary()
        self.special_tokens = self._get_financial_special_tokens()
        
        # Add financial tokens to vocabulary
        self._extend_vocabulary()
        
        logger.info(f"Financial tokenizer initialized with {len(self.financial_vocab)} domain terms")
    
    def _load_financial_vocabulary(self) -> Set[str]:
        """Load financial domain vocabulary"""
        # Load from external JSON file
        financial_data_path = Path(__file__).parent.parent / "config" / "financial_nlp_data.json"
        if financial_data_path.exists():
            try:
                with open(financial_data_path, 'r') as f:
                    financial_data = json.load(f)
                    return set(financial_data.get("financial_terms", []))
            except Exception as e:
                logger.warning(f"Failed to load financial terms from {financial_data_path}: {e}")
        
        # Fallback to hardcoded if file not found or error
        return {
            # Market terms
            "bullish", "bearish", "volatility", "liquidity", "momentum",
            "resistance", "support", "breakout", "pullback", "correction",
            
            # Financial instruments
            "equity", "bond", "derivative", "option", "future", "swap",
            "etf", "reit", "commodity", "forex", "cryptocurrency",
            
            # Financial metrics
            "pe_ratio", "eps", "ebitda", "roe", "roa", "debt_to_equity",
            "current_ratio", "quick_ratio", "gross_margin", "net_margin",
            
            # Corporate actions
            "dividend", "split", "merger", "acquisition", "spinoff",
            "buyback", "rights_issue", "ipo", "delisting",
            
            # Economic indicators
            "gdp", "inflation", "unemployment", "interest_rate", "yield_curve",
            "cpi", "ppi", "retail_sales", "housing_starts", "jobless_claims",
            
            # Trading terms
            "long", "short", "hedge", "arbitrage", "scalping", "swing_trading",
            "day_trading", "position_trading", "algorithmic_trading",
            
            # Risk terms
            "var", "stress_test", "scenario_analysis", "monte_carlo",
            "black_swan", "tail_risk", "correlation", "beta", "alpha",
            
            # Regulatory terms
            "sec", "finra", "basel", "dodd_frank", "mifid", "gdpr",
            "compliance", "audit", "disclosure", "fiduciary"
        }
    
    def _get_financial_special_tokens(self) -> List[str]:
        """Get special tokens for financial domain"""
        return [
            "[TICKER]", "[PRICE]", "[PERCENT]", "[DATE]", "[CURRENCY]",
            "[COMPANY]", "[ANALYST]", "[RATING]", "[TARGET]", "[VOLUME]"
        ]
    
    def _extend_vocabulary(self):
        """Extend base tokenizer with financial vocabulary"""
        # Add special tokens
        self.base_tokenizer.add_special_tokens({
            "additional_special_tokens": self.special_tokens
        })
        
        # Add financial terms (they will be tokenized normally but recognized)
        new_tokens = []
        for term in self.financial_vocab:
            if term not in self.base_tokenizer.vocab:
                new_tokens.append(term)
        
        if new_tokens:
            self.base_tokenizer.add_tokens(new_tokens)
    
    def tokenize(self, text: str, **kwargs) -> List[str]:
        """Tokenize text with financial preprocessing"""
        # Preprocess financial patterns
        processed_text = self._preprocess_financial_text(text)
        
        # Tokenize using base tokenizer
        return self.base_tokenizer.tokenize(processed_text, **kwargs)
    
    def encode(self, text: str, **kwargs) -> List[int]:
        """Encode text to token IDs"""
        processed_text = self._preprocess_financial_text(text)
        return self.base_tokenizer.encode(processed_text, **kwargs)
    
    def decode(self, token_ids: List[int], **kwargs) -> str:
        """Decode token IDs to text"""
        return self.base_tokenizer.decode(token_ids, **kwargs)
    
    def _preprocess_financial_text(self, text: str) -> str:
        """Preprocess text to handle financial patterns"""
        # Replace stock tickers with special token
        text = re.sub(r'\b[A-Z]{1,5}\b(?=\s|$|[^\w])', '[TICKER]', text)
        
        # Replace prices with special token
        text = re.sub(r'\$\d+(?:\.\d{2})?', '[PRICE]', text)
        
        # Replace percentages with special token
        text = re.sub(r'\d+(?:\.\d+)?%', '[PERCENT]', text)
        
        # Replace dates with special token
        text = re.sub(r'\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2}', '[DATE]', text)
        
        # Replace currencies with special token
        text = re.sub(r'(?:USD|EUR|GBP|JPY|CHF|CAD|AUD)\s?\d+', '[CURRENCY]', text)
        
        return text


class FinBERTModel:
    """
    FinBERT model wrapper for financial sentiment analysis
    """
    
    def __init__(self, model_name: str = "ProsusAI/finbert", cache_dir: str = "./models/finbert"):
        """
        Initialize FinBERT model
        
        Args:
            model_name: FinBERT model name from Hugging Face
            cache_dir: Directory to cache the model
        """
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)
        
        # Load model and tokenizer
        self._load_model()
        
        logger.info(f"FinBERT model loaded on {self.device}")
    
    def _load_model(self):
        """Load FinBERT model and tokenizer"""
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name, cache_dir=self.cache_dir
            )
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.model_name, cache_dir=self.cache_dir
            ).to(self.device)
            
            # Create pipeline for easier inference
            self.pipeline = pipeline(
                "sentiment-analysis",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if self.device.type == "cuda" else -1
            )
            
        except Exception as e:
            logger.error(f"Failed to load FinBERT model: {e}")
            raise
    
    def analyze_sentiment(
        self,
        text: str,
        return_all_scores: bool = True
    ) -> FinancialSentimentResult:
        """
        Analyze financial sentiment of text
        
        Args:
            text: Input text to analyze
            return_all_scores: Whether to return scores for all labels
            
        Returns:
            FinancialSentimentResult with sentiment analysis
        """
        start_time = datetime.now()
        
        try:
            # Get prediction from pipeline
            results = self.pipeline(text, return_all_scores=return_all_scores)
            
            if return_all_scores:
                # Extract all scores
                sentiment_scores = {result['label'].lower(): result['score'] for result in results}
                
                # Get the highest scoring sentiment
                best_result = max(results, key=lambda x: x['score'])}
                sentiment_label = best_result['label'].lower()
                confidence = best_result['score']
            else:
                result = results[0]
                sentiment_label = result['label'].lower()
                confidence = result['score']
                sentiment_scores = {sentiment_label: confidence}
            
            # Map to financial sentiment enum
            if sentiment_label in ['positive', 'bullish']:
                sentiment = FinancialSentiment.BULLISH
            elif sentiment_label in ['negative', 'bearish']:
                sentiment = FinancialSentiment.BEARISH
            else:
                sentiment = FinancialSentiment.NEUTRAL
            
            # Extract market indicators
            market_indicators = self._extract_market_indicators(text)
            
            # Extract key phrases
            key_phrases = self._extract_key_phrases(text)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return FinancialSentimentResult(
                text=text,
                model_type=FinancialModelType.FINBERT_SENTIMENT,
                confidence=confidence,
                processing_time=processing_time,
                sentiment=sentiment,
                sentiment_scores=sentiment_scores,
                market_indicators=market_indicators,
                key_phrases=key_phrases,
                metadata={
                    "model_name": self.model_name,
                    "text_length": len(text),
                    "device": str(self.device)
                }
            )
            
        except Exception as e:
            logger.error(f"Error in FinBERT sentiment analysis: {e}")
            processing_time = (datetime.now() - start_time).total_seconds()
            return FinancialSentimentResult(
                text=text,
                model_type=FinancialModelType.FINBERT_SENTIMENT,
                confidence=0.0,
                processing_time=processing_time,
                sentiment=FinancialSentiment.NEUTRAL,
                metadata={"error": str(e)}
            )
    
    def _extract_market_indicators(self, text: str) -> Dict[str, Any]:
        """Extract market indicators from text"""
        indicators = {
            "mentions_earnings": bool(re.search(r'\bearnings?\b', text, re.IGNORECASE)),
            "mentions_revenue": bool(re.search(r'\brevenue\b', text, re.IGNORECASE)),
            "mentions_guidance": bool(re.search(r'\bguidance\b', text, re.IGNORECASE)),
            "mentions_outlook": bool(re.search(r'\boutlook\b', text, re.IGNORECASE)),
            "mentions_growth": bool(re.search(r'\bgrowth\b', text, re.IGNORECASE)),
            "mentions_decline": bool(re.search(r'\bdecline\b', text, re.IGNORECASE)),
            "has_price_target": bool(re.search(r'price target|target price', text, re.IGNORECASE)),
            "has_rating_change": bool(re.search(r'upgrade|downgrade|rating', text, re.IGNORECASE)),
            "mentions_volatility": bool(re.search(r'\bvolatility\b', text, re.IGNORECASE)),
            "mentions_volume": bool(re.search(r'\bvolume\b', text, re.IGNORECASE))
        }
        
        # Extract numerical indicators
        percentages = re.findall(r'(\d+(?:\.\d+)?)%', text)
        if percentages:
            indicators["percentages"] = [float(p) for p in percentages]
        
        prices = re.findall(r'\$(\d+(?:\.\d{2})?)', text)
        if prices:
            indicators["prices"] = [float(p) for p in prices]
        
        return indicators
    
    def _extract_key_phrases(self, text: str) -> List[str]:
        """Extract key financial phrases from text"""
        # Simple keyword extraction based on financial terms
        financial_keywords = [
            "earnings beat", "earnings miss", "revenue growth", "margin expansion",
            "cost cutting", "market share", "competitive advantage", "regulatory approval",
            "merger", "acquisition", "dividend increase", "share buyback",
            "guidance raised", "guidance lowered", "analyst upgrade", "analyst downgrade"
        ]
        
        key_phrases = []
        text_lower = text.lower()
        
        for phrase in financial_keywords:
            if phrase in text_lower:
                key_phrases.append(phrase)
        
        return key_phrases[:10]  # Limit to top 10


class FinancialDocumentClassifier:
    """
    Classifier for financial document types and categories
    """
    
    def __init__(self, model_name: str = "distilbert-base-uncased"):
        """
        Initialize document classifier
        
        Args:
            model_name: Base model for classification
        """
        self.model_name = model_name
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Initialize components
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.vectorizer = TfidfVectorizer(max_features=5000, stop_words='english')
        self.category_keywords = self._load_category_keywords()
        
        logger.info("Financial document classifier initialized")
    
    def _load_category_keywords(self) -> Dict[FinancialCategory, List[str]]:
        """Load keywords for each document category"""
        # Load from external JSON file
        financial_data_path = Path(__file__).parent.parent / "config" / "financial_nlp_data.json"
        if financial_data_path.exists():
            try:
                with open(financial_data_path, 'r') as f:
                    financial_data = json.load(f)
                    # Convert list of strings to dictionary with Enum keys
                    category_keywords = {}
                    for category_str, keywords in financial_data.get("document_categories", {}).items():
                        try:
                            category_keywords[FinancialCategory[category_str.upper()]] = keywords
                        except KeyError:
                            logger.warning(f"Unknown FinancialCategory: {category_str}")
                    return category_keywords
            except Exception as e:
                logger.warning(f"Failed to load document categories from {financial_data_path}: {e}")
        
        # Fallback to hardcoded if file not found or error
        return {
            FinancialCategory.EARNINGS_REPORT: [
                "earnings", "quarterly", "revenue", "eps", "guidance", "conference call",
                "financial results", "income statement", "balance sheet"
            ],
            FinancialCategory.NEWS_ARTICLE: [
                "breaking", "news", "reported", "announced", "sources", "according to",
                "market news", "business news", "financial news"
            ],
            FinancialCategory.ANALYST_REPORT: [
                "analyst", "research", "rating", "price target", "recommendation",
                "buy", "sell", "hold", "upgrade", "downgrade", "coverage"
            ],
            FinancialCategory.SEC_FILING: [
                "sec", "filing", "10-k", "10-q", "8-k", "proxy", "form",
                "securities", "commission", "edgar"
            ],
            FinancialCategory.PRESS_RELEASE: [
                "press release", "announces", "company", "today announced",
                "business wire", "pr newswire", "corporate news"
            ],
            FinancialCategory.RESEARCH_NOTE: [
                "research", "note", "analysis", "outlook", "thesis", "investment",
                "fundamental", "technical", "valuation"
            ],
            FinancialCategory.MARKET_COMMENTARY: [
                "market", "commentary", "outlook", "trends", "sector", "industry",
                "economic", "macro", "market update"
            ],
            FinancialCategory.ECONOMIC_DATA: [
                "economic", "data", "gdp", "inflation", "unemployment", "fed",
                "central bank", "monetary policy", "economic indicators"
            ]
        }
    
    def classify_document(
        self,
        text: str,
        title: str = "",
        metadata: Dict[str, Any] = None
    ) -> DocumentClassificationResult:
        """
        Classify financial document
        
        Args:
            text: Document text
            title: Document title (optional)
            metadata: Additional metadata (optional)
            
        Returns:
            DocumentClassificationResult with classification
        """
        start_time = datetime.now()
        
        try:
            # Combine text and title for analysis
            full_text = f"{title} {text}".strip()
            
            # Calculate category scores using keyword matching
            category_scores = {}
            
            for category, keywords in self.category_keywords.items():
                score = 0
                text_lower = full_text.lower()
                
                for keyword in keywords:
                    if keyword in text_lower:
                        score += 1
                
                # Normalize score
                category_scores[category.value] = score / len(keywords)
            
            # Get best category
            best_category_name = max(category_scores.items(), key=lambda x: x[1])[0]
            best_category = FinancialCategory(best_category_name)
            confidence = category_scores[best_category_name]
            
            # Extract topics using simple keyword extraction
            topics = self._extract_topics(full_text)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return DocumentClassificationResult(
                text=text,
                model_type=FinancialModelType.NEWS_CATEGORIZER,
                confidence=confidence,
                processing_time=processing_time,
                category=best_category,
                category_scores=category_scores,
                topics=topics,
                metadata={
                    "title": title,
                    "text_length": len(text),
                    "has_title": bool(title),
                    "additional_metadata": metadata or {}
                }
            )
            
        except Exception as e:
            logger.error(f"Error in document classification: {e}")
            processing_time = (datetime.now() - start_time).total_seconds()
            return DocumentClassificationResult(
                text=text,
                model_type=FinancialModelType.NEWS_CATEGORIZER,
                confidence=0.0,
                processing_time=processing_time,
                category=FinancialCategory.NEWS_ARTICLE,  # Default
                metadata={"error": str(e)}
            )
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract topics from text using keyword analysis"""
        # Define topic keywords
        topic_keywords = {
            "technology": ["tech", "software", "ai", "cloud", "digital", "innovation"],
            "healthcare": ["health", "pharma", "biotech", "medical", "drug", "clinical"],
            "finance": ["bank", "financial", "credit", "loan", "insurance", "fintech"],
            "energy": ["oil", "gas", "renewable", "solar", "wind", "energy"],
            "retail": ["retail", "consumer", "shopping", "e-commerce", "sales"],
            "real_estate": ["real estate", "property", "housing", "reit", "construction"],
            "automotive": ["auto", "car", "vehicle", "electric", "tesla", "ford"],
            "aerospace": ["aerospace", "airline", "aviation", "boeing", "defense"]
        }
        
        topics = []
        text_lower = text.lower()
        
        for topic, keywords in topic_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                topics.append(topic)
        
        return topics[:5]  # Limit to top 5 topics


class FinancialRiskAssessor:
    """
    Risk assessment model for financial texts
    """
    
    def __init__(self):
        """Initialize risk assessor"""
        self.risk_keywords = self._load_risk_keywords()
        self.risk_patterns = self._compile_risk_patterns()
        
        logger.info("Financial risk assessor initialized")
    
    def _load_risk_keywords(self) -> Dict[RiskLevel, List[str]]:
        """Load risk keywords by level"""
        # Load from external JSON file
        financial_data_path = Path(__file__).parent.parent / "config" / "financial_nlp_data.json"
        if financial_data_path.exists():
            try:
                with open(financial_data_path, 'r') as f:
                    financial_data = json.load(f)
                    # Convert list of strings to dictionary with Enum keys
                    risk_keywords = {}
                    for risk_str, keywords in financial_data.get("risk_levels", {}).items():
                        try:
                            risk_keywords[RiskLevel[risk_str.upper()]] = keywords
                        except KeyError:
                            logger.warning(f"Unknown RiskLevel: {risk_str}")
                    return risk_keywords
            except Exception as e:
                logger.warning(f"Failed to load risk levels from {financial_data_path}: {e}")
        
        # Fallback to hardcoded if file not found or error
        return {
            RiskLevel.LOW: [
                "stable", "consistent", "reliable", "predictable", "steady",
                "conservative", "safe", "secure", "established"
            ],
            RiskLevel.MEDIUM: [
                "moderate", "balanced", "cautious", "measured", "reasonable",
                "standard", "typical", "normal", "average"
            ],
            RiskLevel.HIGH: [
                "volatile", "uncertain", "risky", "speculative", "aggressive",
                "challenging", "difficult", "concerning", "warning"
            ],
            RiskLevel.CRITICAL: [
                "crisis", "emergency", "critical", "severe", "dangerous",
                "catastrophic", "collapse", "failure", "bankruptcy", "default"
            ]
        }
    
    def _compile_risk_patterns(self) -> List[Tuple[str, RiskLevel, str]]:
        """Compile regex patterns for risk detection"""
        patterns = [
            (r'bankruptcy|insolvency|chapter 11', RiskLevel.CRITICAL, "Bankruptcy risk"),
            (r'default|missed payment|payment failure', RiskLevel.CRITICAL, "Default risk"),
            (r'investigation|fraud|scandal', RiskLevel.HIGH, "Legal/compliance risk"),
            (r'regulatory|compliance|violation', RiskLevel.HIGH, "Regulatory risk"),
            (r'lawsuit|litigation|legal action', RiskLevel.HIGH, "Legal risk"),
            (r'cyber.?attack|data breach|security', RiskLevel.HIGH, "Cybersecurity risk"),
            (r'market crash|recession|downturn', RiskLevel.HIGH, "Market risk"),
            (r'volatility|fluctuation|instability', RiskLevel.MEDIUM, "Volatility risk"),
            (r'competition|competitive pressure', RiskLevel.MEDIUM, "Competitive risk"),
            (r'supply chain|disruption|shortage', RiskLevel.MEDIUM, "Operational risk")
        ]
        
        return [(re.compile(pattern, re.IGNORECASE), level, desc) 
                for pattern, level, desc in patterns]
    
    def assess_risk(self, text: str) -> RiskAssessmentResult:
        """
        Assess risk level of financial text
        
        Args:
            text: Text to analyze for risk
            
        Returns:
            RiskAssessmentResult with risk assessment
        """
        start_time = datetime.now()
        
        try:
            # Calculate risk scores
            risk_scores = {level.value: 0 for level in RiskLevel}
            risk_factors = []
            
            # Keyword-based scoring
            text_lower = text.lower()
            for level, keywords in self.risk_keywords.items():
                for keyword in keywords:
                    if keyword in text_lower:
                        risk_scores[level.value] += 1
            
            # Pattern-based scoring
            for pattern, level, description in self.risk_patterns:
                if pattern.search(text):
                    risk_scores[level.value] += 2  # Patterns have higher weight
                    risk_factors.append(description)
            
            # Normalize scores
            total_words = len(text.split())
            for level in risk_scores:
                risk_scores[level] = risk_scores[level] / max(total_words / 100, 1)
            
            # Determine overall risk level
            if risk_scores[RiskLevel.CRITICAL.value] > 0.1:
                overall_risk = RiskLevel.CRITICAL
                confidence = min(0.9, risk_scores[RiskLevel.CRITICAL.value])
            elif risk_scores[RiskLevel.HIGH.value] > 0.05:
                overall_risk = RiskLevel.HIGH
                confidence = min(0.8, risk_scores[RiskLevel.HIGH.value] * 2)
            elif risk_scores[RiskLevel.MEDIUM.value] > 0.02:
                overall_risk = RiskLevel.MEDIUM
                confidence = min(0.7, risk_scores[RiskLevel.MEDIUM.value] * 5)
            else:
                overall_risk = RiskLevel.LOW
                confidence = 0.6
            
            # Generate mitigation suggestions
            mitigation_suggestions = self._generate_mitigation_suggestions(
                overall_risk, risk_factors
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return RiskAssessmentResult(
                text=text,
                model_type=FinancialModelType.RISK_CLASSIFIER,
                confidence=confidence,
                processing_time=processing_time,
                risk_level=overall_risk,
                risk_factors=risk_factors,
                risk_scores=risk_scores,
                mitigation_suggestions=mitigation_suggestions,
                metadata={
                    "text_length": len(text),
                    "total_risk_factors": len(risk_factors),
                    "word_count": total_words
                }
            )
            
        except Exception as e:
            logger.error(f"Error in risk assessment: {e}")
            processing_time = (datetime.now() - start_time).total_seconds()
            return RiskAssessmentResult(
                text=text,
                model_type=FinancialModelType.RISK_CLASSIFIER,
                confidence=0.0,
                processing_time=processing_time,
                risk_level=RiskLevel.MEDIUM,  # Default to medium
                metadata={"error": str(e)}
            )
    
    def _generate_mitigation_suggestions(
        self,
        risk_level: RiskLevel,
        risk_factors: List[str]
    ) -> List[str]:
        """Generate risk mitigation suggestions"""
        suggestions = []
        
        if risk_level == RiskLevel.CRITICAL:
            suggestions.extend([
                "Immediate action required - consider emergency protocols",
                "Consult with legal and compliance teams",
                "Review and update risk management procedures",
                "Consider position reduction or hedging strategies"
            ])
        elif risk_level == RiskLevel.HIGH:
            suggestions.extend([
                "Increase monitoring frequency",
                "Review risk exposure limits",
                "Consider diversification strategies",
                "Update stakeholder communications"
            ])
        elif risk_level == RiskLevel.MEDIUM:
            suggestions.extend([
                "Maintain regular monitoring",
                "Review risk tolerance levels",
                "Consider preventive measures"
            ])
        else:  # LOW
            suggestions.extend([
                "Continue standard monitoring procedures",
                "Maintain current risk management practices"
            ])
        
        # Add specific suggestions based on risk factors
        if "Legal/compliance risk" in risk_factors:
            suggestions.append("Engage legal counsel for compliance review")
        if "Cybersecurity risk" in risk_factors:
            suggestions.append("Enhance cybersecurity measures and monitoring")
        if "Market risk" in risk_factors:
            suggestions.append("Consider market hedging strategies")
        
        return suggestions[:5]  # Limit to 5 suggestions


class FinancialNLPModels:
    """
    Main class that orchestrates all financial NLP models
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize financial NLP models
        
        Args:
            config_path: Path to configuration file
        """
        self.config = self._load_config(config_path)
        self.models = {}
        
        # Initialize components
        self._initialize_models()
        
        logger.info("Financial NLP Models initialized")
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load configuration"""
        default_config = {
            "models": {
                "finbert": {
                    "enabled": True,
                    "model_name": "ProsusAI/finbert",
                    "cache_dir": "./models/finbert"
                },
                "document_classifier": {
                    "enabled": True,
                    "model_name": "distilbert-base-uncased"
                },
                "risk_assessor": {
                    "enabled": True
                }
            },
            "tokenizer": {
                "base_model": "bert-base-uncased",
                "add_financial_vocab": True
            },
            "processing": {
                "batch_size": 16,
                "max_length": 512,
                "truncation": True
            }
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")
        
        return default_config
    
    def _initialize_models(self):
        """Initialize all financial NLP models"""
        try:
            # Initialize FinBERT if enabled
            if self.config["models"]["finbert"]["enabled"]:
                self.models["finbert"] = FinBERTModel(
                    model_name=self.config["models"]["finbert"]["model_name"],
                    cache_dir=self.config["models"]["finbert"]["cache_dir"]
                )
            
            # Initialize document classifier if enabled
            if self.config["models"]["document_classifier"]["enabled"]:
                self.models["document_classifier"] = FinancialDocumentClassifier(
                    model_name=self.config["models"]["document_classifier"]["model_name"]
                )
            
            # Initialize risk assessor if enabled
            if self.config["models"]["risk_assessor"]["enabled"]:
                self.models["risk_assessor"] = FinancialRiskAssessor()
            
            # Initialize financial tokenizer
            self.tokenizer = FinancialTokenizer(
                base_tokenizer_name=self.config["tokenizer"]["base_model"]
            )
            
            logger.info(f"Initialized {len(self.models)} financial NLP models")
            
        except Exception as e:
            logger.error(f"Error initializing financial NLP models: {e}")
            raise
    
    def analyze_financial_sentiment(
        self,
        text: str,
        model_type: str = "finbert"
    ) -> FinancialSentimentResult:
        """
        Analyze financial sentiment using specified model
        
        Args:
            text: Text to analyze
            model_type: Model to use ("finbert")
            
        Returns:
            FinancialSentimentResult with sentiment analysis
        """
        if model_type not in self.models:
            raise ValueError(f"Model {model_type} not available")
        
        model = self.models[model_type]
        
        if hasattr(model, 'analyze_sentiment'):
            return model.analyze_sentiment(text)
        else:
            raise ValueError(f"Model {model_type} does not support sentiment analysis")
    
    def classify_document(
        self,
        text: str,
        title: str = "",
        metadata: Dict[str, Any] = None
    ) -> DocumentClassificationResult:
        """
        Classify financial document
        
        Args:
            text: Document text
            title: Document title
            metadata: Additional metadata
            
        Returns:
            DocumentClassificationResult with classification
        """
        if "document_classifier" not in self.models:
            raise ValueError("Document classifier not available")
        
        return self.models["document_classifier"].classify_document(text, title, metadata)
    
    def assess_risk(self, text: str) -> RiskAssessmentResult:
        """
        Assess risk level of financial text
        
        Args:
            text: Text to analyze
            
        Returns:
            RiskAssessmentResult with risk assessment
        """
        if "risk_assessor" not in self.models:
            raise ValueError("Risk assessor not available")
        
        return self.models["risk_assessor"].assess_risk(text)
    
    def comprehensive_analysis(
        self,
        text: str,
        title: str = "",
        include_sentiment: bool = True,
        include_classification: bool = True,
        include_risk: bool = True
    ) -> Dict[str, Any]:
        """
        Perform comprehensive financial text analysis
        
        Args:
            text: Text to analyze
            title: Document title
            include_sentiment: Whether to include sentiment analysis
            include_classification: Whether to include document classification
            include_risk: Whether to include risk assessment
            
        Returns:
            Dictionary with all analysis results
        """
        results = {
            "text": text,
            "title": title,
            "analysis_timestamp": datetime.now().isoformat(),
            "results": {}
        }
        
        try:
            # Sentiment analysis
            if include_sentiment and "finbert" in self.models:
                sentiment_result = self.analyze_financial_sentiment(text)
                results["results"]["sentiment"] = {
                    "sentiment": sentiment_result.sentiment.value,
                    "confidence": sentiment_result.confidence,
                    "sentiment_scores": sentiment_result.sentiment_scores,
                    "market_indicators": sentiment_result.market_indicators,
                    "key_phrases": sentiment_result.key_phrases
                }
            
            # Document classification
            if include_classification and "document_classifier" in self.models:
                classification_result = self.classify_document(text, title)
                results["results"]["classification"] = {
                    "category": classification_result.category.value,
                    "confidence": classification_result.confidence,
                    "category_scores": classification_result.category_scores,
                    "topics": classification_result.topics
                }
            
            # Risk assessment
            if include_risk and "risk_assessor" in self.models:
                risk_result = self.assess_risk(text)
                results["results"]["risk"] = {
                    "risk_level": risk_result.risk_level.value,
                    "confidence": risk_result.confidence,
                    "risk_factors": risk_result.risk_factors,
                    "risk_scores": risk_result.risk_scores,
                    "mitigation_suggestions": risk_result.mitigation_suggestions
                }
            
            # Summary
            results["summary"] = self._create_analysis_summary(results["results"])
            
        except Exception as e:
            logger.error(f"Error in comprehensive analysis: {e}")
            results["error"] = str(e)
        
        return results
    
    def _create_analysis_summary(self, analysis_results: Dict[str, Any]) -> str:
        """Create a human-readable summary of analysis results"""
        summary_parts = []
        
        # Sentiment summary
        if "sentiment" in analysis_results:
            sentiment_data = analysis_results["sentiment"]
            sentiment = sentiment_data["sentiment"]
            confidence = sentiment_data["confidence"]
            summary_parts.append(f"Sentiment: {sentiment} (confidence: {confidence:.2f})")
        
        # Classification summary
        if "classification" in analysis_results:
            classification_data = analysis_results["classification"]
            category = classification_data["category"]
            confidence = classification_data["confidence"]
            summary_parts.append(f"Document type: {category} (confidence: {confidence:.2f})")
        
        # Risk summary
        if "risk" in analysis_results:
            risk_data = analysis_results["risk"]
            risk_level = risk_data["risk_level"]
            confidence = risk_data["confidence"]
            summary_parts.append(f"Risk level: {risk_level} (confidence: {confidence:.2f})")
        
        return ". ".join(summary_parts) if summary_parts else "No analysis results available"
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded models"""
        return {
            "available_models": list(self.models.keys()),
            "model_details": {
                name: {
                    "type": type(model).__name__,
                    "loaded": True
                }
                for name, model in self.models.items()
            },
            "tokenizer": {
                "type": type(self.tokenizer).__name__,
                "base_model": self.config["tokenizer"]["base_model"]
            },
            "config": self.config
        }
    
    def batch_analyze(
        self,
        texts: List[str],
        analysis_type: str = "comprehensive",
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Batch analyze multiple texts
        
        Args:
            texts: List of texts to analyze
            analysis_type: Type of analysis ("sentiment", "classification", "risk", "comprehensive")
            **kwargs: Additional arguments for analysis
            
        Returns:
            List of analysis results
        """
        results = []
        
        for text in texts:
            try:
                if analysis_type == "sentiment":
                    result = self.analyze_financial_sentiment(text, **kwargs)
                    results.append({
                        "text": text,
                        "sentiment": result.sentiment.value,
                        "confidence": result.confidence,
                        "processing_time": result.processing_time
                    })
                
                elif analysis_type == "classification":
                    result = self.classify_document(text, **kwargs)
                    results.append({
                        "text": text,
                        "category": result.category.value,
                        "confidence": result.confidence,
                        "processing_time": result.processing_time
                    })
                
                elif analysis_type == "risk":
                    result = self.assess_risk(text)
                    results.append({
                        "text": text,
                        "risk_level": result.risk_level.value,
                        "confidence": result.confidence,
                        "processing_time": result.processing_time
                    })
                
                elif analysis_type == "comprehensive":
                    result = self.comprehensive_analysis(text, **kwargs)
                    results.append(result)
                
                else:
                    raise ValueError(f"Unsupported analysis type: {analysis_type}")
                    
            except Exception as e:
                logger.error(f"Error analyzing text: {e}")
                results.append({
                    "text": text,
                    "error": str(e)
                })
        
        return results


# Factory function for easy initialization
def create_financial_nlp_models(config_path: Optional[str] = None) -> FinancialNLPModels:
    """
    Factory function to create and initialize financial NLP models
    
    Args:
        config_path: Optional path to configuration file
        
    Returns:
        Initialized FinancialNLPModels instance
    """
    return FinancialNLPModels(config_path)


# Utility functions for common tasks
def quick_sentiment_analysis(text: str) -> Dict[str, Any]:
    """
    Quick sentiment analysis using FinBERT
    
    Args:
        text: Text to analyze
        
    Returns:
        Dictionary with sentiment analysis results
    """
    try:
        models = FinancialNLPModels()
        result = models.analyze_financial_sentiment(text)
        
        return {
            "sentiment": result.sentiment.value,
            "confidence": result.confidence,
            "sentiment_scores": result.sentiment_scores,
            "market_indicators": result.market_indicators,
            "processing_time": result.processing_time
        }
    except Exception as e:
        logger.error(f"Error in quick sentiment analysis: {e}")
        return {"error": str(e)}


def quick_document_classification(text: str, title: str = "") -> Dict[str, Any]:
    """
    Quick document classification
    
    Args:
        text: Text to classify
        title: Document title
        
    Returns:
        Dictionary with classification results
    """
    try:
        models = FinancialNLPModels()
        result = models.classify_document(text, title)
        
        return {
            "category": result.category.value,
            "confidence": result.confidence,
            "category_scores": result.category_scores,
            "topics": result.topics,
            "processing_time": result.processing_time
        }
    except Exception as e:
        logger.error(f"Error in quick document classification: {e}")
        return {"error": str(e)}


def quick_risk_assessment(text: str) -> Dict[str, Any]:
    """
    Quick risk assessment
    
    Args:
        text: Text to assess
        
    Returns:
        Dictionary with risk assessment results
    """
    try:
        models = FinancialNLPModels()
        result = models.assess_risk(text)
        
        return {
            "risk_level": result.risk_level.value,
            "confidence": result.confidence,
            "risk_factors": result.risk_factors,
            "risk_scores": result.risk_scores,
            "mitigation_suggestions": result.mitigation_suggestions,
            "processing_time": result.processing_time
        }
    except Exception as e:
        logger.error(f"Error in quick risk assessment: {e}")
        return {"error": str(e)}


# Export main classes and functions
__all__ = [
    "FinancialNLPModels",
    "FinBERTModel",
    "FinancialDocumentClassifier",
    "FinancialRiskAssessor",
    "FinancialTokenizer",
    "FinancialAnalysisResult",
    "FinancialSentimentResult",
    "DocumentClassificationResult",
    "RiskAssessmentResult",
    "EntityRelationResult",
    "FinancialModelType",
    "FinancialSentiment",
    "FinancialCategory",
    "RiskLevel",
    "create_financial_nlp_models",
    "quick_sentiment_analysis",
    "quick_document_classification",
    "quick_risk_assessment"
]