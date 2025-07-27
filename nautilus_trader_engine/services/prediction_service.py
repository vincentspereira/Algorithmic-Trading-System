"""
Prediction Service
This service loads and manages the AI/ML models for generating trading signals.
"""

import logging
import pandas as pd
from typing import Dict, Any

from ai_assistant.forecasting_models import (
    BaseForecastingModel,
    ForecastingModelFactory,
    ModelConfig,
    ModelType,
    PredictionHorizon,
    PredictionResult,
)

logger = logging.getLogger(__name__)

class PredictionService:
    """
    Manages the loading of forecasting models and the generation of predictions.
    """

    def __init__(self, model_type: ModelType = ModelType.ENSEMBLE):
        self.model_type = model_type
        self.model: BaseForecastingModel = self._load_model()

    def _load_model(self) -> BaseForecastingModel:
        """
        Loads a pre-trained forecasting model.
        """
        try:
            # For now, we'll use a default configuration.
            # In the future, this could be loaded from a config file.
            config = ModelConfig(
                model_type=self.model_type,
                prediction_horizon=PredictionHorizon.ONE_DAY,
                lookback_window=60,
            )

            model = ForecastingModelFactory.create_model(self.model_type, config)
            # In a real scenario, we would load a pre-trained model like this:
            # model.load_model('path/to/your/model.pkl')
            logger.info(f"Successfully loaded {self.model_type.value} model.")
            return model

        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise

    def predict(self, data: Dict[str, Any]) -> PredictionResult:
        """
        Generates a prediction for the given market data.

        Args:
            data: A dictionary representing the market data message from Kafka.

        Returns:
            A PredictionResult object containing the trading signal.
        """
        try:
            # Convert the incoming data to a pandas DataFrame
            df = pd.DataFrame(data['data'])
            df['event_timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            df.set_index('event_timestamp', inplace=True)

            # For now, we'll "train" the model on the fly with the incoming data.
            # In a real production system, the model would be pre-trained.
            if not self.model.is_trained:
                self.model.train(df)

            # Generate a prediction
            prediction = self.model.predict(df, ticker=data['symbol'])
            logger.info(f"Generated prediction for {data['symbol']}: {prediction.predictions}")

            return prediction

        except Exception as e:
            logger.error(f"Error generating prediction: {e}")
            raise