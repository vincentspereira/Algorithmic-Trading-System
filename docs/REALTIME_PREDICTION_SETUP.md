# Real-Time Prediction Service Setup Guide

This document provides a comprehensive guide to setting up, configuring, and maintaining the real-time prediction service for the Algorithmic Trading System.

## 1. Architecture Overview

The real-time prediction service is designed to provide live, AI-driven forecasts of stock price movements to enhance trading decisions. The architecture consists of the following key components:

- **Kafka Integration (`prediction_stream.py`)**: Subscribes to real-time market data from Kafka topics. It processes incoming ticks and forwards them to the prediction engine.

- **Feature Engineering (`feature_engineering.py`)**: Consumes raw market data and generates technical indicators (e.g., RSI, MACD) and other features required by the prediction models.

- **Prediction Models (`lstm_predictor.py`, `model_manager.py`)**:
    - **`lstm_predictor.py`**: An LSTM-based model for time-series forecasting. (Currently a mock implementation).
    - **`model_manager.py`**: Manages the loading, versioning, and selection of different prediction models. It reads from a model registry to determine which model to use.

- **Real-Time Prediction Engine (`realtime_prediction.py`)**: The core of the service. It orchestrates the flow of data from the feature engineering component to the prediction model and generates predictions for multiple time horizons (1min, 5min, 15min) with associated confidence scores.

- **API Endpoints (`predictions.py`)**: Exposes the prediction service's functionality through a RESTful API and WebSockets:
    - `GET /predictions/realtime/{symbol}`: Fetches the latest prediction.
    - `GET /predictions/history/{symbol}`: Retrieves historical prediction data.
    - `GET /predictions/accuracy`: Provides model accuracy metrics.
    - `POST /predictions/subscribe` (WebSocket): Streams real-time predictions to connected clients.

- **Frontend Components (`/frontend/.../predictions/`)**: A suite of React components to visualize the prediction data:
    - **`PredictionWidget.tsx`**: Displays the latest predictions and confidence scores.
    - **`PredictionChart.tsx`**: Visualizes historical predicted prices against actual prices.
    - **`PredictionAlerts.tsx`**: Notifies users of high-confidence trading signals.

## 2. Model Training Process (Future Implementation)

While the current implementation uses mock models, a proper model training pipeline will be established. The planned process is as follows:

1.  **Data Collection**: Historical market data will be collected and stored in a time-series database.
2.  **Feature Generation**: The feature engineering module will be used to process the historical data and create a rich feature set.
3.  **Model Training**: The LSTM model will be trained on the historical feature set. The training process will be versioned and tracked using a tool like MLflow.
4.  **Model Evaluation**: The model's performance will be evaluated against a hold-out test set to measure its accuracy and other relevant metrics.
5.  **Model Registration**: Once a model is deemed satisfactory, it will be registered in the `model_registry.json` file, making it available for the prediction service to use.

## 3. Configuration Guide

The prediction service is configured through the `prediction_config.py` file. This allows for easy adjustments without modifying the core service logic.

-   **`model_name`**: Specifies the name of the model to be loaded from the registry (e.g., `"lstm_v2"`).
-   **`features`**: A list of the features the model requires (e.g., `["close", "rsi", "macd"]`).
-   **`prediction_horizons`**: The time horizons (in minutes) for which to generate predictions (e.g., `[1, 5, 15]`).
-   **`sequence_length`**: The number of historical data points to feed into the model for a single prediction.

To change the model or its parameters, modify the `PredictionConfig` dataclass in this file.

## 4. Performance Optimization Tips

For a high-frequency trading environment, the performance of the prediction service is critical. Here are some optimization strategies:

-   **Batch Processing**: Instead of processing one tick at a time, batch multiple ticks together for more efficient feature generation and prediction.
-   **Hardware Acceleration**: Utilize GPUs for model inference, as deep learning models like LSTMs are significantly faster on GPU hardware.
-   **Asynchronous Operations**: The service is built with `asyncio` to handle concurrent operations efficiently. Ensure all I/O-bound tasks (like Kafka messaging and database calls) are non-blocking.
-   **Caching**: Implement a caching layer (e.g., using Redis) to store recent predictions and features. This can reduce redundant computations and lower latency for API requests.
-   **Optimized Libraries**: Use highly optimized libraries for numerical computations, such as `numpy`, `pandas`, and `TA-Lib` (the real version, not the mock).

By following this guide, you can effectively manage and scale the real-time prediction service to meet the demands of the algorithmic trading system.