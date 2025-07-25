"""
AI Assistant Feature Definitions for Market Data

This module defines features specifically for the AI Assistant to enhance
decision making with market data insights.

Author: Kilo Code
Version: 1.0.0
"""

from datetime import timedelta
from feast import Entity, FeatureView, Field, FileSource, FeatureService
from feast.types import Float64, Int64, String, UnixTimestamp


# Entity Definitions
ticker_entity = Entity(
    name="ticker",
    description="Stock ticker symbol (e.g., AAPL, GOOGL, MSFT)",
    join_keys=["ticker"]
)

# Data Source
market_data_source = FileSource(
    name="market_data_source",
    path="data/market_data.parquet",
    timestamp_field="event_timestamp",
    created_timestamp_column="created_timestamp"
)

# Feature Views
daily_market_features = FeatureView(
    name="daily_market_features",
    entities=[ticker_entity],
    ttl=timedelta(days=2),
    schema=[
        Field(name="daily_high", dtype=Float64, description="Daily high price"),
        Field(name="daily_low", dtype=Float64, description="Daily low price"),
        Field(name="daily_volume", dtype=Int64, description="Daily trading volume"),
        Field(name="price_change_percentage", dtype=Float64, description="Daily price change percentage"),
        Field(name="opening_price", dtype=Float64, description="Opening price"),
        Field(name="closing_price", dtype=Float64, description="Closing price"),
        Field(name="vwap", dtype=Float64, description="Volume weighted average price"),
        Field(name="market_cap", dtype=Float64, description="Market capitalization"),
        Field(name="pe_ratio", dtype=Float64, description="Price to earnings ratio"),
        Field(name="volatility_20d", dtype=Float64, description="20-day volatility"),
    ],
    source=market_data_source,
    tags={
        "team": "ai_assistant",
        "category": "market_data",
        "frequency": "daily"
    }
)

# Technical Indicators Feature View
technical_indicators = FeatureView(
    name="technical_indicators",
    entities=[ticker_entity],
    ttl=timedelta(hours=6),
    schema=[
        Field(name="rsi_14", dtype=Float64, description="14-period RSI"),
        Field(name="macd_line", dtype=Float64, description="MACD line"),
        Field(name="macd_signal", dtype=Float64, description="MACD signal line"),
        Field(name="bollinger_upper", dtype=Float64, description="Bollinger band upper"),
        Field(name="bollinger_lower", dtype=Float64, description="Bollinger band lower"),
        Field(name="sma_20", dtype=Float64, description="20-period simple moving average"),
        Field(name="sma_50", dtype=Float64, description="50-period simple moving average"),
        Field(name="ema_12", dtype=Float64, description="12-period exponential moving average"),
        Field(name="ema_26", dtype=Float64, description="26-period exponential moving average"),
        Field(name="atr_14", dtype=Float64, description="14-period Average True Range"),
    ],
    source=market_data_source,
    tags={
        "team": "ai_assistant",
        "category": "technical_analysis",
        "frequency": "hourly"
    }
)

# Market Sentiment Features
market_sentiment = FeatureView(
    name="market_sentiment",
    entities=[ticker_entity],
    ttl=timedelta(hours=4),
    schema=[
        Field(name="sentiment_score", dtype=Float64, description="Overall sentiment score (-1 to 1)"),
        Field(name="news_sentiment", dtype=Float64, description="News sentiment score"),
        Field(name="social_sentiment", dtype=Float64, description="Social media sentiment score"),
        Field(name="analyst_rating", dtype=Float64, description="Average analyst rating"),
        Field(name="price_momentum_1d", dtype=Float64, description="1-day price momentum"),
        Field(name="price_momentum_7d", dtype=Float64, description="7-day price momentum"),
        Field(name="volume_momentum", dtype=Float64, description="Volume momentum indicator"),
        Field(name="sector_performance", dtype=Float64, description="Sector relative performance"),
    ],
    source=market_data_source,
    tags={
        "team": "ai_assistant",
        "category": "sentiment",
        "frequency": "4hourly"
    }
)

# Feature Services for AI Assistant
ai_trading_decision_service = FeatureService(
    name="ai_trading_decision_v1",
    features=[
        "daily_market_features:closing_price",
        "daily_market_features:daily_volume",
        "daily_market_features:price_change_percentage",
        "daily_market_features:volatility_20d",
        "technical_indicators:rsi_14",
        "technical_indicators:macd_line",
        "technical_indicators:macd_signal",
        "technical_indicators:sma_20",
        "technical_indicators:sma_50",
        "market_sentiment:sentiment_score",
        "market_sentiment:price_momentum_1d",
        "market_sentiment:analyst_rating",
    ],
    tags={
        "use_case": "ai_trading_decision",
        "version": "v1",
        "owner": "ai_assistant"
    }
)

ai_risk_assessment_service = FeatureService(
    name="ai_risk_assessment_v1",
    features=[
        "daily_market_features:volatility_20d",
        "daily_market_features:daily_high",
        "daily_market_features:daily_low",
        "technical_indicators:atr_14",
        "technical_indicators:bollinger_upper",
        "technical_indicators:bollinger_lower",
        "market_sentiment:sentiment_score",
        "market_sentiment:volume_momentum",
    ],
    tags={
        "use_case": "risk_assessment",
        "version": "v1",
        "owner": "ai_assistant"
    }
)

ai_market_analysis_service = FeatureService(
    name="ai_market_analysis_v1",
    features=[
        "daily_market_features",  # All daily market features
        "technical_indicators",   # All technical indicators
        "market_sentiment:sentiment_score",
        "market_sentiment:sector_performance",
    ],
    tags={
        "use_case": "market_analysis",
        "version": "v1",
        "owner": "ai_assistant"
    }
)