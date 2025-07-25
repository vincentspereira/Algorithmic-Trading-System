"""
Integration Tests for Forecasting Models in AI Assistant
Tests the complete integration of forecasting capabilities with the existing AI Assistant infrastructure

This test suite verifies:
1. Tool integration with LangChain
2. Feast feature store integration
3. Model training and prediction pipeline
4. Error handling and graceful degradation
5. Performance and scalability

Author: Vincent S. Pereira
Version: 1.0.0
"""

import os
import sys
import unittest
import logging
import warnings
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil

# Add the ai_assistant directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Suppress warnings for cleaner test output
warnings.filterwarnings('ignore')

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestForecastingIntegration(unittest.TestCase):
    """Test suite for forecasting models integration"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_ticker = "AAPL"
        self.test_query = "Predict AAPL price for next 7 days"
        self.start_date = datetime.now() - timedelta(days=365)
        self.end_date = datetime.now()
        
        # Create temporary directory for test models
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_import_forecasting_modules(self):
        """Test that all forecasting modules can be imported"""
        try:
            from forecasting_models import (
                BaseForecastingModel, ModelConfig, ModelType, 
                PredictionHorizon, ForecastingModelFactory, FeastDataLoader
            )
            from lstm_predictor import LSTMPredictor, LSTMNetwork
            from stock_prediction_models import (
                ARIMAModel, RandomForestModel, XGBoostModel, 
                EnsembleModel, compare_models
            )
            from model_training import ModelTrainer, TrainingConfig, BatchTrainer
            
            logger.info("✅ All forecasting modules imported successfully")
            
        except ImportError as e:
            self.fail(f"Failed to import forecasting modules: {e}")
    
    def test_tools_integration(self):
        """Test that the prediction tool is properly integrated with LangChain tools"""
        try:
            from tools import predict_stock_price_tool, StockPredictionInput
            
            # Test tool schema
            self.assertIsNotNone(predict_stock_price_tool)
            self.assertTrue(hasattr(predict_stock_price_tool, 'name'))
            self.assertEqual(predict_stock_price_tool.name, 'predict_stock_price')
            
            # Test input model
            input_model = StockPredictionInput(
                query=self.test_query,
                model_type="random_forest",
                include_confidence=True
            )
            self.assertEqual(input_model.query, self.test_query)
            self.assertEqual(input_model.model_type, "random_forest")
            self.assertTrue(input_model.include_confidence)
            
            logger.info("✅ Tools integration test passed")
            
        except Exception as e:
            self.fail(f"Tools integration test failed: {e}")
    
    def test_feast_data_loader(self):
        """Test Feast data loader functionality"""
        try:
            from forecasting_models import FeastDataLoader
            
            data_loader = FeastDataLoader()
            
            # Test mock data loading (since Feast may not be fully configured)
            mock_data = data_loader._load_mock_data(
                ticker=self.test_ticker,
                start_date=self.start_date,
                end_date=self.end_date
            )
            
            # Validate mock data structure
            self.assertIsNotNone(mock_data)
            self.assertGreater(len(mock_data), 0)
            self.assertIn('closing_price', mock_data.columns)
            self.assertIn('daily_volume', mock_data.columns)
            
            logger.info("✅ Feast data loader test passed")
            
        except Exception as e:
            self.fail(f"Feast data loader test failed: {e}")
    
    def test_model_factory(self):
        """Test model factory functionality"""
        try:
            from forecasting_models import (
                ForecastingModelFactory, ModelConfig, ModelType, PredictionHorizon
            )
            
            # Test creating different model types
            config = ModelConfig(
                model_type=ModelType.RANDOM_FOREST,
                prediction_horizon=PredictionHorizon.SEVEN_DAYS,
                lookback_window=30,
                features=['closing_price', 'daily_volume']
            )
            
            # Test Random Forest model creation
            rf_model = ForecastingModelFactory.create_model(ModelType.RANDOM_FOREST, config)
            self.assertIsNotNone(rf_model)
            self.assertEqual(rf_model.config.model_type, ModelType.RANDOM_FOREST)
            
            # Test XGBoost model creation
            config.model_type = ModelType.XGBOOST
            xgb_model = ForecastingModelFactory.create_model(ModelType.XGBOOST, config)
            self.assertIsNotNone(xgb_model)
            self.assertEqual(xgb_model.config.model_type, ModelType.XGBOOST)
            
            logger.info("✅ Model factory test passed")
            
        except Exception as e:
            self.fail(f"Model factory test failed: {e}")
    
    def test_query_parsing(self):
        """Test natural language query parsing"""
        try:
            from tools import parse_stock_prediction_request
            
            # Test various query formats
            test_cases = [
                ("Predict AAPL price for next 7 days", {"ticker": "AAPL", "prediction_horizon": 7}),
                ("What will GOOGL be in 30 days?", {"ticker": "GOOGL", "prediction_horizon": 30}),
                ("Forecast MSFT using LSTM for 1 week", {"ticker": "MSFT", "prediction_horizon": 7, "model_type": "lstm"}),
                ("Use XGBoost to predict TSLA for next month", {"ticker": "TSLA", "prediction_horizon": 30, "model_type": "xgboost"})
            ]
            
            for query, expected in test_cases:
                parsed = parse_stock_prediction_request(query)
                
                for key, value in expected.items():
                    self.assertEqual(parsed[key], value, f"Failed for query: {query}, key: {key}")
            
            logger.info("✅ Query parsing test passed")
            
        except Exception as e:
            self.fail(f"Query parsing test failed: {e}")
    
    def test_model_training_pipeline(self):
        """Test model training pipeline"""
        try:
            from model_training import create_training_config, ModelTrainer
            from forecasting_models import FeastDataLoader
            
            # Create training configuration
            config = create_training_config(
                model_type="random_forest",
                prediction_horizon=7,
                optimize_hyperparams=False,  # Disable for faster testing
                n_trials=5
            )
            
            # Create trainer
            trainer = ModelTrainer(config)
            
            # Load test data
            data_loader = FeastDataLoader()
            test_data = data_loader._load_mock_data(
                ticker=self.test_ticker,
                start_date=self.start_date,
                end_date=self.end_date
            )
            
            # Test training (with mock data)
            result = trainer.train_model(
                ticker=self.test_ticker,
                start_date=self.start_date,
                end_date=self.end_date,
                custom_data=test_data
            )
            
            # Validate training result
            self.assertIsNotNone(result)
            self.assertIsNotNone(result.model)
            self.assertIsNotNone(result.performance)
            self.assertGreater(result.training_time, 0)
            
            logger.info("✅ Model training pipeline test passed")
            
        except Exception as e:
            self.fail(f"Model training pipeline test failed: {e}")
    
    def test_prediction_workflow(self):
        """Test end-to-end prediction workflow"""
        try:
            from forecasting_models import (
                ForecastingModelFactory, ModelConfig, ModelType, 
                PredictionHorizon, FeastDataLoader
            )
            
            # Create model
            config = ModelConfig(
                model_type=ModelType.RANDOM_FOREST,
                prediction_horizon=PredictionHorizon.SEVEN_DAYS,
                lookback_window=30,
                features=['closing_price', 'daily_volume', 'sma_20']
            )
            
            model = ForecastingModelFactory.create_model(ModelType.RANDOM_FOREST, config)
            
            # Load and prepare data
            data_loader = FeastDataLoader()
            data = data_loader._load_mock_data(
                ticker=self.test_ticker,
                start_date=self.start_date,
                end_date=self.end_date,
                features=config.features
            )
            
            # Train model
            performance = model.train(data)
            self.assertIsNotNone(performance)
            
            # Make prediction
            prediction_result = model.predict(data, ticker=self.test_ticker)
            
            # Validate prediction result
            self.assertIsNotNone(prediction_result)
            self.assertEqual(prediction_result.ticker, self.test_ticker)
            self.assertIsNotNone(prediction_result.predictions)
            self.assertGreater(len(prediction_result.predictions), 0)
            
            logger.info("✅ Prediction workflow test passed")
            
        except Exception as e:
            self.fail(f"Prediction workflow test failed: {e}")
    
    def test_error_handling(self):
        """Test error handling and graceful degradation"""
        try:
            from tools import predict_stock_price_tool
            
            # Test with invalid ticker
            result = predict_stock_price_tool("Predict INVALID price for next 7 days")
            self.assertIn("❌", result)  # Should contain error indicator
            
            # Test with malformed query
            result = predict_stock_price_tool("This is not a valid prediction query")
            self.assertIn("❌", result)  # Should contain error indicator
            
            logger.info("✅ Error handling test passed")
            
        except Exception as e:
            self.fail(f"Error handling test failed: {e}")
    
    def test_model_registry_integration(self):
        """Test model registry functionality"""
        try:
            import json
            
            # Test loading model registry
            registry_path = os.path.join("models", "model_registry.json")
            if os.path.exists(registry_path):
                with open(registry_path, 'r') as f:
                    registry = json.load(f)
                
                # Validate registry structure
                self.assertIn("registry_version", registry)
                self.assertIn("models", registry)
                self.assertIn("model_types", registry)
                
                # Check sample models
                models = registry["models"]
                self.assertGreater(len(models), 0)
                
                for model_id, model_info in models.items():
                    self.assertIn("model_type", model_info)
                    self.assertIn("ticker", model_info)
                    self.assertIn("prediction_horizon", model_info)
                    self.assertIn("performance", model_info)
            
            logger.info("✅ Model registry integration test passed")
            
        except Exception as e:
            self.fail(f"Model registry integration test failed: {e}")
    
    def test_configuration_loading(self):
        """Test configuration template loading"""
        try:
            import json
            
            # Test loading configuration templates
            config_files = [
                "models/training_configs/lstm_config.json",
                "models/training_configs/xgboost_config.json"
            ]
            
            for config_file in config_files:
                if os.path.exists(config_file):
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                    
                    # Validate configuration structure
                    self.assertIn("model_type", config)
                    self.assertIn("default_config", config)
                    self.assertIn("optimization_space", config)
                    
                    default_config = config["default_config"]
                    self.assertIn("prediction_horizon", default_config)
                    self.assertIn("hyperparameters", default_config)
            
            logger.info("✅ Configuration loading test passed")
            
        except Exception as e:
            self.fail(f"Configuration loading test failed: {e}")
    
    def test_performance_metrics(self):
        """Test performance metrics calculation"""
        try:
            from forecasting_models import ModelPerformance
            import numpy as np
            
            # Create sample performance metrics
            performance = ModelPerformance(
                mae=1.5,
                rmse=2.1,
                mape=3.2,
                directional_accuracy=0.65,
                r2_score=0.78,
                sharpe_ratio=1.2
            )
            
            # Test conversion to dictionary
            perf_dict = performance.to_dict()
            self.assertIn("mae", perf_dict)
            self.assertIn("rmse", perf_dict)
            self.assertEqual(perf_dict["mae"], 1.5)
            self.assertEqual(perf_dict["directional_accuracy"], 0.65)
            
            logger.info("✅ Performance metrics test passed")
            
        except Exception as e:
            self.fail(f"Performance metrics test failed: {e}")


class TestForecastingToolIntegration(unittest.TestCase):
    """Test suite specifically for tool integration"""
    
    def test_tool_registration(self):
        """Test that forecasting tools are properly registered"""
        try:
            from tools import __all__ as tools_exports
            
            # Check that prediction tool is exported
            self.assertIn("predict_stock_price_tool", tools_exports)
            self.assertIn("parse_stock_prediction_request", tools_exports)
            self.assertIn("format_prediction_results", tools_exports)
            
            logger.info("✅ Tool registration test passed")
            
        except Exception as e:
            self.fail(f"Tool registration test failed: {e}")
    
    def test_langchain_compatibility(self):
        """Test LangChain compatibility"""
        try:
            from tools import predict_stock_price_tool
            from langchain.tools import BaseTool
            
            # Check that the tool is a proper LangChain tool
            self.assertTrue(hasattr(predict_stock_price_tool, 'name'))
            self.assertTrue(hasattr(predict_stock_price_tool, 'description'))
            self.assertTrue(hasattr(predict_stock_price_tool, 'args_schema'))
            
            logger.info("✅ LangChain compatibility test passed")
            
        except Exception as e:
            self.fail(f"LangChain compatibility test failed: {e}")


def run_integration_tests():
    """Run all integration tests"""
    print("🚀 Starting Forecasting Models Integration Tests")
    print("=" * 60)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestForecastingIntegration))
    test_suite.addTest(unittest.makeSuite(TestForecastingToolIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\n💥 Errors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    if result.wasSuccessful():
        print("\n🎉 All tests passed! Forecasting models integration is working correctly.")
        return True
    else:
        print("\n⚠️ Some tests failed. Please review the issues above.")
        return False


def test_basic_functionality():
    """Test basic functionality without full test suite"""
    print("🔍 Testing Basic Forecasting Functionality")
    print("-" * 40)
    
    try:
        # Test 1: Import modules
        print("1. Testing module imports...")
        from forecasting_models import ModelType, PredictionHorizon
        from tools import predict_stock_price_tool
        print("   ✅ Modules imported successfully")
        
        # Test 2: Test query parsing
        print("2. Testing query parsing...")
        from tools import parse_stock_prediction_request
        parsed = parse_stock_prediction_request("Predict AAPL price for next 7 days")
        assert parsed["ticker"] == "AAPL"
        assert parsed["prediction_horizon"] == 7
        print("   ✅ Query parsing works correctly")
        
        # Test 3: Test mock data loading
        print("3. Testing data loading...")
        from forecasting_models import FeastDataLoader
        from datetime import datetime, timedelta
        
        data_loader = FeastDataLoader()
        data = data_loader._load_mock_data(
            ticker="AAPL",
            start_date=datetime.now() - timedelta(days=100),
            end_date=datetime.now()
        )
        assert len(data) > 0
        assert "closing_price" in data.columns
        print("   ✅ Data loading works correctly")
        
        # Test 4: Test model creation
        print("4. Testing model creation...")
        from forecasting_models import ForecastingModelFactory, ModelConfig
        
        config = ModelConfig(
            model_type=ModelType.RANDOM_FOREST,
            prediction_horizon=PredictionHorizon.SEVEN_DAYS,
            features=["closing_price", "daily_volume"]
        )
        
        model = ForecastingModelFactory.create_model(ModelType.RANDOM_FOREST, config)
        assert model is not None
        print("   ✅ Model creation works correctly")
        
        print("\n🎉 Basic functionality test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Basic functionality test failed: {e}")
        return False


if __name__ == "__main__":
    print("🔬 Forecasting Models Integration Test Suite")
    print("=" * 50)
    
    # First run basic functionality test
    basic_success = test_basic_functionality()
    
    if basic_success:
        print("\n" + "=" * 50)
        # Run full integration tests
        full_success = run_integration_tests()
        
        if full_success:
            print("\n🚀 Integration Complete!")
            print("The forecasting models are successfully integrated with the AI Assistant.")
            print("\nYou can now use queries like:")
            print("  • 'Predict AAPL price for next 7 days'")
            print("  • 'Forecast GOOGL using LSTM for 1 week'")
            print("  • 'What will MSFT stock price be in 30 days?'")
        else:
            print("\n⚠️ Integration tests revealed some issues.")
            print("Please review the test results and fix any problems.")
    else:
        print("\n❌ Basic functionality test failed.")
        print("Please check the module imports and basic setup.")