# Forecasting Models Directory

This directory contains pre-trained forecasting models and their configurations for stock price prediction.

## Directory Structure

```
models/
├── README.md                    # This file
├── model_registry.json         # Registry of available models
├── training_configs/           # Training configuration templates
│   ├── lstm_config.json
│   ├── arima_config.json
│   ├── random_forest_config.json
│   ├── xgboost_config.json
│   └── ensemble_config.json
├── sample_models/              # Sample pre-trained models
│   ├── lstm_AAPL_7d_sample.pkl
│   ├── lstm_AAPL_7d_sample_metadata.json
│   ├── random_forest_GOOGL_7d_sample.pkl
│   ├── random_forest_GOOGL_7d_sample_metadata.json
│   ├── xgboost_MSFT_7d_sample.pkl
│   └── xgboost_MSFT_7d_sample_metadata.json
└── performance_benchmarks/     # Model performance benchmarks
    └── benchmark_results.json
```

## Model Registry

The `model_registry.json` file contains metadata about all available models including:
- Model type and configuration
- Training parameters and hyperparameters
- Performance metrics
- File paths and timestamps
- Supported tickers and prediction horizons

## Sample Models

Sample pre-trained models are provided for demonstration and testing purposes:

### LSTM Models
- **lstm_AAPL_7d_sample.pkl**: LSTM model trained on AAPL data for 7-day predictions
- Features: OHLCV data, technical indicators (SMA, RSI, MACD)
- Performance: RMSE ~2.5, MAE ~1.8, Directional Accuracy ~65%

### Random Forest Models
- **random_forest_GOOGL_7d_sample.pkl**: Random Forest model for GOOGL 7-day predictions
- Features: Price data, volume, volatility, technical indicators
- Performance: RMSE ~3.2, MAE ~2.1, Directional Accuracy ~62%

### XGBoost Models
- **xgboost_MSFT_7d_sample.pkl**: XGBoost model for MSFT 7-day predictions
- Features: Comprehensive feature set including sentiment indicators
- Performance: RMSE ~2.8, MAE ~1.9, Directional Accuracy ~68%

## Usage

### Loading a Pre-trained Model

```python
from ai_assistant.model_training import load_trained_model

# Load a specific model
model = load_trained_model("ai_assistant/models/sample_models/lstm_AAPL_7d_sample.pkl")

# Make predictions
prediction_result = model.predict(data, ticker="AAPL")
```

### Training New Models

```python
from ai_assistant.model_training import ModelTrainer, create_training_config
from datetime import datetime, timedelta

# Create training configuration
config = create_training_config(
    model_type="lstm",
    prediction_horizon=7,
    optimize_hyperparams=True
)

# Train model
trainer = ModelTrainer(config)
result = trainer.train_model(
    ticker="AAPL",
    start_date=datetime.now() - timedelta(days=365),
    end_date=datetime.now()
)
```

## Model Performance Benchmarks

Performance benchmarks are maintained in `performance_benchmarks/benchmark_results.json` and include:
- Cross-validation scores
- Out-of-sample test results
- Comparison across different model types
- Performance by market conditions (bull/bear markets, high/low volatility)

## Configuration Templates

Training configuration templates are provided for each model type:
- **lstm_config.json**: LSTM hyperparameters and architecture settings
- **arima_config.json**: ARIMA model parameters and seasonality settings
- **random_forest_config.json**: Random Forest ensemble parameters
- **xgboost_config.json**: XGBoost gradient boosting parameters
- **ensemble_config.json**: Ensemble model combination settings

## Notes

- Sample models are trained on synthetic/demo data and should not be used for actual trading
- For production use, retrain models with real market data and proper validation
- Model performance may vary significantly based on market conditions and data quality
- Regular retraining is recommended to maintain model accuracy

## Model Versioning

Models follow the naming convention:
`{model_type}_{ticker}_{horizon}d_{timestamp}.pkl`

Where:
- `model_type`: lstm, arima, random_forest, xgboost, prophet, ensemble
- `ticker`: Stock ticker symbol (e.g., AAPL, GOOGL, MSFT)
- `horizon`: Prediction horizon in days (1, 7, 30)
- `timestamp`: Training timestamp (YYYYMMDD_HHMMSS)

Each model file is accompanied by a metadata JSON file with the same name but `_metadata.json` suffix.