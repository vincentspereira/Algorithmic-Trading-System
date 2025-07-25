# Forecasting Models Integration for AI Assistant

## Overview

The AI Assistant now includes advanced forecasting capabilities for stock price prediction using multiple machine learning and statistical models. This integration provides sophisticated predictive analytics through a unified interface that supports various forecasting algorithms, hyperparameter optimization, and uncertainty quantification.

## Architecture

### Core Components

```
ai_assistant/
├── forecasting_models.py      # Base forecasting infrastructure
├── lstm_predictor.py          # LSTM neural network implementation
├── stock_prediction_models.py # Multiple prediction algorithms
├── model_training.py          # Training pipeline with optimization
├── tools.py                   # LangChain tool integration
└── models/                    # Model storage and configurations
    ├── model_registry.json    # Registry of available models
    ├── training_configs/      # Configuration templates
    └── sample_models/         # Pre-trained sample models
```

### Integration Flow

1. **Natural Language Query** → User requests prediction via AI Assistant
2. **Query Parsing** → Extract ticker, horizon, model preferences
3. **Data Loading** → Fetch historical data from Feast feature store
4. **Model Selection** → Auto-select best model or use specified type
5. **Prediction** → Generate forecasts with confidence intervals
6. **Response Formatting** → Present results in human-readable format

## Supported Models

### 1. LSTM (Long Short-Term Memory)
- **Type**: Deep Learning Neural Network
- **Best For**: Complex patterns, long sequences, non-linear relationships
- **Performance**: RMSE 2.0-4.0, High accuracy for complex patterns
- **Training Time**: Medium to High (GPU recommended)
- **Interpretability**: Low

**Features:**
- Bidirectional LSTM support
- Attention mechanisms
- Monte Carlo dropout for uncertainty quantification
- Configurable architecture (layers, units, dropout)

### 2. ARIMA (AutoRegressive Integrated Moving Average)
- **Type**: Statistical Time Series Model
- **Best For**: Trend analysis, seasonal patterns, statistical modeling
- **Performance**: RMSE 3.0-5.0, Good for trending data
- **Training Time**: Low
- **Interpretability**: High

**Features:**
- Auto ARIMA parameter selection
- Stationarity testing
- Seasonal decomposition
- Statistical confidence intervals

### 3. Random Forest
- **Type**: Ensemble Machine Learning
- **Best For**: Feature-based prediction, interpretability, robustness
- **Performance**: RMSE 2.5-4.5, Robust to outliers
- **Training Time**: Low to Medium
- **Interpretability**: High

**Features:**
- Feature importance analysis
- Out-of-bag error estimation
- Handles mixed data types
- Resistant to overfitting

### 4. XGBoost
- **Type**: Gradient Boosting Framework
- **Best For**: Structured data, feature interactions, competitive performance
- **Performance**: RMSE 2.2-3.8, Often best overall performance
- **Training Time**: Medium
- **Interpretability**: Medium

**Features:**
- Advanced regularization
- Early stopping
- Feature importance
- Handles missing values
- GPU acceleration support

### 5. Prophet
- **Type**: Time Series Forecasting Tool (Facebook)
- **Best For**: Trend and seasonality, holiday effects, missing data
- **Performance**: RMSE 2.8-4.2, Excellent for seasonal data
- **Training Time**: Medium
- **Interpretability**: High

**Features:**
- Automatic seasonality detection
- Holiday effect modeling
- Trend changepoint detection
- Handles missing data gracefully

### 6. Ensemble Models
- **Type**: Combination of Multiple Models
- **Best For**: Maximum accuracy, risk reduction
- **Performance**: Often best overall, combines strengths
- **Training Time**: High (trains multiple models)
- **Interpretability**: Medium

**Features:**
- Weighted averaging based on performance
- Dynamic model selection
- Uncertainty aggregation
- Robust to individual model failures

## Usage Examples

### Basic Prediction via AI Assistant

```python
# Natural language queries supported:
"Predict AAPL price for next 7 days"
"What will GOOGL stock price be in 30 days?"
"Forecast MSFT price using LSTM model for 1 week"
"Use ensemble model to predict TSLA price with confidence intervals"
```

### Programmatic Usage

#### 1. Simple Prediction

```python
from ai_assistant.forecasting_models import ForecastingModelFactory, ModelConfig, ModelType, PredictionHorizon
from ai_assistant.model_training import ModelTrainer, create_training_config
from datetime import datetime, timedelta

# Create model configuration
config = ModelConfig(
    model_type=ModelType.LSTM,
    prediction_horizon=PredictionHorizon.SEVEN_DAYS,
    lookback_window=60,
    features=['closing_price', 'daily_volume', 'sma_20', 'rsi_14']
)

# Create and train model
model = ForecastingModelFactory.create_model(ModelType.LSTM, config)
performance = model.train(historical_data)

# Make prediction
prediction_result = model.predict(data, ticker="AAPL")
print(f"Predicted prices: {prediction_result.predictions}")
```

#### 2. Model Training with Optimization

```python
from ai_assistant.model_training import ModelTrainer, create_training_config

# Create training configuration
training_config = create_training_config(
    model_type="xgboost",
    prediction_horizon=7,
    optimize_hyperparams=True,
    n_trials=100
)

# Train model with hyperparameter optimization
trainer = ModelTrainer(training_config)
result = trainer.train_model(
    ticker="AAPL",
    start_date=datetime.now() - timedelta(days=365),
    end_date=datetime.now()
)

print(f"Best hyperparameters: {result.best_hyperparams}")
print(f"Performance: RMSE={result.performance.rmse:.4f}")
```

#### 3. Batch Training

```python
from ai_assistant.model_training import BatchTrainer

# Create batch trainer
batch_trainer = BatchTrainer(base_config)

# Train multiple models for multiple tickers
results = batch_trainer.train_multiple_models(
    tickers=["AAPL", "GOOGL", "MSFT"],
    model_types=[ModelType.LSTM, ModelType.XGBOOST, ModelType.RANDOM_FOREST],
    start_date=datetime.now() - timedelta(days=365),
    end_date=datetime.now()
)

# Get best models per ticker
best_models = batch_trainer.get_best_models_per_ticker(metric="rmse")
```

#### 4. Model Comparison

```python
from ai_assistant.stock_prediction_models import compare_models, select_best_model

# Compare multiple models
comparison_results = compare_models(
    data=historical_data,
    models=['lstm', 'xgboost', 'random_forest', 'prophet'],
    prediction_horizon=7
)

# Select best performing model
best_model_name, best_model = select_best_model(
    data=historical_data,
    metric='rmse'
)
```

## Feature Engineering

### Supported Features

#### Price Data
- `closing_price`: Daily closing price
- `opening_price`: Daily opening price
- `daily_high`: Daily high price
- `daily_low`: Daily low price

#### Volume Data
- `daily_volume`: Daily trading volume
- `volume_momentum`: Volume momentum indicator

#### Technical Indicators
- `sma_20`, `sma_50`: Simple moving averages
- `ema_12`, `ema_26`: Exponential moving averages
- `rsi_14`: Relative Strength Index
- `macd_line`, `macd_signal`: MACD indicators
- `bollinger_upper`, `bollinger_lower`: Bollinger Bands
- `atr_14`: Average True Range

#### Volatility Measures
- `volatility_20d`: 20-day rolling volatility

#### Sentiment Indicators
- `sentiment_score`: Overall sentiment score
- `news_sentiment`: News-based sentiment
- `analyst_rating`: Average analyst rating

### Feature Store Integration

The system integrates with Feast feature store for consistent feature serving:

```python
from ai_assistant.forecasting_models import FeastDataLoader

# Load features from Feast
data_loader = FeastDataLoader()
features = data_loader.load_historical_data(
    ticker="AAPL",
    start_date=start_date,
    end_date=end_date,
    features=['closing_price', 'sma_20', 'rsi_14']
)
```

## Model Training Pipeline

### Hyperparameter Optimization

The system uses Optuna for automated hyperparameter optimization:

```python
# Optimization is configured per model type
optimization_config = {
    'n_trials': 100,
    'timeout': 3600,  # 1 hour
    'metric': 'rmse',
    'cv_folds': 5
}
```

### Cross-Validation

Time series cross-validation ensures robust performance estimation:

- **Time Series Split**: Respects temporal order
- **Walk-Forward Validation**: Simulates real-world deployment
- **Multiple Metrics**: RMSE, MAE, MAPE, Directional Accuracy

### Performance Metrics

#### Regression Metrics
- **RMSE**: Root Mean Square Error
- **MAE**: Mean Absolute Error
- **MAPE**: Mean Absolute Percentage Error
- **R²**: Coefficient of Determination

#### Trading-Specific Metrics
- **Directional Accuracy**: Percentage of correct direction predictions
- **Sharpe Ratio**: Risk-adjusted returns
- **Maximum Drawdown**: Largest peak-to-trough decline

## Model Persistence and Versioning

### Model Storage

Models are stored with comprehensive metadata:

```
models/
├── lstm_AAPL_7d_20240125_120000.pkl          # Model file
├── lstm_AAPL_7d_20240125_120000_metadata.json # Metadata
└── model_registry.json                        # Registry
```

### Model Registry

The model registry tracks all trained models:

```json
{
  "model_id": "lstm_AAPL_7d_sample",
  "model_type": "lstm",
  "ticker": "AAPL",
  "prediction_horizon": 7,
  "performance": {
    "rmse": 2.45,
    "mae": 1.82,
    "directional_accuracy": 0.65
  },
  "created_at": "2024-01-25T00:00:00Z",
  "status": "active"
}
```

### Loading Trained Models

```python
from ai_assistant.model_training import load_trained_model

# Load a specific model
model = load_trained_model("ai_assistant/models/sample_models/lstm_AAPL_7d_sample.pkl")

# Make predictions
prediction = model.predict(data, ticker="AAPL")
```

## Configuration Management

### Training Configurations

Template configurations are provided for each model type:

```json
{
  "model_type": "lstm",
  "default_config": {
    "prediction_horizon": 7,
    "lookback_window": 60,
    "hyperparameters": {
      "hidden_size": 128,
      "num_layers": 2,
      "dropout": 0.2,
      "learning_rate": 0.001
    }
  },
  "optimization_space": {
    "hidden_size": {"type": "categorical", "choices": [64, 128, 256]},
    "num_layers": {"type": "int", "low": 1, "high": 4}
  }
}
```

## Performance Monitoring

### Model Performance Tracking

- **Training Metrics**: Loss curves, validation scores
- **Prediction Quality**: Out-of-sample performance
- **Drift Detection**: Model degradation over time
- **A/B Testing**: Compare model versions

### Experiment Tracking

Integration with MLflow for experiment management:

```python
import mlflow

# Automatic experiment logging
with mlflow.start_run():
    mlflow.log_params(hyperparameters)
    mlflow.log_metrics(performance_metrics)
    mlflow.log_model(trained_model)
```

## Error Handling and Robustness

### Data Quality Validation

```python
from ai_assistant.forecasting_models import validate_data_quality

# Validate input data
quality_report = validate_data_quality(data, required_columns)
if not quality_report["is_valid"]:
    print(f"Data issues: {quality_report['issues']}")
```

### Graceful Degradation

- **Missing Features**: Automatic feature selection
- **Insufficient Data**: Fallback to simpler models
- **Model Failures**: Ensemble fallback mechanisms
- **API Timeouts**: Cached predictions

## Security and Compliance

### Data Privacy
- No sensitive data stored in models
- Feature anonymization support
- Audit trail for all predictions

### Model Governance
- Version control for all models
- Performance monitoring and alerts
- Automated model retirement

## Deployment Considerations

### Scalability
- **Batch Predictions**: Process multiple requests efficiently
- **Model Caching**: Reduce loading overhead
- **Feature Caching**: Cache frequently used features
- **GPU Support**: Accelerate LSTM training and inference

### Monitoring
- **Prediction Latency**: Track response times
- **Model Accuracy**: Monitor prediction quality
- **Resource Usage**: CPU, memory, GPU utilization
- **Error Rates**: Track and alert on failures

## Best Practices

### Model Selection
1. **Start Simple**: Begin with Random Forest or XGBoost
2. **Add Complexity**: Use LSTM for complex patterns
3. **Ensemble**: Combine models for best performance
4. **Validate**: Always use time series cross-validation

### Feature Engineering
1. **Domain Knowledge**: Include relevant technical indicators
2. **Feature Selection**: Remove redundant features
3. **Scaling**: Normalize features appropriately
4. **Lag Features**: Include historical values

### Training
1. **Data Quality**: Ensure clean, consistent data
2. **Hyperparameter Tuning**: Use systematic optimization
3. **Early Stopping**: Prevent overfitting
4. **Regular Retraining**: Update models with new data

### Production
1. **Model Versioning**: Track all model versions
2. **A/B Testing**: Compare model performance
3. **Monitoring**: Track prediction quality
4. **Fallbacks**: Have backup models ready

## Troubleshooting

### Common Issues

#### 1. Poor Model Performance
- **Check Data Quality**: Validate input features
- **Increase Training Data**: More data often helps
- **Feature Engineering**: Add relevant features
- **Hyperparameter Tuning**: Optimize model parameters

#### 2. Training Failures
- **Memory Issues**: Reduce batch size or model complexity
- **Convergence Problems**: Adjust learning rate
- **Data Issues**: Check for NaN values or outliers

#### 3. Prediction Errors
- **Model Not Trained**: Ensure model is properly trained
- **Feature Mismatch**: Check feature consistency
- **Data Format**: Validate input data format

### Debugging Tools

```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Validate model configuration
config = ModelConfig(...)
print(f"Config validation: {config}")

# Check data quality
quality_report = validate_data_quality(data, features)
print(f"Data quality: {quality_report}")
```

## Future Enhancements

### Planned Features
1. **Real-time Predictions**: Streaming prediction pipeline
2. **Multi-asset Models**: Cross-asset prediction models
3. **Reinforcement Learning**: RL-based trading strategies
4. **Explainable AI**: Enhanced model interpretability
5. **AutoML**: Automated model selection and tuning

### Integration Roadmap
1. **Phase 1**: Basic prediction capabilities ✅
2. **Phase 2**: Advanced models and optimization ✅
3. **Phase 3**: Real-time streaming predictions
4. **Phase 4**: Multi-asset and portfolio optimization
5. **Phase 5**: Reinforcement learning integration

## Support and Maintenance

### Documentation
- **API Reference**: Detailed function documentation
- **Examples**: Comprehensive usage examples
- **Tutorials**: Step-by-step guides

### Testing
- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end workflow testing
- **Performance Tests**: Scalability and speed testing

### Updates
- **Model Updates**: Regular model retraining
- **Feature Updates**: New feature additions
- **Bug Fixes**: Issue resolution and patches

---

## Quick Start Guide

### 1. Basic Usage via AI Assistant

Simply ask the AI Assistant:
```
"Predict AAPL price for next 7 days"
```

### 2. Programmatic Usage

```python
from ai_assistant.tools import predict_stock_price_tool

# Make a prediction
result = predict_stock_price_tool(
    query="Predict GOOGL price for next week using XGBoost",
    include_confidence=True
)
print(result)
```

### 3. Train Custom Model

```python
from ai_assistant.model_training import ModelTrainer, create_training_config

# Create configuration
config = create_training_config(
    model_type="lstm",
    prediction_horizon=7,
    optimize_hyperparams=True
)

# Train model
trainer = ModelTrainer(config)
result = trainer.train_model("AAPL", start_date, end_date)
```

This comprehensive forecasting system provides the AI Assistant with sophisticated predictive capabilities while maintaining ease of use and robust performance.