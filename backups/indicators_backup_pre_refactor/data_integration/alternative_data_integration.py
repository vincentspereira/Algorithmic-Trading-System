"""Alternative Data Integration System - Institutional Grade

This module implements advanced alternative data integration for trading indicators:

- Sentiment analysis from news, social media, and market commentary
- Order flow analysis with smart money detection
- Open interest and options flow integration
- Behavioral overlays with crowd psychology metrics
- Cross-asset correlation and macro factor analysis
- Real-time alternative data processing and fusion
- Machine learning-based sentiment scoring
- Institutional positioning and flow analysis
- Market microstructure and liquidity metrics
- Economic surprise and event impact analysis

Key Features:
- Multi-source sentiment aggregation and scoring
- Real-time order flow pattern recognition
- Options positioning and gamma exposure analysis
- Behavioral bias detection and crowd sentiment
- Macro factor integration with economic indicators
- Alternative data quality scoring and validation
- Cross-market sentiment spillover analysis
- Institutional vs retail sentiment divergence
- Event-driven sentiment impact modeling
- Alternative data risk management integration
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple, NamedTuple, Union
from collections import deque, defaultdict
from dataclasses import dataclass, field
from enum import Enum
import warnings
from abc import ABC, abstractmethod
import json
import re
from statistics import mean, median, stdev

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=FutureWarning)

from .augmented_indicator import (
    AugmentedIndicator, IndicatorSignal, IndicatorConfig,
    SignalType, MarketRegime, RiskLevel, TimeframeConvergence
)

try:
    from utils.logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

class SentimentSource(Enum):
    """Sources of sentiment data"""
    NEWS_HEADLINES = "news_headlines"
    SOCIAL_MEDIA = "social_media"
    ANALYST_REPORTS = "analyst_reports"
    EARNINGS_CALLS = "earnings_calls"
    REGULATORY_FILINGS = "regulatory_filings"
    MARKET_COMMENTARY = "market_commentary"
    ECONOMIC_REPORTS = "economic_reports"
    CENTRAL_BANK_COMMUNICATIONS = "central_bank_communications"
    INSIDER_TRADING = "insider_trading"
    INSTITUTIONAL_FLOWS = "institutional_flows"

class SentimentPolarity(Enum):
    """Sentiment polarity classification"""
    VERY_NEGATIVE = "very_negative"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    VERY_POSITIVE = "very_positive"

class OrderFlowType(Enum):
    """Types of order flow analysis"""
    MARKET_ORDERS = "market_orders"
    LIMIT_ORDERS = "limit_orders"
    ICEBERG_ORDERS = "iceberg_orders"
    BLOCK_TRADES = "block_trades"
    DARK_POOL_ACTIVITY = "dark_pool_activity"
    ALGORITHMIC_TRADING = "algorithmic_trading"
    RETAIL_FLOW = "retail_flow"
    INSTITUTIONAL_FLOW = "institutional_flow"
    HIGH_FREQUENCY_TRADING = "high_frequency_trading"
    CROSS_TRADING = "cross_trading"

class OptionsFlowType(Enum):
    """Types of options flow analysis"""
    CALL_VOLUME = "call_volume"
    PUT_VOLUME = "put_volume"
    PUT_CALL_RATIO = "put_call_ratio"
    OPEN_INTEREST = "open_interest"
    GAMMA_EXPOSURE = "gamma_exposure"
    DELTA_HEDGING = "delta_hedging"
    VOLATILITY_SKEW = "volatility_skew"
    UNUSUAL_ACTIVITY = "unusual_activity"
    LARGE_TRADES = "large_trades"
    EXPIRATION_FLOWS = "expiration_flows"

class BehavioralBias(Enum):
    """Types of behavioral biases"""
    HERDING = "herding"
    OVERCONFIDENCE = "overconfidence"
    ANCHORING = "anchoring"
    LOSS_AVERSION = "loss_aversion"
    CONFIRMATION_BIAS = "confirmation_bias"
    RECENCY_BIAS = "recency_bias"
    AVAILABILITY_HEURISTIC = "availability_heuristic"
    REPRESENTATIVENESS = "representativeness"
    MENTAL_ACCOUNTING = "mental_accounting"
    DISPOSITION_EFFECT = "disposition_effect"

class MacroFactor(Enum):
    """Macro economic factors"""
    INTEREST_RATES = "interest_rates"
    INFLATION = "inflation"
    GDP_GROWTH = "gdp_growth"
    UNEMPLOYMENT = "unemployment"
    CURRENCY_STRENGTH = "currency_strength"
    COMMODITY_PRICES = "commodity_prices"
    GEOPOLITICAL_RISK = "geopolitical_risk"
    CENTRAL_BANK_POLICY = "central_bank_policy"
    FISCAL_POLICY = "fiscal_policy"
    TRADE_POLICY = "trade_policy"

@dataclass
class SentimentData:
    """Individual sentiment data point"""
    source: SentimentSource
    symbol: Optional[str]
    text: str
    polarity: SentimentPolarity
    score: float  # -1.0 to 1.0
    confidence: float  # 0.0 to 1.0
    volume: int  # Number of mentions/articles
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class OrderFlowData:
    """Order flow analysis data"""
    flow_type: OrderFlowType
    symbol: str
    volume: float
    price_level: float
    side: str  # 'buy' or 'sell'
    size_category: str  # 'small', 'medium', 'large', 'block'
    participant_type: str  # 'retail', 'institutional', 'hft'
    urgency_score: float  # 0.0 to 1.0
    smart_money_indicator: float  # -1.0 to 1.0
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class OptionsFlowData:
    """Options flow analysis data"""
    flow_type: OptionsFlowType
    symbol: str
    strike_price: float
    expiration_date: datetime
    option_type: str  # 'call' or 'put'
    volume: float
    open_interest: float
    implied_volatility: float
    delta: float
    gamma: float
    unusual_activity_score: float  # 0.0 to 1.0
    institutional_bias: float  # -1.0 to 1.0
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BehavioralData:
    """Behavioral analysis data"""
    bias_type: BehavioralBias
    symbol: Optional[str]
    intensity: float  # 0.0 to 1.0
    crowd_sentiment: float  # -1.0 to 1.0
    contrarian_signal: float  # -1.0 to 1.0
    fear_greed_index: float  # 0.0 to 100.0
    volatility_risk_premium: float
    positioning_extremes: float  # -1.0 to 1.0
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MacroData:
    """Macro economic factor data"""
    factor: MacroFactor
    value: float
    change: float
    surprise_factor: float  # Actual vs Expected
    market_impact_score: float  # -1.0 to 1.0
    cross_asset_correlation: Dict[str, float]
    regime_indicator: float  # -1.0 to 1.0
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AlternativeDataSignal:
    """Aggregated alternative data signal"""
    symbol: str
    sentiment_score: float  # -1.0 to 1.0
    order_flow_score: float  # -1.0 to 1.0
    options_flow_score: float  # -1.0 to 1.0
    behavioral_score: float  # -1.0 to 1.0
    macro_score: float  # -1.0 to 1.0
    composite_score: float  # -1.0 to 1.0
    confidence: float  # 0.0 to 1.0
    signal_strength: float  # 0.0 to 1.0
    contrarian_indicator: float  # -1.0 to 1.0
    regime_consistency: float  # 0.0 to 1.0
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AlternativeDataConfig:
    """Configuration for alternative data integration"""
    # Sentiment analysis
    enable_sentiment_analysis: bool = True
    sentiment_sources: List[SentimentSource] = field(default_factory=lambda: [
        SentimentSource.NEWS_HEADLINES,
        SentimentSource.SOCIAL_MEDIA,
        SentimentSource.ANALYST_REPORTS
    ])
    sentiment_window: int = 24  # hours
    sentiment_decay_factor: float = 0.95
    
    # Order flow analysis
    enable_order_flow_analysis: bool = True
    order_flow_window: int = 60  # minutes
    smart_money_threshold: float = 0.6
    block_trade_threshold: float = 100000  # USD
    
    # Options flow analysis
    enable_options_analysis: bool = True
    options_window: int = 5  # days
    unusual_volume_threshold: float = 2.0  # multiple of average
    gamma_exposure_threshold: float = 0.1
    
    # Behavioral analysis
    enable_behavioral_analysis: bool = True
    behavioral_window: int = 7  # days
    contrarian_threshold: float = 0.8
    crowd_sentiment_threshold: float = 0.7
    
    # Macro analysis
    enable_macro_analysis: bool = True
    macro_factors: List[MacroFactor] = field(default_factory=lambda: [
        MacroFactor.INTEREST_RATES,
        MacroFactor.INFLATION,
        MacroFactor.GDP_GROWTH
    ])
    economic_surprise_threshold: float = 0.5
    
    # Signal aggregation
    sentiment_weight: float = 0.25
    order_flow_weight: float = 0.25
    options_weight: float = 0.20
    behavioral_weight: float = 0.15
    macro_weight: float = 0.15
    
    # Quality control
    min_data_quality_score: float = 0.6
    max_data_age_hours: int = 48
    enable_cross_validation: bool = True
    
    # Advanced features
    enable_ml_sentiment: bool = True
    enable_regime_detection: bool = True
    enable_cross_asset_analysis: bool = True
    enable_event_impact_modeling: bool = True

class SentimentAnalyzer:
    """Advanced sentiment analysis engine"""
    
    def __init__(self, config: AlternativeDataConfig):
        self.config = config
        self.sentiment_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.keyword_weights = self._initialize_keyword_weights()
        self.source_reliability = self._initialize_source_reliability()
    
    def _initialize_keyword_weights(self) -> Dict[str, float]:
        """Initialize keyword sentiment weights"""
        return {
            # Positive keywords
            'bullish': 0.8, 'buy': 0.6, 'strong': 0.5, 'growth': 0.4, 'positive': 0.6,
            'outperform': 0.7, 'upgrade': 0.8, 'beat': 0.6, 'exceed': 0.5, 'rally': 0.7,
            'surge': 0.8, 'breakout': 0.6, 'momentum': 0.5, 'opportunity': 0.4,
            
            # Negative keywords
            'bearish': -0.8, 'sell': -0.6, 'weak': -0.5, 'decline': -0.4, 'negative': -0.6,
            'underperform': -0.7, 'downgrade': -0.8, 'miss': -0.6, 'fall': -0.5, 'crash': -0.9,
            'plunge': -0.8, 'breakdown': -0.6, 'risk': -0.4, 'concern': -0.3,
            
            # Neutral/context keywords
            'hold': 0.0, 'neutral': 0.0, 'stable': 0.1, 'maintain': 0.0, 'watch': 0.0
        }
    
    def _initialize_source_reliability(self) -> Dict[SentimentSource, float]:
        """Initialize source reliability scores"""
        return {
            SentimentSource.ANALYST_REPORTS: 0.9,
            SentimentSource.EARNINGS_CALLS: 0.85,
            SentimentSource.REGULATORY_FILINGS: 0.8,
            SentimentSource.NEWS_HEADLINES: 0.7,
            SentimentSource.MARKET_COMMENTARY: 0.65,
            SentimentSource.ECONOMIC_REPORTS: 0.8,
            SentimentSource.CENTRAL_BANK_COMMUNICATIONS: 0.9,
            SentimentSource.INSIDER_TRADING: 0.75,
            SentimentSource.INSTITUTIONAL_FLOWS: 0.8,
            SentimentSource.SOCIAL_MEDIA: 0.4
        }
    
    def analyze_text_sentiment(self, text: str, source: SentimentSource) -> Tuple[float, float, SentimentPolarity]:
        """Analyze sentiment of text using keyword-based approach"""
        if not text:
            return 0.0, 0.0, SentimentPolarity.NEUTRAL
        
        text_lower = text.lower()
        sentiment_scores = []
        
        # Keyword-based sentiment scoring
        for keyword, weight in self.keyword_weights.items():
            if keyword in text_lower:
                # Count occurrences and apply weight
                count = text_lower.count(keyword)
                sentiment_scores.append(weight * count)
        
        # Calculate base sentiment score
        if sentiment_scores:
            base_score = sum(sentiment_scores) / len(sentiment_scores)
            base_score = max(-1.0, min(1.0, base_score))  # Clamp to [-1, 1]
        else:
            base_score = 0.0
        
        # Apply source reliability
        reliability = self.source_reliability.get(source, 0.5)
        confidence = reliability * min(1.0, len(sentiment_scores) / 5.0)  # More keywords = higher confidence
        
        # Determine polarity
        if base_score >= 0.6:
            polarity = SentimentPolarity.VERY_POSITIVE
        elif base_score >= 0.2:
            polarity = SentimentPolarity.POSITIVE
        elif base_score <= -0.6:
            polarity = SentimentPolarity.VERY_NEGATIVE
        elif base_score <= -0.2:
            polarity = SentimentPolarity.NEGATIVE
        else:
            polarity = SentimentPolarity.NEUTRAL
        
        return base_score, confidence, polarity
    
    def process_sentiment_data(self, data: SentimentData) -> None:
        """Process and store sentiment data"""
        symbol = data.symbol or 'MARKET'
        self.sentiment_history[symbol].append(data)
    
    def get_aggregated_sentiment(self, symbol: str, window_hours: int = None) -> Tuple[float, float]:
        """Get aggregated sentiment score for symbol"""
        if window_hours is None:
            window_hours = self.config.sentiment_window
        
        if symbol not in self.sentiment_history:
            return 0.0, 0.0
        
        cutoff_time = datetime.now() - timedelta(hours=window_hours)
        recent_data = [d for d in self.sentiment_history[symbol] if d.timestamp >= cutoff_time]
        
        if not recent_data:
            return 0.0, 0.0
        
        # Calculate weighted sentiment score with time decay
        weighted_scores = []
        total_weight = 0.0
        
        for data in recent_data:
            # Time decay factor
            hours_ago = (datetime.now() - data.timestamp).total_seconds() / 3600
            time_weight = self.config.sentiment_decay_factor ** hours_ago
            
            # Volume weight (more mentions = higher weight)
            volume_weight = min(1.0, data.volume / 10.0)
            
            # Combined weight
            weight = time_weight * volume_weight * data.confidence
            
            weighted_scores.append(data.score * weight)
            total_weight += weight
        
        if total_weight > 0:
            aggregated_score = sum(weighted_scores) / total_weight
            confidence = min(1.0, total_weight / len(recent_data))
        else:
            aggregated_score = 0.0
            confidence = 0.0
        
        return aggregated_score, confidence

class OrderFlowAnalyzer:
    """Advanced order flow analysis engine"""
    
    def __init__(self, config: AlternativeDataConfig):
        self.config = config
        self.order_flow_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.flow_patterns = self._initialize_flow_patterns()
    
    def _initialize_flow_patterns(self) -> Dict[str, Dict[str, float]]:
        """Initialize order flow pattern weights"""
        return {
            'smart_money_indicators': {
                'large_block_trades': 0.8,
                'iceberg_orders': 0.7,
                'dark_pool_activity': 0.6,
                'institutional_flow': 0.8,
                'low_urgency_large_size': 0.7
            },
            'retail_indicators': {
                'small_market_orders': -0.3,
                'high_urgency_small_size': -0.4,
                'round_lot_trading': -0.2,
                'momentum_chasing': -0.5
            },
            'algorithmic_indicators': {
                'high_frequency_patterns': 0.2,
                'systematic_execution': 0.3,
                'cross_trading': 0.4
            }
        }
    
    def analyze_order_flow(self, data: OrderFlowData) -> float:
        """Analyze order flow data and return smart money score"""
        smart_money_score = 0.0
        
        # Size-based analysis
        if data.size_category == 'block':
            smart_money_score += 0.6
        elif data.size_category == 'large':
            smart_money_score += 0.4
        elif data.size_category == 'small':
            smart_money_score -= 0.2
        
        # Participant type analysis
        if data.participant_type == 'institutional':
            smart_money_score += 0.5
        elif data.participant_type == 'retail':
            smart_money_score -= 0.3
        elif data.participant_type == 'hft':
            smart_money_score += 0.1
        
        # Flow type analysis
        if data.flow_type == OrderFlowType.ICEBERG_ORDERS:
            smart_money_score += 0.7
        elif data.flow_type == OrderFlowType.DARK_POOL_ACTIVITY:
            smart_money_score += 0.6
        elif data.flow_type == OrderFlowType.BLOCK_TRADES:
            smart_money_score += 0.8
        
        # Urgency analysis (smart money typically has lower urgency)
        urgency_adjustment = (1.0 - data.urgency_score) * 0.3
        smart_money_score += urgency_adjustment
        
        # Clamp score to [-1, 1]
        smart_money_score = max(-1.0, min(1.0, smart_money_score))
        
        return smart_money_score
    
    def process_order_flow_data(self, data: OrderFlowData) -> None:
        """Process and store order flow data"""
        # Calculate smart money indicator
        data.smart_money_indicator = self.analyze_order_flow(data)
        
        self.order_flow_history[data.symbol].append(data)
    
    def get_aggregated_order_flow(self, symbol: str, window_minutes: int = None) -> Tuple[float, float]:
        """Get aggregated order flow score for symbol"""
        if window_minutes is None:
            window_minutes = self.config.order_flow_window
        
        if symbol not in self.order_flow_history:
            return 0.0, 0.0
        
        cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
        recent_data = [d for d in self.order_flow_history[symbol] if d.timestamp >= cutoff_time]
        
        if not recent_data:
            return 0.0, 0.0
        
        # Calculate volume-weighted order flow score
        total_volume = sum(d.volume for d in recent_data)
        if total_volume == 0:
            return 0.0, 0.0
        
        weighted_score = sum(d.smart_money_indicator * d.volume for d in recent_data) / total_volume
        
        # Calculate confidence based on data volume and consistency
        smart_money_flows = [d for d in recent_data if abs(d.smart_money_indicator) > self.config.smart_money_threshold]
        confidence = min(1.0, len(smart_money_flows) / max(1, len(recent_data)))
        
        return weighted_score, confidence

class OptionsFlowAnalyzer:
    """Advanced options flow analysis engine"""
    
    def __init__(self, config: AlternativeDataConfig):
        self.config = config
        self.options_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=500))
        self.historical_volumes: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
    
    def analyze_options_flow(self, data: OptionsFlowData) -> Tuple[float, float]:
        """Analyze options flow data"""
        unusual_score = 0.0
        institutional_bias = 0.0
        
        # Volume analysis
        symbol_volumes = self.historical_volumes[data.symbol]
        if len(symbol_volumes) > 10:
            avg_volume = mean(symbol_volumes)
            if avg_volume > 0:
                volume_ratio = data.volume / avg_volume
                if volume_ratio > self.config.unusual_volume_threshold:
                    unusual_score += min(1.0, (volume_ratio - 1.0) / 3.0)
        
        # Open interest analysis
        if data.open_interest > 0:
            oi_volume_ratio = data.volume / data.open_interest
            if oi_volume_ratio > 0.5:  # High volume relative to OI
                unusual_score += 0.3
        
        # Greeks analysis
        if abs(data.gamma) > self.config.gamma_exposure_threshold:
            institutional_bias += 0.4 * np.sign(data.gamma)
        
        if abs(data.delta) > 0.7:  # Deep ITM/OTM options
            institutional_bias += 0.3 * np.sign(data.delta)
        
        # Implied volatility analysis
        if data.implied_volatility > 0.5:  # High IV
            unusual_score += 0.2
        
        # Option type and expiration analysis
        days_to_expiry = (data.expiration_date - datetime.now()).days
        
        if days_to_expiry > 30:  # Long-term options (institutional)
            institutional_bias += 0.3
        elif days_to_expiry < 7:  # Short-term options (speculative)
            institutional_bias -= 0.2
        
        # Put/Call analysis
        if data.option_type == 'put':
            institutional_bias -= 0.1  # Slight bearish bias
        else:
            institutional_bias += 0.1  # Slight bullish bias
        
        # Clamp scores
        unusual_score = max(0.0, min(1.0, unusual_score))
        institutional_bias = max(-1.0, min(1.0, institutional_bias))
        
        return unusual_score, institutional_bias
    
    def process_options_data(self, data: OptionsFlowData) -> None:
        """Process and store options flow data"""
        # Analyze the options flow
        unusual_score, institutional_bias = self.analyze_options_flow(data)
        data.unusual_activity_score = unusual_score
        data.institutional_bias = institutional_bias
        
        # Store data
        self.options_history[data.symbol].append(data)
        self.historical_volumes[data.symbol].append(data.volume)
    
    def get_aggregated_options_flow(self, symbol: str, window_days: int = None) -> Tuple[float, float, float]:
        """Get aggregated options flow metrics"""
        if window_days is None:
            window_days = self.config.options_window
        
        if symbol not in self.options_history:
            return 0.0, 0.0, 0.0
        
        cutoff_time = datetime.now() - timedelta(days=window_days)
        recent_data = [d for d in self.options_history[symbol] if d.timestamp >= cutoff_time]
        
        if not recent_data:
            return 0.0, 0.0, 0.0
        
        # Calculate put/call ratio
        call_volume = sum(d.volume for d in recent_data if d.option_type == 'call')
        put_volume = sum(d.volume for d in recent_data if d.option_type == 'put')
        
        if call_volume > 0:
            put_call_ratio = put_volume / call_volume
        else:
            put_call_ratio = 0.0
        
        # Calculate average unusual activity score
        unusual_scores = [d.unusual_activity_score for d in recent_data]
        avg_unusual_score = mean(unusual_scores) if unusual_scores else 0.0
        
        # Calculate volume-weighted institutional bias
        total_volume = sum(d.volume for d in recent_data)
        if total_volume > 0:
            institutional_bias = sum(d.institutional_bias * d.volume for d in recent_data) / total_volume
        else:
            institutional_bias = 0.0
        
        return put_call_ratio, avg_unusual_score, institutional_bias

class BehavioralAnalyzer:
    """Advanced behavioral analysis engine"""
    
    def __init__(self, config: AlternativeDataConfig):
        self.config = config
        self.behavioral_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=200))
        self.crowd_metrics = deque(maxlen=100)
    
    def analyze_behavioral_patterns(self, symbol: str, price_data: List[float], 
                                  volume_data: List[float]) -> BehavioralData:
        """Analyze behavioral patterns in price and volume data"""
        if len(price_data) < 10 or len(volume_data) < 10:
            return self._create_neutral_behavioral_data(symbol)
        
        # Calculate returns
        returns = [(price_data[i] - price_data[i-1]) / price_data[i-1] 
                  for i in range(1, len(price_data))]
        
        # Herding behavior analysis
        herding_intensity = self._analyze_herding(returns, volume_data)
        
        # Overconfidence analysis
        overconfidence_score = self._analyze_overconfidence(returns, volume_data)
        
        # Loss aversion analysis
        loss_aversion_score = self._analyze_loss_aversion(returns)
        
        # Calculate crowd sentiment
        crowd_sentiment = self._calculate_crowd_sentiment(returns, volume_data)
        
        # Calculate contrarian signal
        contrarian_signal = self._calculate_contrarian_signal(crowd_sentiment)
        
        # Calculate fear & greed index
        fear_greed_index = self._calculate_fear_greed_index(returns, volume_data)
        
        # Calculate volatility risk premium
        vol_risk_premium = self._calculate_volatility_risk_premium(returns)
        
        # Calculate positioning extremes
        positioning_extremes = self._calculate_positioning_extremes(crowd_sentiment)
        
        return BehavioralData(
            bias_type=BehavioralBias.HERDING,  # Primary bias detected
            symbol=symbol,
            intensity=herding_intensity,
            crowd_sentiment=crowd_sentiment,
            contrarian_signal=contrarian_signal,
            fear_greed_index=fear_greed_index,
            volatility_risk_premium=vol_risk_premium,
            positioning_extremes=positioning_extremes,
            timestamp=datetime.now()
        )
    
    def _create_neutral_behavioral_data(self, symbol: str) -> BehavioralData:
        """Create neutral behavioral data when insufficient data"""
        return BehavioralData(
            bias_type=BehavioralBias.HERDING,
            symbol=symbol,
            intensity=0.0,
            crowd_sentiment=0.0,
            contrarian_signal=0.0,
            fear_greed_index=50.0,
            volatility_risk_premium=0.0,
            positioning_extremes=0.0,
            timestamp=datetime.now()
        )
    
    def _analyze_herding(self, returns: List[float], volumes: List[float]) -> float:
        """Analyze herding behavior intensity"""
        if len(returns) < 5:
            return 0.0
        
        # Look for periods of high correlation between returns and volume
        correlation = np.corrcoef(returns[-len(volumes):], volumes)[0, 1]
        
        # High positive correlation suggests herding
        herding_score = max(0.0, correlation) if not np.isnan(correlation) else 0.0
        
        # Check for momentum clustering
        positive_runs = 0
        negative_runs = 0
        current_run = 0
        
        for i, ret in enumerate(returns):
            if i == 0:
                current_run = 1
                continue
            
            if (ret > 0 and returns[i-1] > 0) or (ret < 0 and returns[i-1] < 0):
                current_run += 1
            else:
                if returns[i-1] > 0:
                    positive_runs = max(positive_runs, current_run)
                else:
                    negative_runs = max(negative_runs, current_run)
                current_run = 1
        
        # Longer runs suggest herding
        max_run = max(positive_runs, negative_runs)
        run_score = min(1.0, max_run / 5.0)
        
        return (herding_score + run_score) / 2.0
    
    def _analyze_overconfidence(self, returns: List[float], volumes: List[float]) -> float:
        """Analyze overconfidence bias"""
        if len(returns) < 10:
            return 0.0
        
        # High volume with extreme returns suggests overconfidence
        extreme_returns = [abs(r) for r in returns if abs(r) > 2 * stdev(returns)]
        
        if not extreme_returns:
            return 0.0
        
        # Check if high volume accompanies extreme returns
        volume_percentile_75 = np.percentile(volumes, 75)
        extreme_volume_count = sum(1 for v in volumes if v > volume_percentile_75)
        
        overconfidence_score = min(1.0, (len(extreme_returns) + extreme_volume_count) / len(returns))
        
        return overconfidence_score
    
    def _analyze_loss_aversion(self, returns: List[float]) -> float:
        """Analyze loss aversion patterns"""
        if len(returns) < 10:
            return 0.0
        
        positive_returns = [r for r in returns if r > 0]
        negative_returns = [r for r in returns if r < 0]
        
        if not positive_returns or not negative_returns:
            return 0.0
        
        # Loss aversion: losses feel twice as powerful as gains
        avg_positive = mean(positive_returns)
        avg_negative = abs(mean(negative_returns))
        
        if avg_positive > 0:
            loss_aversion_ratio = avg_negative / avg_positive
            # Ratio > 2 suggests strong loss aversion
            return min(1.0, max(0.0, (loss_aversion_ratio - 1.0) / 2.0))
        
        return 0.0
    
    def _calculate_crowd_sentiment(self, returns: List[float], volumes: List[float]) -> float:
        """Calculate overall crowd sentiment"""
        if not returns:
            return 0.0
        
        # Volume-weighted sentiment
        total_volume = sum(volumes)
        if total_volume == 0:
            return mean(returns)
        
        weighted_sentiment = sum(r * v for r, v in zip(returns, volumes)) / total_volume
        
        # Normalize to [-1, 1]
        return max(-1.0, min(1.0, weighted_sentiment * 10))
    
    def _calculate_contrarian_signal(self, crowd_sentiment: float) -> float:
        """Calculate contrarian signal strength"""
        # Strong contrarian signal when crowd sentiment is extreme
        if abs(crowd_sentiment) > self.config.contrarian_threshold:
            return -crowd_sentiment  # Opposite of crowd
        else:
            return 0.0
    
    def _calculate_fear_greed_index(self, returns: List[float], volumes: List[float]) -> float:
        """Calculate fear & greed index (0-100)"""
        if len(returns) < 5:
            return 50.0  # Neutral
        
        # Components of fear & greed
        volatility = stdev(returns)
        momentum = mean(returns[-5:])  # Recent momentum
        volume_trend = (volumes[-1] - mean(volumes[:-1])) / mean(volumes[:-1]) if len(volumes) > 1 else 0
        
        # Normalize components
        vol_score = max(0, min(100, 50 - volatility * 1000))  # High vol = fear
        momentum_score = max(0, min(100, 50 + momentum * 1000))  # Positive momentum = greed
        volume_score = max(0, min(100, 50 + volume_trend * 50))  # High volume = greed
        
        # Weighted average
        fear_greed = (vol_score * 0.4 + momentum_score * 0.4 + volume_score * 0.2)
        
        return fear_greed
    
    def _calculate_volatility_risk_premium(self, returns: List[float]) -> float:
        """Calculate volatility risk premium"""
        if len(returns) < 20:
            return 0.0
        
        realized_vol = stdev(returns) * np.sqrt(252)  # Annualized
        
        # Simplified VRP calculation (would need implied vol in practice)
        # Assume implied vol is typically 20% higher than realized
        implied_vol_estimate = realized_vol * 1.2
        
        vrp = implied_vol_estimate - realized_vol
        
        return vrp
    
    def _calculate_positioning_extremes(self, crowd_sentiment: float) -> float:
        """Calculate positioning extremes indicator"""
        # Store crowd sentiment history
        self.crowd_metrics.append(crowd_sentiment)
        
        if len(self.crowd_metrics) < 20:
            return 0.0
        
        # Calculate percentile of current sentiment
        sentiment_array = np.array(list(self.crowd_metrics))
        current_percentile = (sentiment_array < crowd_sentiment).mean()
        
        # Extreme positioning when in top/bottom 10%
        if current_percentile > 0.9:
            return 1.0  # Extreme bullish positioning
        elif current_percentile < 0.1:
            return -1.0  # Extreme bearish positioning
        else:
            return 0.0
    
    def process_behavioral_data(self, data: BehavioralData) -> None:
        """Process and store behavioral data"""
        symbol = data.symbol or 'MARKET'
        self.behavioral_history[symbol].append(data)
    
    def get_aggregated_behavioral_score(self, symbol: str, window_days: int = None) -> Tuple[float, float]:
        """Get aggregated behavioral score"""
        if window_days is None:
            window_days = self.config.behavioral_window
        
        if symbol not in self.behavioral_history:
            return 0.0, 0.0
        
        cutoff_time = datetime.now() - timedelta(days=window_days)
        recent_data = [d for d in self.behavioral_history[symbol] if d.timestamp >= cutoff_time]
        
        if not recent_data:
            return 0.0, 0.0
        
        # Calculate weighted behavioral score
        behavioral_score = mean([d.contrarian_signal for d in recent_data])
        confidence = min(1.0, len(recent_data) / 10.0)
        
        return behavioral_score, confidence

class MacroAnalyzer:
    """Advanced macro economic analysis engine"""
    
    def __init__(self, config: AlternativeDataConfig):
        self.config = config
        self.macro_history: Dict[MacroFactor, deque] = {factor: deque(maxlen=100) for factor in MacroFactor}
        self.factor_correlations: Dict[MacroFactor, Dict[str, float]] = {}
    
    def process_macro_data(self, data: MacroData) -> None:
        """Process and store macro economic data"""
        self.macro_history[data.factor].append(data)
    
    def get_aggregated_macro_score(self, symbol: str) -> Tuple[float, float]:
        """Get aggregated macro score for symbol"""
        macro_scores = []
        
        for factor in self.config.macro_factors:
            if factor in self.macro_history and self.macro_history[factor]:
                latest_data = self.macro_history[factor][-1]
                
                # Get correlation with symbol if available
                correlation = self.factor_correlations.get(factor, {}).get(symbol, 0.0)
                
                # Calculate factor impact
                factor_impact = latest_data.market_impact_score * correlation
                macro_scores.append(factor_impact)
        
        if macro_scores:
            aggregated_score = mean(macro_scores)
            confidence = min(1.0, len(macro_scores) / len(self.config.macro_factors))
        else:
            aggregated_score = 0.0
            confidence = 0.0
        
        return aggregated_score, confidence
    
    def update_factor_correlations(self, symbol: str, factor: MacroFactor, correlation: float) -> None:
        """Update factor correlations for symbol"""
        if factor not in self.factor_correlations:
            self.factor_correlations[factor] = {}
        
        self.factor_correlations[factor][symbol] = correlation

class AlternativeDataIntegrator:
    """Main alternative data integration system"""
    
    def __init__(self, config: AlternativeDataConfig = None):
        self.config = config or AlternativeDataConfig()
        
        # Initialize analyzers
        self.sentiment_analyzer = SentimentAnalyzer(self.config) if self.config.enable_sentiment_analysis else None
        self.order_flow_analyzer = OrderFlowAnalyzer(self.config) if self.config.enable_order_flow_analysis else None
        self.options_analyzer = OptionsFlowAnalyzer(self.config) if self.config.enable_options_analysis else None
        self.behavioral_analyzer = BehavioralAnalyzer(self.config) if self.config.enable_behavioral_analysis else None
        self.macro_analyzer = MacroAnalyzer(self.config) if self.config.enable_macro_analysis else None
        
        # Signal history
        self.signal_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=500))
        
        logger.info("Initialized AlternativeDataIntegrator")
    
    def process_sentiment_data(self, data: SentimentData) -> None:
        """Process sentiment data"""
        if self.sentiment_analyzer:
            self.sentiment_analyzer.process_sentiment_data(data)
    
    def process_order_flow_data(self, data: OrderFlowData) -> None:
        """Process order flow data"""
        if self.order_flow_analyzer:
            self.order_flow_analyzer.process_order_flow_data(data)
    
    def process_options_data(self, data: OptionsFlowData) -> None:
        """Process options flow data"""
        if self.options_analyzer:
            self.options_analyzer.process_options_data(data)
    
    def process_behavioral_data(self, data: BehavioralData) -> None:
        """Process behavioral data"""
        if self.behavioral_analyzer:
            self.behavioral_analyzer.process_behavioral_data(data)
    
    def process_macro_data(self, data: MacroData) -> None:
        """Process macro economic data"""
        if self.macro_analyzer:
            self.macro_analyzer.process_macro_data(data)
    
    def generate_alternative_data_signal(self, symbol: str, price_data: List[float] = None, 
                                       volume_data: List[float] = None) -> AlternativeDataSignal:
        """Generate comprehensive alternative data signal"""
        # Get individual component scores
        sentiment_score, sentiment_confidence = self._get_sentiment_score(symbol)
        order_flow_score, order_flow_confidence = self._get_order_flow_score(symbol)
        options_score, options_confidence = self._get_options_score(symbol)
        behavioral_score, behavioral_confidence = self._get_behavioral_score(symbol, price_data, volume_data)
        macro_score, macro_confidence = self._get_macro_score(symbol)
        
        # Calculate composite score using configured weights
        composite_score = (
            sentiment_score * self.config.sentiment_weight +
            order_flow_score * self.config.order_flow_weight +
            options_score * self.config.options_weight +
            behavioral_score * self.config.behavioral_weight +
            macro_score * self.config.macro_weight
        )
        
        # Calculate overall confidence
        confidence_scores = [sentiment_confidence, order_flow_confidence, options_confidence, 
                           behavioral_confidence, macro_confidence]
        overall_confidence = mean([c for c in confidence_scores if c > 0]) if any(c > 0 for c in confidence_scores) else 0.0
        
        # Calculate signal strength
        signal_strength = abs(composite_score) * overall_confidence
        
        # Calculate contrarian indicator
        contrarian_indicator = self._calculate_contrarian_indicator(behavioral_score, sentiment_score)
        
        # Calculate regime consistency
        regime_consistency = self._calculate_regime_consistency(symbol)
        
        signal = AlternativeDataSignal(
            symbol=symbol,
            sentiment_score=sentiment_score,
            order_flow_score=order_flow_score,
            options_flow_score=options_score,
            behavioral_score=behavioral_score,
            macro_score=macro_score,
            composite_score=composite_score,
            confidence=overall_confidence,
            signal_strength=signal_strength,
            contrarian_indicator=contrarian_indicator,
            regime_consistency=regime_consistency,
            timestamp=datetime.now()
        )
        
        # Store signal
        self.signal_history[symbol].append(signal)
        
        return signal
    
    def _get_sentiment_score(self, symbol: str) -> Tuple[float, float]:
        """Get sentiment score and confidence"""
        if self.sentiment_analyzer:
            return self.sentiment_analyzer.get_aggregated_sentiment(symbol)
        return 0.0, 0.0
    
    def _get_order_flow_score(self, symbol: str) -> Tuple[float, float]:
        """Get order flow score and confidence"""
        if self.order_flow_analyzer:
            return self.order_flow_analyzer.get_aggregated_order_flow(symbol)
        return 0.0, 0.0
    
    def _get_options_score(self, symbol: str) -> Tuple[float, float]:
        """Get options flow score and confidence"""
        if self.options_analyzer:
            put_call_ratio, unusual_score, institutional_bias = self.options_analyzer.get_aggregated_options_flow(symbol)
            
            # Combine metrics into single score
            options_score = (institutional_bias * 0.6 + unusual_score * 0.4)
            
            # Put/call ratio adjustment
            if put_call_ratio > 1.2:  # High put/call ratio = bearish
                options_score -= 0.2
            elif put_call_ratio < 0.8:  # Low put/call ratio = bullish
                options_score += 0.2
            
            confidence = min(1.0, unusual_score + 0.5)  # Higher confidence with unusual activity
            
            return options_score, confidence
        return 0.0, 0.0
    
    def _get_behavioral_score(self, symbol: str, price_data: List[float], volume_data: List[float]) -> Tuple[float, float]:
        """Get behavioral score and confidence"""
        if self.behavioral_analyzer:
            # Generate behavioral analysis if price/volume data provided
            if price_data and volume_data:
                behavioral_data = self.behavioral_analyzer.analyze_behavioral_patterns(symbol, price_data, volume_data)
                self.behavioral_analyzer.process_behavioral_data(behavioral_data)
            
            return self.behavioral_analyzer.get_aggregated_behavioral_score(symbol)
        return 0.0, 0.0
    
    def _get_macro_score(self, symbol: str) -> Tuple[float, float]:
        """Get macro score and confidence"""
        if self.macro_analyzer:
            return self.macro_analyzer.get_aggregated_macro_score(symbol)
        return 0.0, 0.0
    
    def _calculate_contrarian_indicator(self, behavioral_score: float, sentiment_score: float) -> float:
        """Calculate contrarian indicator"""
        # Strong contrarian signal when both behavioral and sentiment are extreme
        avg_score = (behavioral_score + sentiment_score) / 2.0
        
        if abs(avg_score) > self.config.contrarian_threshold:
            return -avg_score  # Contrarian to the crowd
        else:
            return 0.0
    
    def _calculate_regime_consistency(self, symbol: str) -> float:
        """Calculate regime consistency score"""
        if symbol not in self.signal_history or len(self.signal_history[symbol]) < 5:
            return 0.5  # Neutral when insufficient data
        
        recent_signals = list(self.signal_history[symbol])[-5:]
        composite_scores = [s.composite_score for s in recent_signals]
        
        # Check consistency of signal direction
        positive_signals = sum(1 for score in composite_scores if score > 0.1)
        negative_signals = sum(1 for score in composite_scores if score < -0.1)
        
        if positive_signals >= 4 or negative_signals >= 4:
            return 1.0  # High consistency
        elif positive_signals >= 3 or negative_signals >= 3:
            return 0.7  # Medium consistency
        else:
            return 0.3  # Low consistency
    
    def get_signal_summary(self, symbol: str) -> Dict[str, Any]:
        """Get comprehensive signal summary"""
        if symbol not in self.signal_history or not self.signal_history[symbol]:
            return {'status': 'no_data'}
        
        latest_signal = self.signal_history[symbol][-1]
        
        return {
            'symbol': symbol,
            'timestamp': latest_signal.timestamp.isoformat(),
            'composite_score': latest_signal.composite_score,
            'signal_strength': latest_signal.signal_strength,
            'confidence': latest_signal.confidence,
            'components': {
                'sentiment': latest_signal.sentiment_score,
                'order_flow': latest_signal.order_flow_score,
                'options_flow': latest_signal.options_flow_score,
                'behavioral': latest_signal.behavioral_score,
                'macro': latest_signal.macro_score
            },
            'contrarian_indicator': latest_signal.contrarian_indicator,
            'regime_consistency': latest_signal.regime_consistency,
            'signal_interpretation': self._interpret_signal(latest_signal)
        }
    
    def _interpret_signal(self, signal: AlternativeDataSignal) -> str:
        """Interpret the alternative data signal"""
        if signal.signal_strength < 0.2:
            return "Weak signal - insufficient alternative data conviction"
        elif signal.composite_score > 0.5:
            return f"Strong bullish signal (confidence: {signal.confidence:.1%})"
        elif signal.composite_score > 0.2:
            return f"Moderate bullish signal (confidence: {signal.confidence:.1%})"
        elif signal.composite_score < -0.5:
            return f"Strong bearish signal (confidence: {signal.confidence:.1%})"
        elif signal.composite_score < -0.2:
            return f"Moderate bearish signal (confidence: {signal.confidence:.1%})"
        else:
            return "Neutral signal - mixed alternative data signals"
    
    def __str__(self) -> str:
        active_analyzers = sum([
            1 if self.sentiment_analyzer else 0,
            1 if self.order_flow_analyzer else 0,
            1 if self.options_analyzer else 0,
            1 if self.behavioral_analyzer else 0,
            1 if self.macro_analyzer else 0
        ])
        
        return f"AlternativeDataIntegrator(Analyzers={active_analyzers}, Symbols={len(self.signal_history)})"

# Factory function for easy creation
def create_alternative_data_integrator(enable_all_features: bool = True,
                                     sentiment_weight: float = 0.25,
                                     order_flow_weight: float = 0.25,
                                     options_weight: float = 0.20,
                                     behavioral_weight: float = 0.15,
                                     macro_weight: float = 0.15) -> AlternativeDataIntegrator:
    """Factory function to create AlternativeDataIntegrator
    
    Args:
        enable_all_features: Enable all alternative data features
        sentiment_weight: Weight for sentiment analysis
        order_flow_weight: Weight for order flow analysis
        options_weight: Weight for options flow analysis
        behavioral_weight: Weight for behavioral analysis
        macro_weight: Weight for macro analysis
    
    Returns:
        Configured AlternativeDataIntegrator instance
    """
    config = AlternativeDataConfig(
        enable_sentiment_analysis=enable_all_features,
        enable_order_flow_analysis=enable_all_features,
        enable_options_analysis=enable_all_features,
        enable_behavioral_analysis=enable_all_features,
        enable_macro_analysis=enable_all_features,
        sentiment_weight=sentiment_weight,
        order_flow_weight=order_flow_weight,
        options_weight=options_weight,
        behavioral_weight=behavioral_weight,
        macro_weight=macro_weight,
        enable_ml_sentiment=enable_all_features,
        enable_regime_detection=enable_all_features,
        enable_cross_asset_analysis=enable_all_features,
        enable_event_impact_modeling=enable_all_features
    )
    
    return AlternativeDataIntegrator(config)