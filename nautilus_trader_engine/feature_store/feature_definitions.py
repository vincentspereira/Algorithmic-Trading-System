"""
Feature Definitions for Nautilus Trading System

This module defines all features for the Feast feature store including:
- Market data features (OHLCV, volume profiles)
- Technical indicator features
- Custom trading features
- Feature views and entities

Author: Vincent S. Pereira
Version: 1.0.0
"""

from datetime import timedelta
from typing import List, Dict, Any, Optional
import pandas as pd

# Feast imports
try:
    from feast import (
        Entity,
        FeatureView,
        Field,
        FileSource,
        PushSource,
        ValueType,
        FeatureService,
        OnDemandFeatureView,
        RequestSource
    )
    from feast.types import Float32, Float64, Int32, Int64, String, Bool, UnixTimestamp
    FEAST_AVAILABLE = True
except ImportError:
    print("Warning: Feast not available. Install with: pip install feast")
    FEAST_AVAILABLE = False
    
    # Create dummy classes for development
    class Entity:
        def __init__(self, **kwargs): pass
    class FeatureView:
        def __init__(self, **kwargs): pass
    class Field:
        def __init__(self, **kwargs): pass
    class FileSource:
        def __init__(self, **kwargs): pass
    class PushSource:
        def __init__(self, **kwargs): pass
    class FeatureService:
        def __init__(self, **kwargs): pass
    class OnDemandFeatureView:
        def __init__(self, **kwargs): pass
    class RequestSource:
        def __init__(self, **kwargs): pass
    Float32 = Float64 = Int32 = Int64 = String = Bool = UnixTimestamp = None


# Entity Definitions
def create_entities() -> List[Entity]:
    """Create entity definitions"""
    entities = []
    
    if FEAST_AVAILABLE:
        # Symbol entity
        symbol_entity = Entity(
            name="symbol",
            description="Trading symbol (e.g., AAPL, EURUSD)",
            value_type=ValueType.STRING
        )
        entities.append(symbol_entity)
        
        # Exchange entity
        exchange_entity = Entity(
            name="exchange",
            description="Exchange identifier (e.g., NYSE, NASDAQ)",
            value_type=ValueType.STRING
        )
        entities.append(exchange_entity)
        
        # Asset class entity
        asset_class_entity = Entity(
            name="asset_class",
            description="Asset class (STOCK, FOREX, CRYPTO, etc.)",
            value_type=ValueType.STRING
        )
        entities.append(asset_class_entity)
    
    return entities


# Data Sources
def create_data_sources() -> Dict[str, Any]:
    """Create data source definitions"""
    sources = {}
    
    if FEAST_AVAILABLE:
        # Market data source
        market_data_source = FileSource(
            name="market_data_source",
            path="data/market_data.parquet",
            timestamp_field="timestamp",
            created_timestamp_column="created_timestamp"
        )
        sources["market_data"] = market_data_source
        
        # Technical indicators source
        indicators_source = FileSource(
            name="indicators_source",
            path="data/technical_indicators.parquet",
            timestamp_field="timestamp",
            created_timestamp_column="created_timestamp"
        )
        sources["indicators"] = indicators_source
        
        # Trading signals source
        signals_source = FileSource(
            name="signals_source",
            path="data/trading_signals.parquet",
            timestamp_field="timestamp",
            created_timestamp_column="created_timestamp"
        )
        sources["signals"] = signals_source
        
        # Volume profile source
        volume_profile_source = FileSource(
            name="volume_profile_source",
            path="data/volume_profiles.parquet",
            timestamp_field="timestamp",
            created_timestamp_column="created_timestamp"
        )
        sources["volume_profile"] = volume_profile_source
    
    return sources


# Feature Views
def create_market_data_features(sources: Dict[str, Any]) -> List[FeatureView]:
    """Create market data feature views"""
    feature_views = []
    
    if FEAST_AVAILABLE and "market_data" in sources:
        # OHLCV Features
        ohlcv_features = FeatureView(
            name="ohlcv_features",
            entities=["symbol"],
            ttl=timedelta(days=1),
            schema=[
                Field(name="open_price", dtype=Float64),
                Field(name="high_price", dtype=Float64),
                Field(name="low_price", dtype=Float64),
                Field(name="close_price", dtype=Float64),
                Field(name="volume", dtype=Int64),
                Field(name="vwap", dtype=Float64),
                Field(name="typical_price", dtype=Float64),
                Field(name="price_change", dtype=Float64),
                Field(name="price_change_pct", dtype=Float64),
                Field(name="volume_change", dtype=Float64),
                Field(name="volume_change_pct", dtype=Float64),
            ],
            source=sources["market_data"],
            tags={"category": "market_data", "frequency": "1min"}
        )
        feature_views.append(ohlcv_features)
        
        # Price Statistics Features
        price_stats_features = FeatureView(
            name="price_statistics",
            entities=["symbol"],
            ttl=timedelta(hours=6),
            schema=[
                Field(name="price_volatility_1h", dtype=Float64),
                Field(name="price_volatility_1d", dtype=Float64),
                Field(name="price_range_1h", dtype=Float64),
                Field(name="price_range_1d", dtype=Float64),
                Field(name="avg_spread", dtype=Float64),
                Field(name="bid_ask_spread", dtype=Float64),
                Field(name="tick_count_1h", dtype=Int32),
                Field(name="tick_count_1d", dtype=Int32),
            ],
            source=sources["market_data"],
            tags={"category": "price_statistics", "frequency": "1h"}
        )
        feature_views.append(price_stats_features)
    
    return feature_views


def create_technical_indicator_features(sources: Dict[str, Any]) -> List[FeatureView]:
    """Create technical indicator feature views"""
    feature_views = []
    
    if FEAST_AVAILABLE and "indicators" in sources:
        # Moving Average Features
        ma_features = FeatureView(
            name="moving_averages",
            entities=["symbol"],
            ttl=timedelta(hours=1),
            schema=[
                Field(name="sma_5", dtype=Float64),
                Field(name="sma_10", dtype=Float64),
                Field(name="sma_20", dtype=Float64),
                Field(name="sma_50", dtype=Float64),
                Field(name="sma_200", dtype=Float64),
                Field(name="ema_5", dtype=Float64),
                Field(name="ema_10", dtype=Float64),
                Field(name="ema_20", dtype=Float64),
                Field(name="ema_50", dtype=Float64),
                Field(name="ema_200", dtype=Float64),
                Field(name="vw_sma_20", dtype=Float64),
                Field(name="vw_ema_20", dtype=Float64),
            ],
            source=sources["indicators"],
            tags={"category": "moving_averages", "frequency": "1min"}
        )
        feature_views.append(ma_features)
        
        # Momentum Indicators
        momentum_features = FeatureView(
            name="momentum_indicators",
            entities=["symbol"],
            ttl=timedelta(hours=1),
            schema=[
                Field(name="rsi_14", dtype=Float64),
                Field(name="rsi_21", dtype=Float64),
                Field(name="stoch_k", dtype=Float64),
                Field(name="stoch_d", dtype=Float64),
                Field(name="williams_r", dtype=Float64),
                Field(name="roc_10", dtype=Float64),
                Field(name="momentum_10", dtype=Float64),
            ],
            source=sources["indicators"],
            tags={"category": "momentum", "frequency": "1min"}
        )
        feature_views.append(momentum_features)
        
        # Trend Indicators
        trend_features = FeatureView(
            name="trend_indicators",
            entities=["symbol"],
            ttl=timedelta(hours=1),
            schema=[
                Field(name="macd_line", dtype=Float64),
                Field(name="macd_signal", dtype=Float64),
                Field(name="macd_histogram", dtype=Float64),
                Field(name="vw_macd_line", dtype=Float64),
                Field(name="vw_macd_signal", dtype=Float64),
                Field(name="vw_macd_histogram", dtype=Float64),
                Field(name="adx", dtype=Float64),
                Field(name="plus_di", dtype=Float64),
                Field(name="minus_di", dtype=Float64),
                Field(name="aroon_up", dtype=Float64),
                Field(name="aroon_down", dtype=Float64),
            ],
            source=sources["indicators"],
            tags={"category": "trend", "frequency": "1min"}
        )
        feature_views.append(trend_features)
        
        # Volatility Indicators
        volatility_features = FeatureView(
            name="volatility_indicators",
            entities=["symbol"],
            ttl=timedelta(hours=1),
            schema=[
                Field(name="bb_upper", dtype=Float64),
                Field(name="bb_middle", dtype=Float64),
                Field(name="bb_lower", dtype=Float64),
                Field(name="bb_width", dtype=Float64),
                Field(name="bb_percent", dtype=Float64),
                Field(name="atr_14", dtype=Float64),
                Field(name="atr_21", dtype=Float64),
                Field(name="keltner_upper", dtype=Float64),
                Field(name="keltner_lower", dtype=Float64),
                Field(name="donchian_upper", dtype=Float64),
                Field(name="donchian_lower", dtype=Float64),
            ],
            source=sources["indicators"],
            tags={"category": "volatility", "frequency": "1min"}
        )
        feature_views.append(volatility_features)
    
    return feature_views


def create_volume_profile_features(sources: Dict[str, Any]) -> List[FeatureView]:
    """Create volume profile feature views"""
    feature_views = []
    
    if FEAST_AVAILABLE and "volume_profile" in sources:
        # Volume Profile Features
        volume_profile_features = FeatureView(
            name="volume_profiles",
            entities=["symbol"],
            ttl=timedelta(hours=4),
            schema=[
                Field(name="poc_price", dtype=Float64),  # Point of Control
                Field(name="vah_price", dtype=Float64),  # Value Area High
                Field(name="val_price", dtype=Float64),  # Value Area Low
                Field(name="volume_at_price_current", dtype=Int64),
                Field(name="volume_imbalance", dtype=Float64),
                Field(name="volume_delta", dtype=Int64),
                Field(name="cumulative_volume_delta", dtype=Int64),
                Field(name="volume_weighted_price", dtype=Float64),
                Field(name="volume_profile_shape", dtype=String),  # "normal", "bimodal", "flat"
                Field(name="high_volume_nodes", dtype=String),  # JSON array of price levels
                Field(name="low_volume_nodes", dtype=String),   # JSON array of price levels
            ],
            source=sources["volume_profile"],
            tags={"category": "volume_profile", "frequency": "1h"}
        )
        feature_views.append(volume_profile_features)
    
    return feature_views


def create_trading_signal_features(sources: Dict[str, Any]) -> List[FeatureView]:
    """Create trading signal feature views"""
    feature_views = []
    
    if FEAST_AVAILABLE and "signals" in sources:
        # Trading Signals
        signal_features = FeatureView(
            name="trading_signals",
            entities=["symbol"],
            ttl=timedelta(minutes=30),
            schema=[
                Field(name="signal_strength", dtype=Float64),
                Field(name="signal_direction", dtype=String),  # "BUY", "SELL", "HOLD"
                Field(name="signal_confidence", dtype=Float64),
                Field(name="entry_price", dtype=Float64),
                Field(name="stop_loss", dtype=Float64),
                Field(name="take_profit", dtype=Float64),
                Field(name="risk_reward_ratio", dtype=Float64),
                Field(name="signal_source", dtype=String),  # Strategy name
                Field(name="signal_timestamp", dtype=UnixTimestamp),
                Field(name="signal_expiry", dtype=UnixTimestamp),
            ],
            source=sources["signals"],
            tags={"category": "signals", "frequency": "realtime"}
        )
        feature_views.append(signal_features)
        
        # Strategy Performance Features
        strategy_performance_features = FeatureView(
            name="strategy_performance",
            entities=["symbol"],
            ttl=timedelta(hours=24),
            schema=[
                Field(name="strategy_win_rate", dtype=Float64),
                Field(name="strategy_avg_return", dtype=Float64),
                Field(name="strategy_sharpe_ratio", dtype=Float64),
                Field(name="strategy_max_drawdown", dtype=Float64),
                Field(name="strategy_total_trades", dtype=Int32),
                Field(name="strategy_profitable_trades", dtype=Int32),
                Field(name="strategy_last_signal_time", dtype=UnixTimestamp),
                Field(name="strategy_active", dtype=Bool),
            ],
            source=sources["signals"],
            tags={"category": "strategy_performance", "frequency": "1h"}
        )
        feature_views.append(strategy_performance_features)
    
    return feature_views


def create_on_demand_features() -> List[OnDemandFeatureView]:
    """Create on-demand feature views for real-time calculations"""
    on_demand_features = []
    
    if FEAST_AVAILABLE:
        # Price momentum on-demand features
        price_momentum_odv = OnDemandFeatureView(
            name="price_momentum_realtime",
            sources=[
                RequestSource(
                    name="current_price_request",
                    schema=[
                        Field(name="current_price", dtype=Float64),
                        Field(name="current_volume", dtype=Int64),
                    ]
                )
            ],
            schema=[
                Field(name="price_momentum_5min", dtype=Float64),
                Field(name="price_vs_sma20", dtype=Float64),
                Field(name="volume_vs_avg", dtype=Float64),
                Field(name="price_velocity", dtype=Float64),
            ],
            udf="""
            def price_momentum_realtime(inputs: pd.DataFrame) -> pd.DataFrame:
                df = pd.DataFrame()
                
                # Calculate price momentum (would need historical data in real implementation)
                df["price_momentum_5min"] = inputs["current_price"] * 0.01  # Placeholder
                df["price_vs_sma20"] = (inputs["current_price"] - inputs["sma_20"]) / inputs["sma_20"]
                df["volume_vs_avg"] = inputs["current_volume"] / inputs["volume"].rolling(20).mean()
                df["price_velocity"] = inputs["current_price"].pct_change()
                
                return df
            """,
            tags={"category": "realtime", "type": "momentum"}
        )
        on_demand_features.append(price_momentum_odv)
    
    return on_demand_features


def create_feature_services() -> List[FeatureService]:
    """Create feature services for different use cases"""
    feature_services = []
    
    if FEAST_AVAILABLE:
        # Trading decision service
        trading_decision_service = FeatureService(
            name="trading_decision_v1",
            features=[
                "ohlcv_features:close_price",
                "ohlcv_features:volume",
                "ohlcv_features:vwap",
                "moving_averages:sma_20",
                "moving_averages:ema_20",
                "moving_averages:vw_sma_20",
                "momentum_indicators:rsi_14",
                "trend_indicators:macd_line",
                "trend_indicators:macd_signal",
                "volatility_indicators:bb_upper",
                "volatility_indicators:bb_lower",
                "volatility_indicators:atr_14",
                "trading_signals:signal_strength",
                "trading_signals:signal_confidence",
            ],
            tags={"use_case": "trading_decision", "version": "v1"}
        )
        feature_services.append(trading_decision_service)
        
        # Risk management service
        risk_management_service = FeatureService(
            name="risk_management_v1",
            features=[
                "ohlcv_features:price_volatility_1d",
                "volatility_indicators:atr_14",
                "volatility_indicators:bb_width",
                "volume_profiles:volume_imbalance",
                "strategy_performance:strategy_max_drawdown",
                "strategy_performance:strategy_win_rate",
                "trading_signals:risk_reward_ratio",
                "trading_signals:stop_loss",
            ],
            tags={"use_case": "risk_management", "version": "v1"}
        )
        feature_services.append(risk_management_service)
        
        # Market analysis service
        market_analysis_service = FeatureService(
            name="market_analysis_v1",
            features=[
                "ohlcv_features",  # All OHLCV features
                "price_statistics",  # All price statistics
                "volume_profiles",   # All volume profile features
                "moving_averages:sma_50",
                "moving_averages:sma_200",
                "trend_indicators:adx",
                "momentum_indicators:rsi_14",
            ],
            tags={"use_case": "market_analysis", "version": "v1"}
        )
        feature_services.append(market_analysis_service)
    
    return feature_services


def get_all_feature_definitions() -> Dict[str, List[Any]]:
    """Get all feature definitions organized by type"""
    
    # Create data sources
    sources = create_data_sources()
    
    # Create all feature definitions
    definitions = {
        "entities": create_entities(),
        "feature_views": [],
        "on_demand_features": create_on_demand_features(),
        "feature_services": create_feature_services(),
        "sources": sources
    }
    
    # Combine all feature views
    definitions["feature_views"].extend(create_market_data_features(sources))
    definitions["feature_views"].extend(create_technical_indicator_features(sources))
    definitions["feature_views"].extend(create_volume_profile_features(sources))
    definitions["feature_views"].extend(create_trading_signal_features(sources))
    
    return definitions


def get_feature_list_by_category() -> Dict[str, List[str]]:
    """Get organized list of features by category"""
    return {
        "market_data": [
            "ohlcv_features:open_price",
            "ohlcv_features:high_price", 
            "ohlcv_features:low_price",
            "ohlcv_features:close_price",
            "ohlcv_features:volume",
            "ohlcv_features:vwap",
            "price_statistics:price_volatility_1d",
            "price_statistics:avg_spread",
        ],
        "technical_indicators": [
            "moving_averages:sma_20",
            "moving_averages:ema_20",
            "moving_averages:vw_sma_20",
            "momentum_indicators:rsi_14",
            "trend_indicators:macd_line",
            "trend_indicators:vw_macd_line",
            "volatility_indicators:bb_upper",
            "volatility_indicators:atr_14",
        ],
        "volume_analysis": [
            "volume_profiles:poc_price",
            "volume_profiles:vah_price",
            "volume_profiles:volume_delta",
            "volume_profiles:volume_imbalance",
        ],
        "trading_signals": [
            "trading_signals:signal_strength",
            "trading_signals:signal_confidence",
            "trading_signals:entry_price",
            "trading_signals:risk_reward_ratio",
            "strategy_performance:strategy_win_rate",
            "strategy_performance:strategy_sharpe_ratio",
        ]
    }


def test_feature_definitions():
    """Test feature definitions"""
    print("Testing Feature Definitions...")
    print("=" * 50)
    
    # Get all definitions
    definitions = get_all_feature_definitions()
    
    print(f"Entities: {len(definitions['entities'])}")
    print(f"Feature Views: {len(definitions['feature_views'])}")
    print(f"On-Demand Features: {len(definitions['on_demand_features'])}")
    print(f"Feature Services: {len(definitions['feature_services'])}")
    print(f"Data Sources: {len(definitions['sources'])}")
    
    # Print feature categories
    feature_categories = get_feature_list_by_category()
    print(f"\nFeature Categories:")
    for category, features in feature_categories.items():
        print(f"  {category}: {len(features)} features")
    
    print(f"\nFeast Available: {FEAST_AVAILABLE}")
    print("Feature definitions test completed!")


if __name__ == "__main__":
    test_feature_definitions()