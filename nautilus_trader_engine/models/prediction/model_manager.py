import json
from nautilus_trader_engine.models.prediction.lstm_predictor import LSTMPredictor

class ModelManager:
    """
    Manages the loading, versioning, and access of prediction models.
    This class uses a mock implementation to simulate model management for development.
    """

    def __init__(self, model_registry_path: str):
        self.model_registry_path = model_registry_path
        self._load_model_registry()
        self.loaded_models = {}

    def _load_model_registry(self):
        """
        Loads the model registry from a JSON file.
        In a real system, this might connect to a dedicated model registry service.
        """
        try:
            with open(self.model_registry_path, 'r') as f:
                self.model_registry = json.load(f)
        except FileNotFoundError:
            # Create a mock registry if the file doesn't exist
            print(f"Warning: Model registry not found at {self.model_registry_path}. Creating a mock registry.")
            self.model_registry = {
                "lstm_v1": {
                    "type": "lstm",
                    "path": "models/lstm_v1.h5",
                    "config": {"features": ["close", "rsi"], "prediction_horizons": [1, 5]}
                },
                "lstm_v2": {
                    "type": "lstm",
                    "path": "models/lstm_v2.h5",
                    "config": {"features": ["close", "rsi", "macd"], "prediction_horizons": [1, 5, 15]}
                }
            }
        print("Model registry loaded.")

    def get_model(self, model_name: str):
        """
        Loads and returns a model instance based on its name from the registry.
        Caches loaded models to avoid reloading them.
        """
        if model_name in self.loaded_models:
            return self.loaded_models[model_name]

        if model_name not in self.model_registry:
            raise ValueError(f"Model '{model_name}' not found in the registry.")

        model_info = self.model_registry[model_name]
        model_type = model_info.get("type")
        
        model = None
        if model_type == "lstm":
            # This is where we would load a real model. For now, we use our mock predictor.
            model = LSTMPredictor(model_path=model_info["path"], config=model_info["config"])
            print(f"Mock LSTM model '{model_name}' loaded.")
        else:
            raise NotImplementedError(f"Model type '{model_type}' is not supported.")
            
        self.loaded_models[model_name] = model
        return model

    def list_models(self) -> list:
        """Returns a list of all available models in the registry."""
        return list(self.model_registry.keys())

    def get_model_info(self, model_name: str) -> dict:
        """Returns the configuration information for a specific model."""
        if model_name not in self.model_registry:
            raise ValueError(f"Model '{model_name}' not found in the registry.")
        return self.model_registry[model_name]

# Example usage:
if __name__ == "__main__":
    # Create a dummy registry file for testing
    mock_registry_data = {
        "test_lstm_1": {
            "type": "lstm",
            "path": "/path/to/test_model_1.h5",
            "config": {"features": ["close"], "prediction_horizons": [1]}
        },
        "test_lstm_2": {
            "type": "lstm",
            "path": "/path/to/test_model_2.h5",
            "config": {"features": ["close", "volume"], "prediction_horizons": [1, 5, 15]}
        }
    }
    registry_file = "mock_model_registry.json"
    with open(registry_file, 'w') as f:
        json.dump(mock_registry_data, f)

    # Initialize the model manager
    manager = ModelManager(model_registry_path=registry_file)
    
    # List available models
    print("\n--- Model Manager Test ---")
    print(f"Available models: {manager.list_models()}")
    
    # Get info for a specific model
    model_name_to_test = "test_lstm_2"
    print(f"Info for '{model_name_to_test}': {manager.get_model_info(model_name_to_test)}")
    
    # Load the model
    loaded_model = manager.get_model(model_name_to_test)
    print(f"Loaded model type: {type(loaded_model)}")
    print(f"Loaded model info from instance: {loaded_model.get_model_info()}")
    
    # Try loading again (should be cached)
    cached_model = manager.get_model(model_name_to_test)
    print(f"Is the cached model the same instance? {loaded_model is cached_model}")
    print("--------------------------")

    # Clean up dummy file
    import os
    os.remove(registry_file)