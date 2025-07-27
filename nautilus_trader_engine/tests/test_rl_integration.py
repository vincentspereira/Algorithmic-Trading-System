# nautilus_trader_engine/tests/test_rl_integration.py

"""
Tests for the RL integration components.
"""

import unittest
import pandas as pd
from unittest.mock import MagicMock

from nautilus_trader_engine.rl.environment import NautilusTradingEnv
from nautilus_trader_engine.rl.agents import get_agent
from nautilus_trader_engine.rl.training.data_preprocessor import preprocess_data
from nautilus_trader_engine.rl.training.feature_extractor import add_technical_indicators

class TestRLIntegration(unittest.TestCase):

    def setUp(self):
        """Set up test data and mock objects."""
        # Create a mock backtest engine
        self.mock_engine = MagicMock()
        
        # Create a mock instrument
        self.mock_instrument = MagicMock()
        self.mock_instrument.id = "BTC/USD"
        
        # Sample data for testing
        self.sample_data = pd.DataFrame({
            "timestamp": pd.to_datetime(pd.date_range("2023-01-01", periods=100)),
            "open": 100, "high": 110, "low": 90, "close": 105, "volume": 1000
        }).set_index("timestamp")

    def test_environment_creation(self):
        """Test if the RL environment can be created."""
        env = NautilusTradingEnv(self.mock_engine, self.mock_instrument)
        self.assertIsNotNone(env)
        self.assertIn("discrete", str(env.action_space).lower())

    def test_agent_creation(self):
        """Test if RL agents can be created."""
        env = NautilusTradingEnv(self.mock_engine, self.mock_instrument)
        ppo_agent = get_agent("PPO", env)
        self.assertIsNotNone(ppo_agent)
        
        a2c_agent = get_agent("A2C", env)
        self.assertIsNotNone(a2c_agent)

    def test_data_preprocessing(self):
        """Test the data preprocessing pipeline."""
        processed_df = preprocess_data(self.sample_data, resample_period="1D")
        self.assertFalse(processed_df.isnull().values.any())
        self.assertEqual(len(processed_df), 100) # Should be unchanged for 1D

    def test_feature_extraction(self):
        """Test the feature extraction process."""
        df_with_features = add_technical_indicators(self.sample_data)
        self.assertIn("sma_30", df_with_features.columns)
        self.assertIn("rsi_14", df_with_features.columns)
        self.assertFalse(df_with_features.isnull().values.any())

if __name__ == "__main__":
    unittest.main()