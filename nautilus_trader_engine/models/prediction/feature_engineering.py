import pandas as pd
import numpy as np

class FeatureEngineering:
    """
    Handles the creation of technical indicators and other market features.
    This class provides mock implementations for feature generation for development purposes.
    """

    def __init__(self, config: dict):
        self.config = config

    def _calculate_mock_rsi(self, data: pd.Series, period: int = 14) -> pd.Series:
        """
        Generates a mock Relative Strength Index (RSI).
        In a real implementation, this would use a library like TA-Lib.
        """
        # Simulate RSI values oscillating between 30 and 70
        mock_rsi = 50 + (np.random.randn(len(data)) * 10)
        mock_rsi = np.clip(mock_rsi, 30, 70)
        return pd.Series(mock_rsi, index=data.index)

    def _calculate_mock_macd(self, data: pd.Series, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        """
        Generates a mock Moving Average Convergence Divergence (MACD).
        A real implementation would use a proper financial library.
        """
        # Simulate MACD values
        last_price = data.iloc[-1] if not data.empty else 100
        mock_macd = (np.random.randn(len(data)) * 0.1) * last_price
        mock_signal = mock_macd.rolling(window=signal_period, min_periods=1).mean()
        mock_hist = mock_macd - mock_signal
        return pd.Series(mock_macd, index=data.index), pd.Series(mock_signal, index=data.index), pd.Series(mock_hist, index=data.index)

    def generate_features(self, market_data: pd.DataFrame) -> pd.DataFrame:
        """
        Generates a DataFrame with all the required features for the prediction model.
        
        Args:
            market_data: A pandas DataFrame with 'close' prices and other raw data.
        
        Returns:
            A pandas DataFrame with the original data and the new feature columns.
        """
        if 'close' not in market_data.columns:
            raise ValueError("Market data must contain a 'close' column.")

        features_df = market_data.copy()
        
        # Generate mock features based on the configuration
        if "rsi" in self.config.get("features", []):
            features_df['rsi'] = self._calculate_mock_rsi(features_df['close'])
        
        if "macd" in self.config.get("features", []):
            features_df['macd'], features_df['macd_signal'], features_df['macd_hist'] = self._calculate_mock_macd(features_df['close'])
        
        # Add other potential mock features
        if "moving_average" in self.config.get("features", []):
            window = self.config.get("moving_average_window", 20)
            features_df['moving_average'] = features_df['close'].rolling(window=window).mean().fillna(method='bfill')

        print(f"Mock features generated for data shape {market_data.shape}")
        
        return features_df.dropna()

# Example usage:
if __name__ == "__main__":
    mock_config = {
        "features": ["rsi", "macd", "moving_average"],
        "moving_average_window": 50
    }
    
    # Create a feature engineering instance
    feature_generator = FeatureEngineering(config=mock_config)
    
    # Generate some mock market data
    dates = pd.to_datetime(pd.date_range(start="2023-01-01", periods=100))
    mock_data = pd.DataFrame({
        "open": np.random.rand(100) * 10 + 100,
        "high": np.random.rand(100) * 10 + 105,
        "low": np.random.rand(100) * 10 + 95,
        "close": np.random.rand(100) * 10 + 100,
        "volume": np.random.rand(100) * 10000,
    }, index=dates)
    
    # Generate features
    features = feature_generator.generate_features(mock_data)
    
    # Print results
    print("\n--- Mock Feature Engineering Test ---")
    print(f"Feature Engineering Config: {feature_generator.config}")
    print("Generated Features DataFrame (last 5 rows):")
    print(features.tail())
    print("\nColumns:")
    print(features.columns)
    print("---------------------------------------")