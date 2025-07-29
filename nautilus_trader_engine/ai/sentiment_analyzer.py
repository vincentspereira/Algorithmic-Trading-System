"""
AI-Powered Sentiment Analysis Pipeline
Ultra-advanced real-time market sentiment analysis from multiple sources
with ML integration, real-time processing, and predictive capabilities
"""

import asyncio
import re
import time
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
import logging
import json
import hashlib
from datetime import datetime, timedelta

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

# Import enhanced components
from .inference_engine import InferenceEngine, InferenceRequest, InferencePriority
from .model_manager import ModelManager
from ..core.messaging.message_bus import MessageBus
from ..core.caching.cache_manager import CacheManager


class SentimentPolarity(Enum):
    """Sentiment polarity levels"""
    VERY_POSITIVE = 1.0
    POSITIVE = 0.5
    NEUTRAL = 0.0
    NEGATIVE = -0.5
    VERY_NEGATIVE = -1.0


class SentimentSource(Enum):
    """Enhanced sources of sentiment data"""
    # Traditional sources
    NEWS = "news"
    SOCIAL_MEDIA = "social_media"
    ANALYST_REPORTS = "analyst_reports"
    EARNINGS_CALLS = "earnings_calls"
    MARKET_DATA = "market_data"
    REGULATORY_FILINGS = "regulatory_filings"
    
    # Enhanced sources
    REDDIT = "reddit"
    TWITTER = "twitter"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    YOUTUBE = "youtube"
    PODCASTS = "podcasts"
    BLOGS = "blogs"
    FORUMS = "forums"
    
    # Professional sources
    BLOOMBERG = "bloomberg"
    REUTERS = "reuters"
    CNBC = "cnbc"
    SEEKING_ALPHA = "seeking_alpha"
    MOTLEY_FOOL = "motley_fool"
    
    # Alternative data
    SATELLITE_DATA = "satellite_data"
    PATENT_FILINGS = "patent_filings"
    JOB_POSTINGS = "job_postings"
    EXECUTIVE_MOVES = "executive_moves"
    
    # Real-time sources
    LIVE_STREAMS = "live_streams"
    CHAT_ROOMS = "chat_rooms"
    TRADING_SIGNALS = "trading_signals"
    
    # Aggregated sources
    MULTI_SOURCE = "multi_source"
    CONSENSUS = "consensus"


@dataclass
class SentimentScore:
    """Enhanced sentiment analysis result with advanced metrics"""
    source: SentimentSource
    symbol: Optional[str]
    polarity: float  # -1.0 to 1.0
    confidence: float  # 0.0 to 1.0
    magnitude: float  # 0.0 to 1.0 (strength of sentiment)
    
    # Content metadata
    content_id: Optional[str] = None
    content_snippet: Optional[str] = None
    author: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    
    # Analysis details
    keywords: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    
    # Enhanced sentiment metrics
    emotion_scores: Dict[str, float] = field(default_factory=dict)  # joy, fear, anger, etc.
    subjectivity: float = 0.5  # 0.0 (objective) to 1.0 (subjective)
    urgency: float = 0.0  # 0.0 to 1.0 (how urgent/time-sensitive)
    credibility: float = 0.5  # 0.0 to 1.0 (source credibility)
    
    # Market impact metrics
    market_relevance: float = 0.5  # 0.0 to 1.0 (relevance to market)
    price_impact_prediction: Optional[float] = None  # Predicted price impact
    volatility_impact: Optional[float] = None  # Predicted volatility impact
    
    # Social metrics (for social media sources)
    engagement_score: float = 0.0  # likes, shares, comments
    reach: int = 0  # potential audience size
    influence_score: float = 0.0  # author influence
    viral_potential: float = 0.0  # likelihood to go viral
    
    # ML-specific metrics
    ml_confidence: Optional[float] = None
    model_version: Optional[str] = None
    feature_importance: Dict[str, float] = field(default_factory=dict)
    
    # Processing metadata
    processing_time_ms: float = 0.0
    cache_hit: bool = False
    
    # Aggregation metadata
    sample_size: int = 1
    time_window_minutes: Optional[int] = None
    constituent_scores: List[str] = field(default_factory=list)  # IDs of constituent scores
    
    # Validation and quality
    quality_score: float = 0.5  # Overall quality of the sentiment analysis
    anomaly_score: float = 0.0  # How anomalous this sentiment is
    
    # Temporal context
    trend_direction: str = "neutral"  # "positive", "negative", "neutral"
    momentum: float = 0.0  # Rate of sentiment change
    
    # Risk metrics
    controversy_score: float = 0.0  # How controversial the content is
    misinformation_risk: float = 0.0  # Risk of misinformation
    
    @property
    def sentiment_label(self) -> str:
        """Get human-readable sentiment label"""
        if self.polarity >= 0.7:
            return "Very Positive"
        elif self.polarity >= 0.3:
            return "Positive"
        elif self.polarity >= -0.3:
            return "Neutral"
        elif self.polarity >= -0.7:
            return "Negative"
        else:
            return "Very Negative"
    
    @property
    def is_significant(self) -> bool:
        """Check if sentiment is statistically significant"""
        return self.confidence >= 0.6 and self.magnitude >= 0.4
    
    @property
    def is_actionable(self) -> bool:
        """Check if sentiment is actionable for trading"""
        return (self.is_significant and 
                self.market_relevance >= 0.6 and
                self.credibility >= 0.5 and
                self.quality_score >= 0.6)
    
    @property
    def risk_adjusted_score(self) -> float:
        """Get risk-adjusted sentiment score"""
        risk_penalty = (self.controversy_score + self.misinformation_risk) / 2
        return self.polarity * self.confidence * (1 - risk_penalty)
    
    def get_overall_score(self) -> float:
        """Calculate comprehensive sentiment score"""
        base_score = self.polarity * self.confidence * self.magnitude
        
        # Apply quality adjustments
        quality_multiplier = (self.quality_score + self.credibility) / 2
        
        # Apply market relevance
        relevance_multiplier = self.market_relevance
        
        # Apply risk penalty
        risk_penalty = (self.controversy_score + self.misinformation_risk) / 2
        
        final_score = base_score * quality_multiplier * relevance_multiplier * (1 - risk_penalty)
        
        return max(-1.0, min(1.0, final_score))
    
    def get_dominant_emotion(self) -> Tuple[str, float]:
        """Get the dominant emotion and its score"""
        if not self.emotion_scores:
            return "neutral", 0.0
        
        dominant_emotion = max(self.emotion_scores.items(), key=lambda x: x[1])
        return dominant_emotion
    
    def is_trending(self) -> bool:
        """Check if this sentiment indicates a trending topic"""
        return (self.viral_potential >= 0.7 or 
                self.engagement_score >= 0.8 or
                self.urgency >= 0.7)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'source': self.source.value,
            'symbol': self.symbol,
            'polarity': self.polarity,
            'confidence': self.confidence,
            'magnitude': self.magnitude,
            'timestamp': self.timestamp,
            'sentiment_label': self.sentiment_label,
            'is_significant': self.is_significant,
            'is_actionable': self.is_actionable,
            'overall_score': self.get_overall_score(),
            'risk_adjusted_score': self.risk_adjusted_score,
            'dominant_emotion': self.get_dominant_emotion(),
            'is_trending': self.is_trending(),
            'keywords': self.keywords,
            'entities': self.entities,
            'topics': self.topics,
            'emotion_scores': self.emotion_scores,
            'market_relevance': self.market_relevance,
            'credibility': self.credibility,
            'quality_score': self.quality_score,
            'processing_time_ms': self.processing_time_ms
        }


class SentimentAnalyzer(ABC):
    """Abstract base class for sentiment analyzers"""
    
    @abstractmethod
    async def analyze_text(self, text: str, symbol: Optional[str] = None) -> SentimentScore:
        """Analyze sentiment of text content"""
        pass
    
    @abstractmethod
    async def analyze_batch(self, texts: List[str], symbol: Optional[str] = None) -> List[SentimentScore]:
        """Analyze sentiment of multiple texts"""
        pass


class RuleBasedSentimentAnalyzer(SentimentAnalyzer):
    """Rule-based sentiment analyzer using lexicons and patterns"""
    
    def __init__(self):
        self.positive_words = self._load_positive_lexicon()
        self.negative_words = self._load_negative_lexicon()
        self.financial_terms = self._load_financial_terms()
        self.intensifiers = self._load_intensifiers()
        self.negations = {'not', 'no', 'never', 'none', 'nobody', 'nothing', 'neither', 'nowhere', 'hardly'}
        
        self.logger = logging.getLogger(__name__)
    
    def _load_positive_lexicon(self) -> Dict[str, float]:
        """Load positive sentiment words with weights"""
        return {
            # Strong positive
            'excellent': 1.0, 'outstanding': 1.0, 'exceptional': 1.0, 'superb': 1.0,
            'amazing': 0.9, 'fantastic': 0.9, 'wonderful': 0.9, 'brilliant': 0.9,
            
            # Moderate positive
            'good': 0.6, 'positive': 0.6, 'strong': 0.6, 'solid': 0.6,
            'improved': 0.5, 'better': 0.5, 'growth': 0.5, 'gain': 0.5,
            
            # Financial positive
            'profit': 0.7, 'revenue': 0.4, 'earnings': 0.4, 'dividend': 0.6,
            'upgrade': 0.8, 'outperform': 0.8, 'buy': 0.7, 'bullish': 0.8,
            'rally': 0.7, 'surge': 0.8, 'soar': 0.9, 'boom': 0.8
        }
    
    def _load_negative_lexicon(self) -> Dict[str, float]:
        """Load negative sentiment words with weights"""
        return {
            # Strong negative
            'terrible': -1.0, 'awful': -1.0, 'horrible': -1.0, 'disaster': -1.0,
            'catastrophic': -1.0, 'devastating': -1.0, 'collapse': -0.9,
            
            # Moderate negative
            'bad': -0.6, 'negative': -0.6, 'weak': -0.6, 'poor': -0.6,
            'decline': -0.5, 'worse': -0.5, 'loss': -0.6, 'drop': -0.5,
            
            # Financial negative
            'deficit': -0.7, 'debt': -0.5, 'bankruptcy': -1.0, 'default': -0.9,
            'downgrade': -0.8, 'underperform': -0.8, 'sell': -0.7, 'bearish': -0.8,
            'crash': -0.9, 'plunge': -0.8, 'tumble': -0.7, 'recession': -0.8
        }
    
    def _load_financial_terms(self) -> Dict[str, float]:
        """Load financial-specific terms"""
        return {
            'merger': 0.3, 'acquisition': 0.3, 'ipo': 0.2, 'spinoff': 0.1,
            'restructuring': -0.2, 'layoffs': -0.6, 'cost-cutting': -0.3,
            'expansion': 0.5, 'partnership': 0.4, 'innovation': 0.6
        }
    
    def _load_intensifiers(self) -> Dict[str, float]:
        """Load intensity modifiers"""
        return {
            'very': 1.5, 'extremely': 2.0, 'incredibly': 2.0, 'highly': 1.3,
            'quite': 1.2, 'rather': 1.1, 'somewhat': 0.8, 'slightly': 0.7
        }
    
    async def analyze_text(self, text: str, symbol: Optional[str] = None) -> SentimentScore:
        """Analyze sentiment of single text"""
        try:
            # Preprocess text
            processed_text = self._preprocess_text(text)
            words = processed_text.split()
            
            # Calculate sentiment scores
            sentiment_score = 0.0
            word_count = 0
            matched_words = []
            
            # Process words with context
            for i, word in enumerate(words):
                word_lower = word.lower()
                
                # Check for negation in previous words
                negation_multiplier = self._check_negation(words, i)
                
                # Check for intensifiers in previous words
                intensity_multiplier = self._check_intensifier(words, i)
                
                # Calculate word sentiment
                word_sentiment = 0.0
                
                if word_lower in self.positive_words:
                    word_sentiment = self.positive_words[word_lower]
                    matched_words.append(f"+{word}")
                elif word_lower in self.negative_words:
                    word_sentiment = self.negative_words[word_lower]
                    matched_words.append(f"-{word}")
                elif word_lower in self.financial_terms:
                    word_sentiment = self.financial_terms[word_lower]
                    matched_words.append(f"${word}")
                
                if word_sentiment != 0.0:
                    # Apply modifiers
                    word_sentiment *= negation_multiplier * intensity_multiplier
                    sentiment_score += word_sentiment
                    word_count += 1
            
            # Normalize sentiment score
            if word_count > 0:
                normalized_score = sentiment_score / word_count
                # Clamp to [-1, 1] range
                normalized_score = max(-1.0, min(1.0, normalized_score))
            else:
                normalized_score = 0.0
            
            # Calculate confidence based on word count and clarity
            confidence = min(1.0, word_count / 10.0)  # More words = higher confidence
            if abs(normalized_score) > 0.5:
                confidence *= 1.2  # Clear sentiment increases confidence
            
            # Calculate magnitude (absolute strength)
            magnitude = abs(normalized_score)
            
            # Extract entities and keywords
            entities = self._extract_entities(text, symbol)
            keywords = matched_words[:10]  # Top 10 matched words
            
            return SentimentScore(
                source=SentimentSource.NEWS,  # Default, can be overridden
                symbol=symbol,
                polarity=normalized_score,
                confidence=min(1.0, confidence),
                magnitude=magnitude,
                content_snippet=text[:200] + "..." if len(text) > 200 else text,
                keywords=keywords,
                entities=entities
            )
        
        except Exception as e:
            self.logger.error(f"Error analyzing text sentiment: {e}")
            return SentimentScore(
                source=SentimentSource.NEWS,
                symbol=symbol,
                polarity=0.0,
                confidence=0.0,
                magnitude=0.0
            )
    
    async def analyze_batch(self, texts: List[str], symbol: Optional[str] = None) -> List[SentimentScore]:
        """Analyze sentiment of multiple texts"""
        results = []
        
        for text in texts:
            sentiment = await self.analyze_text(text, symbol)
            results.append(sentiment)
        
        return results
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for analysis"""
        # Convert to lowercase
        text = text.lower()
        
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove special characters but keep spaces
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text
    
    def _check_negation(self, words: List[str], current_index: int) -> float:
        """Check for negation in previous 3 words"""
        start_index = max(0, current_index - 3)
        
        for i in range(start_index, current_index):
            if words[i].lower() in self.negations:
                return -1.0
        
        return 1.0
    
    def _check_intensifier(self, words: List[str], current_index: int) -> float:
        """Check for intensifiers in previous 2 words"""
        start_index = max(0, current_index - 2)
        
        for i in range(start_index, current_index):
            word = words[i].lower()
            if word in self.intensifiers:
                return self.intensifiers[word]
        
        return 1.0
    
    def _extract_entities(self, text: str, symbol: Optional[str] = None) -> List[str]:
        """Extract named entities from text"""
        entities = []
        
        # Add symbol if provided
        if symbol:
            entities.append(symbol)
        
        # Simple pattern matching for common entities
        # Company names (capitalized words)
        company_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Inc|Corp|Ltd|LLC|Co)\b'
        companies = re.findall(company_pattern, text)
        entities.extend(companies)
        
        # Stock symbols (3-4 uppercase letters)
        symbol_pattern = r'\b[A-Z]{3,4}\b'
        symbols = re.findall(symbol_pattern, text)
        entities.extend(symbols)
        
        # Remove duplicates and limit
        entities = list(set(entities))[:5]
        
        return entities


class MarketSentimentAnalyzer:
    """
    Comprehensive market sentiment analyzer
    
    Aggregates sentiment from multiple sources and provides
    market-wide and symbol-specific sentiment analysis
    """
    
    def __init__(self):
        self.text_analyzer = RuleBasedSentimentAnalyzer()
        
        # Sentiment history
        self.sentiment_history: Dict[str, List[SentimentScore]] = {}
        self.market_sentiment_history: List[SentimentScore] = []
        
        # Configuration
        self.max_history_size = 1000
        self.sentiment_decay_hours = 24
        
        self.logger = logging.getLogger(__name__)
    
    async def analyze_news_sentiment(self, 
                                   news_articles: List[Dict[str, Any]], 
                                   symbol: Optional[str] = None) -> SentimentScore:
        """
        Analyze sentiment from news articles
        
        Args:
            news_articles: List of news articles with 'title', 'content', 'timestamp'
            symbol: Optional symbol to filter for
            
        Returns:
            Aggregated sentiment score
        """
        if not news_articles:
            return SentimentScore(
                source=SentimentSource.NEWS,
                symbol=symbol,
                polarity=0.0,
                confidence=0.0,
                magnitude=0.0
            )
        
        sentiments = []
        
        for article in news_articles:
            # Combine title and content
            text = f"{article.get('title', '')} {article.get('content', '')}"
            
            if symbol:
                # Check if article mentions the symbol
                if symbol.upper() not in text.upper():
                    continue
            
            sentiment = await self.text_analyzer.analyze_text(text, symbol)
            sentiment.source = SentimentSource.NEWS
            sentiment.content_id = article.get('id')
            sentiment.timestamp = article.get('timestamp', time.time())
            
            sentiments.append(sentiment)
        
        if not sentiments:
            return SentimentScore(
                source=SentimentSource.NEWS,
                symbol=symbol,
                polarity=0.0,
                confidence=0.0,
                magnitude=0.0
            )
        
        # Aggregate sentiments
        return self._aggregate_sentiments(sentiments, SentimentSource.NEWS, symbol)
    
    async def analyze_social_sentiment(self, 
                                     social_posts: List[Dict[str, Any]], 
                                     symbol: Optional[str] = None) -> SentimentScore:
        """
        Analyze sentiment from social media posts
        
        Args:
            social_posts: List of social media posts
            symbol: Optional symbol to filter for
            
        Returns:
            Aggregated sentiment score
        """
        if not social_posts:
            return SentimentScore(
                source=SentimentSource.SOCIAL_MEDIA,
                symbol=symbol,
                polarity=0.0,
                confidence=0.0,
                magnitude=0.0
            )
        
        sentiments = []
        
        for post in social_posts:
            text = post.get('text', '')
            
            if symbol:
                # Check if post mentions the symbol
                if symbol.upper() not in text.upper() and f"${symbol.upper()}" not in text:
                    continue
            
            sentiment = await self.text_analyzer.analyze_text(text, symbol)
            sentiment.source = SentimentSource.SOCIAL_MEDIA
            sentiment.content_id = post.get('id')
            sentiment.author = post.get('author')
            sentiment.timestamp = post.get('timestamp', time.time())
            
            # Weight by follower count or engagement if available
            followers = post.get('followers', 1)
            engagement = post.get('likes', 0) + post.get('retweets', 0)
            weight = min(3.0, 1.0 + np.log10(max(1, followers + engagement)) / 3) if NUMPY_AVAILABLE else 1.0
            
            # Apply weight to sentiment
            sentiment.magnitude *= weight
            sentiment.confidence *= min(1.0, weight)
            
            sentiments.append(sentiment)
        
        if not sentiments:
            return SentimentScore(
                source=SentimentSource.SOCIAL_MEDIA,
                symbol=symbol,
                polarity=0.0,
                confidence=0.0,
                magnitude=0.0
            )
        
        return self._aggregate_sentiments(sentiments, SentimentSource.SOCIAL_MEDIA, symbol)
    
    async def get_symbol_sentiment(self, 
                                 symbol: str, 
                                 time_window_hours: int = 24) -> Optional[SentimentScore]:
        """
        Get aggregated sentiment for a specific symbol
        
        Args:
            symbol: Stock symbol
            time_window_hours: Time window for sentiment aggregation
            
        Returns:
            Aggregated sentiment score or None if no data
        """
        if symbol not in self.sentiment_history:
            return None
        
        # Filter by time window
        cutoff_time = time.time() - (time_window_hours * 3600)
        recent_sentiments = [
            s for s in self.sentiment_history[symbol]
            if s.timestamp >= cutoff_time
        ]
        
        if not recent_sentiments:
            return None
        
        # Aggregate recent sentiments
        aggregated = self._aggregate_sentiments(recent_sentiments, None, symbol)
        aggregated.time_window_minutes = time_window_hours * 60
        
        return aggregated
    
    async def get_market_sentiment(self, time_window_hours: int = 24) -> Optional[SentimentScore]:
        """
        Get overall market sentiment
        
        Args:
            time_window_hours: Time window for sentiment aggregation
            
        Returns:
            Market-wide sentiment score
        """
        # Filter by time window
        cutoff_time = time.time() - (time_window_hours * 3600)
        recent_sentiments = [
            s for s in self.market_sentiment_history
            if s.timestamp >= cutoff_time
        ]
        
        if not recent_sentiments:
            return None
        
        # Aggregate market sentiments
        aggregated = self._aggregate_sentiments(recent_sentiments, SentimentSource.MARKET_DATA, None)
        aggregated.time_window_minutes = time_window_hours * 60
        
        return aggregated
    
    def add_sentiment(self, sentiment: SentimentScore):
        """Add sentiment score to history"""
        # Add to symbol-specific history
        if sentiment.symbol:
            if sentiment.symbol not in self.sentiment_history:
                self.sentiment_history[sentiment.symbol] = []
            
            self.sentiment_history[sentiment.symbol].append(sentiment)
            
            # Limit history size
            if len(self.sentiment_history[sentiment.symbol]) > self.max_history_size:
                self.sentiment_history[sentiment.symbol] = self.sentiment_history[sentiment.symbol][-self.max_history_size:]
        
        # Add to market history
        self.market_sentiment_history.append(sentiment)
        if len(self.market_sentiment_history) > self.max_history_size:
            self.market_sentiment_history = self.market_sentiment_history[-self.max_history_size:]
    
    def _aggregate_sentiments(self, 
                            sentiments: List[SentimentScore], 
                            source: Optional[SentimentSource],
                            symbol: Optional[str]) -> SentimentScore:
        """Aggregate multiple sentiment scores"""
        if not sentiments:
            return SentimentScore(
                source=source or SentimentSource.NEWS,
                symbol=symbol,
                polarity=0.0,
                confidence=0.0,
                magnitude=0.0
            )
        
        # Weight sentiments by confidence and recency
        total_weight = 0.0
        weighted_polarity = 0.0
        weighted_magnitude = 0.0
        
        current_time = time.time()
        
        for sentiment in sentiments:
            # Time decay (more recent = higher weight)
            time_diff_hours = (current_time - sentiment.timestamp) / 3600
            time_weight = max(0.1, 1.0 - (time_diff_hours / self.sentiment_decay_hours))
            
            # Combined weight
            weight = sentiment.confidence * sentiment.magnitude * time_weight
            
            weighted_polarity += sentiment.polarity * weight
            weighted_magnitude += sentiment.magnitude * weight
            total_weight += weight
        
        if total_weight == 0:
            return SentimentScore(
                source=source or sentiments[0].source,
                symbol=symbol,
                polarity=0.0,
                confidence=0.0,
                magnitude=0.0
            )
        
        # Calculate aggregated values
        avg_polarity = weighted_polarity / total_weight
        avg_magnitude = weighted_magnitude / total_weight
        
        # Confidence based on sample size and agreement
        sample_confidence = min(1.0, len(sentiments) / 10.0)
        
        # Agreement measure (how consistent are the sentiments)
        polarities = [s.polarity for s in sentiments]
        if NUMPY_AVAILABLE:
            agreement = 1.0 - (np.std(polarities) / 2.0)  # Normalize std dev
        else:
            mean_pol = sum(polarities) / len(polarities)
            variance = sum((p - mean_pol) ** 2 for p in polarities) / len(polarities)
            agreement = 1.0 - (variance ** 0.5 / 2.0)
        
        final_confidence = sample_confidence * max(0.1, agreement)
        
        # Collect all keywords and entities
        all_keywords = []
        all_entities = []
        for s in sentiments:
            all_keywords.extend(s.keywords)
            all_entities.extend(s.entities)
        
        # Remove duplicates and limit
        unique_keywords = list(set(all_keywords))[:20]
        unique_entities = list(set(all_entities))[:10]
        
        return SentimentScore(
            source=source or sentiments[0].source,
            symbol=symbol,
            polarity=avg_polarity,
            confidence=min(1.0, final_confidence),
            magnitude=avg_magnitude,
            keywords=unique_keywords,
            entities=unique_entities,
            sample_size=len(sentiments),
            timestamp=current_time
        )
    
    def get_sentiment_trend(self, 
                          symbol: Optional[str] = None, 
                          hours: int = 24) -> Dict[str, Any]:
        """
        Get sentiment trend analysis
        
        Args:
            symbol: Optional symbol (None for market-wide)
            hours: Number of hours to analyze
            
        Returns:
            Trend analysis dictionary
        """
        # Get relevant sentiment history
        if symbol:
            sentiments = self.sentiment_history.get(symbol, [])
        else:
            sentiments = self.market_sentiment_history
        
        # Filter by time
        cutoff_time = time.time() - (hours * 3600)
        recent_sentiments = [
            s for s in sentiments
            if s.timestamp >= cutoff_time
        ]
        
        if len(recent_sentiments) < 2:
            return {
                'trend': 'insufficient_data',
                'direction': 'unknown',
                'strength': 0.0,
                'sample_size': len(recent_sentiments)
            }
        
        # Sort by timestamp
        recent_sentiments.sort(key=lambda x: x.timestamp)
        
        # Calculate trend
        timestamps = [s.timestamp for s in recent_sentiments]
        polarities = [s.polarity for s in recent_sentiments]
        
        if NUMPY_AVAILABLE:
            # Linear regression for trend
            x = np.array(timestamps)
            y = np.array(polarities)
            
            # Normalize timestamps
            x = (x - x.min()) / (x.max() - x.min() + 1e-10)
            
            # Calculate slope
            slope = np.polyfit(x, y, 1)[0]
            
            # Determine trend
            if abs(slope) < 0.1:
                trend = 'stable'
                direction = 'sideways'
            elif slope > 0:
                trend = 'improving'
                direction = 'up'
            else:
                trend = 'deteriorating'
                direction = 'down'
            
            strength = min(1.0, abs(slope))
        else:
            # Simple trend calculation
            first_half = recent_sentiments[:len(recent_sentiments)//2]
            second_half = recent_sentiments[len(recent_sentiments)//2:]
            
            first_avg = sum(s.polarity for s in first_half) / len(first_half)
            second_avg = sum(s.polarity for s in second_half) / len(second_half)
            
            change = second_avg - first_avg
            
            if abs(change) < 0.1:
                trend = 'stable'
                direction = 'sideways'
            elif change > 0:
                trend = 'improving'
                direction = 'up'
            else:
                trend = 'deteriorating'
                direction = 'down'
            
            strength = min(1.0, abs(change))
        
        return {
            'trend': trend,
            'direction': direction,
            'strength': strength,
            'sample_size': len(recent_sentiments),
            'time_window_hours': hours
        }

class
 MLSentimentAnalyzer(SentimentAnalyzer):
    """
    Machine Learning-based sentiment analyzer
    
    Uses pre-trained models for more accurate sentiment analysis
    """
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path
        self.model = None
        self.tokenizer = None
        self.is_initialized = False
        
        # Fallback to rule-based analyzer
        self.fallback_analyzer = RuleBasedSentimentAnalyzer()
        
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self):
        """Initialize ML model (placeholder for actual model loading)"""
        try:
            # In a real implementation, this would load a pre-trained model
            # like BERT, RoBERTa, or FinBERT for financial sentiment
            
            # For now, we'll simulate model initialization
            await asyncio.sleep(0.1)  # Simulate loading time
            self.is_initialized = True
            
            self.logger.info("ML sentiment model initialized (simulated)")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ML model: {e}")
            self.is_initialized = False
    
    async def analyze_text(self, text: str, symbol: Optional[str] = None) -> SentimentScore:
        """Analyze sentiment using ML model"""
        if not self.is_initialized:
            # Fallback to rule-based analysis
            return await self.fallback_analyzer.analyze_text(text, symbol)
        
        try:
            # Simulate ML model inference
            # In reality, this would:
            # 1. Tokenize the text
            # 2. Run inference through the model
            # 3. Extract sentiment scores
            
            # For simulation, we'll enhance the rule-based approach
            rule_based_result = await self.fallback_analyzer.analyze_text(text, symbol)
            
            # Simulate ML enhancement
            ml_confidence_boost = 0.2
            ml_polarity_adjustment = 0.1 * np.random.normal() if NUMPY_AVAILABLE else 0.0
            
            enhanced_polarity = max(-1.0, min(1.0, rule_based_result.polarity + ml_polarity_adjustment))
            enhanced_confidence = min(1.0, rule_based_result.confidence + ml_confidence_boost)
            
            return SentimentScore(
                source=rule_based_result.source,
                symbol=symbol,
                polarity=enhanced_polarity,
                confidence=enhanced_confidence,
                magnitude=rule_based_result.magnitude,
                content_snippet=rule_based_result.content_snippet,
                keywords=rule_based_result.keywords,
                entities=rule_based_result.entities,
                timestamp=time.time()
            )
            
        except Exception as e:
            self.logger.error(f"ML sentiment analysis failed: {e}")
            # Fallback to rule-based
            return await self.fallback_analyzer.analyze_text(text, symbol)
    
    async def analyze_batch(self, texts: List[str], symbol: Optional[str] = None) -> List[SentimentScore]:
        """Analyze batch of texts with ML model"""
        if not self.is_initialized:
            return await self.fallback_analyzer.analyze_batch(texts, symbol)
        
        results = []
        for text in texts:
            sentiment = await self.analyze_text(text, symbol)
            results.append(sentiment)
        
        return results


class EarningsCallAnalyzer:
    """
    Specialized analyzer for earnings call transcripts
    
    Focuses on financial language and executive sentiment
    """
    
    def __init__(self):
        self.financial_keywords = {
            # Revenue and growth
            'revenue growth': 0.7, 'strong revenue': 0.8, 'revenue beat': 0.9,
            'revenue miss': -0.7, 'revenue decline': -0.6, 'weak revenue': -0.5,
            
            # Profitability
            'margin expansion': 0.8, 'improved margins': 0.7, 'margin compression': -0.7,
            'cost savings': 0.6, 'cost reduction': 0.5, 'cost overruns': -0.6,
            
            # Guidance and outlook
            'raised guidance': 0.9, 'increased outlook': 0.8, 'positive outlook': 0.7,
            'lowered guidance': -0.9, 'reduced outlook': -0.8, 'cautious outlook': -0.4,
            
            # Market conditions
            'strong demand': 0.8, 'robust demand': 0.7, 'weak demand': -0.6,
            'market headwinds': -0.5, 'challenging environment': -0.4,
            
            # Execution
            'strong execution': 0.7, 'operational excellence': 0.8, 'execution issues': -0.7,
            'integration challenges': -0.5, 'synergies realized': 0.6
        }
        
        self.uncertainty_phrases = {
            'uncertain', 'unclear', 'challenging to predict', 'difficult to forecast',
            'remains to be seen', 'too early to tell', 'monitoring closely'
        }
        
        self.confidence_phrases = {
            'confident', 'optimistic', 'excited', 'pleased', 'strong conviction',
            'well positioned', 'on track', 'ahead of schedule'
        }
        
        self.logger = logging.getLogger(__name__)
    
    async def analyze_earnings_call(self, 
                                  transcript: str, 
                                  symbol: str,
                                  speaker_segments: Optional[List[Dict[str, Any]]] = None) -> SentimentScore:
        """
        Analyze earnings call transcript
        
        Args:
            transcript: Full transcript text
            symbol: Company symbol
            speaker_segments: Optional list of speaker segments with metadata
            
        Returns:
            Sentiment score focused on financial outlook
        """
        try:
            # Analyze overall transcript
            base_analyzer = RuleBasedSentimentAnalyzer()
            base_sentiment = await base_analyzer.analyze_text(transcript, symbol)
            
            # Apply earnings-specific analysis
            earnings_score = self._analyze_financial_language(transcript)
            confidence_score = self._analyze_management_confidence(transcript)
            uncertainty_score = self._analyze_uncertainty_indicators(transcript)
            
            # Weight the different components
            combined_polarity = (
                base_sentiment.polarity * 0.4 +
                earnings_score * 0.4 +
                confidence_score * 0.2
            )
            
            # Adjust confidence based on uncertainty
            adjusted_confidence = base_sentiment.confidence * (1.0 - uncertainty_score * 0.3)
            
            # Extract earnings-specific entities
            entities = self._extract_financial_entities(transcript)
            
            return SentimentScore(
                source=SentimentSource.EARNINGS_CALLS,
                symbol=symbol,
                polarity=max(-1.0, min(1.0, combined_polarity)),
                confidence=max(0.0, min(1.0, adjusted_confidence)),
                magnitude=base_sentiment.magnitude,
                content_snippet=transcript[:300] + "..." if len(transcript) > 300 else transcript,
                keywords=base_sentiment.keywords,
                entities=entities,
                timestamp=time.time()
            )
            
        except Exception as e:
            self.logger.error(f"Earnings call analysis failed: {e}")
            # Fallback to basic analysis
            return SentimentScore(
                source=SentimentSource.EARNINGS_CALLS,
                symbol=symbol,
                polarity=0.0,
                confidence=0.0,
                magnitude=0.0
            )
    
    def _analyze_financial_language(self, text: str) -> float:
        """Analyze financial-specific language patterns"""
        text_lower = text.lower()
        score = 0.0
        matches = 0
        
        for phrase, weight in self.financial_keywords.items():
            if phrase in text_lower:
                score += weight
                matches += 1
        
        return score / max(1, matches)
    
    def _analyze_management_confidence(self, text: str) -> float:
        """Analyze management confidence indicators"""
        text_lower = text.lower()
        confidence_count = 0
        
        for phrase in self.confidence_phrases:
            confidence_count += text_lower.count(phrase)
        
        # Normalize by text length
        text_length = len(text.split())
        confidence_density = confidence_count / max(100, text_length) * 100
        
        return min(1.0, confidence_density)
    
    def _analyze_uncertainty_indicators(self, text: str) -> float:
        """Analyze uncertainty and hedging language"""
        text_lower = text.lower()
        uncertainty_count = 0
        
        for phrase in self.uncertainty_phrases:
            uncertainty_count += text_lower.count(phrase)
        
        # Normalize by text length
        text_length = len(text.split())
        uncertainty_density = uncertainty_count / max(100, text_length) * 100
        
        return min(1.0, uncertainty_density)
    
    def _extract_financial_entities(self, text: str) -> List[str]:
        """Extract financial entities from earnings call"""
        entities = []
        
        # Financial metrics patterns
        metric_patterns = [
            r'\$[\d,]+(?:\.\d+)?[BMK]?',  # Dollar amounts
            r'\d+(?:\.\d+)?%',  # Percentages
            r'Q[1-4]\s+\d{4}',  # Quarters
            r'FY\s*\d{4}',  # Fiscal years
        ]
        
        for pattern in metric_patterns:
            matches = re.findall(pattern, text)
            entities.extend(matches[:5])  # Limit to 5 per pattern
        
        return entities[:10]  # Total limit


class SocialMediaAnalyzer:
    """
    Specialized analyzer for social media content
    
    Handles hashtags, mentions, emojis, and social media specific language
    """
    
    def __init__(self):
        self.emoji_sentiment = {
            '😀': 0.8, '😃': 0.8, '😄': 0.9, '😁': 0.7, '😊': 0.6,
            '🙂': 0.4, '😐': 0.0, '😕': -0.3, '😞': -0.6, '😢': -0.8,
            '😭': -0.9, '😡': -0.9, '🤬': -1.0, '💪': 0.7, '👍': 0.6,
            '👎': -0.6, '🚀': 0.9, '📈': 0.8, '📉': -0.8, '💎': 0.7,
            '🌙': 0.8, '🔥': 0.7, '💯': 0.8, '⚡': 0.6
        }
        
        self.social_slang = {
            'bullish': 0.8, 'bearish': -0.8, 'moon': 0.9, 'lambo': 0.8,
            'hodl': 0.6, 'diamond hands': 0.8, 'paper hands': -0.6,
            'to the moon': 0.9, 'stonks': 0.5, 'yolo': 0.3,
            'fud': -0.7, 'fomo': 0.4, 'rekt': -0.9, 'pump': 0.7,
            'dump': -0.7, 'ape': 0.5, 'degenerates': 0.3
        }
        
        self.logger = logging.getLogger(__name__)
    
    async def analyze_social_post(self, 
                                post_text: str, 
                                symbol: Optional[str] = None,
                                metadata: Optional[Dict[str, Any]] = None) -> SentimentScore:
        """
        Analyze social media post with social-specific features
        
        Args:
            post_text: Social media post text
            symbol: Optional stock symbol
            metadata: Optional metadata (followers, likes, etc.)
            
        Returns:
            Social media sentiment score
        """
        try:
            # Base analysis
            base_analyzer = RuleBasedSentimentAnalyzer()
            base_sentiment = await base_analyzer.analyze_text(post_text, symbol)
            
            # Social media specific analysis
            emoji_score = self._analyze_emojis(post_text)
            slang_score = self._analyze_social_slang(post_text)
            hashtag_sentiment = self._analyze_hashtags(post_text)
            
            # Combine scores
            social_polarity = (
                base_sentiment.polarity * 0.5 +
                emoji_score * 0.2 +
                slang_score * 0.2 +
                hashtag_sentiment * 0.1
            )
            
            # Adjust confidence based on social signals
            social_confidence = base_sentiment.confidence
            
            # Boost confidence if multiple social signals align
            signal_alignment = self._calculate_signal_alignment([
                base_sentiment.polarity, emoji_score, slang_score, hashtag_sentiment
            ])
            social_confidence *= (1.0 + signal_alignment * 0.3)
            
            # Extract social entities
            entities = self._extract_social_entities(post_text)
            
            # Apply influence weighting if metadata available
            influence_weight = 1.0
            if metadata:
                followers = metadata.get('followers', 0)
                engagement = metadata.get('likes', 0) + metadata.get('retweets', 0)
                influence_weight = self._calculate_influence_weight(followers, engagement)
            
            return SentimentScore(
                source=SentimentSource.SOCIAL_MEDIA,
                symbol=symbol,
                polarity=max(-1.0, min(1.0, social_polarity)),
                confidence=max(0.0, min(1.0, social_confidence)),
                magnitude=base_sentiment.magnitude * influence_weight,
                content_snippet=post_text[:200] + "..." if len(post_text) > 200 else post_text,
                keywords=base_sentiment.keywords,
                entities=entities,
                timestamp=time.time()
            )
            
        except Exception as e:
            self.logger.error(f"Social media analysis failed: {e}")
            return SentimentScore(
                source=SentimentSource.SOCIAL_MEDIA,
                symbol=symbol,
                polarity=0.0,
                confidence=0.0,
                magnitude=0.0
            )
    
    def _analyze_emojis(self, text: str) -> float:
        """Analyze emoji sentiment in text"""
        emoji_scores = []
        
        for char in text:
            if char in self.emoji_sentiment:
                emoji_scores.append(self.emoji_sentiment[char])
        
        if not emoji_scores:
            return 0.0
        
        return sum(emoji_scores) / len(emoji_scores)
    
    def _analyze_social_slang(self, text: str) -> float:
        """Analyze social media slang and trading terminology"""
        text_lower = text.lower()
        slang_scores = []
        
        for term, score in self.social_slang.items():
            if term in text_lower:
                slang_scores.append(score)
        
        if not slang_scores:
            return 0.0
        
        return sum(slang_scores) / len(slang_scores)
    
    def _analyze_hashtags(self, text: str) -> float:
        """Analyze sentiment of hashtags"""
        hashtags = re.findall(r'#\w+', text.lower())
        
        if not hashtags:
            return 0.0
        
        # Simple hashtag sentiment (could be enhanced with hashtag sentiment database)
        positive_hashtags = ['#bullish', '#moon', '#buy', '#long', '#calls']
        negative_hashtags = ['#bearish', '#sell', '#short', '#puts', '#crash']
        
        positive_count = sum(1 for tag in hashtags if tag in positive_hashtags)
        negative_count = sum(1 for tag in hashtags if tag in negative_hashtags)
        
        total_sentiment_tags = positive_count + negative_count
        if total_sentiment_tags == 0:
            return 0.0
        
        return (positive_count - negative_count) / total_sentiment_tags
    
    def _extract_social_entities(self, text: str) -> List[str]:
        """Extract social media specific entities"""
        entities = []
        
        # Extract hashtags
        hashtags = re.findall(r'#\w+', text)
        entities.extend(hashtags[:3])
        
        # Extract mentions
        mentions = re.findall(r'@\w+', text)
        entities.extend(mentions[:3])
        
        # Extract cashtags (stock symbols)
        cashtags = re.findall(r'\$[A-Z]{1,5}', text)
        entities.extend(cashtags[:3])
        
        return entities[:10]
    
    def _calculate_signal_alignment(self, signals: List[float]) -> float:
        """Calculate how well different sentiment signals align"""
        if not signals or len(signals) < 2:
            return 0.0
        
        # Remove zero signals
        non_zero_signals = [s for s in signals if abs(s) > 0.1]
        
        if len(non_zero_signals) < 2:
            return 0.0
        
        # Check if signals have same direction
        positive_signals = [s for s in non_zero_signals if s > 0]
        negative_signals = [s for s in non_zero_signals if s < 0]
        
        # High alignment if most signals point in same direction
        if len(positive_signals) > len(negative_signals) * 2:
            return 0.8
        elif len(negative_signals) > len(positive_signals) * 2:
            return 0.8
        else:
            return 0.2  # Mixed signals
    
    def _calculate_influence_weight(self, followers: int, engagement: int) -> float:
        """Calculate influence weight based on social metrics"""
        if followers == 0 and engagement == 0:
            return 1.0
        
        # Logarithmic scaling for influence
        if NUMPY_AVAILABLE:
            follower_weight = np.log10(max(1, followers)) / 6.0  # Max weight at 1M followers
            engagement_weight = np.log10(max(1, engagement)) / 4.0  # Max weight at 10K engagement
        else:
            follower_weight = min(1.0, followers / 100000)  # Linear approximation
            engagement_weight = min(1.0, engagement / 1000)
        
        return 1.0 + (follower_weight + engagement_weight) * 0.5
 
       # Sort by timestamp
        recent_sentiments.sort(key=lambda x: x.timestamp)
        
        # Calculate trend
        first_half = recent_sentiments[:len(recent_sentiments)//2]
        second_half = recent_sentiments[len(recent_sentiments)//2:]
        
        if not first_half or not second_half:
            return {
                'trend': 'insufficient_data',
                'direction': 'unknown',
                'strength': 0.0,
                'sample_size': len(recent_sentiments)
            }
        
        # Average sentiment for each half
        first_avg = sum(s.polarity for s in first_half) / len(first_half)
        second_avg = sum(s.polarity for s in second_half) / len(second_half)
        
        # Calculate trend strength and direction
        trend_change = second_avg - first_avg
        trend_strength = abs(trend_change)
        
        if trend_change > 0.1:
            direction = 'improving'
        elif trend_change < -0.1:
            direction = 'deteriorating'
        else:
            direction = 'stable'
        
        return {
            'trend': direction,
            'direction': direction,
            'strength': trend_strength,
            'change': trend_change,
            'first_half_avg': first_avg,
            'second_half_avg': second_avg,
            'sample_size': len(recent_sentiments),
            'time_span_hours': hours
        }


class MLSentimentAnalyzer(SentimentAnalyzer):
    """
    Machine Learning-powered sentiment analyzer
    
    Uses trained models for more accurate sentiment analysis
    with support for financial domain-specific models
    """
    
    def __init__(self, 
                 inference_engine: Optional[InferenceEngine] = None,
                 model_manager: Optional[ModelManager] = None,
                 fallback_analyzer: Optional[SentimentAnalyzer] = None):
        
        self.inference_engine = inference_engine
        self.model_manager = model_manager
        self.fallback_analyzer = fallback_analyzer or RuleBasedSentimentAnalyzer()
        
        # Model configurations
        self.sentiment_model_id = "financial_sentiment_model"
        self.emotion_model_id = "emotion_classification_model"
        self.entity_model_id = "financial_entity_extraction_model"
        
        # Feature extraction
        self.max_sequence_length = 512
        self.vocab_size = 50000
        
        # Performance tracking
        self.prediction_cache = {}
        self.cache_ttl = 3600  # 1 hour
        
        self.logger = logging.getLogger(__name__)
    
    async def analyze_text(self, text: str, symbol: Optional[str] = None) -> SentimentScore:
        """Analyze sentiment using ML models with fallback"""
        try:
            # Check cache first
            cache_key = self._get_cache_key(text, symbol)
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                cached_result.cache_hit = True
                return cached_result
            
            start_time = time.time()
            
            # Try ML analysis first
            if self.inference_engine and self.model_manager:
                try:
                    ml_result = await self._analyze_with_ml(text, symbol)
                    if ml_result:
                        processing_time = (time.time() - start_time) * 1000
                        ml_result.processing_time_ms = processing_time
                        
                        # Cache result
                        self._cache_result(cache_key, ml_result)
                        return ml_result
                except Exception as e:
                    self.logger.warning(f"ML sentiment analysis failed, using fallback: {e}")
            
            # Fallback to rule-based analysis
            fallback_result = await self.fallback_analyzer.analyze_text(text, symbol)
            processing_time = (time.time() - start_time) * 1000
            fallback_result.processing_time_ms = processing_time
            
            # Cache fallback result
            self._cache_result(cache_key, fallback_result)
            return fallback_result
            
        except Exception as e:
            self.logger.error(f"Sentiment analysis failed: {e}")
            return SentimentScore(
                source=SentimentSource.NEWS,
                symbol=symbol,
                polarity=0.0,
                confidence=0.0,
                magnitude=0.0
            )
    
    async def analyze_batch(self, texts: List[str], symbol: Optional[str] = None) -> List[SentimentScore]:
        """Analyze multiple texts efficiently"""
        if not texts:
            return []
        
        # Check cache for all texts
        results = []
        uncached_texts = []
        uncached_indices = []
        
        for i, text in enumerate(texts):
            cache_key = self._get_cache_key(text, symbol)
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                cached_result.cache_hit = True
                results.append((i, cached_result))
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        # Process uncached texts
        if uncached_texts:
            if self.inference_engine and len(uncached_texts) > 1:
                # Batch ML processing
                try:
                    batch_results = await self._analyze_batch_with_ml(uncached_texts, symbol)
                    for idx, result in zip(uncached_indices, batch_results):
                        results.append((idx, result))
                        # Cache result
                        cache_key = self._get_cache_key(uncached_texts[uncached_indices.index(idx)], symbol)
                        self._cache_result(cache_key, result)
                except Exception as e:
                    self.logger.warning(f"Batch ML analysis failed, using fallback: {e}")
                    # Fallback to individual processing
                    for idx, text in zip(uncached_indices, uncached_texts):
                        result = await self.fallback_analyzer.analyze_text(text, symbol)
                        results.append((idx, result))
            else:
                # Individual processing
                for idx, text in zip(uncached_indices, uncached_texts):
                    result = await self.analyze_text(text, symbol)
                    results.append((idx, result))
        
        # Sort results by original index
        results.sort(key=lambda x: x[0])
        return [result for _, result in results]
    
    async def _analyze_with_ml(self, text: str, symbol: Optional[str] = None) -> Optional[SentimentScore]:
        """Analyze sentiment using ML models"""
        try:
            # Prepare features
            features = await self._prepare_features(text, symbol)
            
            # Get sentiment prediction
            sentiment_request = InferenceRequest(
                request_id=f"sentiment_{int(time.time_ns())}",
                model_id=self.sentiment_model_id,
                input_data=features,
                priority=InferencePriority.HIGH,
                timeout_ms=500.0,
                use_cache=True
            )
            
            sentiment_response = await self.inference_engine.predict(sentiment_request)
            
            if sentiment_response.status.value != 'completed':
                return None
            
            # Parse sentiment prediction
            sentiment_pred = sentiment_response.prediction
            if isinstance(sentiment_pred, (list, np.ndarray)) and len(sentiment_pred) >= 3:
                # [negative, neutral, positive] probabilities
                negative_prob = sentiment_pred[0]
                neutral_prob = sentiment_pred[1]
                positive_prob = sentiment_pred[2]
                
                # Calculate polarity (-1 to 1)
                polarity = positive_prob - negative_prob
                confidence = max(negative_prob, neutral_prob, positive_prob)
                magnitude = abs(polarity)
            else:
                # Single value prediction
                polarity = float(sentiment_pred)
                confidence = abs(polarity)
                magnitude = abs(polarity)
            
            # Get emotion analysis if available
            emotion_scores = {}
            try:
                emotion_request = InferenceRequest(
                    request_id=f"emotion_{int(time.time_ns())}",
                    model_id=self.emotion_model_id,
                    input_data=features,
                    priority=InferencePriority.MEDIUM,
                    timeout_ms=300.0,
                    use_cache=True
                )
                
                emotion_response = await self.inference_engine.predict(emotion_request)
                if emotion_response.status.value == 'completed':
                    emotion_pred = emotion_response.prediction
                    if isinstance(emotion_pred, dict):
                        emotion_scores = emotion_pred
                    elif isinstance(emotion_pred, (list, np.ndarray)) and len(emotion_pred) >= 6:
                        # Standard emotions: joy, sadness, anger, fear, surprise, disgust
                        emotion_labels = ['joy', 'sadness', 'anger', 'fear', 'surprise', 'disgust']
                        emotion_scores = dict(zip(emotion_labels, emotion_pred[:6]))
            except Exception as e:
                self.logger.debug(f"Emotion analysis failed: {e}")
            
            # Extract entities if available
            entities = []
            try:
                entity_request = InferenceRequest(
                    request_id=f"entity_{int(time.time_ns())}",
                    model_id=self.entity_model_id,
                    input_data={'text': text},
                    priority=InferencePriority.LOW,
                    timeout_ms=200.0,
                    use_cache=True
                )
                
                entity_response = await self.inference_engine.predict(entity_request)
                if entity_response.status.value == 'completed':
                    entities = entity_response.prediction or []
            except Exception as e:
                self.logger.debug(f"Entity extraction failed: {e}")
            
            # Calculate additional metrics
            subjectivity = self._calculate_subjectivity(text)
            market_relevance = self._calculate_market_relevance(text, symbol)
            credibility = self._calculate_credibility(text)
            
            return SentimentScore(
                source=SentimentSource.NEWS,
                symbol=symbol,
                polarity=max(-1.0, min(1.0, polarity)),
                confidence=min(1.0, confidence),
                magnitude=min(1.0, magnitude),
                content_snippet=text[:200] + "..." if len(text) > 200 else text,
                entities=entities,
                emotion_scores=emotion_scores,
                subjectivity=subjectivity,
                market_relevance=market_relevance,
                credibility=credibility,
                ml_confidence=confidence,
                model_version=sentiment_response.model_version,
                feature_importance=sentiment_response.feature_importance or {}
            )
            
        except Exception as e:
            self.logger.error(f"ML sentiment analysis failed: {e}")
            return None
    
    async def _analyze_batch_with_ml(self, texts: List[str], symbol: Optional[str] = None) -> List[SentimentScore]:
        """Batch ML sentiment analysis"""
        try:
            # Prepare batch features
            batch_features = []
            for text in texts:
                features = await self._prepare_features(text, symbol)
                batch_features.append(features)
            
            # Batch sentiment prediction
            sentiment_request = InferenceRequest(
                request_id=f"batch_sentiment_{int(time.time_ns())}",
                model_id=self.sentiment_model_id,
                input_data=batch_features,
                priority=InferencePriority.HIGH,
                timeout_ms=2000.0,
                use_cache=True
            )
            
            sentiment_response = await self.inference_engine.predict(sentiment_request)
            
            if sentiment_response.status.value != 'completed':
                raise Exception("Batch sentiment prediction failed")
            
            # Parse batch predictions
            batch_predictions = sentiment_response.prediction
            results = []
            
            for i, (text, prediction) in enumerate(zip(texts, batch_predictions)):
                if isinstance(prediction, (list, np.ndarray)) and len(prediction) >= 3:
                    negative_prob = prediction[0]
                    neutral_prob = prediction[1]
                    positive_prob = prediction[2]
                    
                    polarity = positive_prob - negative_prob
                    confidence = max(negative_prob, neutral_prob, positive_prob)
                    magnitude = abs(polarity)
                else:
                    polarity = float(prediction)
                    confidence = abs(polarity)
                    magnitude = abs(polarity)
                
                # Create sentiment score
                sentiment_score = SentimentScore(
                    source=SentimentSource.NEWS,
                    symbol=symbol,
                    polarity=max(-1.0, min(1.0, polarity)),
                    confidence=min(1.0, confidence),
                    magnitude=min(1.0, magnitude),
                    content_snippet=text[:200] + "..." if len(text) > 200 else text,
                    ml_confidence=confidence,
                    model_version=sentiment_response.model_version
                )
                
                results.append(sentiment_score)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Batch ML sentiment analysis failed: {e}")
            # Fallback to individual analysis
            results = []
            for text in texts:
                result = await self.fallback_analyzer.analyze_text(text, symbol)
                results.append(result)
            return results
    
    async def _prepare_features(self, text: str, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Prepare features for ML model"""
        features = {
            'text': text,
            'text_length': len(text),
            'word_count': len(text.split()),
            'has_symbol': symbol is not None,
            'symbol': symbol or '',
            'timestamp': time.time()
        }
        
        # Add basic text statistics
        features['exclamation_count'] = text.count('!')
        features['question_count'] = text.count('?')
        features['uppercase_ratio'] = sum(1 for c in text if c.isupper()) / max(1, len(text))
        features['digit_ratio'] = sum(1 for c in text if c.isdigit()) / max(1, len(text))
        
        # Add financial keywords presence
        financial_keywords = ['profit', 'loss', 'revenue', 'earnings', 'dividend', 'growth', 'decline']
        for keyword in financial_keywords:
            features[f'has_{keyword}'] = keyword.lower() in text.lower()
        
        return features
    
    def _calculate_subjectivity(self, text: str) -> float:
        """Calculate text subjectivity (0=objective, 1=subjective)"""
        subjective_indicators = [
            'i think', 'i believe', 'in my opinion', 'personally', 'i feel',
            'amazing', 'terrible', 'love', 'hate', 'best', 'worst'
        ]
        
        text_lower = text.lower()
        subjective_count = sum(1 for indicator in subjective_indicators if indicator in text_lower)
        
        # Normalize by text length
        subjectivity = min(1.0, subjective_count / max(1, len(text.split()) / 10))
        return subjectivity
    
    def _calculate_market_relevance(self, text: str, symbol: Optional[str] = None) -> float:
        """Calculate market relevance of the text"""
        market_keywords = [
            'stock', 'market', 'trading', 'investment', 'financial', 'economic',
            'earnings', 'revenue', 'profit', 'loss', 'dividend', 'merger',
            'acquisition', 'ipo', 'sec', 'fed', 'interest rate', 'inflation'
        ]
        
        text_lower = text.lower()
        relevance_score = 0.0
        
        for keyword in market_keywords:
            if keyword in text_lower:
                relevance_score += 0.1
        
        # Bonus if symbol is mentioned
        if symbol and symbol.lower() in text_lower:
            relevance_score += 0.3
        
        return min(1.0, relevance_score)
    
    def _calculate_credibility(self, text: str) -> float:
        """Calculate source credibility based on text characteristics"""
        credibility = 0.5  # Base credibility
        
        # Factors that increase credibility
        if len(text) > 100:  # Longer texts tend to be more credible
            credibility += 0.1
        
        if any(word in text.lower() for word in ['according to', 'reported', 'announced']):
            credibility += 0.1
        
        if any(word in text.lower() for word in ['ceo', 'cfo', 'official', 'spokesperson']):
            credibility += 0.1
        
        # Factors that decrease credibility
        if text.count('!') > 3:  # Too many exclamations
            credibility -= 0.1
        
        if text.isupper():  # All caps
            credibility -= 0.2
        
        if any(word in text.lower() for word in ['rumor', 'allegedly', 'unconfirmed']):
            credibility -= 0.1
        
        return max(0.0, min(1.0, credibility))
    
    def _get_cache_key(self, text: str, symbol: Optional[str] = None) -> str:
        """Generate cache key for text and symbol"""
        content = f"{text}_{symbol or ''}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[SentimentScore]:
        """Get cached sentiment result"""
        if cache_key in self.prediction_cache:
            cached_data, timestamp = self.prediction_cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return cached_data
            else:
                # Remove expired cache entry
                del self.prediction_cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, result: SentimentScore):
        """Cache sentiment result"""
        self.prediction_cache[cache_key] = (result, time.time())
        
        # Limit cache size
        if len(self.prediction_cache) > 1000:
            # Remove oldest entries
            oldest_keys = sorted(
                self.prediction_cache.keys(),
                key=lambda k: self.prediction_cache[k][1]
            )[:100]
            for key in oldest_keys:
                del self.prediction_cache[key]


class RealTimeSentimentPipeline:
    """
    Real-time sentiment analysis pipeline
    
    Processes sentiment from multiple sources in real-time
    with advanced aggregation, filtering, and alerting
    """
    
    def __init__(self,
                 inference_engine: Optional[InferenceEngine] = None,
                 model_manager: Optional[ModelManager] = None,
                 message_bus: Optional[MessageBus] = None,
                 cache_manager: Optional[CacheManager] = None,
                 max_concurrent_analyses: int = 20):
        
        self.inference_engine = inference_engine
        self.model_manager = model_manager
        self.message_bus = message_bus
        self.cache_manager = cache_manager
        self.max_concurrent_analyses = max_concurrent_analyses
        
        # Initialize analyzers
        self.ml_analyzer = MLSentimentAnalyzer(inference_engine, model_manager)
        self.market_analyzer = MarketSentimentAnalyzer()
        
        # Real-time processing
        self.processing_queue = asyncio.Queue(maxsize=10000)
        self.worker_tasks: List[asyncio.Task] = []
        self.running = False
        
        # Thread pool for CPU-intensive operations
        self.thread_pool = ThreadPoolExecutor(
            max_workers=max_concurrent_analyses,
            thread_name_prefix="sentiment-analysis"
        )
        
        # Sentiment aggregation
        self.sentiment_aggregator = SentimentAggregator()
        
        # Alert system
        self.alert_thresholds = {
            'extreme_sentiment': 0.8,
            'sentiment_shift': 0.5,
            'volume_spike': 3.0,
            'controversy_threshold': 0.7
        }
        
        # Performance metrics
        self.metrics = {
            'total_processed': 0,
            'processing_time_ms': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'ml_analyses': 0,
            'fallback_analyses': 0,
            'alerts_generated': 0
        }
        
        # Source-specific processors
        self.source_processors = {
            SentimentSource.NEWS: self._process_news_content,
            SentimentSource.SOCIAL_MEDIA: self._process_social_content,
            SentimentSource.REDDIT: self._process_reddit_content,
            SentimentSource.TWITTER: self._process_twitter_content,
            SentimentSource.ANALYST_REPORTS: self._process_analyst_content
        }
        
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Start the real-time sentiment pipeline"""
        if self.running:
            return
        
        self.running = True
        
        # Start worker tasks
        for i in range(self.max_concurrent_analyses):
            task = asyncio.create_task(self._sentiment_worker(f"worker-{i}"))
            self.worker_tasks.append(task)
        
        # Start aggregation task
        aggregation_task = asyncio.create_task(self._aggregation_worker())
        self.worker_tasks.append(aggregation_task)
        
        # Start alert monitoring
        alert_task = asyncio.create_task(self._alert_worker())
        self.worker_tasks.append(alert_task)
        
        self.logger.info(f"Sentiment pipeline started with {len(self.worker_tasks)} workers")
    
    async def stop(self):
        """Stop the sentiment pipeline"""
        self.running = False
        
        # Cancel all tasks
        for task in self.worker_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        
        # Shutdown thread pool
        self.thread_pool.shutdown(wait=True)
        
        self.logger.info("Sentiment pipeline stopped")
    
    async def process_content(self, 
                            content: Dict[str, Any], 
                            source: SentimentSource,
                            priority: str = "normal") -> Optional[SentimentScore]:
        """
        Process content for sentiment analysis
        
        Args:
            content: Content dictionary with text, metadata
            source: Source of the content
            priority: Processing priority (high, normal, low)
            
        Returns:
            Sentiment score or None if queued for async processing
        """
        try:
            # Create processing request
            request = {
                'content': content,
                'source': source,
                'priority': priority,
                'timestamp': time.time(),
                'request_id': f"req_{int(time.time_ns())}"
            }
            
            # Add to processing queue
            if priority == "high":
                # Process immediately for high priority
                return await self._process_sentiment_request(request)
            else:
                # Queue for async processing
                try:
                    await self.processing_queue.put(request)
                    return None
                except asyncio.QueueFull:
                    self.logger.warning("Sentiment processing queue full, dropping request")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Failed to process content: {e}")
            return None
    
    async def _sentiment_worker(self, worker_name: str):
        """Background worker for sentiment processing"""
        self.logger.debug(f"Sentiment worker {worker_name} started")
        
        while self.running:
            try:
                # Get request from queue
                try:
                    request = await asyncio.wait_for(
                        self.processing_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Process the request
                sentiment_score = await self._process_sentiment_request(request)
                
                if sentiment_score:
                    # Add to market analyzer
                    self.market_analyzer.add_sentiment(sentiment_score)
                    
                    # Publish to message bus
                    if self.message_bus:
                        await self._publish_sentiment(sentiment_score)
                    
                    # Check for alerts
                    await self._check_sentiment_alerts(sentiment_score)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Sentiment worker {worker_name} error: {e}")
                await asyncio.sleep(1)
        
        self.logger.debug(f"Sentiment worker {worker_name} stopped")
    
    async def _process_sentiment_request(self, request: Dict[str, Any]) -> Optional[SentimentScore]:
        """Process individual sentiment request"""
        try:
            start_time = time.time()
            
            content = request['content']
            source = request['source']
            
            # Use source-specific processor if available
            if source in self.source_processors:
                processor = self.source_processors[source]
                sentiment_score = await processor(content)
            else:
                # Default processing
                text = content.get('text', '')
                symbol = content.get('symbol')
                sentiment_score = await self.ml_analyzer.analyze_text(text, symbol)
                sentiment_score.source = source
            
            if sentiment_score:
                # Add metadata from request
                sentiment_score.content_id = content.get('id')
                sentiment_score.author = content.get('author')
                sentiment_score.timestamp = content.get('timestamp', time.time())
                
                # Update metrics
                processing_time = (time.time() - start_time) * 1000
                sentiment_score.processing_time_ms = processing_time
                
                self.metrics['total_processed'] += 1
                self.metrics['processing_time_ms'] += processing_time
                
                if sentiment_score.ml_confidence:
                    self.metrics['ml_analyses'] += 1
                else:
                    self.metrics['fallback_analyses'] += 1
                
                if sentiment_score.cache_hit:
                    self.metrics['cache_hits'] += 1
                else:
                    self.metrics['cache_misses'] += 1
            
            return sentiment_score
            
        except Exception as e:
            self.logger.error(f"Sentiment request processing failed: {e}")
            return None
    
    async def _process_news_content(self, content: Dict[str, Any]) -> Optional[SentimentScore]:
        """Process news content"""
        text = f"{content.get('title', '')} {content.get('content', '')}"
        symbol = content.get('symbol')
        
        sentiment = await self.ml_analyzer.analyze_text(text, symbol)
        sentiment.source = SentimentSource.NEWS
        
        # Enhanced news-specific metrics
        sentiment.credibility = self._calculate_news_credibility(content)
        sentiment.market_relevance = self._calculate_market_relevance(text, symbol)
        
        return sentiment
    
    async def _process_social_content(self, content: Dict[str, Any]) -> Optional[SentimentScore]:
        """Process social media content"""
        text = content.get('text', '')
        symbol = content.get('symbol')
        
        sentiment = await self.ml_analyzer.analyze_text(text, symbol)
        sentiment.source = SentimentSource.SOCIAL_MEDIA
        
        # Social-specific metrics
        sentiment.engagement_score = self._calculate_engagement_score(content)
        sentiment.reach = content.get('followers', 0)
        sentiment.influence_score = self._calculate_influence_score(content)
        sentiment.viral_potential = self._calculate_viral_potential(content)
        
        return sentiment
    
    async def _process_reddit_content(self, content: Dict[str, Any]) -> Optional[SentimentScore]:
        """Process Reddit content"""
        text = content.get('text', '')
        symbol = content.get('symbol')
        
        sentiment = await self.ml_analyzer.analyze_text(text, symbol)
        sentiment.source = SentimentSource.REDDIT
        
        # Reddit-specific metrics
        upvotes = content.get('upvotes', 0)
        downvotes = content.get('downvotes', 0)
        comments = content.get('comments', 0)
        
        sentiment.engagement_score = (upvotes + comments) / max(1, upvotes + downvotes + comments)
        sentiment.controversy_score = min(downvotes / max(1, upvotes), 1.0)
        
        return sentiment
    
    async def _process_twitter_content(self, content: Dict[str, Any]) -> Optional[SentimentScore]:
        """Process Twitter content"""
        text = content.get('text', '')
        symbol = content.get('symbol')
        
        sentiment = await self.ml_analyzer.analyze_text(text, symbol)
        sentiment.source = SentimentSource.TWITTER
        
        # Twitter-specific metrics
        retweets = content.get('retweets', 0)
        likes = content.get('likes', 0)
        replies = content.get('replies', 0)
        followers = content.get('followers', 0)
        
        sentiment.engagement_score = (retweets + likes + replies) / max(1, followers)
        sentiment.reach = followers
        sentiment.viral_potential = min(retweets / max(1, followers), 1.0)
        
        return sentiment
    
    async def _process_analyst_content(self, content: Dict[str, Any]) -> Optional[SentimentScore]:
        """Process analyst report content"""
        text = content.get('text', '')
        symbol = content.get('symbol')
        
        sentiment = await self.ml_analyzer.analyze_text(text, symbol)
        sentiment.source = SentimentSource.ANALYST_REPORTS
        
        # Analyst-specific metrics
        sentiment.credibility = 0.8  # High credibility for analyst reports
        sentiment.market_relevance = 0.9  # High market relevance
        sentiment.subjectivity = 0.3  # Lower subjectivity
        
        # Extract price targets and ratings if available
        if 'price_target' in content:
            sentiment.metadata['price_target'] = content['price_target']
        if 'rating' in content:
            sentiment.metadata['rating'] = content['rating']
        
        return sentiment
    
    def _calculate_news_credibility(self, content: Dict[str, Any]) -> float:
        """Calculate news source credibility"""
        source = content.get('source', '').lower()
        
        # High credibility sources
        high_credibility = ['reuters', 'bloomberg', 'ap', 'wsj', 'ft']
        if any(src in source for src in high_credibility):
            return 0.9
        
        # Medium credibility sources
        medium_credibility = ['cnbc', 'cnn', 'bbc', 'marketwatch']
        if any(src in source for src in medium_credibility):
            return 0.7
        
        # Default credibility
        return 0.5
    
    def _calculate_engagement_score(self, content: Dict[str, Any]) -> float:
        """Calculate social media engagement score"""
        likes = content.get('likes', 0)
        shares = content.get('shares', 0)
        comments = content.get('comments', 0)
        followers = content.get('followers', 1)
        
        total_engagement = likes + shares + comments
        engagement_rate = total_engagement / max(1, followers)
        
        return min(1.0, engagement_rate * 100)  # Normalize to 0-1
    
    def _calculate_influence_score(self, content: Dict[str, Any]) -> float:
        """Calculate author influence score"""
        followers = content.get('followers', 0)
        verified = content.get('verified', False)
        
        # Base score from follower count
        if followers > 1000000:
            base_score = 1.0
        elif followers > 100000:
            base_score = 0.8
        elif followers > 10000:
            base_score = 0.6
        elif followers > 1000:
            base_score = 0.4
        else:
            base_score = 0.2
        
        # Verification bonus
        if verified:
            base_score = min(1.0, base_score + 0.2)
        
        return base_score
    
    def _calculate_viral_potential(self, content: Dict[str, Any]) -> float:
        """Calculate viral potential of content"""
        shares = content.get('shares', 0)
        retweets = content.get('retweets', 0)
        engagement_rate = self._calculate_engagement_score(content)
        
        # Viral indicators
        viral_score = 0.0
        
        # High share/retweet rate
        if shares + retweets > 100:
            viral_score += 0.3
        
        # High engagement rate
        if engagement_rate > 0.1:
            viral_score += 0.3
        
        # Trending hashtags or keywords
        text = content.get('text', '').lower()
        trending_indicators = ['breaking', 'urgent', 'alert', 'massive', 'huge']
        if any(indicator in text for indicator in trending_indicators):
            viral_score += 0.2
        
        # Time factor (recent content has higher viral potential)
        timestamp = content.get('timestamp', time.time())
        age_hours = (time.time() - timestamp) / 3600
        if age_hours < 1:
            viral_score += 0.2
        elif age_hours < 6:
            viral_score += 0.1
        
        return min(1.0, viral_score)
    
    async def _aggregation_worker(self):
        """Worker for sentiment aggregation"""
        while self.running:
            try:
                await asyncio.sleep(60)  # Aggregate every minute
                await self.sentiment_aggregator.aggregate_sentiments()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Aggregation worker error: {e}")
    
    async def _alert_worker(self):
        """Worker for sentiment alerts"""
        while self.running:
            try:
                await asyncio.sleep(30)  # Check alerts every 30 seconds
                await self._check_market_alerts()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Alert worker error: {e}")
    
    async def _check_sentiment_alerts(self, sentiment: SentimentScore):
        """Check individual sentiment for alerts"""
        try:
            alerts = []
            
            # Extreme sentiment alert
            if abs(sentiment.polarity) >= self.alert_thresholds['extreme_sentiment']:
                alerts.append({
                    'type': 'extreme_sentiment',
                    'symbol': sentiment.symbol,
                    'polarity': sentiment.polarity,
                    'confidence': sentiment.confidence,
                    'source': sentiment.source.value,
                    'message': f"Extreme {'positive' if sentiment.polarity > 0 else 'negative'} sentiment detected"
                })
            
            # High controversy alert
            if sentiment.controversy_score >= self.alert_thresholds['controversy_threshold']:
                alerts.append({
                    'type': 'high_controversy',
                    'symbol': sentiment.symbol,
                    'controversy_score': sentiment.controversy_score,
                    'source': sentiment.source.value,
                    'message': "High controversy content detected"
                })
            
            # Viral content alert
            if sentiment.viral_potential >= 0.8:
                alerts.append({
                    'type': 'viral_content',
                    'symbol': sentiment.symbol,
                    'viral_potential': sentiment.viral_potential,
                    'source': sentiment.source.value,
                    'message': "Content with high viral potential detected"
                })
            
            # Publish alerts
            for alert in alerts:
                if self.message_bus:
                    await self.message_bus.publish(
                        topic=f"alerts.sentiment.{alert['type']}",
                        message=alert
                    )
                
                self.metrics['alerts_generated'] += 1
                self.logger.info(f"Sentiment alert: {alert['message']}")
        
        except Exception as e:
            self.logger.error(f"Alert checking failed: {e}")
    
    async def _check_market_alerts(self):
        """Check for market-wide sentiment alerts"""
        try:
            # Get recent market sentiment
            market_sentiment = await self.market_analyzer.get_market_sentiment(time_window_hours=1)
            
            if not market_sentiment:
                return
            
            # Check for significant market sentiment shifts
            previous_sentiment = await self.market_analyzer.get_market_sentiment(time_window_hours=2)
            
            if previous_sentiment:
                sentiment_change = abs(market_sentiment.polarity - previous_sentiment.polarity)
                
                if sentiment_change >= self.alert_thresholds['sentiment_shift']:
                    alert = {
                        'type': 'market_sentiment_shift',
                        'current_sentiment': market_sentiment.polarity,
                        'previous_sentiment': previous_sentiment.polarity,
                        'change': sentiment_change,
                        'message': f"Significant market sentiment shift detected: {sentiment_change:.2f}"
                    }
                    
                    if self.message_bus:
                        await self.message_bus.publish(
                            topic="alerts.sentiment.market_shift",
                            message=alert
                        )
                    
                    self.metrics['alerts_generated'] += 1
                    self.logger.info(f"Market alert: {alert['message']}")
        
        except Exception as e:
            self.logger.error(f"Market alert checking failed: {e}")
    
    async def _publish_sentiment(self, sentiment: SentimentScore):
        """Publish sentiment score to message bus"""
        try:
            topic = f"sentiment.{sentiment.source.value}"
            if sentiment.symbol:
                topic += f".{sentiment.symbol}"
            
            await self.message_bus.publish(
                topic=topic,
                message=sentiment.to_dict()
            )
        except Exception as e:
            self.logger.error(f"Failed to publish sentiment: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get pipeline performance metrics"""
        total_processed = max(1, self.metrics['total_processed'])
        
        return {
            'total_processed': self.metrics['total_processed'],
            'avg_processing_time_ms': self.metrics['processing_time_ms'] / total_processed,
            'cache_hit_rate': self.metrics['cache_hits'] / (self.metrics['cache_hits'] + self.metrics['cache_misses']) if (self.metrics['cache_hits'] + self.metrics['cache_misses']) > 0 else 0,
            'ml_analysis_rate': self.metrics['ml_analyses'] / total_processed,
            'fallback_analysis_rate': self.metrics['fallback_analyses'] / total_processed,
            'alerts_generated': self.metrics['alerts_generated'],
            'queue_size': self.processing_queue.qsize(),
            'workers_active': len([t for t in self.worker_tasks if not t.done()])
        }


class SentimentAggregator:
    """
    Advanced sentiment aggregation system
    
    Aggregates sentiment across multiple dimensions:
    - Time windows
    - Sources
    - Symbols
    - Market sectors
    """
    
    def __init__(self):
        self.aggregated_sentiments: Dict[str, Dict[str, SentimentScore]] = defaultdict(dict)
        self.time_windows = [5, 15, 60, 240, 1440]  # minutes
        self.logger = logging.getLogger(__name__)
    
    async def aggregate_sentiments(self):
        """Perform sentiment aggregation across all dimensions"""
        try:
            # This would aggregate sentiments from various sources
            # Implementation would depend on data storage backend
            self.logger.debug("Performing sentiment aggregation")
        except Exception as e:
            self.logger.error(f"Sentiment aggregation failed: {e}")


# Export main classes
__all__ = [
    'SentimentScore',
    'SentimentSource',
    'SentimentPolarity',
    'SentimentAnalyzer',
    'RuleBasedSentimentAnalyzer',
    'MLSentimentAnalyzer',
    'MarketSentimentAnalyzer',
    'RealTimeSentimentPipeline',
    'SentimentAggregator'
]