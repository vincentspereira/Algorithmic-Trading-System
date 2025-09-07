"""Data Provider Configurations

Configuration settings for all supported data providers including API keys,
rate limits, endpoints, and asset class mappings.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from shared.config import settings

class ProviderTier(str, Enum):
    """Provider reliability tiers"""
    PRIMARY = "primary"      # Most reliable, lowest latency
    SECONDARY = "secondary"  # Good reliability, moderate latency
    FALLBACK = "fallback"    # Backup option, higher latency acceptable
    EMERGENCY = "emergency"  # Last resort, may have limitations

@dataclass
class ProviderEndpoints:
    """API endpoints for a data provider"""
    base_url: str
    real_time: str
    historical: str
    options_chain: Optional[str] = None
    fundamentals: Optional[str] = None
    news: Optional[str] = None
    earnings: Optional[str] = None

@dataclass
class ProviderLimits:
    """Rate limits and quotas for a provider"""
    requests_per_minute: int
    requests_per_day: Optional[int] = None
    concurrent_requests: int = 5
    timeout_seconds: float = 10.0
    retry_attempts: int = 3
    backoff_multiplier: float = 2.0

@dataclass
class ProviderFeatures:
    """Features supported by a provider"""
    real_time_data: bool = True
    historical_data: bool = True
    options_data: bool = False
    futures_data: bool = False
    forex_data: bool = False
    crypto_data: bool = False
    fundamental_data: bool = False
    news_data: bool = False
    earnings_data: bool = False
    dividend_data: bool = False
    splits_data: bool = False
    insider_trading: bool = False
    institutional_holdings: bool = False
    analyst_ratings: bool = False
    economic_indicators: bool = False

@dataclass
class ProviderConfig:
    """Complete configuration for a data provider"""
    name: str
    display_name: str
    tier: ProviderTier
    api_key_required: bool
    api_key: Optional[str]
    endpoints: ProviderEndpoints
    limits: ProviderLimits
    features: ProviderFeatures
    supported_exchanges: List[str]
    supported_countries: List[str]
    data_quality_score: float  # 0.0 to 1.0
    cost_per_request: float = 0.0  # For cost optimization
    free_tier_available: bool = True

# Provider configurations
PROVIDER_CONFIGS: Dict[str, ProviderConfig] = {
    "yahoo_finance": ProviderConfig(
        name="yahoo_finance",
        display_name="Yahoo Finance",
        tier=ProviderTier.PRIMARY,
        api_key_required=False,
        api_key=None,
        endpoints=ProviderEndpoints(
            base_url="https://query1.finance.yahoo.com",
            real_time="/v8/finance/chart/{symbol}",
            historical="/v8/finance/chart/{symbol}",
            options_chain="/v7/finance/options/{symbol}",
            fundamentals="/v10/finance/quoteSummary/{symbol}",
            news="/v1/finance/search"
        ),
        limits=ProviderLimits(
            requests_per_minute=2000,
            requests_per_day=None,
            concurrent_requests=10,
            timeout_seconds=5.0,
            retry_attempts=3
        ),
        features=ProviderFeatures(
            real_time_data=True,
            historical_data=True,
            options_data=True,
            forex_data=True,
            crypto_data=True,
            fundamental_data=True,
            news_data=True,
            earnings_data=True,
            dividend_data=True,
            splits_data=True
        ),
        supported_exchanges=["NYSE", "NASDAQ", "AMEX", "LSE", "TSE", "ASX"],
        supported_countries=["US", "CA", "GB", "AU", "DE", "FR", "JP"],
        data_quality_score=0.85,
        free_tier_available=True
    ),
    
    "alpha_vantage": ProviderConfig(
        name="alpha_vantage",
        display_name="Alpha Vantage",
        tier=ProviderTier.SECONDARY,
        api_key_required=True,
        api_key=getattr(settings, 'ALPHA_VANTAGE_API_KEY', None),
        endpoints=ProviderEndpoints(
            base_url="https://www.alphavantage.co/query",
            real_time="?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}",
            historical="?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={api_key}",
            fundamentals="?function=OVERVIEW&symbol={symbol}&apikey={api_key}",
            earnings="?function=EARNINGS&symbol={symbol}&apikey={api_key}",
            news="?function=NEWS_SENTIMENT&tickers={symbol}&apikey={api_key}"
        ),
        limits=ProviderLimits(
            requests_per_minute=5,  # Free tier
            requests_per_day=500,
            concurrent_requests=1,
            timeout_seconds=10.0,
            retry_attempts=2
        ),
        features=ProviderFeatures(
            real_time_data=True,
            historical_data=True,
            forex_data=True,
            crypto_data=True,
            fundamental_data=True,
            earnings_data=True,
            news_data=True,
            economic_indicators=True
        ),
        supported_exchanges=["NYSE", "NASDAQ", "AMEX"],
        supported_countries=["US"],
        data_quality_score=0.90,
        cost_per_request=0.001,
        free_tier_available=True
    ),
    
    "finnhub": ProviderConfig(
        name="finnhub",
        display_name="Finnhub",
        tier=ProviderTier.SECONDARY,
        api_key_required=True,
        api_key=getattr(settings, 'FINNHUB_API_KEY', None),
        endpoints=ProviderEndpoints(
            base_url="https://finnhub.io/api/v1",
            real_time="/quote?symbol={symbol}&token={api_key}",
            historical="/stock/candle?symbol={symbol}&resolution=D&from={start}&to={end}&token={api_key}",
            fundamentals="/stock/metric?symbol={symbol}&metric=all&token={api_key}",
            earnings="/calendar/earnings?from={start}&to={end}&token={api_key}",
            news="/company-news?symbol={symbol}&from={start}&to={end}&token={api_key}"
        ),
        limits=ProviderLimits(
            requests_per_minute=60,  # Free tier
            requests_per_day=None,
            concurrent_requests=5,
            timeout_seconds=8.0,
            retry_attempts=3
        ),
        features=ProviderFeatures(
            real_time_data=True,
            historical_data=True,
            fundamental_data=True,
            earnings_data=True,
            news_data=True,
            insider_trading=True,
            institutional_holdings=True,
            analyst_ratings=True
        ),
        supported_exchanges=["NYSE", "NASDAQ", "AMEX", "LSE", "TSE"],
        supported_countries=["US", "GB", "JP", "CA", "AU"],
        data_quality_score=0.88,
        cost_per_request=0.002,
        free_tier_available=True
    ),
    
    "polygon": ProviderConfig(
        name="polygon",
        display_name="Polygon.io",
        tier=ProviderTier.SECONDARY,
        api_key_required=True,
        api_key=getattr(settings, 'POLYGON_API_KEY', None),
        endpoints=ProviderEndpoints(
            base_url="https://api.polygon.io",
            real_time="/v2/last/trade/{symbol}?apikey={api_key}",
            historical="/v2/aggs/ticker/{symbol}/range/1/day/{start}/{end}?apikey={api_key}",
            options_chain="/v3/reference/options/contracts?underlying_ticker={symbol}&apikey={api_key}",
            fundamentals="/vX/reference/financials?ticker={symbol}&apikey={api_key}",
            news="/v2/reference/news?ticker={symbol}&apikey={api_key}"
        ),
        limits=ProviderLimits(
            requests_per_minute=5,  # Free tier
            requests_per_day=None,
            concurrent_requests=2,
            timeout_seconds=10.0,
            retry_attempts=3
        ),
        features=ProviderFeatures(
            real_time_data=True,
            historical_data=True,
            options_data=True,
            crypto_data=True,
            fundamental_data=True,
            news_data=True,
            dividend_data=True,
            splits_data=True
        ),
        supported_exchanges=["NYSE", "NASDAQ", "AMEX"],
        supported_countries=["US"],
        data_quality_score=0.92,
        cost_per_request=0.003,
        free_tier_available=True
    ),
    
    "twelve_data": ProviderConfig(
        name="twelve_data",
        display_name="Twelve Data",
        tier=ProviderTier.FALLBACK,
        api_key_required=True,
        api_key=getattr(settings, 'TWELVE_DATA_API_KEY', None),
        endpoints=ProviderEndpoints(
            base_url="https://api.twelvedata.com",
            real_time="/price?symbol={symbol}&apikey={api_key}",
            historical="/time_series?symbol={symbol}&interval=1day&apikey={api_key}",
            fundamentals="/profile?symbol={symbol}&apikey={api_key}",
            earnings="/earnings?symbol={symbol}&apikey={api_key}"
        ),
        limits=ProviderLimits(
            requests_per_minute=8,  # Free tier
            requests_per_day=800,
            concurrent_requests=1,
            timeout_seconds=12.0,
            retry_attempts=2
        ),
        features=ProviderFeatures(
            real_time_data=True,
            historical_data=True,
            forex_data=True,
            crypto_data=True,
            fundamental_data=True,
            earnings_data=True
        ),
        supported_exchanges=["NYSE", "NASDAQ", "LSE", "TSE", "FOREX"],
        supported_countries=["US", "GB", "JP", "CA", "AU", "DE", "FR"],
        data_quality_score=0.82,
        cost_per_request=0.001,
        free_tier_available=True
    ),
    
    "oanda": ProviderConfig(
        name="oanda",
        display_name="OANDA",
        tier=ProviderTier.PRIMARY,  # For forex
        api_key_required=True,
        api_key=getattr(settings, 'OANDA_API_KEY', None),
        endpoints=ProviderEndpoints(
            base_url="https://api-fxtrade.oanda.com",
            real_time="/v3/instruments/{symbol}/price",
            historical="/v3/instruments/{symbol}/candles"
        ),
        limits=ProviderLimits(
            requests_per_minute=120,
            concurrent_requests=10,
            timeout_seconds=5.0,
            retry_attempts=3
        ),
        features=ProviderFeatures(
            real_time_data=True,
            historical_data=True,
            forex_data=True
        ),
        supported_exchanges=["FOREX"],
        supported_countries=["GLOBAL"],
        data_quality_score=0.95,  # Excellent for forex
        cost_per_request=0.0,
        free_tier_available=False
    ),
    
    "cboe": ProviderConfig(
        name="cboe",
        display_name="CBOE",
        tier=ProviderTier.PRIMARY,  # For options
        api_key_required=True,
        api_key=getattr(settings, 'CBOE_API_KEY', None),
        endpoints=ProviderEndpoints(
            base_url="https://www.cboe.com/us/options",
            real_time="/market_statistics/current_statistics/",
            historical="/market_statistics/historical_data/",
            options_chain="/product/{symbol}/"
        ),
        limits=ProviderLimits(
            requests_per_minute=30,
            concurrent_requests=3,
            timeout_seconds=8.0,
            retry_attempts=2
        ),
        features=ProviderFeatures(
            real_time_data=True,
            historical_data=True,
            options_data=True
        ),
        supported_exchanges=["CBOE"],
        supported_countries=["US"],
        data_quality_score=0.98,  # Excellent for options
        cost_per_request=0.005,
        free_tier_available=False
    ),
    
    "cme_group": ProviderConfig(
        name="cme_group",
        display_name="CME Group",
        tier=ProviderTier.PRIMARY,  # For futures
        api_key_required=True,
        api_key=getattr(settings, 'CME_API_KEY', None),
        endpoints=ProviderEndpoints(
            base_url="https://www.cmegroup.com/market-data",
            real_time="/api/v1/market-data/real-time",
            historical="/api/v1/market-data/historical"
        ),
        limits=ProviderLimits(
            requests_per_minute=60,
            concurrent_requests=5,
            timeout_seconds=10.0,
            retry_attempts=3
        ),
        features=ProviderFeatures(
            real_time_data=True,
            historical_data=True,
            futures_data=True,
            options_data=True
        ),
        supported_exchanges=["CME", "CBOT", "NYMEX", "COMEX"],
        supported_countries=["US"],
        data_quality_score=0.96,  # Excellent for futures
        cost_per_request=0.01,
        free_tier_available=False
    ),
    
    "barchart": ProviderConfig(
        name="barchart",
        display_name="Barchart",
        tier=ProviderTier.SECONDARY,
        api_key_required=True,
        api_key=getattr(settings, 'BARCHART_API_KEY', None),
        endpoints=ProviderEndpoints(
            base_url="https://marketdata.websol.barchart.com",
            real_time="/getQuote.json?apikey={api_key}&symbols={symbol}",
            historical="/getHistory.json?apikey={api_key}&symbol={symbol}",
            fundamentals="/getProfile.json?apikey={api_key}&symbol={symbol}"
        ),
        limits=ProviderLimits(
            requests_per_minute=400,  # Free tier
            requests_per_day=None,
            concurrent_requests=5,
            timeout_seconds=8.0,
            retry_attempts=3
        ),
        features=ProviderFeatures(
            real_time_data=True,
            historical_data=True,
            futures_data=True,
            options_data=True,
            fundamental_data=True
        ),
        supported_exchanges=["NYSE", "NASDAQ", "CME", "CBOT"],
        supported_countries=["US"],
        data_quality_score=0.86,
        cost_per_request=0.002,
        free_tier_available=True
    ),
    
    "spiderrock": ProviderConfig(
        name="spiderrock",
        display_name="SpiderRock",
        tier=ProviderTier.SECONDARY,  # For options
        api_key_required=True,
        api_key=getattr(settings, 'SPIDERROCK_API_KEY', None),
        endpoints=ProviderEndpoints(
            base_url="https://api.spiderrock.com",
            real_time="/rest/json",
            historical="/rest/json",
            options_chain="/rest/json"
        ),
        limits=ProviderLimits(
            requests_per_minute=100,
            concurrent_requests=10,
            timeout_seconds=6.0,
            retry_attempts=3
        ),
        features=ProviderFeatures(
            real_time_data=True,
            historical_data=True,
            options_data=True
        ),
        supported_exchanges=["CBOE", "ISE", "AMEX", "NYSE"],
        supported_countries=["US"],
        data_quality_score=0.91,
        cost_per_request=0.008,
        free_tier_available=False
    )
}

# Asset class to provider mapping with priority order
ASSET_PROVIDER_CHAINS = {
    "stock": [
        "yahoo_finance",
        "alpha_vantage", 
        "finnhub",
        "polygon",
        "twelve_data",
        "barchart"
    ],
    "etf": [
        "yahoo_finance",
        "alpha_vantage",
        "polygon",
        "twelve_data"
    ],
    "option": [
        "cboe",
        "spiderrock",
        "polygon",
        "barchart"
    ],
    "future": [
        "cme_group",
        "barchart",
        "polygon"
    ],
    "forex": [
        "oanda",
        "alpha_vantage",
        "twelve_data",
        "yahoo_finance"
    ],
    "crypto": [
        "polygon",
        "alpha_vantage",
        "twelve_data",
        "yahoo_finance"
    ],
    "commodity": [
        "barchart",
        "twelve_data",
        "alpha_vantage"
    ]
}

def get_provider_config(provider_name: str) -> Optional[ProviderConfig]:
    """Get configuration for a specific provider"""
    return PROVIDER_CONFIGS.get(provider_name)

def get_providers_for_asset_class(asset_class: str) -> List[str]:
    """Get ordered list of providers for an asset class"""
    return ASSET_PROVIDER_CHAINS.get(asset_class, [])

def get_available_providers() -> List[str]:
    """Get list of all configured providers"""
    return list(PROVIDER_CONFIGS.keys())

def get_providers_by_tier(tier: ProviderTier) -> List[str]:
    """Get providers filtered by tier"""
    return [
        name for name, config in PROVIDER_CONFIGS.items()
        if config.tier == tier
    ]

def get_free_tier_providers() -> List[str]:
    """Get providers that offer free tier access"""
    return [
        name for name, config in PROVIDER_CONFIGS.items()
        if config.free_tier_available
    ]

def validate_provider_credentials() -> Dict[str, bool]:
    """Validate that required API keys are available"""
    validation_results = {}
    
    for name, config in PROVIDER_CONFIGS.items():
        if config.api_key_required:
            validation_results[name] = config.api_key is not None and len(config.api_key.strip()) > 0
        else:
            validation_results[name] = True  # No API key required
    
    return validation_results