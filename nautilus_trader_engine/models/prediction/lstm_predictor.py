import numpy as np

class LSTMPredictor:
    """
    Mock LSTM model for time-series prediction.
    This class simulates the behavior of a real LSTM model for development and testing purposes.
    """

    def __init__(self, model_path: str, config: dict):
        self.model_path = model_path
        self.config = config
        self._load_mock_model()

    def _load_mock_model(self):
        """
        Simulates loading a trained model.
        In a real implementation, this would load a TensorFlow/Keras model from disk.
        """
        print(f"Mock loading model from: {self.model_path}")
        # In a real scenario, you would have model loading logic here, e.g.:
        # from tensorflow.keras.models import load_model
        # self.model = load_model(self.model_path)
        self.mock_model_loaded = True

    def predict(self, input_data: np.ndarray) -> np.ndarray:
        """
        Generates a mock prediction based on the input data.
        A real implementation would use the loaded model to make a prediction.
        
        Args:
            input_data: A numpy array of historical data (e.g., prices, indicators).
        
        Returns:
            A numpy array representing the predicted values for the time horizons.
        """
        if not self.mock_model_loaded:
            raise RuntimeError("Model is not loaded.")

        # Simulate the prediction process
        # The shape of the output should match the prediction horizons
        num_horizons = len(self.config.get("prediction_horizons", [1, 5, 15]))
        
        # Generate random predictions that are slight variations of the last input value
        last_value = input_data[-1] if len(input_data) > 0 else 100
        mock_predictions = np.array([
            last_value * (1 + np.random.uniform(-0.01, 0.01)) for _ in range(num_horizons)
        ])
        
        print(f"Mock prediction generated for input shape {input_data.shape}: {mock_predictions}")
        return mock_predictions

    def get_model_info(self) -> dict:
        """Returns information about the mock model."""
        return {
            "model_path": self.model_path,
            "type": "Mock LSTM",
            "config": self.config,
            "loaded": self.mock_model_loaded
        }

# Example usage:
if __name__ == "__main__":
    mock_config = {
        "prediction_horizons": [1, 5, 15], # in minutes
        "features": ["close_price", "rsi", "macd"],
    }
    
    # Create a mock model instance
    predictor = LSTMPredictor(model_path="/path/to/mock/model.h5", config=mock_config)
    
    # Generate some mock input data (e.g., 10 time steps, 3 features)
    mock_input = np.random.rand(10, 3) * 100
    
    # Make a prediction
    predictions = predictor.predict(mock_input)
    
    # Print results
    print("\n--- Mock LSTM Predictor Test ---")
    print(f"Model Info: {predictor.get_model_info()}")
    print(f"Input Data (last value): {mock_input[-1]}")
    print(f"Prediction Output: {predictions}")
    print("---------------------------------")