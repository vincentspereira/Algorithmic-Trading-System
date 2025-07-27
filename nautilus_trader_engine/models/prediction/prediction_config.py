from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class PredictionConfig:
    """
    Configuration for the real-time prediction service.
    This class centralizes all parameters related to model selection, feature engineering, and prediction horizons.
    """

    # --- Model Configuration ---
    # Specifies which model to use from the model registry
    model_name: str = "lstm_v2"
    
    # Path to the model registry file
    model_registry_path: str = "nautilus_trader_engine/models/prediction/model_registry.json"

    # --- Feature Engineering Configuration ---
    # List of features to be used by the model
    features: List[str] = field(default_factory=lambda: ["close", "rsi", "macd"])
    
    # Configuration for specific features
    feature_configs: Dict[str, int] = field(default_factory=lambda: {
        "rsi_period": 14,
        "macd_fast_period": 12,
        "macd_slow_period": 26,
        "macd_signal_period": 9,
        "moving_average_window": 50,
    })

    # --- Prediction Horizons ---
    # Time horizons for predictions in minutes
    prediction_horizons: List[int] = field(default_factory=lambda: [1, 5, 15])

    # --- Data Processing ---
    # The number of historical data points (e.g., candles) to use for a single prediction
    sequence_length: int = 60

    def to_dict(self) -> dict:
        """Converts the configuration to a dictionary."""
        return {
            "model_name": self.model_name,
            "model_registry_path": self.model_registry_path,
            "features": self.features,
            "feature_configs": self.feature_configs,
            "prediction_horizons": self.prediction_horizons,
            "sequence_length": self.sequence_length,
        }

# Example of how to use the configuration
if __name__ == "__main__":
    # Create a default configuration instance
    default_config = PredictionConfig()
    
    # Print the default configuration
    print("--- Default Prediction Configuration ---")
    print(default_config.to_dict())
    print("--------------------------------------")
    
    # Create a custom configuration instance
    custom_config = PredictionConfig(
        model_name="custom_model_v1",
        features=["close", "volume", "bollinger_bands"],
        sequence_length=120,
        prediction_horizons=[1, 10, 30]
    )
    
    print("\n--- Custom Prediction Configuration ---")
    print(custom_config.to_dict())
    print("-------------------------------------")