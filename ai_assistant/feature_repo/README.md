# AI Assistant Feature Repository

This directory contains the Feast feature store configuration and definitions for the AI Assistant in Phase 3 of the Algorithmic Trading System.

## Overview

The AI Assistant uses Feast Feature Store to access market data features for enhanced decision making. This setup provides:

- **Real-time feature serving** for trading decisions
- **Historical feature access** for backtesting and analysis
- **Feature versioning** and lineage tracking
- **Scalable feature computation** and storage

## Architecture

```
ai_assistant/feature_repo/
├── feature_store.yaml          # Feast configuration
├── features.py                 # Feature definitions
├── data/
│   └── market_data.parquet    # Sample market data
├── generate_sample_data.py    # Data generation script
├── init_feast.py             # Initialization script
└── README.md                 # This file
```

## Features

### Entities
- **ticker**: Stock ticker symbol (AAPL, GOOGL, MSFT, etc.)

### Feature Views

#### 1. Daily Market Features (`daily_market_features`)
- `daily_high`, `daily_low`: Daily price extremes
- `daily_volume`: Trading volume
- `price_change_percentage`: Daily price change
- `opening_price`, `closing_price`: OHLC data
- `vwap`: Volume weighted average price
- `market_cap`, `pe_ratio`: Fundamental metrics
- `volatility_20d`: 20-day volatility

#### 2. Technical Indicators (`technical_indicators`)
- `rsi_14`: 14-period RSI
- `macd_line`, `macd_signal`: MACD indicators
- `bollinger_upper`, `bollinger_lower`: Bollinger bands
- `sma_20`, `sma_50`: Simple moving averages
- `ema_12`, `ema_26`: Exponential moving averages
- `atr_14`: Average True Range

#### 3. Market Sentiment (`market_sentiment`)
- `sentiment_score`: Overall sentiment (-1 to 1)
- `news_sentiment`, `social_sentiment`: Sentiment sources
- `analyst_rating`: Average analyst rating
- `price_momentum_1d`, `price_momentum_7d`: Momentum indicators
- `volume_momentum`: Volume-based momentum
- `sector_performance`: Sector relative performance

### Feature Services

#### 1. AI Trading Decision Service (`ai_trading_decision_v1`)
Core features for trading decisions:
- Price and volume data
- Key technical indicators
- Sentiment scores

#### 2. AI Risk Assessment Service (`ai_risk_assessment_v1`)
Features for risk evaluation:
- Volatility measures
- Price ranges
- Sentiment indicators

#### 3. AI Market Analysis Service (`ai_market_analysis_v1`)
Comprehensive market analysis features:
- All daily market features
- All technical indicators
- Sentiment and sector data

## Setup Instructions

### 1. Prerequisites
- Python 3.8+
- Docker and Docker Compose
- PostgreSQL (via docker-compose)
- Redis (via docker-compose)

### 2. Install Dependencies
```bash
pip install feast pandas pyarrow
```

### 3. Generate Sample Data
```bash
cd ai_assistant/feature_repo
python generate_sample_data.py
```

### 4. Initialize Feature Store
```bash
python init_feast.py
```

### 5. Start Services
```bash
# From project root
docker-compose up -d postgres redis feast
```

## Usage

### Python SDK
```python
from feast import FeatureStore

# Initialize feature store
store = FeatureStore(repo_path="ai_assistant/feature_repo")

# Get online features for trading decision
features = [
    "daily_market_features:closing_price",
    "daily_market_features:daily_volume", 
    "technical_indicators:rsi_14",
    "market_sentiment:sentiment_score"
]

entity_rows = [{"ticker": "AAPL"}]

online_features = store.get_online_features(
    features=features,
    entity_rows=entity_rows
)

print(online_features.to_df())
```

### Feature Server API
The Feast feature server runs on port 6566 and provides REST API access:

```bash
# Get online features
curl -X POST "http://localhost:6566/get-online-features" \
  -H "Content-Type: application/json" \
  -d '{
    "features": [
      "daily_market_features:closing_price",
      "technical_indicators:rsi_14"
    ],
    "entities": {
      "ticker": ["AAPL", "GOOGL"]
    }
  }'
```

### Feature Services
Use predefined feature services for common use cases:

```python
# Trading decision features
trading_features = store.get_feature_service("ai_trading_decision_v1")

# Risk assessment features  
risk_features = store.get_feature_service("ai_risk_assessment_v1")

# Market analysis features
analysis_features = store.get_feature_service("ai_market_analysis_v1")
```

## Configuration

### Offline Store (PostgreSQL)
- **Host**: postgres (Docker service)
- **Database**: trading_system
- **Schema**: public

### Online Store (Redis)
- **Host**: redis (Docker service)
- **Port**: 6379
- **Database**: 0

### Feature Server
- **Host**: 0.0.0.0
- **Port**: 6566
- **Metrics**: Enabled on port 8080

## Data Sources

### Market Data Source
- **Type**: Parquet file
- **Path**: `data/market_data.parquet`
- **Timestamp Field**: `event_timestamp`
- **Created Timestamp**: `created_timestamp`

## Monitoring

### Health Checks
- Feature server health: `http://localhost:6566/health`
- Metrics endpoint: `http://localhost:8080/metrics`

### Logs
```bash
# View Feast service logs
docker-compose logs feast

# View feature server logs
docker-compose logs -f feast
```

## Development

### Adding New Features
1. Define new feature views in `features.py`
2. Update data generation in `generate_sample_data.py`
3. Run initialization: `python init_feast.py`
4. Test with sample queries

### Data Updates
- Historical data: Update Parquet files and re-materialize
- Real-time data: Use Feast's streaming ingestion capabilities
- Batch updates: Schedule materialization jobs

## Integration with AI Assistant

The AI Assistant integrates with this feature store to:

1. **Enhance Trading Decisions**: Access real-time market features
2. **Risk Assessment**: Evaluate position risks using volatility features
3. **Market Analysis**: Provide comprehensive market insights
4. **Backtesting**: Access historical features for strategy validation

## Troubleshooting

### Common Issues

1. **Feature Store Not Found**
   - Ensure `feature_store.yaml` exists
   - Check working directory

2. **Connection Errors**
   - Verify PostgreSQL and Redis are running
   - Check Docker service status

3. **Feature Not Found**
   - Run `python init_feast.py` to apply definitions
   - Verify feature names in `features.py`

4. **Materialization Errors**
   - Check Redis connectivity
   - Verify data source paths

### Debug Commands
```bash
# List all features
feast feature-views list

# Describe feature view
feast feature-views describe daily_market_features

# Test feature retrieval
feast materialize-incremental $(date -u +%Y-%m-%dT%H:%M:%S)
```

## Next Steps

1. **Production Setup**: Configure production databases
2. **Real Data Integration**: Connect to live market data feeds
3. **Feature Engineering**: Add more sophisticated features
4. **Monitoring**: Set up feature quality monitoring
5. **Automation**: Schedule regular materialization jobs

For more information, see the [Feast documentation](https://docs.feast.dev/).