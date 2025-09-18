"""
Test suite for enhanced sentiment analysis pipeline
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, AsyncMock
from typing import List, Dict, Any

from nautilus_trader_engine.ai.sentiment_analyzer import (
    SentimentScore,
    SentimentSource,
    SentimentPolarity,
    RuleBasedSentimentAnalyzer,
    MarketSentimentAnalyzer,
    EnhancedSentimentPipeline,
    SentimentAnomalyDetector
)
from nautilus_trader_engine.ai.inference_engine import InferenceEngine, InferenceRequest, InferencePriority
from nautilus_trader_engine.ai.model_manager import ModelManager
from nautilus_trader_engine.core.messaging.message_bus import MessageBus
from nautilus_trader_engine.core.caching.cache_manager import CacheManager


class TestSentimentScore:
    """Test SentimentScore functionality"""
    
    def test_sentiment_score_creation(self):
        """Test basic sentiment score creation"""
        score = SentimentScore(
            source=SentimentSource.NEWS,
            symbol="AAPL",
            polarity=0.7,
            confidence=0.8,
            magnitude=0.7
        )
        
        assert score.source == SentimentSource.NEWS
        assert score.symbol == "AAPL"
        assert score.polarity == 0.7
        assert score.confidence == 0.8
        assert score.magnitude == 0.7
        assert score.sentiment_label == "Positive"
    
    def test_sentiment_score_validation(self):
        """Test sentiment score validation"""
        # Test invalid confidence
        with pytest.raises(ValueError):
            SentimentScore(
                source=SentimentSource.NEWS,
                symbol="AAPL",
                polarity=0.5,
                confidence=1.5,  # Invalid
                magnitude=0.5
            )
        
        # Test invalid polarity (should be clamped)
        score = SentimentScore(
            source=SentimentSource.NEWS,
            symbol="AAPL",
            polarity=2.0,  # Will be clamped
            confidence=0.8,
            magnitude=0.7
        )
        # Note: Polarity clamping would be handled in the analyzer, not the score itself
    
    def test_sentiment_score_properties(self):
        """Test sentiment score computed properties"""
        score = SentimentScore(
            source=SentimentSource.NEWS,
            symbol="AAPL",
            polarity=0.8,
            confidence=0.9,
            magnitude=0.8,
            market_relevance=0.7,
            credibility=0.8,
            quality_score=0.7
        )
        
        assert score.is_significant
        assert score.is_actionable
        assert score.get_overall_score() > 0.5
    
    def test_sentiment_score_serialization(self):
        """Test sentiment score to_dict method"""
        score = SentimentScore(
            source=SentimentSource.NEWS,
            symbol="AAPL",
            polarity=0.6,
            confidence=0.8,
            magnitude=0.6,
            keywords=["positive", "growth"],
            entities=["AAPL", "Apple Inc"]
        )
        
        data = score.to_dict()
        
        assert data['source'] == 'news'
        assert data['symbol'] == 'AAPL'
        assert data['polarity'] == 0.6
        assert data['confidence'] == 0.8
        assert data['sentiment_label'] == 'Positive'
        assert 'keywords' in data
        assert 'entities' in data


class TestRuleBasedSentimentAnalyzer:
    """Test rule-based sentiment analyzer"""
    
    @pytest.fixture
    def analyzer(self):
        return RuleBasedSentimentAnalyzer()
    
    @pytest.mark.asyncio
    async def test_positive_sentiment_analysis(self, analyzer):
        """Test positive sentiment detection"""
        text = "Apple reported excellent earnings with strong revenue growth and outstanding performance"
        result = await analyzer.analyze_text(text, "AAPL")
        
        assert result.polarity > 0
        assert result.confidence > 0
        assert result.symbol == "AAPL"
        assert len(result.keywords) > 0
    
    @pytest.mark.asyncio
    async def test_negative_sentiment_analysis(self, analyzer):
        """Test negative sentiment detection"""
        text = "Apple stock crashes due to terrible earnings and awful market conditions"
        result = await analyzer.analyze_text(text, "AAPL")
        
        assert result.polarity < 0
        assert result.confidence > 0
        assert result.symbol == "AAPL"
    
    @pytest.mark.asyncio
    async def test_neutral_sentiment_analysis(self, analyzer):
        """Test neutral sentiment detection"""
        text = "Apple announced a new product launch date for next quarter"
        result = await analyzer.analyze_text(text, "AAPL")
        
        assert abs(result.polarity) < 0.3  # Should be relatively neutral
        assert result.symbol == "AAPL"
    
    @pytest.mark.asyncio
    async def test_negation_handling(self, analyzer):
        """Test negation handling in sentiment analysis"""
        positive_text = "The stock performance is good"
        negative_text = "The stock performance is not good"
        
        positive_result = await analyzer.analyze_text(positive_text, "AAPL")
        negative_result = await analyzer.analyze_text(negative_text, "AAPL")
        
        assert positive_result.polarity > negative_result.polarity
    
    @pytest.mark.asyncio
    async def test_intensifier_handling(self, analyzer):
        """Test intensifier handling"""
        normal_text = "The earnings are good"
        intensified_text = "The earnings are very good"
        
        normal_result = await analyzer.analyze_text(normal_text, "AAPL")
        intensified_result = await analyzer.analyze_text(intensified_text, "AAPL")
        
        assert intensified_result.polarity > normal_result.polarity
    
    @pytest.mark.asyncio
    async def test_batch_analysis(self, analyzer):
        """Test batch sentiment analysis"""
        texts = [
            "Excellent quarterly results with strong growth",
            "Terrible performance and declining revenue",
            "Neutral market conditions with stable outlook"
        ]
        
        results = await analyzer.analyze_batch(texts, "AAPL")
        
        assert len(results) == 3
        assert results[0].polarity > 0  # Positive
        assert results[1].polarity < 0  # Negative
        assert abs(results[2].polarity) < 0.3  # Neutral
    
    def test_entity_extraction(self, analyzer):
        """Test entity extraction from text"""
        text = "Apple Inc and Microsoft Corp are competing in the tech sector. AAPL and MSFT stocks are rising."
        entities = analyzer._extract_entities(text, "AAPL")
        
        assert "AAPL" in entities
        assert len(entities) > 0


class TestMarketSentimentAnalyzer:
    """Test market sentiment analyzer"""
    
    @pytest.fixture
    def analyzer(self):
        return MarketSentimentAnalyzer()
    
    @pytest.mark.asyncio
    async def test_news_sentiment_analysis(self, analyzer):
        """Test news sentiment analysis"""
        news_articles = [
            {
                'id': '1',
                'title': 'Apple Reports Strong Quarterly Earnings',
                'content': 'Apple Inc reported excellent financial results with revenue growth exceeding expectations',
                'timestamp': time.time()
            },
            {
                'id': '2',
                'title': 'Apple Stock Rises on Positive Outlook',
                'content': 'Analysts are bullish on Apple stock following strong performance indicators',
                'timestamp': time.time()
            }
        ]
        
        result = await analyzer.analyze_news_sentiment(news_articles, "AAPL")
        
        assert result.symbol == "AAPL"
        assert result.source == SentimentSource.NEWS
        assert result.polarity > 0  # Should be positive
        assert result.sample_size == 2
    
    @pytest.mark.asyncio
    async def test_social_sentiment_analysis(self, analyzer):
        """Test social media sentiment analysis"""
        social_posts = [
            {
                'id': '1',
                'text': '$AAPL to the moon! Great earnings report 🚀',
                'author': 'trader123',
                'followers': 1000,
                'likes': 50,
                'retweets': 20,
                'timestamp': time.time()
            },
            {
                'id': '2',
                'text': 'AAPL looking strong, buying more shares',
                'author': 'investor456',
                'followers': 5000,
                'likes': 100,
                'retweets': 30,
                'timestamp': time.time()
            }
        ]
        
        result = await analyzer.analyze_social_sentiment(social_posts, "AAPL")
        
        assert result.symbol == "AAPL"
        assert result.source == SentimentSource.SOCIAL_MEDIA
        assert result.polarity > 0  # Should be positive
        assert result.sample_size == 2
    
    @pytest.mark.asyncio
    async def test_symbol_sentiment_tracking(self, analyzer):
        """Test symbol sentiment tracking over time"""
        # Add some sentiment scores
        for i in range(5):
            sentiment = SentimentScore(
                source=SentimentSource.NEWS,
                symbol="AAPL",
                polarity=0.5 + (i * 0.1),  # Increasing sentiment
                confidence=0.8,
                magnitude=0.6,
                timestamp=time.time() - (i * 3600)  # 1 hour apart
            )
            analyzer.add_sentiment(sentiment)
        
        # Get symbol sentiment
        result = await analyzer.get_symbol_sentiment("AAPL", 24)
        
        assert result is not None
        assert result.symbol == "AAPL"
        assert result.sample_size == 5
    
    def test_sentiment_trend_analysis(self, analyzer):
        """Test sentiment trend analysis"""
        # Add sentiments with increasing trend
        base_time = time.time()
        for i in range(10):
            sentiment = SentimentScore(
                source=SentimentSource.NEWS,
                symbol="AAPL",
                polarity=-0.5 + (i * 0.1),  # Improving trend
                confidence=0.8,
                magnitude=0.6,
                timestamp=base_time - ((9 - i) * 3600)  # Chronological order
            )
            analyzer.add_sentiment(sentiment)
        
        trend = analyzer.get_sentiment_trend("AAPL", 24)
        
        assert trend['direction'] == 'improving'
        assert trend['strength'] > 0
        assert trend['sample_size'] == 10


class TestEnhancedSentimentPipeline:
    """Test enhanced sentiment pipeline"""
    
    @pytest.fixture
    def mock_inference_engine(self):
        mock = Mock(spec=InferenceEngine)
        mock.predict = AsyncMock()
        return mock
    
    @pytest.fixture
    def mock_message_bus(self):
        mock = Mock(spec=MessageBus)
        mock.publish = AsyncMock()
        return mock
    
    @pytest.fixture
    def mock_cache_manager(self):
        mock = Mock(spec=CacheManager)
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock()
        return mock
    
    @pytest.fixture
    async def pipeline(self, mock_inference_engine, mock_message_bus, mock_cache_manager):
        pipeline = EnhancedSentimentPipeline(
            inference_engine=mock_inference_engine,
            message_bus=mock_message_bus,
            cache_manager=mock_cache_manager,
            enable_ml=False,  # Use rule-based for testing
            max_concurrent_analyses=2
        )
        await pipeline.start()
        yield pipeline
        await pipeline.stop()
    
    @pytest.mark.asyncio
    async def test_pipeline_startup_shutdown(self, mock_inference_engine, mock_message_bus, mock_cache_manager):
        """Test pipeline startup and shutdown"""
        pipeline = EnhancedSentimentPipeline(
            inference_engine=mock_inference_engine,
            message_bus=mock_message_bus,
            cache_manager=mock_cache_manager,
            max_concurrent_analyses=2
        )
        
        assert not pipeline.running
        
        await pipeline.start()
        assert pipeline.running
        assert len(pipeline.worker_tasks) == 2
        
        await pipeline.stop()
        assert not pipeline.running
    
    @pytest.mark.asyncio
    async def test_content_stream_analysis(self, pipeline):
        """Test content stream analysis"""
        content_stream = [
            {
                'content': 'Apple reports excellent earnings with strong growth',
                'source': 'news',
                'symbol': 'AAPL',
                'metadata': {'author': 'analyst1', 'credibility': 0.9}
            },
            {
                'content': 'AAPL stock looking bearish after poor guidance',
                'source': 'social_media',
                'symbol': 'AAPL',
                'metadata': {'engagement_score': 0.8}
            }
        ]
        
        results = await pipeline.analyze_content_stream(content_stream)
        
        assert len(results) == 2
        assert all(isinstance(r, SentimentScore) for r in results)
        assert results[0].symbol == 'AAPL'
        assert results[1].symbol == 'AAPL'
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self, pipeline):
        """Test performance metrics collection"""
        # Process some content
        content_stream = [
            {
                'content': 'Test content for metrics',
                'source': 'news',
                'symbol': 'TEST',
                'metadata': {}
            }
        ]
        
        await pipeline.analyze_content_stream(content_stream)
        
        metrics = pipeline.get_performance_metrics()
        
        assert 'total_processed' in metrics
        assert 'avg_processing_time_ms' in metrics
        assert 'cache_hit_rate' in metrics
        assert 'is_running' in metrics
        assert metrics['is_running'] == True
    
    def test_cache_key_generation(self, mock_inference_engine, mock_message_bus, mock_cache_manager):
        """Test cache key generation"""
        pipeline = EnhancedSentimentPipeline(
            inference_engine=mock_inference_engine,
            message_bus=mock_message_bus,
            cache_manager=mock_cache_manager
        )
        
        key1 = pipeline._generate_cache_key("test content", "AAPL", SentimentSource.NEWS)
        key2 = pipeline._generate_cache_key("test content", "AAPL", SentimentSource.NEWS)
        key3 = pipeline._generate_cache_key("different content", "AAPL", SentimentSource.NEWS)
        
        assert key1 == key2  # Same content should generate same key
        assert key1 != key3  # Different content should generate different key
        assert key1.startswith("sentiment:")


class TestSentimentAnomalyDetector:
    """Test sentiment anomaly detector"""
    
    @pytest.fixture
    def detector(self):
        return SentimentAnomalyDetector()
    
    @pytest.mark.asyncio
    async def test_anomaly_detection_insufficient_baseline(self, detector):
        """Test anomaly detection with insufficient baseline"""
        sentiment = SentimentScore(
            source=SentimentSource.NEWS,
            symbol="AAPL",
            polarity=0.8,
            confidence=0.9,
            magnitude=0.8
        )
        
        anomaly_score = await detector.detect_anomaly(sentiment)
        assert anomaly_score == 0.0  # Should return 0 for insufficient baseline
    
    @pytest.mark.asyncio
    async def test_anomaly_detection_with_baseline(self, detector):
        """Test anomaly detection with sufficient baseline"""
        symbol = "AAPL"
        
        # Build baseline with normal sentiments
        for i in range(15):
            normal_sentiment = SentimentScore(
                source=SentimentSource.NEWS,
                symbol=symbol,
                polarity=0.1 + (i * 0.05),  # Gradual increase
                confidence=0.8,
                magnitude=0.6
            )
            await detector.detect_anomaly(normal_sentiment)
        
        # Test anomalous sentiment
        anomalous_sentiment = SentimentScore(
            source=SentimentSource.NEWS,
            symbol=symbol,
            polarity=0.95,  # Very high compared to baseline
            confidence=0.9,
            magnitude=0.9
        )
        
        anomaly_score = await detector.detect_anomaly(anomalous_sentiment)
        assert anomaly_score > 0.3  # Should detect as anomalous
    
    @pytest.mark.asyncio
    async def test_baseline_management(self, detector):
        """Test baseline management and size limits"""
        symbol = "AAPL"
        
        # Add more sentiments than max baseline size
        for i in range(150):  # More than max_baseline_size (100)
            sentiment = SentimentScore(
                source=SentimentSource.NEWS,
                symbol=symbol,
                polarity=0.5,
                confidence=0.8,
                magnitude=0.6
            )
            await detector.detect_anomaly(sentiment)
        
        # Check that baseline size is limited
        assert len(detector.baseline_sentiments[symbol]) <= detector.max_baseline_size


class TestIntegration:
    """Integration tests for sentiment analysis components"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_sentiment_analysis(self):
        """Test end-to-end sentiment analysis workflow"""
        # Create components
        rule_analyzer = RuleBasedSentimentAnalyzer()
        market_analyzer = MarketSentimentAnalyzer()
        anomaly_detector = SentimentAnomalyDetector()
        
        # Test content
        test_content = [
            "Apple reports record-breaking quarterly earnings with exceptional growth",
            "AAPL stock surges on positive analyst upgrades and strong outlook",
            "Apple faces challenges but maintains solid market position"
        ]
        
        # Analyze content
        results = []
        for content in test_content:
            sentiment = await rule_analyzer.analyze_text(content, "AAPL")
            market_analyzer.add_sentiment(sentiment)
            
            anomaly_score = await anomaly_detector.detect_anomaly(sentiment)
            sentiment.anomaly_score = anomaly_score
            
            results.append(sentiment)
        
        # Verify results
        assert len(results) == 3
        assert all(r.symbol == "AAPL" for r in results)
        assert results[0].polarity > 0  # Positive
        assert results[1].polarity > 0  # Positive
        
        # Test market analysis
        symbol_sentiment = await market_analyzer.get_symbol_sentiment("AAPL", 24)
        assert symbol_sentiment is not None
        assert symbol_sentiment.sample_size == 3
        
        # Test trend analysis
        trend = market_analyzer.get_sentiment_trend("AAPL", 24)
        assert trend['sample_size'] == 3
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self):
        """Test sentiment analysis performance under load"""
        analyzer = RuleBasedSentimentAnalyzer()
        
        # Generate test content
        test_texts = [
            f"Test sentiment analysis content number {i} with positive outlook"
            for i in range(100)
        ]
        
        start_time = time.time()
        
        # Analyze in batch
        results = await analyzer.analyze_batch(test_texts, "TEST")
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify performance
        assert len(results) == 100
        assert processing_time < 5.0  # Should complete within 5 seconds
        assert all(isinstance(r, SentimentScore) for r in results)
        
        # Calculate average processing time per item
        avg_time_per_item = processing_time / 100
        assert avg_time_per_item < 0.05  # Less than 50ms per item


if __name__ == "__main__":
    # Run basic tests
    import sys
    
    async def run_basic_tests():
        """Run basic functionality tests"""
        print("Running basic sentiment analysis tests...")
        
        # Test rule-based analyzer
        analyzer = RuleBasedSentimentAnalyzer()
        
        test_cases = [
            ("Apple reports excellent earnings with strong growth", "AAPL", "positive"),
            ("Apple stock crashes due to terrible market conditions", "AAPL", "negative"),
            ("Apple announces new product launch date", "AAPL", "neutral")
        ]
        
        for text, symbol, expected in test_cases:
            result = await analyzer.analyze_text(text, symbol)
            
            if expected == "positive":
                assert result.polarity > 0, f"Expected positive sentiment for: {text}"
            elif expected == "negative":
                assert result.polarity < 0, f"Expected negative sentiment for: {text}"
            else:  # neutral
                assert abs(result.polarity) < 0.3, f"Expected neutral sentiment for: {text}"
            
            print(f"✓ {expected.capitalize()} sentiment detected: {result.polarity:.2f}")
        
        # Test market analyzer
        market_analyzer = MarketSentimentAnalyzer()
        
        news_articles = [
            {
                'title': 'Apple Reports Strong Earnings',
                'content': 'Apple Inc exceeded expectations with excellent quarterly results',
                'timestamp': time.time()
            }
        ]
        
        news_sentiment = await market_analyzer.analyze_news_sentiment(news_articles, "AAPL")
        print(f"✓ News sentiment analysis: {news_sentiment.polarity:.2f}")
        
        print("All basic tests passed!")
    
    # Run the tests
    asyncio.run(run_basic_tests())